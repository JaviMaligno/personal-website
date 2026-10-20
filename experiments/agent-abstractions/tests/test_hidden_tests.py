"""Hidden-test rewrite for A+ (aa.hidden_tests): replayed on real Actual test files.

Input = the file in the A variant, expected = the same file in the AP variant (the
rewrite done by hand when A+ was built). Formatting is normalised (whitespace and
trailing commas: prettier re-wraps long lines; loot-core's lint ignores test files).
"""
import re
import subprocess
from pathlib import Path

import pytest

from aa import config
from aa.hidden_tests import (RESET_COMMENT, exported_names, moved_names,
                             rewrite_for_condition)

FIX = Path(__file__).parent / "fixtures" / "hidden_tests"
VARIANTS = config.WORK / "variants"
PAIRS = sorted(p.relative_to(FIX / "A").as_posix() for p in (FIX / "A").rglob("*.test.ts"))
NAMES = moved_names(Path("/nonexistent"))  # from substrate/patches/aplus.patch


def norm(text: str) -> str:
    return re.sub(r",(?=[)}\]])", "", re.sub(r"\s+", "", text))


def loot(rel: str) -> str:
    return f"{config.LOOT}/{rel}"


# --- moved names ----------------------------------------------------------------------

def test_moved_names_from_aplus_patch():
    assert {"update", "insert", "insertWithUUID", "delete_", "deleteAll", "insertWithSchema",
            "updateWithSchema", "insertAccount", "insertTransaction", "moveSchedule",
            "updateTag"} <= NAMES
    assert not {"all", "first", "runQuery", "getTransaction", "getAccounts"} & NAMES
    assert len(NAMES) == 36


@pytest.mark.skipif(not (VARIANTS / "AP" / config.LOOT).exists(), reason="AP variant not built")
def test_moved_names_variant_matches_patch():
    assert moved_names(VARIANTS) == NAMES


def test_exported_names_shapes():
    src = ("export async function a() {}\nexport function b() {}\nexport const c = 1;\n"
           "export { d, e as f, type G };\nfunction hidden() {}\n")
    assert exported_names(src) == {"a", "b", "c", "d", "f"}


# --- replay on real Actual test files (vendored A/AP pairs) ---------------------------

def test_enough_real_files():
    assert len(PAIRS) >= 5


@pytest.mark.parametrize("rel", PAIRS)
@pytest.mark.parametrize("cond", ["AP", "APL"])
def test_replay_real_file(rel, cond):
    a = (FIX / "A" / rel).read_text()
    ap = (FIX / "AP" / rel).read_text()
    assert a != ap
    out = rewrite_for_condition(a, cond, loot(rel), NAMES)
    assert norm(out) == norm(ap)
    # the AP version is a fixed point (nothing left to move)
    assert rewrite_for_condition(ap, cond, loot(rel), NAMES) == ap


@pytest.mark.parametrize("rel", PAIRS)
@pytest.mark.parametrize("cond", ["A", "AL"])
def test_identity_on_a_and_al(rel, cond):
    a = (FIX / "A" / rel).read_text()
    assert rewrite_for_condition(a, cond, loot(rel), NAMES) == a


def test_mock_cases_get_reset_and_companion_mock():
    rel = "src/server/budget/cleanup-template-notes.test.ts"
    out = rewrite_for_condition((FIX / "A" / rel).read_text(), "AP", loot(rel), NAMES)
    assert (RESET_COMMENT + "vi.hoisted(() => vi.resetModules());\nvi.mock('#server/db');\n"
            "vi.mock('#server/db/write');\n") in out


@pytest.mark.skipif(not (VARIANTS / "AP" / config.LOOT).exists(), reason="variants not built")
def test_replay_every_actual_test_file():
    """All of Actual's test files: the 33 rewritten ones match AP, the rest are untouched."""
    files = subprocess.run(["git", "ls-files", "*.test.ts", "*.test.tsx", "*.test.js"],
                           cwd=VARIANTS / "A", capture_output=True, text=True, check=True).stdout.split()
    changed = 0
    for f in files:
        a, ap = (VARIANTS / "A" / f).read_text(), (VARIANTS / "AP" / f).read_text()
        out = rewrite_for_condition(a, "AP", f, NAMES)
        assert norm(out) == norm(ap), f
        if a == ap:
            assert out == a, f
        else:
            changed += 1
    assert changed == 33


# --- synthetic edge cases -------------------------------------------------------------

def test_named_import_moves_to_write_module():
    src = ("import { first, insertAccount, type DbAccount } from '#server/db';\n\n"
           "test('x', async () => { await insertAccount({}); await first('q'); });\n")
    out = rewrite_for_condition(src, "AP", None, NAMES)
    assert "import { first, type DbAccount } from '#server/db';" in out
    assert "import { insertAccount } from '#server/db/write';" in out


def test_named_import_fully_moved_is_dropped():
    src = "import { insertAccount } from '#server/db';\n\ninsertAccount({});\n"
    out = rewrite_for_condition(src, "APL", None, NAMES)
    assert "from '#server/db';" not in out and "import { insertAccount } from '#server/db/write';" in out


def test_spy_on_moved_function():
    src = ("import * as db from '#server/db';\n\n"
           "vi.spyOn(db, 'insertAccount');\nvi.spyOn(db, 'first');\n")
    out = rewrite_for_condition(src, "AP", None, NAMES)
    assert "vi.spyOn(dbWrite, 'insertAccount')" in out and "vi.spyOn(db, 'first')" in out
    assert "import * as db from '#server/db';\nimport * as dbWrite from '#server/db/write';" in out


def test_prefix_names_are_not_rewritten():
    src = "import * as db from '#server/db';\n\ndb.updateFoo(); db.update('t', {}); x.db.update();\n"
    out = rewrite_for_condition(src, "AP", None, NAMES)
    assert "db.updateFoo()" in out and "dbWrite.update('t', {})" in out and "x.db.update()" in out


def test_factory_mock_left_alone_and_no_reset_without_moved_use():
    src = ("import * as db from '#server/db';\n\nvi.mock('#server/db', () => ({ first: vi.fn() }));\n"
           "db.first();\n")
    assert rewrite_for_condition(src, "AP", None, NAMES) == src


def test_relative_import_needs_path_to_resolve():
    src = "import * as db from './index';\n\ndb.insertAccount({});\n"
    other = "packages/loot-core/src/server/foo/a.test.ts"
    assert rewrite_for_condition(src, "AP", other, NAMES) == src  # ./index is not the db module
    out = rewrite_for_condition(src, "AP", f"{config.LOOT}/src/server/db/a.test.ts", NAMES)
    assert out.startswith("import * as dbWrite from '#server/db/write';\n\n")
    assert "import * as db from" not in out


def test_existing_write_import_is_reused():
    src = ("import * as db from '#server/db';\nimport * as dbWrite from '#server/db/write';\n\n"
           "db.insertAccount({}); dbWrite.update('t', {}); db.first();\n")
    out = rewrite_for_condition(src, "AP", None, NAMES)
    assert out.count("from '#server/db/write'") == 1 and "dbWrite.insertAccount" in out
