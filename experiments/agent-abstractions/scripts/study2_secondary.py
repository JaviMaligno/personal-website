"""Study 2 exploratory measures (post hoc, added 2026-10-10 after reading traces).

Not pre-registered. (a) any pre-existing consumer failing on a rule step (catches the
total misses the registered missed-copy definition excludes); (b) chains with a true
regression (an earlier test that passed at its own step fails later), as opposed to
carried failures that never passed; (c) correctness per agent; (d) pooled Bayesian
mixed logistic over the three agents (agent and zone fixed, chain random).
Correct = tables2.is_correct (timed-out steps not correct; fixed 2026-10-12, the first
version read the raw `correct` flag).
Run: uv run python scripts/study2_secondary.py > out/study2/secondary.txt"""
import collections, glob, json, math, warnings
import pandas as pd
from scipy.stats import fisher_exact
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
from aa.tables2 import is_correct  # status == "ok" and hidden tests passed (timeout = not correct)
warnings.filterwarnings("ignore")

def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"{100*p:.0f}% [{100*max(0,c-h):.0f}–{100*min(1,c+h):.0f}]"

def fisher(a, b):
    return fisher_exact([[a[0], a[1] - a[0]], [b[0], b[1] - b[0]]])[1]

R = [json.load(open(p)) for p in sorted(glob.glob("runs2/*/*/*/*/T*/result.json"))]
AG = ("claude", "codex", "haiku")
anyf = collections.defaultdict(lambda: [0, 0]); corr = collections.defaultdict(lambda: [0, 0])
for r in R:
    k = (r["agent"], r["cond"])
    corr[k][1] += 1; corr[k][0] += is_correct(r)
    if r["kind"] == "rule" and r.get("consumers_preexisting_total"):
        anyf[k][1] += 1
        anyf[k][0] += r["consumers_preexisting_passed"] < r["consumers_preexisting_total"]
print("## (a) any pre-existing consumer fails, T1+T3")
for a in AG:
    x, y = anyf[(a, "R")], anyf[(a, "F")]
    print(f"{a}: R {x[0]}/{x[1]} {wilson(*x)} | F {y[0]}/{y[1]} {wilson(*y)} | Fisher p={fisher(x, y):.3g}")
print("\n## (b) chains with a true regression")
idx = collections.defaultdict(dict)
for r in R:
    idx[(r["agent"], r["cond"], r["zone"], r["chain"])][r["step_id"]] = r
reg = collections.defaultdict(lambda: [0, 0])
for (a, c, z, ch), steps in idx.items():
    own = {s: (steps[s].get("test_status") or {}).get(s, {}) for s in steps}
    hit = any(not ok and own.get(prev, {}).get(t) is True
              for s, r in steps.items() for prev, tests in (r.get("test_status") or {}).items()
              if prev != s for t, ok in tests.items())
    reg[(a, c)][1] += 1; reg[(a, c)][0] += hit
for a in AG:
    print(f"{a}: R {reg[(a,'R')][0]}/{reg[(a,'R')][1]} | F {reg[(a,'F')][0]}/{reg[(a,'F')][1]}")
print("\n## (c) correct, all steps")
for a in AG:
    x, y = corr[(a, "R")], corr[(a, "F")]
    print(f"{a}: R {x[0]}/{x[1]} {wilson(*x)} | F {y[0]}/{y[1]} {wilson(*y)} | Fisher p={fisher(x, y):.3g}")
print("\n## (d) pooled mixed logistic, F coefficient (log-odds, posterior sd)")
df = pd.DataFrame([{"agent": r["agent"], "F": int(r["cond"] == "F"), "zone": r["zone"],
                    "chain": f"{r['agent']}{r['cond']}{r['zone']}{r['chain']}",
                    "correct": int(is_correct(r)),
                    "miss": int(bool(r.get("missed_copy_preexisting"))),
                    "rule": r["kind"] == "rule"} for r in R])
for name, y, sub in (("missed copy (registered), 3 agents", "miss", df[df.rule]),
                     ("correct, 3 agents", "correct", df),
                     ("correct, claude+haiku", "correct", df[df.agent != "codex"])):
    m = BinomialBayesMixedGLM.from_formula(f"{y} ~ F + C(agent) + C(zone)",
                                           {"chain": "0+C(chain)"}, sub).fit_vb()
    i = list(m.model.exog_names).index("F")
    print(f"{name}: F = {m.fe_mean[i]:.2f} (sd {m.fe_sd[i]:.2f}), n = {len(sub)}")
