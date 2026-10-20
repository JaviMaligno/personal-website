"""Study-3 result tables (the agent as abstraction designer), from result files only.

`aa tables3` -> `out/study3/tables3.md` + `out/study3/summary3.json` (spec
`docs/specs/2026-10-10-agent-as-designer-design.md` sections 6-8 and its amendments;
plan Task 6).

Inputs
------
- Study-3 step results, `<runs3>/<agent>/<arm>/<zone>/<chain>/T<k>/result.json`
  (arms R, RG, RL, RC; RC chains also have `T0/result.json`, `step` 0), written by the
  chain evaluator (`aa.chain_eval` + `aa.chain_eval3`): the study-2 fields
  (`aa.tables2`'s contract) plus `lint_runs`, `ratchet_trips`, `ratchet_final`
  (`{"fires": bool, ...}` or None), `ratchet_kind`, `ratchet_split`, `gaming_flags`
  (`{flag: [paths]}`), `rule_cited`, `rule_cited_detail.reuse_talk`,
  `rule_sites_touched`, and on T0 `probe_unchanged`, `probe_changed_cases`,
  `inconsistencies_unified`, `typecheck_ok`, `lint_ok`, `related_ok`.
- Chain results, `chain_result.json`: `duplication` with `T0` (the tree T1 starts from:
  the untouched variant, or in RC the agent's post-T0 tree), `T1`..`T4` and, in RC,
  `start` (the untouched variant).
- F (descriptive only): the study-2 F steps and chains (`runs2/`, cond `F`).
- Judge labels (optional, plan Task 7): a JSON object keyed
  `"<agent>/<arm>/<zone>/<chain>/T<k>"` with any of `t2_reuse`
  (`helper` | `copy` | `reimplements`), `one_place` (bool, rule steps), `completeness`
  (0..1, T0) and `interface` (1..5, T0). Absent labels are reported as pending.

Counting rules
--------------
- As study 2 (`aa.tables2`): only evaluated steps count (not `setup_error` /
  `harness_error` / `infra*`, no `eval_error`); `timeout` is not correct; missed copy is
  the registered one (consumers listed at T1, rule steps T1/T3); carried defects from T2.
- **T1-T4 metrics never include RC's T0** (Review Focus 3): every per-step comparison
  (T2 reuse, missed copy, correct, carried, efficiency, RL/RG fields) is over steps 1-4.
  T0 has its own table. **Chain totals** (tokens, wall time) are given both T1-T4 only
  and over all steps (RC with T0, spec H5); a chain is totalled only when every one of
  its steps (T0 included in RC) has a result whose status is not excluded.
- Each lever arm is compared with R per agent, over all zones and without Z4 (spec
  section 8: Z4 is pre-declared weak). RL's confirmatory scope is the non-blind zones
  Z1 + Z3 (amendments 2026-10-10 / 2026-10-11: Z2 and Z4 lint-blind at min-tokens 35,
  a disclosed deviation); its all-zones rows are descriptive.
- Rates are Wilson 95 % intervals; the lever effect is a mixed-effects logistic `y ~ L`
  (L = 1 for the lever arm, 0 for R) with zone and, when a chain contributes more than
  one row, chain random effects (statsmodels `BinomialBayesMixedGLM`, as `aa.tables2`).
  Distributions are median [IQR], compared by Mann-Whitney and per-zone sign tests.
- T2 reuse: the judge label is primary (spec amendment 2026-10-11b), the static3 label
  (`t2_reuses_logic`) secondary; each rate's denominator is the steps with that label.
- RL: a step *fired* when the agent saw a dup-check failure (`ratchet_trips` > 0) or
  the ratchet fires on its final tree; H4 = fired steps that end passing with no gaming
  flag. Lint runs and efficiency are also split by `ratchet_split` (amendment
  2026-10-11b), in every arm (R, RG, RC: the counterfactual). Beside the registered H4,
  a *seen-only* H4 over the steps where the agent saw the ratchet fire.
- Pilot blocking fixes (2026-10-12): a step after an `infra*` step of its chain was
  built on a tree the runner discards when it re-runs that step (`after_infra`, not
  counted); missing usage (`tokens` None: a Codex step killed before `turn.completed`)
  is excluded from every token distribution and counted (`n=…, k missing`), and a chain
  with a missing step has no token total; `inconsistencies_unified_step` (the T0
  inconsistency tests still in scope at the step, on its post tree) is reported per arm
  and step, beside H4 and the T2 static label.
- Pre-pilot review (2026-10-11): T0's pooled "any inconsistency unified" is over Z1-Z3
  (Z4 has no inconsistency tests; shown apart); T0's typecheck / lint / related checks
  keep evals with a non-fatal `eval_error` (amendment 2026-10-11d: checks that ran are
  kept, a check that did not run is None); an RC chain without `duplication.start` is
  missing for the start-based growth (counted), never read as its T0; efficiency is
  given per step as well as pooled; judged rows say "kappa pending" until a kappa is
  supplied (`aa tables3 --kappa`).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from statistics import mean, median

from aa import config, rg_check
from aa.stats import mann_whitney_u, wilson
from aa.tables2 import (_agents, _dist, _fmt_dist, _fmt_p, _num, _present, _rate,
                        cached_input, carried, chain_id, exclusion, is_correct, is_counted,
                        is_infra, lines_added, lines_changed, load_chains, mark_after_infra,
                        missed_copy_preexisting, sign_test, step_of, total_tokens)

ARMS: tuple[str, ...] = tuple(config.CONDITIONS3)
LEVERS: tuple[str, ...] = tuple(a for a in ARMS if a != "R")
STEPS = (1, 2, 3, 4)
RULE_STEPS = (1, 3)
ZONES = ("Z1", "Z2", "Z3", "Z4")
# Amendment 2026-10-11 (unchanged from 2026-10-10): T2 copy sensitivity < 50 % at 35.
LINT_BLIND = ("Z2", "Z4")
NON_BLIND = tuple(z for z in ZONES if z not in LINT_BLIND)
# Zones without T0 inconsistency tests (spec section 3: Z4 has none; its
# `inconsistencies_unified` is always empty): kept out of the pooled rate.
NO_INCONSISTENCY_TESTS = ("Z4",)
# Judge-based measures (plan Task 7) and the kappa that must precede any comparison.
JUDGED = ("t2_reuse", "one_place", "completeness", "interface")
SCOPES = {"all": ZONES, "without_Z4": ("Z1", "Z2", "Z3"), "non_blind": NON_BLIND}
SCOPE_LABEL = {"all": "all zones", "without_Z4": "without Z4",
               "non_blind": "non-blind Z1+Z3 †"}
RATCHET_SPLITS = ("adds_new_clone_side", "touches_preexisting_only", "modified_into_clone",
                  "no_fire", "unknown")
T2_REUSE = ("helper", "copy", "reimplements")
# H4's fired-step classes (spec amendment 2026-10-12b, item 6), in the registered order;
# "seen_passing" stands for (a)+(ab)+(b)+(u) on results without `ratchet_trip_clones`
H4_SUCCESS = ("a", "ab", "b", "u", "seen_passing")
H4_FAILURE = ("g", "c", "d0", "d1")
H4_CLASSES = (*H4_SUCCESS, *H4_FAILURE)
H4_CLASS_LABEL = {
    "a": "(a) consolidation", "ab": "(ab) mixed", "b": "(b) edit moved outside the clone",
    "u": "(u) unreadable", "seen_passing": "seen, passing (split not derived)",
    "g": "(g) passing with a gaming flag", "c": "(c) seen, not fixed",
    "d0": "(d0) never seen, no lint run", "d1": "(d1) never seen, lint run"}
# Calibration of ratchet firing (amendment 2026-10-11; benchmark rule: amendment
# 2026-10-12b, item 5): study-2 R trees, fired / steps per zone x step at min-tokens 35.
CALIBRATION_FILE = config.ROOT / "out" / "study3" / "ratchet-calibration-summary.json"
# arms whose firing is benchmarked against calibration at every step (counterfactual
# ratchet_final); RL only at T1 (its later trees are downstream of the treatment)
CALIBRATED_ARMS = ("R", "RG", "RC")
RG_RULE_FILE = config.ROOT / "tasks3" / "rg-rule.md"
RG_RULE_FALLBACK = ("Do not copy logic: when new code needs behaviour that already exists, "
                    "extract it into a shared function and reuse it; when a rule changes, "
                    "change it in one place.")
EFFICIENCY: dict[str, Callable[[dict], float]] = {
    "tokens": total_tokens,
    "cached_input": cached_input,
    "turns": lambda r: int(r.get("turns") or 0),
    "tool_calls": lambda r: int(r.get("tool_calls") or 0),
    "wall_s": lambda r: float(r.get("wall_s") or 0),
    "lines_added": lines_added,
    "lines_changed": lines_changed,
}
RATCHET_NOTE = (
    "† RL's confirmatory scope. The ratchet runs jscpd at **min-tokens 35**, a disclosed "
    "post-hoc deviation from the registered calibration rule (which gives 25; spec "
    "amendment 2026-10-11, decided before any study-3 run): pooled T2 sensitivity 47/93 "
    "= 51 % [41–60], FPR 29/91 = 32 % [23–42]. Lint-blind zones (T2 copy sensitivity "
    "< 50 %): Z2, Z4, excluded from RL's confirmatory analyses and kept descriptively. "
    "Z3 stays in but is non-discriminating (fires on helper and copy steps alike); the "
    "ratchet also fires at rule steps (Z1/Z3 T1, Z4 T3) and every Z1/Z3 T4, in R and F.")


# --- loading ------------------------------------------------------------------------

def load_steps(runs_dir: Path) -> list[dict]:
    """Every step `result.json` (`<agent>/<arm>/<zone>/<chain>/T<k>/`), stable order;
    evaluator side files deeper in the step dir are never read."""
    return mark_after_infra([json.loads(p.read_text())
                             for p in sorted(Path(runs_dir).glob("*/*/*/*/T*/result.json"))])


def load_f_steps(runs2_dir: Path | None) -> list[dict]:
    if runs2_dir is None or not Path(runs2_dir).is_dir():
        return []
    return [r for r in load_steps(runs2_dir) if r.get("cond") == "F"]


def load_f_chains(runs2_dir: Path | None) -> list[dict]:
    if runs2_dir is None or not Path(runs2_dir).is_dir():
        return []
    return [c for c in load_chains(runs2_dir) if c.get("cond") == "F"]


def load_labels(path: Path | None) -> dict[str, dict]:
    if path is None or not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text())


def load_kappa(path: Path | None) -> dict[str, float | None]:
    """``aa tables3 --kappa``: the flat {measure: kappa} JSON of
    ``scripts/study3_design_review.py --kappa-out``; also its full result JSON
    (``design_review3.json``: ``kappa``, or ``reliability.questions.<q>.kappa``). A
    given file that is missing, or holds none of :data:`JUDGED`, is an error (before:
    silently "kappa pending")."""
    if path is None:
        return {}
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict) and isinstance(data.get("kappa"), dict):
        data = data["kappa"]
    elif isinstance(data, dict) and isinstance(data.get("reliability"), dict):
        qs = data["reliability"].get("questions") or {}
        data = {q: (qs.get(q) or {}).get("kappa") for q in JUDGED if q in qs}
    if not isinstance(data, dict) or not any(q in data for q in JUDGED):
        raise ValueError(f"{path}: no kappa for any of {', '.join(JUDGED)}")
    return {q: data.get(q) for q in JUDGED}


def rg_rule_text(path: Path = RG_RULE_FILE) -> str:
    try:
        for line in Path(path).read_text().splitlines():
            if line.startswith("Do not copy logic"):
                return line.strip()
    except OSError:
        pass
    return RG_RULE_FALLBACK


# --- per-step values ----------------------------------------------------------------

def step_key(r: dict) -> str:
    return f"{r.get('agent')}/{r.get('cond')}/{r.get('zone')}/{r.get('chain')}/T{step_of(r)}"


def label(r: dict, labels: dict[str, dict], name: str):
    return (labels.get(step_key(r)) or {}).get(name)


def gamed(r: dict) -> bool:
    return any(bool(v) for v in (r.get("gaming_flags") or {}).values())


def final_fires(r: dict) -> bool | None:
    rf = r.get("ratchet_final")
    return None if rf is None else bool(rf.get("fires"))


def fired(r: dict) -> bool:
    """The ratchet fired on the step: the agent saw a dup-check failure, or it fires on
    the final tree (RL; in other arms only the latter, as a counterfactual)."""
    return int(r.get("ratchet_trips") or 0) > 0 or bool(final_fires(r))


def split_of(r: dict) -> str:
    s = r.get("ratchet_split")
    return s if s in RATCHET_SPLITS else "unknown"


def h4_class(r: dict) -> str | None:
    """The class of an RL step in H4's decomposition (amendment 2026-10-12b, item 6), or
    None when the ratchet did not fire or its final-tree result is missing (outside H4's
    denominator). Tested in the registered order: (g) passing with a gaming flag; (d0) /
    (d1) fired on the final tree, never seen (no lint run / lint run); (c) seen, not
    fixed; then seen, passing split by ``ratchet_trip_clones``: (u) a trip unreadable,
    (a) no listed pre-existing clone remains, (b) all remain, (ab) some remain;
    ``seen_passing`` when the field is not derived yet."""
    ff = final_fires(r)
    if not fired(r) or ff is None:
        return None
    trips = int(r.get("ratchet_trips") or 0)
    if not ff and gamed(r):
        return "g"
    if trips == 0:
        return "d0" if int(r.get("lint_runs") or 0) == 0 else "d1"
    if ff:
        return "c"
    tc = r.get("ratchet_trip_clones")
    if tc is None:
        return "seen_passing"
    if int(tc.get("unreadable_trips") or 0) > 0 or \
            any(k is None for k in (r.get("ratchet_trip_kinds") or [])):
        return "u"
    listed, remaining = int(tc.get("listed_preexisting") or 0), int(tc.get("remaining") or 0)
    if remaining == 0:
        return "a"
    return "b" if remaining == listed else "ab"


def h4_decomposition(rl_rows: list[dict]) -> dict:
    """Per scope (non-blind Z1+Z3, all zones) and period (all steps, T1, T2-T4): fired
    steps, counts per class, registered H4 (successes / fired) and how many successes
    unified an in-scope T0 inconsistency (``inconsistencies_unified_step``)."""
    out: dict = {}
    for scope, zones in (("non_blind", NON_BLIND), ("all", ZONES)):
        out[scope] = {}
        for period, steps in (("all_steps", STEPS), ("T1", (1,)), ("T2_T4", (2, 3, 4))):
            cls = [(r, h4_class(r)) for r in rl_rows
                   if r.get("zone") in zones and step_of(r) in steps]
            cls = [(r, c) for r, c in cls if c is not None]
            succ = [r for r, c in cls if c in H4_SUCCESS]
            out[scope][period] = {
                "fired": len(cls),
                "counts": {k: sum(1 for _, c in cls if c == k) for k in H4_CLASSES},
                "h4": _rate(len(succ), len(cls)),
                "success_unified": sum(1 for r in succ
                                       if r.get("inconsistencies_unified_step")),
            }
    return out


def load_calibration(path: Path | None = CALIBRATION_FILE) -> dict | None:
    """The calibration's R cells {zone: {T<k>: [fired, n]}} (study-2 R trees at
    min-tokens 35), or None when the file is missing."""
    if path is None or not Path(path).exists():
        return None
    d = json.loads(Path(path).read_text())
    return (d.get("firing_by_step_at_chosen") or {}).get("R")


def calibration_table(rows: list[dict], calib: dict | None) -> dict | None:
    """Amendment 2026-10-12b, item 5: per zone x step, each arm's firing (seen or on the
    final tree; outside RL only the counterfactual final tree) with its Wilson interval
    beside calibration's. Benchmarked cells: R, RG and RC at T1-T4 and RL at T1; a
    benchmarked cell whose interval does not overlap calibration's is *off calibration*
    (to be read in the traces before any interpretation). RL at T2-T4 is a treatment
    outcome, never benchmarked (``off`` None)."""
    if not calib:
        return None
    rows = [r for r in rows if step_of(r) in STEPS and final_fires(r) is not None]
    arms = [a for a in ARMS if any(r.get("cond") == a for r in rows)]
    cells: dict = {}
    off: list[list[str]] = []
    cal_rates: dict = {}
    for z in ZONES:
        cells[z], cal_rates[z] = {}, {}
        for s in STEPS:
            st = f"T{s}"
            k, n = (calib.get(z) or {}).get(st) or (0, 0)
            cr = _rate(int(k), int(n))
            cal_rates[z][st] = cr
            cells[z][st] = {}
            for a in arms:
                sel = [r for r in rows if r.get("cond") == a and r.get("zone") == z
                       and step_of(r) == s]
                rate = _rate(sum(1 for r in sel if fired(r)), len(sel))
                bench = a in CALIBRATED_ARMS or (a == "RL" and s == 1)
                flag = None
                if bench and sel and n:
                    lo, hi = wilson(rate["k"], rate["n"])
                    clo, chi = wilson(int(k), int(n))
                    flag = hi < clo or lo > chi
                    if flag:
                        off.append([z, st, a])
                cells[z][st][a] = {"rate": rate, "benchmarked": bench, "off": flag}
    return {"arms": arms, "calibration": cal_rates, "cells": cells, "off": off}


def chain_index(rows: list[dict]) -> dict[tuple, dict[str, dict]]:
    """(agent, chain id) -> {step id: result}."""
    idx: dict[tuple, dict[str, dict]] = {}
    for r in rows:
        idx.setdefault((r.get("agent"), chain_id(r)), {})[
            r.get("step_id") or f"T{step_of(r)}"] = r
    return idx


def carried_split(r: dict, idx: dict[tuple, dict[str, dict]]) -> dict[str, int]:
    """Carried failures of earlier steps' hidden tests, split into *regressions* (the
    test passed at its own step) and *never passed* (it failed there too); `unknown`
    when the own step's status is not available (or the result has no
    `test_status`, then the whole `carried_defects` count)."""
    out = {"regressions": 0, "never_passed": 0, "unknown": 0}
    ts = r.get("test_status")
    if not ts:
        out["unknown"] = carried(r)
        return out
    sid = r.get("step_id") or f"T{step_of(r)}"
    chain = idx.get((r.get("agent"), chain_id(r)), {})
    for prev, tests in ts.items():
        if prev == sid:
            continue
        own = ((chain.get(prev) or {}).get("test_status") or {}).get(prev) or {}
        for t, ok in tests.items():
            if ok:
                continue
            if own.get(t) is True:
                out["regressions"] += 1
            elif own.get(t) is False:
                out["never_passed"] += 1
            else:
                out["unknown"] += 1
    return out


def chain_totals(all_steps: list[dict]) -> list[dict]:
    """Tokens and wall time per chain, T1-T4 and over all steps (RC with T0). A chain
    is totalled only when each expected step has a result whose status is not
    excluded (`eval_error` does not matter: the agent ran)."""
    by: dict[tuple, dict[int, dict]] = {}
    for r in all_steps:
        by.setdefault((r.get("agent"), r.get("cond"), r.get("zone"), str(r.get("chain"))),
                      {})[step_of(r)] = r
    out = []
    for (agent, arm, zone, chain), steps in sorted(by.items(), key=lambda kv: str(kv[0])):
        want = (0, *STEPS) if arm == "RC" else STEPS
        if any(k not in steps or steps[k].get("status") in ("setup_error", "harness_error")
               or is_infra(steps[k].get("status")) or steps[k].get("excluded_reason")
               for k in want):
            continue
        t14 = [steps[k] for k in STEPS]
        every = [steps[k] for k in want]

        def tok(rs: list[dict]) -> int | None:  # None when any step's usage is missing
            v = [total_tokens(r) for r in rs]
            return None if any(x is None for x in v) else sum(v)
        out.append({"agent": agent, "cond": arm, "zone": zone, "chain": chain,
                    "tokens_t1_t4": tok(t14),
                    "tokens_all_steps": tok(every),
                    "tokens_missing_steps": sum(total_tokens(r) is None for r in every),
                    "wall_s_t1_t4": sum(float(r.get("wall_s") or 0) for r in t14),
                    "wall_s_all_steps": sum(float(r.get("wall_s") or 0) for r in every)})
    return out


# --- models -------------------------------------------------------------------------

def lever_model(rows: list[dict], arm: str, y: Callable[[dict], bool]) -> dict:
    """Mixed-effects logistic `y ~ L` over R and `arm` rows (L = 1 for `arm`), zone
    random effect when >= 2 zones, chain random effect when a chain has > 1 row."""
    try:
        import pandas as pd
        from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
    except ImportError:
        return {"available": False, "reason": "statsmodels not installed"}
    data = [{"y": int(bool(y(r))), "L": int(r.get("cond") == arm), "zone": str(r.get("zone")),
             "chain": chain_id(r)} for r in rows if r.get("cond") in ("R", arm)]
    if len({d["y"] for d in data}) < 2:
        return {"available": False, "reason": "no variation in outcome"}
    if len({d["L"] for d in data}) < 2:
        return {"available": False, "reason": "only one arm present"}
    vc = {}
    if len({d["zone"] for d in data}) >= 2:
        vc["zone"] = "0 + C(zone)"
    if len({d["chain"] for d in data}) < len(data):
        vc["chain"] = "0 + C(chain)"
    if not vc:
        return {"available": False, "reason": "no random-effect levels"}
    try:
        model = BinomialBayesMixedGLM.from_formula("y ~ L", vc, pd.DataFrame(data))
        fit = model.fit_vb()
    except Exception as exc:  # noqa: BLE001 - report, never crash the tables
        return {"available": False, "reason": f"fit failed: {exc}"}
    coef = {name: {"mean": float(fit.fe_mean[i]), "sd": float(fit.fe_sd[i])}
            for i, name in enumerate(model.exog_names)}
    return {"available": True, "n": len(data), "coef": coef,
            "vc_log_sd": {name: float(fit.vcp_mean[i])
                          for i, name in enumerate(model.vcp_names)}}


# --- comparisons --------------------------------------------------------------------

def _pair_rate(rows: list[dict], arm: str, fn: Callable[[dict], bool]) -> dict:
    out = {}
    for key, a in (("R", "R"), ("arm", arm)):
        sel = [r for r in rows if r.get("cond") == a]
        out[key] = _rate(sum(bool(fn(r)) for r in sel), len(sel))
    return out


def _pair_dist(values: dict[str, list[float]], zones_of: dict[str, list[str]] | None = None
               ) -> dict:
    # missing values (usage not reported) are excluded and counted by _dist
    out = {"R": _dist(values["R"]), "arm": _dist(values["arm"])}
    u, p = mann_whitney_u(_present(values["arm"]), _present(values["R"]))
    out["mann_whitney"] = {"u": u, "p": p}
    if zones_of is not None:
        wins = losses = 0
        for z in sorted(set(zones_of["R"]) & set(zones_of["arm"])):
            rv = [v for v, zz in zip(values["R"], zones_of["R"]) if zz == z and v is not None]
            av = [v for v, zz in zip(values["arm"], zones_of["arm"]) if zz == z and v is not None]
            if rv and av:
                wins += median(av) < median(rv)
                losses += median(av) > median(rv)
        out.update(zones_arm_lower=wins, zones_arm_higher=losses,
                   sign_p=sign_test(wins, losses))
    return out


def _by_arm(rows: list[dict], arm: str, fn: Callable[[dict], float]) -> tuple[dict, dict]:
    vals = {k: [fn(r) for r in rows if r.get("cond") == a] for k, a in (("R", "R"), ("arm", arm))}
    zones = {k: [str(r.get("zone")) for r in rows if r.get("cond") == a]
             for k, a in (("R", "R"), ("arm", arm))}
    return vals, zones


def _dup_values(chains: list[dict], counted_keys: set) -> list[dict]:
    rows = []
    for c in chains:
        d = c.get("duplication") or {}
        if "T4" not in d or (chain_id(c), 4) not in counted_keys:
            continue
        t0 = d.get("T0")
        # RC: `start` is the untouched variant, T0 the agent's tree; a missing start is
        # missing (counted in `rc_start_missing`), never T0. Elsewhere start = T0.
        start = d.get("start") if c.get("cond") == "RC" else d.get("start", t0)
        rows.append({"cond": c.get("cond"), "zone": c.get("zone"),
                     "growth_T0_T4": None if t0 is None else
                     int(d["T4"].get("duplicated_lines", 0)) - int(t0.get("duplicated_lines", 0)),
                     "growth_start_T4": None if start is None else
                     int(d["T4"].get("duplicated_lines", 0))
                     - int(start.get("duplicated_lines", 0))})
    return rows


def _dup_by_step(chains: list[dict], arm: str, counted_keys: set) -> dict:
    out: dict[str, dict] = {}
    for key in ("start", "T0", "T1", "T2", "T3", "T4"):
        cell = {}
        for k, a in (("R", "R"), ("arm", arm)):
            sel = []
            for c in chains:
                if c.get("cond") != a:
                    continue
                d = (c.get("duplication") or {}).get(key)
                if d is None or (key not in ("start", "T0")
                                 and (chain_id(c), int(key[1:])) not in counted_keys):
                    continue
                sel.append(d)
            cell[k] = {"n": len(sel),
                       "clones_mean": _num(mean(int(d.get("clones", 0)) for d in sel))
                       if sel else None,
                       "dup_lines_mean": _num(mean(int(d.get("duplicated_lines", 0))
                                                   for d in sel)) if sel else None}
        if cell["R"]["n"] or cell["arm"]["n"]:
            out[key] = cell
    return out


def compare(steps: list[dict], chains: list[dict], totals: list[dict], arm: str,
            zones: tuple[str, ...], labels: dict[str, dict], idx: dict) -> dict:
    """One lever arm vs R over `zones`: T1-T4 counted steps only."""
    rows = [r for r in steps if r.get("cond") in ("R", arm) and r.get("zone") in zones
            and step_of(r) in STEPS]
    t2 = [r for r in rows if step_of(r) == 2]
    t2_static = [r for r in t2 if r.get("t2_reuses_logic") is not None]
    t2_judge = [r for r in t2 if label(r, labels, "t2_reuse") is not None]
    rule = [r for r in rows if step_of(r) in RULE_STEPS]
    later = [r for r in rows if step_of(r) >= 2]

    def helper_static(r): return r.get("t2_reuses_logic") == "helper"
    def helper_judge(r): return label(r, labels, "t2_reuse") == "helper"

    out: dict = {
        "zones": list(zones),
        "t2_reuse_judge": _pair_rate(t2_judge, arm, helper_judge),
        "t2_reuse_judge_model": lever_model(t2_judge, arm, helper_judge),
        "t2_reuse_static": _pair_rate(t2_static, arm, helper_static),
        "t2_reuse_static_model": lever_model(t2_static, arm, helper_static),
        "t2_reuse_static_unknown": {k: sum(1 for r in t2 if r.get("cond") == a
                                           and r.get("t2_reuses_logic") is None)
                                    for k, a in (("R", "R"), ("arm", arm))},
        "missed_copy": _pair_rate(rule, arm, missed_copy_preexisting),
        "missed_copy_model": lever_model(rule, arm, missed_copy_preexisting),
        "correct": _pair_rate(rows, arm, is_correct),
        "correct_model": lever_model(rows, arm, is_correct),
        "correct_by_step": {f"T{s}": _pair_rate([r for r in rows if step_of(r) == s], arm,
                                                is_correct) for s in STEPS},
        "one_place_judge": _pair_rate([r for r in rule if label(r, labels, "one_place")
                                       is not None], arm,
                                      lambda r: bool(label(r, labels, "one_place"))),
        "rule_sites_touched": _pair_dist(*_by_arm(
            [r for r in rule if r.get("rule_sites_touched") is not None], arm,
            lambda r: int(r["rule_sites_touched"]))),
    }
    split = {r_key: carried_split(r, idx) for r_key, r in
             ((step_key(r), r) for r in later)}
    out["carried"] = {
        "any": _pair_rate(later, arm, lambda r: carried(r) > 0),
        "any_model": lever_model(later, arm, lambda r: carried(r) > 0),
        "never_passed": _pair_rate(later, arm, lambda r: split[step_key(r)]["never_passed"] > 0),
        "regression": _pair_rate(later, arm, lambda r: split[step_key(r)]["regressions"] > 0),
        "chains_with_regression": {
            k: _rate(len({chain_id(r) for r in later if r.get("cond") == a
                          and split[step_key(r)]["regressions"] > 0}),
                     len({chain_id(r) for r in rows if r.get("cond") == a}))
            for k, a in (("R", "R"), ("arm", arm))},
        "by_step": {f"T{s}": _pair_rate([r for r in later if step_of(r) == s], arm,
                                        lambda r: carried(r) > 0) for s in STEPS[1:]},
    }
    out["efficiency"] = {name: _pair_dist(*_by_arm(rows, arm, fn))
                         for name, fn in EFFICIENCY.items()}
    out["efficiency_by_step"] = {
        f"T{s}": {name: _pair_dist(*_by_arm([r for r in rows if step_of(r) == s], arm,
                                             EFFICIENCY[name]))
                  for name in ("tokens", "turns", "wall_s")} for s in STEPS}
    tot = [t for t in totals if t["cond"] in ("R", arm) and t["zone"] in zones]
    out["chain_totals"] = {name: _pair_dist(*_by_arm(tot, arm, lambda t, n=name: t[n]))
                           for name in ("tokens_t1_t4", "tokens_all_steps",
                                        "wall_s_t1_t4", "wall_s_all_steps")}
    counted_keys = {(chain_id(r), step_of(r)) for r in rows}
    ch = [c for c in chains if c.get("cond") in ("R", arm) and c.get("zone") in zones]
    dv = _dup_values(ch, counted_keys)
    out["duplication"] = {
        "rc_start_missing": sum(1 for c in ch if c.get("cond") == "RC"
                                and "T4" in (c.get("duplication") or {})
                                and "start" not in (c.get("duplication") or {})
                                and (chain_id(c), 4) in counted_keys),
        "by_step": _dup_by_step(ch, arm, counted_keys),
        **{g: {"R": _dist([d[g] for d in dv if d["cond"] == "R" and d[g] is not None]),
               "arm": _dist([d[g] for d in dv if d["cond"] == arm and d[g] is not None])}
           for g in ("growth_T0_T4", "growth_start_T4")}}
    return out


# --- arm-specific tables ------------------------------------------------------------

def t0_table(t0_rows: list[dict], labels: dict[str, dict]) -> dict | None:
    if not t0_rows:
        return None
    counted = [r for r in t0_rows if is_counted(r)]
    reasons = [x for x in map(exclusion, t0_rows) if x is not None]

    def block(rows: list[dict]) -> dict:
        probe = [r for r in rows if r.get("probe_unchanged") is not None]
        inc = [r for r in rows if r.get("inconsistencies_unified") is not None
               and r.get("zone") not in NO_INCONSISTENCY_TESTS]
        comp = [float(v) for r in rows
                if (v := label(r, labels, "completeness")) is not None]
        iface = [float(v) for r in rows if (v := label(r, labels, "interface")) is not None]
        judged = [r for r in rows if label(r, labels, "completeness") is not None]
        # amendment 2026-10-12b item 8: a T0 whose probe changed or that unified an
        # inconsistency is scored like any other and flagged; exploratory value without them
        flagged = [r for r in judged if r.get("probe_unchanged") is False
                   or bool(r.get("inconsistencies_unified"))]
        return {
            "n": len(rows),
            "probe_unchanged": _rate(sum(bool(r["probe_unchanged"]) for r in probe), len(probe)),
            "inconsistencies_unified": _rate(sum(bool(r["inconsistencies_unified"])
                                                 for r in inc), len(inc))
            if any(r.get("zone") not in NO_INCONSISTENCY_TESTS for r in rows) else None,
            "correct": _rate(sum(is_correct(r) for r in rows), len(rows)),
            "completeness": _dist(comp),
            "completeness_ge_075": _rate(sum(v >= 0.75 for v in comp), len(comp)),
            **{f"completeness_{k}": _dist([float(v) for r in rows if (
                v := label(r, labels, f"completeness_{k}")) is not None])
               for k in ("lenient", "strict")},
            "completeness_flagged": {
                "probe_changed": sum(r.get("probe_unchanged") is False for r in judged),
                "inconsistency_unified": sum(bool(r.get("inconsistencies_unified"))
                                             for r in judged),
                "judged": len(judged)},
            "completeness_unflagged": _dist([float(label(r, labels, "completeness"))
                                             for r in judged if r not in flagged]),
            "interface": _dist(iface),
        }
    out = {"n": len(t0_rows), "excluded": {k: reasons.count(k) for k in sorted(set(reasons))},
           "status": {s: sum(1 for r in t0_rows if r.get("status") == s)
                      for s in sorted({str(r.get("status")) for r in t0_rows})},
           **{k: v for k, v in block(counted).items() if k != "n"},
           "evaluated": len(counted)}
    ids: dict[str, int] = {}
    for r in counted:
        for i in r.get("inconsistencies_unified") or []:
            ids[i] = ids.get(i, 0) + 1
    out["inconsistency_ids"] = dict(sorted(ids.items()))
    # amendment 2026-10-11d: an unfinished T0 eval (non-fatal `eval_error`) keeps the
    # checks that ran (their value is None when they did not); only status exclusions drop
    ran = [r for r in t0_rows if exclusion(r) in (None, "eval_error")]
    for name in ("typecheck_ok", "typecheck_full_ok", "lint_ok", "lint_root_ok",
                 "related_ok"):
        sel = [r for r in ran if r.get(name) is not None]
        out[name] = _rate(sum(bool(r[name]) for r in sel), len(sel))
    for name in ("tokens", "wall_s", "turns", "lines_changed"):
        out[name] = _dist([EFFICIENCY[name](r) for r in t0_rows
                           if r.get("status") not in ("setup_error", "harness_error")
                           and not is_infra(r.get("status"))])
    out["per_zone"] = {z: block([r for r in counted if r.get("zone") == z])
                       for z in sorted({str(r.get("zone")) for r in t0_rows})}
    return out


def behaviour_table(steps: list[dict]) -> dict:
    """Study-3 pilot blocking item 9 (descriptive): the zone's T0 inconsistency tests not
    superseded at the step (`inconsistencies_unified_step`) on every T1-T4 post tree, per
    arm, by step, beside H4 (RL steps where the ratchet fired) and the T2 static label. A
    step is *checked* when the field is a list (None: no test in scope at that step, or
    the check did not run)."""
    rows = [r for r in steps if step_of(r) in STEPS]
    arms = [a for a in ARMS if any(r.get("cond") == a for r in rows)]

    def checked(sel: list[dict]) -> list[dict]:
        return [r for r in sel if isinstance(r.get("inconsistencies_unified_step"), list)]

    def unified(r: dict) -> bool:
        return bool(r.get("inconsistencies_unified_step"))
    by_arm = {a: [r for r in rows if r.get("cond") == a] for a in arms}
    out: dict = {
        "unified": {a: _rate(sum(map(unified, checked(by_arm[a]))), len(checked(by_arm[a])))
                    for a in arms},
        "not_checked": {a: len(by_arm[a]) - len(checked(by_arm[a])) for a in arms},
        "by_step": {f"T{s}": {a: _rate(sum(map(unified, c := checked(
            [r for r in by_arm[a] if step_of(r) == s]))), len(c)) for a in arms}
            for s in STEPS},
        "ids": {a: {} for a in arms},
        "h4_fired": {}, "h4_success_unified": {},
        "t2_label": {a: {} for a in arms},
    }
    for a in arms:
        for r in checked(by_arm[a]):
            for i in r["inconsistencies_unified_step"]:
                out["ids"][a][i] = out["ids"][a].get(i, 0) + 1
        for lab in (*T2_REUSE, None):
            c = checked([r for r in by_arm[a] if step_of(r) == 2
                         and r.get("t2_reuses_logic") == lab])
            if c:
                out["t2_label"][a]["unknown" if lab is None else lab] = _rate(
                    sum(map(unified, c)), len(c))
    rl = by_arm.get("RL", [])
    for scope, zones in (("non_blind", NON_BLIND), ("all", ZONES)):
        c = checked([r for r in rl if r.get("zone") in zones and fired(r)])
        out["h4_fired"][scope] = _rate(sum(map(unified, c)), len(c))
        out["h4_success_unified"][scope] = sum(
            1 for r in c if unified(r) and final_fires(r) is False and not gamed(r))
    return out


def render_behaviour(b: dict) -> str:
    arms = list(b["unified"])
    head = "| | " + " | ".join(arms) + " |"
    sep = "|---" * (len(arms) + 1) + "|"
    lines = ["### Behaviour check outside T0 (descriptive)", "",
             "`inconsistencies_unified_step`: the zone's T0 inconsistency tests that no step "
             "statement up to this one supersedes (`tasks3/inconsistency-scope.json`: in "
             "practice Z3's three tests at every step; Z1's and Z2's are superseded from T1 "
             "on, Z4 has none) run on the step's post tree; a step is counted when the check "
             "ran. Rate = checked steps with at least one inconsistency unified.", "",
             head, sep,
             "| any unified, T1–T4 | " + " | ".join(b["unified"][a]["cell"] for a in arms) + " |",
             "| not checked | " + " | ".join(str(b["not_checked"][a]) for a in arms) + " |"]
    for st, row in b["by_step"].items():
        lines.append(f"| {st} | " + " | ".join(row[a]["cell"] for a in arms) + " |")
    lines += ["", "Unified ids: " + "; ".join(
        f"{a} " + (", ".join(f"{k} {v}" for k, v in b["ids"][a].items()) or "none")
        for a in arms) + ".", "",
        f"Beside H4: RL steps where the ratchet fired, checked, with an inconsistency unified: "
        f"non-blind Z1+Z3 † {b['h4_fired']['non_blind']['cell']}, all zones "
        f"{b['h4_fired']['all']['cell']}; of them counted as H4 successes (pass at end, no "
        f"gaming flag): {b['h4_success_unified']['non_blind']} (non-blind), "
        f"{b['h4_success_unified']['all']} (all).", "",
        "Beside the T2 static label (T2 steps checked, unified): " + "; ".join(
            f"{a} " + (", ".join(f"{lab} {c['cell']}" for lab, c in b["t2_label"][a].items())
                       or "–") for a in arms) + ".", ""]
    return "\n".join(lines)


def rl_table(steps: list[dict]) -> dict:
    rows = [r for r in steps if step_of(r) in STEPS]
    arms = [a for a in ARMS if any(r.get("cond") == a for r in rows)]

    def rate(a, fn, sel=None):
        sel = [r for r in rows if r.get("cond") == a] if sel is None else sel
        return _rate(sum(bool(fn(r)) for r in sel), len(sel))

    rl = [r for r in rows if r.get("cond") == "RL"]
    known = [r for r in rows if final_fires(r) is not None]
    out: dict = {
        "lint_runs": {a: _dist([int(r.get("lint_runs") or 0) for r in rows
                                if r.get("cond") == a]) for a in arms},
        "lint_runs_by_step": {f"T{s}": {a: _dist([int(r.get("lint_runs") or 0) for r in rows
                                                  if r.get("cond") == a and step_of(r) == s])
                                        for a in arms} for s in STEPS},
        "tripped": {a: rate(a, lambda r: int(r.get("ratchet_trips") or 0) > 0) for a in arms},
        "fired": {a: rate(a, fired) for a in arms},
        "final_fires": {a: rate(a, final_fires, [r for r in known if r.get("cond") == a])
                        for a in arms},
        "passed_at_end": {a: rate(a, lambda r: not final_fires(r),
                                  [r for r in known if r.get("cond") == a]) for a in arms},
        "ratchet_error": {a: sum(1 for r in rows if r.get("cond") == a
                                 and final_fires(r) is None) for a in arms},
        "gaming": {a: rate(a, gamed) for a in arms},
        "gaming_flags": {a: _flag_counts([r for r in rows if r.get("cond") == a])
                         for a in arms},
    }
    h4 = {}
    for scope, zones in (("non_blind", NON_BLIND), ("all", ZONES)):
        sel = [r for r in rl if r.get("zone") in zones and fired(r)
               and final_fires(r) is not None]
        h4[scope] = _rate(sum(1 for r in sel if not final_fires(r) and not gamed(r)), len(sel))
    h4["per_zone"] = {z: _rate(sum(1 for r in rl if r.get("zone") == z and fired(r)
                                   and final_fires(r) is False and not gamed(r)),
                               sum(1 for r in rl if r.get("zone") == z and fired(r)
                                   and final_fires(r) is not None)) for z in ZONES}
    h4["ratchet_error_fired"] = sum(1 for r in rl if fired(r) and final_fires(r) is None)
    # beside the registered H4: only steps where the agent *saw* the ratchet fire
    for scope, zones in (("non_blind", NON_BLIND), ("all", ZONES)):
        sel = [r for r in rl if r.get("zone") in zones and int(r.get("ratchet_trips") or 0) > 0
               and final_fires(r) is not None]
        h4[f"seen_{scope}"] = _rate(sum(1 for r in sel if not final_fires(r) and not gamed(r)),
                                    len(sel))
    out["h4"] = h4
    out["h4_decomposition"] = h4_decomposition(rl)
    out["fired_by_zone_step"] = {z: {f"T{s}": {a: rate(a, fired, [
        r for r in rows if r.get("cond") == a and r.get("zone") == z and step_of(r) == s])
        for a in arms} for s in STEPS} for z in ZONES}
    out["split"] = {a: {sp: _split_cell([r for r in rows if r.get("cond") == a
                                         and split_of(r) == sp]) for sp in RATCHET_SPLITS}
                    for a in arms}
    return out


def _flag_counts(rows: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        for k, v in (r.get("gaming_flags") or {}).items():
            if v:
                out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def _split_cell(rows: list[dict]) -> dict:
    return {"n": len(rows),
            "lint_runs": _dist([int(r.get("lint_runs") or 0) for r in rows]),
            **{name: _dist([EFFICIENCY[name](r) for r in rows])
               for name in ("tokens", "turns", "wall_s")}}


def rg_table(steps: list[dict]) -> dict:
    rows = [r for r in steps if step_of(r) in STEPS]
    arms = [a for a in ARMS if any(r.get("cond") == a for r in rows)]
    out = {"rule_text": rg_rule_text(),
           "rule_cited": {}, "reuse_talk": {}, "rule_cited_by_step": {}}
    for a in arms:
        sel = [r for r in rows if r.get("cond") == a]
        out["rule_cited"][a] = _rate(sum(bool(r.get("rule_cited")) for r in sel), len(sel))
        out["reuse_talk"][a] = _rate(sum(bool((r.get("rule_cited_detail") or {})
                                              .get("reuse_talk")) for r in sel), len(sel))
        out["rule_cited_by_step"][a] = {
            f"T{s}": _rate(sum(bool(r.get("rule_cited")) for r in sel if step_of(r) == s),
                           sum(1 for r in sel if step_of(r) == s)) for s in STEPS}
        # amendment 2026-10-12b, item 7: opened AGENTS.md with a tool call (either key)
        ex = [rg_check.agents_md_explicit_read(r.get("rule_cited_detail")) for r in sel]
        ex = [v for v in ex if v is not None]
        out.setdefault("explicit_read", {})[a] = _rate(sum(ex), len(ex))
    return out


def f_column(f_steps: list[dict], f_chains: list[dict], labels: dict[str, dict]) -> dict | None:
    """Study-2 F, descriptive (same measures, study 2's evaluator and T2 label)."""
    if not f_steps:
        return None
    counted = [r for r in f_steps if is_counted(r) and step_of(r) in STEPS]
    t2 = [r for r in counted if step_of(r) == 2 and r.get("t2_reuses_logic") is not None]
    t2j = [r for r in counted if step_of(r) == 2 and label(r, labels, "t2_reuse") is not None]
    rule = [r for r in counted if step_of(r) in RULE_STEPS]
    later = [r for r in counted if step_of(r) >= 2]
    tot = chain_totals(f_steps)
    keys = {(chain_id(r), step_of(r)) for r in counted}
    dv = _dup_values(f_chains, keys)
    return {
        "n": len(counted),
        "t2_reuse": _rate(sum(r["t2_reuses_logic"] == "helper" for r in t2), len(t2)),
        "t2_reuse_judge": _rate(sum(label(r, labels, "t2_reuse") == "helper" for r in t2j),
                                len(t2j)),
        "missed_copy": _rate(sum(missed_copy_preexisting(r) for r in rule), len(rule)),
        "correct": _rate(sum(is_correct(r) for r in counted), len(counted)),
        "carried_any": _rate(sum(carried(r) > 0 for r in later), len(later)),
        **{name: _dist([EFFICIENCY[name](r) for r in counted])
           for name in ("tokens", "turns", "wall_s", "lines_added")},
        "chain_tokens": _dist([t["tokens_t1_t4"] for t in tot]),
        "chain_wall_s": _dist([t["wall_s_t1_t4"] for t in tot]),
        "dup_growth": _dist([d["growth_T0_T4"] for d in dv if d["growth_T0_T4"] is not None]),
    }


# --- summary ------------------------------------------------------------------------

def _summarise_agent(all_steps: list[dict], chains: list[dict], labels: dict[str, dict],
                     f_steps: list[dict], f_chains: list[dict],
                     kappa: dict[str, float] | None = None,
                     calibration: dict | None = None) -> dict:
    counted = [r for r in all_steps if is_counted(r)]
    t14 = [r for r in counted if step_of(r) in STEPS]
    idx = chain_index(all_steps)
    totals = chain_totals(all_steps)
    arms = [a for a in LEVERS if any(r.get("cond") == a for r in all_steps)]
    comparisons = {a: {scope: compare(t14, chains, totals, a, SCOPES[scope], labels, idx)
                       for scope in (("all", "without_Z4", "non_blind") if a == "RL"
                                     else ("all", "without_Z4"))}
                   for a in arms}
    reasons = [(r, x) for r in all_steps if (x := exclusion(r)) is not None]
    eval_errors = [str(r.get("eval_error")) for r, x in reasons if x == "eval_error"]
    t2_both = [r for r in t14 if step_of(r) == 2 and r.get("t2_reuses_logic") is not None
               and label(r, labels, "t2_reuse") is not None]
    contaminated = [r for r in counted if r.get("contamination_flag")]
    present = [a for a in ARMS if any(r.get("cond") == a for r in all_steps)]
    return {
        "arms": present,
        "n_by_status": {a: {s: sum(1 for r in t14 if r.get("cond") == a
                                   and r.get("status") == s)
                            for s in sorted({str(r.get("status")) for r in t14
                                             if r.get("cond") == a})} for a in present},
        "excluded": {
            "total": len(reasons),
            "t1_t4": sum(1 for r, _ in reasons if step_of(r) in STEPS),
            "t0": sum(1 for r, _ in reasons if step_of(r) == 0),
            "by_reason": {k: [x for _, x in reasons].count(k)
                          for k in sorted({x for _, x in reasons})},
            "eval_errors": {k: eval_errors.count(k) for k in sorted(set(eval_errors))},
            "by_arm": {a: sum(1 for r, _ in reasons if r.get("cond") == a
                              and step_of(r) in STEPS) for a in present}},
        "contamination": [step_key(r) for r in contaminated],
        "labels_present": any(step_key(r) in labels for r in all_steps),
        "t2_label_agreement": {"both": len(t2_both), "agree": sum(
            1 for r in t2_both if r["t2_reuses_logic"] == label(r, labels, "t2_reuse"))},
        "t2_reuse_counts": {a: {k: sum(1 for r in t14 if r.get("cond") == a and step_of(r) == 2
                                       and r.get("t2_reuses_logic") == k)
                                for k in (*T2_REUSE, None)} for a in present},
        "comparisons": comparisons,
        "t0": t0_table([r for r in all_steps if step_of(r) == 0 and r.get("cond") == "RC"],
                       labels),
        "rl": rl_table(t14),
        "calibration": calibration_table(t14, calibration),
        "behaviour": behaviour_table(t14),
        "rg": rg_table(t14),
        "f": f_column(f_steps, f_chains, labels),
        "kappa": {k: (kappa or {}).get(k) for k in JUDGED},
    }


def summarise(steps: list[dict], chains: list[dict] | None = None, *,
              f_steps: list[dict] | None = None, f_chains: list[dict] | None = None,
              labels: dict[str, dict] | None = None,
              kappa: dict[str, float] | None = None,
              calibration: dict | None = None) -> dict:
    """``kappa``: inter-judge agreement per judged measure (:data:`JUDGED`); a judged
    row without one is printed "kappa pending" (kappa comes before any comparison)."""
    chains = chains or []
    f_steps, f_chains, labels = f_steps or [], f_chains or [], labels or {}
    out = {}
    for agent in _agents(steps, chains):
        out[agent] = _summarise_agent(
            [r for r in steps if r.get("agent") == agent],
            [c for c in chains if c.get("agent") == agent], labels,
            [r for r in f_steps if r.get("agent") == agent],
            [c for c in f_chains if c.get("agent") == agent], kappa, calibration)
    for agent, s in out.items():
        for k in ("t2_reuse_counts",):
            s[k] = {a: {("unknown" if kk is None else kk): v for kk, v in d.items()}
                    for a, d in s[k].items()}
    return out


# --- markdown -----------------------------------------------------------------------

def _kappa(s: dict, name: str) -> str:
    k = (s.get("kappa") or {}).get(name)
    return " (kappa pending)" if k is None else f" (kappa {float(k):.2f})"


def _model_cell(m: dict) -> str:
    if not m.get("available"):
        return f"– ({m['reason']})"
    co = m["coef"]["L"]
    return f"{co['mean']:.2f} (sd {co['sd']:.2f}), n = {m['n']}"


def _rows_by_arm(s: dict):
    for arm, scopes in s["comparisons"].items():
        for scope, c in scopes.items():
            yield arm, scope, c


def _scope(arm: str, scope: str) -> str:
    return SCOPE_LABEL[scope]


def _rate_table(s: dict, title: str, get: Callable[[dict], dict],
                model: Callable[[dict], dict] | None, note: str = "") -> list[str]:
    lines = [f"### {title}", ""] + ([note, ""] if note else [])
    lines += ["| arm | scope | R | arm |" + (" lever log-odds (mixed logistic) |"
                                           if model else ""),
              "|---|---|---|---|" + ("---|" if model else "")]
    for arm, scope, c in _rows_by_arm(s):
        g = get(c)
        lines.append(f"| {arm} | {_scope(arm, scope)} | {g['R']['cell']} | {g['arm']['cell']} |"
                     + (f" {_model_cell(model(c))} |" if model else ""))
    return lines + [""]


def _dist_table(s: dict, title: str, names: list[tuple[str, Callable[[dict], dict]]],
                note: str = "") -> list[str]:
    lines = [f"### {title}", ""] + ([note, ""] if note else [])
    lines += ["| measure | arm | scope | R | arm | Mann-Whitney p | zones arm lower / higher |",
              "|---|---|---|---|---|---|---|"]
    for name, get in names:
        for arm, scope, c in _rows_by_arm(s):
            d = get(c)
            sign = (f"{d['zones_arm_lower']} / {d['zones_arm_higher']} "
                    f"(sign p {_fmt_p(d['sign_p'])})" if "sign_p" in d else "–")
            lines.append(f"| {name} | {arm} | {_scope(arm, scope)} | {_fmt_dist(d['R'])} | "
                         f"{_fmt_dist(d['arm'])} | {_fmt_p(d['mann_whitney']['p'])} | {sign} |")
    return lines + [""]


def _render_agent(agent: str, s: dict) -> list[str]:
    ex = s["excluded"]
    lines = [f"## {agent}", "",
             "T1–T4 steps counted: " + ", ".join(
                 f"{a} {sum(s['n_by_status'][a].values())}" for a in s["arms"])
             + f"; excluded: {ex['total']} (T1–T4 {ex['t1_t4']}, T0 {ex['t0']}: "
             + (", ".join(f"{k} {v}" for k, v in ex["by_reason"].items()) or "none") + ")"
             + ("; eval errors: " + ", ".join(f"{k} {v}" for k, v in ex["eval_errors"].items())
                if ex["eval_errors"] else "") + ".", ""]
    if s["contamination"]:
        lines += [f"**Contamination flagged** (counted, read with care): "
                  f"{len(s['contamination'])} — " + ", ".join(s["contamination"][:20]), ""]
    if not s["comparisons"]:
        lines += ["No lever arm present: no comparisons.", ""]
    pending = "" if s["labels_present"] else " (judge labels pending: plan Task 7)"

    agr = s["t2_label_agreement"]
    lines += _rate_table(
        s, "T2 reuse (H2): the new consumer reuses a shared function" + _kappa(s, "t2_reuse"),
        lambda c: c["t2_reuse_judge"], lambda c: c["t2_reuse_judge_model"],
        f"Primary: the judge's label{pending}. Denominator: T2 steps with a label.")
    lines += _rate_table(
        s, "T2 reuse, static3 label (secondary)", lambda c: c["t2_reuse_static"],
        lambda c: c["t2_reuse_static_model"],
        "`t2_reuses_logic` (amendment 2026-10-11b; agent-made helpers count, so R's base is "
        f"not ~0 %). Static vs judge agreement: {agr['agree']}/{agr['both']}. Counts: "
        + "; ".join(f"{a} " + ", ".join(f"{k} {v}" for k, v in d.items())
                    for a, d in s["t2_reuse_counts"].items()) + ".")
    lines += _rate_table(
        s, "Missed copy on rule steps (T1, T3), registered (consumers listed at T1)",
        lambda c: c["missed_copy"], lambda c: c["missed_copy_model"],
        "Secondary (floor in R for Sonnet/Haiku; spec section 7).")
    lines += _rate_table(s, "Correct, T1–T4", lambda c: c["correct"],
                         lambda c: c["correct_model"], "T1–T4 only: RC's T0 has its own table.")
    lines += ["| arm | scope | step | R | arm |", "|---|---|---|---|---|"]
    for arm, scope, c in _rows_by_arm(s):
        for st, g in c["correct_by_step"].items():
            lines.append(f"| {arm} | {_scope(arm, scope)} | {st} | {g['R']['cell']} | "
                         f"{g['arm']['cell']} |")
    lines += [""]
    lines += _rate_table(s, "Rule change through one shared definition (T1, T3; judge)"
                         + _kappa(s, "one_place"),
                         lambda c: c["one_place_judge"], None, f"Judge label{pending}.")
    lines += _dist_table(s, "Rule sites touched (T1, T3; static, secondary)",
                         [("rule_sites_touched", lambda c: c["rule_sites_touched"])])
    lines += ["### Carried defects (T2–T4): never passed vs regressions", "",
              "| arm | scope | any R | any arm | never passed R | never passed arm | "
              "regression R | regression arm | chains with a regression R / arm | "
              "any: lever log-odds |", "|---" * 10 + "|"]
    for arm, scope, c in _rows_by_arm(s):
        k = c["carried"]
        lines.append(
            f"| {arm} | {_scope(arm, scope)} | {k['any']['R']['cell']} | {k['any']['arm']['cell']}"
            f" | {k['never_passed']['R']['cell']} | {k['never_passed']['arm']['cell']} | "
            f"{k['regression']['R']['cell']} | {k['regression']['arm']['cell']} | "
            f"{k['chains_with_regression']['R']['cell']} / "
            f"{k['chains_with_regression']['arm']['cell']} | {_model_cell(k['any_model'])} |")
    lines += [""]
    lines += _dist_table(s, "Efficiency per step (T1–T4 only)",
                         [(n, lambda c, n=n: c["efficiency"][n])
                          for n in ("tokens", "turns", "wall_s", "tool_calls", "lines_changed")],
                         "Input + output tokens (cached input apart). RC's T0 is not a step "
                         "here; see the chain totals.")
    lines += ["### Efficiency by step", "", "Median [IQR] (n) per step, R vs arm.", "",
              "| measure | arm | scope | step | R | arm | Mann-Whitney p |",
              "|---|---|---|---|---|---|---|"]
    for name in ("tokens", "turns", "wall_s"):
        for arm, scope, c in _rows_by_arm(s):
            for st, by in c["efficiency_by_step"].items():
                d = by[name]
                lines.append(f"| {name} | {arm} | {_scope(arm, scope)} | {st} | "
                             f"{_fmt_dist(d['R'])} | {_fmt_dist(d['arm'])} | "
                             f"{_fmt_p(d['mann_whitney']['p'])} |")
    lines += [""]
    lines += _dist_table(
        s, "Chain totals (H5: does T0 pay for itself?)",
        [(n, lambda c, n=n: c["chain_totals"][n])
         for n in ("tokens_t1_t4", "tokens_all_steps", "wall_s_t1_t4", "wall_s_all_steps")],
        "`*_t1_t4`: T1–T4 only; `*_all_steps`: every step, RC with T0. A chain is totalled "
        "only when all its steps ran (status not excluded).")
    lines += ["### Duplication (jscpd, zone files)", "",
              "T0 = the tree T1 starts from (RC: the agent's post-T0 tree); start = the "
              "untouched variant (RC only; elsewhere = T0). Mean clones / duplicated lines (n).",
              "", "| arm | scope | tree | R | arm |", "|---|---|---|---|---|"]
    missing = sum(c["duplication"]["rc_start_missing"] for a, sc, c in _rows_by_arm(s)
                  if a == "RC" and sc == "all")
    if missing:
        lines += [f"RC chains without `duplication.start` (left out of growth_start_T4, not "
                  f"read as T0): {missing}.", ""]
    for arm, scope, c in _rows_by_arm(s):
        for key, cell in c["duplication"]["by_step"].items():
            lines.append(f"| {arm} | {_scope(arm, scope)} | {key} | " + " | ".join(
                "–" if not cell[k]["n"] else
                f"{cell[k]['clones_mean']} / {cell[k]['dup_lines_mean']} ({cell[k]['n']})"
                for k in ("R", "arm")) + " |")
        for g in ("growth_T0_T4", "growth_start_T4"):
            d = c["duplication"][g]
            lines.append(f"| {arm} | {_scope(arm, scope)} | {g} | {_fmt_dist(d['R'])} | "
                         f"{_fmt_dist(d['arm'])} |")
    lines += [""]

    t0 = s["t0"]
    lines += ["### T0 (RC): the directed refactor (H3)", ""]
    if t0 is None:
        lines += ["No T0 results.", ""]
    else:
        lines += [f"{t0['n']} T0 steps, {t0['evaluated']} evaluated; status: "
                  + ", ".join(f"{k} {v}" for k, v in t0["status"].items())
                  + "; excluded: " + (", ".join(f"{k} {v}" for k, v in t0["excluded"].items())
                                      or "none")
                  + " (missing, not counted as changed). Registered thresholds (H3): median "
                  "completeness ≥ 0.75, probe unchanged in ≥ 75 % of RC chains.", "",
                  "| measure | value |", "|---|---|",
                  f"| completeness (judge){pending}{_kappa(s, 'completeness')} | "
                  f"{_fmt_dist(t0['completeness'])} |",
                  f"| completeness ≥ 0.75 | {t0['completeness_ge_075']['cell']} |",
                  f"| completeness, partial = 1 (lenient, descriptive) | "
                  f"{_fmt_dist(t0['completeness_lenient'])} |",
                  f"| completeness, partial = 0 (strict, descriptive) | "
                  f"{_fmt_dist(t0['completeness_strict'])} |",
                  f"| judged T0 flagged: probe changed / inconsistency unified | "
                  f"{t0['completeness_flagged']['probe_changed']} / "
                  f"{t0['completeness_flagged']['inconsistency_unified']} of "
                  f"{t0['completeness_flagged']['judged']} |",
                  f"| completeness over unflagged T0 (exploratory) | "
                  f"{_fmt_dist(t0['completeness_unflagged'])} |",
                  f"| probe unchanged (minus exclusions) | {t0['probe_unchanged']['cell']} |",
                  f"| any inconsistency unified (Z1–Z3; Z4 has no inconsistency tests) | "
                  f"{_cell(t0['inconsistencies_unified'])} |",
                  f"| correct (both clean) | {t0['correct']['cell']} |",
                  f"| interface 1–5 (judge){pending}{_kappa(s, 'interface')} | "
                  f"{_fmt_dist(t0['interface'])} |",
                  f"| typecheck (tsgo -b) ok | {t0['typecheck_ok']['cell']} |",
                  f"| typecheck, full (yarn typecheck) ok | {t0['typecheck_full_ok']['cell']} |",
                  f"| loot-core lint ok | {t0['lint_ok']['cell']} |",
                  f"| root lint ok | {t0['lint_root_ok']['cell']} |",
                  f"| related tests ok | {t0['related_ok']['cell']} |"]
        for name in ("tokens", "wall_s", "turns", "lines_changed"):
            lines.append(f"| {name} | {_fmt_dist(t0[name])} |")
        lines += ["", "Inconsistencies unified: " + (", ".join(
            f"{k} {v}" for k, v in t0["inconsistency_ids"].items()) or "none") + ".", "",
            "| zone | probe unchanged | inconsistency unified | correct | completeness |",
            "|---|---|---|---|---|"]
        for z, b in t0["per_zone"].items():
            lines.append(f"| {z} | {b['probe_unchanged']['cell']} | "
                         f"{_cell(b['inconsistencies_unified'])} | {b['correct']['cell']} | "
                         f"{_fmt_dist(b['completeness'])} |")
        lines += [""]

    rl = s["rl"]
    arms = list(rl["lint_runs"])
    head = "| | " + " | ".join(arms) + " |"
    sep = "|---" * (len(arms) + 1) + "|"
    lines += ["### RL: the ratchet (H4)", "", RATCHET_NOTE, "",
              "Other arms: the harness detector on their trees (counterfactual; no lint ran "
              "the ratchet there).", "", head, sep,
              "| lint runs per step | " + " | ".join(_fmt_dist(rl["lint_runs"][a])
                                                    for a in arms) + " |",
              "| saw a dup-check failure | " + " | ".join(rl["tripped"][a]["cell"]
                                                         for a in arms) + " |",
              "| fired (seen or on final tree) | " + " | ".join(rl["fired"][a]["cell"]
                                                               for a in arms) + " |",
              "| passes at end | " + " | ".join(rl["passed_at_end"][a]["cell"]
                                               for a in arms) + " |",
              "| any gaming flag | " + " | ".join(rl["gaming"][a]["cell"] for a in arms) + " |",
              "| ratchet not computed | " + " | ".join(str(rl["ratchet_error"][a])
                                                      for a in arms) + " |", ""]
    h4 = rl["h4"]
    lines += [f"**H4** (RL steps where the ratchet fired that end passing with no gaming "
              f"flag): non-blind Z1+Z3 † {h4['non_blind']['cell']}; all zones (descriptive) "
              f"{h4['all']['cell']}; per zone " + ", ".join(
                  f"{z} {c['cell']}" for z, c in h4["per_zone"].items())
              + f". Fired steps without a final ratchet result: {h4['ratchet_error_fired']}.",
              "", f"H4, seen only (beside the registered one: steps where the agent saw a "
              f"dup-check failure, `ratchet_trips` > 0): non-blind Z1+Z3 † "
              f"{h4['seen_non_blind']['cell']}; all zones {h4['seen_all']['cell']}.",
              "", *_render_h4_decomposition(rl["h4_decomposition"]),
              "", render_behaviour(s["behaviour"]),
              "", "Gaming flags: " + "; ".join(
                  f"{a} " + (", ".join(f"{k} {v}" for k, v in rl["gaming_flags"][a].items())
                             or "none") for a in arms) + ".", "",
              "Fired by zone and step (seen or on the final tree):", "",
              "| zone | step | " + " | ".join(arms) + " |", "|---" * (len(arms) + 2) + "|"]
    for z, by_step in rl["fired_by_zone_step"].items():
        zl = f"{z} (lint blind)" if z in LINT_BLIND else z
        for st, cell in by_step.items():
            lines.append(f"| {zl} | {st} | " + " | ".join(cell[a]["cell"] for a in arms) + " |")
    if s.get("calibration"):
        lines += ["", *_render_calibration(s["calibration"])]
    lines += ["", "Split by `ratchet_split` (amendment 2026-10-11b; descriptive, beside the "
              "primary comparison): n, lint runs, tokens, turns, wall s.", "",
              "| arm | split | n | lint runs | tokens | turns | wall_s |",
              "|---|---|---|---|---|---|---|"]
    for a in arms:
        for sp, cell in rl["split"][a].items():
            if not cell["n"] and sp == "unknown":
                continue
            lines.append(f"| {a} | {sp} | {cell['n']} | {_fmt_dist(cell['lint_runs'])} | "
                         f"{_fmt_dist(cell['tokens'])} | {_fmt_dist(cell['turns'])} | "
                         f"{_fmt_dist(cell['wall_s'])} |")
    lines += [""]

    lines += _render_rg(s["rg"])

    lines += _closeness(s)
    return lines


def _render_rg(rg: dict) -> list[str]:
    rarms = list(rg["rule_cited"])
    lines = ["### RG: the written rule", "", f"Rule (AGENTS.md, RG only): \"{rg['rule_text']}\"",
             "", "RG compliance is measured by behaviour only (spec amendment 2026-10-12b, "
             "item 7: the judge's T2 and one-place labels, the static T2 label; tables above). "
             "The rows below are descriptive, in every arm (R the baseline), and none is a "
             "manipulation check: `rule_cited`, the agent's own prose quotes the rule; "
             "`reuse talk`, any talk of extracting or reusing logic; "
             "`agents_md_explicit_read`, the agent opened AGENTS.md with a tool call (the file "
             "is already in its context, so this is expected to be rare; not a manipulation "
             "check).", "",
             "| | " + " | ".join(rarms) + " |", "|---" * (len(rarms) + 1) + "|",
             "| rule quoted | " + " | ".join(rg["rule_cited"][a]["cell"] for a in rarms) + " |",
             "| reuse talk | " + " | ".join(rg["reuse_talk"][a]["cell"] for a in rarms) + " |"]
    if rg.get("explicit_read"):
        lines.append("| opened AGENTS.md (`agents_md_explicit_read`) | " + " | ".join(
            rg["explicit_read"][a]["cell"] for a in rarms) + " |")
    for st in (f"T{k}" for k in STEPS):
        lines.append(f"| rule quoted {st} | " + " | ".join(
            rg["rule_cited_by_step"][a][st]["cell"] for a in rarms) + " |")
    return lines + [""]


def _render_h4_decomposition(dec: dict) -> list[str]:
    """Amendment 2026-10-12b, item 6: H4's fired RL steps by class."""
    periods = (("all_steps", "T1–T4"), ("T1", "T1"), ("T2_T4", "T2–T4"))
    cols = [(sc, p) for sc in ("non_blind", "all") for p, _ in periods]
    head = ("| class | " + " | ".join(f"{SCOPE_LABEL[sc]} {dict(periods)[p]}"
                                      for sc, p in cols) + " |")
    lines = ["H4 decomposition of fired RL steps (amendment 2026-10-12b, item 6; successes "
             "(a), (ab), (b), (u); failures (g), (c), (d0), (d1); (b) is read as evidence "
             "for the rival hypothesis, the lint dodged and no duplication removed, never "
             "as an H4 failure). T1 alone shares R's start tree.", "", head,
             "|---" * (len(cols) + 1) + "|",
             "| fired | " + " | ".join(str(dec[sc][p]["fired"]) for sc, p in cols) + " |"]
    for k in H4_CLASSES:
        if k == "seen_passing" and not any(dec[sc][p]["counts"][k] for sc, p in cols):
            continue
        lines.append(f"| {H4_CLASS_LABEL[k]} | "
                     + " | ".join(str(dec[sc][p]["counts"][k]) for sc, p in cols) + " |")
    lines += ["| H4 (successes / fired) | " + " | ".join(dec[sc][p]["h4"]["cell"]
                                                         for sc, p in cols) + " |",
              "| successes that unified an in-scope T0 inconsistency | "
              + " | ".join(str(dec[sc][p]["success_unified"]) for sc, p in cols) + " |", ""]
    return lines


def _render_calibration(cal: dict) -> list[str]:
    """Amendment 2026-10-12b, item 5: firing beside calibration (n = 24 per cell)."""
    arms = cal["arms"]
    lines = ["Ratchet firing vs calibration (amendment 2026-10-12b, item 5): calibration is "
             "study-2 R trees at min-tokens 35. Benchmarked cells: R, RG, RC (counterfactual "
             "final tree; RG and RC trees may already differ by treatment, so a departure "
             "there is drift *or* treatment) at T1–T4, and RL at T1. RL at T2–T4 is a "
             "treatment outcome (‡), never benchmarked. **off** = the cell's Wilson 95 % "
             "interval does not overlap calibration's: off calibration, read in the traces "
             "before any interpretation.", "",
             "| zone | step | calibration (R) | " + " | ".join(arms) + " |",
             "|---" * (len(arms) + 3) + "|"]
    for z, by_step in cal["cells"].items():
        for st, by_arm in by_step.items():
            row = []
            for a in arms:
                c = by_arm[a]
                txt = c["rate"]["cell"]
                if c["off"]:
                    txt += " **off**"
                elif not c["benchmarked"]:
                    txt += " ‡"
                row.append(txt)
            lines.append(f"| {z} | {st} | {cal['calibration'][z][st]['cell']} | "
                         + " | ".join(row) + " |")
    lines += ["", "Off calibration: " + (", ".join(f"{a} {z} {st}" for z, st, a in cal["off"])
                                         or "none") + "."]
    return lines


def _closeness(s: dict) -> list[str]:
    """One descriptive row per measure: each arm (all zones) and, if loaded, study-2 F."""
    arms = [a for a in ARMS if a in s["arms"]]
    f = s["f"]
    vals: dict[str, dict] = {}
    for a in arms:
        c = (s["comparisons"].get(a) or {}).get("all")
        if c is None and a == "R" and s["comparisons"]:
            c = next(iter(s["comparisons"].values()))["all"]
            side = "R"
        else:
            side = "arm"
        if c is None:
            continue
        vals[a] = {
            "T2 reuse (static)": c["t2_reuse_static"][side]["cell"],
            "missed copy (T1+T3)": c["missed_copy"][side]["cell"],
            "correct T1–T4": c["correct"][side]["cell"],
            "carried any (T2–T4)": c["carried"]["any"][side]["cell"],
            "tokens per step": _fmt_dist(c["efficiency"]["tokens"][side]),
            "chain tokens T1–T4": _fmt_dist(c["chain_totals"]["tokens_t1_t4"][side]),
            "chain tokens with T0": _fmt_dist(c["chain_totals"]["tokens_all_steps"][side]),
            "dup. lines T0→T4": _fmt_dist(c["duplication"]["growth_T0_T4"][side]),
        }
    cols = list(vals)
    if f is not None:
        vals["F (study 2)"] = {
            "T2 reuse (static)": f["t2_reuse"]["cell"] + " ‡",
            "missed copy (T1+T3)": f["missed_copy"]["cell"],
            "correct T1–T4": f["correct"]["cell"],
            "carried any (T2–T4)": f["carried_any"]["cell"],
            "tokens per step": _fmt_dist(f["tokens"]),
            "chain tokens T1–T4": _fmt_dist(f["chain_tokens"]),
            "chain tokens with T0": _fmt_dist(f["chain_tokens"]),
            "dup. lines T0→T4": _fmt_dist(f["dup_growth"]),
        }
        cols.append("F (study 2)")
    if not cols:
        return []
    measures = list(next(iter(vals.values())))
    lines = ["### Closeness to F (descriptive)", "",
             "All zones. F is study 2's F runs (ceiling, not a comparison: other sessions, "
             "study 2's evaluator).", "",
             "| measure | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    for m in measures:
        lines.append(f"| {m} | " + " | ".join(vals[c][m] for c in cols) + " |")
    lines += [""]
    if f is not None:
        lines += ["‡ F's T2 label is study 2's (a fixed list of F's helper names), not the "
                  "static3 label.", ""]
    return lines


def _cell(rate: dict | None) -> str:
    return "– (no inconsistency tests)" if rate is None else rate["cell"]


def render_markdown(summary: dict) -> str:
    lines = ["# Study 3 results tables", "",
             "Generated by `aa tables3` from `result.json` / `chain_result.json` files. Rates "
             "are `rate [Wilson 95% CI]`; distributions `median [IQR] (n)`; the lever effect "
             "is the `L` coefficient of a mixed-effects logistic (log-odds of the lever arm vs "
             "R; zone, and chain when repeated, random). Only evaluated steps are counted; "
             "`timeout` is not correct. Every per-step measure is over T1–T4 only (RC's T0 "
             "has its own table); chain totals are given T1–T4 and with T0. Each lever arm is "
             "compared with R over all zones and without Z4 (pre-declared weak); RL's "
             "confirmatory scope is non-blind Z1+Z3 (†).", ""]
    for agent, s in summary.items():
        lines += _render_agent(agent, s)
    lines += ["Differences are read with their intervals; nothing near p = 0.05 is read as an "
              "effect on its own.", ""]
    return "\n".join(lines)


def build(runs_dir: Path, out_dir: Path, *, f_runs: Path | None = None,
          labels: Path | None = None, kappa: Path | None = None,
          calibration: Path | None = CALIBRATION_FILE) -> dict:
    """Write `tables3.md` and `summary3.json` into `out_dir`; return the summary.
    ``kappa``: JSON {measure: kappa} for :data:`JUDGED` (absent: "kappa pending")."""
    summary = summarise(load_steps(runs_dir), load_chains(runs_dir),
                        f_steps=load_f_steps(f_runs), f_chains=load_f_chains(f_runs),
                        labels=load_labels(labels), kappa=load_kappa(kappa),
                        calibration=load_calibration(calibration))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tables3.md").write_text(render_markdown(summary))
    (out_dir / "summary3.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary
