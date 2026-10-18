"""Studies 2 and 3: run an agent over a chain of dependent steps, carrying its tree.

Layout: ``runs2/<agent>/<cond>/<zone>/<chain>/`` (study 3: ``runs3/``, pilot
``runs3-pilot/``) with ``chain.json`` (per-step statuses) and one dir per step
``T<k>/``:

  transcript.jsonl  raw agent stdout
  stderr.log        agent stderr
  setup_ok          the container built the step's start tree
  start.json        tree ref of the step's pre-image: where it comes from (``image``
                    or ``T<j>/tree.tar``), the carried patches in order, and the
                    expected start tree (previous step's ``post_tree``)
  start_tree        git tree id of the start tree, computed in the container
  start_commit      sha of the step's root commit ``start`` (before the agent)
  start_commit_after  the root commit named ``start`` (else HEAD's only root) after
                    the agent; missing when .git is gone or ambiguous
  start_commit_ancestor  1/0: HEAD descends from ``start_commit`` after the agent
  diff.patch        ``git diff --cached --binary <start commit>`` after the agent
                    (against the recorded start commit, so agent commits are kept)
  post_tree         git tree id of the agent's final tree
  diff_ok           diff.patch re-applied on the start tree reproduces post_tree
  tree.tar          only when diff_ok is missing: the tree as the agent left it
                    (no .git, no node_modules); the next step starts from it
  cli_version       ``claude --version`` / ``codex --version`` in the container
  index_flags, stash_present, gitattributes_changed, info_attributes, ...
                    git state that hides changes from the dump (see ``git_hiding``)
  agent.json        status, usage, wall, carry record, ... (as study 1, plus
                    zone/chain/step, the step's limits, the model and CLI version
                    reported by the run, ``git_hiding``)

Carrying (plan Task 3): step 1 starts from the untouched variant image; step k starts
from the image + the verified diffs of steps 1..k-1 applied in order with
``git apply --3way`` (each diff's pre-image is exactly the previous result, so this
is step k-1's start tree + its diff). When a step's diff cannot reproduce its tree
(agent destroyed .git, ...), its ``tree.tar`` replaces the tracked files and later
diffs apply on top. Tree ids are content hashes, so ``start_tree`` of step k must
equal ``post_tree`` of step k-1: a mismatch on a patch-only carry is a
``setup_error`` (harness defect), never silently accepted.

Isolation is study 1's: per-condition image, fresh container per step, only the
prompt mounted, blocked hosts, no web, isolated agent config, same effort. The
carried patches arrive on stdin as a tar and are deleted before the agent starts,
and the start tree is committed into a fresh repository (no history): the code is
the only carrier between steps. Hidden tests are never mounted.

Study 3 (spec 2026-10-10, plan Task 4): arms R, RG, RL, RC, each on its own image.
An RC chain runs T0 (``tasks3/<zone>/T0/statement.md``, 40 min / 90 turns) before
T1..T4; T0 is carried exactly like any other step (T1's start tree = image + T0's
verified diff, or T0's tree.tar) and is stored as step ``T0`` with ``step_index``
None, so T1..T4 keep the study-2 indices 0..3 and nothing of T1..T4 counts T0. The
scheduler interleaves arms per agent (:func:`build_chain_queue3`).

A step that leaves broken code is still ``ok``/``timeout`` and the chain goes on
from its tree (carried defects are an outcome). ``infra`` stops the chain at that
step; the scheduler re-queues the chain with backoff and resumes from that step.
Re-running a step deletes the later steps' dirs (they were built on the old tree).
"""
from __future__ import annotations

import json
import os
import random
import re
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from aa import config, runner
from aa.agents import detect_contamination, parse_stream, transport_stalled
from aa.chains import Chain, T0_ID, load_arm_chain

RUNS2 = config.ROOT / os.environ.get("AA_RUNS2_DIR", "runs2")
RUNS3 = config.ROOT / os.environ.get("AA_RUNS3_DIR", "runs3")
RUNS_PILOT = {2: config.ROOT / "runs2-pilot", 3: config.ROOT / "runs3-pilot"}
CONDITIONS2: tuple[str, ...] = tuple(getattr(config, "CONDITIONS2", ("R", "F")))
# Study 3 arms, in the order the scheduler rotates (ARMS[(i + k + z) % 4], amendment
# 2026-10-11e).
ARMS: tuple[str, ...] = tuple(config.CONDITIONS3)
STUDY_CONDITIONS = {2: CONDITIONS2, 3: ARMS}
STUDY_RUNS = {2: RUNS2, 3: RUNS3}
# `aa chain run` default chains in parallel: study 3 has T0 (40 min, a full
# consolidation) and the RL lint in the agent's loop; the 6 GB Docker VM holds two
# loot-core containers at most (pre-pilot review, 2026-10-11).
STUDY_WORKERS = {2: config.CONCURRENCY, 3: 2}
CHAINS = 8
SCHEDULE_SEED = 20261008
# Steps whose tree the next step starts from (a broken or timed-out step is carried).
CARRIED = ("ok", "timeout")
SETUP_EXIT = runner.SETUP_EXIT
# Host-side grace on top of the in-container `timeout`: setup (git add/commit of the
# whole tree, carried patches) and the post-step dump.
HOST_GRACE_S = 600


class CarryError(RuntimeError):
    """The previous steps do not leave a tree the next step can start from."""


# --------------------------------------------------------------------------- paths

def chain_dir(agent: str, cond: str, zone: str, chain_idx: int,
              runs_root: Path | None = None) -> Path:
    """One tree per (agent, cond, zone, chain): chains never share state (Review Focus 5)."""
    return (runs_root or RUNS2) / agent / cond / zone / str(chain_idx)


def container_name(agent: str, cond: str, zone: str, chain_idx: int, step_id: str,
                   study: int = 2, runs_root: Path | None = None) -> str:
    """``aa<study>-[<runs-root tag>-]<agent>-<cond>-<zone>-<chain>-<step>``: the tag (a
    short hash of the runs root, as the evaluator's names) keeps runs3, runs3-pilot and
    test trees from colliding on one Docker host."""
    tag = f"{root_tag(runs_root)}-" if runs_root is not None else ""
    return f"aa{study}-{tag}{agent}-{cond}-{zone}-{chain_idx}-{step_id}".lower()


def root_tag(root: Path) -> str:
    """Short hash of a directory (a runs root, a sanity work dir)."""
    import hashlib
    return hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()[:6]


def study_of(conds: Iterable[str], study: int | None = None) -> int:
    """The study a set of conditions belongs to: ``study`` if given (validated), else 3
    when any study-3-only arm (RG, RL, RC) is present, else 2. ValueError when a
    condition is not in the study (e.g. F in study 3, A anywhere)."""
    conds = list(conds)
    if study is None:
        study = 3 if any(c in ARMS and c not in CONDITIONS2 for c in conds) else 2
    if study not in STUDY_CONDITIONS:
        raise ValueError(f"unknown study {study!r}")
    bad = [c for c in conds if c not in STUDY_CONDITIONS[study]]
    if bad:
        raise ValueError(f"condition(s) {bad} not in study {study} "
                         f"({', '.join(STUDY_CONDITIONS[study])})")
    return study


# --------------------------------------------------------------------------- container

def _auth_setup(agent: str) -> str:
    if config.engine(agent) == "claude":
        return "mkdir -p /tmp/cc"
    if config.engine(agent) == "codex":
        return "mkdir -p /tmp/codexhome && cp /codex-auth/auth.json /tmp/codexhome/auth.json"
    raise ValueError(f"unknown agent {agent!r}")


def version_command(agent: str) -> str:
    """The CLI's own version report, run in the container before the agent."""
    return f"{config.engine(agent)} --version"


# Git state after the agent that can keep a change out of `git add -A` / `git diff`
# (re-review of plan Tasks 1-3): attribute and exclude sources outside the tree, index
# entries marked assume-unchanged (lowercase tag in `git ls-files -v`) or skip-worktree
# (S), and a stash. Written to /out as files; read by read_git_hiding.
GIT_HIDING_SCRIPT = [
    'if [ -d .git ]; then',
    '  git ls-files -v 2>/dev/null | grep -E "^([a-z]|S) " > "$O/index_flags"',
    '  if git rev-parse -q --verify refs/stash >/dev/null 2>&1; then echo 1; else echo 0; fi '
    '> "$O/stash_present"',
    '  : > "$O/attributes_sources"; : > "$O/excludes_sources"',
    '  [ -s .git/info/attributes ] && echo info/attributes >> "$O/attributes_sources"',
    '  [ -n "$(git config --get core.attributesFile 2>/dev/null)" ] '
    '&& echo core.attributesFile >> "$O/attributes_sources"',
    '  [ -s "$HOME/.config/git/attributes" ] && echo "~/.config/git/attributes" '
    '>> "$O/attributes_sources"',
    '  [ "$(git hash-object .git/info/exclude 2>/dev/null)" = "$EX0" ] '
    '|| echo info/exclude >> "$O/excludes_sources"',
    '  [ -n "$(git config --get core.excludesFile 2>/dev/null)" ] '
    '&& echo core.excludesFile >> "$O/excludes_sources"',
    '  [ -s "$HOME/.config/git/ignore" ] && echo "~/.config/git/ignore" >> "$O/excludes_sources"',
    '  touch "$O/git_checked"',
    'fi',
]


def chain_container_script(agent: str, wall_limit_s: int = config.WALL_LIMIT_S,
                           workdir: str = "/work/actual", out: str = "/out",
                           agent_cmd: str | None = None, auth: str | None = None,
                           turn_limit: int = config.TURN_LIMIT,
                           version_cmd: str | None = None) -> str:
    """Build step k's start tree from the start bundle (tar on stdin), run the agent
    under `timeout`, dump the diff against the start commit and verify it.

    ``workdir``/``out``/``agent_cmd``/``auth``/``version_cmd`` exist so tests can run
    the same script locally with a fake agent; real runs use the defaults.
    """
    auth = _auth_setup(agent) if auth is None else auth
    cmd = runner.agent_command(agent, turn_limit) if agent_cmd is None else agent_cmd
    version_cmd = version_command(agent) if version_cmd is None else version_cmd
    fail = lambda msg: f'{{ echo "aa: {msg}" >&2; exit {SETUP_EXIT}; }}'  # noqa: E731
    commit = "git -c commit.gpgsign=false commit -q --no-verify"
    return "\n".join([
        "set -u",
        f"W='{workdir}'; O='{out}'",
        f'cd "$W" || exit {SETUP_EXIT}',
        'S=$(mktemp -d)',
        f'tar -x -f - -C "$S" || {fail("start bundle unreadable")}',
        # The image tree (variant + its install step) is the origin of every chain.
        f'git add -A && {commit} --allow-empty -m image || {fail("image commit failed")}',
        f'if [ -f "$S/base.tar" ]; then {{ git ls-files -z | xargs -0 rm -f; }} '
        f'&& tar -xf "$S/base.tar" && git add -A || {fail("carried tree does not extract")}; fi',
        'for p in $(ls "$S/patches" 2>/dev/null | sort); do',
        f'  git apply --3way --allow-empty --whitespace=nowarn "$S/patches/$p" '
        f'|| {fail("carried patch $p does not apply")}',
        'done',
        'rm -rf "$S"',
        f'rm -rf .git && git init -q -b main && git add -A && {commit} -m start '
        f'|| {fail("start commit failed")}',
        'START=$(git rev-parse HEAD)',
        'echo "$START" > "$O/start_commit"',
        'git rev-parse "HEAD^{tree}" > "$O/start_tree"',
        'touch "$O/setup_ok"',
        'EX0=$(git hash-object .git/info/exclude 2>/dev/null)',
        auth,
        f'{version_cmd} > "$O/cli_version" 2>/dev/null < /dev/null || rm -f "$O/cli_version"',
        f"timeout {wall_limit_s} bash -c '{runner._sq(cmd)}' < /dev/null",
        'echo $? > "$O/exit_code"',
        # Dump: whatever the agent did to HEAD/branches, diff the worktree against
        # the recorded start commit; then prove the diff reproduces the tree.
        'cd "$W" 2>/dev/null && rm -f .git/index.lock',
        *GIT_HIDING_SCRIPT,
        # The start commit as RL's dup-check finds it after the agent (the root of
        # HEAD named "start", else HEAD's only root) and whether HEAD descends from the
        # recorded one: a rewritten start would hide changes from `git diff <start>`.
        'R=$(git rev-list --max-parents=0 HEAD 2>/dev/null); N=""',
        'for r in $R; do [ "$(git log -1 --format=%s "$r")" = start ] && N="$N $r"; done',
        'set -- $N; if [ $# -eq 1 ]; then echo "$1" > "$O/start_commit_after"; '
        'else set -- $R; [ $# -eq 1 ] && echo "$1" > "$O/start_commit_after"; fi',
        'if [ -n "$R" ]; then git merge-base --is-ancestor "$START" HEAD 2>/dev/null '
        '&& echo 1 > "$O/start_commit_ancestor" || echo 0 > "$O/start_commit_ancestor"; fi',
        # A changed .gitattributes (e.g. `* text=auto` dropped) changes how files hash on
        # the next step's fresh `git add -A`, while stat-clean index entries here keep the
        # old normalization: renormalize then, or the carry would not reproduce the tree.
        'git add -A >/dev/null 2>&1 && git diff --cached --name-only --no-renames "$START" '
        '2>/dev/null | grep -qE "(^|/)\\.gitattributes$" && git add --renormalize . >/dev/null 2>&1',
        'if git add -A >/dev/null 2>&1 && git diff --cached --binary "$START" > "$O/diff.patch" '
        '&& git write-tree > "$O/post_tree"; then',
        '  I=$(mktemp -u)',
        '  if GIT_INDEX_FILE="$I" git read-tree "$START" '
        '&& GIT_INDEX_FILE="$I" git apply --cached --allow-empty "$O/diff.patch" '
        '&& [ "$(GIT_INDEX_FILE="$I" git write-tree)" = "$(cat "$O/post_tree")" ]; '
        'then touch "$O/diff_ok"; fi',
        '  rm -f "$I"',
        # .gitattributes added/changed/removed in the tree (diff/merge/filter attributes
        # change what `git diff` shows); --no-renames lists both sides of a move.
        '  [ -f "$O/git_checked" ] && git diff --cached --name-only --no-renames "$START" '
        '2>/dev/null | grep -E "(^|/)\\.gitattributes$" > "$O/gitattributes_changed"',
        'fi',
        '[ -f "$O/diff_ok" ] || tar --exclude=./.git --exclude=node_modules -cf "$O/tree.tar" .',
    ])


def chain_docker_argv(agent: str, cond: str, name: str, prompt_file: Path, out_dir: Path,
                      codex_auth_dir: Path | None = None,
                      wall_limit_s: int = config.WALL_LIMIT_S,
                      turn_limit: int = config.TURN_LIMIT) -> list[str]:
    """`docker run -i` argv with study 1's isolation; the start bundle goes to stdin."""
    argv = ["docker", "run", "--rm", "-i", "--name", name, "--cpus", runner.CPUS,
            "--memory", runner.MEMORY,
            "-v", f"{prompt_file}:/task/prompt.txt:ro", "-v", f"{out_dir}:/out"]
    argv += runner.blocked_host_args()
    if config.engine(agent) == "claude":
        argv += ["-e", "CLAUDE_CONFIG_DIR=/tmp/cc", "-e", "CLAUDE_CODE_OAUTH_TOKEN"]
    elif config.engine(agent) == "codex":
        if codex_auth_dir is None:
            raise ValueError("codex needs codex_auth_dir")
        argv += ["-v", f"{codex_auth_dir}:/codex-auth:ro", "-e", "CODEX_HOME=/tmp/codexhome"]
    else:
        raise ValueError(f"unknown agent {agent!r}")
    argv += [runner.image_tag(cond), "bash", "-lc",
             chain_container_script(agent, wall_limit_s, turn_limit=turn_limit)]
    return argv


# Launcher(agent, cond, name, prompt_file, out_dir, tmp_dir, wall_limit_s, turn_limit)
#   -> (argv, env)
Launcher = Callable[[str, str, str, Path, Path, Path, int, int],
                    tuple[list[str], dict[str, str]]]
# Executor(argv, env, stdin_file, timeout_s, name) -> (returncode or None, stderr tail)
Executor = Callable[[list[str], dict[str, str], Path, float, str], tuple[int | None, str]]


def docker_launcher(agent: str, cond: str, name: str, prompt_file: Path, out_dir: Path,
                    tmp: Path, wall_limit_s: int,
                    turn_limit: int = config.TURN_LIMIT) -> tuple[list[str], dict[str, str]]:
    env = os.environ.copy()
    auth_dir = None
    if config.engine(agent) == "claude":
        env["CLAUDE_CODE_OAUTH_TOKEN"] = runner.CLAUDE_TOKEN_FILE.read_text().strip()
    elif config.engine(agent) == "codex":
        auth_dir = tmp / "codex-auth"
        auth_dir.mkdir()
        shutil.copy(runner.CODEX_AUTH, auth_dir / "auth.json")
    return chain_docker_argv(agent, cond, name, prompt_file, out_dir, auth_dir, wall_limit_s,
                             turn_limit), env


def subprocess_executor(argv: list[str], env: dict[str, str], stdin_file: Path,
                        timeout_s: float, name: str) -> tuple[int | None, str]:
    with stdin_file.open("rb") as fin:
        try:
            proc = subprocess.run(argv, env=env, stdin=fin, capture_output=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True)
            return None, "host timeout"
    return proc.returncode, proc.stderr.decode("utf-8", "replace")[-4000:]


# --------------------------------------------------------------------------- carrying

def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _read_text(path: Path) -> str | None:
    return path.read_text().strip() if path.exists() else None


def start_plan(cdir: Path, step_ids: Iterable[str], k: int) -> dict:
    """Tree ref of step ``k`` (0-based)'s start tree from steps 0..k-1 on disk.

    Returns {"from": "image" | "T<j>/tree.tar", "patches": ["T<i>/diff.patch", ...],
    "expected_start_tree": <post_tree of step k-1> | None}.
    """
    ids = list(step_ids)
    base: str | None = None
    patches: list[str] = []
    expected: str | None = None
    for sid in ids[:k]:
        d = cdir / sid
        status = _read_json(d / "agent.json").get("status")
        if status not in CARRIED:
            raise CarryError(f"{sid} is not final ({status})")
        if (d / "diff_ok").exists() and (d / "diff.patch").exists():
            patches.append(f"{sid}/diff.patch")
        elif (d / "tree.tar").exists():
            base, patches = f"{sid}/tree.tar", []
        else:
            raise CarryError(f"{sid}: neither a verified diff.patch nor tree.tar")
        expected = _read_text(d / "post_tree")
    return {"from": base or "image", "patches": patches, "expected_start_tree": expected}


def write_bundle(cdir: Path, plan: dict, dest: Path) -> Path:
    """The start bundle (tar) the container reads on stdin: optional base.tar +
    patches/NN-<step>.patch, applied in name order."""
    with tarfile.open(dest, "w") as tar:
        if plan["from"] != "image":
            tar.add(cdir / plan["from"], arcname="base.tar")
        for i, rel in enumerate(plan["patches"], start=1):
            tar.add(cdir / rel, arcname=f"patches/{i:02d}-{rel.split('/')[0]}.patch")
    return dest


# --------------------------------------------------------------------------- records

def _lines(path: Path) -> list[str]:
    return [ln for ln in path.read_text(errors="replace").splitlines() if ln.strip()] \
        if path.exists() else []


def read_git_hiding(out: Path) -> dict | None:
    """Git state after the agent that can hide changes from the dump (written by
    GIT_HIDING_SCRIPT); None when it could not be read (no .git after the agent)."""
    if not (out / "git_checked").exists():
        return None
    return {
        "gitattributes_changed": _lines(out / "gitattributes_changed"),
        "attributes_sources": _lines(out / "attributes_sources"),
        # `git ls-files -v` lines: "<tag> <path>", lowercase = assume-unchanged, S = skip-worktree
        "index_flags": _lines(out / "index_flags"),
        "excludes_sources": _lines(out / "excludes_sources"),
        "stash_present": _read_text(out / "stash_present") == "1",
    }


def reported_models(lines: Iterable[str]) -> list[str]:
    """Distinct model ids the transcript names, in order of appearance: Claude Code's
    init message and each assistant message (``message.model``). Codex's ``--json``
    stream names none (the requested id is ``model``)."""
    out: list[str] = []
    for ln in lines:
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        msg = obj.get("message")
        for m in (obj.get("model"), msg.get("model") if isinstance(msg, dict) else None):
            if isinstance(m, str) and m and m not in out:
                out.append(m)
    return out


def step_limits(step, wall_limit_s: int) -> tuple[int, int]:
    """(wall seconds, turns) of a step: its own (T0) or the chain defaults."""
    return (step.wall_limit_s or wall_limit_s, step.turn_limit or config.TURN_LIMIT)


def step_index(chain: Chain, k: int) -> int | None:
    """Index of step ``k`` among T1..Tn (0-based, as in study 2); None for T0."""
    if chain.steps[k].id == T0_ID:
        return None
    return k - sum(1 for s in chain.steps[:k] if s.id == T0_ID)


# --------------------------------------------------------------------------- one step

def _write_agent_json(out: Path, record: dict) -> None:
    (out / "agent.json").write_text(json.dumps(record, indent=2) + "\n")


def run_step(agent: str, cond: str, chain: Chain, chain_idx: int, k: int,
             runs_root: Path | None = None, wall_limit_s: int = config.WALL_LIMIT_S,
             launcher: Launcher = docker_launcher,
             executor: Executor = subprocess_executor, study: int = 2) -> Path:
    """Run step ``k`` (0-based position in ``chain.steps``) of one chain; returns the
    step dir (always has agent.json). ``wall_limit_s`` is the T1..Tn limit; T0 has its own."""
    cdir = chain_dir(agent, cond, chain.zone, chain_idx, runs_root or STUDY_RUNS[study])
    step = chain.steps[k]
    out = cdir / step.id
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    wall, turns = step_limits(step, wall_limit_s)
    base = {"agent": agent, "cond": cond, "zone": chain.zone, "chain": chain_idx,
            "step": step.id, "step_index": step_index(chain, k),
            "model": config.MODELS.get(agent),
            "effort": config.EFFORT, "cli_version": runner.CLI_VERSIONS.get(agent),
            "study": study, "limits": {"wall_s": wall, "turns": turns}}
    try:
        return _run_step(agent, cond, chain, chain_idx, k, cdir, out, base, wall, turns,
                         launcher, executor, study)
    except Exception as e:  # noqa: BLE001 - recorded so the step is never silently lost
        _write_agent_json(out, base | {"status": "harness_error",
                                       "error": f"{type(e).__name__}: {e}"})
        return out


def _run_step(agent: str, cond: str, chain: Chain, chain_idx: int, k: int, cdir: Path,
              out: Path, base: dict, wall_limit_s: int, turn_limit: int, launcher: Launcher,
              executor: Executor, study: int) -> Path:
    step = chain.steps[k]
    plan = start_plan(cdir, chain.step_ids, k)
    (out / "start.json").write_text(json.dumps(plan, indent=2) + "\n")
    prompt = runner.render_prompt(step.statement())
    name = container_name(agent, cond, chain.zone, chain_idx, step.id, study,
                          runs_root=Path(cdir).resolve().parents[3])
    with tempfile.TemporaryDirectory(prefix="aa2-step-") as tmp:
        tmp = Path(tmp)
        prompt_file = tmp / "prompt.txt"
        prompt_file.write_text(prompt)
        bundle = write_bundle(cdir, plan, tmp / "start.tar")
        argv, env = launcher(agent, cond, name, prompt_file, out, tmp, wall_limit_s,
                             turn_limit)
        started = datetime.now(timezone.utc)
        t0 = time.monotonic()
        docker_rc, docker_err = executor(argv, env, bundle, wall_limit_s + HOST_GRACE_S, name)
        wall_s = round(time.monotonic() - t0, 1)
    exit_code_s = _read_text(out / "exit_code")
    exit_code = int(exit_code_s) if exit_code_s else None
    transcript = out / "transcript.jsonl"
    lines = transcript.read_text(errors="replace").splitlines() if transcript.exists() else []
    usage, outcome = parse_stream(agent, lines)
    status = runner.classify_setup((out / "setup_ok").exists(), docker_rc) \
        or runner.classify_status(outcome, exit_code, usage, turn_limit,
                                  stalled=transport_stalled(agent, lines))
    start_tree = _read_text(out / "start_tree")
    expected = plan["expected_start_tree"]
    carry_exact = None if expected is None or start_tree is None else start_tree == expected
    error = ""
    if carry_exact is False and plan["from"] == "image":
        # Patch-only carry must reproduce the previous step's tree bit for bit.
        status, error = "setup_error", f"carry mismatch: start_tree {start_tree} != {expected}"
    start_commit = _read_text(out / "start_commit") or None
    start_after = _read_text(out / "start_commit_after") or None
    anc = _read_text(out / "start_commit_ancestor")
    start_ancestor = None if anc is None else anc == "1"
    rewritten = None if start_commit is None else (
        start_after != start_commit or start_ancestor is not True)
    hits = detect_contamination(agent, lines, ())
    _write_agent_json(out, base | {
        "status": status, "outcome": outcome, "exit_code": exit_code, "docker_rc": docker_rc,
        "docker_stderr": docker_err if status in ("infra", "setup_error") else "",
        "error": error,
        "usage": asdict(usage), "wall_s": wall_s, "started_at": started.isoformat(),
        "image_digest": runner.image_digest(runner.image_tag(cond)),
        "carry": plan | {"start_tree": start_tree, "exact": carry_exact},
        "post_tree": _read_text(out / "post_tree"),
        # RL gaming evidence (aa.static3.runner_flags): diff.patch cannot show it
        "start_commit": start_commit, "start_commit_after": start_after,
        "start_commit_ancestor": start_ancestor, "start_commit_rewritten": rewritten,
        # changes kept out of the dump (aa.static3.runner_flags); None: .git gone
        "git_hiding": read_git_hiding(out),
        # what the run itself reports (the requested ones are model / cli_version)
        "model_reported": reported_models(lines),
        "cli_version_reported": _read_text(out / "cli_version") or None,
        "diff_ok": (out / "diff_ok").exists(),
        "tree_fallback": (out / "tree.tar").exists(),
        "contamination_flag": bool(hits), "contamination_hits": hits,
    })
    return out


# --------------------------------------------------------------------------- one chain

@dataclass(frozen=True)
class ChainResult:
    status: str               # ok (all steps carried) / infra / setup_error / harness_error
    step_path: Path | None    # the step that stopped the chain (or the last one)


def chain_statuses(cdir: Path, step_ids: Iterable[str]) -> dict[str, str | None]:
    return {sid: runner.read_status(cdir / sid) for sid in step_ids}


def chain_status(statuses: dict[str, str | None]) -> str | None:
    """'ok' when every step is carried, 'setup_error' when one is (final), else None."""
    vals = list(statuses.values())
    if "setup_error" in vals:
        return "setup_error"
    if vals and all(v in CARRIED for v in vals):
        return "ok"
    return None


def _write_chain_json(cdir: Path, agent: str, cond: str, chain: Chain, chain_idx: int,
                      study: int = 2) -> None:
    st = chain_statuses(cdir, chain.step_ids)
    rec = {"agent": agent, "cond": cond, "zone": chain.zone, "chain": chain_idx,
           "steps": st, "status": chain_status(st)}
    if study != 2:  # study-2 chain.json unchanged
        rec["study"] = study
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / "chain.json").write_text(json.dumps(rec, indent=2) + "\n")


def run_chain(agent: str, cond: str, zone: str, chain_idx: int,
              runs_root: Path | None = None, tasks_root: Path | None = None,
              wall_limit_s: int = config.WALL_LIMIT_S, only_step: str | None = None,
              launcher: Launcher = docker_launcher,
              executor: Executor = subprocess_executor, study: int = 2,
              t0_root: Path | None = None) -> ChainResult:
    """Run (or resume) one chain: steps in series, finished steps skipped.

    Stops at the first step that is not carried (infra / setup_error /
    harness_error). Re-running a step removes the later steps (stale start tree).
    ``only_step`` runs that single step (its predecessors must be carried).
    ``study`` 3 takes the arms R/RG/RL/RC (runs3/ by default); an RC chain starts
    with T0 from ``t0_root`` (default tasks3/).
    """
    study_of([cond], study)
    chain = load_arm_chain(zone, cond, tasks_root, t0_root)
    runs_root = runs_root or STUDY_RUNS[study]
    cdir = chain_dir(agent, cond, zone, chain_idx, runs_root)
    ids = list(chain.step_ids)
    if only_step is not None and only_step not in ids:
        raise ValueError(f"{zone} has no step {only_step!r} (steps: {ids})")
    last: Path | None = None
    for k, sid in enumerate(ids):
        sdir = cdir / sid
        st = runner.read_status(sdir)
        forced = only_step == sid
        if only_step is not None and not forced:
            if k > ids.index(only_step):
                break
            if st not in CARRIED:
                _write_chain_json(cdir, agent, cond, chain, chain_idx, study)
                return ChainResult(st or "harness_error", sdir)
            continue
        if st in CARRIED and not forced:
            last = sdir
            continue
        if st == "setup_error" and not forced:
            _write_chain_json(cdir, agent, cond, chain, chain_idx, study)
            return ChainResult("setup_error", sdir)
        for later in ids[k + 1:]:
            if (cdir / later).exists():
                shutil.rmtree(cdir / later)
        last = run_step(agent, cond, chain, chain_idx, k, runs_root, wall_limit_s,
                        launcher, executor, study)
        st = runner.read_status(last) or "infra"
        _write_chain_json(cdir, agent, cond, chain, chain_idx, study)
        if st not in CARRIED:
            return ChainResult(st, last)
    _write_chain_json(cdir, agent, cond, chain, chain_idx, study)
    return ChainResult("ok", last)


def resume_plan(cdir: Path, step_ids: Iterable[str]) -> dict:
    """What :func:`run_chain` would do with this chain dir, without running anything:
    ``resume_from`` (the first step that is not carried: missing, ``infra``,
    ``infra_exhausted``, ``harness_error``; None when the chain is complete or stopped at a
    ``setup_error``), its current ``status`` and ``discard`` (the later step dirs that
    exist and that the re-run removes, since they were built on the old tree)."""
    ids = list(step_ids)
    for k, sid in enumerate(ids):
        st = runner.read_status(cdir / sid)
        if st in CARRIED:
            continue
        if st == "setup_error":
            return {"resume_from": None, "status": st, "stopped_at": sid, "discard": []}
        return {"resume_from": sid, "status": st,
                "discard": [later for later in ids[k + 1:] if (cdir / later).exists()]}
    return {"resume_from": None, "status": "ok", "discard": []}


def plan_all_chains(agent: str, conds: Iterable[str], zones: Iterable[str],
                    chains: Iterable[int], runs_root: Path | None = None,
                    tasks_root: Path | None = None, study: int | None = None,
                    t0_root: Path | None = None) -> list[tuple[ChainJob, dict]]:
    """``aa chain run --dry-run``: the scheduler's queue with each chain's
    :func:`resume_plan`, in dispatch order."""
    conds = list(conds)
    study = study_of(conds, study)
    runs_root = runs_root or STUDY_RUNS[study]
    q = (build_chain_queue3 if study == 3 else build_chain_queue)(agent, conds, zones, chains)
    out = []
    for j in q:
        chain = load_arm_chain(j.zone, j.cond, tasks_root, t0_root)
        out.append((j, resume_plan(chain_dir(j.agent, j.cond, j.zone, j.chain_idx, runs_root),
                                   chain.step_ids)))
    return out


# --------------------------------------------------------------------------- scheduler

@dataclass(frozen=True)
class ChainJob:
    agent: str
    cond: str
    zone: str
    chain_idx: int


def build_chain_queue(agent: str, conds: Iterable[str], zones: Iterable[str],
                      chains: Iterable[int], seed: int = SCHEDULE_SEED) -> list[ChainJob]:
    """for chain, for zone, conditions shuffled with a fixed seed (quota drift hits
    both conditions equally)."""
    conds, zones = list(conds), list(zones)
    rng = random.Random(seed)
    q: list[ChainJob] = []
    for c in chains:
        for z in zones:
            order = conds[:]
            rng.shuffle(order)
            q += [ChainJob(agent, cond, z, c) for cond in order]
    return q


def build_chain_queue3(agent: str, conds: Iterable[str], zones: Iterable[str],
                       chains: Iterable[int]) -> list[ChainJob]:
    """Study 3 (spec section 2, plan Task 4, amendment 2026-10-11e): per agent, jobs
    ordered by chain index; for chain ``i`` and zone ``z`` (its own index,
    :func:`zone_index`: Z1 -> 0), the arms in the rotated order ``ARMS[(i + k + z) % n]``
    (k = 0..n-1, ARMS restricted to ``conds`` in canonical order). Over 8 chains each arm
    is first, second, ... equally often in every zone; with one chain per cell (the
    pilot) each arm is first in one zone instead of R always first."""
    conds = set(conds)
    bad = sorted(conds - set(ARMS))
    if bad:
        raise ValueError(f"not study-3 arms: {bad}")
    arms = [a for a in ARMS if a in conds]
    zones, n = list(zones), len(arms)
    return [ChainJob(agent, arms[(i + k + zone_index(z, zones)) % n], z, i)
            for i in sorted(set(chains)) for z in zones for k in range(n)]


def zone_index(zone: str, zones: Iterable[str] = ()) -> int:
    """The zone's own index (``Z<n>`` -> n - 1), so a subset of zones keeps each zone's
    rotation; another name falls back to its position in the sorted ``zones``."""
    m = re.fullmatch(r"Z(\d+)", zone)
    if m:
        return int(m.group(1)) - 1
    return sorted(zones).index(zone) if zone in zones else 0


def _default_status_of(runs_root: Path | None, tasks_root: Path | None,
                       t0_root: Path | None = None) -> Callable[[ChainJob], str | None]:
    def status_of(j: ChainJob) -> str | None:
        chain = load_arm_chain(j.zone, j.cond, tasks_root, t0_root)
        return chain_status(chain_statuses(
            chain_dir(j.agent, j.cond, j.zone, j.chain_idx, runs_root), chain.step_ids))
    return status_of


@dataclass
class ChainScheduler:
    """Chains in parallel (``workers``), steps in series inside ``run``.

    Infra rules as study 1: an ``infra`` step pauses every worker (backoff 60 s
    doubling to 30 min) and re-queues its chain, which resumes from that step;
    after ``max_infra_attempts`` on the same step it is marked ``infra_exhausted``
    (a later ``aa chain run`` retries it). ``run``/``sleep``/``status_of`` are
    injectable for tests.
    """
    jobs: list[ChainJob]
    run: Callable[[ChainJob], ChainResult]
    status_of: Callable[[ChainJob], str | None]
    workers: int = config.CONCURRENCY
    sleep: Callable[[float], None] = time.sleep
    max_infra_attempts: int | None = runner.MAX_INFRA_ATTEMPTS
    log: Callable[[str], None] = print
    # Checked before each dispatch; a message stops dispatching and marks the job and
    # every pending one ``auth_expired`` (no infra attempt is spent; rerun to resume).
    preflight: Callable[[ChainJob], str | None] | None = None

    def execute(self) -> dict[ChainJob, str]:
        done = ("ok", "setup_error")
        pending = [j for j in self.jobs if self.status_of(j) not in done]
        results: dict[ChainJob, str] = {j: self.status_of(j) for j in self.jobs
                                        if j not in pending}
        lock = threading.Lock()
        attempts: dict[tuple[ChainJob, str], int] = {}
        pause_until = [0.0]

        def worker() -> None:
            while True:
                with lock:
                    if not pending:
                        return
                    job = pending.pop(0)
                    problem = self.preflight(job) if self.preflight else None
                    if problem:
                        for j in [job, *pending]:
                            results[j] = "auth_expired"
                        pending.clear()
                        self.log(f"{job}: stopped dispatching: {problem}")
                        return
                    wait = pause_until[0] - time.monotonic()
                if wait > 0:
                    self.sleep(wait)
                try:
                    res = self.run(job)
                except Exception as e:  # noqa: BLE001 - a dead worker would stall the queue
                    with lock:
                        results[job] = "harness_error"
                        self.log(f"{job}: harness_error: {type(e).__name__}: {e}")
                    continue
                with lock:
                    if res.status == "infra":
                        key = (job, res.step_path.name if res.step_path else "")
                        n = attempts.get(key, 0)
                        attempts[key] = n + 1
                        if self.max_infra_attempts is not None and n + 1 >= self.max_infra_attempts:
                            results[job] = "infra_exhausted"
                            if res.step_path is not None:
                                runner._mark_exhausted(res.step_path)
                            self.log(f"{job}: infra_exhausted at {key[1]} after {n + 1} attempts")
                            continue
                        delay = runner.backoff_s(n)
                        pause_until[0] = max(pause_until[0], time.monotonic() + delay)
                        pending.append(job)
                        self.log(f"{job}: infra at {key[1]}, re-queued (backoff {delay}s)")
                    else:
                        results[job] = res.status
                        self.log(f"{job}: {res.status}")

        threads = [threading.Thread(target=worker, daemon=True)
                   for _ in range(max(1, self.workers))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return results


def parse_indices(spec: str) -> list[int]:
    """'8' -> 0..7; '0,3' -> [0, 3]; '2-5' -> [2, 3, 4, 5]; mixes allowed ('0,2-3')."""
    spec = spec.strip()
    if spec.isdigit():
        return list(range(int(spec)))
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out += range(int(a), int(b) + 1)
        elif part:
            out.append(int(part))
    return sorted(set(out))


def run_all_chains(agent: str, conds: Iterable[str], zones: Iterable[str],
                   chains: Iterable[int], workers: int = config.CONCURRENCY,
                   runs_root: Path | None = None, tasks_root: Path | None = None,
                   study: int | None = None, t0_root: Path | None = None
                   ) -> dict[ChainJob, str]:
    """Entry point for `aa chain run`. Study 2 (R/F): seeded shuffle per (chain, zone),
    runs2/. Study 3 (R/RG/RL/RC): rotated arm order (build_chain_queue3), runs3/."""
    conds = list(conds)
    study = study_of(conds, study)
    runs_root = runs_root or STUDY_RUNS[study]
    q = (build_chain_queue3 if study == 3 else build_chain_queue)(agent, conds, zones, chains)
    return ChainScheduler(
        q, workers=workers,
        run=lambda j: run_chain(j.agent, j.cond, j.zone, j.chain_idx, runs_root, tasks_root,
                                study=study, t0_root=t0_root),
        status_of=_default_status_of(runs_root, tasks_root, t0_root),
        preflight=_codex_preflight if config.engine(agent) == "codex" else None).execute()


# A T0 step lasts up to 40 min plus evaluation-free grace; keep a margin.
CODEX_MIN_HOURS_PER_JOB = 2.0


def _codex_preflight(job: ChainJob) -> str | None:
    return runner.codex_auth_problem(CODEX_MIN_HOURS_PER_JOB)
