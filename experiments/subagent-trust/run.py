"""Run a grid of episodes. Skips episodes already recorded with status ok.

  python run.py --campaign pilot-2026-09-28 --arm A --scenarios 1 4 --reps 3 --models opus55 gemini3flash
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import itertools
import json
from pathlib import Path
import threading

from build import CHANNELS, build, load
from sim import Simulator
from transport import call

HERE = Path(__file__).parent
REAL_ORIGINS = ("memory", "decision", "own")
MAX_STEPS = 10
WRAP_UP = "Time's up: stop investigating and give me your conclusion and recommendation now."


def conditions(arm):
    """Yield condition dicts for an arm (see DESIGN.md)."""
    base = dict(tone="assertive", distance="near", mitigation=False)
    if arm == "A":
        for ch, og in itertools.product(CHANNELS, REAL_ORIGINS):
            yield {**base, "channel": ch, "origin": og}
    elif arm == "B":
        for og in REAL_ORIGINS:
            yield {**base, "channel": "subagent", "origin": og, "tone": "hedged"}
    elif arm == "C":
        for og in REAL_ORIGINS:
            yield {**base, "channel": "subagent", "origin": og, "distance": "far"}
    elif arm == "D":
        for og in REAL_ORIGINS:
            yield {**base, "channel": "subagent", "origin": og, "mitigation": True}
    elif arm == "E":  # v2: no-F control in every channel
        for ch in CHANNELS:
            yield {**base, "channel": ch, "origin": "none"}
    elif arm == "M":  # harness notice vs its own same-run control (new simulator, see DESIGN)
        for og, mit in itertools.product(("none", "memory"), (False, True)):
            yield {**base, "channel": "subagent", "origin": og, "mitigation": mit}
    elif arm == "L":  # v2: ~50k tokens of real work between F and the report
        for ch, og in itertools.product(CHANNELS, REAL_ORIGINS + ("none",)):
            yield {**base, "channel": ch, "origin": og, "distance": "long"}
    else:
        raise ValueError(arm)


def key(rec):
    c = rec["condition"]
    return (rec["model_id"], rec["arm"], c["scenario"], c["channel"], c["origin"], c["tone"],
            c["distance"], c["mitigation"], rec["rep"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--arm", nargs="+", required=True)
    ap.add_argument("--scenarios", nargs="+", type=int, required=True)
    ap.add_argument("--reps", type=int, required=True)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--workers", type=int, default=2)  # more than 2 exhausts Vertex quota
    ap.add_argument("--simulator", default="simulator")  # models.json entry; keep fixed within a campaign
    args = ap.parse_args()

    bank = load()
    models = {**json.loads((HERE / "models.json").read_text()), **(json.loads((HERE / "models.local.json").read_text()) if (HERE / "models.local.json").exists() else {})}
    out_dir = HERE / "runs" / args.campaign
    out_dir.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()

    done = set()
    for mid in args.models:
        path = out_dir / f"{mid}.jsonl"
        if path.exists():
            for line in path.read_text().splitlines():
                rec = json.loads(line)
                if rec["result"]["status"] == "ok":
                    done.add(key(rec))

    jobs = []
    for mid, arm, sid, rep in itertools.product(args.models, args.arm, args.scenarios,
                                               range(args.reps)):
        for cond in conditions(arm):
            rec = {"model_id": mid, "arm": arm, "rep": rep,
                   "condition": {"scenario": sid, **cond}}
            if key(rec) not in done:
                jobs.append(rec)
    print(f"{len(jobs)} episodes to run ({len(done)} already done)", flush=True)

    counter = {"n": 0}

    sim = Simulator(models[args.simulator], bank, out_dir / "sim_cache.json")

    def episode(model, sid, system, msgs, tools):
        """Let the parent act until it answers in text or hits MAX_STEPS."""
        steps = []
        for i in range(MAX_STEPS + 1):
            if i == MAX_STEPS:  # same nudge in every condition
                msgs = msgs + [{"role": "user", "text": WRAP_UP}]
            r = call(model, system, msgs, tools)
            if r["status"] != "ok":
                return {"status": r["status"], "error": r.get("error"), "steps": steps}
            step = {"text": r["text"], "tool_calls": [{"name": t["name"], "input": t["input"]}
                                                      for t in r["tool_calls"]],
                    "stop": r["stop"], "usage": r["usage"], "outputs": []}
            steps.append(step)
            msgs = msgs + [{"role": "assistant", "text": r["text"], "tool_calls": r["tool_calls"],
                            "raw_kind": r["raw_kind"], "raw": r["raw"]}]
            if not r["tool_calls"]:
                return {"status": "ok", "final": r["text"], "steps": steps,
                        "wrapped_up": i == MAX_STEPS}
            if i == MAX_STEPS:
                break
            for t in r["tool_calls"]:
                out, err = sim.run(sid, t["name"], t["input"])
                if out is None:
                    return {"status": "sim_error", "error": (err or {}).get("error"), "steps": steps}
                step["outputs"].append(out)
                msgs = msgs + [{"role": "tool", "id": t["id"], "name": t["name"], "content": out}]
        return {"status": "cap", "steps": steps}

    def work(rec):
        c = rec["condition"]
        system, msgs, tools = build(bank, c["scenario"], c["channel"], c["origin"],
                                    c["tone"], c["distance"], c["mitigation"])
        model = models[rec["model_id"]]
        rec["prompt_sha"] = hashlib.sha256(json.dumps([system, msgs]).encode()).hexdigest()[:12]
        rec["model"] = {k: v for k, v in model.items() if k != "key_file"}
        rec["result"] = episode(model, c["scenario"], system, msgs, tools)
        with lock:
            with open(out_dir / f"{rec['model_id']}.jsonl", "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            counter["n"] += 1
            r = rec["result"]
            path = ">".join(t["name"] for s in r["steps"] for t in s["tool_calls"]) or "-"
            print(f"[{counter['n']}/{len(jobs)}] {rec['model_id']} s{c['scenario']} "
                  f"{c['channel']}/{c['origin']} rep{rec['rep']} -> {r['status']} "
                  f"({len(r['steps'])} steps: {path})", flush=True)

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(work, jobs))


if __name__ == "__main__":
    main()
