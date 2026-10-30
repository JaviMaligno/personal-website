import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent.parent


def test_server_lists_tools_and_logs_executed_calls(tmp_path):
    ep = tmp_path / "episode.json"
    ep.write_text(json.dumps({"world": "rewrite", "max_calls": 1, "task": {
        "start": "(x**2 + x)/x", "target": "x + 1", "assumptions": {"x": "positive"}, "kind": "solvable"}}))
    log = tmp_path / "steps.jsonl"
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "factor", "arguments": {"sub": "x**2 + x"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "submit", "arguments": {}}},
    ]
    proc = subprocess.run([sys.executable, str(HERE / "mcp_world.py"), str(ep), str(log)],
                          input="\n".join(json.dumps(m) for m in msgs) + "\n",
                          capture_output=True, text=True, encoding="utf-8", timeout=60)
    replies = [json.loads(l) for l in proc.stdout.splitlines()]
    assert [r["id"] for r in replies] == [1, 2, 3, 4]          # no reply to the notification
    assert "factor" in {t["name"] for t in replies[1]["result"]["tools"]}
    assert replies[2]["result"]["content"][0]["text"] == "x*(x + 1)/x"
    assert replies[3]["result"]["content"][0]["text"].startswith("not executed")  # budget of 1
    assert [json.loads(l) for l in log.read_text().splitlines()] == [
        {"tool": "factor", "args": {"sub": "x**2 + x"}}]
