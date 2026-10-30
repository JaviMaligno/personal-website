"""Score every trace with E0-E3 against the semantic truth.

    uv run python analyze.py traces/pilot.jsonl [--pilot]

Groups: rewrite (solvable), rewrite-trap, onboarding. Counts are absolute: n is small.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluators import condensed, e0, e1, e2, e3

HERE = Path(__file__).parent
TAUS = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


def load(path):
    last = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        last[(r["world"], r["task_id"], r["model"], r["rep"])] = r
    return [r for r in last.values() if r["stop"] != "error"]


def load_tasks():
    out = {}
    for wn in ("rewrite", "onboarding"):
        for t in json.loads((HERE / f"tasks/{wn}.json").read_text()):
            out[(wn, t["id"])] = t
    return out


def group(r):
    return "rewrite-trap" if r["kind"] == "trap" else r["world"]


def score(r, task, tau):
    return {"E0": e0(r), "E1": e1(r, task["rules"]), "E2": e2(r, task["rules"]),
            "E3": e3(r, task["reference_tokens"], tau)}


def table(traces, tasks, tau=0.8):
    rows = {}
    for r in traces:
        for ev, v in score(r, tasks[(r["world"], r["task_id"])], tau).items():
            if v is None:
                continue
            c = rows.setdefault((group(r), ev), {"n": 0, "FP": 0, "FN": 0})
            c["n"] += 1
            c["FP"] += int(v and not r["truth"])
            c["FN"] += int(not v and r["truth"])
    return rows


def fn_kind(tokens, refs):
    for ref in refs:
        if sorted(tokens) == sorted(ref):
            return "order"
        it = iter(tokens)
        if all(t in it for t in ref):
            return "extra_steps"
    return "other"


def tokens_used(r):
    keys = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens",
            "prompt_tokens", "completion_tokens")
    return sum(u.get(k, 0) or 0 for u in r.get("usage", []) for k in keys)


def print_table(rows):
    print(f"{'group':<14}{'eval':<6}{'n':>5}{'FP':>5}{'FN':>5}")
    for (g, ev), c in sorted(rows.items()):
        print(f"{g:<14}{ev:<6}{c['n']:>5}{c['FP']:>5}{c['FN']:>5}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("traces")
    ap.add_argument("--pilot", action="store_true")
    args = ap.parse_args()
    traces, tasks = load(args.traces), load_tasks()

    print(f"{len(traces)} traces\n")
    print_table(table(traces, tasks))

    print("\nE3 by tau (FP/FN):")
    for g in ("rewrite", "onboarding"):
        row = []
        for tau in TAUS:
            c = table([r for r in traces if group(r) == g], tasks, tau).get((g, "E3"), {"FP": 0, "FN": 0})
            row.append(f"{tau}:{c['FP']}/{c['FN']}")
        print(f"  {g:<12}", "  ".join(row))

    print("\nE3 false negatives by kind (tau=0.8):")
    for r in traces:
        task = tasks[(r["world"], r["task_id"])]
        if r["truth"] and e3(r, task["reference_tokens"], 0.8) is False:
            print(f"  {r['world']} {r['task_id']} {r['model']} r{r['rep']}: "
                  f"{fn_kind(condensed(r['steps']), task['reference_tokens'])}")

    print("\nE2 disagreements with the truth (declared rules vs semantics):")
    for r in traces:
        v = e2(r, tasks[(r["world"], r["task_id"])]["rules"])
        if v != r["truth"]:
            print(f"  {'FP' if v else 'FN'} {r['world']} {r['task_id']} {r['model']} r{r['rep']}")

    print("\nExamples: final state right, derivation false (E0 FP):")
    for r in traces:
        if r["final_ok"] and not r["truth"]:
            print(f"  {r['world']} {r['task_id']} {r['model']} r{r['rep']}")

    if args.pilot:
        rw = [r for r in traces if r["world"] == "rewrite"]
        invalid = sum(any(s.get("valid") is False for s in r["steps"]) for r in rw)
        detours = 0
        for r in rw:
            refs = tasks[("rewrite", r["task_id"])]["reference_tokens"]
            if r["truth"] and refs and len(condensed(r["steps"])) > min(map(len, refs)):
                detours += 1
        per_model = {}
        for r in traces:
            per_model.setdefault(r["model"], []).append(tokens_used(r))
        print(f"\nPILOT: rewrite traces with an invalid step = {invalid} (need >= 3)")
        print(f"PILOT: valid rewrite traces longer than the shortest reference = {detours} (need >= 3)")
        for m, xs in per_model.items():
            print(f"PILOT: {m} mean tokens per trace = {sum(xs) // max(1, len(xs))}")


if __name__ == "__main__":
    main()
