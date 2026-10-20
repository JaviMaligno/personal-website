"""Chain sanity (plan Task 2, Review Focus 3): pure parts, no Docker."""
import json
import re
from pathlib import Path

from aa import chains
from aa.chains import (_name_pattern, _split_name, reference_leaks, reference_script,
                       untouched_script, untouched_verdicts)

LOOT = "packages/loot-core"
ROOT = f"/work/actual/{LOOT}"


def _report(path: Path, tests: dict[str, str], file: str = "src/x.test.ts") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"testResults": [{
        "name": f"{ROOT}/{file}", "status": "failed",
        "assertionResults": [{"fullName": n, "status": st} for n, st in tests.items()]}]}))


def test_name_pattern_matches_only_the_full_name():
    full = "month-wide actions (hidden) skip $x.y #fixed"
    pat = re.compile(_name_pattern(full))
    assert pat.match(full)
    assert not pat.match(full + " too")
    assert not pat.match("other " + full)
    # vitest matches describe > test
    assert pat.match("month-wide actions (hidden) > skip $x.y #fixed")


def test_split_name_with_and_without_file():
    hidden = [f"{LOOT}/src/a.test.ts", f"{LOOT}/src/b.test.ts"]
    assert _split_name("a test", hidden) == (["src/a.test.ts", "src/b.test.ts"], "a test")
    assert _split_name(f"{LOOT}/src/b.test.ts::d t", hidden) == (["src/b.test.ts"], "d t")


def test_untouched_verdicts(tmp_path):
    tests = [("T1::a", ["src/x.test.ts"], "a"), ("T1::b", ["src/x.test.ts"], "b"),
             ("T1::c", ["src/x.test.ts"], "c"), ("T1::d", ["src/x.test.ts"], "d"),
             ("T1::e", ["src/x.test.ts"], "e")]
    u = tmp_path / "u"
    _report(u / "0.json", {"a": "failed", "b": "skipped"})        # ok
    _report(u / "1.json", {"a": "skipped", "b": "passed"})        # passes untouched
    _report(u / "2.json", {"c": "failed", "a": "failed"})         # another test ran
    _report(u / "3.json", {"a": "skipped"})                       # did not run
    v = untouched_verdicts(tests, tmp_path)                       # 4: no report
    assert [v[k]["ok"] for k in ("T1::a", "T1::b", "T1::c", "T1::d", "T1::e")] == \
        [True, False, False, False, False]
    assert v["T1::b"]["why"] == "passed"
    assert v["T1::d"]["why"] == "did not run"
    assert v["T1::e"]["why"] == "no report"


def test_scripts_shape():
    s = untouched_script([("T1::a", ["src/x.test.ts"], "a b")], [f"{LOOT}/src/x.test.ts"])
    assert "-t '^a(?: | > )b$'" in s and "/out/u/0.json" in s
    r = reference_script([[f"{LOOT}/src/x.test.ts"], [f"{LOOT}/src/y.test.ts"]])
    # cumulative: step 2 runs both steps' hidden tests, after both patches
    assert r.index("/refs/T1.patch") < r.index("/refs/T2.patch")
    t2 = r[r.index("/refs/T2.patch"):]
    assert "src/x.test.ts" in t2 and "src/y.test.ts" in t2
    assert "yarn lint" in t2 and "yarn tsgo -b" in t2


def test_reference_leaks(tmp_path, monkeypatch):
    z = tmp_path / "Z9"
    (z / "T1" / "hidden" / LOOT / "src").mkdir(parents=True)
    (z / "chain.json").write_text(json.dumps({"zone": "Z9", "steps": ["T1"],
                                              "zone_files": ["server/a.ts"]}))
    (z / "T1" / "statement.md").write_text("Public Title of the step\n")
    (z / "T1" / "consumers.json").write_text(json.dumps({"skips the secret thing": "c"}))
    (z / "T1" / "hidden" / LOOT / "src" / "s.test.ts").write_text(
        "it('skips the secret thing', () => expect(x).toBe('very-specific-sentinel'));\n"
        "// 'public title of the step'\n")
    (z / "T1" / "reference.R.patch").write_text(
        f"diff --git a/{LOOT}/src/a.ts b/{LOOT}/src/a.ts\n--- a\n+++ b\n"
        "+const v = 'very-specific-sentinel';\n+// public title of the step\n"
        f"diff --git a/{LOOT}/src/s.test.ts b/{LOOT}/src/s.test.ts\n+x\n")
    monkeypatch.setattr(chains.config, "WORK", tmp_path / "nowork")
    r = reference_leaks("Z9", "R", tmp_path)["T1"]
    assert r["hidden_or_test_files"] == [f"{LOOT}/src/s.test.ts"]
    assert r["literals"] == ["very-specific-sentinel"]
    assert r["test_names"] == []


# --- statement leak check (spec amendment 2026-10-08) ---------------------------

import pytest  # noqa: E402

from aa.chains import check_statements2, statement_leaks2  # noqa: E402


@pytest.mark.parametrize("zone,text,bad", [
    ("Z1", "Month-wide budget actions leave hidden categories untouched.", False),
    ("Z1", "Every month-wide budget action leaves hidden categories untouched.", True),
    ("Z1", "Expected behaviour, for every one of these actions:", True),
    ("Z1", "Make sure all of them skip hidden categories.", True),
    ("Z1", "Actions such as copying last month's budget or setting budgets to zero.", True),
    ("Z1", "It fills in the budget of every category for that month.", False),
    ("Z2", "The rule must hold consistently: nothing in Actual may use the middle.", True),
    ("Z2", "It gives the same figure Actual uses everywhere else.", True),
    ("Z2", "The forecast and the upcoming-schedules preview use the end of the range.", True),
    ("Z2", "Change the rule: the end of the range furthest from zero.", False),
    ("Z3", "Linking works as for GoCardless and SimpleFIN accounts.", True),
    ("Z3", "...and every rule that applies when linking a bank account.", True),
    ("Z4", "It must hold wherever the app works out a schedule's dates.", True),
    ("Z4", "An occurrence that falls on a Saturday is skipped.", False),
])
def test_statement_leaks2(zone, text, bad):
    assert bool(statement_leaks2(text, zone)) is bad


def test_statement_leaks2_allows_introduced_method_only():
    text = "Expose it as `budget/set-last-month-spending`."
    assert statement_leaks2(text, "Z1")
    assert not statement_leaks2(text, "Z1", frozenset({"budget/set-last-month-spending"}))


def test_committed_statements_are_clean():
    assert check_statements2() == {}
