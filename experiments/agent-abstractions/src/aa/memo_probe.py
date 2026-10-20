"""Memorisation probe (spec section 4, filter 3; plan Task 7).

Each model is asked, without the repository, for the diff that implements a
task. If its answer reproduces the reference change (token Jaccard over added
lines >= MEMORISED_THRESHOLD for either agent), the task is marked
``memorised`` in ``tasks/_ledger.json`` and must not be selected.

The probe consumes subscription quota only (Claude Code token / Codex ChatGPT
login); it never goes through an API gateway. Calls run in the repository-free
`aa-cli` image (build it with aa.runner.build_cli_image).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterable

from aa import config

MEMORISED_THRESHOLD = 0.5
WORKERS = 4
# Rate-limit / usage-limit failures are infra, never a probe result: back off
# 60 s -> 120 -> 240 -> ... (cap 30 min) and retry, like the runner (Task 8).
INFRA_BACKOFF_S = 60
INFRA_BACKOFF_CAP_S = 30 * 60
MAX_INFRA_RETRIES = 8
# An answer with no added diff lines (e.g. the agent refuses because it cannot
# see the repository) is not a probe result: re-ask, then leave it undecided.
MAX_NO_DIFF_RETRIES = 2
CALL_TIMEOUT_S = 600
MEMO_RAW = config.WORK / "memo"
CLAUDE_TOKEN_FILE = Path.home() / ".aa-claude-token"
# Study 1's memorisation probe covers the study-1 agents only (haiku joined in study 2).
MEMO_AGENTS = ("claude", "codex")
CODEX_AUTH_FILE = Path.home() / ".codex" / "auth.json"

PROMPT_TEMPLATE = (
    "This is a change in the open-source repository actualbudget/actual (packages/loot-core). "
    "Without access to the repository, write the unified diff you believe implements it.\n\n"
    "Statement:\n{statement}\n\n"
    "Files likely touched: {files}\n"
)

_TOKEN = re.compile(r"""[A-Za-z_]\w+|'[^']*'|"[^"]*\"""")
_FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)

# (agent, prompt, raw_path) -> model text; must also write the raw output to raw_path.
Caller = Callable[[str, str, Path], str]


# --------------------------------------------------------------------------- similarity

def _added_tokens(diff: str) -> set[str]:
    toks: set[str] = set()
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            toks.update(_TOKEN.findall(line[1:]))
    return toks


def similarity(predicted_diff: str, reference_diff: str) -> float:
    """Token Jaccard over added lines (identifiers and string literals only)."""
    pred, ref = _added_tokens(predicted_diff), _added_tokens(reference_diff)
    if not ref:
        return 0.0
    union = pred | ref
    return len(pred & ref) / len(union)


def extract_diff(text: str) -> str:
    """Concatenate fenced code blocks if the answer has any, else the whole text."""
    blocks = _FENCE.findall(text)
    return "".join(blocks) if blocks else text


def build_prompt(statement: str, touched_files: Iterable[str]) -> str:
    return PROMPT_TEMPLATE.format(statement=statement.strip(), files=", ".join(touched_files))


def estimate(n_tasks: int, workers: int = WORKERS) -> str:
    calls = n_tasks * len(MEMO_AGENTS)
    minutes = -(-calls // workers)  # ~1 min per call
    return (f"{n_tasks} tasks x {len(MEMO_AGENTS)} agents = {calls} calls, "
            f"~{minutes} min wall time at {workers} parallel (~1 min/call); "
            "subscription quota only, no API spend")


# --------------------------------------------------------------------------- task access

def _get(task: Any, name: str, default: Any = None) -> Any:
    """Read a field from a Task object (Task 6) or a plain dict."""
    if isinstance(task, dict):
        return task.get(name, default)
    return getattr(task, name, default)


def _task_dir(task: Any, tasks_dir: Path) -> Path:
    d = _get(task, "dir") or _get(task, "path")
    return Path(d) if d else tasks_dir / _get(task, "id")


def _is_test_file(path: str) -> bool:
    return ".test." in path or "__tests__/" in path


_DIFF_FILE = re.compile(r"^diff --git a/\S+ b/(\S+)", re.M)


def _filter_patch(patch: str, keep: Callable[[str], bool]) -> str:
    """The sections of a `git diff` patch whose b/ path satisfies ``keep``."""
    starts = [(m.start(), m.group(1)) for m in _DIFF_FILE.finditer(patch)]
    out = []
    for i, (pos, path) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(patch)
        if keep(path):
            out.append(patch[pos:end])
    return "".join(out)


def reference_diff(task: Any, repo: Path | None = None) -> str:
    """The reference change without test files. Mined tasks: the original commit's
    non-test changes, from the base clone. Issue tasks (no upstream commit): the
    task's ``reference.A.patch`` (plan Task 6b Step 8)."""
    hidden = set(_get(task, "hidden_tests", []) or [])
    if not _get(task, "sha"):
        patch = (_task_dir(task, config.TASKS) / "reference.A.patch").read_text()
        return _filter_patch(patch, lambda f: f not in hidden and not _is_test_file(f))
    repo = repo or config.WORK / "actual-base"
    files = [f for f in _get(task, "touched_files", []) if f not in hidden and not _is_test_file(f)]
    return subprocess.run(
        ["git", "-C", str(repo), "show", "--format=", _get(task, "sha"), "--", *files],
        check=True, capture_output=True, text=True,
    ).stdout


# --------------------------------------------------------------------------- agent calls

# Probe calls run inside the `aa-cli` image (Node + agent CLIs, built from the
# `cli` stage of substrate/docker/Dockerfile): no Actual checkout exists in it,
# so neither agent can read the repository (the host has work/actual-base).
PROBE_IMAGE = "aa-cli"
# No tools at all: the container has network (the CLIs need it), and with web
# search on, Codex looked the merged fix up on GitHub (memo run 1, 4556e9e244).
# Verified with a canary prompt that both CLIs then answer without any tool.
CODEX_NO_TOOLS = ("--strict-config -c web_search=disabled --disable shell_tool --disable browser_use "
                  "--disable computer_use --disable in_app_browser --disable apps "
                  "--disable image_generation")
_CODEX_TOOL_RE = re.compile(r"^(?:web search:|exec$|mcp:|tool )", re.M)


def codex_tool_use(transcript: str) -> bool:
    """True if a codex exec transcript shows a web search, shell command or tool call."""
    return _CODEX_TOOL_RE.search(transcript) is not None


def claude_tool_use(result: dict[str, Any]) -> bool:
    """True if a `claude -p --output-format json` result used any tool (more than one
    turn, or any server-side web search/fetch)."""
    stu = (result.get("usage") or {}).get("server_tool_use") or {}
    return (result.get("num_turns") or 1) > 1 or any(v for v in stu.values())


def probe_docker_argv(agent: str, out_dir: Path, auth_dir: Path | None = None) -> list[str]:
    """`docker run -i` argv for one probe call; the prompt is piped to stdin and the
    model's answer lands in /out. Empty workdir, isolated agent config."""
    argv = ["docker", "run", "--rm", "-i", "-v", f"{out_dir}:/out", "-w", "/tmp/empty"]
    model = config.MODELS[agent]
    if config.engine(agent) == "claude":
        argv += ["-e", "CLAUDE_CONFIG_DIR=/tmp/cc", "-e", "CLAUDE_CODE_OAUTH_TOKEN"]
        script = ('mkdir -p /tmp/cc /tmp/empty && cd /tmp/empty && P="$(cat)" && '
                  f'claude -p "$P" --model {model} --tools "" --output-format json < /dev/null '
                  "> /out/stdout.txt 2> /out/stderr.txt")
    elif config.engine(agent) == "codex":
        if auth_dir is None:
            raise ValueError("codex needs auth_dir")
        argv += ["-v", f"{auth_dir}:/codex-auth:ro", "-e", "CODEX_HOME=/tmp/codexhome"]
        script = ("mkdir -p /tmp/codexhome /tmp/empty && cp /codex-auth/auth.json /tmp/codexhome/ "
                  '&& cd /tmp/empty && P="$(cat)" && '
                  f'codex exec --model {model} --skip-git-repo-check {CODEX_NO_TOOLS} -o /out/last.txt "$P" '
                  "< /dev/null > /out/stdout.txt 2> /out/stderr.txt")
    else:
        raise ValueError(f"unknown agent {agent!r}")
    return argv + [PROBE_IMAGE, "bash", "-c", script]


def _run_probe_container(agent: str, prompt: str, tmp: Path,
                         env_extra: dict[str, str] | None = None) -> tuple[int, Path]:
    out = tmp / "out"
    out.mkdir()
    auth = None
    if config.engine(agent) == "codex":
        auth = tmp / "auth"
        auth.mkdir()
        shutil.copy2(CODEX_AUTH_FILE, auth / "auth.json")
    env = os.environ.copy() | (env_extra or {})
    proc = subprocess.run(probe_docker_argv(agent, out, auth), input=prompt, env=env,
                          capture_output=True, text=True, timeout=CALL_TIMEOUT_S)
    return proc.returncode, out


def _rel(p: Path) -> str:
    """Repo-relative path for memo.json (absolute if outside the repo)."""
    try:
        return str(Path(p).resolve().relative_to(config.ROOT))
    except ValueError:
        return str(p)


def _read(p: Path) -> str:
    return p.read_text(errors="replace") if p.exists() else ""


def call_claude(prompt: str, raw_path: Path) -> str:
    token = CLAUDE_TOKEN_FILE.read_text().strip()
    with tempfile.TemporaryDirectory(prefix="aa-memo-cc-") as tmp:
        rc, out = _run_probe_container("claude", prompt, Path(tmp),
                                       {"CLAUDE_CODE_OAUTH_TOKEN": token})
        stdout, stderr = _read(out / "stdout.txt"), _read(out / "stderr.txt")
    raw_path.write_text(stdout + (f"\n--- stderr ---\n{stderr}" if stderr else ""))
    if rc != 0:
        raise RuntimeError(f"claude exit {rc}: {stderr[-500:]}")
    data = json.loads(stdout)
    if data.get("is_error"):
        raise RuntimeError(f"claude error: {str(data.get('result'))[:500]}")
    if claude_tool_use(data):
        raise RuntimeError("probe invalid: claude used a tool (possible repository access)")
    return data.get("result", "")


def call_codex(prompt: str, raw_path: Path) -> str:
    with tempfile.TemporaryDirectory(prefix="aa-memo-codex-") as tmp:
        rc, out = _run_probe_container("codex", prompt, Path(tmp))
        text = _read(out / "last.txt")
        stdout, stderr = _read(out / "stdout.txt"), _read(out / "stderr.txt")
    raw_path.write_text(text + f"\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}")
    if rc != 0 or not text:
        raise RuntimeError(f"codex exit {rc}: {stderr[-500:]}")
    if codex_tool_use(stderr + "\n" + stdout):
        raise RuntimeError("probe invalid: codex used a tool (possible repository access)")
    return text


def default_call(agent: str, prompt: str, raw_path: Path) -> str:
    return {"claude": call_claude, "codex": call_codex}[agent](prompt, raw_path)


# --------------------------------------------------------------------------- runner

def missing_entries(tasks: list[Any], tasks_dir: Path = config.TASKS) -> set[tuple[str, str]]:
    """(task_id, agent) pairs with no probe result yet (no memo.json entry, or
    similarity None after a failed call / an answer without a diff)."""
    out = set()
    for t in tasks:
        p = _task_dir(t, tasks_dir) / "memo.json"
        memo = json.loads(p.read_text()) if p.exists() else {}
        for agent in MEMO_AGENTS:
            if (memo.get(agent) or {}).get("similarity") is None:
                out.add((_get(t, "id"), agent))
    return out


def mark_memorised(ledger_path: Path, verdicts: dict[str, bool]) -> None:
    """Set ``memorised`` on ledger entries (dict keyed by id, or list of {"id": ...})."""
    ledger: Any = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    if isinstance(ledger, list):
        by_id = {e.get("id"): e for e in ledger}
        for tid, v in verdicts.items():
            if tid not in by_id:
                by_id[tid] = {"id": tid}
                ledger.append(by_id[tid])
            by_id[tid]["memorised"] = v
    else:
        entries = ledger.get("tasks", ledger) if isinstance(ledger.get("tasks"), dict) else ledger
        for tid, v in verdicts.items():
            entries.setdefault(tid, {})["memorised"] = v
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")


def run_probe(
    tasks: list[Any],
    *,
    reference: Callable[[Any], str] = reference_diff,
    call: Caller = default_call,
    raw_dir: Path = MEMO_RAW,
    tasks_dir: Path = config.TASKS,
    workers: int = WORKERS,
    sleep: Callable[[float], None] = time.sleep,
    max_infra_retries: int = MAX_INFRA_RETRIES,
    only: set[tuple[str, str]] | None = None,
) -> dict[str, bool | None]:
    """Probe every task with both agents; write tasks/<id>/memo.json and update the ledger.

    Returns {task_id: True (memorised) | False (clean) | None (a call failed and
    no agent crossed the threshold: re-run before selecting)}.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    refs = {_get(t, "id"): reference(t) for t in tasks}
    jobs = []
    for t in tasks:
        statement = (_task_dir(t, tasks_dir) / "statement.md").read_text()
        prompt = build_prompt(statement, _get(t, "touched_files", []))
        for agent in MEMO_AGENTS:
            if only is not None and (_get(t, "id"), agent) not in only:
                continue
            jobs.append((t, agent, prompt, raw_dir / f"{_get(t, 'id')}.{agent}.txt"))

    def one(job: tuple[Any, str, str, Path]) -> tuple[str, str, dict[str, Any]]:
        from aa.agents import classify_infra
        t, agent, prompt, raw = job
        tid = _get(t, "id")
        retries = no_diff = 0
        while True:
            try:
                text = call(agent, prompt, raw)
            except Exception as e:  # noqa: BLE001 - recorded, decided below
                err = str(e)
                infra = classify_infra(err) or classify_infra(_read(raw)[-2000:])
                if not infra or retries >= max_infra_retries:
                    return tid, agent, {"similarity": None, "raw": _rel(raw), "error": err,
                                        "infra": infra, "infra_retries": retries}
                sleep(min(INFRA_BACKOFF_S * 2 ** retries, INFRA_BACKOFF_CAP_S))
                retries += 1
                continue
            diff = extract_diff(text)
            if _added_tokens(diff):
                break
            if no_diff >= MAX_NO_DIFF_RETRIES:
                return tid, agent, {"similarity": None, "raw": _rel(raw),
                                    "error": "no diff in answer", "no_diff_retries": no_diff,
                                    "infra_retries": retries}
            no_diff += 1
            if raw.exists():  # keep the refused answer for the record
                raw.rename(raw.with_name(f"{raw.stem}.nodiff{no_diff}.txt"))
        rec = {"similarity": similarity(diff, refs[tid]), "raw": _rel(raw), "infra_retries": retries}
        if no_diff:
            rec["no_diff_retries"] = no_diff
        return tid, agent, rec

    memos: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for tid, agent, rec in ex.map(one, jobs):
            memos.setdefault(tid, {})[agent] = rec

    verdicts: dict[str, bool | None] = {}
    for t in tasks:
        tid = _get(t, "id")
        memo_path = _task_dir(t, tasks_dir) / "memo.json"
        memo = json.loads(memo_path.read_text()) if only is not None and memo_path.exists() else {}
        memo.update(memos.get(tid, {}))
        if not memo:
            continue
        memo_path.write_text(json.dumps(memo, indent=2) + "\n")
        sims = [(memo.get(a) or {}).get("similarity") for a in MEMO_AGENTS]
        if any(s is not None and s >= MEMORISED_THRESHOLD for s in sims):
            verdicts[tid] = True
        elif any(s is None for s in sims):
            verdicts[tid] = None
        else:
            verdicts[tid] = False

    decided = {k: v for k, v in verdicts.items() if v is not None}
    if decided:
        mark_memorised(tasks_dir / "_ledger.json", decided)
    return verdicts
