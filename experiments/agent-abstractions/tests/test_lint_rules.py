"""Runs the RuleTester suite (substrate/lint/rules.test.mjs) against the AL and APL
variant trees (plan Task 4, Step 1). Skipped when a variant is not built and
installed with the eslint devDependencies (`aa variant build` + `aa variant
install`, the same install-lint-deps.sh step the Docker image runs), since eslint
is resolved from the variant."""
from __future__ import annotations

import shutil
import subprocess

import pytest

from aa.config import LOOT, ROOT, WORK

TESTS = ROOT / "substrate" / "lint" / "rules.test.mjs"


@pytest.mark.parametrize("cond", ["AL", "APL"])
def test_rule_tester_suite(cond: str) -> None:
    loot = WORK / "variants" / cond / LOOT
    if not (loot / "node_modules" / "eslint").exists() and not (
        WORK / "variants" / cond / "node_modules" / "eslint").exists():
        pytest.skip(f"{loot} not installed with eslint")
    if not (loot / "eslint-rules").exists():
        pytest.skip(f"{loot} has no eslint-rules (variant built before Task 4?)")
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not on PATH")
    r = subprocess.run([node, "--test", str(TESTS)], env={"LOOT_CORE": str(loot), "PATH": ""},
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]
