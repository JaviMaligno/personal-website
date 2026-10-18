import json
import os
import re
import shutil
import subprocess

import pytest

from aa import checker, config
from aa.suite import SuiteResult

CANARY_RAW = {"kind": "raw_write", "table": "categories", "sql": "UPDATE categories SET hidden = 1 WHERE id = ?",
              "caller": "src/server/aa-canary.test.ts:15"}
CANARY_BATCH = {"kind": "raw_write", "table": "category_groups",
                "sql": "UPDATE category_groups SET hidden = 1 WHERE id = ?",
                "caller": "src/server/aa-canary.test.ts:40"}
CANARY_MONEY = {"kind": "non_integer_money", "table": "transactions", "column": "amount", "value": 12.5,
                "caller": "src/server/aa-canary.test.ts:25"}
SUITE_OK = SuiteResult(passed={"src/server/aa-canary.test.ts::aa probe canary: raw UPDATE categories",
                               "src/server/aa-canary.test.ts::aa probe canary: non-integer amount"})


CANARY_ALL = [CANARY_RAW, CANARY_BATCH, CANARY_MONEY]


def test_canary_ok_when_all_events_from_canary():
    assert checker.canary_problems(CANARY_ALL, SUITE_OK) == []


def test_canary_fails_when_probe_records_nothing():
    probs = checker.canary_problems([], SUITE_OK)
    assert len(probs) == 3 and "raw_write" in probs[0] and "batchMessages" in probs[1]
    assert "non_integer_money" in probs[2]


def test_canary_fails_when_raw_write_inside_batch_is_missed():
    # A probe that treats "any sync/ frame on the stack" as CRDT-engine work hides it.
    probs = checker.canary_problems([CANARY_RAW, CANARY_MONEY], SUITE_OK)
    assert len(probs) == 1 and "category_groups" in probs[0]


def test_canary_fails_when_events_not_attributed_to_canary():
    # The probe fired, but the caller points elsewhere (e.g. probe file name broke the
    # frame filter) -> attribution broken, the checker would never match agent lines.
    raw = dict(CANARY_RAW, caller="src/mocks/aa-probe.setup.ts:62")
    batch = dict(CANARY_BATCH, caller="src/server/sync/index.ts:716")
    money = dict(CANARY_MONEY, caller="unknown")
    assert len(checker.canary_problems([raw, batch, money], SUITE_OK)) == 3


def test_canary_fails_when_tests_did_not_run_or_failed():
    assert any("did not run" in p for p in checker.canary_problems(CANARY_ALL, SuiteResult()))
    bad = SuiteResult(failed={"<suite>::<no report>"})
    assert any("failed" in p for p in checker.canary_problems(CANARY_ALL, bad))


def test_run_canary_uses_runner_with_canary_file(tmp_path):
    calls = []

    def fake(tree, files, timeout, canary):
        calls.append((tree, files, canary))
        return SUITE_OK, CANARY_ALL

    r = checker.run_canary(tmp_path, runner=fake)
    assert r.ok and calls == [(tmp_path, [checker.CANARY_DST], True)]
    r2 = checker.run_canary(tmp_path, runner=lambda *a, **k: (SUITE_OK, []))
    assert not r2.ok


def test_baseline_entries_exclude_canary_and_dedupe():
    w = {"kind": "raw_write", "table": "dashboard", "sql": "INSERT INTO dashboard", "caller": "src/server/migrate/migrations.ts:107"}
    out = checker.baseline_entries([w, dict(w), CANARY_RAW, CANARY_MONEY])
    assert out == [{"caller": "src/server/migrate/migrations.ts:107", "sql": "INSERT INTO dashboard"}]


def test_probe_installed_copies_and_always_removes(tmp_path):
    loot = tmp_path
    (loot / "src" / "mocks").mkdir(parents=True)
    (loot / "src" / "server").mkdir(parents=True)
    with pytest.raises(RuntimeError):
        with checker.probe_installed(loot, canary=True):
            for d in (checker.PROBE_DST, checker.CONFIG_DST, checker.CANARY_DST,
                      checker.SEED_DST, checker.SEED_CONFIG_DST):
                assert (loot / d).exists()
            raise RuntimeError("boom")
    for d in (checker.PROBE_DST, checker.CONFIG_DST, checker.CANARY_DST,
              checker.SEED_DST, checker.SEED_CONFIG_DST):
        assert not (loot / d).exists()


def test_vitest_probe_cmd_uses_wrapper_config_not_setupfiles_flag():
    cmd = checker.vitest_probe_cmd("/out/report.json", ["src/a.test.ts"])
    assert "--setupFiles" not in cmd
    assert cmd[cmd.index("--config") + 1] == "vitest.aa.config.ts"
    assert cmd[-1] == "src/a.test.ts"
    assert f"--testTimeout={checker.PROBE_TEST_TIMEOUT_MS}" in cmd
    assert f"--hookTimeout={checker.PROBE_HOOK_TIMEOUT_MS}" in cmd
    assert checker.PROBE_TEST_TIMEOUT_MS == 50_000 and checker.PROBE_HOOK_TIMEOUT_MS == 100_000
    assert not any(a.startswith("--testTimeout") for a in
                   checker.vitest_probe_cmd("/r.json", [], raised_timeouts=False))


def test_vitest_clean_cmd_has_no_probe_and_default_timeouts():
    cmd = checker.vitest_clean_cmd("/out/report.json", ["src/a.test.ts"])
    assert cmd[cmd.index("--config") + 1] == "vitest.aa-seed.config.ts"  # seed only, no probe
    assert not any("Timeout" in a for a in cmd)
    assert "--outputFile=/out/report.json" in cmd and cmd[-1] == "src/a.test.ts"


def test_probe_config_extends_seed_config_and_seed_is_fixed():
    probe_cfg = checker.CONFIG_SRC.read_text()
    assert "from './vitest.aa-seed.config'" in probe_cfg
    seed_cfg = checker.SEED_CONFIG_SRC.read_text()
    assert "from './vitest.config'" in seed_cfg and "./src/mocks/aa-seed.setup.ts" in seed_cfg
    assert checker.SEED_DST == "src/mocks/aa-seed.setup.ts"
    seed = checker.SEED_SRC.read_text()
    assert re.search(r"AA_FAST_CHECK_SEED = \d+;", seed)
    assert "fc.configureGlobal({ ...fc.readConfigureGlobal(), seed: AA_FAST_CHECK_SEED })" in seed


@pytest.mark.integration
@pytest.mark.skipif(os.environ.get("AA_INTEGRATION") != "1", reason="set AA_INTEGRATION=1 (needs work/actual-base + Node 24.18.1)")
def test_canary_on_base_tree():
    tree = config.WORK / "actual-base"
    if not (tree / "node_modules").exists() or shutil.which("yarn") is None:
        pytest.skip("work/actual-base not installed")
    node = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
    if node != (tree / ".nvmrc").read_text().strip():
        pytest.skip(f"node {node} is not the pinned version")
    r = checker.run_canary(tree)
    assert r.ok, r.problems


def test_money_events_exclude_canary():
    base_money = {"kind": "non_integer_money", "table": "zero_budgets", "column": "amount",
                  "value": 0.5, "caller": "src/server/budget/actions.ts:10"}
    raw = {"kind": "raw_write", "table": "categories", "caller": "src/server/x.ts:1"}
    assert checker.money_events([CANARY_MONEY, CANARY_RAW, raw, base_money]) == [base_money]
    assert checker.is_canary_event(CANARY_RAW) and not checker.is_canary_event(raw)


def test_baseline_document_is_readable_by_load_baseline(tmp_path):
    from aa.static_check import load_baseline
    w = [{"caller": "src/server/migrate/migrations.ts:107", "sql": "INSERT INTO dashboard"}]
    doc = checker.baseline_document({"A": {"passed": 1}}, w)
    assert doc["writers"] == w and doc["non_integer_money"] == [] and doc["runs"]["A"]["passed"] == 1
    f = tmp_path / "b.json"
    f.write_text(json.dumps(doc))
    assert load_baseline(f) == ({"src/server/migrate/migrations.ts:107"}, w)
