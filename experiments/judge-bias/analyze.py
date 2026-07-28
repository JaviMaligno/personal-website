#!/usr/bin/env python3
"""Compute the bias metrics from a results file produced by run.py (or by the pilot).

    python3 analyze.py results/pilot-claude-family.json

Four metrics, one per question worth asking:

  slot-A rate      Does the judge prefer whichever answer it reads first?
  flip rate        How often does swapping the slots reverse the verdict?
  self-preference  Does a judge favour its own output MORE THAN other judges do?
  length bias      How often does the longer answer win?
  agreement        Do judges agree with each other, per subjectivity level?

The self-preference metric is the one that needs care. "Judge X picked X's own
answer 70% of the time" proves nothing on its own — X's answer may simply be
better. What proves bias is the *delta*: how much more often X picks its own
answer than the other judges pick that same answer, on the same pairs.
"""

from __future__ import annotations

import collections
import itertools
import json
import pathlib
import sys


def order_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def load(path: str) -> dict:
    return json.loads(pathlib.Path(path).read_text())


def cells(data: dict) -> dict:
    """(task_id, m_first, m_second, judge) -> {'first': verdict, 'second': verdict}

    Keyed on the canonical (sorted) model order, so the two presentation orders
    of the same comparison land in the same cell.
    """
    out: dict = collections.defaultdict(dict)
    for j in data["judgments"]:
        if j["verdict"] is None:
            continue
        m_first, m_second = order_key(j["slot_a"], j["slot_b"])
        winner = {
            "a": j["slot_a"],
            "b": j["slot_b"],
            "tie": "tie",
        }[j["verdict"]]
        slot = "ab" if (j["slot_a"], j["slot_b"]) == (m_first, m_second) else "ba"
        out[(j["task_id"], m_first, m_second, j["judge"])][slot] = winner
    return out


def resolve(cell: dict) -> str:
    """Collapse the two presentation orders into one verdict.

    Returns a model name, 'tie', 'flip' (the judge reversed itself) or
    'unstable' (one order was a tie, the other was not).
    """
    if len(cell) < 2:
        return "incomplete"
    x, y = cell["ab"], cell["ba"]
    if x == y:
        return x
    if "tie" in (x, y):
        return "unstable"
    return "flip"


def score(verdict: str, model: str) -> float:
    """1 = model won, 0 = model lost, 0.5 = no decision."""
    if verdict == model:
        return 1.0
    if verdict in {"tie", "flip", "unstable", "incomplete"}:
        return 0.5
    return 0.0


def kappa(a: list[str], b: list[str]) -> float | None:
    if not a:
        return None
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return None if pe == 1.0 else (po - pe) / (1 - pe)


def pct(x: float | None) -> str:
    return "  n/a" if x is None else f"{100 * x:5.1f}%"


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    data = load(sys.argv[1])
    judges = data["meta"]["judges"]
    subj = {t["id"]: t["subjectivity"] for t in data["tasks"]}
    words = {(o["task_id"], o["model"]): o["words"] for o in data["outputs"]}
    C = cells(data)

    print(f"\n=== {sys.argv[1]} ===")
    print(f"generators: {', '.join(data['meta']['generators'])}")
    print(f"judges:     {', '.join(judges)}")
    print(f"tasks: {len(data['tasks'])}   outputs: {len(data['outputs'])}   "
          f"judgments: {len(data['judgments'])}")

    # --- 1 & 2. position -----------------------------------------------------
    print("\n## Position")
    print(f"{'judge':<34} {'slot-A rate':>12} {'flip rate':>11} {'n cells':>8}")
    for j in judges:
        raw = [x for x in data["judgments"] if x["judge"] == j and x["verdict"] in {"a", "b"}]
        slot_a = sum(1 for x in raw if x["verdict"] == "a") / len(raw) if raw else None
        cs = [resolve(v) for (t, m1, m2, jj), v in C.items() if jj == j]
        decided = [c for c in cs if c not in {"incomplete"}]
        flips = sum(1 for c in decided if c == "flip")
        print(f"{j:<34} {pct(slot_a):>12} "
              f"{pct(flips / len(decided) if decided else None):>11} {len(decided):>8}")
    print("  slot-A rate: 50% = no position preference.")
    print("  flip rate:   fraction of comparisons the judge reversed when slots were swapped.")

    # --- 3. self-preference --------------------------------------------------
    print("\n## Self-preference (the delta is the finding, not the raw rate)")
    print(f"{'judge = generator':<34} {'own rate':>9} {'others':>9} {'delta':>9} {'n':>5}")
    for j in judges:
        if j not in data["meta"]["generators"]:
            continue
        own, others = [], []
        seen = {(t, m1, m2) for (t, m1, m2, jj) in C if jj == j and j in (m1, m2)}
        for (t, m1, m2) in sorted(seen):
            own.append(score(resolve(C[(t, m1, m2, j)]), j))
            peer = [score(resolve(C[(t, m1, m2, k)]), j)
                    for k in judges if k != j and (t, m1, m2, k) in C]
            if peer:
                others.append(sum(peer) / len(peer))
        if not own:
            continue
        o = sum(own) / len(own)
        p = sum(others) / len(others) if others else None
        d = None if p is None else o - p
        print(f"{j:<34} {pct(o):>9} {pct(p):>9} "
              f"{('  n/a' if d is None else f'{100 * d:+5.1f}pp'):>9} {len(own):>5}")
    print("  own rate:  how often this judge picks its own output.")
    print("  others:    how often the OTHER judges pick that same output, same pairs.")
    print("  delta:     positive = self-preference beyond what peers see in the output.")

    # --- 4. length -----------------------------------------------------------
    print("\n## Length")
    print(f"{'judge':<34} {'longer wins':>12} {'n':>5}")
    for j in judges:
        hits = tot = 0
        for x in data["judgments"]:
            if x["judge"] != j or x["verdict"] not in {"a", "b"}:
                continue
            win = x["slot_a"] if x["verdict"] == "a" else x["slot_b"]
            lose = x["slot_b"] if x["verdict"] == "a" else x["slot_a"]
            wl, ll = words.get((x["task_id"], win)), words.get((x["task_id"], lose))
            if wl is None or ll is None or wl == ll:
                continue
            tot += 1
            hits += wl > ll
        print(f"{j:<34} {pct(hits / tot if tot else None):>12} {tot:>5}")
    print("  50% = no length preference; higher = longer answers win more.")
    print("  CONFOUNDED with quality on its own — read the length control below instead.")

    # --- 4b. length control --------------------------------------------------
    probe = data.get("length_probe")
    if probe:
        pw = {(o["task_id"], o["model"], o["variant"]): o["words"] for o in probe["outputs"]}
        short_w = [v for (t, m, var), v in pw.items() if var == "short"]
        long_w = [v for (t, m, var), v in pw.items() if var == "long"]
        print("\n## Length control (same model, same task, only the target length differs)")
        print(f"  manipulation check: short mean {sum(short_w)/len(short_w):.0f} words, "
              f"long mean {sum(long_w)/len(long_w):.0f} words")

        pc: dict = collections.defaultdict(dict)
        for x in probe["judgments"]:
            if x["verdict"] is None:
                continue
            win = {"a": x["slot_a_variant"], "b": x["slot_b_variant"], "tie": "tie"}[x["verdict"]]
            slot = "sl" if x["slot_a_variant"] == "short" else "ls"
            pc[(x["task_id"], x["model"], x["judge"])][slot] = win

        print(f"\n{'judge':<34} {'long wins':>10} {'flip':>7} {'n':>5}")
        for j in judges:
            vals, flips = [], 0
            for (t, m, jj), cell in pc.items():
                if jj != j or len(cell) < 2:
                    continue
                x, y = cell["sl"], cell["ls"]
                if x == y:
                    vals.append(1.0 if x == "long" else 0.0 if x == "short" else 0.5)
                else:
                    vals.append(0.5)
                    flips += x != y and "tie" not in (x, y)
            if vals:
                print(f"{j:<34} {pct(sum(vals)/len(vals)):>10} "
                      f"{pct(flips/len(vals)):>7} {len(vals):>5}")
        print("  50% = no length preference, quality held as fixed as this design allows.")
        print("  Compare against the confounded number above; a large gap means that")
        print("  number was measuring quality, not verbosity.")

        print(f"\n{'by subjectivity':<34} {'long wins':>10} {'n':>5}")
        for lvl in ["low", "medium", "high"]:
            psubj = {t["id"]: t["subjectivity"] for t in probe["tasks"]}
            vals = []
            for (t, m, jj), cell in pc.items():
                if psubj.get(t) != lvl or len(cell) < 2:
                    continue
                x, y = cell["sl"], cell["ls"]
                vals.append((1.0 if x == "long" else 0.0 if x == "short" else 0.5)
                            if x == y else 0.5)
            if vals:
                print(f"{lvl:<34} {pct(sum(vals)/len(vals)):>10} {len(vals):>5}")

    # --- 5. agreement --------------------------------------------------------
    print("\n## Inter-judge agreement (Cohen's kappa), by subjectivity")
    levels = ["low", "medium", "high"]
    print(f"{'judge pair':<52} " + " ".join(f"{l:>9}" for l in levels))
    for j1, j2 in itertools.combinations(judges, 2):
        row = []
        for lvl in levels:
            a, b = [], []
            for (t, m1, m2, jj), v in C.items():
                if jj != j1 or subj.get(t) != lvl:
                    continue
                if (t, m1, m2, j2) not in C:
                    continue
                lab = {m1: "first", m2: "second"}
                a.append(lab.get(resolve(v), "neither"))
                b.append(lab.get(resolve(C[(t, m1, m2, j2)]), "neither"))
            k = kappa(a, b)
            row.append("     n/a" if k is None else f"{k:+8.2f}")
        print(f"{j1.split(':')[-1]} vs {j2.split(':')[-1]:<28}"[:52].ljust(52)
              + " ".join(f"{r:>9}" for r in row))
    print("  1.0 = perfect agreement, 0.0 = chance. Expect it to fall as subjectivity rises.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
