import pytest

from aa.cli import build_parser


def test_parser_routes_task1_subcommands():
    p = build_parser()
    assert p.parse_args(["substrate", "fetch"]).func.__name__ == "_cmd_substrate_fetch"
    a = p.parse_args(["variant", "build", "AP"])
    assert a.cond == "AP" and a.func.__name__ == "_cmd_variant_build"
    a = p.parse_args(["suite", "baseline"])
    assert a.cond == "A" and a.func.__name__ == "_cmd_suite_baseline"


def test_parser_rejects_unknown_condition():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["variant", "build", "B"])


@pytest.mark.parametrize("argv,func", [
    (["checker", "baseline"], "_cmd_checker_baseline"),
    (["checker", "canary", "--conds", "A"], "_cmd_checker_canary"),
    (["image", "build-cli"], "_cmd_image_build_cli"),
    (["evaluate", "--all", "--workers", "3"], "_cmd_evaluate"),
    (["evaluate", "runs/x"], "_cmd_evaluate"),
    (["tasks", "preview"], "_cmd_tasks_preview"),
    (["tasks", "mine", "--since", "2024-01-01"], "_cmd_tasks_mine"),
    (["tasks", "materialise", "--sha", "abc"], "_cmd_tasks_materialise"),
    (["tasks", "check", "--task", "t01", "--force"], "_cmd_tasks_check"),
    (["tasks", "select-preview", "-v"], "_cmd_tasks_select_preview"),
    (["memo-probe", "estimate"], "_cmd_memo_estimate"),
    (["memo-probe", "run", "--workers", "2"], "_cmd_memo_run"),
    (["image", "build", "AP"], "_cmd_image_build"),
    (["run", "--agent", "codex", "--conds", "A,AP", "--tasks", "t01"], "_cmd_run"),
    (["run-one", "--agent", "claude", "--cond", "A", "--task", "t01"], "_cmd_run_one"),
    (["view", "runs/x"], "_cmd_view"),
    (["status", "--watch"], "_cmd_status"),
    (["tables"], "_cmd_tables"),
    (["equivalence", "A", "AP"], "_cmd_equivalence"),
])
def test_parser_routes_later_subcommands(argv, func):
    assert build_parser().parse_args(argv).func.__name__ == func


def test_status_and_tables_run_on_fixtures(tmp_path, monkeypatch, capsys):
    import shutil
    from pathlib import Path

    from aa import cli, config
    src = Path(__file__).parent / "fixtures" / "viewer" / "rundirs"
    runs = tmp_path / "runs"
    shutil.copytree(src, runs)
    monkeypatch.setattr(config, "RUNS", runs)
    assert cli.main(["status", "--total-per-cell", "4"]) == 0
    assert (runs / "status.html").exists()
    assert cli.main(["tables", "--runs", str(runs), "--out", str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / "tables.md").exists()


def _task(root, tid, **meta):
    import json
    d = root / tid
    d.mkdir(parents=True)
    (d / "task.json").write_text(json.dumps({
        "id": tid, "sha": tid * 4, "date": "2026-01-01", "subject": f"subj {tid}",
        "hidden_tests": [], "touched_files": [], "statement_path": "statement.md",
        "per_condition": {}, "selected": False, **meta}))
    return d


def test_tasks_select_preview(tmp_path, monkeypatch, capsys):
    import json

    from aa import cli, config
    from aa.tasks import selection_preview
    for tid in ("t1", "t2", "t3", "t4"):
        _task(tmp_path, tid)
    (tmp_path / "_ledger.json").write_text(json.dumps({
        "t1": {"sanity": "ok", "memorised": False},
        "t2": {"sanity": "dropped", "dropped": "not_discriminating"},
        "t3": {"sanity": "ok", "memorised": True},
        "t5": {"status": "dropped", "reason": "revert_conflict:AP", "subject": "s5"},
    }))
    rows = {r["id"]: r for r in selection_preview(tmp_path)}
    assert [k for k, r in rows.items() if r["survives"]] == ["t1"]
    assert {k: r["reason"] for k, r in rows.items()} == {
        "t1": None, "t2": "not_discriminating", "t3": "memorised", "t4": "unchecked",
        "t5": "revert_conflict:AP"}
    monkeypatch.setattr(config, "TASKS", tmp_path)
    assert cli.main(["tasks", "select-preview"]) == 0
    out = capsys.readouterr().out
    assert "survivors: 1 / 5" in out and "t1\t2026-01-01\tmemo=clean" in out
    assert "revert_conflict:AP\t1" in out


def test_tasks_check_runs_every_task(tmp_path, monkeypatch, capsys):
    import json

    from aa import cli, config, runner, tasks
    for tid in ("t1", "t2"):
        _task(tmp_path, tid)
    (tmp_path / "t2" / "sanity.json").write_text(json.dumps({"reason": "not_discriminating"}))
    monkeypatch.setattr(config, "TASKS", tmp_path)
    monkeypatch.setattr(runner, "image_digest", lambda tag: "sha256:x")
    seen = []
    monkeypatch.setattr(tasks, "check_and_record",
                        lambda d, root=None, **kw: seen.append(d.name))
    assert cli.main(["tasks", "check"]) == 0
    assert seen == ["t1"]  # t2 cached
    assert "t2\tnot_discriminating\t(cached" in capsys.readouterr().out
    assert cli.main(["tasks", "check", "--force", "--task", "t2"]) == 0
    assert seen == ["t1", "t2"]
    monkeypatch.setattr(runner, "image_digest", lambda tag: None if tag.endswith("APL") else "x")
    assert cli.main(["tasks", "check"]) == 2
