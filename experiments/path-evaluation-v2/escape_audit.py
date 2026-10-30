"""List every absolute path an agent's tool calls mention outside its work copy.

    uv run python escape_audit.py runs/events runs/pilot0/events

Reads the raw events (Claude Code tool_use inputs, Codex commands and file changes, Qwen tool
arguments). A hit is not proof of a write; it is the list to read by hand.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ABS = re.compile(r"(?:[A-Za-z]:/|/c/|/mnt/[a-z]/)[^\s\"';|&<>()]*", re.I)
ALLOWED = ("/pe2/", "windowspowershell", "/dev/null", "/tmp/", "/.elan/", "c:/users/usuario/.elan")
# Two or more `..` in a row can leave the copy from its root (one `..` from a subfolder cannot).
UP = re.compile(r"(?:\.\./){2,}\.?\.?|cd\s+\.\.(?:\s|$|;|&)")


def calls(m: dict) -> list[str]:
    if m.get("type") == "assistant":
        return [json.dumps(c.get("input")) for c in m.get("message", {}).get("content", []) if c.get("type") == "tool_use"]
    if m.get("type") == "item.completed":
        it = m.get("item", {})
        if it.get("type") in ("command_execution", "file_change"):
            return [it.get("command", "") + json.dumps(it.get("changes", ""))]
    if "tool" in m:
        return [json.dumps(m.get("args"))]
    return []


def audit(path: Path) -> list[str]:
    hits = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            continue
        for c in calls(m):
            # JSON-escaped newlines/tabs first, or "SECONDS:\n" reads as the path "S:/n".
            flat = c.replace("\\n", " ").replace("\\t", " ").replace("\\\\", "/").replace("\\", "/")
            for p in ABS.findall(flat):
                if not any(a in p.lower() for a in ALLOWED):
                    hits.add(p[:120])
            for up in UP.findall(flat):
                hits.add(f"relative climb: {up.strip()[:60]}")
    return sorted(hits)


if __name__ == "__main__":
    for d in sys.argv[1:]:
        for f in sorted(Path(d).glob("*.jsonl")):
            h = audit(f)
            if h:
                print(f.name, h[:8])
