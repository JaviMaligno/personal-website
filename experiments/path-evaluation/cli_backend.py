"""Run one episode through the Claude Code CLI (subscription auth) instead of an API.

The CLI runs the tool loop itself; the world lives in an MCP server (mcp_world.py)
that logs every executed call. The caller replays those calls into a fresh world,
which is deterministic, so steps/final_ok/truth come out as with agent.run_episode.

Context differences against the API path, constant across Claude runs and reported
in the results: Claude Code adds a short account/workspace note to our system prompt,
and the model thinks by default. --setting-sources "" keeps settings hooks and
CLAUDE.md out; --tools "" removes the built-in tools. --bare would be cleaner but
disables subscription auth.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
CLAUDE = shutil.which("claude") or "claude"


def build_cmd(model, system, user, mcp_cfg, max_turns):
    return [CLAUDE, "-p", user, "--system-prompt", system, "--model", model["model"],
            "--setting-sources", "", "--strict-mcp-config", "--mcp-config", str(mcp_cfg),
            "--tools", "", "--allowedTools", "mcp__world", "--no-session-persistence",
            "--output-format", "stream-json", "--verbose", "--max-turns", str(max_turns)]


def parse_stream(text):
    usage, result, model = {}, None, None
    for line in text.splitlines():
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            continue
        if m.get("type") == "system" and m.get("subtype") == "init":
            model = m.get("model")
        elif m.get("type") == "assistant":
            msg = m.get("message", {})
            usage[msg.get("id")] = msg.get("usage", {})  # one event per content block
        elif m.get("type") == "result":
            result = m
    return list(usage.values()), result, model


def run_cli_episode(model, world_name, task, system, user, max_calls=30, max_turns=40, timeout=900):
    """Returns (result dict, executed calls as [{"tool", "args"}])."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "episode.json").write_text(json.dumps({"world": world_name, "task": task, "max_calls": max_calls}),
                                        encoding="utf-8")
        steps_log = d / "steps.jsonl"
        cfg = {"mcpServers": {"world": {"command": sys.executable,
                                        "args": [str(HERE / "mcp_world.py"), str(d / "episode.json"),
                                                 str(steps_log)]}}}
        (d / "mcp.json").write_text(json.dumps(cfg), encoding="utf-8")
        try:
            proc = subprocess.run(build_cmd(model, system, user, d / "mcp.json", max_turns), cwd=d,
                                  capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"stop": "error", "error": f"timeout after {timeout}s", "calls": 0, "usage": []}, []
        calls = ([json.loads(l) for l in steps_log.read_text(encoding="utf-8").splitlines()]
                 if steps_log.exists() else [])
    usage, result, resolved = parse_stream(proc.stdout)
    if result is None:
        return {"stop": "error", "error": f"exit {proc.returncode}: {proc.stderr[-500:]}",
                "calls": len(calls), "usage": usage}, calls
    return {"stop": result.get("subtype"), "calls": len(calls), "usage": usage, "resolved_model": resolved,
            "num_turns": result.get("num_turns"), "final_text": result.get("result", "")}, calls
