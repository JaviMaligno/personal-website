"""Codex login guard: the host auth.json is copied into every container and container-side
token refreshes are never written back, so an access token that expires mid-run makes
parallel containers race on the single-use refresh token (pilot 2026-10-12: 7 chains
infra_exhausted). The guard refuses to start, or stops dispatching, before that happens."""
import base64
import json
import time
from pathlib import Path

from aa import chain_runner as cr
from aa import runner


def _auth(tmp_path: Path, exp: float) -> Path:
    def b64(d: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    tok = f"{b64({'alg': 'none'})}.{b64({'exp': int(exp)})}.sig"
    p = tmp_path / "auth.json"
    p.write_text(json.dumps({"tokens": {"access_token": tok}}))
    return p


def test_hours_left_reads_jwt_exp(tmp_path):
    now = 1_000_000.0
    p = _auth(tmp_path, now + 36 * 3600)
    assert abs(runner.codex_auth_hours_left(p, now=now) - 36.0) < 1e-6


def test_hours_left_none_when_missing_or_unreadable(tmp_path):
    assert runner.codex_auth_hours_left(tmp_path / "nope.json") is None
    bad = tmp_path / "auth.json"
    bad.write_text("{}")
    assert runner.codex_auth_hours_left(bad) is None


def test_auth_problem_messages(tmp_path):
    now = time.time()
    ok = _auth(tmp_path, now + 48 * 3600)
    assert runner.codex_auth_problem(min_hours=24, path=ok) is None
    short = _auth(tmp_path, now + 2 * 3600)
    msg = runner.codex_auth_problem(min_hours=24, path=short)
    assert msg and "codex login" in msg
    assert runner.codex_auth_problem(min_hours=24, path=tmp_path / "missing") is not None


def _job(i: int) -> cr.ChainJob:
    return cr.ChainJob(agent="codex", cond="R", zone="Z1", chain_idx=i)


def test_scheduler_preflight_stops_dispatch_without_burning_attempts():
    ran: list = []
    calls = {"n": 0}

    def preflight(job):
        calls["n"] += 1
        return None if calls["n"] <= 1 else "codex token expires in 0.5 h"

    res = cr.ChainScheduler(
        [_job(0), _job(1), _job(2)], workers=1,
        run=lambda j: (ran.append(j), cr.ChainResult("ok", None))[1],
        status_of=lambda j: None, sleep=lambda s: None, log=lambda m: None,
        preflight=preflight).execute()
    assert ran == [_job(0)]
    assert res[_job(0)] == "ok"
    assert res[_job(1)] == res[_job(2)] == "auth_expired"


def test_scheduler_without_preflight_unchanged():
    res = cr.ChainScheduler([_job(0)], workers=1, run=lambda j: cr.ChainResult("ok", None),
                            status_of=lambda j: None, sleep=lambda s: None,
                            log=lambda m: None).execute()
    assert res == {_job(0): "ok"}


def test_cli_refuses_codex_run_with_short_login(tmp_path, monkeypatch, capsys):
    from aa import cli
    monkeypatch.setattr(runner, "CODEX_AUTH", _auth(tmp_path, time.time() + 3600))
    called = []
    monkeypatch.setattr(cr, "run_all_chains", lambda *a, **k: called.append(1) or {})
    rc = cli.main(["chain", "run", "--agent", "codex", "--conds", "R,RG,RL,RC",
                   "--zones", "Z1", "--chains", "1"])
    assert rc == 2 and not called
    assert "codex login" in capsys.readouterr().err


def test_run_all_chains_wires_preflight_only_for_codex(monkeypatch):
    seen = {}

    class FakeSched:
        def __init__(self, q, **kw):
            seen[kw["preflight"] is not None] = True
        def execute(self):
            return {}
    monkeypatch.setattr(cr, "ChainScheduler", FakeSched)
    cr.run_all_chains("codex", ["R"], ["Z1"], [0], study=3)
    cr.run_all_chains("claude", ["R"], ["Z1"], [0], study=3)
    assert seen == {True: True, False: True}
