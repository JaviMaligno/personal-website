from aa.equivalence import compare
from aa.suite import SuiteResult


def test_identical_sets_are_equivalent():
    a = SuiteResult(passed={"f::x", "f::y"}, failed={"g::z"})
    b = SuiteResult(passed={"f::x", "f::y", "src/server/domain/money.test.ts::new"},
                    failed={"g::z"})
    assert compare(a, b, excluded={"g::z"}, allow_new_passing_prefix="src/server/domain/") == []


def test_regression_is_reported():
    a = SuiteResult(passed={"f::x"})
    b = SuiteResult(failed={"f::x"})
    assert compare(a, b, excluded=set()) == ["f::x"]


def test_new_test_outside_domain_or_failing_is_a_difference():
    a = SuiteResult(passed={"f::x"})
    b = SuiteResult(passed={"f::x", "other::new"}, failed={"src/server/domain/money.test.ts::bad"})
    assert compare(a, b, excluded=set(), allow_new_passing_prefix="src/server/domain/") == [
        "other::new", "src/server/domain/money.test.ts::bad"]


def test_test_missing_on_one_side_is_a_difference():
    a = SuiteResult(passed={"f::x", "f::y"})
    b = SuiteResult(passed={"f::x"}, skipped={"f::y"})
    assert compare(a, b, excluded=set()) == ["f::y"]


def test_round_trip_json():
    r = SuiteResult(passed={"a"}, failed={"b"}, skipped={"c"})
    back = SuiteResult.from_json(r.to_json())
    assert (back.passed, back.failed, back.skipped) == ({"a"}, {"b"}, {"c"})
