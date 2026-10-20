"""Issue tasks (aa.issue_tasks): layout, sanity check with a fake executor, and the
evaluator / runner / viewer paths for kind="issue" (empty revert, new hidden tests,
per-family reference)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from aa import evaluate, issue_tasks, runner, viewer
from aa.evaluate import eval_script, evaluate_run
from test_evaluate import FAKE_YARN, LOOT_C, _exe, fake_executor, report

HIDDEN = "packages/loot-core/src/server/budget/issue.test.ts"
HIDDEN_REL = "src/server/budget/issue.test.ts"
STATEMENT = "Hiding a category whose group is hidden should keep the budget balanced.\n"
TEST_BODY = ("// ORIGINAL issue test\nimport { handlers } from '#server/main';\n\n"
             "test('hide keeps balance', async () => { expect(1).toBe(1); });\n")
REF_A = """\
diff --git a/packages/loot-core/src/server/budget/a.ts b/packages/loot-core/src/server/budget/a.ts
--- a/packages/loot-core/src/server/budget/a.ts
+++ b/packages/loot-core/src/server/budget/a.ts
@@ -1 +1 @@
-export const a = 0;
+export const a = 1;
"""
REF_AP = REF_A.replace("a = 1", "a = 2")


def make_issue_task(root: Path, issue=1234, *, test_body=TEST_BODY, ref_a=REF_A,
                    ref_ap=REF_AP) -> Path:
    d = issue_tasks.init_issue_task(issue, "Hidden category breaks balance", "2026-09-01",
                                    [HIDDEN], root=root)
    (d / "statement.md").write_text(STATEMENT)
    (d / "hidden" / HIDDEN).parent.mkdir(parents=True)
    (d / "hidden" / HIDDEN).write_text(test_body)
    (d / "reference.A.patch").write_text(ref_a)
    (d / "reference.AP.patch").write_text(ref_ap)
    return d


def _mount(argv: list[str], dst: str) -> Path:
    return Path(next(a.rsplit(":", 2)[0] for a in argv if a.split(":")[1:2] == [dst]))


def issue_executor(*, untouched_passes=(), ref_fails=(), lint_fail=(), tc_fail=(), calls=None):
    """Fake container: the hidden test passes iff the agent diff is non-empty (the
    reference), with per-condition overrides."""
    def run(argv, timeout):
        if calls is not None:
            calls.append(argv)
        cond = argv[argv.index("bash") - 1].split(":")[1]
        is_ref = bool((_mount(argv, "/agentrun") / "diff.patch").read_text())
        ok = (cond not in ref_fails) if is_ref else (cond in untouched_passes)
        rep = report(status="passed" if ok else "failed", name=HIDDEN_REL)
        return fake_executor(rep=rep, lint_rc=int(cond in lint_fail),
                             tc_rc=int(cond in tc_fail))(argv, timeout)
    return run


def _check(d: Path, tmp_path: Path, **kw):
    return issue_tasks.check_issue_task(d, execute=issue_executor(**kw), work_root=tmp_path / "w",
                                        variants=tmp_path / "novariants")


# --- scaffold and layout -------------------------------------------------------------------

def test_init_writes_loadable_task_json_and_empty_reverts(tmp_path):
    from aa.tasks import load_tasks
    d = make_issue_task(tmp_path)
    meta = json.loads((d / "task.json").read_text())
    assert d.name == "issue-1234" and meta["kind"] == "issue" and meta["issue"] == 1234
    assert meta["hidden_tests"] == [HIDDEN]
    for c in ("A", "AL", "AP", "APL"):
        assert (d / meta["per_condition"][c]["revert_patch"]).read_text() == ""
    assert meta["per_condition"]["AL"]["reference_patch"] == "reference.A.patch"
    assert meta["per_condition"]["APL"]["reference_patch"] == "reference.AP.patch"
    [t] = load_tasks(selected_only=False, root=tmp_path)
    assert t.id == "issue-1234" and t.hidden_tests == [HIDDEN]
    with pytest.raises(FileExistsError):
        issue_tasks.init_issue_task(1234, "x", "2026-09-01", [HIDDEN], root=tmp_path)


def test_validate_layout_clean(tmp_path):
    d = make_issue_task(tmp_path)
    assert issue_tasks.validate_layout(d, tmp_path / "novariants") == []


def test_validate_layout_problems(tmp_path):
    d = make_issue_task(tmp_path, test_body="import { cents } from '#server/domain';\n",
                        ref_ap=REF_A.replace("budget/a.ts", "budget/issue.test.ts"))
    (d / "revert.AP.patch").write_text(REF_A)
    (d / "statement.md").write_text("Fix db.updateCategory in budget/actions.ts\n")
    (d / "reference.A.patch").unlink()
    probs = issue_tasks.validate_layout(d, tmp_path / "novariants")
    joined = "\n".join(probs)
    assert "names the A+ layer" in joined
    assert "AP: revert patch is not empty" in joined
    assert "reference.A.patch missing" in joined
    assert "reference.AP.patch touches hidden tests" in joined
    assert "statement forbidden" in joined and "statement file path" in joined


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_validate_layout_hidden_test_must_be_new(tmp_path):
    d = make_issue_task(tmp_path / "tasks")
    v = tmp_path / "variants" / "A"
    (v / HIDDEN).parent.mkdir(parents=True)
    (v / HIDDEN).write_text("// exists already\n")
    for a in (["init", "-q"], ["add", "-A"],
              ["-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "v"]):
        subprocess.run(["git", *a], cwd=v, check=True, capture_output=True)
    assert issue_tasks.validate_layout(d, tmp_path / "variants") == [
        f"A: hidden test already exists: {HIDDEN}"]


# --- sanity check --------------------------------------------------------------------------

def test_check_ok_on_all_conditions_and_records(tmp_path):
    d = make_issue_task(tmp_path / "tasks")
    calls: list = []
    doc = issue_tasks.check_issue_task(d, execute=issue_executor(calls=calls),
                                       work_root=tmp_path / "w", variants=tmp_path / "nov",
                                       tasks_root=tmp_path / "tasks")
    assert doc["ok"] is True and doc["reasons"] == [] and doc["layout"] == []
    assert set(doc["runs"]) == {f"{c}:{m}" for c in ("A", "AL", "AP", "APL")
                                for m in ("untouched", "reference")}
    assert doc["runs"]["AP:reference"]["lint_ok"] and doc["runs"]["AP:reference"]["typecheck_ok"]
    assert json.loads((d / "sanity.json").read_text())["ok"] is True
    ledger = json.loads((tmp_path / "tasks" / "_ledger.json").read_text())
    assert ledger["issue-1234"]["sanity"] == "ok" and ledger["issue-1234"]["kind"] == "issue"
    # one container per condition and mode, in the condition's image
    assert len(calls) == 8
    images = sorted(argv[argv.index("bash") - 1] for argv in calls)
    assert images == sorted([f"aa-actual:{c}" for c in ("A", "AL", "AP", "APL")] * 2)
    # the reference given to each condition is its family's
    for argv in calls:
        cond = argv[argv.index("bash") - 1].split(":")[1]
        diff = (_mount(argv, "/agentrun") / "diff.patch").read_text()
        script = argv[-1]
        if diff:
            assert diff == (REF_A if cond in ("A", "AL") else REF_AP)
            assert "yarn lint" in script and "yarn tsgo" in script
        else:
            assert "yarn lint" not in script
        # evaluator script, issue flavour: empty revert applies, hidden test is a new file
        assert "git apply --allow-empty" in script and f"/task/revert.{cond}.patch" in script
        assert f"git checkout HEAD -- {HIDDEN}" not in script and f"rm -f {HIDDEN}" in script
        assert "aa-seed" in script and "vitest" in script


def test_check_staged_hidden_rewritten_on_aplus(tmp_path):
    body = ("// ORIGINAL\nimport * as db from '#server/db';\n\n"
            "test('a', async () => { await db.insertAccount({ id: 'x' }); });\n")
    d = make_issue_task(tmp_path / "tasks", test_body=body)
    doc = _check(d, tmp_path)
    staged = Path(doc["runs"]["APL:untouched"]["out_dir"]) / "hidden_src" / HIDDEN
    assert "dbWrite.insertAccount" in staged.read_text()
    staged_a = Path(doc["runs"]["AL:untouched"]["out_dir"]) / "hidden_src" / HIDDEN
    assert staged_a.read_text() == body


def test_check_failures_are_reported_per_condition(tmp_path):
    d = make_issue_task(tmp_path / "tasks")
    doc = _check(d, tmp_path, untouched_passes=("AL",), ref_fails=("AP",), lint_fail=("APL",),
                 tc_fail=("A",))
    assert doc["ok"] is False
    assert set(doc["reasons"]) == {"untouched_passes:AL", "reference_fails:AP",
                                   "reference_lint:APL", "reference_typecheck:A"}
    ledger = json.loads((tmp_path / "tasks" / "_ledger.json").read_text())
    assert ledger["issue-1234"]["sanity"] == "failed"
    meta = json.loads((d / "task.json").read_text())
    assert "dropped" not in meta  # a failure goes to adjudication, not an automatic drop


def test_check_eval_error_and_load_failure_warning(tmp_path):
    d = make_issue_task(tmp_path / "tasks")

    def run(argv, timeout):
        is_ref = bool((_mount(argv, "/agentrun") / "diff.patch").read_text())
        if is_ref:
            return fake_executor(eval_error="diff_apply")(argv, timeout)
        return fake_executor(rep=report(load_fail=True, name=HIDDEN_REL))(argv, timeout)

    doc = issue_tasks.check_issue_task(d, execute=run, work_root=tmp_path / "w",
                                       variants=tmp_path / "nov", conds=("A",))
    assert doc["reasons"] == ["sanity_error:A:reference:diff_apply"]
    assert doc["warnings"] == ["untouched_no_assertion_failure:A"]


def test_check_layout_problem_skips_containers(tmp_path):
    d = make_issue_task(tmp_path / "tasks")
    (d / "statement.md").unlink()
    calls: list = []
    doc = issue_tasks.check_issue_task(d, execute=issue_executor(calls=calls),
                                       work_root=tmp_path / "w", variants=tmp_path / "nov")
    assert calls == [] and doc["ok"] is False
    assert doc["reasons"] == ["layout:missing or empty statement"]


def test_issue_task_dirs_only_issue_kind(tmp_path):
    from test_evaluate import make_task
    make_task(tmp_path, "4556e9e244")
    d = make_issue_task(tmp_path)
    assert issue_tasks.issue_task_dirs(tmp_path) == [d]


# --- evaluator, runner, viewer -------------------------------------------------------------

def test_evaluate_run_on_issue_task(tmp_path):
    make_issue_task(tmp_path / "tasks")
    run = tmp_path / "runs" / "codex" / "AP" / "issue-1234" / "0"
    run.mkdir(parents=True)
    (run / "agent.json").write_text(json.dumps({"agent": "codex", "cond": "AP", "task": "issue-1234",
                                                "pass": 0, "status": "ok", "usage": {}}))
    (run / "diff.patch").write_text(REF_AP)
    calls: list = []
    r = evaluate_run(run, tasks_root=tmp_path / "tasks",
                     execute=fake_executor(rep=report(name=HIDDEN_REL), calls=calls))
    assert r["correct"] is True and r["eval_error"] is None
    script = calls[0][-1]
    assert f"git checkout HEAD -- {HIDDEN}" not in script and f"rm -f {HIDDEN}" in script
    assert (run / "eval" / "hidden_src" / HIDDEN).read_text() == TEST_BODY


def test_mined_eval_script_unchanged_by_new_hidden_support():
    mined = "packages/loot-core/src/server/budget/a.test.ts"
    s = eval_script("revert.A.patch", [mined])
    assert f"git checkout HEAD -- {mined}" in s and "rm -f" not in s


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
@pytest.mark.parametrize("staged", [True, False])
def test_real_script_new_hidden_test_replaces_agent_file(tmp_path, staged):
    """Empty revert applies; the agent's own file at the hidden path is replaced by the
    staged hidden test; without a staged copy the run is a hidden_restore error."""
    repo = tmp_path / "actual"
    loot = repo / "packages/loot-core"
    (loot / "src/server/budget").mkdir(parents=True)
    (loot / "src/mocks").mkdir(parents=True)
    (loot / "src/mocks/.keep").write_text("")
    (loot / "src/server/budget/a.ts").write_text("export const a = 0;\n")

    def git(*a):
        return subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", *a], cwd=repo,
                              check=True, capture_output=True, text=True).stdout

    git("init", "-q"); git("add", "-A"); git("commit", "-qm", "variant")
    (loot / "src/server/budget/a.ts").write_text("export const a = 1;\n")
    (loot / HIDDEN_REL).write_text("// AGENT's own test at the hidden path\n")
    git("add", "-A")
    agent_diff = git("diff", "--cached", "HEAD")
    git("reset", "-q", "--hard", "HEAD")
    assert not (loot / HIDDEN_REL).exists()

    task_dir, run_dir, out = tmp_path / "task", tmp_path / "run", tmp_path / "out"
    for d in (task_dir, run_dir, out):
        d.mkdir()
    (task_dir / "revert.A.patch").write_text("")
    (run_dir / "diff.patch").write_text(agent_diff)
    if staged:
        # a new directory: the eval script must create it
        (out / "hidden_src" / HIDDEN).parent.mkdir(parents=True)
        (out / "hidden_src" / HIDDEN).write_text(TEST_BODY)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _exe(bin_dir / "yarn", FAKE_YARN.replace("src/server/budget/a.test.ts", HIDDEN_REL))
    _exe(bin_dir / "timeout", '#!/bin/bash\nshift\nexec "$@"\n')
    mounts = {"/work/actual": str(repo), "/task/": f"{task_dir}/", "/agentrun/": f"{run_dir}/",
              "/checker/": f"{evaluate.PROBE_SRC.parent}/", "/out/": f"{out}/"}
    script = re.sub("|".join(re.escape(k) for k in mounts), lambda m: mounts[m.group(0)],
                    eval_script("revert.A.patch", [HIDDEN], new_hidden=[HIDDEN]))
    proc = subprocess.run(["bash", "-c", script],
                          env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    if not staged:
        assert (out / "eval_error").read_text().strip() == "hidden_restore"
        return
    assert not (out / "eval_error").exists(), (out / "apply.log").read_text()
    assert (loot / HIDDEN_REL).read_text() == TEST_BODY
    assert (loot / "src/server/budget/a.ts").read_text() == "export const a = 1;\n"
    rep = json.loads((out / "report.json").read_text())
    assert rep["testResults"][0]["status"] == "passed"
    assert rep["testResults"][0]["name"] == f"{LOOT_C}/{HIDDEN_REL}"


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_runner_setup_accepts_empty_revert(tmp_path):
    repo, out = tmp_path / "work" / "actual", tmp_path / "out"
    repo.mkdir(parents=True)
    out.mkdir()
    (repo / "f.ts").write_text("export const x = 1;\n")
    for a in (["init", "-q", "-b", "main"], ["add", "-A"],
              ["-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "base"]):
        subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)
    lines = runner.container_script("codex").splitlines()
    setup = "\n".join(lines[:lines.index("touch /out/setup_ok") + 1])
    setup = setup.replace("/work/actual", str(repo)).replace("/out/", f"{out}/")
    env = {**os.environ, "GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": "a@a",
           "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": "a@a"}
    r = subprocess.run(["bash", "-c", setup], input="", text=True, capture_output=True, env=env)
    assert r.returncode == 0, r.stderr
    assert (out / "setup_ok").exists()
    assert (repo / "f.ts").read_text() == "export const x = 1;\n"


def test_reference_patch_per_family_and_viewer(tmp_path):
    d = make_issue_task(tmp_path / "tasks")
    assert issue_tasks.reference_patch_path(d, "AL").name == "reference.A.patch"
    assert issue_tasks.reference_patch_path(d, "APL").name == "reference.AP.patch"
    assert issue_tasks.reference_patch_path(tmp_path / "mined", "A").name == "reference.patch"
    run = tmp_path / "runs" / "codex" / "APL" / "issue-1234" / "0"
    run.mkdir(parents=True)
    html = viewer.render_run(run, tasks_dir=tmp_path / "tasks")
    assert "a = 2" in html and "No reference diff" not in html


# --- eligibility (spec 4.2, decision 2026-10-06) -------------------------------------------

SRC = "packages/loot-core/src/server/budget/cat.ts"
SRC_BODY = """\
import * as db from '#server/db';

export async function rename(id: string, name: string) {
  const clean = name.trim();
  await db.update('categories', { id, name: clean });
}

export function label(name: string) {
  return name.trim();
}
"""


def _variant(tmp_path: Path) -> Path:
    v = tmp_path / "variantA"
    (v / SRC).parent.mkdir(parents=True)
    (v / SRC).write_text(SRC_BODY)
    g = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q", str(v)], check=True)
    subprocess.run([*g, "-C", str(v), "add", "-A"], check=True)
    subprocess.run([*g, "-C", str(v), "commit", "-qm", "variant"], check=True)
    # A dirty working tree must not matter: the rule reads the committed HEAD.
    (v / SRC).write_text("garbage\n")
    return v


def _ref(old: str, new: str) -> str:
    lines = SRC_BODY.split("\n")
    i = lines.index(old) + 1
    return (f"diff --git a/{SRC} b/{SRC}\n--- a/{SRC}\n+++ b/{SRC}\n"
            f"@@ -{i} +{i} @@\n-{old}\n+{new}\n")


def test_eligible_when_reference_changes_a_function_with_a_db_write(tmp_path):
    v = _variant(tmp_path)
    d = make_issue_task(tmp_path / "tasks", ref_a=_ref("  const clean = name.trim();",
                                                       "  const clean = (name ?? '').trim();"))
    assert issue_tasks.reference_protected_units(d, v) == [f"{SRC}::fn:rename"]
    r = issue_tasks.record_eligibility(d, tasks_root=tmp_path / "tasks", variant=v)
    assert r["eligible"] and r["protected_hits_A"] == 1
    meta = json.loads((d / "task.json").read_text())
    assert meta["eligible"] is True and "dropped" not in meta


def test_ineligible_is_dropped_invariant_not_at_stake_and_reversible(tmp_path):
    from aa.tasks import load_tasks, read_ledger
    root = tmp_path / "tasks"
    v = _variant(tmp_path)
    d = make_issue_task(root, ref_a=_ref("  return name.trim();", "  return name.trim() || '?';"))
    meta = json.loads((d / "task.json").read_text())
    meta["selected"] = True
    (d / "task.json").write_text(json.dumps(meta))
    r = issue_tasks.record_eligibility(d, tasks_root=root, variant=v)
    assert not r["eligible"] and r["protected_hits_A"] == 0
    meta = json.loads((d / "task.json").read_text())
    assert meta["dropped"] == issue_tasks.INELIGIBLE and meta["selected"] is False
    e = read_ledger(root)["issue-1234"]
    assert e["dropped"] == "invariant_not_at_stake" and e["status"] == "dropped"
    assert load_tasks(selected_only=True, root=root) == []
    # a regenerated reference that touches the write makes it eligible again
    (d / "reference.A.patch").write_text(_ref("  const clean = name.trim();",
                                              "  const clean = name.trim() || '?';"))
    assert issue_tasks.record_eligibility(d, tasks_root=root, variant=v)["eligible"]
    e = read_ledger(root)["issue-1234"]
    assert e["dropped"] is None and e["status"] == "ok"
    assert "dropped" not in json.loads((d / "task.json").read_text())


def test_eligibility_keeps_other_drops_and_recheck_keeps_drop(tmp_path):
    from aa.tasks import read_ledger, update_ledger
    root = tmp_path / "tasks"
    v = _variant(tmp_path)
    d = make_issue_task(root, ref_a=_ref("  return name.trim();", "  return name;"))
    update_ledger(root, "issue-1234", status="dropped", dropped="needs_migration")
    issue_tasks.record_eligibility(d, tasks_root=root, variant=v)
    assert read_ledger(root)["issue-1234"]["dropped"] == "needs_migration"
    _check(d, tmp_path)  # a sanity recheck must not resurrect a dropped task
    e = read_ledger(root)["issue-1234"]
    assert e["status"] == "dropped" and e["dropped"] == "needs_migration"
