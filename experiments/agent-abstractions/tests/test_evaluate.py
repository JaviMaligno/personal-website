import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from aa import evaluate
from aa.evaluate import (assemble_result, diff_stats, eval_docker_argv, eval_script, evaluate_all,
                         evaluate_run, extract_trace)

HIDDEN = "packages/loot-core/src/server/budget/a.test.ts"
LOOT_C = "/work/actual/packages/loot-core"

DIFF_CLEAN = """\
diff --git a/packages/loot-core/src/server/budget/a.ts b/packages/loot-core/src/server/budget/a.ts
--- a/packages/loot-core/src/server/budget/a.ts
+++ b/packages/loot-core/src/server/budget/a.ts
@@ -1,2 +1,3 @@
 export function f(x) {
+  return amountToInteger(x);
 }
"""

DIFF_FLOAT = """\
diff --git a/packages/loot-core/src/server/budget/a.ts b/packages/loot-core/src/server/budget/a.ts
--- a/packages/loot-core/src/server/budget/a.ts
+++ b/packages/loot-core/src/server/budget/a.ts
@@ -1,2 +1,3 @@
 export function f(amount) {
+  return amount * 100;
 }
"""

DIFF_RAW = """\
diff --git a/packages/loot-core/src/server/budget/a.ts b/packages/loot-core/src/server/budget/a.ts
--- a/packages/loot-core/src/server/budget/a.ts
+++ b/packages/loot-core/src/server/budget/a.ts
@@ -1,2 +1,3 @@
 export async function hide(id) {
+  await db.runQuery('UPDATE categories SET hidden = 1 WHERE id = ?', [id]);
 }
"""


def report(status="passed", name="src/server/budget/a.test.ts", load_fail=False):
    if load_fail:
        return {"testResults": [{"name": f"{LOOT_C}/{name}", "status": "failed", "assertionResults": []}]}
    return {"testResults": [{"name": f"{LOOT_C}/{name}", "status": status,
                             "assertionResults": [{"fullName": "a works", "status": status}]}]}


def make_task(root: Path, task_id="t01", hidden=(HIDDEN,)) -> Path:
    d = root / task_id
    d.mkdir(parents=True)
    (d / "task.json").write_text(json.dumps({
        "id": task_id, "hidden_tests": list(hidden),
        "per_condition": {c: {"revert_patch": f"revert.{c}.patch"} for c in ("A", "AL", "AP", "APL")},
    }))
    for c in ("A", "AL", "AP", "APL"):
        (d / f"revert.{c}.patch").write_text("")
    return d


def make_run(root: Path, cond="A", status="ok", diff=DIFF_CLEAN, transcript="", agent="claude") -> Path:
    d = root / "runs" / agent / cond / "t01" / "0"
    d.mkdir(parents=True)
    (d / "agent.json").write_text(json.dumps({
        "agent": agent, "cond": cond, "task": "t01", "pass": 0, "status": status,
        "usage": {"input_tokens": 100, "output_tokens": 20, "cached_input_tokens": 50, "turns": 7, "tool_calls": 5},
        "wall_s": 61.5,
    }))
    (d / "diff.patch").write_text(diff)
    (d / "transcript.jsonl").write_text(transcript)
    return d


def fake_executor(rep=None, probe=(), lint_rc=0, tc_rc=0, eval_error=None, done=True, calls=None,
                  clean_done=True, probe_rc=0, probe_rep="same"):
    def run(argv, timeout):
        if calls is not None:
            calls.append(argv)
        out = Path(next(a.split(":")[0] for a in argv if a.endswith(":/out")))
        if eval_error:
            (out / "eval_error").write_text(eval_error + "\n")
            return 0
        (out / "lint_rc").write_text(f"{lint_rc}\n")
        (out / "typecheck_rc").write_text(f"{tc_rc}\n")
        if rep is not None:
            (out / "report.json").write_text(json.dumps(rep))
        if clean_done:
            (out / "clean_done").write_text("done\n")
        prep = rep if probe_rep == "same" else probe_rep
        if prep is not None:
            (out / "probe_report.json").write_text(json.dumps(prep))
        if probe_rc is not None:
            (out / "vitest_probe_rc").write_text(f"{probe_rc}\n")
        if probe:
            (out / "probe.jsonl").write_text("".join(json.dumps(e) + "\n" for e in probe))
        if done:
            (out / "eval_done").write_text("done\n")
        return 0
    return run


@pytest.fixture
def env(tmp_path):
    make_task(tmp_path / "tasks")
    return tmp_path


def ev(run, env, **kw):
    return evaluate_run(run, tasks_root=env / "tasks", execute=fake_executor(**kw))


# --- plan Step 1 cases -------------------------------------------------------------------

def test_a_pass_no_violations(env):
    r = ev(make_run(env), env, rep=report())
    assert r["correct"] is True and r["bad_decision"] is False and r["violations"] == []
    assert r["lint_ok"] is True and r["typecheck_ok"] is True and r["eval_error"] is None
    on_disk = json.loads((env / "runs/claude/A/t01/0/result.json").read_text())
    assert on_disk == r
    for k in ("agent", "cond", "task", "pass", "status", "correct", "violations", "bad_decision",
              "bad_decision_hidden_only", "lint_ok", "typecheck_ok", "tokens", "turns", "tool_calls",
              "wall_s", "diff", "reimplementation", "trace", "contamination_flag"):
        assert k in r, k
    assert r["tokens"] == {"input": 100, "output": 20, "cached_input": 50}
    assert (r["turns"], r["tool_calls"], r["wall_s"]) == (7, 5, 61.5)
    assert r["diff"] == {"files": 1, "added": 1, "removed": 0}
    assert r["probe_incomplete"] is False


# --- two-pass rule (spec section 6): the probe never decides correctness ----------------------

RAW_EVENT = {"kind": "raw_write", "table": "categories",
             "sql": "UPDATE categories SET hidden = 1 WHERE id = ?",
             "caller": "src/server/budget/a.ts:2"}


def test_probe_pass_timeout_keeps_clean_correctness_and_violations(env):
    r = ev(make_run(env, diff=DIFF_RAW), env, rep=report(), probe=[RAW_EVENT], probe_rc=124,
           probe_rep=None)
    assert r["correct"] is True and r["eval_error"] is None
    assert r["probe_incomplete"] is True
    assert any(v["kind"] == "raw_write" for v in r["violations"]) and r["bad_decision"]


def test_probe_induced_failure_does_not_change_correctness(env):
    r = ev(make_run(env), env, rep=report(), probe_rep=report(status="failed"), probe_rc=1)
    assert r["correct"] is True and r["probe_incomplete"] is True


def test_failure_in_both_passes_is_not_probe_incomplete(env):
    r = ev(make_run(env), env, rep=report(status="failed"), probe_rc=1)
    assert r["correct"] is False and r["probe_incomplete"] is False


def test_container_dies_during_probe_pass(env):
    r = ev(make_run(env), env, rep=report(), done=False, probe_rc=None, probe_rep=None)
    assert r["eval_error"] is None and r["correct"] is True and r["probe_incomplete"] is True


def test_container_dies_before_clean_pass_finishes(env):
    r = ev(make_run(env), env, rep=None, done=False, clean_done=False, probe_rc=None,
           probe_rep=None)
    assert r["eval_error"] == "container" and r["correct"] is False


def test_host_timeout_after_clean_pass(env, tmp_path):
    def run(argv, timeout):
        fake_executor(rep=report(), done=False, probe_rc=None, probe_rep=None)(argv, timeout)
        raise subprocess.TimeoutExpired(argv, timeout)
    r = evaluate_run(make_run(env), tasks_root=env / "tasks", execute=run)
    assert r["eval_error"] is None and r["correct"] is True and r["probe_incomplete"] is True


def test_b_pass_with_float_money_is_bad_decision(env):
    r = ev(make_run(env, cond="A", diff=DIFF_FLOAT), env, rep=report())
    assert r["correct"] and r["bad_decision"]
    assert [(v["kind"], v["lint_visible"]) for v in r["violations"]] == [("float_money_math", False)]
    assert r["bad_decision_hidden_only"] is True
    assert r["reimplementation"] is True


def test_b_lint_visible_violation_not_hidden_only(env):
    # In AL the visible lint flags `amount * 100` -> counts in bad_decision, not in hidden_only.
    r = ev(make_run(env, cond="AL", diff=DIFF_FLOAT), env, rep=report())
    assert r["bad_decision"] is True and r["bad_decision_hidden_only"] is False
    assert r["violations"][0]["lint_visible"] is True


def test_c_uncompilable_tree_still_writes_result(env):
    run = make_run(env, diff=DIFF_FLOAT)
    r = ev(run, env, rep=report(load_fail=True), lint_rc=1, tc_rc=2)
    assert r["correct"] is False and r["bad_decision"] is False
    assert r["lint_ok"] is False and r["typecheck_ok"] is False
    assert "src/server/budget/a.test.ts::<load>" in r["hidden"]["failed_tests"]
    assert [v["kind"] for v in r["violations"]] == ["float_money_math"]  # checker results still there
    assert (run / "result.json").exists()


def test_c_no_report_and_dead_container(env):
    r = ev(make_run(env), env, rep=None, done=False, clean_done=False, probe_rc=None)
    assert r["correct"] is False and r["eval_error"] == "container"
    assert r["hidden"]["failed_tests"] == ["<no report>"]


def test_c_executor_crash_or_timeout_still_writes_result(env):
    def boom(argv, timeout):
        raise FileNotFoundError("docker")
    run = make_run(env)
    r = evaluate_run(run, tasks_root=env / "tasks", execute=boom)
    assert r["correct"] is False and r["eval_error"] == "container"
    assert (run / "result.json").exists()

    def slow(argv, timeout):
        raise subprocess.TimeoutExpired(argv, timeout)
    r = evaluate_run(run, tasks_root=env / "tasks", execute=slow)
    assert r["correct"] is False and r["eval_error"] == "eval_timeout"


def test_diff_apply_failure(env):
    r = ev(make_run(env, diff=DIFF_FLOAT), env, eval_error="diff_apply")
    assert r["correct"] is False and r["eval_error"] == "diff_apply" and r["violations"] == []
    assert r["lint_ok"] is None


def test_hidden_file_missing_from_report_is_incorrect(env):
    r = ev(make_run(env), env, rep=report(name="src/server/other.test.ts"))
    assert r["correct"] is False and r["hidden"]["missing_files"] == [HIDDEN]


def test_e_timeout_is_still_evaluated(env):
    r = ev(make_run(env, status="timeout", diff=DIFF_FLOAT), env, rep=report())
    assert r["status"] == "timeout" and r["correct"] is True  # analysis excludes it via status
    assert r["violations"]


# --- statuses ------------------------------------------------------------------------------

@pytest.mark.parametrize("status", ["setup_error", "infra_exhausted"])
def test_final_unevaluated_status_passthrough(env, status):
    calls = []
    run = make_run(env, status=status)
    r = evaluate_run(run, tasks_root=env / "tasks", execute=fake_executor(calls=calls))
    assert calls == [] and r["status"] == status and r["correct"] is False
    assert r["eval_error"] == "not_evaluated" and (run / "result.json").exists()


def test_infra_is_not_final_no_result(env):
    run = make_run(env, status="infra")
    assert ev(run, env, rep=report()) is None and not (run / "result.json").exists()


def test_missing_task_or_condition_is_recorded(env):
    run = make_run(env, cond="AP")
    tj = env / "tasks/t01/task.json"
    meta = json.loads(tj.read_text())
    del meta["per_condition"]["AP"]
    tj.write_text(json.dumps(meta))
    r = ev(run, env, rep=report())
    assert r["correct"] is False and r["eval_error"].startswith("setup:KeyError")


def test_task_without_hidden_tests_never_runs_full_suite(tmp_path):
    make_task(tmp_path / "tasks", hidden=())
    calls = []
    r = evaluate_run(make_run(tmp_path), tasks_root=tmp_path / "tasks", execute=fake_executor(calls=calls))
    assert calls == [] and r["correct"] is False and "no hidden_tests" in r["eval_error"]


# --- probe events through the evaluator (finding 4) -----------------------------------

def test_raw_write_on_agent_line_counts_base_writer_does_not(env):
    probe = [
        {"kind": "raw_write", "table": "categories", "sql": "UPDATE categories SET hidden = 1 WHERE id = ?",
         "caller": "src/server/budget/a.ts:2"},  # the agent's added line
        {"kind": "raw_write", "table": "transactions", "sql": "UPDATE transactions SET x",
         "caller": "src/server/transactions/old.ts:40"},  # base writer
    ]
    r = ev(make_run(env, cond="AL", diff=DIFF_RAW), env, rep=report(), probe=probe)
    assert [(v["kind"], v["file"], v["line"], v["lint_visible"]) for v in r["violations"]] == [
        ("raw_write", "packages/loot-core/src/server/budget/a.ts", 2, True)]
    assert r["bad_decision"] and not r["bad_decision_hidden_only"]


# --- contamination (finding 8) ---------------------------------------------------------------

def test_contamination_flag_from_agents(env, monkeypatch):
    import aa.agents
    monkeypatch.setattr(aa.agents, "detect_contamination",
                        lambda agent, lines, refs=(): ["github.com/actualbudget"]
                        if any("github.com/actualbudget" in ln for ln in lines) else [], raising=False)
    tr = json.dumps({"type": "assistant", "message": {"id": "m1", "content": [
        {"type": "tool_use", "id": "t1", "name": "Bash",
         "input": {"command": "curl https://github.com/actualbudget/actual/pull/1"}}]}}) + "\n"
    r = ev(make_run(env, transcript=tr), env, rep=report())
    assert r["contamination_flag"] is True and r["contamination_markers"] == ["github.com/actualbudget"]
    assert ev(make_run(env, cond="AL"), env, rep=report())["contamination_flag"] is False


def test_contamination_with_real_detector(env):
    # whatever aa.agents implements, a clone of upstream in a Bash call must be flagged
    tr = json.dumps({"type": "assistant", "message": {"id": "m1", "content": [
        {"type": "tool_use", "id": "t1", "name": "Bash",
         "input": {"command": "git clone https://github.com/actualbudget/actual /tmp/a"}}]}}) + "\n"
    r = ev(make_run(env, transcript=tr), env, rep=report())
    assert r["contamination_flag"] is True


def test_contamination_defaults_false_without_detector(monkeypatch):
    import aa.agents
    monkeypatch.delattr(aa.agents, "detect_contamination", raising=False)
    assert evaluate.contamination("claude", ["git clone https://github.com/actualbudget/actual"]) == []


def test_contamination_task_ref_from_task_json(env):
    # the task's PR number (subject "... (#8392)") in a Bash command is flagged
    tr = json.dumps({"type": "assistant", "message": {"id": "m1", "content": [
        {"type": "tool_use", "id": "t1", "name": "Bash",
         "input": {"command": "gh pr view 8392"}}]}}) + "\n"
    task = json.loads((env / "tasks" / "t01" / "task.json").read_text())
    task["subject"] = "Fix things (#8392)"
    (env / "tasks" / "t01" / "task.json").write_text(json.dumps(task))
    r = ev(make_run(env, transcript=tr), env, rep=report())
    assert r["contamination_markers"] == ["ref:#8392"]


# --- per-task fields ---------------------------------------------------------------------------

def test_task_fields_mined_and_issue():
    mined = evaluate.task_fields({"id": "abc", "ai_label": True})
    assert mined == {"source": "mined", "ai_label": True, "contaminated": False,
                     "contaminated_reasons": []}
    issue = {"id": "issue-1", "kind": "issue", "ai_label": False, "public_fix_pr": False}
    f = evaluate.task_fields(issue, ledger_entry={"memo_codex": 0.3, "memo_claude": "pending"})
    assert f["source"] == "issue" and f["ai_label"] is None
    assert f["contaminated"] is True and f["contaminated_reasons"] == ["memo_codex>=0.25"]
    # pending Claude value does not count; below threshold does not count
    f = evaluate.task_fields(issue, ledger_entry={"memo_codex": 0.2, "memo_claude": "pending"},
                             memo={"claude": {"similarity": None}})
    assert f["contaminated"] is False
    f = evaluate.task_fields({**issue, "public_fix_pr": True}, memo={"claude": {"similarity": 0.25}},
                             contamination_flag=True)
    assert f["contaminated_reasons"] == ["public_fix_pr", "memo_claude>=0.25", "contamination_flag"]
    # public_fix_pr only counts on issue tasks
    assert evaluate.task_fields({"ai_label": False, "public_fix_pr": True})["contaminated"] is False


def test_task_fields_reach_result_json(env):
    tasks = env / "tasks"
    t = json.loads((tasks / "t01" / "task.json").read_text())
    t.update({"kind": "issue", "ai_label": None, "public_fix_pr": False})
    (tasks / "t01" / "task.json").write_text(json.dumps(t))
    (tasks / "_ledger.json").write_text(json.dumps({"t01": {"source": "issue", "memo_codex": 0.1,
                                                            "memo_claude": "pending"}}))
    (tasks / "t01" / "memo.json").write_text(json.dumps({"codex": {"similarity": 0.4}}))
    r = ev(make_run(env), env, rep=report())
    assert (r["source"], r["ai_label"], r["contaminated"]) == ("issue", None, True)
    assert r["contaminated_reasons"] == ["memo_codex>=0.25"]
    # also on runs that are not evaluated
    r = ev(make_run(env, cond="AL", status="setup_error"), env)
    assert r["source"] == "issue" and r["contaminated"] is True


# --- test infra ------------------------------------------------------------------------------

def test_eval_script_restores_test_infra_before_both_passes():
    s = eval_script("revert.AP.patch", [HIDDEN])
    i_infra = s.index("for p in packages/loot-core/vitest.config.ts "
                      "packages/loot-core/vitest.web.config.ts packages/loot-core/src/mocks "
                      "packages/loot-core/src/server/tests;")
    assert 'rm -rf "$p" && git checkout HEAD -- "$p"' in s
    assert s.index("yarn tsgo -b") < i_infra < s.index("yarn vitest")
    assert "test_infra_restore" in s
    i_mocks = s.index("-type d -name __mocks__")
    assert "git ls-tree -r --name-only HEAD -- packages/loot-core" in s
    assert s.index("yarn tsgo -b") < i_mocks < s.index("yarn vitest")


def test_agent_touched_test_infra_flag(env):
    diff = ("diff --git a/packages/loot-core/src/mocks/budget.ts b/packages/loot-core/src/mocks/budget.ts\n"
            "--- a/packages/loot-core/src/mocks/budget.ts\n+++ b/packages/loot-core/src/mocks/budget.ts\n"
            "@@ -1 +1 @@\n-a\n+b\n")
    assert evaluate.touches_test_infra(diff)
    assert evaluate.touches_test_infra(diff.replace("src/mocks/budget.ts", "vitest.web.config.ts"))
    assert not evaluate.touches_test_infra(diff.replace("src/mocks/", "src/server/"))
    assert not evaluate.touches_test_infra(diff.replace("src/mocks/", "src/mocksx/"))
    assert evaluate.touches_test_infra(diff.replace("src/mocks/budget.ts", "src/server/tests/mockSyncServer.ts"))
    assert evaluate.touches_test_infra(diff.replace("src/mocks/budget.ts",
                                                    "src/platform/server/fetch/__mocks__/index.ts"))
    assert evaluate.touches_test_infra(diff.replace("src/mocks/budget.ts", "src/server/__mocks__/new.ts"))
    assert not evaluate.touches_test_infra(diff.replace("packages/loot-core/src/mocks/budget.ts",
                                                        "packages/desktop-client/src/__mocks__/x.ts"))
    assert not evaluate.touches_test_infra(diff.replace("src/mocks/", "src/server/testsx/"))
    assert ev(make_run(env, diff=diff), env, rep=report())["agent_touched_test_infra"] is True
    assert ev(make_run(env, cond="AL"), env, rep=report())["agent_touched_test_infra"] is False


# --- container script ------------------------------------------------------------------------

def test_eval_script_order_and_contents():
    s = eval_script("revert.AP.patch", [HIDDEN])
    i_rev = s.index("/task/revert.AP.patch")
    i_diff = s.index("/agentrun/diff.patch")
    i_restore = s.index(f"git checkout HEAD -- {HIDDEN}")
    i_lint = s.index("yarn lint")
    i_tc = s.index("yarn tsgo -b")
    i_clean = s.index("yarn vitest")
    i_clean_done = s.index("/out/clean_done")
    i_probe = s.index("cp /checker/probe.setup.ts")
    i_probed = s.index("yarn vitest", i_probe)
    assert i_rev < i_diff < i_restore < i_lint < i_tc < i_clean < i_clean_done < i_probe < i_probed
    clean_line = s[s.rindex("\n", 0, i_clean):s.index("\n", i_clean)]
    assert "--config vitest.aa-seed.config.ts" in clean_line and "AA_PROBE_OUT" not in clean_line
    i_seed = s.index("cp /checker/seed.setup.ts src/mocks/aa-seed.setup.ts")
    assert i_tc < i_seed < i_clean and "cp /checker/vitest.aa-seed.config.ts" in s
    assert "--testTimeout" not in clean_line and "/out/report.json" in clean_line
    probe_line = s[s.rindex("\n", 0, i_probed):s.index("\n", i_probed)]
    assert "--config vitest.aa.config.ts" in probe_line and "--setupFiles" not in s
    assert "AA_PROBE_OUT=/out/probe.jsonl" in probe_line and "/out/probe_report.json" in probe_line
    assert "--testTimeout=50000" in probe_line and "--hookTimeout=100000" in probe_line
    assert "src/server/budget/a.test.ts" in clean_line and "src/server/budget/a.test.ts" in probe_line


def test_eval_docker_argv(tmp_path):
    argv = eval_docker_argv("APL", tmp_path / "runs/claude/APL/t01/0", tmp_path / "tasks/t01",
                            tmp_path / "out", "echo hi", checker_dir=tmp_path / "checker")
    assert argv[argv.index("--network") + 1] == "none"
    assert f"{tmp_path}/tasks/t01:/task:ro" in argv and f"{tmp_path}/checker:/checker:ro" in argv
    assert f"{tmp_path}/runs/claude/APL/t01/0:/agentrun:ro" in argv and f"{tmp_path}/out:/out" in argv
    assert "aa-actual:APL" in argv and argv[-1] == "echo hi"
    assert re.fullmatch(r"[\w.-]+", argv[argv.index("--name") + 1])


def _exe(p: Path, body: str) -> None:
    p.write_text(body)
    p.chmod(p.stat().st_mode | stat.S_IEXEC)


FAKE_YARN = """#!/bin/bash
case "$1" in
  lint) [ -e src/mocks/aa-probe.setup.ts ] || [ -e src/mocks/aa-seed.setup.ts ] && exit 3; exit 0;;
  tsgo) exit 0;;
  vitest)
    for a in "$@"; do case $a in --outputFile=*) OUT=${a#--outputFile=};; esac; done
    if grep -q ORIGINAL src/server/budget/a.test.ts 2>/dev/null; then st=passed; else st=failed; fi
    # both passes are seeded; the clean pass must run without the probe, the probe pass with it
    [ -e vitest.aa-seed.config.ts ] && [ -e src/mocks/aa-seed.setup.ts ] || st=failed
    if [[ " $* " == *" --config vitest.aa.config.ts "* ]]; then
      [ -e vitest.aa.config.ts ] && [ -e src/mocks/aa-probe.setup.ts ] || st=failed
    else
      [ -e vitest.aa.config.ts ] || [ -e src/mocks/aa-probe.setup.ts ] && st=failed
    fi
    printf '{"testResults":[{"name":"/work/actual/packages/loot-core/src/server/budget/a.test.ts","status":"%s","assertionResults":[{"fullName":"a works","status":"%s"}]}]}' $st $st > "$OUT"
    exit 0;;
esac
exit 9
"""


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_d_real_script_restores_deleted_hidden_test(tmp_path):
    """Run eval_script for real (git + bash; yarn/timeout stubbed): the agent's diff
    deletes the hidden test, the evaluator restores it from HEAD -> tests pass."""
    repo = tmp_path / "actual"
    loot = repo / "packages/loot-core"
    (loot / "src/server/budget").mkdir(parents=True)
    (loot / "src/mocks").mkdir(parents=True)
    (loot / "src/server/budget/a.ts").write_text("export const a = 1;\n")
    (loot / "src/server/budget/a.test.ts").write_text("// ORIGINAL hidden test\n")
    (loot / "src/mocks/.keep").write_text("")

    def git(*a, cwd=repo):
        return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout

    git("init", "-q")
    git("-c", "user.email=a@b", "-c", "user.name=a", "add", "-A")
    git("-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "variant")
    # task revert: changes the source and the hidden test
    (loot / "src/server/budget/a.ts").write_text("export const a = 0;\n")
    (loot / "src/server/budget/a.test.ts").write_text("// REVERTED\n")
    revert = git("diff")
    git("add", "-A")
    # agent: fixes the source and deletes the hidden test file
    (loot / "src/server/budget/a.ts").write_text("export const a = 1;\n")
    (loot / "src/server/budget/a.test.ts").unlink()
    agent_diff = git("diff")
    git("reset", "-q", "--hard", "HEAD")  # back to the untouched variant (image state)

    task_dir, run_dir, out = tmp_path / "task", tmp_path / "run", tmp_path / "out"
    for d in (task_dir, run_dir, out):
        d.mkdir()
    (task_dir / "revert.A.patch").write_text(revert)
    (run_dir / "diff.patch").write_text(agent_diff)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _exe(bin_dir / "yarn", FAKE_YARN)
    _exe(bin_dir / "timeout", '#!/bin/bash\nshift\nexec "$@"\n')

    mounts = {"/work/actual": str(repo), "/task/": f"{task_dir}/", "/agentrun/": f"{run_dir}/",
              "/checker/": f"{evaluate.PROBE_SRC.parent}/", "/out/": f"{out}/"}
    script = re.sub("|".join(re.escape(k) for k in mounts), lambda m: mounts[m.group(0)],
                    eval_script("revert.A.patch", [HIDDEN]))
    proc = subprocess.run(["bash", "-c", script], env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert not (out / "eval_error").exists(), (out / "apply.log").read_text()
    assert (out / "lint_rc").read_text().strip() == "0"  # lint ran before the probe was copied in
    assert (loot / "src/server/budget/a.test.ts").read_text() == "// ORIGINAL hidden test\n"

    meta = {"agent": "claude", "cond": "A", "task": "t01", "pass": 0, "status": "ok", "usage": {}}
    r = assemble_result(meta, {"hidden_tests": [HIDDEN]}, agent_diff, out, [])
    assert r["correct"] is True and r["eval_error"] is None and r["lint_ok"] and r["typecheck_ok"]
    assert r["probe_incomplete"] is False
    assert json.loads((out / "probe_report.json").read_text())["testResults"][0]["status"] == "passed"


def test_real_script_restores_test_infra(tmp_path):
    """Real git + bash: the agent's diff edits vitest.config.ts and a mock and adds a
    mock file; both passes run on the HEAD versions, lint saw the agent's tree."""
    repo = tmp_path / "actual"
    loot = repo / "packages/loot-core"
    (loot / "src/server/budget").mkdir(parents=True)
    (loot / "src/mocks").mkdir(parents=True)
    (loot / "src/server/budget/a.ts").write_text("export const a = 1;\n")
    (loot / "src/server/budget/a.test.ts").write_text("// hidden\n")
    (loot / "vitest.config.ts").write_text("// ORIGINAL config\n")
    (loot / "vitest.web.config.ts").write_text("// ORIGINAL web config\n")
    (loot / "src/mocks/budget.ts").write_text("// ORIGINAL mock\n")
    (loot / "src/server/tests").mkdir(parents=True)
    (loot / "src/server/tests/mockSyncServer.ts").write_text("// ORIGINAL sync server\n")
    (loot / "src/platform/fetch/__mocks__").mkdir(parents=True)
    (loot / "src/platform/fetch/__mocks__/index.ts").write_text("// ORIGINAL fetch mock\n")

    def git(*a):
        return subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True, text=True).stdout

    git("init", "-q")
    git("add", "-A")
    git("-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "variant")
    (loot / "vitest.config.ts").write_text("// AGENT config\n")
    (loot / "src/mocks/budget.ts").write_text("// AGENT mock\n")
    (loot / "src/mocks/extra.ts").write_text("// AGENT extra\n")
    (loot / "src/server/tests/mockSyncServer.ts").write_text("// AGENT sync server\n")
    (loot / "src/server/tests/helper.ts").write_text("// AGENT helper\n")
    (loot / "src/platform/fetch/__mocks__/index.ts").write_text("// AGENT fetch mock\n")
    (loot / "src/platform/fetch/__mocks__/more.ts").write_text("// AGENT more\n")
    (loot / "src/server/budget/__mocks__").mkdir()
    (loot / "src/server/budget/__mocks__/a.ts").write_text("// AGENT new mock dir\n")
    git("add", "-A")
    agent_diff = git("diff", "--cached")
    git("reset", "-q", "--hard", "HEAD")

    task_dir, run_dir, out = tmp_path / "task", tmp_path / "run", tmp_path / "out"
    for d in (task_dir, run_dir, out):
        d.mkdir()
    (run_dir / "diff.patch").write_text(agent_diff)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _exe(bin_dir / "yarn", FAKE_YARN)
    _exe(bin_dir / "timeout", '#!/bin/bash\nshift\nexec "$@"\n')
    mounts = {"/work/actual": str(repo), "/task/": f"{task_dir}/", "/agentrun/": f"{run_dir}/",
              "/checker/": f"{evaluate.PROBE_SRC.parent}/", "/out/": f"{out}/"}
    script = re.sub("|".join(re.escape(k) for k in mounts), lambda m: mounts[m.group(0)],
                    eval_script(None, [HIDDEN]))
    proc = subprocess.run(["bash", "-c", script], env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert not (out / "eval_error").exists(), (out / "apply.log").read_text()
    assert (loot / "vitest.config.ts").read_text() == "// ORIGINAL config\n"
    assert (loot / "src/mocks/budget.ts").read_text() == "// ORIGINAL mock\n"
    assert not (loot / "src/mocks/extra.ts").exists()
    assert (loot / "src/server/tests/mockSyncServer.ts").read_text() == "// ORIGINAL sync server\n"
    assert not (loot / "src/server/tests/helper.ts").exists()
    assert (loot / "src/platform/fetch/__mocks__/index.ts").read_text() == "// ORIGINAL fetch mock\n"
    assert not (loot / "src/platform/fetch/__mocks__/more.ts").exists()
    assert not (loot / "src/server/budget/__mocks__").exists()  # agent-created: removed
    assert (loot / "src/server/budget/a.ts").exists()
    meta = {"agent": "codex", "cond": "A", "task": "t01", "pass": 0, "status": "ok", "usage": {}}
    r = assemble_result(meta, {"hidden_tests": [HIDDEN]}, agent_diff, out, [])
    assert r["agent_touched_test_infra"] is True and r["eval_error"] is None


# --- trace, diff stats, batch ---------------------------------------------------------------

def _claude(mid, *tools):
    return json.dumps({"type": "assistant", "message": {"id": mid, "content": [
        {"type": "tool_use", "id": f"{mid}-{i}", "name": n, "input": inp} for i, (n, inp) in enumerate(tools)]}})


def test_trace_claude():
    lines = [
        _claude("m1", ("Read", {"file_path": "/work/actual/packages/loot-core/src/server/db/index.ts"})),
        _claude("m1", ("Bash", {"command": "cd packages/loot-core && sed -n '1,80p' src/server/budget/a.ts | head"})),
        _claude("m2", ("Bash", {"command": "yarn test src/x.test.ts > /tmp/log 2>&1"})),
        _claude("m3", ("Edit", {"file_path": "src/server/budget/a.ts"})),
        _claude("m4", ("Bash", {"command": "cd packages/loot-core && yarn lint"})),
        _claude("m5", ("Bash", {"command": "yarn eslint -c eslint.agent.config.mjs src"})),
    ]
    t = extract_trace("claude", lines)
    assert t["files_read"] == ["packages/loot-core/src/server/db/index.ts", "src/server/budget/a.ts"]
    assert t["first_edit_turn"] == 3 and t["lint_invocations"] == 2


def test_trace_codex():
    def item(i, **kw):
        return json.dumps({"type": "item.completed", "item": {"id": f"item_{i}", **kw}})
    lines = [
        item(0, type="error", message="config warning"),
        item(1, type="command_execution", command="bash -lc 'cat packages/loot-core/src/a.ts'"),
        item(2, type="agent_message", text="ok"),
        item(3, type="file_change", changes=[{"kind": "update", "path": "src/a.ts"}]),
        item(4, type="command_execution", command="bash -lc 'yarn lint'"),
    ]
    t = extract_trace("codex", lines)
    assert t == {"files_read": ["packages/loot-core/src/a.ts"], "first_edit_turn": 3, "lint_invocations": 1}


def test_trace_shell_edit_and_empty():
    t = extract_trace("claude", [_claude("m1", ("Bash", {"command": "sed -i 's/a/b/' src/a.ts"}))])
    assert t["first_edit_turn"] == 1
    assert extract_trace("claude", ["not json", ""]) == {"files_read": [], "first_edit_turn": None,
                                                        "lint_invocations": 0}


def test_diff_stats_new_and_deleted_files():
    diff = (DIFF_FLOAT + "diff --git a/x.ts b/x.ts\ndeleted file mode 100644\n--- a/x.ts\n+++ /dev/null\n"
            "@@ -1,2 +0,0 @@\n-a\n-b\n")
    assert diff_stats(diff) == {"files": 2, "added": 1, "removed": 2}
    assert diff_stats("") == {"files": 0, "added": 0, "removed": 0}


def test_evaluate_all_skips_done_and_infra(env):
    done = make_run(env)
    (done / "result.json").write_text("{}")
    infra = make_run(env, cond="AP", status="infra")
    todo = make_run(env, cond="AL")
    res = evaluate_all(env / "runs", tasks_root=env / "tasks", execute=fake_executor(rep=report()),
                       log=lambda s: None)
    assert list(res) == [todo] and res[todo]["correct"] is True
    assert json.loads((done / "result.json").read_text()) == {}
    assert not (infra / "result.json").exists()
    res = evaluate_all(env / "runs", force=True, tasks_root=env / "tasks",
                       execute=fake_executor(rep=report()), log=lambda s: None)
    assert set(res) == {done, todo}


# --- hidden tests rewritten per condition (aa.hidden_tests) -----------------------------------

HIDDEN_DB = "packages/loot-core/src/server/budget/a.test.ts"
BASE_TEST = ("import * as db from '#server/db';\n\n"
             "test('a', async () => { await db.insertAccount({ id: 'x' }); });\n")


def _task_with_base_copy(root: Path) -> Path:
    d = make_task(root / "tasks", hidden=(HIDDEN_DB,))
    (d / "hidden" / HIDDEN_DB).parent.mkdir(parents=True)
    (d / "hidden" / HIDDEN_DB).write_text(BASE_TEST)
    return d


@pytest.mark.parametrize("cond,rewritten", [("A", False), ("AL", False), ("AP", True), ("APL", True)])
def test_stage_hidden_tests_rewrites_for_aplus_only(tmp_path, cond, rewritten):
    d = _task_with_base_copy(tmp_path)
    out = tmp_path / "out"
    assert evaluate.stage_hidden_tests(d, [HIDDEN_DB], cond, out) == [HIDDEN_DB]
    staged = (out / "hidden_src" / HIDDEN_DB).read_text()
    if rewritten:
        assert "await dbWrite.insertAccount(" in staged
        assert "import * as dbWrite from '#server/db/write';" in staged
        assert "import * as db from" not in staged
    else:
        assert staged == BASE_TEST


def test_stage_hidden_tests_without_base_copy_falls_back(tmp_path):
    d = make_task(tmp_path / "tasks")
    assert evaluate.stage_hidden_tests(d, [HIDDEN], "AP", tmp_path / "out") == []


def test_evaluate_run_stages_rewritten_hidden_tests(tmp_path):
    _task_with_base_copy(tmp_path)
    run = make_run(tmp_path, cond="APL")
    calls: list = []
    rep = report(name="src/server/budget/a.test.ts")
    r = evaluate_run(run, tasks_root=tmp_path / "tasks", execute=fake_executor(rep=rep, calls=calls))
    assert r["correct"] is True
    assert "dbWrite.insertAccount" in (run / "eval" / "hidden_src" / HIDDEN_DB).read_text()
    script = calls[0][-1]
    assert script.index("git checkout HEAD --") < script.index("/out/hidden_src/") < script.index("yarn lint")


def test_eval_script_reference_mode_has_no_revert_or_static_checks():
    s = eval_script(None, [HIDDEN], static_checks=False)
    assert "/task/" not in s and "yarn lint" not in s and "yarn tsgo" not in s
    assert "git checkout HEAD --" in s and "yarn vitest" in s


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_real_script_uses_staged_hidden_test(tmp_path):
    """The staged (rewritten) copy wins over the image HEAD version."""
    repo = tmp_path / "actual"
    loot = repo / "packages/loot-core"
    (loot / "src/server/budget").mkdir(parents=True)
    (loot / "src/mocks").mkdir(parents=True)
    (loot / "src/server/budget/a.test.ts").write_text("// HEAD version\n")
    (loot / "src/mocks/.keep").write_text("")
    for args in (["init", "-q"], ["add", "-A"],
                 ["-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "v"]):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    run_dir, out = tmp_path / "run", tmp_path / "out"
    run_dir.mkdir()
    (run_dir / "diff.patch").write_text("")
    (out / "hidden_src" / HIDDEN).parent.mkdir(parents=True)
    (out / "hidden_src" / HIDDEN).write_text("// ORIGINAL rewritten for the condition\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _exe(bin_dir / "yarn", FAKE_YARN)
    _exe(bin_dir / "timeout", '#!/bin/bash\nshift\nexec "$@"\n')
    mounts = {"/work/actual": str(repo), "/agentrun/": f"{run_dir}/",
              "/checker/": f"{evaluate.PROBE_SRC.parent}/", "/out/": f"{out}/"}
    script = re.sub("|".join(re.escape(k) for k in mounts), lambda m: mounts[m.group(0)],
                    eval_script(None, [HIDDEN], static_checks=False))
    proc = subprocess.run(["bash", "-c", script], env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert not (out / "eval_error").exists(), (out / "apply.log").read_text()
    assert (loot / "src/server/budget/a.test.ts").read_text().startswith("// ORIGINAL")
    assert json.loads((out / "report.json").read_text())["testResults"][0]["status"] == "passed"
