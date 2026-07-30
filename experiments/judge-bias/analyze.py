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
import random
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


def binom_p(k: int, n: int, p: float = 0.5) -> float | None:
    """Two-sided exact binomial p-value: how surprised should you be by k of n?

    Reported next to the slot-A rate because a 60% slot-A rate on 20 decisions and
    on 200 decisions are very different claims, and only one of them is a finding.
    """
    if n == 0:
        return None
    from math import comb
    probs = [comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(n + 1)]
    return min(1.0, sum(x for x in probs if x <= probs[k] * (1 + 1e-9)))


def bootstrap_ci(pairs: list[tuple[float, float]], resamples: int = 10000) -> tuple[float, float] | None:
    """Percentile CI for the mean paired difference (own − peers).

    Resamples the paired cells, not the individual judgments: the two numbers in a
    cell describe the same comparison, so they have to move together.
    """
    if len(pairs) < 2:
        return None
    rng = random.Random(20260728)  # fixed so the reported interval is reproducible
    n = len(pairs)
    means = []
    for _ in range(resamples):
        sample = [pairs[rng.randrange(n)] for _ in range(n)]
        means.append(sum(o - p for o, p in sample) / n)
    means.sort()
    return means[int(0.025 * resamples)], means[int(0.975 * resamples) - 1]


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

    # --- 0. ranking ----------------------------------------------------------
    #
    # The question the whole harness exists to answer: does swapping the judge
    # swap the ranking? Everything below is diagnosis; this is the symptom.
    print("\n## Ranking (win score: 1 = won the comparison, 0.5 = tie/flip/unstable)")
    gens = data["meta"]["generators"]
    header = f"{'generator':<34} {'overall':>8}" + "".join(
        f" {('by ' + j.split(':')[-1])[:12]:>13}" for j in judges) + f" {'mean words':>11}"
    print(header)
    for g in gens:
        overall, per_judge = [], []
        for j in judges:
            got = [score(resolve(v), g)
                   for (t, m1, m2, jj), v in C.items() if jj == j and g in (m1, m2)]
            per_judge.append(sum(got) / len(got) if got else None)
            overall += got
        mw = [w for (t, m), w in words.items() if m == g]
        print(f"{g:<34} {pct(sum(overall) / len(overall) if overall else None):>8}"
              + "".join(f" {pct(x):>13}" for x in per_judge)
              + f" {sum(mw) / len(mw):>10.0f}")
    print("  If the columns disagree on the order, the judge is part of the result.")

    # --- 1 & 2. position -----------------------------------------------------
    print("\n## Position")
    print(f"{'judge':<34} {'slot-A rate':>12} {'p':>7} {'flip rate':>11} {'n cells':>8}")
    for j in judges:
        raw = [x for x in data["judgments"] if x["judge"] == j and x["verdict"] in {"a", "b"}]
        a_hits = sum(1 for x in raw if x["verdict"] == "a")
        slot_a = a_hits / len(raw) if raw else None
        p = binom_p(a_hits, len(raw))
        cs = [resolve(v) for (t, m1, m2, jj), v in C.items() if jj == j]
        decided = [c for c in cs if c not in {"incomplete"}]
        flips = sum(1 for c in decided if c == "flip")
        print(f"{j:<34} {pct(slot_a):>12} {('  n/a' if p is None else f'{p:5.3f}'):>7} "
              f"{pct(flips / len(decided) if decided else None):>11} {len(decided):>8}")
    print("  slot-A rate: 50% = no position preference; p = exact binomial vs 50%.")
    print("  flip rate:   fraction of comparisons the judge reversed when slots were swapped.")

    # --- 3. self-preference --------------------------------------------------
    print("\n## Self-preference (the delta is the finding, not the raw rate)")
    print(f"{'judge = generator':<34} {'own rate':>9} {'others':>9} {'delta':>9} "
          f"{'95% CI':>18} {'vs neutral judge only':>24} {'n':>5}")
    for j in judges:
        if j not in data["meta"]["generators"]:
            continue
        paired, neutral_paired = [], []
        seen = {(t, m1, m2) for (t, m1, m2, jj) in C if jj == j and j in (m1, m2)}
        for (t, m1, m2) in sorted(seen):
            own_score = score(resolve(C[(t, m1, m2, j)]), j)
            peer = [score(resolve(C[(t, m1, m2, k)]), j)
                    for k in judges if k != j and (t, m1, m2, k) in C]
            if peer:
                paired.append((own_score, sum(peer) / len(peer)))
            # The strict baseline: only judges with no stake in this pair. With
            # three judges that is one model — the peer set above also contains
            # the *opponent*, whose own self-preference pushes the other way and
            # inflates the delta.
            uninvolved = [score(resolve(C[(t, m1, m2, k)]), j) for k in judges
                          if k not in (m1, m2) and (t, m1, m2, k) in C]
            if uninvolved:
                neutral_paired.append((own_score, sum(uninvolved) / len(uninvolved)))
        if not paired:
            continue
        o = sum(x for x, _ in paired) / len(paired)
        p = sum(y for _, y in paired) / len(paired)
        ci = bootstrap_ci(paired)
        ci_txt = "n/a" if ci is None else f"[{100 * ci[0]:+.1f}, {100 * ci[1]:+.1f}]"
        nd = (sum(x - y for x, y in neutral_paired) / len(neutral_paired)
              if neutral_paired else None)
        nci = bootstrap_ci(neutral_paired)
        nd_txt = "n/a" if nd is None else f"{100 * nd:+.1f}pp"
        if nci is not None:
            nd_txt += f" [{100 * nci[0]:+.1f}, {100 * nci[1]:+.1f}]"
        print(f"{j:<34} {pct(o):>9} {pct(p):>9} {100 * (o - p):+5.1f}pp    "
              f"{ci_txt:>18} {nd_txt:>24} {len(paired):>5}")
    print("  own rate:  how often this judge picks its own output.")
    print("  others:    how often the OTHER judges pick that same output, same pairs.")
    print("  delta:     positive = self-preference beyond what peers see in the output.")
    print("  95% CI:    percentile bootstrap over the paired cells (10k resamples, fixed seed).")

    # Where does self-preference live? A delta that survives on tasks with a
    # checkable answer is a different, worse problem than one that only shows up
    # where taste is all there is.
    print(f"\n{'same delta, split by subjectivity':<34} "
          + " ".join(f"{lvl:>12}" for lvl in ["low", "medium", "high"]))
    for j in judges:
        if j not in data["meta"]["generators"]:
            continue
        row = []
        for lvl in ["low", "medium", "high"]:
            paired = []
            seen = {(t, m1, m2) for (t, m1, m2, jj) in C
                    if jj == j and j in (m1, m2) and subj.get(t) == lvl}
            for (t, m1, m2) in sorted(seen):
                peer = [score(resolve(C[(t, m1, m2, k)]), j)
                        for k in judges if k != j and (t, m1, m2, k) in C]
                if peer:
                    paired.append((score(resolve(C[(t, m1, m2, j)]), j),
                                   sum(peer) / len(peer)))
            if not paired:
                row.append("         n/a")
                continue
            d = sum(o - p for o, p in paired) / len(paired)
            row.append(f"{100 * d:+8.1f}pp")
        print(f"{j:<34} " + " ".join(f"{r:>12}" for r in row))

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

        def long_rate(predicate):
            vals = []
            for (t, m, jj), cell in pc.items():
                if not predicate(t) or len(cell) < 2:
                    continue
                x, y = cell["sl"], cell["ls"]
                vals.append((1.0 if x == "long" else 0.0 if x == "short" else 0.5)
                            if x == y else 0.5)
            return (sum(vals) / len(vals), len(vals)) if vals else None

        # The split that matters, and the reason the aggregate above is not the
        # finding. The pilot found a reversal hiding inside it: judges reward
        # elaboration where the task invites it and penalise it where the task's
        # implicit goal is compression. A probe set containing only one kind of
        # task produces a confident, wrong headline number either way.
        rewards = {t["id"]: t.get("rewards") for t in probe["tasks"]}
        if any(rewards.values()):
            print(f"\n{'by what the task rewards':<34} {'long wins':>10} {'n':>5}")
            for r in ["elaboration", "concision"]:
                got = long_rate(lambda t, r=r: rewards.get(t) == r)
                if got:
                    print(f"{r:<34} {pct(got[0]):>10} {got[1]:>5}")
            print("  The GAP between these two rows is the finding — not the aggregate.")
            print("  Near-identical rows would mean a genuine length preference;")
            print("  a wide gap means the judge is tracking the task's goal, not word count.")

        psubj = {t["id"]: t["subjectivity"] for t in probe["tasks"]}
        print(f"\n{'by subjectivity':<34} {'long wins':>10} {'n':>5}")
        for lvl in ["low", "medium", "high"]:
            got = long_rate(lambda t, lvl=lvl: psubj.get(t) == lvl)
            if got:
                print(f"{lvl:<34} {pct(got[0]):>10} {got[1]:>5}")

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
