from aa.suite import parse_vitest_json

REPORT = {
    "testResults": [
        {
            "name": "/x/packages/loot-core/src/server/db/index.test.ts",
            "assertionResults": [
                {"fullName": "db insert works", "status": "passed"},
                {"fullName": "db update fails", "status": "failed"},
                {"fullName": "db skip", "status": "pending"},
            ],
        }
    ]
}


def test_parse_vitest_json_ids_relative_to_loot_core():
    r = parse_vitest_json(REPORT, root="/x/packages/loot-core")
    assert r.passed == {"src/server/db/index.test.ts::db insert works"}
    assert r.failed == {"src/server/db/index.test.ts::db update fails"}
    assert r.skipped == {"src/server/db/index.test.ts::db skip"}


def test_parse_vitest_json_file_load_failure_counts_once():
    report = {"testResults": [{"name": "/x/packages/loot-core/src/a.test.ts",
                               "status": "failed", "assertionResults": []}]}
    r = parse_vitest_json(report, root="/x/packages/loot-core")
    assert r.failed == {"src/a.test.ts::<load>"}


def test_node_mismatch_reports_expected_and_actual(tmp_path):
    from aa.suite import node_mismatch
    (tmp_path / ".nvmrc").write_text("v24.18.1\n")
    assert node_mismatch(tmp_path, actual="v24.18.1") is None
    assert node_mismatch(tmp_path, actual="v22.14.0") == ("v24.18.1", "v22.14.0")
    assert node_mismatch(tmp_path / "missing", actual="v22.14.0") is None


# --- fast-check seed + kept logs (freeze gate 2026-10-06) -----------------------------

import os  # noqa: E402
import stat  # noqa: E402

from aa import suite as suite_mod  # noqa: E402

STUB_YARN = """#!/bin/bash
for a in "$@"; do case $a in --outputFile=*) OUT=${a#--outputFile=};; esac; done
[[ " $* " == *" --config vitest.aa-seed.config.ts "* ]] || exit 7
[ -e vitest.aa-seed.config.ts ] && [ -e src/mocks/aa-seed.setup.ts ] || exit 8
echo "stderr line" >&2
st=${STUB_STATUS:-passed}
printf '{"testResults":[{"name":"%s/src/a.test.ts","status":"%s","assertionResults":[{"fullName":"a","status":"%s"}]}]}' "$PWD" $st $st > "$OUT"
[ $st = passed ]
"""


def _stub_tree(tmp_path, monkeypatch, status):
    tree = tmp_path / "tree"
    (tree / suite_mod.LOOT / "src" / "mocks").mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    y = bin_dir / "yarn"
    y.write_text(STUB_YARN)
    y.chmod(y.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    monkeypatch.setenv("STUB_STATUS", status)
    return tree


def test_run_suite_is_seeded_and_cleans_up_no_logs_on_success(tmp_path, monkeypatch):
    tree = _stub_tree(tmp_path, monkeypatch, "passed")
    logs = tmp_path / "logs"
    res = suite_mod.run_suite(tree, log_dir=logs, label="suite-A")
    assert res.passed == {"src/a.test.ts::a"} and not res.failed
    loot = tree / suite_mod.LOOT
    assert not (loot / suite_mod.SEED_DST).exists() and not (loot / suite_mod.SEED_CONFIG_DST).exists()
    assert not logs.exists()


def test_run_suite_keeps_report_and_stderr_on_failure(tmp_path, monkeypatch):
    tree = _stub_tree(tmp_path, monkeypatch, "failed")
    logs = tmp_path / "logs"
    res = suite_mod.run_suite(tree, log_dir=logs, label="suite-APL")
    assert res.failed == {"src/a.test.ts::a"}
    (d,) = list(logs.iterdir())
    assert d.name.startswith("suite-APL-")
    assert "stderr line" in (d / "stderr.log").read_text()
    assert '"status":"failed"' in (d / "report.json").read_text()
    assert (d / "failed.txt").read_text() == "src/a.test.ts::a\n"
    assert "returncode=1" in (d / "cmd.txt").read_text()


def test_keep_logs_on_host_timeout_without_report(tmp_path):
    run = suite_mod.VitestRun(["yarn", "vitest"], None, "out", "err")
    res = suite_mod.result_from_report(tmp_path / "missing.json", tmp_path, run)
    assert res.failed == {"<suite>::<host timeout>"}
    d = suite_mod.keep_logs(tmp_path / "logs", "probe-A", run, res, {"report.json": tmp_path / "missing.json"})
    assert d is not None and (d / "stderr.log").read_text() == "err" and not (d / "report.json").exists()
