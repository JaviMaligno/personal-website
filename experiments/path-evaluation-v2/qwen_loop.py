"""Minimal tool loop for Qwen over OpenRouter, with tools equivalent to the CLIs' basics."""
from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path

URL = "https://openrouter.ai/api/v1/chat/completions"
SYSTEM = "You are a software engineering agent working in the current directory. Use the tools to inspect files, run commands and edit files. When you are done, reply with a short summary and no tool call."


def _tool(name, desc, props, req):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": req}}}


S = {"type": "string"}
TOOLS = [
    _tool("read_file", "Read a text file.", {"path": S}, ["path"]),
    _tool("list_dir", "List a directory.", {"path": S}, ["path"]),
    _tool("search", "Search a regex in files under a path (like grep -rn).", {"pattern": S, "path": S}, ["pattern"]),
    _tool("write_file", "Create or overwrite a file.", {"path": S, "content": S}, ["path", "content"]),
    _tool("replace_in_file", "Replace one exact occurrence of old with new in a file.", {"path": S, "old": S, "new": S}, ["path", "old", "new"]),
    _tool("run_command", "Run a shell command (bash) and return its output.", {"command": S}, ["command"]),
]


def _exec(work: Path, env: dict, tool: str, a: dict) -> str:
    try:
        if tool == "read_file":
            return (work / a["path"]).read_text(encoding="utf-8")[:20000]
        if tool == "list_dir":
            return "\n".join(sorted(p.name + ("/" if p.is_dir() else "") for p in (work / a.get("path", ".")).iterdir()))
        if tool == "search":
            r = subprocess.run(["grep", "-rn", "-E", a["pattern"], a.get("path", ".")], cwd=work, capture_output=True, text=True, timeout=60)
            return r.stdout[:20000] or "(no matches)"
        if tool == "write_file":
            p = work / a["path"]; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(a["content"], encoding="utf-8"); return "written"
        if tool == "replace_in_file":
            p = work / a["path"]; s = p.read_text(encoding="utf-8")
            if s.count(a["old"]) != 1:
                return f"error: old text found {s.count(a['old'])} times"
            p.write_text(s.replace(a["old"], a["new"]), encoding="utf-8"); return "replaced"
        if tool == "run_command":
            r = subprocess.run(["bash", "-lc", a["command"]], cwd=work, env=env, capture_output=True, text=True, timeout=600)
            return (r.stdout + r.stderr)[-20000:] + f"\n[exit {r.returncode}]"
    except Exception as e:  # tool errors go back to the model, like a CLI would show them
        return f"error: {type(e).__name__}: {e}"
    return f"error: unknown tool {tool}"


def run(cfg: dict, work: Path, prompt: str, env: dict, max_calls: int = 80) -> dict:
    key = Path(cfg["key_file"]).expanduser().read_text().strip()
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    steps, usage, empty, calls = [], [], 0, 0
    while calls < max_calls:
        body = {"model": cfg["model"], "messages": msgs, "tools": TOOLS, "max_tokens": cfg.get("max_tokens", 8192),
                "reasoning": {"enabled": True}}
        req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.loads(r.read())
        usage.append(data.get("usage", {}))
        msg = data["choices"][0]["message"]
        tcs = msg.get("tool_calls") or []
        if not tcs and not (msg.get("content") or "").strip():
            empty += 1
            if empty <= 3:
                continue
            return {"steps": steps, "usage": usage, "stop": "empty_reply", "resolved_model": cfg["model"]}
        msgs.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls", "reasoning", "reasoning_details")})
        if not tcs:
            return {"steps": steps, "usage": usage, "stop": "done", "final_text": msg.get("content"), "resolved_model": cfg["model"]}
        for tc in tcs:
            args = json.loads(tc["function"]["arguments"] or "{}")
            out = _exec(work, env, tc["function"]["name"], args)
            steps.append({"tool": tc["function"]["name"], "args": args})
            msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": out})
            calls += 1
    return {"steps": steps, "usage": usage, "stop": "budget", "resolved_model": cfg["model"]}
