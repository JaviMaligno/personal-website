"""Run agents over the tasks and append one JSON line per episode.

    uv run python run.py --models haiku,sonnet,qwen --world both --tasks 5 --reps 1 --out traces/pilot.jsonl

Claude models go through the Claude Code CLI (subscription); others through the API
loop in agent.py. Sequential on purpose (this machine saturates). Re-running with the
same --out skips episodes already recorded without error, so an interrupted run
resumes where it stopped.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import onboarding
import prompts
import rewrite
import transport
from agent import run_episode
from cli_backend import run_cli_episode

HERE = Path(__file__).parent
MAX_CALLS = 30


def load_models(names):
    configs = json.loads((HERE / "models.json").read_text())
    out = {}
    for n in names:
        m = dict(configs[n])
        if m.get("project") == "from-gcloud":
            m["project"] = transport.gcloud_project()
        out[n] = m
    return out


def make(world_name, task):
    if world_name == "rewrite":
        w = rewrite.RewriteWorld(task["start"], task["target"], task["assumptions"], kind=task["kind"])
        return w, prompts.REWRITE_SYSTEM, prompts.rewrite_user(task, w), rewrite.TOOLS
    w = onboarding.OnboardingWorld(task["customer"])
    user = prompts.ONBOARDING_USER.format(id=task["customer"]["id"])
    if "note" in task["customer"]:  # the tempting cases arrive with a note attached
        user += f"\nCase note: {task['customer']['note']}"
    return w, prompts.ONBOARDING_SYSTEM, user, onboarding.TOOLS


def episode(model, wn, task):
    w, system, user, tools = make(wn, task)
    if model["transport"] != "claude_cli":
        return w, run_episode(model, w, system, user, tools, max_calls=MAX_CALLS)
    res, calls = run_cli_episode(model, wn, task, system, user, max_calls=MAX_CALLS)
    for c in calls:  # deterministic replay: same steps the MCP server produced
        w.call(c["tool"], c["args"])
    if res["stop"] != "error":
        res["stop"] = ("done" if w.done else "budget" if len(calls) >= MAX_CALLS
                       else "max_turns" if res["stop"] == "error_max_turns" else "no_tool_call")
    return w, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--world", choices=["rewrite", "onboarding", "both"], default="both")
    ap.add_argument("--tasks", type=int, default=999, help="first N tasks of each world")
    ap.add_argument("--task-ids", default="", help="comma-separated ids; overrides --tasks")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["stop"] != "error":
                done.add((r["world"], r["task_id"], r["model"], r["rep"]))

    models = load_models(args.models.split(","))
    worlds = ["rewrite", "onboarding"] if args.world == "both" else [args.world]
    wanted = set(filter(None, args.task_ids.split(",")))
    for wn in worlds:
        tasks = json.loads((HERE / f"tasks/{wn}.json").read_text())
        tasks = [t for t in tasks if t["id"] in wanted] if wanted else tasks[:args.tasks]
        for task in tasks:
            for mname, model in models.items():
                for rep in range(args.reps):
                    if (wn, task["id"], mname, rep) in done:
                        continue
                    w, res = episode(model, wn, task)
                    rec = {"world": wn, "task_id": task["id"], "kind": task["kind"], "model": mname,
                           "rep": rep, **res, "steps": w.steps,
                           "final_ok": w.final_ok(), "truth": w.truth()}
                    with out.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(rec) + "\n")
                    print(f"{wn} {task['id']} {mname} r{rep}: stop={res['stop']} calls={res['calls']} "
                          f"final_ok={rec['final_ok']} truth={rec['truth']}"
                          + (f" error={res['error'][:200]}" if res.get("error") else ""), flush=True)


if __name__ == "__main__":
    main()
