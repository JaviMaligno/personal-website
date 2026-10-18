"""Study-2 result tables (repetition vs abstraction over chains), from result files only.

`aa tables2` -> `out2/tables2.md` + `out2/summary2.json`.

Input contract (written by the chain evaluator, Task 4):

- one step result per step at
  `<runs>/<agent>/<cond>/<zone>/<chain>/T<k>/result.json` with at least
  `agent`, `cond` (`R`|`F`), `zone` (`Z1`..`Z4`), `chain` (int), `step` (1..4),
  `status` (the runner's: `ok` | `timeout` | `infra` | `infra_exhausted` |
  `setup_error` | `harness_error`), `eval_error` (None when the evaluation ran
  cleanly), `correct`, `consumers_passed`, `consumers_total`, `missed_copy` (all of
  the step's consumers), `missed_copy_preexisting` + `consumers_preexisting_passed` /
  `consumers_preexisting_total` (only the consumers listed at T1 of the zone's
  chain.json), `t2_consumer_ok` (the consumer added at T2, on later steps),
  `carried_defects` (number of previous steps' hidden tests failing, or a list of
  them), `contamination_flag`, `diff` (`added`, `removed`), `tokens` (`input`,
  `output`, `cached_input`), `turns`, `tool_calls`, `wall_s`, and on T2
  `t2_reuses_logic` (`helper` | `copy` | `reimplements` | null), and
  `depends_on_f_comment_fact` (the step's tag in chain.json: its hidden tests depend on
  a fact stated only in F's doc comments; null = untagged);
- one chain result per chain at `<runs>/<agent>/<cond>/<zone>/<chain>/chain_result.json`
  with `duplication`: `{"T0": {"clones": n, "duplicated_lines": n}, ..., "T4": {...}}`
  (`T0` = start of the chain; intermediate steps optional).

Counting rules (spec §5, as study 1):
- only evaluated steps are counted: status not `setup_error` / `harness_error` /
  `infra*`, and `eval_error` None. The rest are reported as excluded, by status and
  by eval error (`excluded`; `excluded_infra` = the `infra*` ones).
- `correct` only if `status == "ok"` and the hidden tests passed (`timeout` counts as
  not correct). T2 correctness is also reported conditional on the chain's T1 being
  correct (T2 builds on T1's tree).
- missed copy is measured on rule steps (T1, T3) only: >= 1 consumer updated and
  >= 1 not. Zero consumers updated is *incorrect*, not a missed copy. Denominator
  (spec amendment 2026-10-08, item 11): every counted rule step of the condition.
  A `timeout` step is counted, on the tree as the agent left it (missed copy if
  0 < updated < total there); a step with zero consumers updated stays in the
  denominator as not missed. A sensitivity table repeats missed copy and correctness
  without the `timeout` steps (`sensitivity_excluding_timeouts`). The primary
  measure counts only the consumers listed at T1 (`missed_copy_preexisting`): at T3
  the consumer the agent added at T2 can fail because T2 failed, so it is reported
  apart (`t2_consumer_ok`), and the all-consumer measure is kept as secondary. Each
  is taken from the evaluator's field when present, else derived from the counts.
- carried defects are counted from T2 on (T1 has no previous steps).
- steps whose transcript tripped the contamination check are counted but flagged.
- doc-comment confound (spec amendment 2026-10-08, item 10): missed copy and
  correctness are also split by the step's `depends_on_f_comment_fact` tag
  (`f_comment_fact_split`: `depends` / `independent`, plus `untagged` if any).
- Z4 is a weak R/F contrast (R already shares the date arithmetic; only the decision
  is repeated, docs/study2-variants.md), marked as such in the per-zone table.
"""

from __future__ import annotations

import json
from math import comb
from pathlib import Path
from statistics import mean, median, quantiles

from aa import config
from aa.stats import mann_whitney_u, wilson

CONDITIONS2: tuple[str, ...] = tuple(getattr(config, "CONDITIONS2", ("R", "F")))
STEPS = (1, 2, 3, 4)
RULE_STEPS = (1, 3)
ZONES = ("Z1", "Z2", "Z3", "Z4")
T2_REUSE = ("helper", "copy", "reimplements")
EXCLUDED_STATUSES = ("setup_error", "harness_error")
WEAK_CONTRAST_ZONES = {
    "Z4": "weak contrast: in R the weekend date arithmetic is already shared "
          "(getDateWithSkippedWeekend); only the decision is repeated",
}


# --- loading ------------------------------------------------------------------------

def load_steps(runs_dir: Path) -> list[dict]:
    """Every step `result.json` under `runs_dir`, in a stable order."""
    return [json.loads(p.read_text()) for p in sorted(Path(runs_dir).rglob("result.json"))]


def load_chains(runs_dir: Path) -> list[dict]:
    """Every `chain_result.json`, with agent/cond/zone/chain filled from the path
    when the file omits them."""
    out = []
    for p in sorted(Path(runs_dir).rglob("chain_result.json")):
        d = json.loads(p.read_text())
        agent, cond, zone, chain = p.parent.parts[-4:]
        d.setdefault("agent", agent)
        d.setdefault("cond", cond)
        d.setdefault("zone", zone)
        d.setdefault("chain", chain)
        out.append(d)
    return out


# --- per-step values ----------------------------------------------------------------

def step_of(r: dict) -> int:
    s = r.get("step")
    return int(str(s).lstrip("Tt")) if s is not None else 0


def chain_id(r: dict) -> str:
    """Chains are only unique within (zone, cond): Z1 chain 0 in R and in F are different
    agent histories, so the random effect is keyed by all three."""
    return f"{r.get('zone')}/{r.get('cond')}/{r.get('chain')}"


def is_infra(status: object) -> bool:
    return str(status).startswith("infra")


def mark_after_infra(steps: list[dict]) -> list[dict]:
    """In memory only: a step that comes after an `infra*` step of its chain was built on
    a tree the chain runner would discard when it re-runs that step (study-3 pilot,
    blocking item 1: steps carried from a network-stalled step); it gets
    `excluded_reason` = `after_infra` and is not counted."""
    by: dict[tuple, list[dict]] = {}
    for r in steps:
        by.setdefault((r.get("agent"), r.get("cond"), r.get("zone"), str(r.get("chain"))),
                      []).append(r)
    for rows in by.values():
        infra = [step_of(r) for r in rows if is_infra(r.get("status"))]
        if infra:
            first = min(infra)
            for r in rows:
                if step_of(r) > first and not is_infra(r.get("status")):
                    r["excluded_reason"] = "after_infra"
    return steps


def exclusion(r: dict) -> str | None:
    """Why a step is not counted (None = counted): its status, `after_infra`
    (:func:`mark_after_infra`), or `eval_error`."""
    if r.get("excluded_reason"):
        return str(r["excluded_reason"])
    status = r.get("status")
    if status in EXCLUDED_STATUSES or is_infra(status):
        return str(status)
    if r.get("eval_error") is not None:
        return "eval_error"
    return None


def is_counted(r: dict) -> bool:
    return exclusion(r) is None


def is_correct(r: dict) -> bool:
    return r.get("status") == "ok" and bool(r.get("correct"))


def comment_fact_group(r: dict) -> str:
    """`depends` / `independent` by the step's chain.json tag, `untagged` without one."""
    v = r.get("depends_on_f_comment_fact")
    return "untagged" if v is None else ("depends" if v else "independent")


def missed_copy(r: dict) -> bool:
    """All of the step's consumers (secondary measure)."""
    if r.get("missed_copy") is not None:
        return bool(r["missed_copy"])
    k, n = int(r.get("consumers_passed") or 0), int(r.get("consumers_total") or 0)
    return 0 < k < n


def preexisting_counts(r: dict) -> tuple[int, int]:
    """(updated, total) over the consumers listed at T1. Results without the split
    (T1, or written before it existed) fall back to all consumers."""
    if r.get("consumers_preexisting_total") is not None \
            and r.get("consumers_preexisting_passed") is not None:
        return int(r["consumers_preexisting_passed"]), int(r["consumers_preexisting_total"])
    return int(r.get("consumers_passed") or 0), int(r.get("consumers_total") or 0)


def missed_copy_preexisting(r: dict) -> bool:
    """Primary measure: missed copy over the consumers listed at T1 only."""
    if r.get("missed_copy_preexisting") is not None:
        return bool(r["missed_copy_preexisting"])
    if r.get("consumers_preexisting_total") is None and r.get("missed_copy") is not None:
        return bool(r["missed_copy"])
    k, n = preexisting_counts(r)
    return 0 < k < n


def carried(r: dict) -> int:
    c = r.get("carried_defects")
    if isinstance(c, list):
        return len(c)
    return int(c or 0)


def lines_changed(r: dict) -> int:
    d = r.get("diff") or {}
    return int(d.get("added", 0)) + int(d.get("removed", 0))


def lines_added(r: dict) -> int:
    return int((r.get("diff") or {}).get("added", 0))


def total_tokens(r: dict) -> int | None:
    """Input + output tokens (cached input reported separately, as study 1); None when
    the step's usage is missing (a Codex step killed before `turn.completed`: study-3
    pilot, blocking item 3), which every distribution excludes and counts."""
    t = r.get("tokens") or {}
    if t.get("input", 0) is None or t.get("output", 0) is None:
        return None
    return int(t.get("input", 0)) + int(t.get("output", 0))


def cached_input(r: dict) -> int | None:
    v = (r.get("tokens") or {}).get("cached_input", 0)
    return None if v is None else int(v)


# --- small helpers ------------------------------------------------------------------

def format_rate(k: int, n: int) -> str:
    if n == 0:
        return "–"
    lo, hi = wilson(k, n)
    return f"{round(100 * k / n)}% [{round(100 * lo)}–{round(100 * hi)}]"


def _rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": k / n if n else None, "ci": [lo, hi],
            "cell": format_rate(k, n)}


def _fmt_p(p: float | None) -> str:
    if p is None:
        return "–"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def _num(x: float) -> float | int:
    return int(x) if float(x).is_integer() else round(float(x), 3)


def _present(values: list) -> list:
    return [v for v in values if v is not None]


def _dist(values: list[float | None]) -> dict:
    """Median [IQR] over the values present; None values (missing usage) are excluded
    and counted (`missing`)."""
    vals = sorted(_present(values))
    missing = len(values) - len(vals)
    if not vals:
        return {"n": 0, "median": None, "iqr": None, "missing": missing}
    if len(vals) == 1:
        iqr = [vals[0], vals[0]]
    else:
        q = quantiles(vals, n=4, method="inclusive")
        iqr = [q[0], q[2]]
    return {"n": len(vals), "median": _num(median(vals)), "iqr": [_num(v) for v in iqr],
            "missing": missing}


def _fmt_dist(d: dict) -> str:
    miss = f", {d['missing']} missing" if d.get("missing") else ""
    if not d["n"]:
        return f"– ({d['missing']} missing)" if d.get("missing") else "–"
    return f"{d['median']} [{d['iqr'][0]}–{d['iqr'][1]}] (n={d['n']}{miss})"


def sign_test(wins: int, losses: int) -> float:
    """Two-sided exact sign test (ties dropped by the caller)."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def _agents(steps: list[dict], chains: list[dict]) -> list[str]:
    seen = {r.get("agent") for r in steps + chains} - {None}
    return [a for a in config.AGENTS if a in seen] + sorted(seen - set(config.AGENTS))


# --- models -------------------------------------------------------------------------

def missed_copy_model(rows: list[dict]) -> dict:
    """Mixed-effects logistic `missed ~ F` with zone and chain random effects
    (statsmodels `BinomialBayesMixedGLM`, as study 1). `rows`: counted rule steps;
    the outcome is the primary measure (pre-existing consumers)."""
    try:
        import pandas as pd
        from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
    except ImportError:
        return {"available": False, "reason": "statsmodels not installed"}
    data = [{"y": int(missed_copy_preexisting(r)), "F": int(r.get("cond") == "F"),
             "zone": str(r.get("zone")), "chain": chain_id(r)}
            for r in rows if r.get("cond") in CONDITIONS2]
    if len({d["y"] for d in data}) < 2:
        return {"available": False, "reason": "no variation in outcome"}
    if len({d["F"] for d in data}) < 2:
        return {"available": False, "reason": "only one condition present"}
    try:
        model = BinomialBayesMixedGLM.from_formula(
            "y ~ F", {"zone": "0 + C(zone)", "chain": "0 + C(chain)"}, pd.DataFrame(data))
        fit = model.fit_vb()
    except Exception as exc:  # noqa: BLE001 - report, never crash the tables
        return {"available": False, "reason": f"fit failed: {exc}"}
    coef = {name: {"mean": float(fit.fe_mean[i]), "sd": float(fit.fe_sd[i])}
            for i, name in enumerate(model.exog_names)}
    vc = {name: float(fit.vcp_mean[i]) for i, name in enumerate(model.vcp_names)}
    return {"available": True, "n": len(data), "coef": coef, "vc_log_sd": vc}


def interaction_model(rows: list[dict], outcome: str, kind: str) -> dict:
    """condition x step on `outcome` (a key of each row), chain random effect.

    kind `logistic`: BinomialBayesMixedGLM; kind `linear`: MixedLM with chain groups.
    `step` enters as a number (trend along the chain); the `F:step` coefficient is the
    H3 interaction (negative = F grows less along the chain than R).
    """
    try:
        import pandas as pd
    except ImportError:
        return {"available": False, "reason": "pandas not installed"}
    data = [{"y": row[outcome], "F": int(row["cond"] == "F"), "step": row["step"],
             "chain": row["chain"]} for row in rows if row["cond"] in CONDITIONS2]
    if len({d["y"] for d in data}) < 2:
        return {"available": False, "reason": "no variation in outcome"}
    if len({d["F"] for d in data}) < 2 or len({d["step"] for d in data}) < 2:
        return {"available": False, "reason": "needs both conditions and >= 2 steps"}
    df = pd.DataFrame(data)
    try:
        if kind == "logistic":
            from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
            df["y"] = (df["y"] > 0).astype(int)
            model = BinomialBayesMixedGLM.from_formula(
                "y ~ F * step", {"chain": "0 + C(chain)"}, df)
            fit = model.fit_vb()
            coef = {n: {"mean": float(fit.fe_mean[i]), "sd": float(fit.fe_sd[i])}
                    for i, n in enumerate(model.exog_names)}
        else:
            import warnings

            import statsmodels.formula.api as smf
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fit = smf.mixedlm("y ~ F * step", df, groups=df["chain"]).fit()
            coef = {n: {"mean": float(fit.fe_params[n]), "sd": float(fit.bse_fe[n]),
                        "p": float(fit.pvalues[n])} for n in fit.fe_params.index}
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "reason": f"fit failed: {exc}"}
    return {"available": True, "kind": kind, "n": len(data), "coef": coef}


# --- summary ------------------------------------------------------------------------

def _duplication_rows(chains: list[dict]) -> list[dict]:
    rows = []
    for c in chains:
        for key, v in (c.get("duplication") or {}).items():
            rows.append({"cond": c.get("cond"), "zone": c.get("zone"), "chain": chain_id(c),
                         "step": int(str(key).lstrip("Tt")),
                         "clones": int(v.get("clones", 0)),
                         "duplicated_lines": int(v.get("duplicated_lines", 0))})
    return rows


def _step_key(r: dict) -> tuple[str, int]:
    return chain_id(r), step_of(r)


def _summarise_agent(steps: list[dict], chains: list[dict], all_steps: list[dict]) -> dict:
    by = {c: [r for r in steps if r.get("cond") == c] for c in CONDITIONS2}
    rule = {c: [r for r in by[c] if step_of(r) in RULE_STEPS] for c in CONDITIONS2}

    def rates(fn, rows_by_cond):
        return {c: _rate(sum(fn(r) for r in rows_by_cond[c]), len(rows_by_cond[c]))
                for c in CONDITIONS2}

    def by_step(fn):
        return {f"T{s}": rates(fn, {c: [r for r in rule[c] if step_of(r) == s]
                                    for c in CONDITIONS2}) for s in RULE_STEPS}

    missed = rates(missed_copy_preexisting, rule)
    missed_by_step = by_step(missed_copy_preexisting)
    missed_all = rates(missed_copy, rule)
    missed_all_by_step = by_step(missed_copy)
    t2_ok = {f"T{s}": rates(lambda r: bool(r.get("t2_consumer_ok")),
                            {c: [r for r in by[c] if step_of(r) == s
                                 and r.get("t2_consumer_ok") is not None]
                             for c in CONDITIONS2}) for s in STEPS[2:]}
    correct = {f"T{s}": {c: _rate(sum(is_correct(r) for r in by[c] if step_of(r) == s),
                                  sum(1 for r in by[c] if step_of(r) == s))
                         for c in CONDITIONS2} for s in STEPS}
    # T2 builds on T1's tree: T2 correct among chains whose T1 is counted and correct.
    t1_correct = {chain_id(r): is_correct(r) for r in steps if step_of(r) == 1}
    t2_given = {}
    for label, want in (("T1_correct", True), ("T1_incorrect", False)):
        t2_given[label] = rates(is_correct, {c: [r for r in by[c] if step_of(r) == 2
                                                 and t1_correct.get(chain_id(r)) is want]
                                             for c in CONDITIONS2})
    coverage = {c: _dist([k / n for k, n in map(preexisting_counts, rule[c]) if n])
                for c in CONDITIONS2}
    t2 = {c: {k: sum(1 for r in by[c] if step_of(r) == 2 and r.get("t2_reuses_logic") == k)
              for k in (*T2_REUSE, None)} for c in CONDITIONS2}
    t2 = {c: {("unknown" if k is None else k): v for k, v in d.items()} for c, d in t2.items()}

    efficiency = {}
    for name, fn in (("lines_added", lines_added), ("lines_changed", lines_changed),
                     ("tokens", total_tokens),
                     ("cached_input", cached_input),
                     ("turns", lambda r: int(r.get("turns") or 0)),
                     ("tool_calls", lambda r: int(r.get("tool_calls") or 0)),
                     ("wall_s", lambda r: float(r.get("wall_s") or 0))):
        per_step = {f"T{s}": {c: _dist([fn(r) for r in by[c] if step_of(r) == s])
                              for c in CONDITIONS2} for s in STEPS}
        allc = {c: _dist([fn(r) for r in by[c]]) for c in CONDITIONS2}
        u, p = mann_whitney_u(_present([fn(r) for r in by.get("R", [])]),
                              _present([fn(r) for r in by.get("F", [])]))
        # Per-zone sign test: in how many zones is F's median below R's.
        wins = losses = 0
        for z in sorted({r.get("zone") for r in steps}):
            rv = _present([fn(r) for r in by.get("R", []) if r.get("zone") == z])
            fv = _present([fn(r) for r in by.get("F", []) if r.get("zone") == z])
            if rv and fv:
                mr, mf = median(rv), median(fv)
                wins += mf < mr
                losses += mf > mr
        efficiency[name] = {"by_step": per_step, "all": allc,
                            "mann_whitney_R_vs_F": {"u": u, "p": p},
                            "zones_F_lower": wins, "zones_F_higher": losses,
                            "sign_p": sign_test(wins, losses)}

    # Cost growth: T4 tokens / T1 tokens within each chain.
    growth = {}
    for c in CONDITIONS2:
        ratios = []
        for cid in sorted({chain_id(r) for r in by[c]}):
            t1 = [total_tokens(r) for r in by[c] if chain_id(r) == cid and step_of(r) == 1]
            t4 = [total_tokens(r) for r in by[c] if chain_id(r) == cid and step_of(r) == 4]
            if t1 and t4 and t1[0] and t4[0] is not None:
                ratios.append(t4[0] / t1[0])
        growth[c] = _dist(ratios)

    # Carried defects, condition x step (T2..T4).
    carried_rows = [{"cond": r.get("cond"), "step": step_of(r), "chain": chain_id(r),
                     "carried": carried(r)} for r in steps if step_of(r) >= 2]
    carried_tab = {f"T{s}": {c: {**_rate(sum(1 for x in carried_rows if x["cond"] == c
                                             and x["step"] == s and x["carried"] > 0),
                                         sum(1 for x in carried_rows if x["cond"] == c
                                             and x["step"] == s)),
                                 "mean_count": _num(mean(xs)) if (xs := [
                                     x["carried"] for x in carried_rows
                                     if x["cond"] == c and x["step"] == s]) else None}
                             for c in CONDITIONS2} for s in STEPS[1:]}

    # Duplication after step k only where step k is counted (T0 = the chain's start).
    counted_keys = {_step_key(r) for r in steps}
    dup_rows = [d for d in _duplication_rows(chains)
                if d["step"] == 0 or (d["chain"], d["step"]) in counted_keys]
    dup_tab = {}
    for s in sorted({d["step"] for d in dup_rows}):
        dup_tab[f"T{s}"] = {}
        for c in CONDITIONS2:
            sel = [d for d in dup_rows if d["cond"] == c and d["step"] == s]
            dup_tab[f"T{s}"][c] = {
                "n": len(sel),
                "clones_mean": _num(mean(d["clones"] for d in sel)) if sel else None,
                "dup_lines_mean": _num(mean(d["duplicated_lines"] for d in sel))
                if sel else None}
    dup_growth = {}
    for c in CONDITIONS2:
        deltas = []
        for ch in [x for x in chains if x.get("cond") == c]:
            d = ch.get("duplication") or {}
            if "T0" in d and "T4" in d and (chain_id(ch), 4) in counted_keys:
                deltas.append(int(d["T4"].get("duplicated_lines", 0))
                              - int(d["T0"].get("duplicated_lines", 0)))
        dup_growth[c] = _dist(deltas)

    # Sensitivity: the same headline rates without the timed-out steps.
    no_to = {c: [r for r in by[c] if r.get("status") != "timeout"] for c in CONDITIONS2}
    no_to_rule = {c: [r for r in no_to[c] if step_of(r) in RULE_STEPS] for c in CONDITIONS2}
    sensitivity = {
        "timeouts_dropped": {c: sum(1 for r in by[c] if r.get("status") == "timeout")
                             for c in CONDITIONS2},
        "missed_copy": rates(missed_copy_preexisting, no_to_rule),
        "missed_copy_by_step": {f"T{s}": rates(missed_copy_preexisting,
                                               {c: [r for r in no_to_rule[c]
                                                    if step_of(r) == s] for c in CONDITIONS2})
                                for s in RULE_STEPS},
        "correct_by_step": {f"T{s}": rates(is_correct, {c: [r for r in no_to[c]
                                                            if step_of(r) == s]
                                                        for c in CONDITIONS2})
                            for s in STEPS},
    }

    # Doc-comment confound: missed copy (primary) and correctness by the step's tag.
    groups = [g for g in ("depends", "independent", "untagged")
              if g != "untagged" or any(comment_fact_group(r) == g for r in steps)]
    fact_split = {g: {
        "missed_copy": rates(missed_copy_preexisting,
                             {c: [r for r in rule[c] if comment_fact_group(r) == g]
                              for c in CONDITIONS2}),
        "correct": rates(is_correct, {c: [r for r in by[c] if comment_fact_group(r) == g]
                                      for c in CONDITIONS2}),
    } for g in groups}

    zones = sorted({r.get("zone") for r in steps}, key=str)
    per_zone = {z: {c: {
        "missed_copy": _rate(sum(missed_copy_preexisting(r) for r in rule[c]
                                 if r.get("zone") == z),
                             sum(1 for r in rule[c] if r.get("zone") == z)),
        "correct": _rate(sum(is_correct(r) for r in by[c] if r.get("zone") == z),
                         sum(1 for r in by[c] if r.get("zone") == z)),
        "tokens": _dist([total_tokens(r) for r in by[c] if r.get("zone") == z]),
        "lines_added": _dist([lines_added(r) for r in by[c] if r.get("zone") == z]),
    } for c in CONDITIONS2} for z in zones}
    per_zone_notes = {z: WEAK_CONTRAST_ZONES[z] for z in zones if z in WEAK_CONTRAST_ZONES}

    reasons = [x for x in map(exclusion, all_steps) if x is not None]
    eval_errors = [str(r.get("eval_error")) for r in all_steps
                   if exclusion(r) == "eval_error"]
    contaminated = [r for r in steps if r.get("contamination_flag")]

    return {
        "n_by_status": {c: {s: sum(1 for r in by[c] if r.get("status") == s)
                            for s in sorted({str(r.get("status")) for r in by[c]})}
                        for c in CONDITIONS2},
        "excluded_infra": sum(1 for x in reasons if is_infra(x)),
        "excluded": {"total": len(reasons),
                     "by_reason": {k: reasons.count(k) for k in sorted(set(reasons))},
                     "eval_errors": {k: eval_errors.count(k) for k in sorted(set(eval_errors))},
                     "by_cond": {c: sum(1 for r in all_steps if r.get("cond") == c
                                        and exclusion(r) is not None) for c in CONDITIONS2}},
        "contamination": {"by_cond": {c: sum(1 for r in contaminated if r.get("cond") == c)
                                      for c in CONDITIONS2},
                          "steps": [f"{r.get('cond')}/{r.get('zone')}/{r.get('chain')}/"
                                    f"T{step_of(r)}" for r in contaminated]},
        "missed_copy": missed,
        "missed_copy_by_step": missed_by_step,
        "missed_copy_model": missed_copy_model(rule.get("R", []) + rule.get("F", [])),
        "missed_copy_all_consumers": missed_all,
        "missed_copy_all_consumers_by_step": missed_all_by_step,
        "t2_consumer_ok": t2_ok,
        "coverage": coverage,
        "correct_by_step": correct,
        "t2_correct_given_t1": t2_given,
        "t2_reuse": t2,
        "efficiency": efficiency,
        "cost_growth_T4_over_T1": growth,
        "carried_defects": carried_tab,
        "carried_defects_model": interaction_model(carried_rows, "carried", "logistic"),
        "duplication": dup_tab,
        "duplication_growth_T0_to_T4": dup_growth,
        "duplication_model": interaction_model(
            [{**d, "y": d["duplicated_lines"]} for d in dup_rows], "y", "linear"),
        "sensitivity_excluding_timeouts": sensitivity,
        "f_comment_fact_split": fact_split,
        "per_zone": per_zone,
        "per_zone_notes": per_zone_notes,
    }


def summarise(steps: list[dict], chains: list[dict] | None = None) -> dict:
    chains = chains or []
    out = {}
    for agent in _agents(steps, chains):
        mine = [r for r in steps if r.get("agent") == agent]
        out[agent] = _summarise_agent(
            [r for r in mine if is_counted(r)],
            [c for c in chains if c.get("agent") == agent], mine)
    return out


# --- markdown -----------------------------------------------------------------------

def _model_line(m: dict, term: str) -> str:
    if not m.get("available"):
        return f"unavailable: {m['reason']}"
    co = m["coef"].get(term)
    if not co:
        return "–"
    p = f", p = {_fmt_p(co['p'])}" if "p" in co else ""
    return f"{term} = {co['mean']:.2f} (sd {co['sd']:.2f}{p}), n = {m['n']}"


def render_markdown(summary: dict) -> str:
    C = CONDITIONS2
    head = "| | " + " | ".join(C) + " |"
    sep = "|---" * (len(C) + 1) + "|"
    lines = ["# Study 2 results tables", "",
             "Generated by `aa tables2` from `result.json` / `chain_result.json` files. "
             "Rates are `rate [Wilson 95% CI]`; distributions are `median [IQR] (n)`; "
             "Only evaluated steps are counted (not `setup_error` / `harness_error` / "
             "`infra*`, no `eval_error`); `timeout` counts as not correct.", ""]
    for agent, s in summary.items():
        ex = s["excluded"]
        lines += [f"## {agent}", "",
                  "Steps counted: " + ", ".join(
                      f"{c} {sum(s['n_by_status'][c].values())}" for c in C)
                  + f"; excluded: {ex['total']} ("
                  + (", ".join(f"{k} {v}" for k, v in ex["by_reason"].items()) or "none")
                  + ")" + ("; eval errors: " + ", ".join(
                      f"{k} {v}" for k, v in ex["eval_errors"].items())
                      if ex["eval_errors"] else "") + ".", ""]
        ct = s["contamination"]
        if ct["steps"]:
            lines += ["**Contamination flagged** (counted, read with care): "
                      + ", ".join(f"{c} {ct['by_cond'][c]}" for c in C)
                      + " — " + ", ".join(ct["steps"][:20])
                      + (" …" if len(ct["steps"]) > 20 else "") + ".", ""]

        lines += ["### Missed copy on rule steps (T1, T3) — H1", "",
                  "Primary: consumers listed at T1 only (the T2-added consumer apart).",
                  "", head, sep,
                  "| T1+T3 | " + " | ".join(s["missed_copy"][c]["cell"] for c in C) + " |"]
        for st, row in s["missed_copy_by_step"].items():
            lines.append(f"| {st} | " + " | ".join(row[c]["cell"] for c in C) + " |")
        lines.append("| consumer coverage (T1 consumers) | "
                     + " | ".join(_fmt_dist(s["coverage"][c]) for c in C) + " |")
        lines.append("| secondary: all consumers, T1+T3 | " + " | ".join(
            s["missed_copy_all_consumers"][c]["cell"] for c in C) + " |")
        for st, row in s["t2_consumer_ok"].items():
            lines.append(f"| T2-added consumer updated at {st} | "
                         + " | ".join(row[c]["cell"] for c in C) + " |")
        lines += ["", "Mixed-effects logistic (zone and chain random effects): "
                  + _model_line(s["missed_copy_model"], "F")
                  + " (log-odds of F vs R).", ""]

        sv = s["sensitivity_excluding_timeouts"]
        lines += ["### Sensitivity: without timed-out steps", "",
                  "Timed-out steps dropped: " + ", ".join(
                      f"{c} {sv['timeouts_dropped'][c]}" for c in C) + ".", "", head, sep,
                  "| missed copy T1+T3 | " + " | ".join(
                      sv["missed_copy"][c]["cell"] for c in C) + " |"]
        for st, row in sv["missed_copy_by_step"].items():
            lines.append(f"| missed copy {st} | " + " | ".join(row[c]["cell"] for c in C)
                         + " |")
        for st, row in sv["correct_by_step"].items():
            lines.append(f"| correct {st} | " + " | ".join(row[c]["cell"] for c in C) + " |")
        lines += ["", "### Doc-comment confound: steps whose tests depend on a fact stated "
                  "only in F's comments", "",
                  "| group | " + " | ".join(f"{c} missed copy (T1+T3)" for c in C) + " | "
                  + " | ".join(f"{c} correct" for c in C) + " |",
                  "|---" * (2 * len(C) + 1) + "|"]
        for g, row in s["f_comment_fact_split"].items():
            lines.append(f"| {g} | " + " | ".join(row["missed_copy"][c]["cell"] for c in C)
                         + " | " + " | ".join(row["correct"][c]["cell"] for c in C) + " |")
        lines += ["", "An F advantage confined to `depends` is at least partly a "
                  "documentation effect, not a shape effect.", ""]

        lines += ["### Correct per step", "", head, sep]
        for st, row in s["correct_by_step"].items():
            lines.append(f"| {st} | " + " | ".join(row[c]["cell"] for c in C) + " |")
        for label, row in s["t2_correct_given_t1"].items():
            lines.append(f"| T2 given {label.replace('_', ' ')} | "
                         + " | ".join(row[c]["cell"] for c in C) + " |")
        lines += ["", "T2 new consumer: " + "; ".join(
            f"{c} " + ", ".join(f"{k} {v}" for k, v in s["t2_reuse"][c].items()) for c in C)
            + ".", ""]

        lines += ["### Efficiency per step — H2", ""]
        for name, e in s["efficiency"].items():
            lines += [f"**{name}**", "", head, sep]
            for st, row in e["by_step"].items():
                lines.append(f"| {st} | " + " | ".join(_fmt_dist(row[c]) for c in C) + " |")
            lines.append("| all | " + " | ".join(_fmt_dist(e["all"][c]) for c in C) + " |")
            mw = e["mann_whitney_R_vs_F"]
            lines += ["", f"Mann-Whitney R vs F: U = {mw['u']:g}, p = {_fmt_p(mw['p'])}; "
                      f"zones with F median lower {e['zones_F_lower']}, higher "
                      f"{e['zones_F_higher']} (sign test p = {_fmt_p(e['sign_p'])}).", ""]
        lines += ["Cost growth (T4 tokens / T1 tokens per chain): " + "; ".join(
            f"{c} {_fmt_dist(s['cost_growth_T4_over_T1'][c])}" for c in C) + ".", ""]

        lines += ["### Carried defects, condition x step — H3", "",
                  "| step | " + " | ".join(f"{c} any (mean count)" for c in C) + " |", sep]
        for st, row in s["carried_defects"].items():
            lines.append(f"| {st} | " + " | ".join(
                f"{row[c]['cell']} ({'–' if row[c]['mean_count'] is None else row[c]['mean_count']})"
                for c in C) + " |")
        lines += ["", "Mixed-effects logistic (chain random effect): "
                  + _model_line(s["carried_defects_model"], "F:step") + ".", ""]

        lines += ["### Duplication (jscpd, zone files), condition x step — H3", "",
                  "| step | " + " | ".join(f"{c} clones / dup. lines (n)" for c in C) + " |",
                  sep]
        for st, row in s["duplication"].items():
            lines.append(f"| {st} | " + " | ".join(
                "–" if not row[c]["n"] else
                f"{row[c]['clones_mean']} / {row[c]['dup_lines_mean']} ({row[c]['n']})"
                for c in C) + " |")
        lines += ["", "Duplicated lines T4 − T0 per chain: " + "; ".join(
            f"{c} {_fmt_dist(s['duplication_growth_T0_to_T4'][c])}" for c in C) + ".",
            "Mixed linear model (chain random effect): "
            + _model_line(s["duplication_model"], "F:step") + ".", ""]

        lines += ["### Per zone", "",
                  "| zone | cond | missed copy | correct | tokens | lines added |",
                  "|---|---|---|---|---|---|"]
        for z, row in s["per_zone"].items():
            zl = f"{z} (weak contrast)" if z in s["per_zone_notes"] else z
            for c in C:
                v = row[c]
                lines.append(f"| {zl} | {c} | {v['missed_copy']['cell']} | "
                             f"{v['correct']['cell']} | {_fmt_dist(v['tokens'])} | "
                             f"{_fmt_dist(v['lines_added'])} |")
        lines += [""] + [f"{z}: {note}." for z, note in s["per_zone_notes"].items()]
        lines += ["", "Differences are read with their intervals; nothing near p = 0.05 "
                  "is read as an effect on its own.", ""]
    return "\n".join(lines)


def build(runs_dir: Path, out_dir: Path) -> dict:
    """Write `tables2.md` and `summary2.json` into `out_dir`; return the summary."""
    summary = summarise(load_steps(runs_dir), load_chains(runs_dir))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tables2.md").write_text(render_markdown(summary))
    (out_dir / "summary2.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary
