import json
from pathlib import Path

from aa.memo_probe import (
    MEMORISED_THRESHOLD,
    build_prompt,
    estimate,
    extract_diff,
    mark_memorised,
    run_probe,
    similarity,
)

REF = "+++ b/a.ts\n+  const total = sumAmounts(rows);\n+  return total;\n"


def test_identical_is_one():
    assert similarity(REF, REF) == 1.0


def test_unrelated_is_low():
    assert similarity("+++ b/a.ts\n+  console.log('hi');\n", REF) < 0.2


def test_ignores_removed_lines():
    assert similarity("+++ b/a.ts\n-  const total = sumAmounts(rows);\n", REF) == 0.0


def test_empty_reference_is_zero():
    assert similarity(REF, "") == 0.0
    assert similarity("", "") == 0.0


def test_partial_overlap():
    pred = "+++ b/a.ts\n+  const total = sumAmounts(items);\n"
    # pred {const,total,sumAmounts,items} vs ref {const,total,sumAmounts,rows,return}
    assert similarity(pred, REF) == 3 / 6


def test_string_literals_are_tokens():
    a = "+  fn('ab cd');\n"
    b = "+  fn('ab');\n"
    assert similarity(a, b) == 1 / 3  # {fn,'ab cd'} vs {fn,'ab'}


def test_extract_diff_prefers_fenced_blocks():
    text = "Here it is:\n```diff\n+++ b/a.ts\n+  return total;\n```\n+ not part of diff\n"
    assert extract_diff(text) == "+++ b/a.ts\n+  return total;\n"


def test_extract_diff_falls_back_to_whole_text():
    assert extract_diff(REF) == REF


def test_prompt_contains_statement_and_files():
    p = build_prompt("Budgets should roll over.", ["packages/loot-core/src/a.ts", "packages/loot-core/src/b.ts"])
    assert "actualbudget/actual (packages/loot-core)" in p
    assert "Without access to the repository" in p
    assert "Budgets should roll over." in p
    assert "packages/loot-core/src/a.ts, packages/loot-core/src/b.ts" in p


def test_estimate_mentions_calls():
    s = estimate(10)
    assert "10 tasks x 2 agents = 20 calls" in s


def _task(tasks_dir: Path, tid: str) -> dict:
    d = tasks_dir / tid
    d.mkdir(parents=True)
    (d / "statement.md").write_text(f"statement {tid}\n")
    return {"id": tid, "dir": d, "touched_files": ["packages/loot-core/src/a.ts"]}


def test_run_probe_writes_memo_and_marks_ledger(tmp_path):
    tasks_dir = tmp_path / "tasks"
    t1, t2 = _task(tasks_dir, "t1"), _task(tasks_dir, "t2")
    (tasks_dir / "_ledger.json").write_text(json.dumps({"t1": {"status": "kept"}, "t2": {"status": "kept"}}))
    refs = {"t1": REF, "t2": REF}
    seen_prompts = []

    def fake_call(agent, prompt, raw_path):
        seen_prompts.append(prompt)
        # claude reproduces t1; nobody reproduces t2
        text = REF if (agent == "claude" and "statement t1" in prompt) else "+  console.log('no');\n"
        raw_path.write_text(text)
        return text

    out = run_probe([t1, t2], reference=lambda t: refs[t["id"]], call=fake_call,
                    raw_dir=tmp_path / "raw", tasks_dir=tasks_dir, workers=2)

    assert len(seen_prompts) == 4
    m1 = json.loads((tasks_dir / "t1" / "memo.json").read_text())
    assert m1["claude"]["similarity"] == 1.0
    assert m1["codex"]["similarity"] < MEMORISED_THRESHOLD
    assert Path(m1["claude"]["raw"]).exists()
    assert out == {"t1": True, "t2": False}
    ledger = json.loads((tasks_dir / "_ledger.json").read_text())
    assert ledger["t1"]["memorised"] is True
    assert ledger["t2"]["memorised"] is False
    assert ledger["t1"]["status"] == "kept"  # other fields untouched


def test_run_probe_call_failure_is_recorded_not_fatal(tmp_path):
    tasks_dir = tmp_path / "tasks"
    t1 = _task(tasks_dir, "t1")

    calls, sleeps = [], []

    def failing(agent, prompt, raw_path):
        calls.append(agent)
        raise RuntimeError("usage limit")

    out = run_probe([t1], reference=lambda t: REF, call=failing,
                    raw_dir=tmp_path / "raw", tasks_dir=tasks_dir, workers=1,
                    sleep=sleeps.append, max_infra_retries=3)
    m1 = json.loads((tasks_dir / "t1" / "memo.json").read_text())
    assert m1["claude"]["similarity"] is None
    assert "usage limit" in m1["claude"]["error"]
    assert m1["claude"]["infra_retries"] == 3
    assert calls.count("claude") == 4  # first try + 3 infra retries
    assert sleeps[:3] == [60, 120, 240]
    assert out == {"t1": None}  # undecided: must be re-run, never silently kept


def test_run_probe_retries_infra_then_succeeds(tmp_path):
    tasks_dir = tmp_path / "tasks"
    t1 = _task(tasks_dir, "t1")
    n = {"claude": 0, "codex": 0}

    def flaky(agent, prompt, raw_path):
        n[agent] += 1
        if n[agent] == 1:
            raise RuntimeError("429 Too Many Requests: rate limit exceeded")
        raw_path.write_text(REF)
        return REF

    sleeps = []
    out = run_probe([t1], reference=lambda t: REF, call=flaky,
                    raw_dir=tmp_path / "raw", tasks_dir=tasks_dir, workers=1, sleep=sleeps.append)
    m1 = json.loads((tasks_dir / "t1" / "memo.json").read_text())
    assert m1["claude"]["similarity"] == 1.0 and m1["claude"]["infra_retries"] == 1
    assert "error" not in m1["claude"]
    assert out == {"t1": True}
    assert sleeps == [60, 60]


def test_run_probe_non_infra_error_is_not_retried(tmp_path):
    tasks_dir = tmp_path / "tasks"
    t1 = _task(tasks_dir, "t1")
    calls = []

    def broken(agent, prompt, raw_path):
        calls.append(agent)
        raise RuntimeError("json decode error")

    out = run_probe([t1], reference=lambda t: REF, call=broken,
                    raw_dir=tmp_path / "raw", tasks_dir=tasks_dir, workers=1,
                    sleep=lambda s: None)
    assert len(calls) == 2 and out == {"t1": None}


def test_mark_memorised_list_ledger(tmp_path):
    p = tmp_path / "_ledger.json"
    p.write_text(json.dumps([{"id": "t1"}, {"id": "t2"}]))
    mark_memorised(p, {"t1": True})
    assert json.loads(p.read_text()) == [{"id": "t1", "memorised": True}, {"id": "t2"}]


def test_mark_memorised_missing_ledger_creates_it(tmp_path):
    p = tmp_path / "_ledger.json"
    mark_memorised(p, {"t1": False})
    assert json.loads(p.read_text()) == {"t1": {"memorised": False}}


def test_probe_runs_in_repo_free_container(tmp_path):
    from aa import memo_probe
    a = memo_probe.probe_docker_argv("claude", tmp_path / "out")
    s = " ".join(a)
    assert a[:4] == ["docker", "run", "--rm", "-i"] and memo_probe.PROBE_IMAGE in a
    assert "/work/actual" not in s and "actual-base" not in s
    mounts = [a[i + 1] for i, x in enumerate(a) if x == "-v"]
    assert mounts == [f"{tmp_path / 'out'}:/out"]
    assert "CLAUDE_CODE_OAUTH_TOKEN" in a and "CLAUDE_CONFIG_DIR=/tmp/cc" in a
    assert "cd /tmp/empty" in a[-1] and "--output-format json" in a[-1]
    c = memo_probe.probe_docker_argv("codex", tmp_path / "out", tmp_path / "auth")
    assert [c[i + 1] for i, x in enumerate(c) if x == "-v"] == [
        f"{tmp_path / 'out'}:/out", f"{tmp_path / 'auth'}:/codex-auth:ro"]
    assert "--skip-git-repo-check" in c[-1] and "cd /tmp/empty" in c[-1]


def test_answer_without_diff_is_retried_then_undecided(tmp_path):
    tasks_dir = tmp_path / "tasks"
    t1 = _task(tasks_dir, "t1")
    calls = []

    def refuses(agent, prompt, raw_path):
        calls.append(agent)
        raw_path.write_text("I can't inspect the repository here.")
        return "I can't inspect the repository here."

    out = run_probe([t1], reference=lambda t: REF, call=refuses,
                    raw_dir=tmp_path / "raw", tasks_dir=tasks_dir, workers=1, sleep=lambda s: None)
    m1 = json.loads((tasks_dir / "t1" / "memo.json").read_text())
    assert m1["codex"]["similarity"] is None and "no diff" in m1["codex"]["error"]
    assert calls.count("codex") == 3  # first try + 2 retries; a refusal never scores 0.0
    assert out == {"t1": None}
    assert (tmp_path / "raw" / "t1.codex.nodiff1.txt").exists()


def test_only_reprobes_selected_entries_and_merges(tmp_path):
    tasks_dir = tmp_path / "tasks"
    t1 = _task(tasks_dir, "t1")
    (tasks_dir / "t1" / "memo.json").write_text(json.dumps({
        "claude": {"similarity": 0.1, "raw": "x"},
        "codex": {"similarity": None, "raw": "y", "error": "no diff in answer"}}))
    calls = []

    def fake(agent, prompt, raw_path):
        calls.append(agent)
        raw_path.write_text(REF)
        return REF

    out = run_probe([t1], reference=lambda t: REF, call=fake, raw_dir=tmp_path / "raw",
                    tasks_dir=tasks_dir, workers=1, only={("t1", "codex")})
    assert calls == ["codex"]
    m1 = json.loads((tasks_dir / "t1" / "memo.json").read_text())
    assert m1["claude"] == {"similarity": 0.1, "raw": "x"}
    assert m1["codex"]["similarity"] == 1.0
    assert out == {"t1": True}


def test_missing_entries(tmp_path):
    from aa.memo_probe import missing_entries
    tasks_dir = tmp_path / "tasks"
    t1, t2 = _task(tasks_dir, "t1"), _task(tasks_dir, "t2")
    (tasks_dir / "t1" / "memo.json").write_text(json.dumps({
        "claude": {"similarity": 0.1}, "codex": {"similarity": None}}))
    assert missing_entries([t1, t2], tasks_dir) == {("t1", "codex"), ("t2", "claude"), ("t2", "codex")}


def test_probe_disables_web_and_tools(tmp_path):
    from aa import memo_probe
    cl = memo_probe.probe_docker_argv("claude", tmp_path / "out")[-1]
    assert '--tools ""' in cl
    cx = memo_probe.probe_docker_argv("codex", tmp_path / "out", tmp_path / "auth")[-1]
    assert "-c web_search=disabled" in cx and "--strict-config" in cx
    assert "--disable shell_tool" in cx


def test_tool_use_detected_in_raw_output():
    from aa.memo_probe import codex_tool_use, claude_tool_use
    assert codex_tool_use("codex\nhi\nweb search: \nweb search: https://github.com/x\n")
    assert codex_tool_use("exec\n/bin/bash -lc 'rg x' in /tmp/empty\n")
    assert not codex_tool_use("codex\nhere is the diff\n")
    assert claude_tool_use({"num_turns": 1, "usage": {"server_tool_use": {"web_search_requests": 1}}})
    assert claude_tool_use({"num_turns": 3, "usage": {}})
    assert not claude_tool_use({"num_turns": 1, "usage": {"server_tool_use": {
        "web_search_requests": 0, "web_fetch_requests": 0}}})


def test_reference_diff_of_issue_task_reads_reference_a_without_tests(tmp_path):
    from aa.memo_probe import reference_diff
    d = tmp_path / "issue-1"
    d.mkdir()
    (d / "reference.A.patch").write_text(
        "diff --git a/src/x.ts b/src/x.ts\n--- a/src/x.ts\n+++ b/src/x.ts\n@@ -1 +1 @@\n+keepMe();\n"
        "diff --git a/src/x.test.ts b/src/x.test.ts\n--- a/src/x.test.ts\n+++ b/src/x.test.ts\n"
        "@@ -1 +1 @@\n+dropMe();\n")
    ref = reference_diff({"id": "issue-1", "sha": "", "dir": d, "hidden_tests": []})
    assert "keepMe" in ref and "dropMe" not in ref
