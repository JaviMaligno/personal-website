"""`haiku` (study 2, amendment 12): Claude Code with claude-haiku-5-5, otherwise `claude`."""
import json
from pathlib import Path

import pytest

from aa import chain_runner as cr
from aa import config, runner, tables2
from aa.agents import detect_contamination, parse_stream
from aa.cli import build_parser

F = Path(__file__).parent / "fixtures"


def _swap_model(s: str) -> str:
    return s.replace(config.MODELS["claude"], config.MODELS["haiku"])


def test_config_engine():
    assert config.AGENTS == ("claude", "codex", "haiku")
    assert config.MODELS["haiku"] == "claude-haiku-5-5"
    assert [config.engine(a) for a in config.AGENTS] == ["claude", "codex", "claude"]
    with pytest.raises(ValueError):
        config.engine("gemini")


def test_haiku_argv_equals_claude_except_model(tmp_path):
    assert runner.agent_command("haiku") == _swap_model(runner.agent_command("claude"))
    assert "--model claude-haiku-5-5" in runner.agent_command("haiku")
    assert f"--effort {config.EFFORT}" in runner.agent_command("haiku")
    assert runner.container_script("haiku") == _swap_model(runner.container_script("claude"))
    assert cr.chain_container_script("haiku") == _swap_model(cr.chain_container_script("claude"))
    p, o = tmp_path / "p", tmp_path / "o"
    h = cr.chain_docker_argv("haiku", "R", "n", p, o)
    c = cr.chain_docker_argv("claude", "R", "n", p, o)
    assert h[:-1] == c[:-1] and h[-1] == _swap_model(c[-1])
    assert "CLAUDE_CODE_OAUTH_TOKEN" in h
    h1 = runner.docker_argv("haiku", "A", "t01", 0, p, o)
    c1 = runner.docker_argv("claude", "A", "t01", 0, p, o)
    # only the container name carries the agent name
    assert [x.replace("aa-haiku-", "aa-claude-") for x in h1[:-1]] == c1[:-1]
    assert h1[-1] == _swap_model(c1[-1])


def test_haiku_launcher_uses_claude_token(tmp_path, monkeypatch):
    tok = tmp_path / "tok"
    tok.write_text("secret\n")
    monkeypatch.setattr(runner, "CLAUDE_TOKEN_FILE", tok)
    argv, env = cr.docker_launcher("haiku", "F", "n", tmp_path / "p", tmp_path / "o", tmp_path, 60)
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "secret"
    assert "secret" not in " ".join(argv)


def test_parsers_and_contamination_work_for_haiku():
    lines = (F / "claude-stream-ok.jsonl").read_text().splitlines()
    assert parse_stream("haiku", lines) == parse_stream("claude", lines)
    noweb = (F / "claude-noweb-smoke.jsonl").read_text().splitlines()
    assert detect_contamination("haiku", noweb) == detect_contamination("claude", noweb)


@pytest.mark.parametrize("argv", [
    ["chain", "run", "--agent", "haiku"],
    ["chain", "run-one", "--agent", "haiku", "--cond", "R", "--zone", "Z1"],
    ["run-one", "--agent", "haiku", "--cond", "A", "--task", "t01"],
])
def test_cli_accepts_haiku(argv):
    assert build_parser().parse_args(argv).agent == "haiku"


def test_tables2_groups_by_three_agents(tmp_path):
    root = tmp_path / "runs2"
    for agent in ("haiku", "codex", "claude"):
        for cond in ("R", "F"):
            r = {"agent": agent, "cond": cond, "zone": "Z1", "chain": 0, "step": 1,
                 "status": "ok", "correct": agent != "haiku", "consumers_total": 3,
                 "consumers_passed": 3 if agent != "haiku" else 1}
            d = root / agent / cond / "Z1" / "0" / "T1"
            d.mkdir(parents=True)
            (d / "result.json").write_text(json.dumps(r))
    summary = tables2.summarise(tables2.load_steps(root), tables2.load_chains(root))
    assert list(summary) == ["claude", "codex", "haiku"]
    assert summary["haiku"]["missed_copy"]["R"]["k"] == 1
    assert summary["claude"]["missed_copy"]["R"]["k"] == 0
    assert "## haiku" in tables2.render_markdown(summary)
