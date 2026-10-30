"""Expose one world as an MCP server over stdio, for agents driven by the Claude Code CLI.

    python mcp_world.py <episode.json> <steps.jsonl>

episode.json holds {"world", "task", "max_calls"}. Every executed tool call is appended
to steps.jsonl as {"tool", "args"}; the runner replays them into a fresh world
afterwards, so this process never has to report scores.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import onboarding  # noqa: E402
import rewrite  # noqa: E402


def make_world(world, task):
    if world == "rewrite":
        w = rewrite.RewriteWorld(task["start"], task["target"], task["assumptions"], kind=task["kind"])
        return w, rewrite.TOOLS
    return onboarding.OnboardingWorld(task["customer"]), onboarding.TOOLS


def handle(msg, world, tools, log, state):
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:  # notification
        return None
    if method == "initialize":
        version = (msg.get("params") or {}).get("protocolVersion", "2025-06-18")
        result = {"protocolVersion": version, "capabilities": {"tools": {}},
                  "serverInfo": {"name": "world", "version": "0.1.0"}}
    elif method == "tools/list":
        result = {"tools": [{"name": t["name"], "description": t["description"], "inputSchema": t["schema"]}
                            for t in tools]}
    elif method == "tools/call":
        name = msg["params"]["name"]
        args = msg["params"].get("arguments") or {}
        if world.done or state["calls"] >= state["max_calls"]:
            text = "not executed: the episode is over"
        else:
            text = world.call(name, args)
            state["calls"] += 1
            with log.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"tool": name, "args": args}) + "\n")
        result = {"content": [{"type": "text", "text": text}], "isError": False}
    elif method == "ping":
        result = {}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"unknown method {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    ep = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    log = Path(sys.argv[2])
    world, tools = make_world(ep["world"], ep["task"])
    state = {"calls": 0, "max_calls": ep.get("max_calls", 30)}
    for line in sys.stdin:
        if not line.strip():
            continue
        reply = handle(json.loads(line), world, tools, log, state)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
