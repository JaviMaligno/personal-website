"""Study 2 design review (H4), analysis as pre-registered in docs/design-review-rubric.md
(study 2 addendum). Run: uv run python scripts/study2_design_review.py > out/study2/design_review.txt"""
import collections, json, os, warnings
import numpy as np, pandas as pd
from scipy.stats import mannwhitneyu, binomtest
warnings.filterwarnings("ignore")
W = "work/review2"
DIMS = ("maintainability", "duplication", "reuse", "placement", "scope")

def qwk(a, b, k=5):
    a, b = np.asarray(a) - 1, np.asarray(b) - 1
    O = np.zeros((k, k))
    for x, y in zip(a, b): O[x, y] += 1
    w = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)]) / (k - 1) ** 2
    E = np.outer(O.sum(1), O.sum(0)) / O.sum()
    return 1 - (w * O).sum() / (w * E).sum()

def norm(x):
    """30 of 1104 judge files use an abbreviated shape ([score, why]; bp/db/wm): same
    content, mapped losslessly to the rubric's shape."""
    out = dict(x)
    for d in DIMS:
        if isinstance(x[d], list):
            out[d] = {"score": x[d][0], "why": x[d][1]}
    if "bp" in x:
        out["bypasses_abstraction"] = {"value": x["bp"][0], "where": x["bp"][1]}
        out["duplicated_blocks"], out["would_merge"] = x["db"], x["wm"]
    return out

def load(d):
    return {f[:-5]: norm(json.load(open(f"{W}/{d}/{f}"))) for f in os.listdir(f"{W}/{d}")}

A, B = load("scores"), load("scores2")
ids = sorted(set(A) & set(B))
print(f"## Reliability (second judge, {len(ids)} packets): quadratic-weighted kappa")
for d in DIMS:
    print(f"{d}: {qwk([A[i][d]['score'] for i in ids], [B[i][d]['score'] for i in ids]):.2f}")
print(f"would_merge exact agreement: {np.mean([A[i]['would_merge'] == B[i]['would_merge'] for i in ids]):.2f}")

M = json.load(open("work/review2-mapping.json"))
rows = []
for pid, s in A.items():
    m = M[pid]
    rows.append({"id": pid, "kind": m["kind"], "agent": m["agent"], "cond": m["cond"],
                 "zone": m["zone"], "chain": m["chain"], "step": m.get("step"),
                 **{d: s[d]["score"] for d in DIMS},
                 "bypass": bool(s["bypasses_abstraction"]["value"]),
                 "dup_blocks": int(s["duplicated_blocks"]), "merge": s["would_merge"]})
df = pd.DataFrame(rows)
for kind in ("step", "chain"):
    print(f"\n## {kind} packets")
    for a in ("claude", "codex", "haiku"):
        g = df[(df.kind == kind) & (df.agent == a)]
        r, f = g[g.cond == "R"], g[g.cond == "F"]
        print(f"\n### {a} (R n={len(r)}, F n={len(f)})")
        for d in DIMS + ("dup_blocks",):
            p = mannwhitneyu(r[d], f[d]).pvalue
            zs = [(zg[zg.cond == "F"][d].mean() - zg[zg.cond == "R"][d].mean())
                  for _, zg in g.groupby("zone")]
            hi, lo = sum(z > 0 for z in zs), sum(z < 0 for z in zs)
            sp = binomtest(hi, hi + lo).pvalue if hi + lo else 1.0
            print(f"{d}: R {r[d].mean():.2f} | F {f[d].mean():.2f} | MW p={p:.3g} | "
                  f"zones F higher {hi}, lower {lo} (sign p={sp:.3g})")
        for c, gg in (("R", r), ("F", f)):
            mc = collections.Counter(gg["merge"])
            print(f"{c}: bypasses_abstraction {gg.bypass.mean():.0%}, would_merge yes "
                  f"{mc['yes']/len(gg):.0%} / with_changes {mc['with_changes']/len(gg):.0%} / no {mc['no']/len(gg):.0%}")
print("\n## step packets by zone, maintainability mean R | F (all agents)")
g = df[df.kind == "step"]
for z, zg in g.groupby("zone"):
    print(z, f"{zg[zg.cond=='R'].maintainability.mean():.2f} | {zg[zg.cond=='F'].maintainability.mean():.2f}")
print("\n## step packets by step, maintainability mean R | F (all agents)")
for s, sg in g.groupby("step"):
    print(s, f"{sg[sg.cond=='R'].maintainability.mean():.2f} | {sg[sg.cond=='F'].maintainability.mean():.2f}")
