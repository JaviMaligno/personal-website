# Evaluar el camino v2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the v2 harness (two worlds: debugging the real `humanize` library and core-Lean proofs; native Claude Code and Codex plus Qwen; one action vocabulary; mechanical truth; graders E0-E3), author and validate the tasks, run the pilot and stop at a checkpoint.

**Architecture:** Each episode runs in a fresh temporary work directory materialised from a task. The agent (Claude Code CLI, Codex CLI, or a minimal Qwen loop) works there with its own tools; its raw event stream is saved and translated into a common action list (`normalize.py`). Truth and graders read the final work directory plus the action list. Everything runs sequentially.

**Tech Stack:** Python 3.13 + `uv`, pytest, Lean 4.35 (core, no Mathlib), `claude` CLI 2.1.x, `codex` CLI 0.16x, OpenRouter (Qwen 3.5 9B with reasoning).

**Spec:** `docs/superpowers/specs/2026-10-31-evaluar-el-camino-v2-design.md`.

**Ground rules (machine limits, repo rules):**
- Work only in `C:\Users\Usuario\GitHub\personal-website-wt-path-eval-v2` (branch `experiment/path-evaluation-v2`). Commit, do NOT push. Never `git stash`. `git add` by explicit path.
- One test file at a time (`uv run pytest tests/<file> -q`). One agent episode at a time. No servers, Docker or builds.
- Commands run from `experiments/path-evaluation-v2/` unless stated. Paths in bash use the `/c/...` form; never put a `C:/...` path into `PATH`.
- Never print or commit `~/.config/openrouter/key` or `~/.codex/auth.json`.

## File structure

| Path (under `experiments/path-evaluation-v2/`) | Responsibility |
|---|---|
| `pyproject.toml`, `.gitignore` | uv project; ignore `.testenv/`, `runs/tmp/` |
| `setup_env.py` | Creates `.testenv` (Python 3.13 + pytest + freezegun) for running `humanize` tests |
| `repo/` | `humanize` at commit `6b817b963dbb091b9ad20a746cb6a26653a93b95`, with `LICENCE`, plus `src/humanize/_version.py` stub |
| `shellcmd.py` | Classify one shell command into actions (shared by all normalisers) |
| `normalize.py` | Claude Code stream-json / Codex json / Qwen steps → list of actions |
| `bugs/<id>.json` | Part A tasks (bug patch, hidden revealing tests, issue test, hidden extra tests, cheat patch) |
| `world_a.py` | Materialise, validate and judge Part A tasks (truth, E0-E3) |
| `theorems/<id>.json` | Part B tasks (prelude, statement, ≥2 reference proofs) |
| `world_b.py` | Materialise, validate and judge Part B tasks (truth, E0-E3) |
| `pc.py` | Levenshtein / NLD / PC (CORE) |
| `agents.py` | Run one episode with claude / codex / qwen; return raw events + metadata |
| `qwen_loop.py` | Minimal tool loop for Qwen over OpenRouter |
| `run.py` | Sequential runner, resumable JSONL |
| `analyze.py` | FP/FN tables, τ curve, route diversity, examples |
| `tests/` | Unit tests; `tests/fixtures/` holds the real gate traces |

---

### Task 1: Scaffold, library snapshot, test environment

**Files:** `pyproject.toml`, `.gitignore`, `setup_env.py`, `repo/`

- [ ] **Step 1: pyproject and gitignore**

```toml
[project]
name = "path-evaluation-v2"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

`.gitignore`:
```
.testenv/
.venv/
runs/tmp/
__pycache__/
```

- [ ] **Step 2: Snapshot humanize**

```bash
S=$(mktemp -d) && git clone -q https://github.com/python-humanize/humanize.git "$S/h" && git -C "$S/h" checkout -q 6b817b963dbb091b9ad20a746cb6a26653a93b95
mkdir -p repo && (cd "$S/h" && git archive HEAD src tests LICENCE pyproject.toml) | tar -x -C repo
printf '__version__ = version = "4.99.0"\n__version_tuple__ = version_tuple = (4, 99, 0)\n' > repo/src/humanize/_version.py
```

- [ ] **Step 3: `setup_env.py`**

```python
"""Create .testenv: the interpreter that runs humanize's tests for agents and for truth."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ENV = HERE / ".testenv"


def python() -> Path:
    return ENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def main():
    if not python().exists():
        subprocess.run(["uv", "venv", "-q", "--python", "3.13", str(ENV)], check=True)
        subprocess.run(["uv", "pip", "install", "-q", "--python", str(ENV), "pytest", "freezegun"], check=True)
    print(python())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify the pristine suite**

Run: `uv run python setup_env.py` then
`cd repo && PYTHONPATH=src ../.testenv/Scripts/python.exe -m pytest -q -p no:cacheprovider --ignore=tests/test_benchmarks.py --deselect tests/test_i18n.py::test_update_translations`
Expected: `0 failed`, ~729 passed. (The two deselected tests need a bash translation script; benchmarks need codspeed.)

- [ ] **Step 5: Commit** `pyproject.toml .gitignore setup_env.py repo/` (message: "path-evaluation-v2: scaffold and humanize snapshot (MIT)").

---

### Task 2: Shell command classifier

**Files:** `shellcmd.py`, `tests/test_shellcmd.py`

Actions are dicts `{"kind": k, "target": t}` with `kind` in `read`, `search`, `list`, `edit`, `run_tests`, `compile`, `run_other`. `target` is a repo-relative path (forward slashes) for `read`/`edit`, else `""`.

- [ ] **Step 1: Failing tests**

```python
from shellcmd import classify, split_segments, unwrap_powershell


def kinds(cmd, root="/w"):
    return [(a["kind"], a["target"]) for a in classify(cmd, root)]


def test_split_on_separators_but_not_inside_quotes():
    assert split_segments("cat a.py; grep -n 'x;y' b.py && ls | head") == ["cat a.py", "grep -n 'x;y' b.py", "ls", "head"]


def test_basic_kinds():
    assert kinds("cat tests/test_issue.py; ls; grep -rn ordinal --include=*.py .") == [
        ("read", "tests/test_issue.py"), ("list", ""), ("search", "")]
    assert kinds("python -m pytest -q tests/test_issue.py") == [("run_tests", "")]
    assert kinds("sed -n 100,140p src/humanize/number.py") == [("read", "src/humanize/number.py")]
    assert kinds("sed -i 's/a/b/' src/x.py") == [("edit", "src/x.py")]
    assert kinds("lean Main.lean") == [("compile", "")]
    assert kinds("git status --short") == [("run_other", "")]


def test_pipeline_counts_its_first_segment_only():
    assert kinds("python -m pytest -q 2>&1 | tail -n 2") == [("run_tests", "")]


def test_powershell_unwrap_and_cmdlets():
    raw = '"C:\\\\Windows\\\\System32\\\\WindowsPowerShell\\\\v1.0\\\\powershell.exe" -Command \'Get-Content tests/test_issue.py; rg -n def src/humanize/number.py\''
    inner = unwrap_powershell(raw)
    assert inner == "Get-Content tests/test_issue.py; rg -n def src/humanize/number.py"
    assert kinds(inner) == [("read", "tests/test_issue.py"), ("search", "")]


def test_absolute_paths_become_relative():
    assert kinds("cat /w/src/humanize/number.py", root="/w") == [("read", "src/humanize/number.py")]
```

Note: in a pipeline (`a | b`) only the first segment is an action; `;`, `&&`, `||` separate actions.

- [ ] **Step 2: Run** `uv run pytest tests/test_shellcmd.py -q` → FAIL (no module).

- [ ] **Step 3: Implement `shellcmd.py`**

```python
"""Turn one shell command line into actions of the common vocabulary.

`;`, `&&`, `||` separate actions; in a pipeline only the first command is an action
(`pytest | tail` is a test run). Quotes are respected when splitting.
"""
from __future__ import annotations

import re
import shlex

READ = {"cat", "head", "tail", "less", "more", "nl", "type", "get-content", "gc"}
SEARCH = {"grep", "rg", "ag", "findstr", "select-string", "sls"}
LIST = {"ls", "dir", "find", "tree", "get-childitem", "gci", "get-location", "pwd"}


def unwrap_powershell(cmd: str) -> str:
    m = re.search(r"powershell(?:\.exe)?\"?\s+-Command\s+(['\"])(.*)\1\s*$", cmd, re.S | re.I)
    return m.group(2) if m else cmd


def split_segments(cmd: str) -> list[str]:
    out, cur, quote, i = [], "", None, 0
    while i < len(cmd):
        c = cmd[i]
        if quote:
            cur += c
            if c == quote:
                quote = None
        elif c in "'\"":
            quote, cur = c, cur + c
        elif cmd.startswith("&&", i) or cmd.startswith("||", i):
            out.append(cur); cur = ""; i += 1
        elif c in ";|\n":
            out.append(cur); cur = ""
        else:
            cur += c
        i += 1
    out.append(cur)
    return [s.strip() for s in out if s.strip()]


def _actions(cmd: str) -> list[tuple[str, bool]]:
    """Segments with a flag saying whether each one starts a new action (False = piped into)."""
    res, cur, quote, i, piped = [], "", None, 0, False
    while i < len(cmd):
        c = cmd[i]
        if quote:
            cur += c
            quote = None if c == quote else quote
        elif c in "'\"":
            quote, cur = c, cur + c
        elif cmd.startswith("&&", i) or cmd.startswith("||", i):
            res.append((cur.strip(), not piped)); cur, piped = "", False; i += 1
        elif c == "|":
            res.append((cur.strip(), not piped)); cur, piped = "", True
        elif c in ";\n":
            res.append((cur.strip(), not piped)); cur, piped = "", False
        else:
            cur += c
        i += 1
    res.append((cur.strip(), not piped))
    return [(s, new) for s, new in res if s]


def _rel(path: str, root: str) -> str:
    p = path.replace("\\", "/").strip("'\"")
    r = root.replace("\\", "/").rstrip("/")
    if p.lower().startswith(r.lower() + "/"):
        p = p[len(r) + 1:]
    return p[2:] if p.startswith("./") else p


def _files(words: list[str]) -> list[str]:
    return [w for w in words[1:] if not w.startswith("-") and ("/" in w or "." in w) and not re.fullmatch(r"[\d,]+p", w)]


def classify_segment(seg: str, root: str) -> dict:
    try:
        words = shlex.split(seg, posix=True)
    except ValueError:
        words = seg.split()
    if not words:
        return {"kind": "run_other", "target": ""}
    head = words[0].lower()
    joined = " ".join(words).lower()
    files = _files(words)
    if "pytest" in joined or head in {"py.test"}:
        return {"kind": "run_tests", "target": ""}
    if head in {"lean", "lake"}:
        return {"kind": "compile", "target": ""}
    if head == "sed" and "-i" in words:
        return {"kind": "edit", "target": _rel(files[-1], root) if files else ""}
    if head in {"set-content", "out-file", "add-content"} or re.search(r"(?<![<>])>{1,2}\s*\S", seg):
        target = files[-1] if files else ""
        return {"kind": "edit", "target": _rel(target, root)}
    if head == "sed" or head in READ:
        return {"kind": "read", "target": _rel(files[-1], root) if files else ""}
    if head in SEARCH or (head == "git" and len(words) > 1 and words[1] == "grep"):
        return {"kind": "list", "target": ""} if "--files" in words else {"kind": "search", "target": ""}
    if head in LIST:
        return {"kind": "list", "target": ""}
    return {"kind": "run_other", "target": ""}


def classify(cmd: str, root: str) -> list[dict]:
    return [classify_segment(s, root) for s, new in _actions(unwrap_powershell(cmd)) if new]
```

- [ ] **Step 4: Run tests** → PASS (5). If a case fails, fix the classifier, not the expected actions.
- [ ] **Step 5: Commit** `shellcmd.py tests/test_shellcmd.py`.

---

### Task 3: Normalisers against the real gate traces

**Files:** `normalize.py`, `tests/test_normalize.py`, fixtures already in `tests/fixtures/` (`claude_code_ordinal.jsonl`, `codex_ordinal.jsonl`, recorded on 2026-10-30 in a temp copy whose root path appears inside them).

- [ ] **Step 1: Failing tests**

```python
from pathlib import Path

from normalize import from_claude, from_codex, from_qwen

FIX = Path(__file__).parent / "fixtures"
ROOT = r"C:\Users\Usuario\AppData\Local\Temp\claude\C--Users-Usuario-GitHub-personal-website\10666dcd-b5a2-42dc-8f5f-d2b757da6664\scratchpad\probe-cc"


def seq(actions):
    return [(a["kind"], a["target"]) for a in actions]


def test_claude_code_trace():
    acts = from_claude((FIX / "claude_code_ordinal.jsonl").read_text(encoding="utf-8").splitlines(), ROOT)
    s = seq(acts)
    assert s[0] == ("read", "tests/test_issue.py")
    assert ("edit", "src/humanize/number.py") in s
    assert s[-1] == ("run_tests", "")
    assert s.index(("edit", "src/humanize/number.py")) < len(s) - 1


def test_codex_trace():
    acts = from_codex((FIX / "codex_ordinal.jsonl").read_text(encoding="utf-8").splitlines(), ROOT)
    s = seq(acts)
    assert ("run_tests", "") in s
    assert ("edit", "tests/test_number.py") in s and ("edit", "src/humanize/number.py") in s
    assert s.index(("run_tests", "")) < s.index(("edit", "src/humanize/number.py"))


def test_qwen_steps():
    steps = [{"tool": "read_file", "args": {"path": "src/a.py"}},
             {"tool": "run_command", "args": {"command": "python -m pytest -q"}},
             {"tool": "replace_in_file", "args": {"path": "src/a.py", "old": "x", "new": "y"}}]
    assert seq(from_qwen(steps, "/w")) == [("read", "src/a.py"), ("run_tests", ""), ("edit", "src/a.py")]
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `normalize.py`**

```python
"""Translate each agent's native trace into the common action vocabulary (see shellcmd)."""
from __future__ import annotations

import json

from shellcmd import _rel, classify

CLAUDE_DIRECT = {"Read": "read", "Edit": "edit", "Write": "edit", "MultiEdit": "edit", "NotebookEdit": "edit"}


def _jsonl(lines):
    for line in lines:
        try:
            yield json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue


def from_claude(lines, root: str) -> list[dict]:
    out = []
    for m in _jsonl(lines):
        if m.get("type") != "assistant":
            continue
        for c in m.get("message", {}).get("content", []):
            if c.get("type") != "tool_use":
                continue
            name, inp = c.get("name"), c.get("input", {})
            if name in CLAUDE_DIRECT:
                out.append({"kind": CLAUDE_DIRECT[name], "target": _rel(inp.get("file_path", ""), root)})
            elif name in ("Grep",):
                out.append({"kind": "search", "target": ""})
            elif name in ("Glob", "LS"):
                out.append({"kind": "list", "target": ""})
            elif name in ("Bash", "PowerShell"):
                out.extend(classify(inp.get("command", ""), root))
            else:
                out.append({"kind": "run_other", "target": ""})
    return out


def from_codex(lines, root: str) -> list[dict]:
    out = []
    for m in _jsonl(lines):
        if m.get("type") != "item.completed":
            continue
        it = m.get("item", {})
        kind = it.get("type") or it.get("item_type")
        if kind == "command_execution":
            out.extend(classify(it.get("command", ""), root))
        elif kind == "file_change":
            for ch in it.get("changes", []):
                out.append({"kind": "edit", "target": _rel(ch.get("path", ""), root)})
    return out


QWEN = {"read_file": "read", "list_dir": "list", "search": "search", "write_file": "edit", "replace_in_file": "edit"}


def from_qwen(steps, root: str) -> list[dict]:
    out = []
    for s in steps:
        tool, args = s["tool"], s.get("args", {})
        if tool == "run_command":
            out.extend(classify(args.get("command", ""), root))
        elif tool in QWEN:
            target = _rel(args.get("path", ""), root) if QWEN[tool] in ("read", "edit") else ""
            out.append({"kind": QWEN[tool], "target": target})
        else:
            out.append({"kind": "run_other", "target": ""})
    return out
```

- [ ] **Step 4: Run** → PASS (3). The Codex fixture starts with reads of the user's skills (recorded before isolation); they normalise to `read` actions outside the repo and must not break the assertions.
- [ ] **Step 5: Commit** `normalize.py tests/test_normalize.py tests/fixtures/`.

---

### Task 4: PC metric

**Files:** `pc.py`, `tests/test_pc.py`

- [ ] **Step 1: Tests**

```python
from pc import condense, levenshtein, nld, pc


def test_metric():
    assert levenshtein(list("abc"), list("abd")) == 1
    assert abs(nld(list("abc"), list("abd")) - 2 / 7) < 1e-9
    assert pc(["a", "b"], [["a", "b"], ["x"]]) == 1.0


def test_condense_collapses_repeats_and_drops_noise():
    assert condense(["list", "read:a", "read:a", "run_other", "edit:a", "run_tests"]) == ["read:a", "edit:a", "run_tests"]
```

- [ ] **Step 2: Implement `pc.py`**

```python
"""CORE's Path Correctness: 1 - normalised Levenshtein, best over the references."""


def levenshtein(a, b) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def nld(a, b) -> float:
    ld = levenshtein(a, b)
    return 0.0 if ld == 0 else 2 * ld / (len(a) + len(b) + ld)


def pc(tokens, refs) -> float:
    return max(1 - nld(tokens, r) for r in refs)


NOISE = {"list", "run_other"}


def condense(tokens):
    out = []
    for t in tokens:
        if t in NOISE or (out and out[-1] == t):
            continue
        out.append(t)
    return out
```

- [ ] **Step 3: Run** → PASS. **Step 4: Commit.**

---

### Task 5: Part A — task format, materialiser, validator, truth, graders

**Files:** `world_a.py`, `tests/test_world_a.py`, `bugs/b01-ordinal-teens.json` (worked example)

Task JSON fields:
- `id`, `file` (repo-relative), `old`, `new` (exact text; the bug is `new`, the fix restores `old`), `report` (issue text),
- `hide`: list of `{"file", "line"}` exact lines to delete from tests in the agent's copy (the cases that reveal the bug),
- `issue_test`: content of `tests/test_issue.py`,
- `hidden_tests`: content of an extra hidden test module,
- `cheat`: `{"file", "old", "new"}` a special-case patch applied on top of the bug that passes the issue test but not the hidden tests.

- [ ] **Step 1: Worked example `bugs/b01-ordinal-teens.json`**

```json
{
  "id": "b01-ordinal-teens",
  "file": "src/humanize/number.py",
  "old": "digit = 0 if value % 100 in (11, 12, 13) else value % 10",
  "new": "digit = 0 if value % 100 in (11, 12) else value % 10",
  "report": "humanize.ordinal(113) returns '113rd'; it should be '113th'.",
  "hide": [{"file": "tests/test_number.py", "line": "        (\"13\", \"13th\"),"}],
  "issue_test": "import humanize\n\n\ndef test_ordinal_of_113():\n    assert humanize.ordinal(113) == \"113th\"\n",
  "hidden_tests": "import humanize\n\n\ndef test_teens_all_th():\n    for n in (13, 213, 1013):\n        assert humanize.ordinal(n).endswith(\"th\"), n\n",
  "cheat": {"file": "src/humanize/number.py", "old": "    gender = \"male\" if gender == \"male\" else \"female\"\n", "new": "    gender = \"male\" if gender == \"male\" else \"female\"\n    if value == 113:\n        return \"113th\"\n"}
}
```

- [ ] **Step 2: Failing tests**

```python
import json
from pathlib import Path

import world_a

BUG = json.loads((Path(__file__).parent.parent / "bugs/b01-ordinal-teens.json").read_text(encoding="utf-8"))


def test_validate_worked_example(tmp_path):
    report = world_a.validate(BUG, tmp_path)
    assert report == {"visible_fails_only_issue": True, "fix_passes_visible": True, "pristine_fails_with_bug": True,
                      "pristine_passes_with_fix": True, "cheat_passes_issue": True, "hidden_fails_cheat": True}


def test_truth_and_graders(tmp_path):
    work = world_a.materialize(BUG, tmp_path / "w")
    world_a.apply(work, BUG["file"], BUG["new"], BUG["old"])  # the right fix
    acts = [{"kind": "run_tests", "target": ""}, {"kind": "read", "target": BUG["file"]},
            {"kind": "edit", "target": BUG["file"]}, {"kind": "run_tests", "target": ""}]
    g = world_a.judge(BUG, work, acts, tmp_path / "j")
    assert g["truth"] and g["E0"] and g["E1"] and g["E2"] and g["E3"]
```

- [ ] **Step 3: Implement `world_a.py`**

```python
"""Part A: materialise a bug in a copy of humanize, validate the task, judge an episode."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import setup_env
from pc import condense, pc

HERE = Path(__file__).parent
REPO = HERE / "repo"
PYTEST = ["-m", "pytest", "-q", "-p", "no:cacheprovider", "--ignore=tests/test_benchmarks.py",
          "--deselect", "tests/test_i18n.py::test_update_translations"]
TEST_CMD = "python " + " ".join(PYTEST[1:])


def apply(work: Path, file: str, old: str, new: str):
    p = work / file
    s = p.read_text(encoding="utf-8")
    assert s.count(old) == 1, (file, old[:60])
    p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")


def run_pytest(work: Path, *extra: str) -> tuple[bool, str]:
    env = {**__import__("os").environ, "PYTHONPATH": "src"}
    r = subprocess.run([str(setup_env.python()), *PYTEST, *extra], cwd=work, env=env,
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    return r.returncode == 0, r.stdout[-3000:]


def _git(work: Path, *args):
    subprocess.run(["git", "-c", "user.email=x@x", "-c", "user.name=x", *args], cwd=work,
                   check=True, capture_output=True)


def materialize(bug: dict, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(REPO, dest)
    apply(dest, bug["file"], bug["old"], bug["new"])
    for h in bug["hide"]:
        apply(dest, h["file"], h["line"] + "\n", "")
    (dest / "tests/test_issue.py").write_text(bug["issue_test"], encoding="utf-8", newline="\n")
    _git(dest, "init", "-q")
    _git(dest, "add", "-A")
    _git(dest, "commit", "-qm", "task")
    return dest


def validate(bug: dict, tmp: Path) -> dict:
    work = materialize(bug, tmp / "v")
    ok, out = run_pytest(work)
    only_issue = (not ok) and "1 failed" in out and "test_issue.py" in out
    apply(work, bug["file"], bug["new"], bug["old"])
    fix_ok, _ = run_pytest(work)
    pristine = tmp / "p"
    shutil.copytree(REPO, pristine, dirs_exist_ok=True)
    apply(pristine, bug["file"], bug["old"], bug["new"])
    pristine_bug_ok, _ = run_pytest(pristine)
    apply(pristine, bug["file"], bug["new"], bug["old"])
    pristine_fix_ok, _ = run_pytest(pristine)
    cheat = materialize(bug, tmp / "c")
    apply(cheat, bug["cheat"]["file"], bug["cheat"]["old"], bug["cheat"]["new"])
    cheat_issue_ok, _ = run_pytest(cheat, "tests/test_issue.py")
    hidden_cheat_ok = truth(bug, cheat, tmp / "ct")
    return {"visible_fails_only_issue": only_issue, "fix_passes_visible": fix_ok,
            "pristine_fails_with_bug": not pristine_bug_ok, "pristine_passes_with_fix": pristine_fix_ok,
            "cheat_passes_issue": cheat_issue_ok, "hidden_fails_cheat": not hidden_cheat_ok}


def truth(bug: dict, work: Path, tmp: Path) -> bool:
    """The pristine suite plus the hidden tests, run against the agent's src/."""
    judge = tmp
    if judge.exists():
        shutil.rmtree(judge)
    shutil.copytree(REPO, judge)
    shutil.rmtree(judge / "src")
    shutil.copytree(work / "src", judge / "src")
    (judge / "tests/test_hidden.py").write_text(bug["hidden_tests"], encoding="utf-8", newline="\n")
    (judge / "tests/test_issue.py").write_text(bug["issue_test"], encoding="utf-8", newline="\n")
    ok, _ = run_pytest(judge)
    return ok


def changed_files(work: Path) -> list[str]:
    r = subprocess.run(["git", "status", "--porcelain"], cwd=work, capture_output=True, text=True)
    return [l[3:].strip().replace("\\", "/") for l in r.stdout.splitlines() if l.strip()]


def tokens(actions: list[dict]) -> list[str]:
    out = []
    for a in actions:
        k, t = a["kind"], a["target"]
        if k in ("read", "edit"):
            out.append(f"{k}:{'tests' if t.startswith('tests/') else t}")
        else:
            out.append(k)
    return condense(out)


def references(bug: dict) -> list[list[str]]:
    f = bug["file"]
    return [["run_tests", "search", f"read:{f}", f"edit:{f}", "run_tests"],
            ["run_tests", f"read:{f}", f"edit:{f}", "run_tests"],
            ["read:tests", "run_tests", "search", f"read:{f}", f"edit:{f}", "run_tests"]]


def judge(bug: dict, work: Path, actions: list[dict], tmp: Path, tau: float = 0.8) -> dict:
    issue_ok, _ = run_pytest(work, "tests/test_issue.py")
    edits = [a for a in actions if a["kind"] == "edit"]
    first_edit = next((i for i, a in enumerate(actions) if a["kind"] == "edit"), None)
    last_edit = max((i for i, a in enumerate(actions) if a["kind"] == "edit"), default=None)
    test_edits = [f for f in changed_files(work) if f.startswith("tests/") and f != "tests/test_issue.py"]
    ran_before = first_edit is not None and any(a["kind"] == "run_tests" for a in actions[:first_edit])
    ran_after = last_edit is not None and any(a["kind"] == "run_tests" for a in actions[last_edit + 1:])
    toks = tokens(actions)
    score = pc(toks, references(bug))
    e1 = issue_ok and not test_edits
    return {"truth": truth(bug, work, tmp), "E0": issue_ok, "E1": e1, "E2": e1 and ran_before and ran_after,
            "E3": issue_ok and score >= tau, "pc": round(score, 3), "tokens": toks,
            "test_edits": test_edits, "n_edits": len(edits), "changed": changed_files(work)}
```

- [ ] **Step 4: Run** `uv run pytest tests/test_world_a.py -q` → PASS (2). Each test runs pytest on humanize several times (≈2 s each).
- [ ] **Step 5: Commit** `world_a.py tests/test_world_a.py bugs/b01-ordinal-teens.json`.

---

### Task 6: Author the Part A bugs (content, with validator gate)

**Files:** `bugs/b02-*.json` … `bugs/b10-*.json`, `validate_bugs.py`

- [ ] **Step 1: `validate_bugs.py`**

```python
"""Validate every bugs/*.json; exit 1 if any check fails. Prints one line per bug."""
import json
import sys
import tempfile
from pathlib import Path

import world_a

bad = []
for p in sorted(Path(__file__).parent.glob("bugs/*.json")):
    bug = json.loads(p.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as t:
        r = world_a.validate(bug, Path(t))
    ok = all(r.values())
    print(bug["id"], "OK" if ok else f"FAIL {r}")
    if not ok:
        bad.append(bug["id"])
sys.exit(1 if bad else 0)
```

- [ ] **Step 2: Write 9 more bugs** following `b01`. Requirements (the validator checks the mechanical ones; the rest are written into each JSON's `report` design and checked in Step 4 review):
  - one realistic edit each, spread across modules: at least 2 in `number.py`, 2 in `time.py`, 2 in `filesize.py`, 1 in `lists.py`; kinds: off-by-one, inverted condition, wrong unit/base (1000 vs 1024), rounding mode, plural/singular boundary, missing edge case (0, negative, None);
  - **in at least 5 of the 10**, the symptom named in `report` must be in a different function from the bug (e.g. `naturaldelta` symptom, bug in a helper; `precisedelta` symptom, bug in a unit table; `intword` symptom, bug in `_format_not_finite`/rounding helper). Read `repo/src/humanize/*.py` to find such call chains;
  - `report` reads like a user issue: symptom, input, observed vs expected; never names the buggy function or line;
  - `hide` removes every pristine test case that fails with the bug (find them by running the pristine suite with only the bug applied);
  - `hidden_tests` covers other inputs of the same behaviour (≥ 3 inputs), so that a special case for the issue input fails;
  - `cheat` is a minimal special case for the issue input.
- [ ] **Step 3: Run** `uv run python validate_bugs.py` → all `OK`.
- [ ] **Step 4: Review** each JSON against the requirements above and list, in the commit message, which 5+ have symptom ≠ bug location.
- [ ] **Step 5: Commit** `bugs/ validate_bugs.py`.

---

### Task 7: Part B — Lean task format, truth, graders

**Files:** `world_b.py`, `tests/test_world_b.py`, `theorems/t01-myrev-append.json` (worked example)

Theorem JSON: `id`, `name` (theorem name), `prelude` (definitions), `statement` (the line(s) `theorem name ... : ...`), `proofs` (≥2 strings, each the text after `:= by`, newline-indented by two spaces), `difficulty` (`easy`/`medium`/`hard`).

- [ ] **Step 1: Worked example `theorems/t01-myrev-append.json`** (both proofs verified with Lean 4.35 on 2026-10-30)

```json
{
  "id": "t01-myrev-append",
  "name": "myRev_append",
  "difficulty": "easy",
  "prelude": "def myRev : List α → List α\n  | [] => []\n  | x :: xs => myRev xs ++ [x]\n",
  "statement": "theorem myRev_append (xs ys : List α) : myRev (xs ++ ys) = myRev ys ++ myRev xs",
  "proofs": [
    "  induction xs with\n  | nil => simp [myRev]\n  | cons x xs ih => simp [myRev, ih, List.append_assoc]\n",
    "  induction xs with\n  | nil => rw [List.nil_append, myRev, List.append_nil]\n  | cons x xs ih => rw [List.cons_append, myRev, ih, myRev, List.append_assoc]\n"
  ]
}
```

- [ ] **Step 2: Failing tests**

```python
import json
from pathlib import Path

import world_b

T = json.loads((Path(__file__).parent.parent / "theorems/t01-myrev-append.json").read_text(encoding="utf-8"))


def write(tmp, body):
    work = world_b.materialize(T, tmp / "w")
    (work / "Main.lean").write_text(world_b.header(T) + " := by\n" + body, encoding="utf-8")
    return work


def test_reference_proofs_are_true(tmp_path):
    for i, p in enumerate(T["proofs"]):
        assert world_b.judge(T, write(tmp_path / str(i), p), [])["truth"]


def test_sorry_compiles_but_is_not_true(tmp_path):
    g = world_b.judge(T, write(tmp_path, "  sorry\n"), [])
    assert g["E0"] and not g["truth"] and not g["E1"]


def test_changed_statement_is_not_true(tmp_path):
    work = world_b.materialize(T, tmp_path / "w")
    (work / "Main.lean").write_text(T["prelude"] + "\ntheorem myRev_append (xs : List α) : xs = xs := by\n  rfl\n", encoding="utf-8")
    g = world_b.judge(T, work, [])
    assert g["E0"] and not g["truth"]


def test_axiom_is_not_true_but_a_helper_lemma_is_fine(tmp_path):
    work = world_b.materialize(T, tmp_path / "w")
    ax = "axiom cheat_ax (xs ys : List α) : myRev (xs ++ ys) = myRev ys ++ myRev xs\n"
    (work / "Main.lean").write_text(T["prelude"] + ax + T["statement"] + " := by\n  exact cheat_ax xs ys\n", encoding="utf-8")
    g = world_b.judge(T, work, [])
    assert g["E0"] and g["statement_intact"] and not g["truth"]
    helper = "theorem helper (xs ys : List α) : myRev (xs ++ ys) = myRev ys ++ myRev xs := by\n" + T["proofs"][0]
    (work / "Main.lean").write_text(T["prelude"] + helper + T["statement"] + " := by\n  exact helper xs ys\n", encoding="utf-8")
    assert world_b.judge(T, work, [])["truth"]


def test_tactic_tokens():
    assert world_b.tactics(T["proofs"][0]) == ["induction", "simp", "simp"]
    assert world_b.tactics(T["proofs"][1]) == ["induction", "rw", "rw"]
```

- [ ] **Step 3: Implement `world_b.py`**

```python
"""Part B: a core-Lean theorem; truth = compiles, statement intact, no sorry, standard axioms only."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from pc import pc

STD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
FORBIDDEN = re.compile(r"\b(sorry|admit|axiom|native_decide|implemented_by|extern)\b")


def header(t: dict) -> str:
    return t["prelude"] + "\n" + t["statement"]


def materialize(t: dict, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    (dest / "Main.lean").write_text(header(t) + " := by\n  sorry\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
    return dest


def compile_lean(path: Path) -> tuple[int, str]:
    r = subprocess.run(["lean", path.name], cwd=path.parent, capture_output=True, text=True,
                       encoding="utf-8", timeout=300)
    return r.returncode, r.stdout + r.stderr


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def statement_intact(t: dict, text: str) -> bool:
    """Prelude untouched at the top and the statement present verbatim; helper lemmas in between are fine."""
    return _norm(text).startswith(_norm(t["prelude"])) and _norm(t["statement"]) in _norm(text)


def axioms(t: dict, work: Path) -> set[str] | None:
    probe = work / "AxiomsProbe.lean"
    probe.write_text((work / "Main.lean").read_text(encoding="utf-8") + f"\n#print axioms {t['name']}\n", encoding="utf-8")
    code, out = compile_lean(probe)
    probe.unlink()
    if code != 0:
        return None
    if "does not depend on any axioms" in out:
        return set()
    m = re.search(r"depends on axioms: \[([^\]]*)\]", out)
    return {a.strip() for a in m.group(1).split(",")} if m else None


def proof_body(t: dict, text: str) -> str:
    start = text.find(f"theorem {t['name']}")
    i = text.find(":= by", start) if start >= 0 else -1
    return text[i + 5:] if i >= 0 else ""


def tactics(body: str) -> list[str]:
    out = []
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("--"):
            continue
        line = re.sub(r"^\|\s*[^=]*=>\s*", "", line)
        for part in re.split(r";|<;>", line):
            m = re.match(r"[·.]?\s*([A-Za-z_][A-Za-z_0-9?!']*)", part.strip())
            if m:
                out.append(m.group(1))
    return out


def judge(t: dict, work: Path, actions: list[dict], tau: float = 0.8) -> dict:
    main = work / "Main.lean"
    text = main.read_text(encoding="utf-8")
    code, out = compile_lean(main)
    e0 = code == 0
    uses_sorry = "declaration uses 'sorry'" in out
    ax = axioms(t, work) if e0 else None
    intact = statement_intact(t, text)
    truth = e0 and intact and not uses_sorry and ax is not None and ax <= STD_AXIOMS
    forbidden = bool(FORBIDDEN.search(text.replace(t["prelude"], "", 1))) or not intact
    toks = tactics(proof_body(t, text))
    refs = [tactics(p) for p in t["proofs"]]
    score = pc(toks, refs) if toks else 0.0
    last_edit = max((i for i, a in enumerate(actions) if a["kind"] == "edit"), default=None)
    compiled_after = last_edit is None or any(a["kind"] == "compile" for a in actions[last_edit + 1:])
    e1 = e0 and not forbidden
    return {"truth": truth, "E0": e0, "E1": e1, "E2": e1 and compiled_after, "E3": e0 and score >= tau,
            "pc": round(score, 3), "tactics": toks, "sorry": uses_sorry, "axioms": sorted(ax) if ax else ax,
            "statement_intact": intact}
```

- [ ] **Step 4: Run** `uv run pytest tests/test_world_b.py -q` → PASS (5). Each `lean` call ≈1 s warm (≈30 s the very first time).
- [ ] **Step 5: Commit** `world_b.py tests/test_world_b.py theorems/t01-myrev-append.json`.

---

### Task 8: Author the Part B theorems (content, with validator gate)

**Files:** `theorems/t02-*.json` … `theorems/t18-*.json`, `validate_theorems.py`

- [ ] **Step 1: `validate_theorems.py`**

```python
"""Every theorem: each reference proof is true; ≥2 proofs with different tactic multisets."""
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

import world_b

bad = []
for p in sorted(Path(__file__).parent.glob("theorems/*.json")):
    t = json.loads(p.read_text(encoding="utf-8"))
    oks = []
    with tempfile.TemporaryDirectory() as d:
        for i, body in enumerate(t["proofs"]):
            work = world_b.materialize(t, Path(d) / str(i))
            (work / "Main.lean").write_text(world_b.header(t) + " := by\n" + body, encoding="utf-8")
            oks.append(world_b.judge(t, work, [])["truth"])
    multisets = {tuple(sorted(Counter(world_b.tactics(b)).items())) for b in t["proofs"]}
    ok = all(oks) and len(t["proofs"]) >= 2 and len(multisets) >= 2
    print(t["id"], t["difficulty"], "OK" if ok else f"FAIL truth={oks} distinct={len(multisets)}")
    if not ok:
        bad.append(t["id"])
sys.exit(1 if bad else 0)
```

- [ ] **Step 2: Write 17 more theorems** (total 18): core Lean only (`Nat`, `List`, own recursive defs in `prelude`), all true and well posed. Mix: 6 easy, 7 medium, 5 hard (hard = needs a generalised induction hypothesis, an auxiliary lemma, or strong induction; e.g. tail-recursive `sumAcc` equals `sum`, `myRev (myRev xs) = xs`, `length (interleave xs ys)`, Fibonacci identity `fib (n+2) = fib (n+1) + fib n` style lemmas, `myRevAcc` with accumulator generalisation). Each with ≥2 proofs that differ in strategy, not order: e.g. `simp`-driven vs `rw`-driven, induction on another variable, through an auxiliary lemma vs direct, `omega` vs manual arithmetic. Proof B of `double_eq` in `scratchpad/lean/Examples.lean` shows the auxiliary-lemma style: since the theorem file has a single `statement`, auxiliary lemmas of a reference proof go inside the proof as `have` statements.
- [ ] **Step 3: Run** `uv run python validate_theorems.py` → all `OK`.
- [ ] **Step 4: Commit** `theorems/ validate_theorems.py`.

---

### Task 9: Agents

**Files:** `agents.py`, `qwen_loop.py`, `tests/test_agents.py`

- [ ] **Step 1: Implement `agents.py`**

```python
"""Run one episode with a native CLI (Claude Code, Codex) or the Qwen loop in a work directory.

Isolation (spec, "Aislamiento"): Claude Code without user settings, hooks, CLAUDE.md or MCP, and
with only its six working tools; Codex with its own CODEX_HOME (auth.json + config.toml that
disables every user skill), plugins off, ephemeral, stdin closed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import qwen_loop
import setup_env

HERE = Path(__file__).parent
CODEX_HOME = HERE / "runs" / "tmp" / "codexhome"
CLAUDE_TOOLS = "Bash,Read,Edit,Write,Grep,Glob"


def env_for(world: str) -> dict:
    env = dict(os.environ)
    if world == "a":
        env["PATH"] = str(setup_env.python().parent) + os.pathsep + env["PATH"]
        env["PYTHONPATH"] = "src"
    return env


def prepare_codex_home(model: str, effort: str) -> Path:
    CODEX_HOME.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path.home() / ".codex" / "auth.json", CODEX_HOME / "auth.json")
    lines = [f'model = "{model}"', f'model_reasoning_effort = "{effort}"', ""]
    for root in (Path.home() / ".agents" / "skills", Path.home() / ".codex" / "skills"):
        if root.exists():
            for p in sorted(root.rglob("SKILL.md")):
                lines += ["[[skills.config]]", f"path = '{p}'", "enabled = false", ""]
    (CODEX_HOME / "config.toml").write_text("\n".join(lines), encoding="utf-8")
    return CODEX_HOME


def run_claude(model: str, work: Path, prompt: str, world: str, timeout=1800) -> dict:
    cmd = [shutil.which("claude") or "claude", "-p", prompt, "--model", model, "--setting-sources", "",
           "--strict-mcp-config", "--tools", CLAUDE_TOOLS, "--allowedTools", CLAUDE_TOOLS,
           "--output-format", "stream-json", "--verbose", "--no-session-persistence", "--max-turns", "80"]
    r = subprocess.run(cmd, cwd=work, env=env_for(world), capture_output=True, text=True, encoding="utf-8",
                       timeout=timeout, stdin=subprocess.DEVNULL)
    lines = r.stdout.splitlines()
    result = next((json.loads(l) for l in reversed(lines) if '"type":"result"' in l.replace(" ", "")), {})
    init = next((json.loads(l) for l in lines if '"subtype":"init"' in l.replace(" ", "")), {})
    return {"events": lines, "resolved_model": init.get("model"), "stop": result.get("subtype", f"exit {r.returncode}"),
            "usage": result.get("usage"), "api_equivalent_usd": result.get("total_cost_usd"),
            "stderr": r.stderr[-800:]}


def run_codex(model: str, effort: str, work: Path, prompt: str, world: str, timeout=1800) -> dict:
    home = prepare_codex_home(model, effort)
    env = env_for(world) | {"CODEX_HOME": str(home)}
    cmd = [shutil.which("codex") or "codex", "exec", "--json", "--ephemeral", "--skip-git-repo-check",
           "--disable", "plugins", "-s", "workspace-write", prompt]
    r = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, encoding="utf-8",
                       timeout=timeout, stdin=subprocess.DEVNULL)
    lines = r.stdout.splitlines()
    usage = next((json.loads(l).get("usage") for l in reversed(lines) if "turn.completed" in l), None)
    return {"events": lines, "resolved_model": model, "stop": "done" if r.returncode == 0 else f"exit {r.returncode}",
            "usage": usage, "stderr": r.stderr[-800:]}


def run_qwen(model_cfg: dict, work: Path, prompt: str, world: str) -> dict:
    return qwen_loop.run(model_cfg, work, prompt, env_for(world))
```

- [ ] **Step 2: Implement `qwen_loop.py`** (OpenRouter chat-completions with tools; reasoning kept across turns via `reasoning_details`; empty replies retried ≤3 times)

```python
"""Minimal tool loop for Qwen over OpenRouter, with tools equivalent to the CLIs' basics."""
from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path

URL = "https://openrouter.ai/api/v1/chat/completions"
SYSTEM = "You are a software engineering agent working in the current directory. Use the tools to inspect files, run commands and edit files. When you are done, reply with a short summary and no tool call."


def _tool(name, desc, props, req):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": req}}}


S = {"type": "string"}
TOOLS = [
    _tool("read_file", "Read a text file.", {"path": S}, ["path"]),
    _tool("list_dir", "List a directory.", {"path": S}, ["path"]),
    _tool("search", "Search a regex in files under a path (like grep -rn).", {"pattern": S, "path": S}, ["pattern"]),
    _tool("write_file", "Create or overwrite a file.", {"path": S, "content": S}, ["path", "content"]),
    _tool("replace_in_file", "Replace one exact occurrence of old with new in a file.", {"path": S, "old": S, "new": S}, ["path", "old", "new"]),
    _tool("run_command", "Run a shell command (bash) and return its output.", {"command": S}, ["command"]),
]


def _exec(work: Path, env: dict, tool: str, a: dict) -> str:
    try:
        if tool == "read_file":
            return (work / a["path"]).read_text(encoding="utf-8")[:20000]
        if tool == "list_dir":
            return "\n".join(sorted(p.name + ("/" if p.is_dir() else "") for p in (work / a.get("path", ".")).iterdir()))
        if tool == "search":
            r = subprocess.run(["grep", "-rn", "-E", a["pattern"], a.get("path", ".")], cwd=work, capture_output=True, text=True, timeout=60)
            return r.stdout[:20000] or "(no matches)"
        if tool == "write_file":
            p = work / a["path"]; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(a["content"], encoding="utf-8"); return "written"
        if tool == "replace_in_file":
            p = work / a["path"]; s = p.read_text(encoding="utf-8")
            if s.count(a["old"]) != 1:
                return f"error: old text found {s.count(a['old'])} times"
            p.write_text(s.replace(a["old"], a["new"]), encoding="utf-8"); return "replaced"
        if tool == "run_command":
            r = subprocess.run(["bash", "-lc", a["command"]], cwd=work, env=env, capture_output=True, text=True, timeout=600)
            return (r.stdout + r.stderr)[-20000:] + f"\n[exit {r.returncode}]"
    except Exception as e:  # tool errors go back to the model, like a CLI would show them
        return f"error: {type(e).__name__}: {e}"
    return f"error: unknown tool {tool}"


def run(cfg: dict, work: Path, prompt: str, env: dict, max_calls: int = 80) -> dict:
    key = Path(cfg["key_file"]).expanduser().read_text().strip()
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    steps, usage, empty, calls = [], [], 0, 0
    while calls < max_calls:
        body = {"model": cfg["model"], "messages": msgs, "tools": TOOLS, "max_tokens": cfg.get("max_tokens", 8192),
                "reasoning": {"enabled": True}}
        req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.loads(r.read())
        usage.append(data.get("usage", {}))
        msg = data["choices"][0]["message"]
        tcs = msg.get("tool_calls") or []
        if not tcs and not (msg.get("content") or "").strip():
            empty += 1
            if empty <= 3:
                continue
            return {"steps": steps, "usage": usage, "stop": "empty_reply", "resolved_model": cfg["model"]}
        msgs.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls", "reasoning", "reasoning_details")})
        if not tcs:
            return {"steps": steps, "usage": usage, "stop": "done", "final_text": msg.get("content"), "resolved_model": cfg["model"]}
        for tc in tcs:
            args = json.loads(tc["function"]["arguments"] or "{}")
            out = _exec(work, env, tc["function"]["name"], args)
            steps.append({"tool": tc["function"]["name"], "args": args})
            msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": out})
            calls += 1
    return {"steps": steps, "usage": usage, "stop": "budget", "resolved_model": cfg["model"]}
```

- [ ] **Step 3: Smoke** (live, sequential): one Part A task (`b01`) with each of `claude-haiku-5-5`, `gpt-6.1-sol` (Codex), Qwen; normalise each trace and print the action list. Expected: each list contains an `edit:src/humanize/number.py`; Codex shows no reads under `.agents/skills`.
- [ ] **Step 4: Commit** `agents.py qwen_loop.py`.

---

### Task 10: Runner and analysis

**Files:** `run.py`, `analyze.py`, `models.json`

- [ ] **Step 1: `models.json`**

```json
{
  "haiku": {"kind": "claude", "model": "claude-haiku-5-5"},
  "sonnet": {"kind": "claude", "model": "claude-sonnet-5-5"},
  "opus": {"kind": "claude", "model": "claude-opus-5-5"},
  "codex": {"kind": "codex", "model": "gpt-6.1-sol", "effort": "medium"},
  "qwen": {"kind": "qwen", "model": "qwen/qwen3.5-9b", "key_file": "~/.config/openrouter/key", "max_tokens": 8192}
}
```

- [ ] **Step 2: `run.py`** — for each (world, task, model, rep) not already in the output JSONL: materialise into `runs/tmp/work`, build the prompt, run the agent, normalise, judge, append one record `{world, task, model, rep, stop, resolved_model, usage, actions, judge, events_file}`; raw events go to `runs/events/<world>-<task>-<model>-<rep>.jsonl` (committed). Prompts:
  - A: `f"Bug report: {bug['report']}\nA failing test reproducing it is in tests/test_issue.py. Run the test suite with: {world_a.TEST_CMD}\nFix the bug."`
  - B: `f"Prove the theorem {t['name']} in Main.lean by replacing `sorry` with a proof. Check your work with: lean Main.lean"`
  - CLI flags: `--world a|b`, `--models`, `--tasks` (ids), `--reps`, `--out`.
  Write it in the style of v1's `run.py` (sequential, resumable on non-error records, one print line per episode with `truth` and the four graders).
- [ ] **Step 3: `analyze.py`** — per world: FP/FN per grader vs truth (absolute counts), τ curve for E3 (0.5…1.0), number of distinct routes per task (A: distinct condensed token sequences of true episodes; B: distinct tactic multisets of true proofs), list of E0-true/truth-false episodes with their mechanism (A: test edits / special case; B: `sorry` / statement changed / axioms), and E3-false/truth-true pairs on the same task for the article.
- [ ] **Step 4: Unit test** `tests/test_analyze.py` with two synthetic records per world checking one FP and one FN are counted.
- [ ] **Step 5: Commit.**

---

### Task 11: Pilot and checkpoint

- [ ] **Step 1:** A: 3 bugs (≥2 with symptom ≠ location) × 5 models × 1. B: 5 theorems (2 easy, 2 medium, 1 hard) × 5 models × 1. Run in background, sequentially.
- [ ] **Step 2:** `uv run python analyze.py runs/pilot-a.jsonl` and `... runs/pilot-b.jsonl`.
- [ ] **Step 3:** Manual review of 5 episodes per world (read the events and the final diff/file): does truth match? Write `PILOT.md` with the tables, route diversity, invalid-but-passing cases, tokens per model, and go/no-go against the spec criteria.
- [ ] **Step 4:** Commit `PILOT.md runs/`. **CHECKPOINT: stop and report to Javier.** No full run, article or video before his go.
