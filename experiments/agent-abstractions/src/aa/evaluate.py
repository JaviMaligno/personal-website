"""Evaluator (plan Task 9): turn one run dir into ``result.json``.

In a fresh container of the run's condition image (network off):

1. apply the task's ``revert.<cond>.patch`` (from ``task.json``) -> start tree;
2. apply the agent's ``diff.patch`` (failure -> ``eval_error="diff_apply"``);
3. restore the hidden test files from the image's HEAD (the untouched variant), so
   an agent that edited or deleted them changes nothing (Review Focus #2), then
   overwrite them with the task's base copies (``tasks/<id>/hidden/``) rewritten
   for the condition by ``aa.hidden_tests`` (identity on A/AL, the A+ import
   rewrite on AP/APL), staged on the host under ``eval/hidden_src/``;
4. ``yarn lint`` (-> ``lint_ok``) and ``yarn tsgo -b`` (-> ``typecheck_ok``), *before*
   the probe files are copied in, so they never affect lint or typecheck;
5. copy the fast-check seed setup + its wrapper config (``aa.suite``, freeze gate
   2026-10-06), also after lint and typecheck; both passes below are seeded the same;
   pass 1 (clean): vitest on the hidden tests only, repo config + seed, default
   timeouts, no probe -> ``report.json``; this alone decides ``correct``;
6. pass 2 (probe): copy the probe + wrapper config, vitest on the hidden tests again
   with testTimeout/hookTimeout raised x10 (``aa.checker.vitest_probe_cmd``) ->
   ``probe.jsonl`` (+ ``probe_report.json``), used only to collect violations.

Two-pass rule (spec section 6): the probe slows write-heavy property tests past
vitest's timeouts (freeze gate 2026-10-05), so it must never decide correctness. If
pass 2 errors, times out or does not finish, ``probe_incomplete=true`` and the
violations seen so far are still kept; static checks are unaffected.

On the host: ``check_diff`` + ``probe_violations`` (only agent-added lines count for
``raw_write``), ``lint_visible`` per condition, trace and token stats from the
transcript. Whatever breaks (diff does not apply, tree does not compile, container
dies), a ``result.json`` is still written with ``correct=false`` (Review Focus #2).

Statuses: ``ok`` and ``timeout`` runs are evaluated (a timeout's diff may be partial;
analysis counts it as a failure via ``status``). ``setup_error`` and
``infra_exhausted`` are final and passed through without evaluation. Plain
``infra`` is not final (the scheduler retries it) and gets no ``result.json``.
"""
from __future__ import annotations

import json
import posixpath
import re
import shlex
import shutil
import subprocess
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from aa import config
from aa.checker import (CONFIG_DST, CONFIG_SRC, PROBE_DST, PROBE_SRC, SEED_CONFIG_DST,
                        SEED_CONFIG_SRC, SEED_DST, SEED_SRC, vitest_clean_cmd, vitest_probe_cmd)
from aa.agents import task_refs
from aa.hidden_tests import rewrite_for_condition
from aa.static_check import Violation, check_diff, probe_violations, read_probe_events
from aa.suite import parse_vitest_json

EVALUATED = ("ok", "timeout")
FINAL_UNEVALUATED = ("setup_error", "infra_exhausted")
EVAL_DIR = "eval"
CONTAINER_LOOT = f"/work/actual/{config.LOOT}"
STEP_TIMEOUT_S = 900
HOST_TIMEOUT_S = 5 * STEP_TIMEOUT_S  # lint, typecheck, clean vitest, probe vitest + slack
PROBE_REPORT = "probe_report.json"
CLEAN_DONE = "clean_done"  # written after pass 1: correctness is known even if pass 2 dies
# Test infrastructure the hidden tests depend on (relative to the Actual checkout).
# Restored from the image HEAD before both vitest passes (review 4), so an agent
# that edited the vitest configs or the shared mocks cannot change how the hidden
# tests run; `agent_touched_test_infra` records whether its diff touched them.
# Besides the fixed paths, every ``__mocks__`` directory under loot-core (vitest's
# automatic module mocks) is test infra: those in HEAD are restored, those the agent
# created are deleted.
TEST_INFRA_FILES = (f"{config.LOOT}/vitest.config.ts", f"{config.LOOT}/vitest.web.config.ts")
TEST_INFRA_DIRS = (f"{config.LOOT}/src/mocks", f"{config.LOOT}/src/server/tests")
MOCKS_DIR = "__mocks__"
HIDDEN_SRC = "hidden_src"  # under the eval dir (mounted at /out): staged hidden tests
TASK_HIDDEN = "hidden"  # under tasks/<id>/: hidden tests as they are at base
# Kinds that mean "re-implemented something an existing helper already does"
# (plan Task 9: sendMessages / *100 rounding / raw SQL write). Reported separately,
# not part of bad_decision.
REIMPLEMENTATION_KINDS = frozenset({"send_messages_outside_db", "float_money_math", "raw_write"})

Executor = Callable[[list[str], int], int]


# --------------------------------------------------------------------------- container

def eval_script(revert_patch: str | None, hidden_tests: list[str], *,
                static_checks: bool = True, new_hidden: Iterable[str] = ()) -> str:
    """Bash run inside the eval container. Mounts: /task (ro, tasks/<id>), /agentrun
    (ro, the run dir), /checker (ro, substrate/checker), /out (rw).

    ``revert_patch=None`` skips the revert (the untouched variant = the reference
    solution, used by the task sanity check); ``static_checks=False`` skips lint
    and typecheck. ``new_hidden``: hidden tests that do not exist in the image (issue
    tasks, ``aa.issue_tasks``): whatever the agent left at that path is deleted and
    the staged copy is required instead of the HEAD restore. An empty revert patch
    applies as a no-op (``--allow-empty``)."""
    q = shlex.quote
    new = [t for t in hidden_tests if t in set(new_hidden)]
    rel_hidden = [t[len(config.LOOT) + 1:] if t.startswith(config.LOOT + "/") else t
                  for t in hidden_tests]
    clean = " ".join(q(a) for a in vitest_clean_cmd("/out/report.json", rel_hidden))
    probed = " ".join(q(a) for a in vitest_probe_cmd(f"/out/{PROBE_REPORT}", rel_hidden))
    restore = " ".join(q(t) for t in hidden_tests if t not in new)
    every = " ".join(q(t) for t in hidden_tests)
    lines = ["set -u", "cd /work/actual"]
    if revert_patch is not None:
        lines.append(f"git apply --allow-empty --whitespace=nowarn /task/{q(revert_patch)} "
                     "2> /out/apply.log "
                     "|| { echo revert > /out/eval_error; exit 0; }")
    lines.append(
        "if [ -s /agentrun/diff.patch ]; then "
        "git apply --whitespace=nowarn /agentrun/diff.patch 2>> /out/apply.log "
        "|| { echo diff_apply > /out/eval_error; exit 0; }; fi")
    if restore:
        # hidden tests always come from the untouched variant (image HEAD) ...
        lines.append(f"git checkout HEAD -- {restore} 2>> /out/apply.log "
                     "|| { echo hidden_restore > /out/eval_error; exit 0; }")
    for t in new:
        # ... or, for a new hidden test, nothing the agent wrote there survives
        lines.append(f"rm -f {q(t)} && mkdir -p {q(posixpath.dirname(t))} "
                     f"&& [ -f /out/{HIDDEN_SRC}/{q(t)} ] "
                     "|| { echo hidden_restore > /out/eval_error; exit 0; }")
    lines += [
        # ... overwritten by the task's base copy rewritten for this condition, if staged
        f"for t in {every}; do if [ -f /out/{HIDDEN_SRC}/\"$t\" ]; then "
        f"cp /out/{HIDDEN_SRC}/\"$t\" \"$t\" 2>> /out/apply.log "
        "|| { echo hidden_restore > /out/eval_error; exit 0; }; fi; done",
        f"cd {config.LOOT}",
    ]
    if static_checks:
        lines += [
            f"timeout {STEP_TIMEOUT_S} yarn lint > /out/lint.log 2>&1; echo $? > /out/lint_rc",
            f"timeout {STEP_TIMEOUT_S} yarn tsgo -b > /out/typecheck.log 2>&1; "
            "echo $? > /out/typecheck_rc",
        ]
    infra = " ".join(q(p) for p in TEST_INFRA_FILES + TEST_INFRA_DIRS)
    loot = q(config.LOOT)
    return "\n".join(lines + [
        # test infra (vitest configs, mocks, server test helpers) back to the image
        # HEAD for both passes, after lint/typecheck (those judge the agent's tree as
        # it left it) (paths absent from HEAD are skipped: only test fixtures lack them)
        f"( cd /work/actual && for p in {infra}; do "
        'if git cat-file -e HEAD:"$p" 2>/dev/null; then '
        'rm -rf "$p" && git checkout HEAD -- "$p" || exit 1; fi; done ) 2>> /out/apply.log '
        "|| { echo test_infra_restore > /out/eval_error; exit 0; }",
        # every __mocks__ dir under loot-core (in HEAD or created by the agent):
        # removed, then restored from HEAD when it exists there
        f"( cd /work/actual && {{ git ls-tree -r --name-only HEAD -- {loot} "
        f"| sed -n 's#^\\(.*/{MOCKS_DIR}\\)/.*#\\1#p'; "
        f"find {loot} -name node_modules -prune -o -type d -name {MOCKS_DIR} -print; }} "
        '| sort -u | while IFS= read -r p; do rm -rf "$p" || exit 1; '
        'if git cat-file -e HEAD:"$p" 2>/dev/null; then git checkout HEAD -- "$p" || exit 1; fi; '
        "done ) 2>> /out/apply.log "
        "|| { echo test_infra_restore > /out/eval_error; exit 0; }",
        # fast-check seed for both passes (after lint/typecheck, like the probe)
        f"cp /checker/{SEED_SRC.name} {SEED_DST} && "
        f"cp /checker/{SEED_CONFIG_SRC.name} {SEED_CONFIG_DST} "
        "|| { echo seed_install > /out/eval_error; exit 0; }",
        # pass 1, clean (seeded): decides correctness
        f"ENV=node timeout {STEP_TIMEOUT_S} {clean} > /out/vitest.log 2>&1; "
        "echo $? > /out/vitest_rc",
        f"echo done > /out/{CLEAN_DONE}",
        # pass 2, probe + raised vitest timeouts: violations only
        f"cp /checker/{PROBE_SRC.name} {PROBE_DST} && cp /checker/{CONFIG_SRC.name} {CONFIG_DST}",
        f"ENV=node AA_PROBE_OUT=/out/probe.jsonl timeout {STEP_TIMEOUT_S} {probed} "
        "> /out/vitest_probe.log 2>&1; echo $? > /out/vitest_probe_rc",
        "echo done > /out/eval_done",
    ]) + "\n"


def eval_docker_argv(cond: str, run_dir: Path, task_dir: Path, out_dir: Path,
                     script: str, checker_dir: Path = PROBE_SRC.parent) -> list[str]:
    name = "aa-eval-" + "-".join(run_dir.parts[-4:])
    return ["docker", "run", "--rm", "--name", re.sub(r"[^\w.-]", "_", name),
            "--network", "none", "--cpus", "2", "--memory", "6g",
            "-v", f"{task_dir}:/task:ro", "-v", f"{run_dir}:/agentrun:ro",
            "-v", f"{checker_dir}:/checker:ro", "-v", f"{out_dir}:/out",
            f"aa-actual:{cond}", "bash", "-c", script]


def stage_hidden_tests(task_dir: Path, hidden_tests: list[str], cond: str,
                       eval_dir: Path) -> list[str]:
    """Write each hidden test's base copy (``tasks/<id>/hidden/<path>``), rewritten for
    ``cond``, to ``<eval_dir>/hidden_src/<path>``; the eval script copies it over the
    restored file. Returns the staged paths; a test without a base copy is left to
    the image HEAD restore (older task dirs)."""
    staged = []
    for t in hidden_tests:
        src = task_dir / TASK_HIDDEN / t
        if not src.is_file():
            continue
        text = src.read_text(encoding="utf-8", errors="surrogateescape")
        dst = eval_dir / HIDDEN_SRC / t
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(rewrite_for_condition(text, cond, t), encoding="utf-8",
                       errors="surrogateescape")
        staged.append(t)
    return staged


def docker_execute(argv: list[str], timeout: int) -> int:
    name = argv[argv.index("--name") + 1]
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        raise


# --------------------------------------------------------------------------- pieces

def _read_int(p: Path) -> int | None:
    try:
        return int(p.read_text().strip())
    except (OSError, ValueError):
        return None


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def diff_files(diff_text: str) -> set[str]:
    """Paths (old and new side) touched by a unified git diff."""
    files: set[str] = set()
    for ln in diff_text.splitlines():
        if ln.startswith("diff --git "):
            parts = ln[len("diff --git "):].split(" b/", 1)
            files.add(parts[0][2:] if parts[0].startswith("a/") else parts[0])
            if len(parts) == 2:
                files.add(parts[1])
        elif ln.startswith(("--- a/", "+++ b/")):
            files.add(ln[6:].split("\t")[0])
    return files


def touches_test_infra(diff_text: str) -> bool:
    return any(f in TEST_INFRA_FILES or any(f.startswith(d + "/") for d in TEST_INFRA_DIRS)
               or (f.startswith(config.LOOT + "/") and f"/{MOCKS_DIR}/" in f)
               for f in diff_files(diff_text))


def diff_stats(diff_text: str) -> dict[str, int]:
    files: set[str] = set()
    added = removed = 0
    lines = diff_text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("diff --git "):
            files.add(ln.split(" b/", 1)[-1])
        elif ln.startswith("+++ ") or ln.startswith("--- "):
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if ln.startswith("--- ") and nxt.startswith("+++ "):
                continue
            if ln.startswith("+++ ") and i > 0 and lines[i - 1].startswith("--- "):
                tgt = ln[4:].split("\t")[0]
                src = lines[i - 1][4:].split("\t")[0]
                path = src if tgt == "/dev/null" else tgt
                files.add(path[2:] if path[:2] in ("a/", "b/") else path)
                continue
        if ln.startswith("+") and not ln.startswith("+++ "):
            added += 1
        elif ln.startswith("-") and not ln.startswith("--- "):
            removed += 1
    return {"files": len(files), "added": added, "removed": removed}


def hidden_outcome(report: dict | None, hidden_tests: list[str]) -> dict[str, Any]:
    """correct = report present, every hidden file in it, >=1 pass, 0 failures."""
    if report is None:
        return {"correct": False, "passed": 0, "failed": 0, "failed_tests": ["<no report>"],
                "missing_files": list(hidden_tests)}
    res = parse_vitest_json(report, root=CONTAINER_LOOT)
    present = {f"{config.LOOT}/{t.split('::', 1)[0]}" for t in res.passed | res.failed | res.skipped}
    present |= {f"{config.LOOT}/{_rel_report(f.get('name', ''))}" for f in report.get("testResults", [])}
    missing = [t for t in hidden_tests if t not in present]
    correct = bool(res.passed) and not res.failed and not missing
    return {"correct": correct, "passed": len(res.passed), "failed": len(res.failed),
            "failed_tests": sorted(res.failed)[:50], "missing_files": missing}


def probe_incomplete(eval_dir: Path, clean_report: dict | None) -> bool:
    """True when pass 2 (probe) cannot be trusted to have seen the whole hidden run:
    it did not finish, was killed by ``timeout`` (rc 124/137), wrote no parseable
    report, or has a test failing that passed in the clean pass (a probe-induced
    timeout or error)."""
    rc = _read_int(eval_dir / "vitest_probe_rc")
    if rc is None or rc in (124, 137) or not (eval_dir / "eval_done").exists():
        return True
    try:
        probe_report = json.loads((eval_dir / PROBE_REPORT).read_text())
    except (OSError, json.JSONDecodeError):
        return True
    probed = parse_vitest_json(probe_report, root=CONTAINER_LOOT)
    if clean_report is None:
        return bool(probed.failed)
    clean = parse_vitest_json(clean_report, root=CONTAINER_LOOT)
    return bool(probed.failed - clean.failed)


def _rel_report(name: str) -> str:
    prefix = CONTAINER_LOOT + "/"
    return name[len(prefix):] if name.startswith(prefix) else name


# --------------------------------------------------------------------------- trace

_EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "apply_patch"}
_READERS = {"cat", "sed", "head", "tail", "nl", "less", "more", "bat"}
# sed -i, apply_patch / git apply, or a redirection into the repo's sources.
_SHELL_EDIT = re.compile(
    r"\bsed\s+(?:-\w+\s+)*-i|\bapply_patch\b|\bgit\s+apply\b"
    r"""|>>?\s*['"]?(?:/work/actual/)?(?:packages/|src/)""")
_LINT_CMD = re.compile(r"\b(lint(:\w+)?|eslint|oxlint)\b")
_PATHLIKE = re.compile(r"^[\w./@#+-]+$")
_SHELL_WRAP = re.compile(r"""^\s*(?:/\w+)*/?(?:ba|z)?sh\s+-l?c\s+(['"])(.*)\1\s*$""", re.S)


def _norm_path(p: str) -> str:
    for pre in ("/work/actual/", "./"):
        if p.startswith(pre):
            p = p[len(pre):]
    return p


def _paths_read_by_shell(cmd: str) -> list[str]:
    m = _SHELL_WRAP.match(cmd)
    if m:
        cmd = m.group(2)
    out: list[str] = []
    for seg in re.split(r"&&|\|\||;|\||\n", cmd):
        try:
            toks = shlex.split(seg)
        except ValueError:
            toks = seg.split()
        if toks and toks[0] == "cd":
            continue
        if not toks or toks[0] not in _READERS:
            continue
        args = [t for t in toks[1:] if not t.startswith("-")]
        if toks[0] == "sed" and "-e" not in toks and args:
            args = args[1:]  # first non-flag argument is the sed script
        for a in args:
            if _PATHLIKE.match(a) and ("/" in a or re.search(r"\.\w+$", a)):
                out.append(_norm_path(a))
    return out


def extract_trace(agent: str, lines: Iterable[str]) -> dict[str, Any]:
    """files_read (Read tool + cat/sed/head/... in shell commands), first_edit_turn
    (1-based model turn of the first edit), lint_invocations (shell commands running lint)."""
    files: list[str] = []
    first_edit: int | None = None
    lint = 0
    turn = 0
    seen_msgs: set[str] = set()

    def read(p: str) -> None:
        p = _norm_path(p)
        if p and p not in files:
            files.append(p)

    def shell(cmd: str) -> None:
        nonlocal lint, first_edit
        for p in _paths_read_by_shell(cmd):
            read(p)
        if _LINT_CMD.search(cmd):
            lint += 1
        if first_edit is None and _SHELL_EDIT.search(cmd):
            first_edit = turn

    for raw in lines:
        raw = raw.strip()
        if not raw.startswith("{"):
            continue
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict):
            continue
        if config.engine(agent) == "claude":
            if ev.get("type") != "assistant":
                continue
            msg = ev.get("message") or {}
            mid = msg.get("id") or f"_anon{turn}"
            if mid not in seen_msgs:
                seen_msgs.add(mid)
                turn += 1
            for b in msg.get("content") or []:
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                name, inp = b.get("name", ""), b.get("input") or {}
                if name == "Read" and inp.get("file_path"):
                    read(str(inp["file_path"]))
                elif name == "Bash":
                    shell(str(inp.get("command", "")))
                if name in _EDIT_TOOLS and first_edit is None:
                    first_edit = turn
        else:
            if ev.get("type") != "item.completed":
                continue
            item = ev.get("item") or {}
            it = item.get("type")
            if it in ("command_execution", "local_shell_call", "function_call", "custom_tool_call",
                      "file_change", "mcp_tool_call", "web_search", "agent_message"):
                turn += 1
            if it in ("command_execution", "local_shell_call"):
                cmd = item.get("command", "")
                shell(" ".join(cmd) if isinstance(cmd, list) else str(cmd))
            elif it == "file_change" and first_edit is None:
                first_edit = turn
            elif it in ("function_call", "custom_tool_call") and item.get("name") == "apply_patch" \
                    and first_edit is None:
                first_edit = turn
    return {"files_read": files, "first_edit_turn": first_edit, "lint_invocations": lint}


def contamination(agent: str, lines: list[str], refs: Iterable[str] = ()) -> list[str]:
    """Upstream-access markers in the agent's actions, from
    ``aa.agents.detect_contamination(agent, lines, refs)`` (review finding 8; ``refs``
    are the task's upstream PR/issue numbers). Empty when that function is not
    available."""
    try:
        from aa.agents import detect_contamination  # type: ignore[attr-defined]
    except ImportError:
        return []
    return sorted(detect_contamination(agent, lines, refs) or [])


# --------------------------------------------------------------------------- task fields

# Memo-probe similarity at or above which a task counts as contaminated in the
# results (a softer bar than memo_probe.MEMORISED_THRESHOLD, which drops tasks).
CONTAMINATION_MEMO_THRESHOLD = 0.25


def _memo_similarities(task: dict, ledger_entry: dict | None, memo: dict | None) -> dict[str, float]:
    """Numeric memo similarity per agent from task.json / ledger ``memo_<agent>`` and
    ``memo.json`` (``{agent: {"similarity": x}}``). Pending/None values are skipped;
    the highest known value per agent wins."""
    sims: dict[str, float] = {}

    def add(agent: str, v: Any) -> None:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return
        sims[agent] = max(sims.get(agent, float("-inf")), float(v))

    for src in (task, ledger_entry or {}):
        for k, v in src.items():
            if k.startswith("memo_") and k not in ("memo_reference", "memo_contaminated"):
                add(k[len("memo_"):], v)
    for agent, rec in (memo or {}).items():
        if isinstance(rec, dict):
            add(agent, rec.get("similarity"))
    return sims


def task_fields(task: dict, *, ledger_entry: dict | None = None, memo: dict | None = None,
                contamination_flag: bool = False) -> dict[str, Any]:
    """Per-task fields copied into every result.json: ``source`` ("mined"|"issue"),
    ``ai_label`` (bool on mined tasks, None on issue tasks), ``contaminated`` and its
    ``contaminated_reasons`` (public fix PR on issue tasks, memo similarity >=
    CONTAMINATION_MEMO_THRESHOLD for either agent, or the run's own contamination flag)."""
    entry = ledger_entry or {}
    kind = task.get("kind") or entry.get("kind")
    source = task.get("source") or entry.get("source") or ("issue" if kind == "issue" else "mined")
    if source == "issue":
        ai_label = None
    else:
        raw = task.get("ai_label", entry.get("ai_label"))
        ai_label = None if raw is None else bool(raw)
    reasons: list[str] = []
    if source == "issue" and (task.get("public_fix_pr") or entry.get("public_fix_pr")):
        reasons.append("public_fix_pr")
    for agent, sim in sorted(_memo_similarities(task, entry, memo).items()):
        if sim >= CONTAMINATION_MEMO_THRESHOLD:
            reasons.append(f"memo_{agent}>={CONTAMINATION_MEMO_THRESHOLD}")
    if contamination_flag:
        reasons.append("contamination_flag")
    return {"source": source, "ai_label": ai_label, "contaminated": bool(reasons),
            "contaminated_reasons": reasons}


def load_task_context(task_id: str, tasks_root: Path | None = None) -> tuple[dict | None, dict | None]:
    """(ledger entry, memo.json) for a task; None for whatever is missing or unreadable."""
    root = tasks_root or config.TASKS
    entry = memo = None
    try:
        ledger = json.loads((root / "_ledger.json").read_text())
        e = ledger.get(task_id) if isinstance(ledger, dict) else None
        entry = e if isinstance(e, dict) else None
    except (OSError, ValueError):
        pass
    try:
        m = json.loads((root / task_id / "memo.json").read_text())
        memo = m if isinstance(m, dict) else None
    except (OSError, ValueError):
        pass
    return entry, memo


# --------------------------------------------------------------------------- result

def assemble_result(meta: dict, task: dict, diff_text: str, eval_dir: Path | None,
                    transcript: list[str], eval_error: str | None = None, *,
                    ledger_entry: dict | None = None, memo: dict | None = None) -> dict:
    """Pure: build result.json from agent.json, task.json, the diff and the eval outputs."""
    agent, cond = meta["agent"], meta["cond"]
    usage = meta.get("usage") or {}
    status = meta.get("status")
    result: dict[str, Any] = {
        "agent": agent, "cond": cond, "task": meta.get("task"), "pass": meta.get("pass"),
        "status": status,
        "correct": False,
        "violations": [],
        "bad_decision": False,
        "bad_decision_hidden_only": False,
        "lint_ok": None, "typecheck_ok": None,
        "tokens": {"input": int(usage.get("input_tokens") or 0),
                   "output": int(usage.get("output_tokens") or 0),
                   "cached_input": int(usage.get("cached_input_tokens") or 0)},
        "turns": int(usage.get("turns") or 0), "tool_calls": int(usage.get("tool_calls") or 0),
        "wall_s": meta.get("wall_s"),
        "diff": diff_stats(diff_text),
        "agent_touched_test_infra": touches_test_infra(diff_text),
        "reimplementation": False,
        "trace": extract_trace(agent, transcript),
        "contamination_flag": False,
        "contamination_markers": contamination(agent, transcript, task_refs(task)),
        "eval_error": None,
        "hidden": None,
        "probe_incomplete": None,
    }
    result["contamination_flag"] = bool(result["contamination_markers"])
    result.update(task_fields(task, ledger_entry=ledger_entry, memo=memo,
                              contamination_flag=result["contamination_flag"]))
    for k in ("infra_retries", "infra_attempts"):
        if k in meta:
            result[k] = meta[k]
    if status not in EVALUATED:
        result["eval_error"] = "not_evaluated"
        return result

    if eval_error is None and eval_dir is not None:
        e = _read_text(eval_dir / "eval_error").strip()
        eval_error = e or None
    if eval_error is None and (eval_dir is None or not (eval_dir / "eval_done").exists()):
        eval_error = "container"
    if eval_error in ("container", "eval_timeout") and eval_dir is not None \
            and (eval_dir / CLEAN_DONE).exists():
        # Died during pass 2 (probe): the clean pass already decided correctness.
        eval_error = None
    result["eval_error"] = eval_error
    if eval_error in ("revert", "diff_apply", "hidden_restore") or eval_dir is None:
        # Nothing ran on the agent's tree (plan: diff_apply -> correct=false, violations=[]).
        return result

    lint_rc, tc_rc = _read_int(eval_dir / "lint_rc"), _read_int(eval_dir / "typecheck_rc")
    result["lint_ok"] = None if lint_rc is None else lint_rc == 0
    result["typecheck_ok"] = None if tc_rc is None else tc_rc == 0
    report_p = eval_dir / "report.json"
    try:
        report = json.loads(report_p.read_text()) if report_p.exists() else None
    except json.JSONDecodeError:
        report = None
    hidden = hidden_outcome(report, task.get("hidden_tests") or [])
    result["hidden"] = hidden
    result["correct"] = hidden["correct"] and eval_error is None
    result["probe_incomplete"] = probe_incomplete(eval_dir, report)

    violations: list[Violation] = check_diff(diff_text, cond)
    violations += probe_violations(read_probe_events(eval_dir / "probe.jsonl"), diff_text, cond)
    result["violations"] = [v.to_json() for v in violations]
    result["bad_decision"] = result["correct"] and bool(violations)
    result["bad_decision_hidden_only"] = result["correct"] and any(not v.lint_visible for v in violations)
    result["reimplementation"] = any(v.kind in REIMPLEMENTATION_KINDS for v in violations)
    return result


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)


def load_task_meta(task_id: str, tasks_root: Path | None = None) -> tuple[dict, Path]:
    d = (tasks_root or config.TASKS) / task_id
    return json.loads((d / "task.json").read_text()), d


def evaluate_run(run_dir: Path, *, tasks_root: Path | None = None,
                 execute: Executor = docker_execute,
                 checker_dir: Path = PROBE_SRC.parent) -> dict | None:
    """Evaluate one run dir and write ``result.json``. Returns the result, or None when
    the run is not final yet (no agent.json, or status ``infra``)."""
    run_dir = Path(run_dir).resolve()
    meta_p = run_dir / "agent.json"
    if not meta_p.exists():
        return None
    meta = json.loads(meta_p.read_text())
    status = meta.get("status")
    if status == "infra":
        return None
    transcript = _read_text(run_dir / "transcript.jsonl").splitlines()
    diff_text = _read_text(run_dir / "diff.patch")
    if status not in EVALUATED:
        try:  # only for the contamination refs; the run is not evaluated
            task_for_refs = load_task_meta(meta["task"], tasks_root)[0]
        except (OSError, KeyError, ValueError):
            task_for_refs = {}
        ledger_entry, memo = load_task_context(str(meta.get("task")), tasks_root)
        result = assemble_result(meta, task_for_refs, diff_text, None, transcript,
                                 ledger_entry=ledger_entry, memo=memo)
        _write_json(run_dir / "result.json", result)
        return result

    eval_error: str | None = None
    eval_dir: Path | None = run_dir / EVAL_DIR
    task: dict = {}
    try:
        task, task_dir = load_task_meta(meta["task"], tasks_root)
        revert = task["per_condition"][meta["cond"]]["revert_patch"]
        if not task.get("hidden_tests"):
            raise ValueError("task has no hidden_tests")  # vitest would run the whole suite
        if eval_dir.exists():
            shutil.rmtree(eval_dir)
        eval_dir.mkdir()
        stage_hidden_tests(task_dir, task["hidden_tests"], meta["cond"], eval_dir)
        new_hidden = task["hidden_tests"] if task.get("kind") == "issue" else []
        script = eval_script(revert, task["hidden_tests"], new_hidden=new_hidden)
        argv = eval_docker_argv(meta["cond"], run_dir, task_dir.resolve(), eval_dir, script,
                                checker_dir)
    except (OSError, KeyError, ValueError) as exc:  # missing task, bad task.json, no hidden tests
        eval_error = f"setup:{type(exc).__name__}: {exc}"[:300]
        eval_dir = None
    else:
        try:
            execute(argv, HOST_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            eval_error = "eval_timeout"
        except Exception:  # docker missing / daemon down: recorded as `container` below
            pass
    ledger_entry, memo = load_task_context(str(meta.get("task")), tasks_root)
    result = assemble_result(meta, task, diff_text, eval_dir, transcript, eval_error,
                             ledger_entry=ledger_entry, memo=memo)
    _write_json(run_dir / "result.json", result)
    return result


def pending_runs(root: Path | None = None, force: bool = False) -> list[Path]:
    """Run dirs with agent.json and a final status that have no result.json yet."""
    root = root or config.RUNS
    out = []
    for meta_p in sorted(Path(root).rglob("agent.json")):
        d = meta_p.parent
        try:
            status = json.loads(meta_p.read_text()).get("status")
        except (OSError, json.JSONDecodeError):
            continue
        if status == "infra":
            continue
        if force or not (d / "result.json").exists():
            out.append(d)
    return out


def evaluate_all(root: Path | None = None, *, force: bool = False, workers: int = 2,
                 log: Callable[[str], None] = print, **kw: Any) -> dict[Path, dict | None]:
    """Entry point for `aa evaluate --all`: evaluates every pending run dir."""
    dirs = pending_runs(root, force)
    results: dict[Path, dict | None] = {}

    def one(d: Path) -> None:
        try:
            r = evaluate_run(d, **kw)
        except Exception as exc:  # never let one run stop the batch
            log(f"{d}: evaluator crashed: {type(exc).__name__}: {exc}")
            r = None
        results[d] = r
        if r is not None:
            log(f"{d}: status={r['status']} correct={r['correct']} "
                f"violations={len(r['violations'])} eval_error={r['eval_error']}")

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(one, dirs))
    return results
