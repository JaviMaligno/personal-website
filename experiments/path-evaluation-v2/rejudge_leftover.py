"""Judge an episode whose work copy survived a judge crash, from its saved events, and append the
record. Used once for f2f-aime_1983_p2 luna #2 (compile timeout raised instead of failing E0).

    uv run python rejudge_leftover.py c f2f-aime_1983_p2 luna 2 runs/trial-mathlib-hard.jsonl
"""
import json
import os
import sys
from pathlib import Path

import escape_audit
import normalize
import run
import world_b

world, task_id, model, rep, out = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), Path(sys.argv[5])
if world == "c":
    import agents
    os.environ["LEAN_PATH"] = agents.env_for("c")["LEAN_PATH"]
task = next(t for t in run.load_tasks(world, [task_id]))
cfg = json.loads((run.HERE / "models.json").read_text(encoding="utf-8"))[model]
work = run.TMP / f"work-{world}" / f"{task_id}-{model}-{rep}"
ev_file = run.EVENTS / f"{world}-{task_id}-{model}-{rep}.jsonl"
events = [l for l in ev_file.read_text(encoding="utf-8").splitlines() if l.strip()]
parse = {"claude": normalize.from_claude, "codex": normalize.from_codex}[cfg["kind"]]
actions = parse(events, str(work))
judge = world_b.judge(task, work, actions)
usage = next((json.loads(l).get("usage") for l in reversed(events) if "turn.completed" in l), None)
rec = {"world": world, "task": task_id, "model": model, "rep": rep, "stop": "done", "resolved_model": cfg["model"],
       "usage": usage, "actions": actions, "judge": judge, "events_file": ev_file.relative_to(run.HERE).as_posix(),
       "root": str(work), "escape_hits": escape_audit.audit(ev_file), "final": run.final_state(world, work),
       "rejudged": "judge crashed on a compile timeout; judged afterwards from the surviving copy"}
with out.open("a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print(task_id, model, rep, {k: judge[k] for k in ("truth", "E0", "E1", "E2", "E3", "pc")})
