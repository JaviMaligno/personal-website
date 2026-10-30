"""Run one episode with a native CLI (Claude Code, Codex) or the Qwen loop in a work directory.

Isolation (spec, "Aislamiento"): Claude Code without user settings, hooks, CLAUDE.md or MCP, and
with only its six working tools; Codex with its own CODEX_HOME (auth.json + config.toml that
disables every user skill), plugins off, ephemeral, stdin closed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import qwen_loop
import setup_env

HERE = Path(__file__).parent
CODEX_HOME = HERE / "runs" / "tmp" / "codexhome"
CLAUDE_TOOLS = "Bash,Read,Edit,Write,Grep,Glob"


def env_for(world: str) -> dict:
    env = dict(os.environ)
    if world == "a":
        env["PATH"] = str(setup_env.python().parent) + os.pathsep + env["PATH"]
        env["PYTHONPATH"] = "src"
    return env


def prepare_codex_home(model: str, effort: str) -> Path:
    CODEX_HOME.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path.home() / ".codex" / "auth.json", CODEX_HOME / "auth.json")
    # [windows] sandbox: without it the isolated home has no working sandbox and every command is
    # "blocked by policy" (observed 2026-10-30); the user's own config sets it to "elevated".
    lines = [f'model = "{model}"', f'model_reasoning_effort = "{effort}"', "", "[windows]", 'sandbox = "elevated"', ""]
    for root in (Path.home() / ".agents" / "skills", Path.home() / ".codex" / "skills"):
        if root.exists():
            for p in sorted(root.rglob("SKILL.md")):
                lines += ["[[skills.config]]", f"path = '{p}'", "enabled = false", ""]
    (CODEX_HOME / "config.toml").write_text("\n".join(lines), encoding="utf-8")
    return CODEX_HOME


def run_claude(model: str, work: Path, prompt: str, world: str, timeout=1800) -> dict:
    cmd = [shutil.which("claude") or "claude", "-p", prompt, "--model", model, "--setting-sources", "",
           "--strict-mcp-config", "--tools", CLAUDE_TOOLS, "--allowedTools", CLAUDE_TOOLS,
           "--output-format", "stream-json", "--verbose", "--no-session-persistence", "--max-turns", "80"]
    r = subprocess.run(cmd, cwd=work, env=env_for(world), capture_output=True, text=True, encoding="utf-8",
                       timeout=timeout, stdin=subprocess.DEVNULL)
    lines = r.stdout.splitlines()
    result = next((json.loads(l) for l in reversed(lines) if '"type":"result"' in l.replace(" ", "")), {})
    init = next((json.loads(l) for l in lines if '"subtype":"init"' in l.replace(" ", "")), {})
    return {"events": lines, "resolved_model": init.get("model"), "stop": result.get("subtype", f"exit {r.returncode}"),
            "usage": result.get("usage"), "api_equivalent_usd": result.get("total_cost_usd"),
            "stderr": r.stderr[-800:]}


def run_codex(model: str, effort: str, work: Path, prompt: str, world: str, timeout=1800) -> dict:
    home = prepare_codex_home(model, effort)
    env = env_for(world) | {"CODEX_HOME": str(home)}
    cmd = [shutil.which("codex") or "codex", "exec", "--json", "--ephemeral", "--skip-git-repo-check",
           "--disable", "plugins", "-s", "workspace-write", "-"]
    # Prompt goes via stdin ("-"): codex is a .CMD shim on Windows and cmd.exe truncates argv at the first newline.
    # input= also gives EOF after the prompt, so stdin stays isolated.
    r = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, encoding="utf-8",
                       timeout=timeout, input=prompt)
    lines = r.stdout.splitlines()
    usage = next((json.loads(l).get("usage") for l in reversed(lines) if "turn.completed" in l), None)
    return {"events": lines, "resolved_model": model, "stop": "done" if r.returncode == 0 else f"exit {r.returncode}",
            "usage": usage, "stderr": r.stderr[-800:]}


def run_qwen(model_cfg: dict, work: Path, prompt: str, world: str) -> dict:
    return qwen_loop.run(model_cfg, work, prompt, env_for(world))
