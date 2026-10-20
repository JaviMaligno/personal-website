"""Study 3, cross-family judge analysis (exploratory, 2026-10-18). Compares the registered
Opus judge (work/review3/scores) with GPT-6.1 Sol (work/review3/scores_sol, from
scripts/study3_cross_judge.py) on the same chain packets:

1. agreement (quadratic-weighted kappa per score, as the registered reliability);
2. own-family preference: d = Opus - Sol per packet, compared between packets written by
   Claude agents (Sonnet, Haiku) and by Codex. If Opus favours its own family (or Sol its
   own), d is higher on Claude-written code. Mann-Whitney on d, and per zone and arm;
3. H1 re-read with Sol: each lever arm vs R per agent, maintainability, Mann-Whitney.

  uv run python scripts/study3_cross_judge_analysis.py [--out out/study3/cross_judge.md]"""
import argparse
import json
import statistics as st
import sys
from pathlib import Path

from aa import config, review3
from aa.stats import mann_whitney_u

R3 = config.ROOT / "work/review3"
SCORES = ["reuse", "duplication", "placement", "scope", "maintainability"]
FAMILY = {"claude": "Claude", "haiku": "Claude", "codex": "GPT"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=config.ROOT / "out/study3/cross_judge.md")
    a = ap.parse_args(argv)
    m = json.loads((config.ROOT / "work/review3-mapping.json").read_text())
    opus = review3.load_judgements(R3 / "scores")
    sol = review3.load_judgements(R3 / "scores_sol")
    ids = sorted(p for p in sol if p in opus and m[p]["kind"] == "chain")
    L = [f"# Cross-family judge: Opus 5.5 vs GPT-6.1 Sol on {len(ids)} chain packets\n"]
    sc = lambda j, q: j[q]["score"]  # noqa: E731

    L.append("## Agreement (quadratic-weighted kappa)\n\n| score | kappa | exact | mean Opus | mean Sol |\n|---|---|---|---|---|")
    for q in SCORES:
        x = [sc(opus[p], q) for p in ids]
        y = [sc(sol[p], q) for p in ids]
        k = review3.qwk(x, y, [1, 2, 3, 4, 5])
        ex = sum(i == j for i, j in zip(x, y)) / len(ids)
        L.append(f"| {q} | {k:.2f} | {ex:.0%} | {st.mean(x):.2f} | {st.mean(y):.2f} |")

    L.append("\n## Own-family preference: d = Opus − Sol (maintainability)\n")
    L.append("| subset | d, Claude-written (n) | d, Codex-written (n) | difference | MW p |\n|---|---|---|---|---|")
    def row(name, sel):
        dc = [sc(opus[p], "maintainability") - sc(sol[p], "maintainability") for p in sel if FAMILY[m[p]["agent"]] == "Claude"]
        dg = [sc(opus[p], "maintainability") - sc(sol[p], "maintainability") for p in sel if FAMILY[m[p]["agent"]] == "GPT"]
        if dc and dg:
            _, pv = mann_whitney_u(dc, dg)
            L.append(f"| {name} | {st.mean(dc):+.2f} ({len(dc)}) | {st.mean(dg):+.2f} ({len(dg)}) | {st.mean(dc) - st.mean(dg):+.2f} | {pv:.3f} |")
    row("all", ids)
    for z in ("Z1", "Z2", "Z3", "Z4"):
        row(z, [p for p in ids if m[p]["zone"] == z])
    for c in ("R", "RG", "RL", "RC", "F"):
        row(c, [p for p in ids if m[p]["cond"] == c])
    L.append("\nSonnet alone vs Codex (same-tier comparison):\n")
    L.append("| subset | d, Sonnet (n) | d, Haiku (n) | d, Codex (n) |\n|---|---|---|---|")
    for q in SCORES:
        ds = {ag: [sc(opus[p], q) - sc(sol[p], q) for p in ids if m[p]["agent"] == ag] for ag in ("claude", "haiku", "codex")}
        L.append(f"| {q} | {st.mean(ds['claude']):+.2f} ({len(ds['claude'])}) | {st.mean(ds['haiku']):+.2f} ({len(ds['haiku'])}) | {st.mean(ds['codex']):+.2f} ({len(ds['codex'])}) |")

    L.append("\n## H1 re-read with each judge (maintainability, lever arm vs R, all zones)\n")
    L.append("| agent | arm | Opus arm vs R (p) | Sol arm vs R (p) |\n|---|---|---|---|")
    for ag in ("claude", "codex", "haiku"):
        for arm in ("RG", "RL", "RC", "F"):
            cells = []
            for J in (opus, sol):
                x = [sc(J[p], "maintainability") for p in ids if m[p]["agent"] == ag and m[p]["cond"] == arm]
                y = [sc(J[p], "maintainability") for p in ids if m[p]["agent"] == ag and m[p]["cond"] == "R"]
                _, pv = mann_whitney_u(x, y)
                cells.append(f"{st.mean(x):.2f} vs {st.mean(y):.2f} ({pv:.4f})")
            L.append(f"| {ag} | {arm} | {cells[0]} | {cells[1]} |")
        x = [sc(sol[p], "maintainability") for p in ids if m[p]["agent"] == ag and m[p]["cond"] == "RL" and m[p]["zone"] in ("Z1", "Z3")]
        y = [sc(sol[p], "maintainability") for p in ids if m[p]["agent"] == ag and m[p]["cond"] == "R" and m[p]["zone"] in ("Z1", "Z3")]
        xo = [sc(opus[p], "maintainability") for p in ids if m[p]["agent"] == ag and m[p]["cond"] == "RL" and m[p]["zone"] in ("Z1", "Z3")]
        yo = [sc(opus[p], "maintainability") for p in ids if m[p]["agent"] == ag and m[p]["cond"] == "R" and m[p]["zone"] in ("Z1", "Z3")]
        L.append(f"| {ag} | RL, Z1+Z3 | {st.mean(xo):.2f} vs {st.mean(yo):.2f} ({mann_whitney_u(xo, yo)[1]:.4f}) | {st.mean(x):.2f} vs {st.mean(y):.2f} ({mann_whitney_u(x, y)[1]:.4f}) |")
    a.out.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
