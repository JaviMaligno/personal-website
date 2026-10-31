"""subprocess.run with a timeout that kills the whole process tree.

On Windows `claude` and `codex` are .CMD shims: cmd.exe starts node, which starts the real binary.
subprocess.run's timeout kills only cmd.exe, so the agent kept running, holding memory (observed
2026-10-31: a hung Codex preflight left node + codex.exe alive after the timeout fired).
"""
from __future__ import annotations

import subprocess


def run(cmd, timeout: float, input: str | None = None, hidden: bool = False, **kw) -> subprocess.CompletedProcess:
    """hidden: give the tree a console with no window. Started from a process without a console,
    every console program the agent spawns (Codex's sandbox setup before each command) pops up its own."""
    stdin = subprocess.PIPE if input is not None else kw.pop("stdin", subprocess.DEVNULL)
    if hidden:
        kw["creationflags"] = kw.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
    with subprocess.Popen(cmd, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw) as p:
        try:
            out, err = p.communicate(input, timeout=timeout)
        except subprocess.TimeoutExpired:
            kill_tree(p.pid)
            p.communicate()
            raise
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)


def kill_tree(pid: int) -> None:
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
