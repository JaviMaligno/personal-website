"""Chain evaluator (study 2, plan Task 4). Fake chains, fake runs, fake executor; the
eval script itself is run for real with git + bash (yarn, jscpd, timeout stubbed).
No agent and no Docker."""
import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from aa import chain_eval
from aa.chain_eval import (assemble_step_result, chain_eval_script, evaluate_all, evaluate_chain,
                           evaluate_step, export_review_packets, load_chain, missed_copy,
                           parse_jscpd, summarise_chain, t2_reuse, zone_source_files)

LOOT = "packages/loot-core"
CLOOT = "/work/actual/packages/loot-core"
ZONE_SRC = f"{LOOT}/src/server/budget/actions.ts"


def hidden_path(k: int) -> str:
    return f"{LOOT}/src/server/budget/zone-t{k}.test.ts"


# T1 and T3 are rule steps over three consumers; T2 adds one consumer; T4 builds on them.
CONSUMERS = {
    "T1": {"copy month skips hidden": "copy", "zero skips hidden": "zero",
           "avg skips hidden": "avg", "avg skips goal": "avg"},
    "T2": {"new action uses the rule": "spent"},
    "T3": {"copy month skips fixed": "copy", "zero skips fixed": "zero",
           "avg skips fixed": "avg"},
    "T4": {"override includes hidden": "override"},
}


def make_chain(root: Path, zone="Z1", zone_files=None, t2=None) -> Path:
    d = root / zone
    d.mkdir(parents=True)
    (d / "chain.json").write_text(json.dumps({
        "zone": zone, "steps": ["T1", "T2", "T3", "T4"],
        "zone_files": zone_files if zone_files is not None else [
            "server/budget/actions.ts",            # relative to loot-core/src (spec table)
            f"{LOOT}/src/shared/schedules.ts",     # repo-relative
            "server/budget/actions.test.ts",       # test file: never given to jscpd
            "node_modules/x/index.ts",             # never given to jscpd
            "mocks/budget.ts",                     # test infra: never given to jscpd
        ],
        "t2_reuse": t2 if t2 is not None else {
            "helpers": {"F": ["categoriesForBulkAction"], "R": ["copyPreviousMonth", "setZero"]},
            "markers": [r"is_income", r"hidden\s*=\s*0"]},
    }))
    for k in range(1, 5):
        s = d / f"T{k}"
        (s / "hidden" / hidden_path(k)).parent.mkdir(parents=True)
        (s / "hidden" / hidden_path(k)).write_text(f"// HIDDEN T{k}\n")
        (s / "consumers.json").write_text(json.dumps(CONSUMERS[f"T{k}"]))
        (s / "statement.md").write_text(f"Statement of step {k}.\n")
    return d


def make_step(runs: Path, step="T1", cond="R", zone="Z1", chain="0", agent="claude",
              status="ok", diff="", usage=None, start_tree="s" * 40, post_tree="p" * 40,
              diff_ok=True) -> Path:
    """A step dir as aa.chain_runner leaves it (carry by patches of the earlier steps)."""
    d = runs / agent / cond / zone / chain / step
    d.mkdir(parents=True)
    k = int(step[1:])
    plan = {"from": "image", "patches": [f"T{j}/diff.patch" for j in range(1, k)],
            "expected_start_tree": None}
    (d / "start.json").write_text(json.dumps(plan))
    (d / "agent.json").write_text(json.dumps({
        "agent": agent, "cond": cond, "zone": zone, "chain": int(chain), "step": step,
        "status": status, "wall_s": 42.0, "carry": plan | {"start_tree": start_tree},
        "post_tree": post_tree,
        "usage": usage or {"input_tokens": 100, "output_tokens": 10, "cached_input_tokens": 5,
                           "turns": 3, "tool_calls": 2}}))
    (d / "diff.patch").write_text(diff)
    if diff_ok:
        (d / "diff_ok").write_text("")
    (d / "start_tree").write_text(start_tree + "\n")
    (d / "post_tree").write_text(post_tree + "\n")
    (d / "transcript.jsonl").write_text("")
    return d


def report(statuses: dict[int, dict[str, str]] | None = None, load_fail=()) -> dict:
    """statuses: {step k: {test name: passed|failed}}; load_fail: steps whose file failed
    to load (no assertion results)."""
    out = []
    for k, tests in (statuses or {}).items():
        out.append({"name": f"/work/actual/{hidden_path(k)}", "status": "passed",
                    "assertionResults": [{"fullName": n, "status": s} for n, s in tests.items()]})
    for k in load_fail:
        out.append({"name": f"/work/actual/{hidden_path(k)}", "status": "failed",
                    "assertionResults": []})
    return {"testResults": out}


def all_pass(k: int, **overrides: str) -> dict[str, str]:
    return {n: overrides.get(n, "passed") for n in CONSUMERS[f"T{k}"]}


def fake_executor(rep=None, lint_rc=0, tc_rc=0, eval_error=None, calls=None, jscpd=None,
                  done=True, trees=("s" * 40, "p" * 40), pre_image=""):
    def run(argv, timeout):
        if calls is not None:
            calls.append(argv)
        out = Path(next(a.split(":")[0] for a in argv if a.endswith(":/out")))
        if eval_error != "pre_image":
            (out / "start_tree").write_text(trees[0] + "\n")
            (out / "pre_image.patch").write_text(pre_image)
        if eval_error:
            (out / "eval_error").write_text(eval_error + "\n")
            if eval_error == "diff_apply" and jscpd is not None:
                _write_jscpd(out, "jscpd_pre", jscpd[0])
            return 0
        (out / "diff_applied").write_text("done\n")
        (out / "post_tree").write_text(trees[1] + "\n")
        (out / "post_tree.patch").write_text("POST\n")
        (out / "step.patch").write_text("STEP\n")
        if jscpd is not None:
            _write_jscpd(out, "jscpd_pre", jscpd[0])
            _write_jscpd(out, "jscpd_post", jscpd[1])
        (out / "lint_rc").write_text(f"{lint_rc}\n")
        (out / "typecheck_rc").write_text(f"{tc_rc}\n")
        if rep is not None:
            (out / "report.json").write_text(json.dumps(rep))
        if done:
            (out / "clean_done").write_text("done\n")
            (out / "eval_done").write_text("done\n")
        return 0
    return run


def _write_jscpd(out: Path, which: str, dups: list[tuple[str, int, int, str, int, int]]):
    (out / which).mkdir(exist_ok=True)
    (out / which / "jscpd-report.json").write_text(json.dumps({"duplicates": [
        {"lines": e1 - s1 + 1, "firstFile": {"name": a, "start": s1, "end": e1},
         "secondFile": {"name": b, "start": s2, "end": e2}} for a, s1, e1, b, s2, e2 in dups]}))
    (out / f"{which}_rc").write_text("0\n")


@pytest.fixture
def env(tmp_path):
    make_chain(tmp_path / "tasks2")
    return tmp_path


def ev(step_dir, env, **kw):
    return evaluate_step(step_dir, tasks_root=env / "tasks2", execute=fake_executor(**kw))


# --- task loading ---------------------------------------------------------------------------

def test_load_chain_defaults_and_zone_files_are_source_only(env):
    c = load_chain("Z1", env / "tasks2")
    assert [(s.id, s.index, s.kind) for s in c.steps] == [
        ("T1", 1, "rule"), ("T2", 2, "consumer"), ("T3", 3, "rule"), ("T4", 4, "build")]
    assert c.steps[0].consumers == ["copy", "zero", "avg"]
    assert c.steps[0].hidden == [hidden_path(1)]
    # Review Focus 4: tests, node_modules and test infra never reach jscpd
    assert c.files_for("R") == [ZONE_SRC, f"{LOOT}/src/shared/schedules.ts"]


def test_zone_files_per_condition(tmp_path):
    make_chain(tmp_path, zone_files={"R": ["server/budget/actions.ts"],
                                     "F": ["server/budget/actions.ts", "shared/bulk.ts"]})
    c = load_chain("Z1", tmp_path)
    assert c.files_for("R") == [ZONE_SRC]
    assert c.files_for("F") == [ZONE_SRC, f"{LOOT}/src/shared/bulk.ts"]


def test_zone_source_files_filter():
    assert zone_source_files([
        f"{LOOT}/src/a.ts", f"{LOOT}/src/a.test.ts", f"{LOOT}/src/a.spec.tsx",
        f"{LOOT}/node_modules/b/c.ts", f"{LOOT}/src/x/__mocks__/m.ts", f"{LOOT}/src/server/tests/h.ts",
        f"{LOOT}/vitest.config.ts", f"{LOOT}/src/types.d.ts", f"{LOOT}/src/a.ts", "README.md"]) \
        == [f"{LOOT}/src/a.ts"]


def test_load_chain_rejects_inconsistent_consumers(env):
    d = env / "tasks2" / "Z1"
    raw = json.loads((d / "chain.json").read_text())
    raw["steps"] = [{"id": "T1", "consumers": ["copy", "zero", "avg", "never_tested"]},
                    "T2", "T3", "T4"]
    (d / "chain.json").write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="never_tested"):
        load_chain("Z1", env / "tasks2")


def test_load_chain_rejects_hidden_path_shared_by_two_steps(env):
    d = env / "tasks2" / "Z1"
    shutil.copy(d / "T1" / "hidden" / hidden_path(1), d / "T2" / "hidden" / hidden_path(1))
    with pytest.raises(ValueError, match="already belongs"):
        load_chain("Z1", env / "tasks2")


# --- coverage, missed copy (spec §5.2) -----------------------------------------------------

def test_missed_copy_definition():
    assert missed_copy("rule", 2, 3) is True
    assert missed_copy("rule", 0, 3) is False   # nothing updated: incorrect, not a missed copy
    assert missed_copy("rule", 3, 3) is False
    assert missed_copy("consumer", 0, 1) is None
    assert missed_copy("build", 1, 2) is None


def test_rule_step_partial_coverage_is_missed_copy(env):
    # one of avg's two tests fails -> avg not updated; copy and zero updated -> 2/3
    rep = report({1: all_pass(1, **{"avg skips goal": "failed"})})
    r = ev(make_step(env / "runs2"), env, rep=rep)
    assert r["correct"] is False
    assert (r["consumers_passed"], r["consumers_total"]) == (2, 3)
    assert r["consumers"] == {"copy": True, "zero": True, "avg": False}
    assert r["missed_copy"] is True
    assert r["carried_defects"] == 0 and r["carried_steps_failing"] == []
    on_disk = json.loads((env / "runs2/claude/R/Z1/0/T1/result.json").read_text())
    assert on_disk == r
    for k in ("agent", "cond", "zone", "chain", "step", "status", "correct", "consumers_passed",
              "consumers_total", "missed_copy", "carried_defects", "diff", "tokens", "turns",
              "tool_calls", "wall_s", "t2_reuses_logic"):
        assert k in r, k
    assert (r["agent"], r["cond"], r["zone"], r["chain"], r["step"]) == ("claude", "R", "Z1", 0, 1)
    assert r["tokens"] == {"input": 100, "output": 10, "cached_input": 5}


def test_rule_step_no_consumer_updated_is_incorrect_not_missed(env):
    rep = report({1: {n: "failed" for n in CONSUMERS["T1"]}})
    r = ev(make_step(env / "runs2"), env, rep=rep)
    assert r["correct"] is False and r["consumers_passed"] == 0 and r["missed_copy"] is False


def test_rule_step_all_consumers_updated(env):
    r = ev(make_step(env / "runs2"), env, rep=report({1: all_pass(1)}))
    assert r["correct"] is True and r["missed_copy"] is False and r["consumers_passed"] == 3


def test_consumer_test_missing_from_report_counts_as_not_updated(env):
    tests = all_pass(1)
    del tests["zero skips hidden"]
    r = ev(make_step(env / "runs2"), env, rep=report({1: tests}))
    assert r["consumers"]["zero"] is False and r["correct"] is False and r["missed_copy"] is True


def test_consumer_keys_with_file_prefix(tmp_path):
    d = make_chain(tmp_path / "tasks2")
    (d / "T1" / "consumers.json").write_text(json.dumps({
        f"src/server/budget/zone-t1.test.ts::copy month skips hidden": "copy",
        f"{hidden_path(1)}::zero skips hidden": "zero",
        "avg skips hidden": "avg"}))
    rep = report({1: {"copy month skips hidden": "passed", "zero skips hidden": "failed",
                      "avg skips hidden": "passed"}})
    r = evaluate_step(make_step(tmp_path / "runs2"), tasks_root=tmp_path / "tasks2",
                      execute=fake_executor(rep=rep))
    assert r["consumers"] == {"copy": True, "zero": False, "avg": True}


def _t3_with_t2_consumer(env: Path) -> None:
    """T3 as in the real chains: the T1 consumers plus the one the agent added at T2."""
    t3 = dict(CONSUMERS["T3"]) | {"spent skips fixed": "spent"}
    (env / "tasks2" / "Z1" / "T3" / "consumers.json").write_text(json.dumps(t3))


def test_missed_copy_preexisting_leaves_out_the_t2_consumer(env):
    _t3_with_t2_consumer(env)
    assert load_chain("Z1", env / "tasks2").preexisting_consumers == ["copy", "zero", "avg"]
    t3 = {n: "passed" for n in CONSUMERS["T3"]} | {"spent skips fixed": "failed"}
    r = ev(make_step(env / "runs2", step="T3"), env,
           rep=report({1: all_pass(1), 2: all_pass(2), 3: t3}))
    # every T1 consumer updated; only the agent's own T2 consumer fails
    assert (r["consumers_passed"], r["consumers_total"]) == (3, 4)
    assert r["missed_copy"] is True
    assert r["missed_copy_preexisting"] is False and r["t2_consumer_ok"] is False
    assert (r["consumers_preexisting_passed"], r["consumers_preexisting_total"]) == (3, 3)
    # a pre-existing consumer missed while the T2 one is updated
    t3 = {n: "passed" for n in CONSUMERS["T3"]} | {"zero skips fixed": "failed",
                                                     "spent skips fixed": "passed"}
    r = ev(make_step(env / "runs2", step="T3", chain="1"), env,
           rep=report({1: all_pass(1), 2: all_pass(2), 3: t3}))
    assert r["missed_copy_preexisting"] is True and r["t2_consumer_ok"] is True
    assert (r["consumers_preexisting_passed"], r["consumers_preexisting_total"]) == (2, 3)


def test_depends_on_f_comment_fact_tag_reaches_the_result(env):
    cj = env / "tasks2" / "Z1" / "chain.json"
    meta = json.loads(cj.read_text())
    meta["steps"] = [{"id": "T1", "depends_on_f_comment_fact": True}, "T2", "T3", "T4"]
    cj.write_text(json.dumps(meta))
    c = load_chain("Z1", env / "tasks2")
    assert [s.depends_on_f_comment_fact for s in c.steps] == [True, None, None, None]
    r = ev(make_step(env / "runs2"), env, rep=report({1: all_pass(1)}))
    assert r["depends_on_f_comment_fact"] is True
    r = ev(make_step(env / "runs2", step="T2"), env, rep=report({1: all_pass(1), 2: all_pass(2)}))
    assert r["depends_on_f_comment_fact"] is None
    meta["steps"][0]["depends_on_f_comment_fact"] = "yes"
    cj.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="depends_on_f_comment_fact"):
        load_chain("Z1", env / "tasks2")


def test_real_chains_tag_every_step():
    for zone in ("Z1", "Z2", "Z3", "Z4"):
        tags = [s.depends_on_f_comment_fact for s in load_chain(zone).steps]
        assert all(isinstance(t, bool) for t in tags), zone
    assert [s.depends_on_f_comment_fact for s in load_chain("Z4").steps] == [
        False, True, True, True]


def test_z4_budget_template_merged_into_next_date():
    """Spec amendment 2026-10-08, item 8: the template walks occurrences with
    getNextDate, so its test counts towards the next-date consumer."""
    c = load_chain("Z4")
    assert c.preexisting_consumers == ["next-date", "upcoming-dates"]
    t1 = c.step("T1")
    assert "budget-template" not in t1.consumers
    tmpl = [n for n in t1.tests if "schedule template" in n]
    assert len(tmpl) == 1 and t1.tests[tmpl[0]] == "next-date"
    for sid in ("T3", "T4"):
        assert c.step(sid).consumers == ["next-date", "upcoming-dates", "dates-in-range"]
    # next-date updated only with its template test passing too
    status = {n: True for n in t1.tests}
    assert chain_eval.consumer_coverage(status, t1) == {"next-date": True,
                                                         "upcoming-dates": True}
    status[tmpl[0]] = False
    cov = chain_eval.consumer_coverage(status, t1)
    assert cov == {"next-date": False, "upcoming-dates": True}
    assert missed_copy("rule", sum(cov.values()), len(cov)) is True


def test_missed_copy_preexisting_on_t1_and_off_rule_steps(env):
    rep = report({1: all_pass(1, **{"avg skips goal": "failed"})})
    r1 = ev(make_step(env / "runs2"), env, rep=rep)
    assert r1["missed_copy_preexisting"] is True is r1["missed_copy"]
    assert r1["t2_consumer_ok"] is None
    r2 = ev(make_step(env / "runs2", step="T2"), env,
            rep=report({1: all_pass(1), 2: all_pass(2)}))
    assert r2["missed_copy_preexisting"] is None and r2["t2_consumer_ok"] is True
    # nothing pre-existing updated: incorrect, not a missed copy (as missed_copy)
    rep = report({1: {n: "failed" for n in CONSUMERS["T1"]}})
    r0 = ev(make_step(env / "runs2", chain="5"), env, rep=rep)
    assert r0["missed_copy_preexisting"] is False


# --- cumulative tests / carried defects ----------------------------------------------------

def test_cumulative_tests_carried_defects_and_staging(env):
    calls = []
    rep = report({1: all_pass(1, **{"zero skips hidden": "failed"}), 2: all_pass(2),
                  3: all_pass(3)})
    step = make_step(env / "runs2", step="T3")
    r = evaluate_step(step, tasks_root=env / "tasks2", execute=fake_executor(rep=rep, calls=calls))
    assert r["correct"] is True and r["missed_copy"] is False   # T3's own tests all pass
    assert r["carried_defects"] == 1 and r["carried_steps_failing"] == ["T1"]
    assert r["carried_detail"]["T1"] == {"correct": False, "superseded_tests": 0,
                                         "failed_tests": 1,
                                         "consumers_passed": 2, "consumers_total": 3}
    assert r["carried_detail"]["T2"]["correct"] is True
    assert "T4" not in r["test_status"]
    script = calls[0][-1]
    for k in (1, 2, 3):   # hidden tests of steps 1..k, staged and run in the one vitest pass
        vitest_line = next(ln for ln in script.splitlines() if " vitest " in ln)
        assert hidden_path(k)[len(LOOT) + 1:] in vitest_line
        assert (step / "eval" / "hidden_src" / hidden_path(k)).read_text() == f"// HIDDEN T{k}\n"
    assert hidden_path(4) not in script


def test_superseded_tests_are_not_carried_defects(env):
    """A later step that deliberately contradicts earlier tests (chain.json
    ``supersedes``): from that step on those tests may fail without being carried
    defects; before it they still count."""
    d = env / "tasks2" / "Z1"
    raw = json.loads((d / "chain.json").read_text())
    raw["steps"] = ["T1", "T2", {"id": "T3", "supersedes": {"T1": ["zero skips hidden"]}}, "T4"]
    (d / "chain.json").write_text(json.dumps(raw))
    c = load_chain("Z1", env / "tasks2")
    assert c.superseded(c.steps[3], c.steps[0]) == {"zero skips hidden"}
    assert c.superseded(c.steps[1], c.steps[0]) == frozenset()
    t1 = all_pass(1, **{"zero skips hidden": "failed"})
    r3 = ev(make_step(env / "runs2", step="T3"), env,
            rep=report({1: t1, 2: all_pass(2), 3: all_pass(3)}))
    assert r3["carried_defects"] == 0 and r3["carried_detail"]["T1"]["correct"] is True
    assert r3["carried_detail"]["T1"]["superseded_tests"] == 1
    assert "zero skips hidden" not in r3["test_status"]["T1"]
    # "zero" has no other T1 test, so it drops out of T1's carried consumers
    assert r3["carried_detail"]["T1"]["consumers_total"] == 2
    r2 = ev(make_step(env / "runs2", step="T2"), env, rep=report({1: t1, 2: all_pass(2)}))
    assert r2["carried_defects"] == 1


def test_supersedes_must_name_earlier_tests(env):
    d = env / "tasks2" / "Z1"
    raw = json.loads((d / "chain.json").read_text())
    raw["steps"] = ["T1", {"id": "T2", "supersedes": {"T1": ["no such test"]}}, "T3", "T4"]
    (d / "chain.json").write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="supersedes unknown"):
        load_chain("Z1", env / "tasks2")
    raw["steps"] = ["T1", {"id": "T2", "supersedes": {"T3": ["copy month skips fixed"]}},
                    "T3", "T4"]
    (d / "chain.json").write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="not an earlier step"):
        load_chain("Z1", env / "tasks2")


def test_new_carried_defects_against_previous_step(env):
    runs = env / "runs2"
    ev(make_step(runs, step="T1"), env, rep=report({1: all_pass(1)}))
    r = ev(make_step(runs, step="T2"), env,
           rep=report({1: all_pass(1, **{"avg skips goal": "failed"}), 2: all_pass(2)}))
    assert r["carried_defects"] == 1 and r["new_carried_defects"] == 1
    # a defect already present at T2 is carried at T3 but not new
    r3 = ev(make_step(runs, step="T3"), env,
            rep=report({1: all_pass(1, **{"avg skips goal": "failed"}), 2: all_pass(2),
                        3: all_pass(3)}))
    assert r3["carried_defects"] == 1 and r3["new_carried_defects"] == 0


def test_unparseable_tree_still_runs_carried_tests(env):
    """Review Focus 1: the agent left a tree that does not parse -> every hidden file
    fails to load; correct=false, zero consumers, and the carried tests still count."""
    rep = report(load_fail=(1, 2, 3))
    r = ev(make_step(env / "runs2", step="T3", diff="garbage\n"), env, rep=rep, lint_rc=1, tc_rc=2)
    assert r["eval_error"] is None and r["correct"] is False
    assert r["lint_ok"] is False and r["typecheck_ok"] is False
    assert r["consumers_passed"] == 0 and r["missed_copy"] is False
    assert r["carried_defects"] == len(CONSUMERS["T1"]) + len(CONSUMERS["T2"])
    assert r["carried_steps_failing"] == ["T1", "T2"]
    assert r["hidden"]["failed_tests"] == ["src/server/budget/zone-t3.test.ts::<load>"]


def test_diff_apply_failure(env):
    r = ev(make_step(env / "runs2", step="T2", diff="x"), env, eval_error="diff_apply",
           jscpd=([(ZONE_SRC, 1, 9, f"{LOOT}/src/shared/schedules.ts", 3, 11)], []))
    assert r["correct"] is False and r["eval_error"] == "diff_apply"
    assert r["diff_applies_to_pre_image"] is False
    assert r["carried_defects"] is None and r["consumers"] is None and r["missed_copy"] is None
    assert r["duplication_pre"]["clones"] == 1 and r["duplication_post"] is None


def test_pre_image_failure(env):
    r = ev(make_step(env / "runs2", step="T2"), env, eval_error="pre_image")
    assert r["eval_error"] == "pre_image" and r["correct"] is False
    assert r["diff_applies_to_pre_image"] is None
    assert r["tree_check"] == {"start": None, "post": None}


def test_tree_check_against_runner_tree_ids(env):
    r = ev(make_step(env / "runs2", step="T2"), env,
           rep=report({1: all_pass(1), 2: all_pass(2)}))
    assert r["tree_check"] == {"start": True, "post": True}
    r = ev(make_step(env / "runs2", step="T2", chain="1"), env,
           rep=report({1: all_pass(1), 2: all_pass(2)}), trees=("s" * 40, "x" * 40))
    assert r["tree_check"] == {"start": True, "post": False}


def test_step_without_carry_plan_is_a_setup_error(env):
    d = make_step(env / "runs2", step="T2")
    (d / "start.json").unlink()
    meta = json.loads((d / "agent.json").read_text())
    del meta["carry"]
    (d / "agent.json").write_text(json.dumps(meta))
    calls = []
    r = evaluate_step(d, tasks_root=env / "tasks2", execute=fake_executor(calls=calls))
    assert calls == [] and r["eval_error"].startswith("setup:ValueError")


def test_container_dies_before_report(env):
    r = ev(make_step(env / "runs2"), env, rep=None, done=False)
    assert r["eval_error"] == "container" and r["correct"] is False and r["consumers"] is None


def test_executor_timeout_or_crash_still_writes_result(env):
    step = make_step(env / "runs2")

    def slow(argv, timeout):
        raise subprocess.TimeoutExpired(argv, timeout)
    r = evaluate_step(step, tasks_root=env / "tasks2", execute=slow)
    assert r["eval_error"] == "eval_timeout" and (step / "result.json").exists()

    def boom(argv, timeout):
        raise FileNotFoundError("docker")
    r = evaluate_step(step, tasks_root=env / "tasks2", execute=boom)
    assert r["eval_error"] == "container" and r["correct"] is False


def test_statuses(env):
    runs = env / "runs2"
    assert ev(make_step(runs, status="infra"), env, rep=report({1: all_pass(1)})) is None
    calls = []
    s = make_step(runs, chain="1", status="setup_error")
    r = evaluate_step(s, tasks_root=env / "tasks2", execute=fake_executor(calls=calls))
    assert calls == [] and r["eval_error"] == "not_evaluated" and r["correct"] is False
    r = ev(make_step(runs, chain="2", status="timeout"), env, rep=report({1: all_pass(1)}))
    assert r["status"] == "timeout" and r["correct"] is True  # tables count it via status


def test_hidden_path_and_test_infra_flags(env):
    diff = (f"diff --git a/{hidden_path(2)} b/{hidden_path(2)}\n--- /dev/null\n+++ b/{hidden_path(2)}\n"
            "@@ -0,0 +1 @@\n+// agent\n"
            f"diff --git a/{LOOT}/vitest.config.ts b/{LOOT}/vitest.config.ts\n"
            f"--- a/{LOOT}/vitest.config.ts\n+++ b/{LOOT}/vitest.config.ts\n@@ -1 +1 @@\n-a\n+b\n")
    r = ev(make_step(env / "runs2", diff=diff), env, rep=report({1: all_pass(1)}))
    assert r["agent_touched_hidden_paths"] == [hidden_path(2)]
    assert r["agent_touched_test_infra"] is True and r["pre_image_touched_test_infra"] is False


# --- jscpd ---------------------------------------------------------------------------------

def test_parse_jscpd_keeps_only_zone_clones():
    files = [ZONE_SRC, f"{LOOT}/src/shared/schedules.ts"]
    rep = {"duplicates": [
        {"lines": 10, "firstFile": {"name": ZONE_SRC, "start": 1, "end": 10},
         "secondFile": {"name": ZONE_SRC, "start": 20, "end": 29}},
        {"lines": 5, "firstFile": {"name": f"/work/actual/{ZONE_SRC}", "start": 5, "end": 9},
         "secondFile": {"name": f"./{LOOT}/src/shared/schedules.ts", "start": 1, "end": 5}},
        {"lines": 50, "firstFile": {"name": f"{LOOT}/src/server/budget/actions.test.ts",
                                    "start": 1, "end": 50},
         "secondFile": {"name": ZONE_SRC, "start": 1, "end": 50}},
        {"lines": 50, "firstFile": {"name": f"{LOOT}/node_modules/x.ts", "start": 1, "end": 50},
         "secondFile": {"name": f"{LOOT}/node_modules/y.ts", "start": 1, "end": 50}},
    ]}
    d = parse_jscpd(rep, files)
    assert d["clones"] == 2 and d["duplicated_lines"] == 15
    # zone lines 1-10, 20-29 and 5-9 (inside 1-10) + schedules 1-5
    assert d["duplicated_lines_unique"] == 10 + 10 + 5
    assert parse_jscpd(None, files) is None


def test_parse_jscpd_resolves_bare_basenames():
    # jscpd 5.4 as run in the images reports only the basename of each file
    files = [ZONE_SRC, f"{LOOT}/src/shared/schedules.ts", f"{LOOT}/src/a/index.ts",
             f"{LOOT}/src/b/index.ts"]
    rep = {"duplicates": [
        {"lines": 10, "firstFile": {"name": "actions.ts", "start": 136, "end": 145},
         "secondFile": {"name": "actions.ts", "start": 156, "end": 165}},
        {"lines": 4, "firstFile": {"name": "actions.ts", "start": 1, "end": 4},
         "secondFile": {"name": "schedules.ts", "start": 1, "end": 4}},
        # ambiguous basename: dropped and counted, never guessed
        {"lines": 7, "firstFile": {"name": "index.ts", "start": 1, "end": 7},
         "secondFile": {"name": "actions.ts", "start": 30, "end": 36}},
        # not a scanned file
        {"lines": 9, "firstFile": {"name": "other.ts", "start": 1, "end": 9},
         "secondFile": {"name": "actions.ts", "start": 40, "end": 48}},
    ]}
    d = parse_jscpd(rep, files)
    assert d["clones"] == 2 and d["duplicated_lines"] == 14 and d["unresolved"] == 2
    assert {c["a"] for c in d["clone_list"]} == {ZONE_SRC}


def test_duplication_in_result_and_missing_jscpd(env):
    runs = env / "runs2"
    r = ev(make_step(runs), env, rep=report({1: all_pass(1)}),
           jscpd=([(ZONE_SRC, 1, 10, ZONE_SRC, 20, 29)],
                  [(ZONE_SRC, 1, 10, ZONE_SRC, 20, 29), (ZONE_SRC, 40, 44, ZONE_SRC, 50, 54)]))
    assert r["duplication_pre"]["clones"] == 1 and r["duplication_post"]["clones"] == 2
    assert r["duplication_post"]["duplicated_lines"] == 15
    # jscpd absent from the image (rc 127, no report): None, never a fake zero
    r2 = ev(make_step(runs, chain="9"), env, rep=report({1: all_pass(1)}))
    assert r2["duplication_pre"] is None and r2["duplication_post"] is None


def test_read_jscpd_counts_clones_in_agent_created_zone_files(tmp_path):
    new = f"{LOOT}/src/server/budget/bulk-helpers.ts"
    (tmp_path / "jscpd_post_files").write_text(
        f"{ZONE_SRC}\n{new}\n{LOOT}/src/server/budget/x.test.ts\n\n")
    _write_jscpd(tmp_path, "jscpd_post", [(ZONE_SRC, 1, 10, new, 1, 10),
                                          (ZONE_SRC, 1, 10, f"{LOOT}/src/other.ts", 1, 10)])
    d = chain_eval.read_jscpd(tmp_path, "jscpd_post", [ZONE_SRC])
    assert d["clones"] == 1 and d["agent_files"] == [new] and d["files"] == 2


def test_dirs_for_are_the_zone_file_dirs(env):
    c = load_chain("Z1", env / "tasks2")
    assert c.dirs_for("R") == [f"{LOOT}/src/server/budget", f"{LOOT}/src/shared"]


# --- T2 static check -----------------------------------------------------------------------

def _diff(path: str, *added: str) -> str:
    body = "".join(f"+{a}\n" for a in added)
    return (f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
            f"@@ -1,1 +1,{len(added) + 1} @@\n ctx\n{body}")


CFG = {"helpers": {"F": ["categoriesForBulkAction"], "R": ["copyPreviousMonth"]},
       "markers": [r"is_income"]}


def test_t2_reuse_labels():
    f_call = _diff(ZONE_SRC, "  const cats = await categoriesForBulkAction(month, { skipHidden: true });")
    assert t2_reuse(f_call, "F", CFG)[0] == "helper"
    generic = _diff(ZONE_SRC, "  const cats = categoriesForBulkAction<Cat>(m);")
    assert t2_reuse(generic, "F", CFG)[0] == "helper"
    f_copy = _diff(ZONE_SRC, "  const cats = rows.filter(c => !c.is_income && !c.hidden);")
    assert t2_reuse(f_copy, "F", CFG)[0] == "reimplements"
    # editing the helper's own definition is not a call
    f_def = _diff(ZONE_SRC, "export async function categoriesForBulkAction(month) {",
                  "  return rows.filter(c => !c.is_income);")
    lab, det = t2_reuse(f_def, "F", CFG)
    assert lab == "reimplements" and det["calls"] == []
    r_call = _diff(ZONE_SRC, "  await copyPreviousMonth({ month });")
    assert t2_reuse(r_call, "R", CFG)[0] == "copy"
    r_copy = _diff(ZONE_SRC, "  if (cat.is_income) continue;")
    assert t2_reuse(r_copy, "R", CFG)[0] == "copy"
    only_tests = _diff(f"{LOOT}/src/server/budget/new.test.ts", "categoriesForBulkAction(x);")
    assert t2_reuse(only_tests, "F", CFG) == (None, {"added_source_lines": 0, "calls": [],
                                                     "markers": [], "helpers_checked":
                                                     ["categoriesForBulkAction"],
                                                     "reason": "no_source_change"})
    neither = _diff(ZONE_SRC, "  return doSomethingElse(month);")
    lab, det = t2_reuse(neither, "F", CFG)
    assert lab is None and det["reason"] == "no_call_no_marker"


def test_t2_reuse_only_on_consumer_step(env):
    diff = _diff(ZONE_SRC, "  await categoriesForBulkAction(month);")
    r1 = ev(make_step(env / "runs2", cond="F", diff=diff), env, rep=report({1: all_pass(1)}))
    assert r1["t2_reuses_logic"] is None and r1["t2_reuse_detail"] is None
    r2 = ev(make_step(env / "runs2", step="T2", cond="F", diff=diff), env,
            rep=report({1: all_pass(1), 2: all_pass(2)}))
    assert r2["t2_reuses_logic"] == "helper" and r2["missed_copy"] is None


# --- chain level ---------------------------------------------------------------------------

def test_evaluate_chain_in_order_and_chain_result(env):
    runs = env / "runs2"
    seen = []
    for k in range(1, 5):
        make_step(runs, step=f"T{k}", usage={"input_tokens": 100 * k, "output_tokens": 10 * k})

    def execute(argv, timeout):
        out = Path(next(a.split(":")[0] for a in argv if a.endswith(":/out")))
        k = int(out.parent.name[1:])
        seen.append(k)
        rep = report({j: all_pass(j) for j in range(1, k + 1)})
        fake_executor(rep=rep, jscpd=([(ZONE_SRC, 1, 10, ZONE_SRC, 20, 29)] * k,
                                      [(ZONE_SRC, 1, 10, ZONE_SRC, 20, 29)] * (k + 1)))(argv, timeout)
        (out / "post_tree.patch").write_text(f"POST T{k}\n")
        return 0

    chain_dir = runs / "claude/R/Z1/0"
    c = evaluate_chain(chain_dir, tasks_root=env / "tasks2", execute=execute, log=lambda m: None)
    assert seen == [1, 2, 3, 4]
    assert c["complete"] is True
    assert c["duplication"]["T0"]["clones"] == 1 and c["duplication"]["T4"]["clones"] == 5
    assert c["duplication_delta"]["clones"] == 4 and c["duplication_delta"]["duplicated_lines"] == 40
    assert c["cost_growth"] == {"t1_tokens": 110, "last_tokens": 440, "ratio": 4.0}
    assert c["cumulative_diff"]["path"] == "cumulative.patch"
    assert (chain_dir / "cumulative.patch").read_text() == "POST T4\n"
    assert json.loads((chain_dir / "chain_result.json").read_text()) == c
    # done steps are not re-run without force
    seen.clear()
    evaluate_chain(chain_dir, tasks_root=env / "tasks2", execute=execute, log=lambda m: None)
    assert seen == []


def test_chain_result_incomplete_and_nonempty_start(env):
    runs = env / "runs2"
    make_step(runs, step="T1")
    c = evaluate_chain(runs / "claude/R/Z1/0", tasks_root=env / "tasks2",
                       execute=fake_executor(rep=report({1: all_pass(1)}),
                                             pre_image="diff --git a/x b/x\n"),
                       log=lambda m: None)
    assert c["complete"] is False and c["cost_growth"] is None
    assert c["cumulative_diff"] == {"error": "chain_start_not_untouched_variant"}


def test_evaluate_all_keeps_chains_apart(env):
    runs = env / "runs2"
    make_step(runs, chain="0")
    make_step(runs, chain="1")
    make_step(runs, cond="F", chain="0")
    make_step(runs, agent="codex", chain="0", status="infra")
    res = evaluate_all(runs, tasks_root=env / "tasks2",
                       execute=fake_executor(rep=report({1: all_pass(1)})), log=lambda m: None)
    assert len(res) == 4
    for cd in ("claude/R/Z1/0", "claude/R/Z1/1", "claude/F/Z1/0"):
        assert (runs / cd / "T1/result.json").exists() and (runs / cd / "chain_result.json").exists()
    assert not (runs / "codex/R/Z1/0/T1/result.json").exists()


def test_assemble_is_pure_without_eval_dir(env):
    chain = load_chain("Z1", env / "tasks2")
    meta = {"agent": "codex", "cond": "F", "zone": "Z1", "chain": "3", "step": "T4", "status": "ok"}
    r = assemble_step_result(meta, chain, "", None, [], "setup:OSError: x")
    assert r["eval_error"] == "setup:OSError: x" and r["correct"] is False and r["step"] == 4


# --- the eval script, for real (git + bash; yarn / jscpd / timeout stubbed) ------------------

def _exe(p: Path, body: str) -> None:
    p.write_text(body)
    p.chmod(p.stat().st_mode | stat.S_IEXEC)


# lint fails (the agent left a broken tree) and records what it saw; vitest records its
# file arguments and passes each hidden file whose content is the staged task copy.
FAKE_YARN = r"""#!/bin/bash
case "$1" in
  lint) cat vitest.config.ts > "$AA_OUT/lint_saw"; exit 1;;
  tsgo) exit 2;;
  vitest)
    for a in "$@"; do case $a in --outputFile=*) OUT=${a#--outputFile=};; esac; done
    [ -e vitest.aa-seed.config.ts ] && [ -e src/mocks/aa-seed.setup.ts ] || exit 7
    printf '%s\n' "$@" > "$AA_OUT/vitest_args"
    res=""
    for f in "$@"; do case $f in src/*.test.ts)
      if grep -q '^// HIDDEN' "$f"; then st=passed; else st=failed; fi
      res="$res{\"name\":\"/work/actual/packages/loot-core/$f\",\"status\":\"$st\",\"assertionResults\":[{\"fullName\":\"t\",\"status\":\"$st\"}]},";;
    esac; done
    printf '{"testResults":[%s]}' "${res%,}" > "$OUT"; exit 0;;
esac
exit 9
"""

FAKE_JSCPD = r"""#!/bin/bash
out=""; files=()
while [ $# -gt 0 ]; do case $1 in
  --output) out=$2; shift 2;; --min-tokens|--reporters) shift 2;; --silent) shift;;
  *) files+=("$1"); shift;; esac; done
mkdir -p "$out"; printf '%s\n' "${files[@]}" > "$out/files"
printf '{"duplicates":[{"lines":3,"firstFile":{"name":"%s","start":1,"end":3},"secondFile":{"name":"%s","start":5,"end":7}}]}' "${files[0]}" "${files[0]}" > "$out/jscpd-report.json"
"""


def _git(repo: Path, *a: str) -> str:
    return subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", *a], cwd=repo,
                          check=True, capture_output=True, text=True).stdout


def _image_repo(repo: Path, files: dict[str, str]) -> None:
    """A fake image: the variant committed, plus the install step's uncommitted change."""
    for p, body in files.items():
        (repo / p).parent.mkdir(parents=True, exist_ok=True)
        (repo / p).write_text(body)
    (repo / "package.json").write_text('{"name": "actual"}\n')
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "variant")
    (repo / "package.json").write_text('{"name": "actual", "devDependencies": {"eslint": "9"}}\n')


def _record(repo: Path, change) -> tuple[str, str]:
    """Apply ``change`` on the current worktree; return (diff vs the current index state,
    tree id after) the way the runner records them, then keep the change staged."""
    _git(repo, "add", "-A")
    change()
    _git(repo, "add", "-A")
    return _git(repo, "diff", "--cached", "--binary", "HEAD"), _git(repo, "write-tree").strip()


def _run_script(tmp_path: Path, repo: Path, chain_dir: Path, out: Path, script: str) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    _exe(bin_dir / "yarn", FAKE_YARN)
    _exe(bin_dir / "jscpd", FAKE_JSCPD)
    _exe(bin_dir / "timeout", '#!/bin/bash\nshift\nexec "$@"\n')
    mounts = {"/work/actual": str(repo), "/chain/": f"{chain_dir}/",
              "/checker/": f"{chain_eval.SEED_SRC.parent}/", "/out": str(out)}
    script = re.sub("|".join(re.escape(k) for k in mounts), lambda m: mounts[m.group(0)], script)
    proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                          env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}",
                               "AA_OUT": str(out)})
    assert proc.returncode == 0, proc.stderr


ZONE_FILES = {f"{LOOT}/src/server/budget/actions.ts": "export const a = 1;\n",
              f"{LOOT}/src/shared/schedules.ts": "export const s = 1;\n",
              f"{LOOT}/vitest.config.ts": "// ORIGINAL config\n",
              f"{LOOT}/src/mocks/budget.ts": "// ORIGINAL mock\n",
              f"{LOOT}/src/server/tests/helper.ts": "// ORIGINAL helper\n"}


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_real_script_carry_infra_restore_hidden_override(tmp_path):
    """T2 of a chain, for real: start tree rebuilt from T1's diff (tree id checked against
    the runner's), infra restored from the pristine image although both agents edited
    it, hidden paths overwritten, broken tree still runs the carried tests (Review Focus
    1 and 2), jscpd only on existing zone source files, diffs free of install noise."""
    repo = tmp_path / "actual"
    loot = repo / LOOT
    _image_repo(repo, ZONE_FILES)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "image")  # the runner's `image` commit

    def t1():  # previous agent: zone change, carried infra edit, writes the T1 hidden path
        (loot / "src/server/budget/actions.ts").write_text("export const a = 2;\n")
        (loot / "vitest.config.ts").write_text("// PREVIOUS AGENT config\n")
        (loot / "src/server/budget/zone-t1.test.ts").write_text("// previous agent's own test\n")
    t1_diff, t1_post = _record(repo, t1)
    _git(repo, "commit", "-qm", "t1")

    def t2():  # this agent: deletes a zone file, edits infra, writes a hidden path, breaks code
        (loot / "src/shared/schedules.ts").unlink()
        (loot / "src/mocks/budget.ts").write_text("// AGENT mock\n")
        (loot / "src/server/tests/extra.ts").write_text("// AGENT extra\n")
        (loot / "src/server/budget/zone-t2.test.ts").write_text("// AGENT wrote the hidden path\n")
        (loot / "src/server/budget/actions.ts").write_text("export const a = (;\n")
    t2_diff, t2_post = _record(repo, t2)
    _git(repo, "reset", "-q", "--hard", "HEAD~1")  # back to the image commit
    _git(repo, "reset", "-q", "--soft", "HEAD~1")  # = the variant + the uncommitted install change
    _git(repo, "reset", "-q")
    assert "eslint" in (repo / "package.json").read_text()

    cdir = tmp_path / "chain"
    for sid, diff, post in (("T1", t1_diff, t1_post), ("T2", t2_diff, t2_post)):
        (cdir / sid).mkdir(parents=True)
        (cdir / sid / "diff.patch").write_text(diff)
        (cdir / sid / "diff_ok").write_text("")
        (cdir / sid / "post_tree").write_text(post + "\n")
    out = tmp_path / "out"
    hidden = [hidden_path(1), hidden_path(2)]
    for k, h in enumerate(hidden, start=1):
        (out / "hidden_src" / h).parent.mkdir(parents=True, exist_ok=True)
        (out / "hidden_src" / h).write_text(f"// HIDDEN T{k}\n")
    zone = [ZONE_SRC, f"{LOOT}/src/shared/schedules.ts"]
    plan = {"from": "image", "patches": ["T1/diff.patch"]}
    _run_script(tmp_path, repo, cdir, out,
                chain_eval_script("T2", plan, agent_tree="diff", hidden_tests=hidden,
                                  zone_files=zone))

    assert not (out / "eval_error").exists(), (out / "apply.log").read_text()
    assert (out / "start_tree").read_text().strip() == t1_post     # verified pre-image
    assert (out / "post_tree").read_text().strip() == t2_post
    # lint judged the tree as the agents left it (carried infra edit included) ...
    assert (out / "lint_saw").read_text() == "// PREVIOUS AGENT config\n"
    assert (out / "lint_rc").read_text().strip() == "1"
    # ... the tests ran on the pristine image's infra, not on any agent's
    assert (loot / "vitest.config.ts").read_text() == "// ORIGINAL config\n"
    assert (loot / "src/mocks/budget.ts").read_text() == "// ORIGINAL mock\n"
    assert not (loot / "src/server/tests/extra.ts").exists()
    # hidden paths: staged copies, whatever either agent wrote there
    assert (loot / "src/server/budget/zone-t1.test.ts").read_text() == "// HIDDEN T1\n"
    assert (loot / "src/server/budget/zone-t2.test.ts").read_text() == "// HIDDEN T2\n"
    # broken tree: vitest still ran every hidden file (cumulative)
    args = (out / "vitest_args").read_text().split()
    assert "src/server/budget/zone-t1.test.ts" in args and "src/server/budget/zone-t2.test.ts" in args
    # jscpd only saw zone files that exist (pre: both, post: the deleted one is gone)
    assert (out / "jscpd_pre" / "files").read_text().split() == zone
    assert (out / "jscpd_post" / "files").read_text().split() == [ZONE_SRC]
    # diffs: pre-image = T1, post = T1 + T2, step = T2 only; never the install change
    pre, post, step = ((out / f).read_text() for f in
                       ("pre_image.patch", "post_tree.patch", "step.patch"))
    assert "PREVIOUS AGENT config" in pre and "export const a = (;" not in pre
    assert "PREVIOUS AGENT config" in post and "export const a = (;" in post
    assert "export const a = (;" in step and "PREVIOUS AGENT config" not in step
    assert all("package.json" not in t for t in (pre, post, step))

    chain = load_chain("Z1", make_chain(tmp_path / "tasks2").parent)
    meta = {"agent": "claude", "cond": "R", "zone": "Z1", "chain": 0, "step": "T2", "status": "ok"}
    # the fake vitest reports one test "t" per file; map consumers accordingly
    for st in chain.steps:
        st.tests = {f"{st.hidden[0]}::t": st.consumers[0]}
        st.consumers = st.consumers[:1]
    r = assemble_step_result(meta, chain, t2_diff, out, [],
                             runner_trees={"start": t1_post, "post": t2_post},
                             carried_text=t1_diff)
    assert r["eval_error"] is None and r["correct"] is True and r["carried_defects"] == 0
    assert r["tree_check"] == {"start": True, "post": True}
    assert r["lint_ok"] is False and r["typecheck_ok"] is False
    assert r["agent_touched_test_infra"] is True and r["pre_image_touched_test_infra"] is True
    assert r["agent_touched_hidden_paths"] == [hidden_path(2)]
    assert r["duplication_post"]["clones"] == 1


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_real_script_tree_tar_carry_and_tree_tar_step(tmp_path):
    """The runner's fallback: T1 left only tree.tar (no verified diff); T2 starts from
    it, and T2 itself is also a tree.tar step."""
    repo = tmp_path / "actual"
    loot = repo / LOOT
    _image_repo(repo, ZONE_FILES)
    cdir = tmp_path / "chain"
    snap = tmp_path / "snap"
    shutil.copytree(repo, snap, ignore=shutil.ignore_patterns(".git"))
    (snap / LOOT / "src/server/budget/actions.ts").write_text("export const a = 7;\n")
    (snap / LOOT / "src/server/budget/new.ts").write_text("export const n = 1;\n")
    (cdir / "T1").mkdir(parents=True)
    subprocess.run(["tar", "-cf", str(cdir / "T1/tree.tar"), "."], cwd=snap, check=True)
    (snap / LOOT / "src/server/budget/new.ts").unlink()
    (cdir / "T2").mkdir()
    subprocess.run(["tar", "-cf", str(cdir / "T2/tree.tar"), "."], cwd=snap, check=True)
    out = tmp_path / "out"
    (out / "hidden_src" / hidden_path(1)).parent.mkdir(parents=True)
    (out / "hidden_src" / hidden_path(1)).write_text("// HIDDEN T1\n")
    (out / "hidden_src" / hidden_path(2)).write_text("// HIDDEN T2\n")
    _run_script(tmp_path, repo, cdir, out,
                chain_eval_script("T2", {"from": "T1/tree.tar", "patches": []}, agent_tree="tar",
                                  hidden_tests=[hidden_path(1), hidden_path(2)],
                                  zone_files=[ZONE_SRC]))
    assert not (out / "eval_error").exists(), (out / "apply.log").read_text()
    pre, step = (out / "pre_image.patch").read_text(), (out / "step.patch").read_text()
    assert "export const a = 7;" in pre and "new.ts" in pre
    assert "new.ts" in step and "deleted file" in step and "actions.ts" not in step
    assert (loot / "src/server/budget/actions.ts").read_text() == "export const a = 7;\n"


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_real_script_jscpd_scans_agent_created_zone_files(tmp_path):
    """Source files an agent creates in a zone file's directory (a helper, a moved copy)
    are given to jscpd at the next pre-image and after the step; tests, files outside
    the zone dirs and files the agent deleted again are not."""
    repo = tmp_path / "actual"
    loot = repo / LOOT
    _image_repo(repo, ZONE_FILES)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "image")
    helper = f"{LOOT}/src/server/budget/helper.ts"
    copy = f"{LOOT}/src/server/budget/sub/copy.ts"

    def t1():
        (loot / "src/server/budget/helper.ts").write_text("export const h = 1;\n")
        (loot / "src/server/budget/gone.ts").write_text("export const g = 1;\n")
    t1_diff, _ = _record(repo, t1)
    _git(repo, "commit", "-qm", "t1")

    def t2():
        (loot / "src/server/budget/sub").mkdir()
        (loot / "src/server/budget/sub/copy.ts").write_text("export const c = 1;\n")
        (loot / "src/server/budget/sub/copy.test.ts").write_text("// test\n")
        (loot / "src/server/budget/types.d.ts").write_text("// types\n")
        (loot / "src/other").mkdir()
        (loot / "src/other/x.ts").write_text("export const x = 1;\n")
        (loot / "src/server/budget/gone.ts").unlink()
    t2_diff, _ = _record(repo, t2)
    _git(repo, "reset", "-q", "--hard", "HEAD~1")
    cdir = tmp_path / "chain"
    for sid, diff in (("T1", t1_diff), ("T2", t2_diff)):
        (cdir / sid).mkdir(parents=True)
        (cdir / sid / "diff.patch").write_text(diff)
    out = tmp_path / "out"
    for k in (1, 2):
        (out / "hidden_src" / hidden_path(k)).parent.mkdir(parents=True, exist_ok=True)
        (out / "hidden_src" / hidden_path(k)).write_text(f"// HIDDEN T{k}\n")
    _run_script(tmp_path, repo, cdir, out,
                chain_eval_script("T2", {"from": "image", "patches": ["T1/diff.patch"]},
                                  agent_tree="diff",
                                  hidden_tests=[hidden_path(1), hidden_path(2)],
                                  zone_files=[ZONE_SRC]))
    assert not (out / "eval_error").exists(), (out / "apply.log").read_text()
    gone = f"{LOOT}/src/server/budget/gone.ts"
    assert (out / "jscpd_pre" / "files").read_text().split() == [ZONE_SRC, gone, helper]
    assert (out / "jscpd_post" / "files").read_text().split() == [ZONE_SRC, helper, copy]
    assert (out / "jscpd_post_files").read_text().split() == [ZONE_SRC, helper, copy]
    d = chain_eval.read_jscpd(out, "jscpd_post", [ZONE_SRC])
    assert d["agent_files"] == [helper, copy] and d["clones"] == 1


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_real_script_carried_patch_that_does_not_apply(tmp_path):
    repo = tmp_path / "actual"
    _image_repo(repo, {f"{LOOT}/src/a.ts": "one\n"})
    cdir = tmp_path / "chain"
    (cdir / "T1").mkdir(parents=True)
    (cdir / "T1/diff.patch").write_text(
        f"diff --git a/{LOOT}/src/a.ts b/{LOOT}/src/a.ts\n--- a/{LOOT}/src/a.ts\n"
        f"+++ b/{LOOT}/src/a.ts\n@@ -1 +1 @@\n-two\n+three\n")
    (cdir / "T2").mkdir()
    out = tmp_path / "out"
    out.mkdir()
    _run_script(tmp_path, repo, cdir, out,
                chain_eval_script("T2", {"from": "image", "patches": ["T1/diff.patch"]},
                                  agent_tree="diff", hidden_tests=[hidden_path(1)],
                                  zone_files=[f"{LOOT}/src/a.ts"]))
    assert (out / "eval_error").read_text().strip() == "pre_image"
    assert not (out / "diff_applied").exists()


def test_carry_plan_validation(tmp_path):
    d = tmp_path / "T2"
    d.mkdir()
    assert chain_eval.carry_plan(tmp_path / "T1", {}, 1) == {"from": "image", "patches": []}
    (d / "start.json").write_text(json.dumps({"from": "image", "patches": ["../x/diff.patch"]}))
    with pytest.raises(ValueError, match="unexpected carry path"):
        chain_eval.carry_plan(d, {}, 2)
    plan = {"from": "T1/tree.tar", "patches": ["T2/diff.patch"]}
    assert chain_eval.carry_plan(tmp_path / "T3", {"carry": plan | {"exact": None}}, 3) == plan


def test_carry_plan_rc_t1_needs_its_plan(tmp_path):
    """RC's T1 starts from T0's tree, not the image: without start.json / carry it is an
    error (a silent image fallback would drop T0's refactor); RC's T0 and other arms'
    T1 still fall back to the image."""
    with pytest.raises(ValueError, match="no carry plan"):
        chain_eval.carry_plan(tmp_path / "T1", {"cond": "RC", "step": "T1"}, 1)
    assert chain_eval.carry_plan(tmp_path / "T0", {"cond": "RC", "step": "T0"}, 1) == \
        {"from": "image", "patches": []}
    assert chain_eval.carry_plan(tmp_path / "T1", {"cond": "RL", "step": "T1"}, 1) == \
        {"from": "image", "patches": []}


# --- design-review packets ------------------------------------------------------------------

@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_export_review_packets_verifies_pre_images(env):
    variants = env / "variants"
    repo = variants / "R"
    (repo / LOOT / "src").mkdir(parents=True)
    (repo / LOOT / "src/a.ts").write_text("one\n")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "variant")
    path = f"{LOOT}/src/a.ts"

    def patch(old, new):
        return (f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
                f"@@ -1 +1 @@\n-{old}\n+{new}\n")

    ok_tc = {"start": True, "post": True}
    runs = env / "runs2"
    steps = {"T1": ("", patch("one", "two"), ok_tc),
             "T2": (patch("one", "two"), patch("two", "three"), ok_tc),
             # tree ids never match by repo scope: ignored; T3's measured change is not the
             # agent's diff -> rejected
             "T3": (patch("one", "three"), patch("three", "four"), {"start": False, "post": False}),
             "T4": (patch("one", "four"), patch("WRONG", "five"), ok_tc)}  # wrong context
    for sid, (pre, diff, tc) in steps.items():
        d = make_step(runs, step=sid, diff=diff)
        (d / "eval").mkdir()
        (d / "eval/pre_image.patch").write_text(pre)
        (d / "eval/step.patch").write_text(patch("three", "FOUR") if sid == "T3" else diff)
        (d / "result.json").write_text(json.dumps(
            {"status": "ok", "diff_applies_to_pre_image": True, "tree_check": tc}))
    cdir = runs / "claude/R/Z1/0"
    (cdir / "cumulative.patch").write_text(patch("one", "four"))
    (cdir / "chain_result.json").write_text(json.dumps({"complete": True}))
    # a step whose diff did not apply is skipped
    skipped = make_step(runs, chain="1", step="T1", diff="x")
    (skipped / "result.json").write_text(json.dumps({"status": "ok",
                                                     "diff_applies_to_pre_image": False}))

    out, mapping_p = env / "review2", env / "review2-mapping.json"
    rep = export_review_packets(runs, out, mapping_p, tasks_root=env / "tasks2",
                                variants_root=variants, salt="s")
    assert len(rep["ok"]) == 3 and len(rep["bad"]) == 2
    bad = {b["step"]: b["reason"] for b in rep["bad"]}
    assert bad["T3"].startswith("step patch differs") and bad["T4"].startswith("diff")
    mapping = json.loads(mapping_p.read_text())
    assert sorted((m["kind"], m.get("step")) for m in mapping.values()) == [
        ("chain", None), ("step", "T1"), ("step", "T2")]
    assert json.loads((out / "apply-check.json").read_text()) == rep
    for pid, m in mapping.items():
        p = out / "packets" / pid
        assert sorted(x.name for x in p.iterdir()) == ["diff.patch", "pre-image.patch",
                                                       "statement.md", "tree.txt"]
        text = "".join(x.read_text() for x in p.iterdir())
        for leak in ("claude", "Z1", "R/", "runs2"):   # packets are blind
            assert leak not in text, (pid, leak)
        if m["kind"] == "chain":
            assert "## Step 4" in (p / "statement.md").read_text()
            assert (p / "pre-image.patch").read_text() == ""
    assert out not in mapping_p.parents
    # the judge's tree: the variant + the packet's pre-image; the diff applies there
    t2 = next(pid for pid, m in mapping.items() if m.get("step") == "T2")
    tree = chain_eval.materialise_pre_image(repo, out / "packets" / t2 / "pre-image.patch",
                                            env / "trees" / "t2")
    assert (tree / path).read_text() == "two\n"
    subprocess.run(["git", "apply", "--check", str(out / "packets" / t2 / "diff.patch")],
                   cwd=tree, check=True)


# --- CLI --------------------------------------------------------------------------------------

def test_cli_chain_evaluate(monkeypatch, tmp_path):
    from aa import cli
    seen = {}

    def fake_all(root, **kw):
        seen["root"], seen["kw"] = root, kw
        return {}
    monkeypatch.setattr(chain_eval, "evaluate_all", fake_all)
    rc = cli.main(["chain", "evaluate", "--all", "--runs", str(tmp_path / "r"),
                   "--tasks", str(tmp_path / "t"), "--workers", "3", "--force"])
    assert rc == 0 and seen["root"] == tmp_path / "r"
    assert seen["kw"]["tasks_root"] == tmp_path / "t" and seen["kw"]["workers"] == 3
    assert seen["kw"]["force"] is True
    assert cli.main(["chain", "evaluate"]) == 2
