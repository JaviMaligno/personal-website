"""Translate each agent's native trace into the common action vocabulary (see shellcmd)."""
from __future__ import annotations

import json

from shellcmd import _rel, classify

CLAUDE_DIRECT = {"Read": "read", "Edit": "edit", "Write": "edit", "MultiEdit": "edit", "NotebookEdit": "edit"}


def _jsonl(lines):
    for line in lines:
        try:
            yield json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue


def from_claude(lines, root: str) -> list[dict]:
    out = []
    for m in _jsonl(lines):
        if m.get("type") != "assistant":
            continue
        for c in m.get("message", {}).get("content", []):
            if c.get("type") != "tool_use":
                continue
            name, inp = c.get("name"), c.get("input", {})
            if name in CLAUDE_DIRECT:
                out.append({"kind": CLAUDE_DIRECT[name], "target": _rel(inp.get("file_path", ""), root)})
            elif name in ("Grep",):
                out.append({"kind": "search", "target": ""})
            elif name in ("Glob", "LS"):
                out.append({"kind": "list", "target": ""})
            elif name in ("Bash", "PowerShell"):
                out.extend(classify(inp.get("command", ""), root))
            else:
                out.append({"kind": "run_other", "target": ""})
    return out


def from_codex(lines, root: str) -> list[dict]:
    out = []
    for m in _jsonl(lines):
        if m.get("type") != "item.completed":
            continue
        it = m.get("item", {})
        kind = it.get("type") or it.get("item_type")
        if kind == "command_execution":
            out.extend(classify(it.get("command", ""), root))
        elif kind == "file_change":
            for ch in it.get("changes", []):
                out.append({"kind": "edit", "target": _rel(ch.get("path", ""), root)})
    return out


QWEN = {"read_file": "read", "list_dir": "list", "search": "search", "write_file": "edit", "replace_in_file": "edit"}


def from_qwen(steps, root: str) -> list[dict]:
    out = []
    for s in steps:
        tool, args = s["tool"], s.get("args", {})
        if tool == "run_command":
            out.extend(classify(args.get("command", ""), root))
        elif tool in QWEN:
            target = _rel(args.get("path", ""), root) if QWEN[tool] in ("read", "edit") else ""
            out.append({"kind": QWEN[tool], "target": target})
        else:
            out.append({"kind": "run_other", "target": ""})
    return out
