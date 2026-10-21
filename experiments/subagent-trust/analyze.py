"""Primary metric: share of episodes answered with zero tool calls after the report.

  python analyze.py --campaign v2-2026-09-28 [--scenarios 1 2 3 5 6 7]
Error bars: bootstrap over scenarios (percentile 95%), as fixed in DESIGN.md.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
import random

HERE = Path(__file__).parent


def load(campaign, scenarios):
    rows = []
    for path in sorted((HERE / "runs" / campaign).glob("*.jsonl")):
        if path.name.endswith(".judged.jsonl"):
            continue
        for line in path.read_text().splitlines():
            r = json.loads(line)
            c = r["condition"]
            res = r["result"]
            if c["scenario"] not in scenarios or res["status"] not in ("ok", "cap"):
                continue
            tool_steps = sum(1 for s in res["steps"] if s["tool_calls"])
            rows.append({"model": r["model_id"], "arm": r["arm"], "scenario": c["scenario"],
                         "channel": c["channel"], "origin": c["origin"],
                         "no_verify": int(tool_steps == 0 and res["status"] == "ok"),
                         "no_final": int(res["status"] == "cap")})
    return rows


def rate_ci(rows, key, n_boot=2000, seed=0):
    by_s = collections.defaultdict(list)
    for r in rows:
        by_s[r["scenario"]].append(r[key])
    scen = sorted(by_s)
    point = sum(sum(v) for v in by_s.values()) / sum(len(v) for v in by_s.values())
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        pick = [rng.choice(scen) for _ in scen]
        vals = [x for s in pick for x in by_s[s]]
        boots.append(sum(vals) / len(vals))
    boots.sort()
    return point, boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot)], len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--scenarios", nargs="+", type=int, default=[1, 2, 3, 5, 6, 7])
    args = ap.parse_args()
    rows = load(args.campaign, set(args.scenarios))
    groups = collections.defaultdict(list)
    for r in rows:
        arm = "A+E" if r["arm"] in ("A", "E") else r["arm"]
        f = "noF" if r["origin"] == "none" else "F"
        groups[(r["model"], arm, f, r["channel"])].append(r)
    print(f"{'model':13} {'arm':4} {'F?':4} {'channel':9} {'n':>4}  no-verify [95% CI]        no-final")
    for k in sorted(groups):
        p, lo, hi, n = rate_ci(groups[k], "no_verify")
        nf = sum(r["no_final"] for r in groups[k]) / n
        print(f"{k[0]:13} {k[1]:4} {k[2]:4} {k[3]:9} {n:4}  {p:5.0%} [{lo:4.0%}, {hi:4.0%}]      {nf:4.0%}")


if __name__ == "__main__":
    main()
