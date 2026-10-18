"""Suite equivalence between two conditions (Task 3, Step 7).

A and A+ must give identical pass/fail sets on the full loot-core suite; the only
allowed difference is a new passing test under the domain layer (money.test.ts).
"""
from __future__ import annotations

from aa.suite import SuiteResult

DOMAIN_TEST_PREFIX = "src/server/domain/"


def _state(r: SuiteResult, tid: str) -> str:
    return "p" if tid in r.passed else "f" if tid in r.failed else "-"


def compare(a: SuiteResult, b: SuiteResult, excluded: set[str] | frozenset[str],
            allow_new_passing_prefix: str | None = None) -> list[str]:
    """Test ids whose pass/fail state differs between a and b (empty = equivalent).

    A test missing from one side (not run, or skipped) counts as a difference,
    except a test that only b has and that passes under allow_new_passing_prefix.
    """
    diff = []
    for tid in sorted((a.passed | a.failed | b.passed | b.failed) - set(excluded)):
        sa, sb = _state(a, tid), _state(b, tid)
        if sa == sb:
            continue
        if (sa == "-" and sb == "p" and allow_new_passing_prefix
                and tid.startswith(allow_new_passing_prefix)):
            continue
        diff.append(tid)
    return diff
