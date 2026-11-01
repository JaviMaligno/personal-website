"""Reproduce one Luna world-C episode with Codex session persistence on (no --ephemeral), so the
rollout file records what the model read when it polled a still-running `lean` command. The
`exec --json` stream of the trial does not include those polls.

    uv run python repro_luna_poll.py f2f-mathd_numbertheory_175
"""
import json
import os
import sys
import time
from pathlib import Path

import agents
import proctree
import run
import world_b

task = run.load_tasks("c", [sys.argv[1]])[0]
cfg = json.loads((run.HERE / "models.json").read_text(encoding="utf-8"))["luna"]
work = run.TMP / "repro-c" / task["id"]
world_b.materialize(task, work)
home = agents.prepare_codex_home()
env = agents.env_for("c") | {"CODEX_HOME": str(home)}
cmd = [c for c in agents.codex_cmd(cfg["model"], cfg["effort"]) if c != "--ephemeral"]
t0 = time.time()
try:
    r = proctree.run(cmd, cwd=work, env=env, text=True, encoding="utf-8", timeout=1800,
                     input=run.prompt_for("c", task), hidden=True)
finally:
    agents.sync_sandbox_users()
out = run.HERE / "runs" / f"repro-{task['id']}-luna.jsonl"
out.write_text(r.stdout, encoding="utf-8")
rollouts = sorted((p for p in (home / "sessions").rglob("*.jsonl") if p.stat().st_mtime >= t0), key=lambda p: p.stat().st_mtime)
print("events:", out)
print("rollout:", rollouts[-1] if rollouts else None)
print("final Main.lean:\n" + (work / "Main.lean").read_text(encoding="utf-8"))
os.environ["LEAN_PATH"] = env["LEAN_PATH"]
print("judge compile:", world_b.compile_lean(work / "Main.lean"))
