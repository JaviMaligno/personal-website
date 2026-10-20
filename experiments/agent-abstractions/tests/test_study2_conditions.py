"""Study 2, Task 1: conditions R/F in config, CLI and image builds."""
import json
from pathlib import Path

import pytest

from aa import cli, config
from aa.cli import build_parser


def test_study1_conditions_unchanged():
    assert config.CONDITIONS == ("A", "AL", "AP", "APL")
    assert config.CONDITIONS2 == ("R", "F")
    assert config.ALL_CONDITIONS[:6] == config.CONDITIONS + config.CONDITIONS2


def test_r_and_f_patches_exist_and_start_from_lint_script():
    for cond, rel in (("R", "study2/r.patch"), ("F", "study2/f.patch")):
        assert config.CONDITION_PATCHES[cond] == ("lint-script.patch", rel)
        assert (config.PATCHES / rel).is_file()


@pytest.mark.parametrize("argv,func", [
    (["variant", "build", "R"], "_cmd_variant_build"),
    (["variant", "install", "F"], "_cmd_variant_install"),
    (["suite", "baseline", "--cond", "R"], "_cmd_suite_baseline"),
    (["suite", "baseline", "--cond", "A", "--study2"], "_cmd_suite_baseline"),
    (["equivalence", "R", "F"], "_cmd_equivalence"),
    (["equivalence", "A", "R"], "_cmd_equivalence"),
    (["image", "build", "F"], "_cmd_image_build"),
])
def test_parser_accepts_r_and_f(argv, func):
    assert build_parser().parse_args(argv).func.__name__ == func


def test_image_targets():
    from aa.runner import image_target
    assert [image_target(c) for c in config.CONDITIONS] == ["actual"] * 4
    assert [image_target(c) for c in config.CONDITIONS2] == ["study2"] * 2


def test_dockerfile_last_stage_is_study2_and_study1_builds_target_actual():
    # An untargeted `docker build` takes the last stage; study 1 must keep building
    # `actual` (unchanged instructions), only R/F get the jscpd stage.
    df = (config.ROOT / "substrate" / "docker" / "Dockerfile").read_text()
    stages = [ln.split()[-1] for ln in df.splitlines() if ln.startswith("FROM ")]
    assert stages == ["cli", "actual", "study2"]
    assert "jscpd@5.4.0" in df.split("AS study2", 1)[1]
    actual_stage = df.split("FROM cli AS actual", 1)[1].split("FROM actual AS study2", 1)[0]
    instructions = [ln for ln in actual_stage.splitlines() if not ln.lstrip().startswith("#")]
    assert not any("jscpd" in ln for ln in instructions)


def test_build_image_passes_target(monkeypatch, tmp_path):
    import subprocess

    from aa import runner
    calls = []
    real_run = subprocess.run

    def fake_run(argv, *a, **kw):
        if argv[:2] == ["docker", "build"]:
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0)
        return real_run(argv, *a, **kw)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setattr(config, "WORK", tmp_path)
    for cond in ("A", "R"):
        v = tmp_path / "variants" / cond
        v.mkdir(parents=True)
        for args in (["init", "-q"], ["-c", "user.name=t", "-c", "user.email=t@t",
                                     "commit", "-q", "--allow-empty", "-m", "x"]):
            real_run(["git", *args], cwd=v, check=True)
        runner.build_image(cond)
    targets = [c[c.index("--target") + 1] for c in calls]
    assert targets == ["actual", "study2"]


def _write_baseline(path: Path, passed, failed=()):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"passed": sorted(passed), "failed": sorted(failed),
                                "skipped": []}))


def test_equivalence_study2_reads_study2_dir_and_has_no_allowance(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "WORK", tmp_path)
    monkeypatch.setattr(config, "STUDY2_WORK", tmp_path / "study2")
    # Study-1 file for A must be ignored for R/F comparisons.
    _write_baseline(tmp_path / "baseline-A.json", {"x"})
    _write_baseline(tmp_path / "study2" / "baseline-A.json", {"t1", "t2"})
    _write_baseline(tmp_path / "study2" / "baseline-R.json", {"t1", "t2"})
    # A new passing test under the A+ domain prefix is a difference in study 2.
    _write_baseline(tmp_path / "study2" / "baseline-F.json",
                    {"t1", "t2", "src/server/domain/x.test.ts::new"})
    assert cli.main(["equivalence", "A", "R"]) == 0
    assert "equivalent (0 differences)" in capsys.readouterr().out
    assert cli.main(["equivalence", "R", "F"]) == 1
    assert "src/server/domain/x.test.ts::new" in capsys.readouterr().out


def test_equivalence_study2_missing_a_hints_flag(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "WORK", tmp_path)
    monkeypatch.setattr(config, "STUDY2_WORK", tmp_path / "study2")
    _write_baseline(tmp_path / "study2" / "baseline-R.json", {"t1"})
    assert cli.main(["equivalence", "A", "R"]) == 2
    assert "--cond A --study2" in capsys.readouterr().err


def test_equivalence_study1_unchanged(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "WORK", tmp_path)
    _write_baseline(tmp_path / "baseline-A.json", {"t1"})
    _write_baseline(tmp_path / "baseline-AP.json", {"t1", "src/server/domain/m.test.ts::ok"})
    assert cli.main(["equivalence", "A", "AP"]) == 0


def test_probe_diff():
    from aa.probe2 import diff_probe
    a = {"failed": [], "db": {"x": {"ok": 1}, "y": {"ok": 2}}, "template": {"t": {"ok": 0}}}
    assert diff_probe(a, json.loads(json.dumps(a))) == []
    b = {"failed": [], "db": {"x": {"ok": 1}, "y": {"error": "boom"}}, "template": {}}
    assert diff_probe(a, b) == ["db:y", "template:t"]
    c = {"failed": ["f::t"], "db": None, "template": {"t": {"ok": 0}}}
    assert diff_probe(a, c) == ["<probe test failed on b> f::t", "<db.json missing on b>"]


def test_probe_files_exist_and_routes():
    from aa.probe2 import PROBE_DIR, PROBE_FILES
    for src, dst in PROBE_FILES.items():
        assert (PROBE_DIR / src).is_file()
        assert dst.startswith("src/") and dst.endswith(".test.ts")
    assert build_parser().parse_args(["probe2"]).func.__name__ == "_cmd_probe2"
