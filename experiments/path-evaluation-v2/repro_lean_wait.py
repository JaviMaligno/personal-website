"""Time `lean Main.lean` inside Codex's sandbox through the elan proxy (old env) and through the
toolchain binary first on PATH (agents.env_for since 2026-11-01). Session persistence on, so the
rollouts carry each call's wall time. A Mathlib compile took 9.5 min via the proxy, 30 s direct.

    uv run python repro_lean_wait.py b t12-times-eq-mul
"""
import os
import sys
import time

import agents
import proctree
import run
import world_b

world, task_id = sys.argv[1], sys.argv[2]
task = run.load_tasks(world, [task_id])[0]
home = agents.prepare_codex_home()
cmd = [c for c in agents.codex_cmd("gpt-6-luna", "medium") if c != "--ephemeral"]
new_env = agents.env_for(world) | {"CODEX_HOME": str(home)}
old_env = dict(new_env, PATH=new_env["PATH"].split(os.pathsep, 1)[1])
for label, env in (("proxy", old_env), ("direct", new_env)):
    work = run.TMP / "repro-wait" / f"{world}-{label}"
    world_b.materialize(task, work)
    prompt = ("Run this exact command and wait until it has fully finished (check that the result has an "
              "exit code): lean Main.lean\nThen reply with its complete output verbatim and its exit code. "
              "Do not edit any file.")
    t0 = time.time()
    try:
        proctree.run(cmd, cwd=work, env=env, text=True, encoding="utf-8", timeout=900, input=prompt, hidden=True)
    finally:
        agents.sync_sandbox_users()
    rollouts = sorted((p for p in (home / "sessions").rglob("*.jsonl") if p.stat().st_mtime >= t0), key=lambda p: p.stat().st_mtime)
    print(label, "rollout:", rollouts[-1] if rollouts else None, "secs:", round(time.time() - t0), flush=True)
