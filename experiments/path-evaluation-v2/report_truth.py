"""Second-version truth for world A, limited to what each bug report asks for.

The frozen truth runs every hidden test, and some hidden tests go beyond the report (b09 checks
`naturalday`, the report only names `naturaldate`; b06 fixes how long a month is). This script:

1. splits each bug's hidden tests into single cases (one assert, one parameter row each);
2. asks a blind judge, three times, which cases follow from the report alone (it sees the report,
   the visible failing test and the cases; never an agent, a model name or a fix);
3. re-runs, for every episode the frozen truth rejects, the pristine suite plus only the cases the
   judge's majority says follow from the report, against the agent's src rebuilt from its diff.

    uv run python report_truth.py judge     # writes runs/report-cases.json
    uv run python report_truth.py rerun     # writes runs/report-truth.jsonl
"""
from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import proctree
import setup_env
import world_a

HERE = Path(__file__).parent
CASES = HERE / "runs" / "report-cases.json"
OUT = HERE / "runs" / "report-truth.jsonl"
TMP = Path(__import__("tempfile").gettempdir()) / "pe2" / "report-truth"
JUDGE_MODEL = "claude-opus-5-5"
CONTROL = "control::the failing test the developer was given"
VOTES = 3


def split_hidden(src: str) -> str:
    """One test function per top-level assert: the other statements stay, decorators too."""
    tree = ast.parse(src)
    body = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
            asserts = [i for i, s in enumerate(node.body) if isinstance(s, ast.Assert)]
            if len(asserts) <= 1:
                body.append(node)
                continue
            for k, idx in enumerate(asserts):
                keep = [s for i, s in enumerate(node.body) if not isinstance(s, ast.Assert) or i == idx]
                body.append(ast.FunctionDef(name=f"{node.name}__a{k}", args=node.args, body=keep,
                                            decorator_list=node.decorator_list, returns=node.returns,
                                            type_comment=None, type_params=[]))
        else:
            body.append(node)
    return ast.unparse(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[]))) + "\n"


def collect(bug: dict) -> list[str]:
    """Node ids of the split hidden module, collected in a pristine copy."""
    work = TMP / "collect"
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(world_a.REPO, work)
    (work / "tests/test_hidden.py").write_text(split_hidden(bug["hidden_tests"]), encoding="utf-8", newline="\n")
    r = subprocess.run([str(setup_env.python()), "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                        "tests/test_hidden.py"], cwd=work, capture_output=True, text=True, encoding="utf-8",
                       env={**__import__("os").environ, "PYTHONPATH": "src"})
    return [l.strip() for l in r.stdout.splitlines() if l.startswith("tests/test_hidden.py::")]


PROMPT = """You are checking test cases against a bug report, for a study of how code fixes are graded.

Bug report (this is all the developer was told):
{report}

The failing test the developer was given:
```python
{issue}
```

Hidden test cases, written by someone else:
```python
{hidden}
```

For each case id below, decide whether the expected value in that case is determined by the report:
would every correct fix of the defect the report describes make it pass, wherever in the code that
fix is made? Answer "yes" when the report determines it; "no" when a fix that fully resolves what
the report describes could reasonably make it fail; "unclear" when you cannot tell.

Case ids:
{ids}

Reply with only a JSON object mapping every case id to {{"verdict": "yes"|"no"|"unclear", "why": "<one sentence>"}}."""


def ask(prompt: str) -> dict:
    cmd = [shutil.which("claude") or "claude", "-p", prompt, "--model", JUDGE_MODEL, "--setting-sources", "",
           "--strict-mcp-config", "--tools", "", "--output-format", "json", "--no-session-persistence"]
    r = proctree.run(cmd, cwd=TMP, text=True, encoding="utf-8", timeout=600, hidden=True)
    text = json.loads(r.stdout)["result"]
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def judge_all() -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    out = {}
    for p in sorted((HERE / "bugs").glob("*.json")):
        bug = json.loads(p.read_text(encoding="utf-8"))
        ids = collect(bug)
        # control: the developer's own failing test must come back "yes", or the judge is miscalibrated
        prompt = PROMPT.format(report=bug["report"], issue=bug["issue_test"], hidden=split_hidden(bug["hidden_tests"]),
                               ids="\n".join(ids + [CONTROL]))
        votes = [ask(prompt) for _ in range(VOTES)]
        control = [v.get(CONTROL, {}).get("verdict", "missing") for v in votes]
        if any(c != "yes" for c in control):
            print(bug["id"], "CONTROL FAILED", control, flush=True)
        cases = {}
        for i in ids:
            vs = [v.get(i, {}).get("verdict", "missing") for v in votes]
            top, n = Counter(vs).most_common(1)[0]
            cases[i] = {"votes": vs, "majority": top if n * 2 > len(vs) else "split",
                        "why": [v.get(i, {}).get("why", "") for v in votes]}
        out[bug["id"]] = cases
        print(bug["id"], Counter(c["majority"] for c in cases.values()), flush=True)
    CASES.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


def rebuild_src(bug: dict, diff: str, dest: Path) -> Path:
    """The agent's work copy: the task as materialized, plus its final `git diff`."""
    work = world_a.materialize(bug, dest)
    if diff.strip():
        patch = dest.parent / f"{dest.name}.patch"
        patch.write_text(diff if diff.endswith("\n") else diff + "\n", encoding="utf-8", newline="\n")
        # the repo tracks __pycache__, so diffs carry binary .pyc entries git cannot apply; they are not code
        subprocess.run(["git", "apply", "--whitespace=nowarn", "--exclude=*.pyc", str(patch)], cwd=work, check=True,
                       capture_output=True)
    return work


def truth_with(bug: dict, work: Path, node_ids: list[str] | None) -> bool:
    """Pristine suite + test_issue, then the hidden cases (all of them when node_ids is None)."""
    judge = TMP / "judge"
    if judge.exists():
        shutil.rmtree(judge)
    shutil.copytree(world_a.REPO, judge)
    shutil.rmtree(judge / "src")
    shutil.copytree(work / "src", judge / "src")
    (judge / "tests/test_issue.py").write_text(bug["issue_test"], encoding="utf-8", newline="\n")
    suite_ok, _ = world_a.run_pytest(judge)
    if node_ids == []:
        return suite_ok
    (judge / "tests/test_hidden.py").write_text(split_hidden(bug["hidden_tests"]), encoding="utf-8", newline="\n")
    hidden_ok, _ = world_a.run_pytest(judge, *(node_ids or ["tests/test_hidden.py"]))
    return suite_ok and hidden_ok


def rerun() -> None:
    import analyze
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    recs = [r for r in analyze.load("runs/full-a.jsonl") if not r["judge"]["truth"]]
    with OUT.open("w", encoding="utf-8") as f:
        for r in recs:
            bug = json.loads((HERE / "bugs" / f"{r['task']}.json").read_text(encoding="utf-8"))
            implied = [i for i, c in cases[r["task"]].items() if c["majority"] == "yes"]
            unanimous = [i for i, c in cases[r["task"]].items() if c["votes"].count("yes") == VOTES]
            work = rebuild_src(bug, r["final"], TMP / "w")
            full = truth_with(bug, work, None)  # must reproduce the frozen verdict (False)
            limited = truth_with(bug, work, implied)
            # sensitivity: only the cases every vote calls implied
            strict = limited if unanimous == implied else truth_with(bug, work, unanimous)
            row = {"task": r["task"], "model": r["model"], "rep": r["rep"], "E0": r["judge"]["E0"],
                   "truth_rebuilt": full, "truth_report": limited, "truth_report_unanimous": strict,
                   "implied_cases": len(implied), "unanimous_cases": len(unanimous), "all_cases": len(cases[r["task"]])}
            f.write(json.dumps(row) + "\n")
            print(row, flush=True)


if __name__ == "__main__":
    {"judge": judge_all, "rerun": rerun}[sys.argv[1]]()
