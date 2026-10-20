"""Pre-pilot fixes of study 3 (final review of plan Tasks 1-6): safe concurrency defaults,
runs roots inferred from the study, evaluator container names that never collide across
runs roots, and T0 evaluations serialised (exclusive of every other eval container)."""
import json
import threading
import time
from pathlib import Path

import pytest

from aa import chain_eval, chain_runner as cr, cli, config
from aa.chain_eval import ContainerGate, chain_eval_docker_argv, evaluate_all
from test_chain_eval import all_pass, fake_executor, make_chain, make_step, report


# --- item 1: concurrency defaults -----------------------------------------------------------

def _capture_run(monkeypatch):
    seen: dict = {}

    def fake_all(agent, conds, zones, chains, workers, runs_root, tasks_root, study=None,
                 t0_root=None):
        seen.update(workers=workers, study=study, runs=runs_root)
        return {}

    monkeypatch.setattr(cr, "run_all_chains", fake_all)
    return seen


def test_chain_run_workers_default_by_study(tmp_path, monkeypatch):
    make_chain(tmp_path / "t2")
    seen = _capture_run(monkeypatch)
    base = ["chain", "run", "--agent", "claude", "--tasks", str(tmp_path / "t2")]
    assert cli.main(base + ["--study", "3"]) == 0
    assert seen["workers"] == 2 == cr.STUDY_WORKERS[3]
    assert cli.main(base) == 0                                   # study 2 unchanged
    assert seen["workers"] == config.CONCURRENCY == cr.STUDY_WORKERS[2]
    assert cli.main(base + ["--study", "3", "--workers", "1"]) == 0
    assert seen["workers"] == 1


def test_container_gate_exclusive_waits_for_shared_and_blocks_new_ones():
    gate = ContainerGate()
    log: list[str] = []
    in_shared = threading.Event()
    release_shared = threading.Event()

    def shared_holder():
        with gate.shared():
            in_shared.set()
            log.append("shared-in")
            release_shared.wait(5)
            log.append("shared-out")

    def exclusive_holder():
        with gate.exclusive():
            log.append("exclusive-in")
            time.sleep(0.05)
            log.append("exclusive-out")

    def late_shared():
        with gate.shared():
            log.append("late-shared")

    t1 = threading.Thread(target=shared_holder)
    t1.start()
    in_shared.wait(5)
    t2 = threading.Thread(target=exclusive_holder)
    t2.start()
    time.sleep(0.05)
    t3 = threading.Thread(target=late_shared)        # arrives while a writer waits
    t3.start()
    time.sleep(0.05)
    assert log == ["shared-in"]                      # neither got in yet
    release_shared.set()
    for t in (t1, t2, t3):
        t.join(5)
    assert log == ["shared-in", "shared-out", "exclusive-in", "exclusive-out", "late-shared"]


def test_t0_evaluations_never_overlap_any_container(tmp_path, monkeypatch):
    """`aa chain evaluate --all --workers 3` on chains with T0: a T0 evaluation (its
    reference run and its container) runs alone; T1-T4 containers may share."""
    from aa import chain_eval3
    make_chain(tmp_path / "tasks2")
    runs = tmp_path / "runs3"
    for c in ("0", "1", "2"):
        make_step(runs, cond="R", chain=c)
    for c in ("0", "1"):
        make_step(runs, cond="RC", chain=c, step="T1")
        t0 = runs / "claude" / "RC" / "Z1" / c / "T0"
        t0.mkdir(parents=True)
        (t0 / "agent.json").write_text(json.dumps(
            {"agent": "claude", "cond": "RC", "zone": "Z1", "chain": int(c), "step": "T0",
             "status": "ok"}))
    lock = threading.Lock()
    active = {"t0": 0, "other": 0}
    bad: list[str] = []

    def enter(kind):
        with lock:
            active[kind] += 1
            if active["t0"] > 1 or (active["t0"] and active["other"]):
                bad.append(f"{kind}: {dict(active)}")

    def leave(kind):
        with lock:
            active[kind] -= 1

    def fake_t0(step_dir, **kw):
        enter("t0")
        time.sleep(0.1)
        leave("t0")
        res = {"step_id": "T0", "status": "ok", "correct": True, "eval_error": None}
        (Path(step_dir) / "result.json").write_text(json.dumps(res))
        return res

    inner = fake_executor(rep=report({1: all_pass(1)}))

    def execute(argv, timeout):
        enter("other")
        time.sleep(0.05)
        try:
            return inner(argv, timeout)
        finally:
            leave("other")

    monkeypatch.setattr(chain_eval3, "evaluate_t0_step", fake_t0)
    res = evaluate_all(runs, tasks_root=tmp_path / "tasks2", execute=execute, workers=3,
                       log=lambda m: None)
    assert len(res) == 5
    assert bad == []
    for c in ("0", "1"):
        assert (runs / "claude/RC/Z1" / c / "T0/result.json").exists()
        assert (runs / "claude/RC/Z1" / c / "T1/result.json").exists()


# --- item 2: runs roots and container names -------------------------------------------------

def _capture_eval(monkeypatch):
    seen: dict = {}
    monkeypatch.setattr(chain_eval, "evaluate_all",
                        lambda root, **kw: seen.update(root=root, kw=kw) or {})
    return seen


def test_chain_evaluate_runs_root_from_study(tmp_path, monkeypatch):
    seen = _capture_eval(monkeypatch)
    assert cli.main(["chain", "evaluate", "--all"]) == 0
    assert seen["root"] == chain_eval.RUNS2.resolve()            # study 2 unchanged
    assert cli.main(["chain", "evaluate", "--all", "--study", "3"]) == 0
    assert seen["root"] == cr.RUNS3.resolve() and seen["root"].is_absolute()
    assert cli.main(["chain", "evaluate", "--all", "--study", "3", "--pilot"]) == 0
    assert seen["root"] == cr.RUNS_PILOT[3].resolve()
    monkeypatch.chdir(tmp_path)
    assert cli.main(["chain", "evaluate", "--all", "--runs", "rel"]) == 0
    assert seen["root"] == (tmp_path / "rel").resolve()
    assert seen["kw"]["workers"] == 2


def test_chain_packets_runs_root_and_outputs_from_study(tmp_path, monkeypatch):
    seen: dict = {}

    def fake2(runs, out, mapping, **kw):
        seen.update(exporter=2, runs=runs, out=out, mapping=mapping)
        return {"ok": [], "bad": []}

    def fake3(runs, out, mapping, **kw):
        seen.update(exporter=3, runs=runs, out=out, mapping=mapping, kw=kw)
        return {"ok": [], "bad": []}, {}, {"main": []}

    from aa import review3
    monkeypatch.setattr(chain_eval, "export_review_packets", fake2)
    monkeypatch.setattr(review3, "export_and_batch", fake3)
    assert cli.main(["chain", "packets"]) == 0
    assert seen["exporter"] == 2 and seen["runs"] == chain_eval.RUNS2.resolve()
    assert seen["out"] == config.WORK / "review2"
    assert seen["mapping"] == config.WORK / "review2-mapping.json"
    # review HIGH: study 3 runs the study-3 exporter (blind, per-packet trees, F chains,
    # batches), never study 2's into review3's paths
    seen.clear()
    assert cli.main(["chain", "packets", "--study", "3"]) == 0
    assert seen["exporter"] == 3 and seen["runs"] == cr.RUNS3.resolve()
    assert seen["out"] == review3.REVIEW3 and seen["mapping"] == review3.MAPPING3
    assert seen["kw"]["f_runs"] == (config.ROOT / "runs2").resolve()
    assert cli.main(["chain", "packets", "--study", "3", "--pilot",
                     "--out", str(tmp_path / "o")]) == 0
    assert seen["exporter"] == 3
    assert seen["runs"] == cr.RUNS_PILOT[3].resolve() and seen["out"] == tmp_path / "o"


@pytest.mark.parametrize("cmd", [["chain", "evaluate", "--all"], ["chain", "packets"]])
def test_pilot_needs_study(cmd, monkeypatch):
    """Review LOW: --pilot without --study read runs2-pilot/ (which exists)."""
    monkeypatch.setattr(chain_eval, "evaluate_all", lambda *a, **k: pytest.fail("ran"))
    monkeypatch.setattr(chain_eval, "export_review_packets", lambda *a, **k: pytest.fail("ran"))
    with pytest.raises(SystemExit) as e:
        cli.main(cmd + ["--pilot"])
    assert e.value.code == 2


def _name(argv: list[str]) -> str:
    return argv[argv.index("--name") + 1]


def test_eval_container_names_differ_by_runs_root(tmp_path):
    names = set()
    for root in ("runs3", "runs3-pilot", "pytest-x/runs3"):
        step = tmp_path / root / "claude" / "RC" / "Z1" / "0" / "T1"
        names.add(_name(chain_eval_docker_argv("RC", step, tmp_path / "o", "true")))
    assert len(names) == 3
    step = tmp_path / "runs3" / "claude" / "RC" / "Z1" / "0" / "T1"
    a = _name(chain_eval_docker_argv("RC", step, tmp_path / "o", "true"))
    assert a == _name(chain_eval_docker_argv("RC", step, tmp_path / "o2", "true"))  # stable
    assert a.startswith("aa-eval2-") and a.endswith("claude-RC-Z1-0-T1")
    assert chain_eval.runs_root_tag(step) in a


@pytest.mark.parametrize("study", [2, 3])
def test_runs_tag_is_short_hex(study, tmp_path):
    tag = chain_eval.runs_root_tag(tmp_path / f"runs{study}" / "a" / "R" / "Z1" / "0" / "T1")
    assert len(tag) == 6 and int(tag, 16) >= 0


# --- amendment 2026-10-17: AA_T0_SHARED lets a T0 evaluation share the gate -------------

@pytest.mark.parametrize("env, mode", [(None, "exclusive"), ("1", "shared"), ("0", "exclusive")])
def test_t0_gate_mode_follows_aa_t0_shared(tmp_path, monkeypatch, env, mode):
    from contextlib import contextmanager
    from aa import chain_eval3
    held: list[str] = []

    class Gate:
        @contextmanager
        def shared(self):
            held.append("shared")
            yield

        @contextmanager
        def exclusive(self):
            held.append("exclusive")
            yield

    monkeypatch.setattr(chain_eval, "GATE", Gate())
    monkeypatch.setattr(chain_eval3, "evaluate_t0_step", lambda *a, **k: {"ok": True})
    if env is None:
        monkeypatch.delenv("AA_T0_SHARED", raising=False)
    else:
        monkeypatch.setenv("AA_T0_SHARED", env)
    step = tmp_path / "runs3" / "codex" / "RC" / "Z1" / "0" / "T0"
    step.mkdir(parents=True)
    (step / "agent.json").write_text(json.dumps({"status": "ok", "study": 3}))
    assert chain_eval.evaluate_step(step) == {"ok": True}
    assert held == [mode]
