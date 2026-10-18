"""Run one agent on one task inside a per-condition Docker image, and schedule many.

Layout of a run dir: runs/<agent>/<cond>/<task>/<pass>/ with
  transcript.jsonl  raw agent stdout (stream-json / codex --json)
  stderr.log        agent stderr
  setup_ok          written by the container once the start tree is ready
  diff.patch        `git diff --cached HEAD` after the agent stopped
  agent.json        {status, usage, wall_s, started_at, image_digest, cli_version, ...}

Statuses: ok / timeout (final, evaluated), setup_error (the task's revert patch
did not apply in the container: final, never retried), infra (quota, crash:
re-queued with backoff), infra_exhausted (infra MAX_INFRA_ATTEMPTS times in one
`aa run`; a later `aa run` retries it), harness_error (bug on the host side,
e.g. a missing task file; retried on the next `aa run`).

Leak prevention: the container receives the revert patch on stdin (never on
disk) and only `prompt.txt` is mounted. After applying the patch the variant's
git history (base + variant commits, which contain the A+/lint patches) is
deleted and the start tree is committed into a fresh repository.
"""
from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from aa import config
from aa.agents import (BLOCKED_HOSTS, Outcome, Usage, detect_contamination, parse_stream,
                       task_refs, transport_stalled)

DOCKERFILE = config.ROOT / "substrate" / "docker" / "Dockerfile"
INSTALL_SCRIPT = config.ROOT / "substrate" / "docker" / "install-lint-deps.sh"
PROMPT_TEMPLATE = Path(__file__).with_name("prompt.md")
CLAUDE_TOKEN_FILE = Path.home() / ".aa-claude-token"
CODEX_AUTH = Path.home() / ".codex" / "auth.json"
CODEX_LOGIN_CMD = "codex logout; codex login  (nvm: ~/.nvm/versions/node/v22.14.0/bin/codex)"


def codex_auth_hours_left(path: Path | None = None, now: float | None = None) -> float | None:
    """Hours until the access token in the host's Codex auth.json expires (JWT ``exp``);
    None when the file is missing or unreadable. Containers get a copy of this file and
    their token refreshes are never written back, so a token that expires mid-run makes
    parallel containers race on the single-use refresh token (all then fail with 401)."""
    import base64
    try:
        tok = json.loads((path or CODEX_AUTH).read_text())["tokens"]["access_token"]
        payload = tok.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload))["exp"]
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return None
    return (exp - (time.time() if now is None else now)) / 3600


def codex_auth_problem(min_hours: float, path: Path | None = None) -> str | None:
    """None if the Codex login lasts at least ``min_hours``; else a message saying how to log in."""
    left = codex_auth_hours_left(path)
    if left is None:
        return f"codex auth.json missing or unreadable; run: {CODEX_LOGIN_CMD}"
    if left < min_hours:
        return (f"codex access token expires in {left:.1f} h (< {min_hours:g} h); "
                f"run: {CODEX_LOGIN_CMD}")
    return None


CLI_VERSIONS = {"claude": "2.1.289", "haiku": "2.1.289", "codex": "0.159.3"}
CPUS = "2"
MEMORY = "6g"
SCHEDULE_SEED = 20261005
BACKOFF_START_S = 60
BACKOFF_CAP_S = 30 * 60
TERMINAL = ("ok", "timeout", "setup_error")
MAX_INFRA_ATTEMPTS = 8
CLI_IMAGE = "aa-cli"
SETUP_EXIT = 3  # container exit code when the start tree cannot be prepared


def image_tag(cond: str) -> str:
    return f"aa-actual:{cond}"


# --------------------------------------------------------------------------- image

def image_target(cond: str) -> str:
    """Dockerfile stage for a condition. Named explicitly for study 1 too: the file's
    last stage is now `study2`, and an untargeted build would pick it. Study-3 arms
    build `study2` like R (RL's lint runs jscpd; the arms differ only by patch)."""
    return "study2" if cond in config.CONDITIONS2 + config.CONDITIONS3 else "actual"


def build_image(cond: str, variant: Path | None = None,
                no_cache_stages: tuple[str, ...] = ()) -> str:
    """docker build aa-actual:<cond> from work/variants/<cond> (copied as `variant/`).

    Study-1 conditions build the Dockerfile's `actual` stage, study-2 ones (R/F) its
    `study2` stage (the same image plus pinned jscpd); see image_target.
    ``no_cache_stages`` are rebuilt without the build cache (``--no-cache-filter``):
    study 3 rebuilds its arms' install stages together on one cached ``cli`` stage
    (aa.images3)."""
    if cond not in config.ALL_CONDITIONS:
        raise ValueError(f"unknown condition {cond!r}")
    variant = variant or config.WORK / "variants" / cond
    if not (variant / ".git").exists():
        raise FileNotFoundError(f"{variant} is not a built variant; run `aa variant build {cond}`")
    config.WORK.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=config.WORK, prefix=f"imgctx-{cond}-") as ctx:
        shutil.copytree(variant, Path(ctx) / "variant", symlinks=True,
                        ignore=shutil.ignore_patterns("node_modules"))
        # The context holds exactly the patched tree: local installs (the shared
        # eslint devDependencies step edits package.json/yarn.lock) are reset on
        # the copy; the image runs that same step itself.
        for args in (("reset", "-q", "--hard", "HEAD"), ("clean", "-qfd")):
            subprocess.run(["git", *args], cwd=Path(ctx) / "variant", check=True)
        shutil.copy(DOCKERFILE, Path(ctx) / "Dockerfile")
        shutil.copy(INSTALL_SCRIPT, Path(ctx) / "install-lint-deps.sh")
        nocache = [a for st in no_cache_stages for a in ("--no-cache-filter", st)]
        subprocess.run(["docker", "build", "--build-arg", f"COND={cond}", *nocache,
                        "--target", image_target(cond), "-t", image_tag(cond), ctx],
                       check=True)
    return image_tag(cond)


def build_cli_image() -> str:
    """docker build the `cli` stage only (Node + agent CLIs, no repository) as aa-cli.

    Used by the memorisation probe, which must not see any Actual tree.
    """
    config.WORK.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=config.WORK, prefix="imgctx-cli-") as ctx:
        shutil.copy(DOCKERFILE, Path(ctx) / "Dockerfile")
        subprocess.run(["docker", "build", "--target", "cli", "-t", CLI_IMAGE, ctx], check=True)
    return CLI_IMAGE


def image_digest(tag: str) -> str | None:
    r = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", tag],
                       capture_output=True, text=True)
    return r.stdout.strip() or None


# --------------------------------------------------------------------------- prompt

def render_prompt(statement: str) -> str:
    return PROMPT_TEMPLATE.read_text().replace("<statement.md contents>", statement.strip())


# --------------------------------------------------------------------------- commands

# No web for agents in real runs (review 4): the container has network (the CLIs
# need their APIs) and the upstream fix is public. Claude: the web tools are
# disallowed and no MCP server is loaded (`claude --help`, 2.1.289: --disallowedTools,
# --strict-mcp-config without --mcp-config). Codex: web search off AND the `apps`
# feature off -- with only web_search=disabled, codex 0.159.3 still searched the web
# through its codex_apps MCP connector (search_service.web_run; verification run
# 2026-10-06) -- plus the browser/computer features (the memo probe's switches, shell
# kept); --strict-config is safe because CODEX_HOME holds only auth.json.
CLAUDE_NO_WEB = "--disallowedTools WebSearch,WebFetch --strict-mcp-config"
CODEX_NO_WEB = ("--strict-config -c web_search=disabled --disable apps --disable browser_use "
                "--disable browser_use_external --disable computer_use --disable in_app_browser "
                "--disable image_generation")


def agent_command(agent: str, turn_limit: int = config.TURN_LIMIT) -> str:
    """Shell command that runs the agent inside the container, stdout -> /out/transcript.jsonl.

    ``turn_limit`` is Claude Code's ``--max-turns`` (study 3's T0 uses 90); Codex has
    no turn flag, its turns are checked after the run (:func:`classify_status`)."""
    model = config.MODELS[agent]
    if config.engine(agent) == "claude":
        return (f'claude -p "$(cat /task/prompt.txt)" --model {model} '
                f"--output-format stream-json --verbose --permission-mode bypassPermissions "
                f"--effort {config.EFFORT} "
                f"{CLAUDE_NO_WEB} --max-turns {turn_limit} < /dev/null "
                f"> /out/transcript.jsonl 2> /out/stderr.log")
    if config.engine(agent) == "codex":
        return (f"codex exec --model {model} --json --dangerously-bypass-approvals-and-sandbox "
                f"-c model_reasoning_effort={config.EFFORT} {CODEX_NO_WEB} "
                f'--skip-git-repo-check "$(cat /task/prompt.txt)" < /dev/null '
                f"> /out/transcript.jsonl 2> /out/stderr.log")
    raise ValueError(f"unknown agent {agent!r}")


def container_script(agent: str, wall_limit_s: int = config.WALL_LIMIT_S) -> str:
    """Build the start tree from the revert patch on stdin, run the agent under
    `timeout`, always dump the diff.

    - The revert patch arrives on stdin (`docker run -i`); nothing on disk holds it.
    - The image's .git (variant history: base + A+/lint patches) is replaced by a
      fresh repository whose only commit is the start tree.
    - /out/setup_ok marks a ready start tree; on failure the script exits
      SETUP_EXIT and the runner records `setup_error` (final, not retried).
    - The agent's exit code goes to /out/exit_code (124 = wall-clock timeout).
    """
    auth = ""
    if config.engine(agent) == "claude":
        auth = "mkdir -p /tmp/cc"
    elif config.engine(agent) == "codex":
        # CODEX_HOME must be writable (sessions/logs); seed it with auth.json only.
        auth = "mkdir -p /tmp/codexhome && cp /codex-auth/auth.json /tmp/codexhome/auth.json"
    else:
        raise ValueError(f"unknown agent {agent!r}")
    return "\n".join([
        "set -u",
        f"cd /work/actual || exit {SETUP_EXIT}",
        f"git apply --allow-empty --whitespace=nowarn - || {{ echo 'aa: revert patch does not apply' >&2; exit {SETUP_EXIT}; }}",
        "rm -rf .git && git init -q -b main && git add -A && git commit -qm start "
        f"|| {{ echo 'aa: start commit failed' >&2; exit {SETUP_EXIT}; }}",
        "touch /out/setup_ok",
        auth,
        f"timeout {wall_limit_s} bash -c '{_sq(agent_command(agent))}' < /dev/null",
        "echo $? > /out/exit_code",
        "git add -A && git diff --cached HEAD > /out/diff.patch",
    ])


def _sq(s: str) -> str:
    """Escape for embedding inside a single-quoted bash string."""
    return s.replace("'", "'\"'\"'")


def blocked_host_args() -> list[str]:
    """``--add-host <host>:0.0.0.0`` for every upstream source/package host: the
    container keeps network for the model APIs (api.anthropic.com, chatgpt.com /
    api.openai.com are untouched), but GitHub and the npm registries/CDNs resolve to
    an unroutable address, so curl/wget/git/npm towards them fail fast."""
    out: list[str] = []
    for h in BLOCKED_HOSTS:
        out += ["--add-host", f"{h}:0.0.0.0"]
    return out


def docker_argv(agent: str, cond: str, task_id: str, pass_idx: int, prompt_file: Path,
                out_dir: Path, codex_auth_dir: Path | None = None,
                wall_limit_s: int = config.WALL_LIMIT_S) -> list[str]:
    """`docker run -i` argv; the caller pipes the revert patch to stdin.

    Only the prompt file is mounted (read-only) besides /out and Codex auth; the
    upstream hosts are blackholed (``blocked_host_args``).
    """
    name = f"aa-{agent}-{cond}-{task_id}-{pass_idx}"
    argv = ["docker", "run", "--rm", "-i", "--name", name, "--cpus", CPUS, "--memory", MEMORY,
            "-v", f"{prompt_file}:/task/prompt.txt:ro", "-v", f"{out_dir}:/out"]
    argv += blocked_host_args()
    if config.engine(agent) == "claude":
        # Credentials only: empty config dir, token through the environment
        # (value inherited from the host process env, never on the argv).
        argv += ["-e", "CLAUDE_CONFIG_DIR=/tmp/cc", "-e", "CLAUDE_CODE_OAUTH_TOKEN"]
    elif config.engine(agent) == "codex":
        if codex_auth_dir is None:
            raise ValueError("codex needs codex_auth_dir")
        argv += ["-v", f"{codex_auth_dir}:/codex-auth:ro", "-e", "CODEX_HOME=/tmp/codexhome"]
    argv += [image_tag(cond), "bash", "-lc", container_script(agent, wall_limit_s)]
    return argv


# --------------------------------------------------------------------------- one run

def run_dir(agent: str, cond: str, task_id: str, pass_idx: int) -> Path:
    return config.RUNS / agent / cond / task_id / str(pass_idx)


def no_agent_activity(usage: Usage) -> bool:
    """No turn, no tool call and no token reported (missing tokens count as none)."""
    return not usage.turns and not usage.tool_calls and not usage.input_tokens \
        and not usage.output_tokens


def classify_status(outcome: Outcome, exit_code: int | None, usage: Usage,
                    turn_limit: int = config.TURN_LIMIT, stalled: bool = False) -> str:
    """Final run status from the parsed stream plus the agent's exit code.

    ``stalled`` (:func:`aa.agents.transport_stalled`: the transcript ends in transport
    errors with no agent progress after them) is ``infra`` whatever the exit code, and
    so is a wall-clock kill with no agent activity at all (study-3 pilot, blocking
    item 1: a network outage is re-run, never carried as an agent timeout). Codex
    reports tokens only at ``turn.completed``, so missing usage alone is not "no
    activity" (a Codex step killed while it worked has tool calls and turns)."""
    if stalled:
        return "infra"
    # A wall-clock kill truncates the stream (the parser then says infra), so
    # exit 124 takes precedence over the parsed outcome.
    if exit_code == 124:
        return "infra" if no_agent_activity(usage) else "timeout"
    if outcome == "infra":
        return "infra"
    if outcome == "timeout" or usage.turns >= turn_limit:
        return "timeout"
    if exit_code is None:
        return "infra"  # container died before the agent finished
    if exit_code != 0 and usage.turns == 0:
        return "infra"  # agent crashed before doing anything (auth, CLI error)
    return "ok"


def classify_setup(setup_ok: bool, docker_rc: int | None) -> str | None:
    """`setup_error` when the container ran but could not build the start tree;
    `infra` when the container never got that far for host reasons (docker run
    error 125-127, host timeout); None when setup succeeded."""
    if setup_ok:
        return None
    if docker_rc is None or docker_rc in (125, 126, 127):
        return "infra"
    return "setup_error"


def task_meta(task_id: str, tasks_root: Path | None = None) -> dict:
    return json.loads(((tasks_root or config.TASKS) / task_id / "task.json").read_text())


def task_inputs(task_id: str, cond: str, tasks_root: Path | None = None) -> tuple[str, bytes]:
    """(prompt text, revert patch bytes) for one task and condition, from task.json."""
    src = (tasks_root or config.TASKS) / task_id
    meta = task_meta(task_id, tasks_root)
    patch_name = meta["per_condition"][cond]["revert_patch"]
    statement = src / (meta.get("statement_path") or "statement.md")
    return render_prompt(statement.read_text()), (src / patch_name).read_bytes()


def _write_agent_json(out: Path, record: dict) -> None:
    (out / "agent.json").write_text(json.dumps(record, indent=2) + "\n")


def run_one(agent: str, cond: str, task_id: str, pass_idx: int,
            wall_limit_s: int = config.WALL_LIMIT_S, tasks_root: Path | None = None) -> Path:
    """Run the agent once; returns the run dir (always contains agent.json)."""
    out = run_dir(agent, cond, task_id, pass_idx)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    base = {"agent": agent, "cond": cond, "task": task_id, "pass": pass_idx,
            "model": config.MODELS.get(agent), "cli_version": CLI_VERSIONS.get(agent)}
    try:
        return _run_one(agent, cond, task_id, pass_idx, wall_limit_s, tasks_root, out, base)
    except Exception as e:  # noqa: BLE001 - recorded so the run is never silently lost
        _write_agent_json(out, base | {"status": "harness_error",
                                       "error": f"{type(e).__name__}: {e}"})
        return out


def _run_one(agent: str, cond: str, task_id: str, pass_idx: int, wall_limit_s: int,
             tasks_root: Path | None, out: Path, base: dict) -> Path:
    prompt, patch = task_inputs(task_id, cond, tasks_root)
    env = os.environ.copy()
    with tempfile.TemporaryDirectory(prefix="aa-task-") as tmp:
        tmp = Path(tmp)
        prompt_file = tmp / "prompt.txt"
        prompt_file.write_text(prompt)
        auth_dir = None
        if config.engine(agent) == "claude":
            env["CLAUDE_CODE_OAUTH_TOKEN"] = CLAUDE_TOKEN_FILE.read_text().strip()
        elif config.engine(agent) == "codex":
            auth_dir = tmp / "codex-auth"
            auth_dir.mkdir()
            shutil.copy(CODEX_AUTH, auth_dir / "auth.json")
        argv = docker_argv(agent, cond, task_id, pass_idx, prompt_file, out, auth_dir, wall_limit_s)
        started = datetime.now(timezone.utc)
        t0 = time.monotonic()
        # Grace on top of the in-container `timeout` for setup and diff dump.
        try:
            proc = subprocess.run(argv, env=env, input=patch, capture_output=True,
                                  timeout=wall_limit_s + 300)
            docker_rc = proc.returncode
            docker_err = proc.stderr.decode("utf-8", "replace")[-4000:]
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "rm", "-f", argv[argv.index("--name") + 1]],
                           capture_output=True)
            docker_rc, docker_err = None, "host timeout"
        wall_s = round(time.monotonic() - t0, 1)
    exit_file = out / "exit_code"
    exit_code = int(exit_file.read_text().strip()) if exit_file.exists() else None
    transcript = out / "transcript.jsonl"
    lines = transcript.read_text(errors="replace").splitlines() if transcript.exists() else []
    usage, outcome = parse_stream(agent, lines)
    status = classify_setup((out / "setup_ok").exists(), docker_rc) \
        or classify_status(outcome, exit_code, usage, stalled=transport_stalled(agent, lines))
    hits = detect_contamination(agent, lines, task_refs(task_meta(task_id, tasks_root)))
    _write_agent_json(out, base | {
        "status": status, "outcome": outcome, "exit_code": exit_code,
        "docker_rc": docker_rc,
        "docker_stderr": docker_err if status in ("infra", "setup_error") else "",
        "usage": asdict(usage), "wall_s": wall_s, "started_at": started.isoformat(),
        "image_digest": image_digest(image_tag(cond)),
        "contamination_flag": bool(hits), "contamination_hits": hits,
    })
    return out


def read_status(path: Path) -> str | None:
    f = path / "agent.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text()).get("status")
    except (OSError, json.JSONDecodeError):
        return None


# --------------------------------------------------------------------------- scheduler

@dataclass(frozen=True)
class Job:
    agent: str
    cond: str
    task: str
    pass_idx: int


def build_queue(agent: str, conds: Iterable[str], tasks: Iterable[str], passes: int,
                seed: int = SCHEDULE_SEED) -> list[Job]:
    """for pass, for task, conditions shuffled with a fixed seed (quota drift hits all
    conditions equally)."""
    conds, tasks = list(conds), list(tasks)
    rng = random.Random(seed)
    q: list[Job] = []
    for p in range(passes):
        for t in tasks:
            order = conds[:]
            rng.shuffle(order)
            q += [Job(agent, c, t, p) for c in order]
    return q


def backoff_s(attempt: int) -> int:
    """60 s, 120, 240, ... capped at 30 min. attempt starts at 0."""
    return min(BACKOFF_START_S * (2 ** attempt), BACKOFF_CAP_S)


@dataclass
class Scheduler:
    """Runs a queue with N workers; skips finished runs; re-queues `infra` with backoff.

    `run` and `sleep` are injectable for tests.
    """
    jobs: list[Job]
    workers: int = config.CONCURRENCY
    run: Callable[[Job], Path] = field(
        default=lambda j: run_one(j.agent, j.cond, j.task, j.pass_idx))
    sleep: Callable[[float], None] = time.sleep
    status_of: Callable[[Job], str | None] = field(
        default=lambda j: read_status(run_dir(j.agent, j.cond, j.task, j.pass_idx)))
    max_infra_attempts: int | None = MAX_INFRA_ATTEMPTS
    log: Callable[[str], None] = print

    def execute(self) -> dict[Job, str]:
        pending = [j for j in self.jobs if self.status_of(j) not in TERMINAL]
        results: dict[Job, str] = {j: self.status_of(j) for j in self.jobs if j not in pending}
        lock = threading.Lock()
        attempts: dict[Job, int] = {}
        # A global pause: when any run hits infra (quota), all workers wait.
        pause_until = [0.0]

        def worker() -> None:
            while True:
                with lock:
                    if not pending:
                        return
                    job = pending.pop(0)
                    wait = pause_until[0] - time.monotonic()
                if wait > 0:
                    self.sleep(wait)
                try:
                    path = self.run(job)
                except Exception as e:  # noqa: BLE001 - a dead worker would stall the queue
                    with lock:
                        results[job] = "harness_error"
                        self.log(f"{job}: harness_error: {type(e).__name__}: {e}")
                    continue
                status = read_status(path) if isinstance(path, Path) else None
                status = status or "infra"
                with lock:
                    if status == "infra":
                        n = attempts.get(job, 0)
                        attempts[job] = n + 1
                        if self.max_infra_attempts is not None and n + 1 >= self.max_infra_attempts:
                            results[job] = "infra_exhausted"
                            if isinstance(path, Path):
                                _mark_exhausted(path)
                            self.log(f"{job}: infra_exhausted after {n + 1} attempts")
                            continue
                        delay = backoff_s(n)
                        pause_until[0] = max(pause_until[0], time.monotonic() + delay)
                        pending.append(job)
                        self.log(f"{job}: infra, re-queued (backoff {delay}s)")
                    else:
                        results[job] = status
                        self.log(f"{job}: {status}")

        threads = [threading.Thread(target=worker, daemon=True) for _ in range(max(1, self.workers))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return results


def _mark_exhausted(path: Path) -> None:
    f = path / "agent.json"
    try:
        rec = json.loads(f.read_text())
    except (OSError, json.JSONDecodeError):
        return
    rec["status"] = "infra_exhausted"
    f.write_text(json.dumps(rec, indent=2) + "\n")


def run_all(agent: str, conds: Iterable[str], tasks: Iterable[str] | str, passes: int,
            workers: int = config.CONCURRENCY) -> dict[Job, str]:
    """Entry point for `aa run`. tasks='all' -> the selected tasks only."""
    if tasks == "all":
        from aa.tasks import load_tasks
        tasks = [t.id for t in load_tasks(selected_only=True)]
    q = build_queue(agent, conds, tasks, passes)
    return Scheduler(q, workers=workers).execute()
