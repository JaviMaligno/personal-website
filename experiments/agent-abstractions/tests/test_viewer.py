"""Task 10: run viewer and status page, over hand-written transcript fixtures.

The fixtures under tests/fixtures/viewer/ mimic Claude Code `--output-format
stream-json --verbose` and `codex exec --json` output. The directory is named
`rundirs/` (not `runs/`) because `runs/` is gitignored.
"""
import json
import re
import shutil
from pathlib import Path

from aa.status import collect_results, fmt_rate, render_status, wilson, write_status
from aa.viewer import parse_transcript, render_run, write_run_view

F = Path(__file__).parent / "fixtures" / "viewer"
RUNS = F / "rundirs"
TASKS = F / "tasks"
CLAUDE_RUN = RUNS / "claude" / "AP" / "t01" / "0"
CODEX_RUN = RUNS / "codex" / "A" / "t01" / "0"


# --- transcript parsing -----------------------------------------------------

def test_parse_claude_stream_events():
    ev = parse_transcript((CLAUDE_RUN / "transcript.jsonl").read_text().splitlines())
    kinds = [e.kind for e in ev]
    assert kinds.count("tool") == 4
    assert "thinking" in kinds and "text" in kinds
    bash = next(e for e in ev if e.kind == "tool")
    assert bash.name == "Bash" and "UPDATE categories" in bash.input
    assert "index.ts:512" in bash.output and bash.turn == 1
    lint = [e for e in ev if e.kind == "tool"][-1]
    assert lint.is_error and lint.turn == 4


def test_parse_codex_stream_events():
    ev = parse_transcript((CODEX_RUN / "transcript.jsonl").read_text().splitlines())
    tools = [e for e in ev if e.kind == "tool"]
    # item.started duplicates are dropped; only completed items are shown.
    assert [t.name for t in tools] == ["command_execution", "file_change", "command_execution"]
    assert "rg -n closeCategory" in tools[0].input and "actions.ts:38" in tools[0].output
    assert "actions.ts" in tools[1].input
    assert any(e.kind == "thinking" for e in ev)
    assert any(e.kind == "text" and "domain helper" in e.text for e in ev)


def test_parse_tolerates_garbage_lines():
    ev = parse_transcript(["not json", "", '{"type":"error","message":"stream disconnected"}'])
    assert any(e.kind == "error" and "disconnected" in e.text for e in ev)
    assert any(e.kind == "raw" for e in ev)


# --- run viewer -------------------------------------------------------------

def test_render_run_claude_shows_commands_diff_and_violation():
    html = render_run(CLAUDE_RUN, tasks_dir=TASKS)
    # every tool call input is shown
    assert "rg -n &#x27;UPDATE categories&#x27; packages/loot-core/src" in html
    assert "budget/actions.ts" in html
    assert "cd packages/loot-core &amp;&amp; yarn lint" in html
    # agent diff and reference diff
    assert "db.runQuery(&#x27;UPDATE categories SET hidden = 1" in html
    assert "return categories.hide(id);" in html
    # the violating line (new-file line 40) is highlighted inside the diff
    m = re.search(r'<mark class="violation"[^>]*data-line="40"[^>]*>(.*?)</mark>', html, re.S)
    assert m and "UPDATE categories SET hidden" in m.group(1)
    # violation outside the diff is still listed
    assert "src/server/db/index.ts:512" in html
    # header facts
    assert "bad decision" in html.lower() and "7,400" in html and "91" in html
    # tool output is escaped, never raw
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    # thinking is collapsed
    assert re.search(r"<details class=\"thinking\"", html)
    # long output (the Read result) is truncated with an expander
    assert "show all" in html


def test_render_run_codex_and_missing_reference():
    html = render_run(CODEX_RUN, tasks_dir=F / "no-such-tasks")
    assert "rg -n closeCategory" in html
    assert "return hideCategory(id);" in html
    assert "no reference diff" in html.lower()
    assert '<mark class="violation"' not in html


def test_render_run_without_result_json(tmp_path):
    run = tmp_path / "claude" / "A" / "t09" / "1"
    run.mkdir(parents=True)
    shutil.copy(CLAUDE_RUN / "transcript.jsonl", run / "transcript.jsonl")
    html = render_run(run, tasks_dir=TASKS)
    assert "not evaluated" in html.lower()
    assert "rg -n" in html


def test_write_run_view_is_self_contained(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(CLAUDE_RUN, run)
    out = write_run_view(run, tasks_dir=TASKS)
    assert out == run / "view.html"
    html = out.read_text()
    assert html.startswith("<!doctype html>")
    assert "prefers-color-scheme: dark" in html and "viewport" in html
    assert not re.search(r'<(script|link)[^>]+(src|href)="https?://', html)


# --- status page ------------------------------------------------------------

def test_wilson_and_format():
    lo, hi = wilson(1, 3)
    assert round(lo, 3) == 0.061 and round(hi, 3) == 0.792
    assert wilson(0, 0) == (0.0, 0.0)
    assert fmt_rate(1, 3) == "33% [6–79]"
    assert fmt_rate(0, 0) == "–"


def test_collect_results_reads_fixture_tree():
    rows = collect_results(RUNS)
    assert len(rows) == 3
    r = next(r for r in rows if r["agent"] == "claude" and r["cond"] == "AP")
    assert r["_view"] == "claude/AP/t01/0/view.html"
    assert r["_infra_retries"] == 1  # from agent.json


def test_render_status_counts_and_wilson():
    html = render_status(collect_results(RUNS), total_per_cell=4)
    assert "1/4" in html  # done/total for each populated cell
    assert "100% [21–100]" in html  # claude AP correct 1/1, also bad decision 1/1
    assert "0% [0–79]" in html  # codex A correct 0/1
    # all eight agent x cond cells are present even when empty
    for cond in ("A", "AL", "AP", "APL"):
        assert f">{cond}<" in html
    # latest problem runs link to their viewer: claude AP (bad decision), codex A (incorrect)
    assert 'href="claude/AP/t01/0/view.html"' in html
    assert 'href="codex/A/t01/0/view.html"' in html
    assert 'href="claude/A/t01/0/view.html"' not in html
    # infra retry counter
    assert re.search(r"infra retries[^0-9]*1", html, re.I)


def test_write_status(tmp_path):
    root = tmp_path / "runs"
    shutil.copytree(RUNS, root)
    out = write_status(root, total_per_cell=4)
    assert out == root / "status.html"
    assert "prefers-color-scheme: dark" in out.read_text()


def test_status_counts_timeout_as_failure_and_infra_separately(tmp_path):
    rows = [
        {"agent": "claude", "cond": "A", "task": "t1", "pass": 0, "status": "timeout",
         "correct": True, "bad_decision": False, "tokens": {"input": 1, "output": 1}},
        {"agent": "claude", "cond": "A", "task": "t2", "pass": 0, "status": "infra"},
    ]
    html = render_status(rows, total_per_cell=2)
    assert "1/2" in html  # infra is not "done"
    assert "0% [0–79]" in html  # timeout counts as not correct
    json.dumps(rows)  # rows stay JSON-serialisable


def test_watch_single_iteration_writes_status_and_problem_views(tmp_path):
    from aa.status import watch
    root = tmp_path / "runs"
    shutil.copytree(RUNS, root)
    watch(root, interval=0, total_per_cell=4, max_iterations=1)
    assert (root / "status.html").exists()
    # problem runs get their viewer rendered so the status links resolve
    assert (root / "claude/AP/t01/0/view.html").exists()
    assert (root / "codex/A/t01/0/view.html").exists()
