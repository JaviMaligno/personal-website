from aa.static_check import Violation, check_diff, probe_violations

DIFF_FLOAT = """\
--- a/packages/loot-core/src/server/budget/actions.ts
+++ b/packages/loot-core/src/server/budget/actions.ts
@@ -10,3 +10,4 @@
 export function f(amount) {
+  const cents = amount * 100;
   return x;
 }
"""

DIFF_SEND = """\
--- a/packages/loot-core/src/server/budget/actions.ts
+++ b/packages/loot-core/src/server/budget/actions.ts
@@ -1,2 +1,3 @@
 import x from 'y';
+await sendMessages([{ dataset: 'categories', row: id, column: 'hidden', value: 1, timestamp: Timestamp.send() }]);
"""

DIFF_METHOD = """\
--- a/packages/loot-core/src/server/budget/app.ts
+++ b/packages/loot-core/src/server/budget/app.ts
@@ -1,2 +1,3 @@
 const app = createApp();
+app.method('category-hide', hideCategory);
"""


def _diff(path: str, *added: str) -> str:
    body = "".join(f"+{line}\n" for line in added)
    return (
        f"--- a/{path}\n+++ b/{path}\n@@ -1,1 +1,{len(added) + 1} @@\n"
        f" const keep = 1;\n{body}"
    )


def test_float_money_detected():
    v = check_diff(DIFF_FLOAT, cond="A")
    assert [x.kind for x in v] == ["float_money_math"]
    assert v[0].file.endswith("budget/actions.ts") and v[0].line == 11


def test_send_messages_outside_db_detected():
    assert [x.kind for x in check_diff(DIFF_SEND, cond="AP")] == ["send_messages_outside_db"]


def test_unwrapped_mutation_detected():
    assert [x.kind for x in check_diff(DIFF_METHOD, cond="AL")] == ["unwrapped_mutation"]


# --- probe events: only writers on agent-added lines count (review finding 4) ----------

# Agent diff: adds a raw write at src/server/budget/actions.ts:12 (line 11 is added too).
PROBE_DIFF = """\
--- a/packages/loot-core/src/server/budget/actions.ts
+++ b/packages/loot-core/src/server/budget/actions.ts
@@ -10,3 +10,5 @@
 export async function hide(id) {
+  const sql = 'UPDATE categories SET hidden = 1 WHERE id = ?';
+  await db.runQuery(sql, [id]);
   return id;
 }
"""


def _raw(caller, sql="UPDATE categories SET hidden = 1 WHERE id = ?", table="categories"):
    return {"kind": "raw_write", "table": table, "sql": sql, "caller": caller}


def test_probe_raw_write_on_added_line_counts():
    v = probe_violations([_raw("src/server/budget/actions.ts:12")], PROBE_DIFF, cond="A")
    assert v == [Violation("raw_write", "packages/loot-core/src/server/budget/actions.ts", 12,
                           "categories: UPDATE categories SET hidden = 1 WHERE id = ?")]


def test_probe_raw_write_not_added_by_agent_is_not_counted():
    # Same file, a line the agent did not add (a base writer, possibly shifted by the
    # agent's edits above it) -> not the agent's write, whatever its SQL.
    assert probe_violations([_raw("src/server/budget/actions.ts:14")], PROBE_DIFF, cond="A") == []
    # Context line of the hunk (line 10) is not added either.
    assert probe_violations([_raw("src/server/budget/actions.ts:10")], PROBE_DIFF, cond="A") == []
    # A file the agent never touched (Review Focus #5: base writers during hidden tests).
    assert probe_violations([_raw("src/server/old.ts:10")], PROBE_DIFF, cond="A") == []
    # Empty diff -> nothing can be attributed.
    assert probe_violations([_raw("src/server/budget/actions.ts:12")], "", cond="A") == []


def test_probe_no_sql_prefix_discount():
    # The old discount (same file + same SQL prefix as a base writer) is gone: an
    # added line is counted even if its SQL equals a base writer's in that file.
    v = probe_violations([_raw("src/server/budget/actions.ts:12",
                               sql="UPDATE transactions SET amount = ? WHERE id = ?", table="transactions")],
                         PROBE_DIFF, cond="A")
    assert [(x.kind, x.line) for x in v] == [("raw_write", 12)]


def test_probe_added_lines_in_test_files_do_not_count():
    diff = """\
--- a/packages/loot-core/src/server/budget/actions.test.ts
+++ b/packages/loot-core/src/server/budget/actions.test.ts
@@ -1,1 +1,2 @@
 x
+await db.runQuery('UPDATE categories SET hidden = 1');
"""
    assert probe_violations([_raw("src/server/budget/actions.test.ts:2")], diff, cond="A") == []


def test_probe_dedupes_by_kind_and_caller():
    e = _raw("src/server/budget/actions.ts:12")
    assert len(probe_violations([e, dict(e), dict(e)], PROBE_DIFF, cond="A")) == 1


def test_probe_non_integer_money_always_counts():
    events = [
        {"kind": "non_integer_money", "table": "transactions", "column": "amount", "value": 12.5,
         "caller": "src/server/old.ts:10"},
    ]
    v = probe_violations(events, "", cond="AL")
    assert v == [Violation("non_integer_money", "packages/loot-core/src/server/old.ts", 10,
                           "transactions.amount=12.5", lint_visible=False)]


def test_probe_unknown_caller_not_attributed():
    assert probe_violations([_raw("unknown")], PROBE_DIFF, cond="A") == []
    money = {"kind": "non_integer_money", "table": "transactions", "column": "amount", "value": 0.5,
             "caller": "unknown"}
    assert [(x.file, x.line) for x in probe_violations([money], "", cond="A")] == [("unknown", 0)]


def test_probe_unknown_condition_rejected():
    import pytest

    with pytest.raises(ValueError):
        probe_violations([], "", cond="X")


# --- lint_visible per condition (review finding 11) -------------------------------------

LINE_PATH = "packages/loot-core/src/server/budget/actions.ts"


def _vis(line: str, cond: str, path: str = LINE_PATH) -> list[tuple[str, bool]]:
    return [(x.kind, x.lint_visible) for x in check_diff(_diff(path, line), cond=cond)]


def test_nothing_visible_without_custom_lint():
    for line in ["await sendMessages(m);", "const c = amount * 100;",
                 "app.method('x-set', setX);", "import { w } from '#server/db/write';"]:
        for cond in ("A", "AP"):
            assert all(not vis for _, vis in _vis(line, cond)), (line, cond)


def test_send_messages_and_mutator_visible_in_both_lint_conditions():
    for cond in ("AL", "APL"):
        assert _vis("await sendMessages(m);", cond) == [("send_messages_outside_db", True)]
        assert _vis("app.method('x-set', setX);", cond) == [("unwrapped_mutation", True)]


def test_float_money_visible_only_in_al_and_only_for_lint_pattern():
    assert _vis("const c = amount * 100;", "AL") == [("float_money_math", True)]
    assert _vis("const c = amount * 100;", "APL") == [("float_money_math", False)]
    # checker-only patterns: parseFloat / Number / toFixed
    assert _vis("const y = parseFloat(amountText);", "AL") == [("float_money_math", False)]
    assert _vis("const s = amount.toFixed(2);", "AL") == [("float_money_math", False)]
    # toFixed on `money / 100` is also the lint pattern
    assert _vis("const s = (budgeted / 100).toFixed(2);", "AL") == [("float_money_math", True)]


def test_db_write_import_visible_only_in_apl_for_rule_specifiers():
    assert _vis("import { w } from '#server/db/write';", "APL") == [("db_write_import_outside_domain", True)]
    assert _vis("import { w } from '../db/write';", "APL") == [("db_write_import_outside_domain", True)]
    assert _vis("import { w } from '#server/db/write';", "AL") == [("db_write_import_outside_domain", False)]
    # deeper relative paths and explicit extensions match the rule's regex too
    assert _vis("import { w } from '../../db/write';", "APL") == [("db_write_import_outside_domain", True)]
    assert _vis("export * from '../db/write.ts';", "APL") == [("db_write_import_outside_domain", True)]
    # require() is not seen by no-restricted-imports
    assert _vis("const w = require('../db/write');", "APL") == [("db_write_import_outside_domain", False)]


def test_lint_only_sees_ts_files():
    assert _vis("await sendMessages(m);", "AL", path="packages/loot-core/src/server/x.tsx") == [
        ("send_messages_outside_db", False)]


def _raw_diff(*lines: str) -> str:
    return _diff(LINE_PATH, *lines)  # added lines start at line 2


def test_raw_write_visible_in_al_only_for_literal_sql():
    literal = _raw_diff("await db.runQuery('UPDATE categories SET hidden = 1 WHERE id = ?', [id]);")
    ev = [_raw("src/server/budget/actions.ts:2")]
    assert [x.lint_visible for x in probe_violations(ev, literal, cond="AL")] == [True]
    assert [x.lint_visible for x in probe_violations(ev, literal, cond="APL")] == [False]
    assert [x.lint_visible for x in probe_violations(ev, literal, cond="A")] == [False]
    # multi-line call: SQL literal on the next added line
    multi = _raw_diff("await db.runQuery(", "  `DELETE FROM categories WHERE id = ?`, [id]);")
    assert [x.lint_visible for x in probe_violations(ev, multi, cond="AL")] == [True]
    # SQL built at runtime -> the rule cannot see it
    dynamic = _raw_diff("await db.runQuery(sql, [id]);")
    assert [x.lint_visible for x in probe_violations(ev, dynamic, cond="AL")] == [False]
    # non-synced table -> not the rule's business
    other = _raw_diff("await db.runQuery('UPDATE messages_crdt SET x = 1');")
    assert [x.lint_visible for x in probe_violations(ev, other, cond="AL")] == [False]


def test_violation_to_json():
    v = Violation("raw_write", "f.ts", 3, "d", True)
    assert v.to_json() == {"kind": "raw_write", "file": "f.ts", "line": 3, "detail": "d", "lint_visible": True}


# --- static checks: edge cases ---------------------------------------------------------


def test_only_added_lines_count():
    diff = """\
--- a/packages/loot-core/src/server/budget/actions.ts
+++ b/packages/loot-core/src/server/budget/actions.ts
@@ -1,3 +1,2 @@
 const a = 1;
-const cents = amount * 100;
 const b = 2;
"""
    assert check_diff(diff, cond="A") == []


def test_test_files_and_other_packages_ignored():
    for path in [
        "packages/loot-core/src/server/budget/actions.test.ts",
        "packages/loot-core/src/server/budget/__tests__/x.ts",
        "packages/desktop-client/src/components/x.ts",
        "packages/loot-core/src/mocks/aa-probe.setup.ts",
    ]:
        assert check_diff(_diff(path, "const cents = amount * 100;"), cond="A") == [], path


def test_send_messages_allowed_in_db_and_sync():
    for path in ["packages/loot-core/src/server/db/index.ts", "packages/loot-core/src/server/sync/index.ts"]:
        assert check_diff(_diff(path, "await sendMessages(msgs);"), cond="A") == []


def test_mutator_wrapped_and_read_methods_ok():
    d = _diff(
        "packages/loot-core/src/server/budget/app.ts",
        "app.method('category-hide', mutator(hideCategory));",
        "app.method('get-categories', getCategories);",
        "app.method('query-x', q);",
        "app.method('list-y', l);",
    )
    assert check_diff(d, cond="A") == []


def test_mutator_on_next_line_ok():
    d = _diff(
        "packages/loot-core/src/server/budget/app.ts",
        "app.method(",
        "  'category-hide',",
        "  mutator(hideCategory),",
        ");",
    )
    # multi-line registration with the name on its own line is not matched as unwrapped
    assert check_diff(d, cond="A") == []
    d2 = _diff("packages/loot-core/src/server/budget/app.ts", "app.method('category-hide',", "  mutator(hide));")
    assert check_diff(d2, cond="A") == []
    d3 = _diff("packages/loot-core/src/server/budget/app.ts", "app.method('category-hide',", "  hide);")
    assert [x.kind for x in check_diff(d3, cond="A")] == ["unwrapped_mutation"]


def test_float_money_variants():
    path = "packages/loot-core/src/server/budget/actions.ts"
    bad = [
        "const y = t.balance / 100;",
        "const y = 100 * budgeted;",
        "const y = spentTotal * 10 ** 2;",
        "const y = carryover * Math.pow(10, 2);",
        "const y = parseFloat(amountText);",
        "const y = Number(row.amount);",
        "const s = amount.toFixed(2);",
        "const s = (budgeted / 100).toFixed(2);",
    ]
    for line in bad:
        assert [x.kind for x in check_diff(_diff(path, line), cond="A")] == ["float_money_math"], line
    good = [
        "const x = amountToInteger(amount);",
        "const y = count * 100;",
        "const z = Number(id);",
        "const s = ratio.toFixed(2);",
    ]
    for line in good:
        assert check_diff(_diff(path, line), cond="A") == [], line


def test_float_money_allowed_in_shared_util():
    d = _diff("packages/loot-core/src/shared/util.ts", "return Math.round(amount * 100);")
    assert check_diff(d, cond="A") == []


def test_db_write_import_outside_domain_computed_for_all_conditions():
    path = "packages/loot-core/src/server/budget/actions.ts"
    for imp in [
        "import { updateCategory } from '#server/db/write';",
        "import * as w from '../db/write';",
        "import { x } from './db/write';",
        "const w = require('../../db/write');",
    ]:
        for cond in ["A", "AL", "AP", "APL"]:
            assert [x.kind for x in check_diff(_diff(path, imp), cond=cond)] == [
                "db_write_import_outside_domain"
            ], (imp, cond)
    for ok_path in [
        "packages/loot-core/src/server/domain/categories.ts",
        "packages/loot-core/src/server/db/index.ts",
    ]:
        assert check_diff(_diff(ok_path, "import { x } from '#server/db/write';"), cond="AP") == []


def test_line_numbers_across_hunks_and_files():
    diff = """\
--- a/packages/loot-core/src/server/a.ts
+++ b/packages/loot-core/src/server/a.ts
@@ -1,2 +1,3 @@
 line1
+const c = amount * 100;
 line2
@@ -20,2 +21,3 @@
 line20
+await sendMessages(m);
 line21
--- a/packages/loot-core/src/server/b.ts
+++ b/packages/loot-core/src/server/b.ts
@@ -5,1 +5,2 @@
 x
+app.method('x-set', setX);
"""
    v = check_diff(diff, cond="A")
    assert [(x.kind, x.file, x.line) for x in v] == [
        ("float_money_math", "packages/loot-core/src/server/a.ts", 2),
        ("send_messages_outside_db", "packages/loot-core/src/server/a.ts", 22),
        ("unwrapped_mutation", "packages/loot-core/src/server/b.ts", 6),
    ]


def test_new_file_and_empty_diff():
    diff = """\
--- /dev/null
+++ b/packages/loot-core/src/server/new.ts
@@ -0,0 +1,2 @@
+export const x = 1;
+await sendMessages(m);
"""
    assert [(x.kind, x.line) for x in check_diff(diff, cond="A")] == [("send_messages_outside_db", 2)]
    assert check_diff("", cond="A") == []


def test_unknown_condition_rejected():
    import pytest

    with pytest.raises(ValueError):
        check_diff(DIFF_FLOAT, cond="B")


def test_malformed_hunk_headers_fall_back_to_lenient_parser():
    # header lengths are wrong for both files; must not raise, line numbers from the header start
    diff = """\
diff --git a/packages/loot-core/src/server/a.ts b/packages/loot-core/src/server/a.ts
--- a/packages/loot-core/src/server/a.ts
+++ b/packages/loot-core/src/server/a.ts
@@ -3,9 +3,9 @@
 ctx
-old
+await sendMessages(m);
diff --git a/packages/loot-core/src/server/b.ts b/packages/loot-core/src/server/b.ts
--- a/packages/loot-core/src/server/b.ts
+++ b/packages/loot-core/src/server/b.ts
@@ -1,7 +1,7 @@
+app.method('b-set',
+  setB);
"""
    v = check_diff(diff, cond="A")
    assert [(x.kind, x.file, x.line) for x in v] == [
        ("send_messages_outside_db", "packages/loot-core/src/server/a.ts", 4),
        ("unwrapped_mutation", "packages/loot-core/src/server/b.ts", 1),
    ]


def test_load_baseline_and_read_events(tmp_path):
    from aa.static_check import load_baseline, read_probe_events

    f = tmp_path / "baseline-writers.json"
    f.write_text('["src/server/x.ts:1", {"caller": "src/server/old.ts:10", "sql": "UPDATE transactions SET a = 1"}]')
    callers, writers = load_baseline(f)
    assert callers == {"src/server/x.ts:1", "src/server/old.ts:10"}
    assert writers == [{"caller": "src/server/old.ts:10", "sql": "UPDATE transactions SET a = 1"}]
    assert read_probe_events(tmp_path / "missing.jsonl") == []
    ev = tmp_path / "probe.jsonl"
    ev.write_text('{"kind": "raw_write", "caller": "unknown"}\n\n')
    assert read_probe_events(ev) == [{"kind": "raw_write", "caller": "unknown"}]
