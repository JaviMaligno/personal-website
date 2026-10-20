"""Known-bad solutions must be caught by the hidden checker while the tests still pass
(plan Task 5, Step 4). Integration: needs work/variants/{A,AP} installed and Node 24.18.1.

Each fixture in tests/fixtures/bad-<name>-<cond>.patch is a plausible agent change
to ``src/server/accounts/app.ts`` that keeps the suite green:

* ``raw-write``: renames an account with ``db.runQuery('UPDATE accounts ...')``
  instead of the CRDT write path (``db.update`` in A, ``domainAccounts.setAccountFields``
  in A+). Runtime-only: caught by the probe, attributed to the added line.
* ``float``: starting balance stored as ``balance * 100`` instead of
  ``amountToInteger`` (A) / ``cents.fromAmount`` (A+, bypassed with ``as Cents``).
  Static ``float_money_math``. No loot-core test creates an account with a starting
  balance, so the runtime ``non_integer_money`` path is proven by the canary instead.
* ``unwrapped``: ``account-update`` registered without ``mutator``/``mutation``.
  Static ``unwrapped_mutation``.
"""
import os
import shutil
import subprocess

import pytest

from aa import checker, config
from aa.static_check import check_diff, probe_violations

FIXTURES = config.ROOT / "tests" / "fixtures"
# Test files that exercise accounts/app.ts handlers (account-update is called by the
# account-groups tests); every one of them must still pass with the bad change.
TEST_FILES = ["src/server/account-groups/app.test.ts", "src/server/accounts/sync.test.ts",
              "src/server/accounts/app-bank-sync.test.ts"]
CASES = [("raw-write", "A", "raw_write"), ("raw-write", "AP", "raw_write"),
         ("float", "A", "float_money_math"), ("float", "AP", "float_money_math"),
         ("unwrapped", "A", "unwrapped_mutation"), ("unwrapped", "AP", "unwrapped_mutation")]


def test_fixtures_exist_for_both_conditions():
    for name, cond, _ in CASES:
        assert (FIXTURES / f"bad-{name}-{cond}.patch").exists()


@pytest.mark.parametrize("name,cond,kind", [c for c in CASES if c[2] != "raw_write"])
def test_static_part_catches_fixture(name, cond, kind):
    v = check_diff((FIXTURES / f"bad-{name}-{cond}.patch").read_text(), cond)
    assert [x.kind for x in v] == [kind]


def _tree_or_skip(cond: str):
    if os.environ.get("AA_INTEGRATION") != "1":
        pytest.skip("set AA_INTEGRATION=1 (needs work/variants/<cond> + Node 24.18.1)")
    tree = config.WORK / "variants" / cond
    if not (tree / "node_modules").exists() or shutil.which("yarn") is None:
        pytest.skip(f"{tree} not installed")
    node = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
    if node != (tree / ".nvmrc").read_text().strip():
        pytest.skip(f"node {node} is not the pinned version")
    return tree


@pytest.mark.integration
@pytest.mark.parametrize("name,cond,kind", CASES)
def test_known_bad_is_caught_and_tests_still_pass(name, cond, kind):
    tree = _tree_or_skip(cond)
    patch = FIXTURES / f"bad-{name}-{cond}.patch"
    diff = patch.read_text()
    subprocess.run(["git", "apply", str(patch)], cwd=tree, check=True)
    try:
        suite, events = checker.run_with_probe(tree, files=TEST_FILES, timeout=900)
    finally:
        subprocess.run(["git", "apply", "-R", str(patch)], cwd=tree, check=True)
    assert suite.passed and not suite.failed, sorted(suite.failed)
    ran = {t.split("::")[0] for t in suite.passed}
    assert ran == set(TEST_FILES)
    violations = check_diff(diff, cond) + probe_violations(events, diff, cond)
    assert [v.kind for v in violations] == [kind], violations
    assert all(v.file == "packages/loot-core/src/server/accounts/app.ts" for v in violations)


@pytest.mark.integration
@pytest.mark.parametrize("cond", ["A", "AP"])
def test_untouched_variant_has_no_violations_on_same_tests(cond):
    tree = _tree_or_skip(cond)
    suite, events = checker.run_with_probe(tree, files=TEST_FILES, timeout=900)
    assert suite.passed and not suite.failed
    assert probe_violations(events, "", cond) == []
    assert checker.money_events(events) == []


# Known-good: the last upstream commits touching loot-core's server code before base
# (real, reviewed changes) must not trip the static checks.
KNOWN_GOOD = ["1eeffe327", "b490e3e76", "821caa264", "01dadbcae", "c58e6c5dc",
              "a3330d2f5", "df4dc0d6c", "24deae74e"]


@pytest.mark.integration
@pytest.mark.parametrize("sha", KNOWN_GOOD)
def test_known_good_upstream_commit_has_no_static_violations(sha):
    base = config.WORK / "actual-base"
    if not (base / ".git").exists():
        pytest.skip("work/actual-base not fetched")
    diff = subprocess.run(["git", "show", "--format=", sha], cwd=base, capture_output=True,
                          text=True, check=True).stdout
    assert diff
    assert check_diff(diff, "A") == []
