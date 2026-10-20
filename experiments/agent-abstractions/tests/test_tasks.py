import json
import subprocess
from pathlib import Path

import pytest

import aa.tasks as tasks
from aa.config import CONDITIONS
from aa.tasks import Candidate, DropReason, filter_reason


def c(**kw):
    base = dict(sha="abc1234", date="2026-03-01", subject="fix: x", files=["packages/loot-core/src/server/budget/a.ts"],
                test_files=["packages/loot-core/src/server/budget/a.test.ts"], ai_label=False, protected_hits=2)
    base.update(kw)
    return Candidate(**base)


# --- Step 1: filter_reason (plan tests) -------------------------------------

def test_ai_label_is_an_attribute_not_a_filter():
    # Javier's decision 2026-10-06: "[AI]" commits are mined; the label is recorded.
    assert filter_reason(c(ai_label=True)) is None


def test_deps_dropped():
    assert filter_reason(c(files=["package.json", "packages/loot-core/src/x.ts"])) == "touches_deps"
    assert filter_reason(c(files=["packages/loot-core/migrations/1700_x.sql"])) == "touches_deps"


def test_needs_tests_and_protected_sites():
    assert filter_reason(c(test_files=[])) == "no_tests"
    assert filter_reason(c(protected_hits=0)) == "no_protected_sites"


def test_ok():
    assert filter_reason(c()) is None


# --- extra filter cases -------------------------------------------------------

def test_deps_variants():
    assert filter_reason(c(files=["yarn.lock"])) == "touches_deps"
    assert filter_reason(c(files=["packages/loot-core/package.json"])) == "touches_deps"
    assert filter_reason(c(files=["packages/loot-core/migrations/1722_x.js"])) == "touches_deps"
    assert filter_reason(c(files=[".yarnrc.yml"])) == "touches_deps"
    # "migration" inside a source file name is not a migration directory.
    assert filter_reason(c(files=["packages/loot-core/src/server/migrate/migrations-helper.ts"])) is None


def test_filter_order():
    assert filter_reason(c(ai_label=True, files=["package.json"], test_files=[], protected_hits=0)) == "touches_deps"
    assert filter_reason(c(files=["yarn.lock"], test_files=[], protected_hits=0)) == "touches_deps"


def test_is_test_file():
    assert tasks.is_test_file("packages/loot-core/src/server/a.test.ts")
    assert tasks.is_test_file("packages/loot-core/src/server/a.test.tsx")
    assert tasks.is_test_file("packages/loot-core/src/server/__tests__/helpers.ts")
    assert not tasks.is_test_file("packages/loot-core/src/server/a.ts")
    assert not tasks.is_test_file("packages/loot-core/src/server/testing.ts")


# --- protected_hits / patch parsing -------------------------------------------

PATCH = """\
diff --git a/packages/loot-core/src/server/a.ts b/packages/loot-core/src/server/a.ts
index 1111111..2222222 100644
--- a/packages/loot-core/src/server/a.ts
+++ b/packages/loot-core/src/server/a.ts
@@ -10 +10,2 @@ export function f() {
-  await db.update('transactions', { id, amount });
+  await db.updateWithSchema('transactions', { id, amount: amountToInteger(x) });
+  const y = 1;
@@ -20 +21 @@
--- comment that looks like a header
diff --git a/packages/loot-core/src/server/b.ts b/packages/loot-core/src/server/b.ts
index 3333333..4444444 100644
--- a/packages/loot-core/src/server/b.ts
+++ b/packages/loot-core/src/server/b.ts
@@ -1 +1 @@
-  runQuery(`DELETE FROM payees WHERE id = ?`, [id]);
+  runQuery("UPDATE payees SET name = ?", [n]);
diff --git a/packages/loot-core/src/server/a.test.ts b/packages/loot-core/src/server/a.test.ts
index 5555555..6666666 100644
--- a/packages/loot-core/src/server/a.test.ts
+++ b/packages/loot-core/src/server/a.test.ts
@@ -1 +1 @@
+  await db.insert('transactions', { amount: integerToAmount(1) });
"""


def test_parse_patch_files_and_changed_lines():
    files, changes = tasks.parse_patch(PATCH)
    assert files == ["packages/loot-core/src/server/a.ts", "packages/loot-core/src/server/b.ts",
                     "packages/loot-core/src/server/a.test.ts"]
    a, b, t = changes
    # "--- comment that looks like a header" is a removed hunk line, not a file header.
    assert (a.old, a.new, a.removed, a.added) == ("packages/loot-core/src/server/a.ts",
                                                 "packages/loot-core/src/server/a.ts", [10, 20], [10, 11, 21])
    assert (b.removed, b.added) == ([1], [1])
    assert t.path.endswith("a.test.ts")


def test_parse_patch_rename_lists_both_paths():
    p = ("diff --git a/packages/loot-core/package.json b/packages/loot-core/pkg.json\n"
         "similarity index 100%\nrename from packages/loot-core/package.json\n"
         "rename to packages/loot-core/pkg.json\n")
    files, changes = tasks.parse_patch(p)
    assert files == ["packages/loot-core/package.json", "packages/loot-core/pkg.json"]
    assert [(x.removed, x.added) for x in changes] == [([], [])]


def test_parse_patch_added_deleted_and_pure_insert():
    p = ("diff --git a/packages/loot-core/src/n.ts b/packages/loot-core/src/n.ts\nnew file mode 100644\n"
         "index 0000000..1111111\n--- /dev/null\n+++ b/packages/loot-core/src/n.ts\n@@ -0,0 +1,2 @@\n+a\n+b\n"
         "diff --git a/packages/loot-core/src/d.ts b/packages/loot-core/src/d.ts\ndeleted file mode 100644\n"
         "--- a/packages/loot-core/src/d.ts\n+++ /dev/null\n@@ -1 +0,0 @@\n-x\n"
         "diff --git a/packages/loot-core/src/i.ts b/packages/loot-core/src/i.ts\n"
         "--- a/packages/loot-core/src/i.ts\n+++ b/packages/loot-core/src/i.ts\n@@ -4,0 +5 @@\n+y\n")
    n, d, i = tasks.parse_patch(p)[1]
    assert (n.old, n.new, n.removed, n.added) == (None, "packages/loot-core/src/n.ts", [], [1, 2])
    assert (d.old, d.new, d.removed, d.added) == ("packages/loot-core/src/d.ts", None, [1], [])
    assert (i.removed, i.added) == ([], [5])


# --- protected calls / function units (decision 2) -----------------------------

@pytest.mark.parametrize("body,path,expected", [
    ("await db.update('accounts', { id });", "", True),
    ("await db.updateWithSchema('transactions', t);", "", True),
    ("return db.insertTransaction(t);", "", True),
    ("await insertPayee({ name });", "", True),  # named import of a data-specific writer
    ("export async function insertPayee(p) {", "", False),  # its own declaration only
    ("return update('categories', c);", "packages/loot-core/src/server/db/index.ts", True),
    ("return update('categories', c);", "packages/loot-core/src/server/x.ts", False),
    ("await db.run(`\n  UPDATE categories SET hidden = 1\n`);", "", True),
    ("await db.runQuery('DELETE FROM kvcache');", "", False),  # not a synced table
    ("// update payees here", "", False),
    ("const s = 'UPDATE transactions SET x';", "", False),  # SQL text but no SQL call
    ("x = amountToInteger(y);", "", True),
    ("app.method('x', mutator(undoable(f)));", "", True),
    ("const total = rows.length;", "", False),
])
def test_has_protected_call(body, path, expected):
    assert tasks.has_protected_call(body, path) is expected


PRE = """\
import * as db from '../db';

export async function setBudget(id, amount) {
  const row = await db.first('SELECT * FROM zero_budgets');
  await db.update('zero_budgets', { id, amount });
  return row;
}

export function formatName(name) {
  return name.trim();
}

const helper = rows => {
  return rows.map(r => r.amount);
};

app.method('budget/set', mutator(undoable(setBudget)));
"""


def _units_both(text):
    """(TypeScript units, regex-fallback units); TypeScript skipped if unavailable."""
    fb = tasks._units_regex(text)
    node, ts_dir = tasks._node(), tasks._ts_dir()
    if not (node and ts_dir):
        return [fb]
    return [tasks._units_ts({"k": text}, node, ts_dir)["k"], fb]


def _fc(removed=(), added=()):
    p = "packages/loot-core/src/server/budget/x.ts"
    return tasks.FileChange(old=p, new=p, removed=list(removed), added=list(added))


def test_function_units_ts_shape():
    node, ts_dir = tasks._node(), tasks._ts_dir()
    if not (node and ts_dir):
        pytest.skip("node/typescript unavailable")
    us = tasks._units_ts({"k": PRE}, node, ts_dir)["k"]
    fns = {(u.name, u.start, u.end) for u in us if u.kind == "fn"}
    assert fns == {("setBudget", 3, 7), ("formatName", 9, 11), ("helper", 13, 15)}
    assert tasks.Unit("stmt", "app.method('budget/set', mutator(undoable(setBudget)));", 17, 17) in us


@pytest.mark.parametrize("units", _units_both(PRE), ids=lambda u: "units")
def test_units_hit_function_level(units):
    # A change on a non-write line of a function with a db write counts (not line-level).
    post = PRE.replace("return row;", "return { row };")
    assert tasks.units_hit(_fc([6], [6]), PRE, post, units, units) == {
        "packages/loot-core/src/server/budget/x.ts::fn:setBudget"}
    # A change in another function of the same file does not (not file-level).
    post2 = PRE.replace("name.trim()", "name.trim().toLowerCase()")
    assert tasks.units_hit(_fc([10], [10]), PRE, post2, units, units) == set()
    # Nested anonymous callback belongs to its named function (helper: no write).
    post3 = PRE.replace("r => r.amount", "r => r.amount ?? 0")
    assert tasks.units_hit(_fc([14], [14]), PRE, post3, units, units) == set()
    # Top-level undo registration counts.
    post4 = PRE.replace("'budget/set'", "'budget/set-amount'")
    assert len(tasks.units_hit(_fc([17], [17]), PRE, post4, units, units)) == 1


def test_units_hit_write_removed_counts_via_pre_image():
    # The commit deletes the db write: the post-image body has no protected call,
    # but its pre-image counterpart does -> hit.
    post = PRE.replace("  await db.update('zero_budgets', { id, amount });\n", "")
    pre_u = tasks.function_units({"pre": PRE})["pre"]
    post_u = tasks.function_units({"post": post})["post"]
    assert tasks.units_hit(_fc([5], []), PRE, post, pre_u, post_u) == {
        "packages/loot-core/src/server/budget/x.ts::fn:setBudget"}


def test_units_hit_added_function_with_write():
    post = PRE + "\nexport async function clear(id) {\n  await db.delete_('zero_budgets', id);\n}\n"
    n = len(PRE.split("\n"))
    post_u = tasks.function_units({"post": post})["post"]
    pre_u = tasks.function_units({"pre": PRE})["pre"]
    assert tasks.units_hit(_fc([], range(n, n + 4)), PRE, post, pre_u, post_u) == {
        "packages/loot-core/src/server/budget/x.ts::fn:clear"}


def test_class_statement_does_not_inherit_method_writes():
    pre = ("export class Plugin {\n  static names = ['A'];\n\n"
           "  run(x) {\n    return integerToAmount(x);\n  }\n}\n")
    post = pre.replace("['A']", "['A', 'B']")
    u = tasks.function_units({"k": pre})["k"]
    assert tasks.units_hit(_fc([2], [2]), pre, post, u, u) == set()
    post2 = pre.replace("return integerToAmount(x);", "return integerToAmount(x) + 0;")
    assert tasks.units_hit(_fc([5], [5]), pre, post2, u, u) == {
        "packages/loot-core/src/server/budget/x.ts::fn:Plugin.run"}


def test_is_unit_source():
    assert tasks.is_unit_source("packages/loot-core/src/server/budget/a.ts")
    assert not tasks.is_unit_source("packages/loot-core/src/server/budget/a.test.ts")
    assert not tasks.is_unit_source("packages/loot-core/src/mocks/budget.ts")
    assert not tasks.is_unit_source("packages/loot-core/src/types/x.d.ts")
    assert not tasks.is_unit_source("packages/desktop-client/src/a.ts")
    assert not tasks.is_unit_source(None)


def test_fallback_used_without_typescript(monkeypatch):
    monkeypatch.setattr(tasks, "_ts_dir", lambda: None)
    us = tasks.function_units({"k": PRE})["k"]
    assert ("setBudget", 3, 7) in {(u.name, u.start, u.end) for u in us if u.kind == "fn"}


# --- git fixtures ---------------------------------------------------------------

def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def _commit(repo: Path, msg: str, date: str, files: dict[str, str | None]) -> str:
    for rel, content in files.items():
        p = repo / rel
        if content is None:
            p.unlink()
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    _git(repo, "add", "-A")
    env_date = f"{date}T12:00:00"
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", msg],
                   cwd=repo, check=True, capture_output=True,
                   env={"GIT_AUTHOR_DATE": env_date, "GIT_COMMITTER_DATE": env_date,
                        "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin", "HOME": str(repo)})
    return _git(repo, "rev-parse", "HEAD").strip()


SRC = "packages/loot-core/src/server/budget"


@pytest.fixture
def history(tmp_path):
    repo = tmp_path / "actual-base"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    shas = {}
    shas["old"] = _commit(repo, "init", "2024-06-01", {
        f"{SRC}/a.ts": "export const a = 1;\n",
        "package.json": "{}\n",
        "README.md": "x\n",
    })
    shas["fix"] = _commit(repo, "fix: budget rollover", "2025-05-02", {
        f"{SRC}/a.ts": "export const a = 1;\nawait db.update('zero_budgets', { amount });\n",
        f"{SRC}/a.test.ts": "test('a', () => {});\n",
    })
    shas["ai"] = _commit(repo, "feat: thing", "2026-02-01", {
        f"{SRC}/b.ts": "x = amountToInteger(y);\n",
        f"{SRC}/b.test.ts": "test('b', () => {});\n",
    })
    # body carries the [AI] label
    _git(repo, "commit", "--amend", "-qm", "feat: thing\n\nGenerated [AI] change")
    shas["ai"] = _git(repo, "rev-parse", "HEAD").strip()
    shas["deps"] = _commit(repo, "chore: bump", "2026-03-01", {
        f"{SRC}/c.ts": "await db.insert('x', {});\n",
        "package.json": "{\"a\": 1}\n",
    })
    shas["docs"] = _commit(repo, "docs only", "2026-04-01", {"README.md": "y\n"})
    shas["fix26"] = _commit(repo, "fix: payee merge", "2026-01-10", {
        f"{SRC}/a.ts": "export const a = 2;\nawait db.update('zero_budgets', { amount });\n",
        f"{SRC}/a.test.ts": "test('a', () => {});\ntest('a2', () => {});\n",
    })
    return repo, shas


def test_list_candidates_fields_and_order(history):
    repo, shas = history
    cands = tasks.list_candidates(repo, since="2024-10-01")
    by = {x.sha: x for x in cands}
    # docs-only commit doesn't touch loot-core/src; "old" predates since.
    assert set(by) == {shas["fix"], shas["ai"], shas["deps"], shas["fix26"]}
    assert by[shas["ai"]].ai_label is True
    assert by[shas["fix"]].ai_label is False
    assert "package.json" in by[shas["deps"]].files  # full diff, not only the pathspec
    assert by[shas["fix"]].test_files == [f"{SRC}/a.test.ts"]
    assert by[shas["fix"]].protected_hits == 1
    assert by[shas["fix"]].date == "2025-05-02"
    # 2026 first (newest first), then older years
    assert [x.sha for x in cands] == [shas["deps"], shas["ai"], shas["fix26"], shas["fix"]]


def test_list_candidates_function_level(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    body = ("export async function setBudget(id, amount) {\n  const n = 1;\n"
            "  await db.update('zero_budgets', { id, amount });\n}\n\n"
            "export function fmt(x) {\n  return x;\n}\n")
    _commit(repo, "init", "2025-01-01", {f"{SRC}/x.ts": body})
    near = _commit(repo, "fix: near write", "2025-02-01", {
        f"{SRC}/x.ts": body.replace("const n = 1", "const n = 2"),
        f"{SRC}/x.test.ts": "test('x', () => {});\n"})
    body2 = body.replace("const n = 1", "const n = 2")
    far = _commit(repo, "fix: other fn", "2025-03-01", {
        f"{SRC}/x.ts": body2.replace("return x;", "return x + 1;"),
        f"{SRC}/x.test.ts": "test('x', () => {});\ntest('y', () => {});\n"})
    by = {x.sha: x for x in tasks.list_candidates(repo, since="2024-10-01")}
    assert by[near].protected_hits == 1  # same function as the write, other line
    assert by[far].protected_hits == 0  # same file, function without a write


def test_mine_requires_frozen_tag(history, tmp_path, monkeypatch):
    repo, shas = history
    root = tmp_path / "harness"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _commit(root, "x", "2026-10-05", {"f": "1\n"})
    monkeypatch.setattr(tasks, "ROOT", root)
    with pytest.raises(RuntimeError, match="aplus-frozen"):
        tasks.mine(base=repo)
    _git(root, "tag", "aplus-frozen")
    assert len(tasks.mine(base=repo)) == 4


def test_preview_counts_reasons_without_tag(history, tmp_path, monkeypatch):
    repo, shas = history
    out = tmp_path / "tasks"
    monkeypatch.setattr(tasks, "TASKS", out)
    counts = tasks.preview(base=repo)
    # fix26 only edits a top-level statement without a protected call -> no_protected_sites
    assert counts == {"touches_deps": 1, "no_protected_sites": 1, "ok": 2}
    assert not out.exists()


# --- Step 3: materialise --------------------------------------------------------

@pytest.fixture
def mat_env(history, tmp_path, monkeypatch):
    """Base clone at the newest commit + two variant trees (fresh single-commit repos)."""
    repo, shas = history
    root = tmp_path / "harness"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _commit(root, "x", "2026-10-05", {"f": "1\n"})
    _git(root, "tag", "aplus-frozen")
    monkeypatch.setattr(tasks, "ROOT", root)
    variants = tmp_path / "variants"
    from aa.substrate import fresh_repo
    fresh_repo(repo, variants / "A")
    vp = fresh_repo(repo, variants / "AP")
    return repo, shas, variants, vp


def test_materialise_writes_task_dir(mat_env, tmp_path):
    repo, shas, variants, _ = mat_env
    out = tmp_path / "tasks"
    cand = next(x for x in tasks.list_candidates(repo) if x.sha == shas["fix26"])
    res = tasks.materialise(cand, base=repo, variants=variants, out=out, conds=("A", "AP"))
    assert isinstance(res, Path)
    meta = json.loads((res / "task.json").read_text())
    assert meta["sha"] == shas["fix26"]
    assert meta["hidden_tests"] == [f"{SRC}/a.test.ts"]
    assert meta["touched_files"] == [f"{SRC}/a.ts"]
    assert meta["per_condition"] == {"A": {"revert_patch": "revert.A.patch"},
                                     "AP": {"revert_patch": "revert.AP.patch"}}
    assert meta["selected"] is False
    patch = (res / "revert.A.patch").read_text()
    assert "-export const a = 2;" in patch and "+export const a = 1;" in patch
    assert "-test('a2'" in patch  # test files reverted in the start tree too
    # variant trees are untouched
    assert (variants / "A" / SRC / "a.ts").read_text().startswith("export const a = 2;")
    loaded = tasks.load_tasks(selected_only=False, root=out)
    assert [t.sha for t in loaded] == [shas["fix26"]]
    assert tasks.load_tasks(selected_only=True, root=out) == []
    # reference.patch = the original commit's non-test diff (forward direction).
    assert meta["reference_patch"] == "reference.patch"
    ref = (res / "reference.patch").read_text()
    assert "+export const a = 2;" in ref and "-export const a = 1;" in ref
    assert "a.test.ts" not in ref


def _write_task(root, tid, selected):
    d = root / tid
    d.mkdir(parents=True)
    (d / "task.json").write_text(json.dumps({
        "id": tid, "sha": tid * 4, "date": "2026-01-01", "subject": "s", "hidden_tests": [],
        "touched_files": [], "statement_path": "statement.md", "per_condition": {},
        "selected": selected}))


@pytest.mark.parametrize("ledger", [
    {"t1": {"memorised": True}, "t2": {"memorised": False}},
    {"tasks": {"t1": {"memorised": True}}},
    [{"id": "t1", "memorised": True}, {"id": "t2"}],
])
def test_selection_excludes_memorised(tmp_path, ledger):
    for tid in ("t1", "t2", "t3"):
        _write_task(tmp_path, tid, selected=tid != "t3")
    (tmp_path / "_ledger.json").write_text(json.dumps(ledger))
    assert [t.id for t in tasks.load_tasks(selected_only=True, root=tmp_path)] == ["t2"]
    # the unfiltered listing (used by the memo probe itself) still sees every task
    assert [t.id for t in tasks.load_tasks(selected_only=False, root=tmp_path)] == ["t1", "t2", "t3"]


def test_materialise_revert_conflict_drops(mat_env, tmp_path):
    repo, shas, variants, vp = mat_env
    # AP rewrites the reverted line differently -> 3-way conflict on AP only.
    (vp / SRC / "a.ts").write_text("export const a = 2;\nawait domain.budget.set({ amount });\n")
    _git(vp, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "variant")
    out = tmp_path / "tasks"
    cand = next(x for x in tasks.list_candidates(repo) if x.sha == shas["fix26"])
    res = tasks.materialise(cand, base=repo, variants=variants, out=out, conds=("A", "AP"))
    assert res == DropReason("revert_conflict:AP")
    assert not out.exists()


def test_materialise_superseded_drops(mat_env, tmp_path):
    repo, shas, variants, _ = mat_env
    out = tmp_path / "tasks"
    # A commit whose source change was undone later: the revert is a no-op on source files.
    _commit(repo, "prep", "2026-04-30", {f"{SRC}/d.ts": "export const d = 1;\n"})
    sup = _commit(repo, "fix: temp", "2026-05-01", {f"{SRC}/d.ts": "await db.update('t', {});\n",
                                                    f"{SRC}/d.test.ts": "test('d', () => {});\n"})
    _commit(repo, "undo temp src", "2026-05-02", {f"{SRC}/d.ts": "export const d = 1;\n"})
    from aa.substrate import fresh_repo
    fresh_repo(repo, variants / "A")
    cand = next(x for x in tasks.list_candidates(repo) if x.sha == sup)
    res = tasks.materialise(cand, base=repo, variants=variants, out=out, conds=("A",))
    assert res == DropReason("empty_revert:A")


def test_materialise_requires_frozen_tag(history, tmp_path, monkeypatch):
    repo, shas = history
    root = tmp_path / "harness"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    monkeypatch.setattr(tasks, "ROOT", root)
    with pytest.raises(RuntimeError, match="aplus-frozen"):
        tasks.materialise(c(), base=repo, variants=tmp_path, out=tmp_path / "t")


def test_non_utf8_content_round_trips(mat_env, tmp_path):
    repo, shas, variants, _ = mat_env
    (repo / SRC / "csv.ts").write_bytes(b"export const s = 'caf\xe9';\n")
    _commit(repo, "prep csv", "2026-06-01", {})
    (repo / SRC / "csv.ts").write_bytes(b"export const s = 'caf\xe9 2';\nawait db.update('t', {});\n")
    sha = _commit(repo, "fix: csv", "2026-06-02", {f"{SRC}/csv.test.ts": "test('c', () => {});\n"})
    from aa.substrate import fresh_repo
    fresh_repo(repo, variants / "A")
    cand = next(x for x in tasks.list_candidates(repo) if x.sha == sha)
    assert cand.protected_hits == 1
    res = tasks.materialise(cand, base=repo, variants=variants, out=tmp_path / "tasks", conds=("A",))
    assert isinstance(res, Path)
    assert b"+export const s = 'caf\xe9';" in (res / "revert.A.patch").read_bytes()


def test_materialise_keeps_base_copy_of_hidden_tests(mat_env, tmp_path):
    repo, shas, variants, _ = mat_env
    cand = next(x for x in tasks.list_candidates(repo) if x.sha == shas["fix26"])
    res = tasks.materialise(cand, base=repo, variants=variants, out=tmp_path / "tasks", conds=("A", "AP"))
    meta = json.loads((res / "task.json").read_text())
    assert meta["hidden_dir"] == "hidden"
    for f in meta["hidden_tests"]:
        assert (res / "hidden" / f).read_bytes() == subprocess.run(
            ["git", "show", f"HEAD:{f}"], cwd=repo, capture_output=True, check=True).stdout


# --- Step 4: sanity check (reference passes everywhere, start tree fails) ----------

S_HIDDEN = "packages/loot-core/src/server/budget/a.test.ts"
S_BASE = "import * as db from '#server/db';\n\ntest('a', () => db.insertAccount({}));\n"


def _sanity_task(root: Path, tid: str = "t01") -> Path:
    d = root / tid
    (d / "hidden" / S_HIDDEN).parent.mkdir(parents=True)
    (d / "hidden" / S_HIDDEN).write_text(S_BASE)
    (d / "task.json").write_text(json.dumps({
        "id": tid, "sha": "s" * 40, "date": "2026-01-01", "subject": "s", "hidden_tests": [S_HIDDEN],
        "touched_files": [], "statement_path": "statement.md", "selected": True,
        "per_condition": {c: {"revert_patch": f"revert.{c}.patch"} for c in CONDITIONS}}))
    return d


def sanity_executor(passes: dict[tuple[str, str], bool], seen: list | None = None):
    """passes[(cond, mode)] -> do the hidden tests pass in that run (default: reference
    passes, start fails)."""
    def run(argv, timeout):
        cond = next(a for a in argv if a.startswith("aa-actual:")).split(":", 1)[1]
        script = argv[-1]
        mode = "start" if "/task/revert" in script else "reference"
        out = Path(next(a.split(":")[0] for a in argv if a.endswith(":/out")))
        if seen is not None:
            seen.append((cond, mode, (out / "hidden_src" / S_HIDDEN).read_text()))
        ok = passes.get((cond, mode), mode == "reference")
        st = "passed" if ok else "failed"
        (out / "report.json").write_text(json.dumps({"testResults": [{
            "name": "/work/actual/packages/loot-core/src/server/budget/a.test.ts", "status": st,
            "assertionResults": [{"fullName": "a", "status": st}]}]}))
        (out / "eval_done").write_text("done\n")
        return 0
    return run


def test_sanity_ok_and_rewritten_tests_reach_aplus(tmp_path):
    d = _sanity_task(tmp_path / "tasks")
    seen: list = []
    assert tasks.check_and_record(d, root=tmp_path / "tasks", execute=sanity_executor({}, seen),
                                  work_root=tmp_path / "work") is None
    assert {(c, m) for c, m, _ in seen} == {(c, m) for c in CONDITIONS for m in ("start", "reference")}
    for cond, _m, text in seen:
        assert ("dbWrite.insertAccount" in text) == (cond in ("AP", "APL"))
    assert tasks.read_ledger(tmp_path / "tasks")["t01"]["sanity"] == "ok"
    assert [t.id for t in tasks.load_tasks(root=tmp_path / "tasks")] == ["t01"]


@pytest.mark.parametrize("passes,reason", [
    ({("AP", "reference"): False}, "hidden_tests_not_portable"),
    ({("APL", "reference"): False}, "hidden_tests_not_portable"),
    ({("AL", "reference"): False, ("AP", "reference"): False}, "reference_fails:AL"),
    ({("A", "start"): True}, "not_discriminating"),
])
def test_sanity_drop_for_all_conditions(tmp_path, passes, reason):
    root = tmp_path / "tasks"
    d = _sanity_task(root)
    got = tasks.check_and_record(d, root=root, execute=sanity_executor(passes), work_root=tmp_path / "w")
    assert got == DropReason(reason)
    assert tasks.read_ledger(root)["t01"]["dropped"] == reason
    meta = json.loads((d / "task.json").read_text())
    assert meta["dropped"] == reason and meta["selected"] is False
    assert json.loads((d / "sanity.json").read_text())["reason"] == reason
    assert tasks.load_tasks(root=root) == []  # dropped on every condition
    assert [t.id for t in tasks.load_tasks(selected_only=False, root=root)] == ["t01"]


def test_sanity_eval_error_is_reported(tmp_path):
    d = _sanity_task(tmp_path / "tasks")

    def dead(argv, timeout):
        return 1
    assert tasks.sanity_check(d, execute=dead, work_root=tmp_path / "w") == \
        DropReason("sanity_error:A:container")


def test_ledger_drop_keeps_memorised_flag(tmp_path):
    root = tmp_path / "tasks"
    _sanity_task(root)
    (root / "_ledger.json").write_text(json.dumps({"tasks": {"t01": {"memorised": False}}}))
    tasks.update_ledger(root, "t01", dropped="hidden_tests_not_portable")
    assert tasks.read_ledger(root)["t01"] == {"memorised": False, "dropped": "hidden_tests_not_portable"}


# --- materialise: start-tree test files on A+ are derived, not reverted 3-way -------

DBW = "packages/loot-core/src/server/db/write.ts"
T_OLD = "import * as db from '#server/db';\n\ntest('a', () => db.insertAccount({}));\n"
T_NEW = "import * as db from '#server/db';\n\ntest('a', () => db.insertAccount({ name: 'x' }));\n"


@pytest.fixture
def aplus_env(tmp_path, monkeypatch):
    """Base history with a commit touching a source file and two tests (one edited, one
    added), plus A and AP variants; AP has A+'s db/write.ts and its tests rewritten."""
    from aa.hidden_tests import rewrite_for_condition
    from aa.substrate import fresh_repo
    repo = tmp_path / "actual-base"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo, "init", "2025-01-01", {
        f"{SRC}/a.ts": "export const a = 1;\nawait db.update('zero_budgets', { amount });\n",
        f"{SRC}/a.test.ts": T_OLD,
        DBW.replace("write.ts", "index.ts"): "export function insertAccount() {}\n",
    })
    sha = _commit(repo, "fix: accounts", "2026-02-01", {
        f"{SRC}/a.ts": "export const a = 2;\nawait db.update('zero_budgets', { amount });\n",
        f"{SRC}/a.test.ts": T_NEW,
        f"{SRC}/new.test.ts": "import * as db from '#server/db';\n\ntest('n', () => db.insertAccount({}));\n",
    })
    root = tmp_path / "harness"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _commit(root, "x", "2026-10-05", {"f": "1\n"})
    _git(root, "tag", "aplus-frozen")
    monkeypatch.setattr(tasks, "ROOT", root)
    variants = tmp_path / "variants"
    fresh_repo(repo, variants / "A")
    ap = fresh_repo(repo, variants / "AP")
    (ap / DBW).write_text("export function insertAccount() {}\n")
    for t in (f"{SRC}/a.test.ts", f"{SRC}/new.test.ts"):
        (ap / t).write_text(rewrite_for_condition((ap / t).read_text(), "AP", t, {"insertAccount"}))
    _git(ap, "add", "-A")
    _git(ap, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "aplus")
    cand = next(x for x in tasks.list_candidates(repo) if x.sha == sha)
    return repo, variants, cand


def _start_tree(variant: Path, patch: Path, dst: Path) -> Path:
    """Clone of ``variant`` with the task's revert patch applied."""
    _git(dst.parent, "clone", "-q", str(variant), str(dst))
    if patch.read_text():
        _git(dst, "apply", "--index", str(patch))
    return dst


def test_materialise_derives_aplus_start_tests_instead_of_3way(aplus_env, tmp_path):
    from aa.hidden_tests import rewrite_for_condition
    repo, variants, cand = aplus_env
    # The naive 3-way revert of the test file on AP conflicts (A+ rewrote the same line).
    full = _git(repo, "diff", "--binary", "--full-index", cand.sha, f"{cand.sha}^",
                "--", f"{SRC}/a.test.ts")
    (tmp_path / "full.patch").write_text(full)
    probe = tmp_path / "probe"
    _git(tmp_path, "clone", "-q", str(variants / "AP"), str(probe))
    (probe / ".git" / "objects" / "info" / "alternates").write_text(f"{repo}/.git/objects\n")
    r = subprocess.run(["git", "apply", "--3way", "--index", str(tmp_path / "full.patch")],
                       cwd=probe, capture_output=True, text=True)
    unmerged = _git(probe, "diff", "--name-only", "--diff-filter=U").split()
    assert r.returncode != 0 and unmerged == [f"{SRC}/a.test.ts"]

    res = tasks.materialise(cand, base=repo, variants=variants, out=tmp_path / "tasks",
                            conds=("A", "AP"))
    assert isinstance(res, Path), res
    a = _start_tree(variants / "A", res / "revert.A.patch", tmp_path / "sA")
    ap = _start_tree(variants / "AP", res / "revert.AP.patch", tmp_path / "sAP")
    # A: 3-way revert of tests and source.
    assert (a / SRC / "a.test.ts").read_text() == T_OLD
    assert not (a / SRC / "new.test.ts").exists()
    assert (a / SRC / "a.ts").read_text().startswith("export const a = 1;")
    # AP: source reverted 3-way; tests = A's start-tree tests rewritten for A+.
    assert (ap / SRC / "a.ts").read_text().startswith("export const a = 1;")
    assert (ap / SRC / "a.test.ts").read_text() == \
        rewrite_for_condition(T_OLD, "AP", f"{SRC}/a.test.ts", {"insertAccount"})
    assert "dbWrite.insertAccount({})" in (ap / SRC / "a.test.ts").read_text()
    assert not (ap / SRC / "new.test.ts").exists()  # added by the commit -> absent on start
    # hidden tests: base copies (the evaluator rewrites them per condition)
    assert (res / "hidden" / SRC / "a.test.ts").read_text() == T_NEW


def test_materialise_aplus_source_conflict_still_drops(aplus_env, tmp_path):
    repo, variants, cand = aplus_env
    ap = variants / "AP"
    (ap / SRC / "a.ts").write_text("export const a = 2;\nawait domain.budget.set({ amount });\n")
    _git(ap, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "variant")
    res = tasks.materialise(cand, base=repo, variants=variants, out=tmp_path / "tasks",
                            conds=("A", "AP"))
    assert res == DropReason("revert_conflict:AP")


def test_materialise_without_a_in_conds_still_uses_a_tests(aplus_env, tmp_path):
    repo, variants, cand = aplus_env
    res = tasks.materialise(cand, base=repo, variants=variants, out=tmp_path / "tasks",
                            conds=("AP",))
    assert isinstance(res, Path)
    assert not (res / "revert.A.patch").exists()
    ap = _start_tree(variants / "AP", res / "revert.AP.patch", tmp_path / "sAP")
    assert "dbWrite.insertAccount({})" in (ap / SRC / "a.test.ts").read_text()


def test_derive_start_tests_identity_off_aplus():
    t = {f"{SRC}/a.test.ts": T_OLD, f"{SRC}/gone.test.ts": None}
    assert tasks.derive_start_tests(t, "AL", {"insertAccount"}) == t
    ap = tasks.derive_start_tests(t, "APL", {"insertAccount"})
    assert ap[f"{SRC}/gone.test.ts"] is None
    assert "from '#server/db/write'" in ap[f"{SRC}/a.test.ts"]


def test_materialise_ignores_consumed_release_notes(mat_env, tmp_path):
    """Actual deletes ``upcoming-release-notes/*.md`` at every release, so the note a
    task commit added is absent at base; reverting it must not abort the revert."""
    repo, _, variants, _ = mat_env
    sha = _commit(repo, "fix: notes", "2026-05-01", {
        f"{SRC}/e.ts": "await db.update('zero_budgets', {});\n",
        f"{SRC}/e.test.ts": "test('e', () => {});\n",
        "upcoming-release-notes/1234.md": "---\ncategory: Bugfix\n---\nfix\n",
    })
    _commit(repo, "release", "2026-05-02", {"upcoming-release-notes/1234.md": None})
    from aa.substrate import fresh_repo
    fresh_repo(repo, variants / "A")
    fresh_repo(repo, variants / "AP")
    out = tmp_path / "tasks"
    cand = next(x for x in tasks.list_candidates(repo) if x.sha == sha)
    res = tasks.materialise(cand, base=repo, variants=variants, out=out, conds=("A", "AP"))
    assert isinstance(res, Path), res
    meta = json.loads((res / "task.json").read_text())
    assert meta["touched_files"] == [f"{SRC}/e.ts"]
    for name in ("revert.A.patch", "revert.AP.patch", "reference.patch"):
        assert "upcoming-release-notes" not in (res / name).read_text()


@pytest.mark.parametrize("path,expected", [
    ("upcoming-release-notes/8114.md", True),
    ("packages/desktop-client/e2e/budget.mobile.test.ts-snapshots/x-1-chromium-linux.png", True),
    ("packages/desktop-client/e2e/budget.mobile.test.ts", False),
    ("packages/loot-core/src/server/budget/__snapshots__/base.test.ts.snap", False),
    ("packages/loot-core/src/server/budget/base.ts", False),
])
def test_is_non_code(path, expected):
    assert tasks.is_non_code(path) is expected


# --- Step 5: statement leak check -------------------------------------------------

@pytest.mark.parametrize("text,bad", [
    ("Averages must ignore the current month.", False),
    ("Export `getCategoryAverage({ month, maxMonths, categoryId })`.", False),
    ("Call db.getCategories() first.", True),
    ("Use amountToInteger on the value.", True),
    ("Store it in Cents.", True),
    ("Wrap the handler in mutator", True),
    ("register it as undoable", True),
    ("put it under domain/ helpers", True),
    ("then insertTransaction(x)", True),
    ("call updateCategory( with it", True),
    ("Edit packages/loot-core/src/server/budget/actions.ts", True),
    ("the logic lives in actions.ts", True),
    ("see server/accounts/sync for details", True),
    ("e.g. a 3-month average, i.e. the mean", False),
    ("Reported by users (actualbudget/actual issue 5694):", True),
    ("as discussed in issue 5694", True),
    ("see Issue #1062 for context", True),
    ("fixed upstream by PR 8877", True),
    ("the actualbudget/actual repository", True),
    ("https://github.com/actualbudget/actual/issues/1062", True),
    ("see github.com/foo/bar", True),
    ("raw.githubusercontent.com/x/y", True),
    ("Report the issue to the user when 300 rows fail", False),
    ("Two issues remain: 100 rows and the total.", False),
])
def test_statement_leaks(text, bad):
    assert bool(tasks.statement_leaks(text)) is bad


def test_check_statements_reports_missing_and_leaky(tmp_path):
    for tid, body in (("t1", "Fine behaviour."), ("t2", "Use db.update here."), ("t3", None)):
        d = tmp_path / tid
        d.mkdir()
        (d / "task.json").write_text(json.dumps({"id": tid, "statement_path": "statement.md"}))
        if body is not None:
            (d / "statement.md").write_text(body)
    probs = tasks.check_statements(tmp_path)
    assert set(probs) == {"t2", "t3"}
    assert probs["t3"] == ["missing statement.md"]
    assert any("db." in p for p in probs["t2"])


def test_check_statements_skips_dropped(tmp_path):
    d = tmp_path / "t1"
    d.mkdir()
    (d / "task.json").write_text(json.dumps({"id": "t1", "statement_path": "statement.md",
                                             "dropped": "not_discriminating"}))
    assert tasks.check_statements(tmp_path) == {}


# --- PR-number leak stripping (review 4, finding 2) -------------------------------

def test_pr_number():
    assert tasks.pr_number("Budget averages now exclude incomplete months (#8114)") == "8114"
    assert tasks.pr_number("[AI] Fix #7001 rounding") == "7001"
    assert tasks.pr_number("fix: thing") is None


def test_strip_pr_text_markdown():
    md = "# Notes\n- [#8114](u) Budget averages — thanks\n- [#81145](u) other\n- [#7](u) x\n"
    assert tasks.strip_pr_text(md, "8114") == "# Notes\n- [#81145](u) other\n- [#7](u) x\n"
    assert tasks.strip_pr_text(md, "9999") is None


@pytest.mark.parametrize("where", ["middle", "first", "last"])
def test_strip_pr_text_json_keeps_valid_json(where):
    bullets = {"middle": ["- [#1](u) a", '- [#8392](u) Pluggy "x"', "- [#2](u) b"],
               "first": ["- [#8392](u) Pluggy", "- [#2](u) b"],
               "last": ["- [#1](u) a", "- [#8392](u) Pluggy"]}[where]
    details = "\n".join(bullets)
    text = '{\n  "entries": [\n    {\n      "details": ' + json.dumps(details) + ',\n      "x": 1\n    }\n  ]\n}\n'
    new = tasks.strip_pr_text(text, "8392", json_file=True)
    assert new is not None and "#8392" not in new
    d = json.loads(new)["entries"][0]
    assert d["x"] == 1 and d["details"] == "\n".join(b for b in bullets if "#8392" not in b)


def test_materialise_strips_pr_mentions_in_every_condition(mat_env, tmp_path):
    repo, _, variants, _ = mat_env
    sha = _commit(repo, "[AI] fix: rollover (#4321)", "2026-05-01", {
        "upcoming-release-notes/fix-rollover.md": "---\ncategory: Bugfix\n---\nFix rollover\n",
        f"{SRC}/f.ts": "await db.update('zero_budgets', {});\n",
        f"{SRC}/f.test.ts": "test('f', () => {});\n",
    })
    _commit(repo, "release", "2026-05-02", {
        "packages/docs/docs/releases.md": "## 1.0\n- [#4321](u) Fix rollover\n- [#4322](u) y\n",
        "packages/docs/blog/2026-05-02-release-1-0.md": "- [#4321](u) Fix rollover\n",
        "upcoming-release-notes/4321.md": "---\ncategory: Bugfix\n---\nFix rollover\n",
        f"{SRC}/g.ts": "// see #4321\nexport const g = 1;\n",
    })
    from aa.substrate import fresh_repo
    fresh_repo(repo, variants / "A")
    fresh_repo(repo, variants / "AP")
    cand = next(x for x in tasks.list_candidates(repo) if x.sha == sha)
    assert cand.ai_label and filter_reason(cand) is None
    res = tasks.materialise(cand, base=repo, variants=variants, out=tmp_path / "tasks",
                            conds=("A", "AP"))
    assert isinstance(res, Path), res
    meta = json.loads((res / "task.json").read_text())
    assert meta["ai_label"] is True and meta["pr"] == "4321"
    assert meta["pr_mentions_stripped"] == [
        "packages/docs/blog/2026-05-02-release-1-0.md", "packages/docs/docs/releases.md",
        "upcoming-release-notes/4321.md", "upcoming-release-notes/fix-rollover.md"]
    assert meta["pr_mentions_left"] == [f"{SRC}/g.ts"]
    for cond in ("A", "AP"):
        patch = (res / f"revert.{cond}.patch").read_text()
        assert "-- [#4321](u) Fix rollover" in patch
        assert "deleted file mode" in patch and "upcoming-release-notes/4321.md" in patch
        assert "#4322" not in patch.replace("- [#4322](u) y", "")  # context only
