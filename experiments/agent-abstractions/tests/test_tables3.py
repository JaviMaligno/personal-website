"""Study-3 tables (plan Task 6) on a synthetic runs3 tree and on focused rows.

Synthetic runs3, agent "claude", arms R/RG/RL/RC, zones Z1..Z4, chains 0/1, steps T1..T4
(RC also T0). Hand-counted expectations:

- T2 static label (`t2_reuses_logic`): R helper only in Z2/0 (1/8); RG helper in Z1, Z2
  (4/8); RL helper in Z1, Z3 (4/8; non-blind Z1+Z3 4/4); RC helper except Z4 (6/8;
  without Z4 6/6).
- Judge labels (labels.json): R/Z1/0 copy, RC/Z1/0 helper; nothing else judged.
- Registered missed copy: R chain 0 at T1 in every zone (preexisting 2/5) -> 4/16 on
  T1+T3; that step is incorrect. No other misses.
- RC T0: tokens 10000, wall 1000, never counted in T1-T4 metrics; Z1/0 T0 incorrect
  (an inconsistency unified), Z3/1 probe changed, Z2/1 eval_error container (missing).
- Tokens per T1-T4 step: R 1000, RG 1100, RL 1500, RC 800; wall 100.
  Chain totals: R 4000; RC 3200 (T1-T4) / 13200 (all steps).
- RL: lint_runs 3 per step. Ratchet fired: Z1 T1 both chains (trip, passes at end),
  Z3/0 T2 (trip, still fires at end), Z3/1 T2 (trip, passes, jscpd_ignore flag), Z4/0 T3
  (trip, passes; lint-blind zone). H4 over non-blind: 2/4.
- R: Z1 T1 counterfactual ratchet_kind touches_preexisting_only (both chains).
- RG: rule_cited on T1 (8 of 32 steps). One extra RG step (Z1/2/T1) has status infra.
- Duplication: T0 50 -> T4 80 lines in R/RG/RL; RC start 50, T0 (agent's tree) 20 -> T4 25.
"""
import json
from pathlib import Path

import pytest

from aa import tables3
from aa.cli import main

ARMS = ("R", "RG", "RL", "RC")
ZONES = ("Z1", "Z2", "Z3", "Z4")
TOKENS = {"R": 1000, "RG": 1100, "RL": 1500, "RC": 800}
T2_HELPER = {"R": {("Z2", 0)},
             "RG": {(z, c) for z in ("Z1", "Z2") for c in (0, 1)},
             "RL": {(z, c) for z in ("Z1", "Z3") for c in (0, 1)},
             "RC": {(z, c) for z in ("Z1", "Z2", "Z3") for c in (0, 1)}}


def _no_fire():
    return {"ratchet_final": {"fires": False, "n_clones": 0}, "ratchet_kind": None,
            "ratchet_split": "no_fire", "ratchet_trips": 0, "ratchet_trip_kinds": []}


def _step(arm, zone, chain, step):
    tok = TOKENS[arm]
    r = {"agent": "claude", "cond": arm, "zone": zone, "chain": chain, "step": step,
         "step_id": f"T{step}", "kind": {1: "rule", 2: "consumer", 3: "rule", 4: "build"}[step],
         "study": 3, "status": "ok", "eval_error": None, "correct": True,
         "consumers_passed": 5, "consumers_total": 5, "missed_copy": False,
         "consumers_preexisting_passed": 5, "consumers_preexisting_total": 5,
         "missed_copy_preexisting": False, "carried_defects": 0,
         "diff": {"added": 20, "removed": 2},
         "tokens": {"input": tok - 100, "output": 100, "cached_input": 3000},
         "turns": 10, "tool_calls": 20, "wall_s": 100,
         "lint_runs": 3 if arm == "RL" else 1, "gaming_flags": {},
         "rule_cited": arm == "RG" and step == 1,
         "rule_cited_detail": {"reuse_talk": arm in ("RG", "RC")},
         **_no_fire()}
    if arm == "R" and chain == 0 and step == 1:
        r.update(consumers_preexisting_passed=2, consumers_passed=2,
                 missed_copy_preexisting=True, missed_copy=True, correct=False)
    if step == 2:
        r["t2_reuses_logic"] = "helper" if (zone, chain) in T2_HELPER[arm] else "copy"
    if step in (1, 3):
        r["rule_sites_touched"] = 1 if arm == "RC" else 4
    if arm == "R" and zone == "Z1" and step == 1:
        r.update(ratchet_final={"fires": True, "n_clones": 1},
                 ratchet_kind="touches_preexisting_only",
                 ratchet_split="touches_preexisting_only")
    if arm == "RL":
        if zone == "Z1" and step == 1:
            r.update(ratchet_trips=1, ratchet_trip_kinds=["touches_preexisting_only"],
                     ratchet_split="touches_preexisting_only")
        if zone == "Z3" and step == 2:
            r.update(ratchet_trips=1, ratchet_trip_kinds=["adds_new_clone_side"],
                     ratchet_split="adds_new_clone_side")
            if chain == 0:
                r.update(ratchet_final={"fires": True, "n_clones": 1},
                         ratchet_kind="adds_new_clone_side")
            else:
                r["gaming_flags"] = {"jscpd_ignore": ["packages/loot-core/src/x.ts"]}
        if zone == "Z4" and chain == 0 and step == 3:
            r.update(ratchet_trips=1, ratchet_trip_kinds=["touches_preexisting_only"],
                     ratchet_split="touches_preexisting_only")
    return r


def _t0(zone, chain):
    r = {"agent": "claude", "cond": "RC", "zone": zone, "chain": chain, "step": 0,
         "step_id": "T0", "kind": "t0", "study": 3, "status": "ok", "eval_error": None,
         "correct": True, "probe_changed_cases": [], "probe_unchanged": True,
         "inconsistencies_unified": [], "typecheck_ok": True, "lint_ok": True,
         "typecheck_full_ok": True, "lint_root_ok": True,
         "related_ok": True, "diff": {"added": 200, "removed": 300},
         "tokens": {"input": 9000, "output": 1000, "cached_input": 50000},
         "turns": 80, "tool_calls": 120, "wall_s": 1000, "lint_runs": 2,
         "gaming_flags": {}, "rule_cited": False, **_no_fire()}
    if (zone, chain) == ("Z1", 0):
        r.update(correct=False, inconsistencies_unified=["setZero_hidden"])
    if (zone, chain) == ("Z3", 1):
        r.update(correct=False, probe_unchanged=False, probe_changed_cases=["c12", "c13"])
    if (zone, chain) == ("Z2", 1):
        # unfinished eval (amendment 2026-10-11d): typecheck / lint ran and are kept;
        # the root lint did not run
        r.update(eval_error="container", correct=False, probe_unchanged=None,
                 probe_changed_cases=None, inconsistencies_unified=None, lint_root_ok=None,
                 typecheck_full_ok=False)
    return r


def _write(root: Path, r: dict) -> None:
    d = root / r["agent"] / r["cond"] / r["zone"] / str(r["chain"]) / f"T{r['step']}"
    d.mkdir(parents=True)
    (d / "result.json").write_text(json.dumps(r))
    # an evaluator side file that must never be read as a step result
    (d / "eval").mkdir()
    (d / "eval" / "result.json").write_text("{}")


@pytest.fixture(scope="module")
def runs3(tmp_path_factory):
    root = tmp_path_factory.mktemp("t3") / "runs3"
    for arm in ARMS:
        for zone in ZONES:
            for chain in (0, 1):
                if arm == "RC":
                    _write(root, _t0(zone, chain))
                for step in (1, 2, 3, 4):
                    _write(root, _step(arm, zone, chain, step))
                if arm == "RC":
                    dup = {"start": {"clones": 4, "duplicated_lines": 50},
                           "T0": {"clones": 1, "duplicated_lines": 20},
                           "T4": {"clones": 2, "duplicated_lines": 25}}
                else:
                    dup = {"T0": {"clones": 4, "duplicated_lines": 50},
                           "T4": {"clones": 6, "duplicated_lines": 80}}
                (root / "claude" / arm / zone / str(chain) / "chain_result.json").write_text(
                    json.dumps({"duplication": dup,
                                "duplication_T0_tree": "agent_t0_post" if arm == "RC"
                                else "untouched_variant"}))
    _write(root, _step("RG", "Z1", 2, 1) | {"status": "infra"})
    return root


@pytest.fixture(scope="module")
def runs2_f(tmp_path_factory):
    """Study-2 F steps (and R steps, which must be ignored) for the F column."""
    root = tmp_path_factory.mktemp("t2") / "runs2"
    for cond in ("R", "F"):
        for zone in ("Z1", "Z2"):
            for step in (1, 2, 3, 4):
                r = _step("R", zone, 1, step) | {"cond": cond, "study": None}
                r["tokens"] = {"input": 500, "output": 100, "cached_input": 0}
                if step == 2:
                    r["t2_reuses_logic"] = "helper" if cond == "F" else "copy"
                d = root / "claude" / cond / zone / "1" / f"T{step}"
                d.mkdir(parents=True)
                (d / "result.json").write_text(json.dumps(r))
            (root / "claude" / cond / zone / "1" / "chain_result.json").write_text(json.dumps(
                {"duplication": {"T0": {"clones": 1, "duplicated_lines": 10},
                                 "T4": {"clones": 1, "duplicated_lines": 12}}}))
    return root


@pytest.fixture(scope="module")
def labels(tmp_path_factory):
    p = tmp_path_factory.mktemp("lab") / "labels.json"
    p.write_text(json.dumps({"claude/R/Z1/0/T2": {"t2_reuse": "copy"},
                             "claude/RC/Z1/0/T2": {"t2_reuse": "helper"},
                             "claude/RC/Z1/0/T0": {"completeness": 0.8, "interface": 4,
                                                   "completeness_lenient": 1.0,
                                                   "completeness_strict": 0.6},
                             "claude/RC/Z2/0/T0": {"completeness": 0.5, "interface": 3,
                                                   "completeness_lenient": 0.75,
                                                   "completeness_strict": 0.25}}))
    return p


@pytest.fixture(scope="module")
def summary(runs3, runs2_f, labels):
    return tables3.summarise(tables3.load_steps(runs3), tables3.load_chains(runs3),
                             f_steps=tables3.load_f_steps(runs2_f),
                             f_chains=tables3.load_f_chains(runs2_f),
                             labels=tables3.load_labels(labels))["claude"]


# --- loading -----------------------------------------------------------------------

def test_load_steps_reads_only_step_results(runs3):
    steps = tables3.load_steps(runs3)
    assert len(steps) == 4 * 4 * 2 * 4 + 8 + 1          # T1-T4 + RC T0 + the infra step
    assert all(r for r in steps)                         # eval/result.json ({}) not read


# --- T2 reuse (H2) -------------------------------------------------------------------

def test_t2_reuse_static_per_arm_and_scope(summary):
    c = summary["comparisons"]
    assert (c["RG"]["all"]["t2_reuse_static"]["R"]["k"],
            c["RG"]["all"]["t2_reuse_static"]["R"]["n"]) == (1, 8)
    assert c["RG"]["all"]["t2_reuse_static"]["arm"]["k"] == 4
    assert c["RL"]["all"]["t2_reuse_static"]["arm"]["k"] == 4
    nb = c["RL"]["non_blind"]["t2_reuse_static"]
    assert (nb["arm"]["k"], nb["arm"]["n"]) == (4, 4)
    assert (nb["R"]["k"], nb["R"]["n"]) == (0, 4)
    assert (c["RC"]["without_Z4"]["t2_reuse_static"]["arm"]["k"],
            c["RC"]["without_Z4"]["t2_reuse_static"]["arm"]["n"]) == (6, 6)
    assert "non_blind" not in c["RG"] and "non_blind" not in c["RC"]
    lo, hi = c["RC"]["all"]["t2_reuse_static"]["arm"]["ci"]
    assert lo < 0.75 < hi


def test_t2_reuse_judge_is_primary_when_labelled(summary):
    j = summary["comparisons"]["RC"]["all"]["t2_reuse_judge"]
    assert (j["R"]["k"], j["R"]["n"]) == (0, 1)
    assert (j["arm"]["k"], j["arm"]["n"]) == (1, 1)
    agr = summary["t2_label_agreement"]
    assert agr == {"both": 2, "agree": 2}


def test_lever_model_fits_and_is_positive(summary):
    m = summary["comparisons"]["RC"]["all"]["t2_reuse_static_model"]
    assert m["available"], m
    assert m["coef"]["L"]["mean"] > 0
    assert "zone" in m["vc_log_sd"]


def test_lever_model_unavailable_without_variation():
    rows = [{"cond": a, "zone": "Z1", "chain": i, "step": 2, "t2_reuses_logic": "copy"}
            for a in ("R", "RG") for i in range(3)]
    m = tables3.lever_model(rows, "RG", lambda r: r["t2_reuses_logic"] == "helper")
    assert m == {"available": False, "reason": "no variation in outcome"}


# --- secondary measures ------------------------------------------------------------

def test_missed_copy_and_correct(summary):
    c = summary["comparisons"]["RG"]["all"]
    assert (c["missed_copy"]["R"]["k"], c["missed_copy"]["R"]["n"]) == (4, 16)
    assert c["missed_copy"]["arm"]["k"] == 0
    assert (c["correct"]["R"]["k"], c["correct"]["R"]["n"]) == (28, 32)
    assert c["correct_by_step"]["T1"]["R"]["k"] == 4
    assert (c["correct"]["arm"]["k"], c["correct"]["arm"]["n"]) == (32, 32)  # infra out
    assert summary["comparisons"]["RG"]["without_Z4"]["missed_copy"]["R"]["n"] == 12


def test_excluded_steps_reported(summary):
    ex = summary["excluded"]
    assert ex["by_arm"]["RG"] == 1 and ex["by_reason"] == {"eval_error": 1, "infra": 1}
    # the T0 eval error is reported under T0, apart from T1-T4
    assert ex["t0"] == 1 and ex["t1_t4"] == 1


# --- Review Focus 3: T1-T4 metrics exclude T0, totals include it ----------------------

def test_t1_t4_metrics_exclude_t0_and_totals_include_it(summary):
    rc = summary["comparisons"]["RC"]["all"]
    # T0 is incorrect in two chains and costs 10000 tokens: none of it in step metrics
    assert (rc["correct"]["arm"]["k"], rc["correct"]["arm"]["n"]) == (32, 32)
    assert rc["efficiency"]["tokens"]["arm"]["median"] == 800
    assert rc["efficiency"]["tokens"]["arm"]["n"] == 32
    assert rc["efficiency"]["wall_s"]["arm"]["iqr"] == [100, 100]
    assert "T0" not in rc["correct_by_step"]
    tot = rc["chain_totals"]
    assert tot["tokens_t1_t4"]["arm"]["median"] == 3200
    assert tot["tokens_all_steps"]["arm"]["median"] == 13200
    assert tot["wall_s_all_steps"]["arm"]["median"] == 1400
    assert tot["tokens_all_steps"]["R"]["median"] == 4000      # R has no T0
    assert tot["tokens_t1_t4"]["R"]["median"] == 4000


def test_rc_chain_without_t0_result_has_no_total():
    rows = [{"agent": "claude", "cond": "RC", "zone": "Z1", "chain": 0, "step": k,
             "status": "ok", "tokens": {"input": 1, "output": 0}, "wall_s": 1}
            for k in (1, 2, 3, 4)]
    tot = tables3.chain_totals(rows)
    assert tot == []                        # the chain's T0 is missing: not totalled
    tot = tables3.chain_totals(rows + [rows[0] | {"step": 0, "tokens": {"input": 5}}])
    assert tot[0]["tokens_all_steps"] == 9 and tot[0]["tokens_t1_t4"] == 4


def test_efficiency_mann_whitney_and_sign(summary):
    e = summary["comparisons"]["RL"]["all"]["efficiency"]["tokens"]
    assert e["R"]["median"] == 1000 and e["arm"]["median"] == 1500
    assert e["mann_whitney"]["p"] < 0.001
    assert (e["zones_arm_lower"], e["zones_arm_higher"]) == (0, 4)


def test_duplication_growth(summary):
    d = summary["comparisons"]["RC"]["all"]["duplication"]
    assert d["growth_T0_T4"]["R"]["median"] == 30
    assert d["growth_T0_T4"]["arm"]["median"] == 5
    assert d["growth_start_T4"]["arm"]["median"] == -25
    assert d["growth_start_T4"]["R"]["median"] == 30
    assert d["by_step"]["T0"]["arm"]["dup_lines_mean"] == 20


def test_carried_split_never_passed_vs_regression():
    def step(k, status, correct=True):
        return {"agent": "claude", "cond": "R", "zone": "Z1", "chain": 0, "step": k,
                "step_id": f"T{k}", "status": "ok", "eval_error": None, "correct": correct,
                "test_status": status}
    rows = [step(1, {"T1": {"a": True, "b": False}}, correct=False),
            step(2, {"T2": {"c": True}, "T1": {"a": False, "b": False}}, correct=False),
            step(3, {"T3": {"d": True}, "T1": {"a": True, "b": True}, "T2": {"c": True}})]
    idx = tables3.chain_index(rows)
    assert tables3.carried_split(rows[1], idx) == {"regressions": 1, "never_passed": 1,
                                                   "unknown": 0}
    assert tables3.carried_split(rows[2], idx) == {"regressions": 0, "never_passed": 0,
                                                   "unknown": 0}
    # no test_status: the carried count is unknown
    assert tables3.carried_split({"carried_defects": 2}, {}) == {
        "regressions": 0, "never_passed": 0, "unknown": 2}


# --- RL, RG, T0, F ------------------------------------------------------------------

def test_rl_table_h4_over_non_blind(summary):
    rl = summary["rl"]
    h4 = rl["h4"]["non_blind"]
    assert (h4["k"], h4["n"]) == (2, 4)
    assert (rl["h4"]["all"]["k"], rl["h4"]["all"]["n"]) == (3, 5)
    assert rl["fired"]["RL"]["k"] == 5 and rl["passed_at_end"]["RL"]["k"] == 31
    assert rl["gaming"]["RL"]["k"] == 1
    assert rl["gaming_flags"]["RL"] == {"jscpd_ignore": 1}
    assert rl["lint_runs"]["RL"]["median"] == 3
    # counterfactual: the ratchet would fire on R's Z1 T1
    assert rl["final_fires"]["R"]["k"] == 2
    sp = rl["split"]
    assert sp["RL"]["touches_preexisting_only"]["n"] == 3
    assert sp["RL"]["adds_new_clone_side"]["n"] == 2
    assert sp["R"]["touches_preexisting_only"]["n"] == 2
    assert sp["RL"]["no_fire"]["tokens"]["median"] == 1500
    assert sp["RL"]["modified_into_clone"]["n"] == 0


def test_rg_rule_cited(summary):
    rg = summary["rg"]
    assert (rg["rule_cited"]["RG"]["k"], rg["rule_cited"]["RG"]["n"]) == (8, 32)
    assert rg["rule_cited"]["R"]["k"] == 0
    assert rg["reuse_talk"]["RC"]["k"] == 32
    assert "Do not copy logic" in rg["rule_text"]


def test_t0_table(summary):
    t0 = summary["t0"]
    assert t0["n"] == 8
    assert (t0["probe_unchanged"]["k"], t0["probe_unchanged"]["n"]) == (6, 7)
    # pooled over Z1-Z3 only (Z4 has no inconsistency tests): Z1 2, Z2 1 counted, Z3 2
    assert (t0["inconsistencies_unified"]["k"], t0["inconsistencies_unified"]["n"]) == (1, 5)
    assert t0["per_zone"]["Z4"]["inconsistencies_unified"] is None
    assert t0["inconsistency_ids"] == {"setZero_hidden": 1}
    assert (t0["correct"]["k"], t0["correct"]["n"]) == (5, 7)
    assert t0["excluded"] == {"eval_error": 1}
    assert t0["completeness"]["median"] == pytest.approx(0.65)
    assert t0["completeness"]["n"] == 2
    # amendment 2026-10-12b item 8: sensitivity (partial = 1 / 0) and flagged T0s
    assert t0["completeness_lenient"]["median"] == pytest.approx(0.875)
    assert t0["completeness_strict"]["median"] == pytest.approx(0.425)
    assert t0["completeness_flagged"] == {"probe_changed": 0, "inconsistency_unified": 1,
                                          "judged": 2}
    assert t0["completeness_unflagged"]["n"] == 1          # Z1/0 unified an inconsistency
    assert t0["completeness_unflagged"]["median"] == pytest.approx(0.5)
    assert t0["interface"]["n"] == 2
    assert t0["tokens"]["median"] == 10000
    assert t0["per_zone"]["Z3"]["probe_unchanged"]["k"] == 1
    assert t0["per_zone"]["Z2"]["probe_unchanged"]["n"] == 1


def test_f_column_from_study2(summary):
    f = summary["f"]
    assert (f["t2_reuse"]["k"], f["t2_reuse"]["n"]) == (2, 2)
    assert f["correct"]["n"] == 8                   # only F steps, R of study 2 ignored
    assert f["tokens"]["median"] == 600
    assert f["chain_tokens"]["median"] == 2400
    assert f["dup_growth"]["median"] == 2


def test_no_f_runs_no_f_column(runs3):
    s = tables3.summarise(tables3.load_steps(runs3), tables3.load_chains(runs3))["claude"]
    assert s["f"] is None
    md = tables3.render_markdown({"claude": s})
    assert "F (study 2)" not in md


# --- markdown and CLI ---------------------------------------------------------------

def test_markdown_sections_and_footnotes(summary):
    md = tables3.render_markdown({"claude": summary})
    for head in ("## claude", "### T2 reuse", "### Missed copy", "### Correct",
                 "### Carried defects", "### Efficiency", "### Chain totals",
                 "### Duplication", "### T0 (RC)", "### RL: the ratchet",
                 "### RG: the written rule", "### Closeness to F"):
        assert head in md, head
    assert "min-tokens 35" in md and "deviation" in md
    assert "Z2, Z4" in md                               # lint-blind zones named
    assert "| RL | non-blind Z1+Z3 † |" in md
    assert "| RC | without Z4 |" in md
    assert "T1–T4 only" in md and "with T0" in md


def test_cli_writes_tables3(runs3, runs2_f, labels, tmp_path, capsys):
    out = tmp_path / "out3"
    assert main(["tables3", "--runs", str(runs3), "--out", str(out),
                 "--f-runs", str(runs2_f), "--labels", str(labels)]) == 0
    md = (out / "tables3.md").read_text()
    assert "## claude" in md
    data = json.loads((out / "summary3.json").read_text())
    assert data["claude"]["t0"]["n"] == 8
    assert data["claude"]["f"]["t2_reuse"]["k"] == 2


def test_cli_without_labels_or_f(runs3, tmp_path):
    out = tmp_path / "out3"
    assert main(["tables3", "--runs", str(runs3), "--out", str(out),
                 "--f-runs", str(tmp_path / "missing")]) == 0
    md = (out / "tables3.md").read_text()
    assert "judge labels pending" in md


# --- pre-pilot review fixes (2026-10-11) ---------------------------------------------

def test_t0_checks_keep_unfinished_evals(summary):
    """Amendment 2026-10-11d: checks that ran in an unfinished T0 eval are kept."""
    t0 = summary["t0"]
    assert (t0["typecheck_ok"]["k"], t0["typecheck_ok"]["n"]) == (8, 8)
    assert (t0["typecheck_full_ok"]["k"], t0["typecheck_full_ok"]["n"]) == (7, 8)
    assert (t0["lint_root_ok"]["k"], t0["lint_root_ok"]["n"]) == (7, 7)   # None: not run
    assert t0["lint_ok"]["n"] == 8 and t0["related_ok"]["n"] == 8
    md = tables3.render_markdown({"claude": summary})
    assert "| typecheck, full (yarn typecheck) ok |" in md and "| root lint ok |" in md
    assert "| Z4 | " in md and "no inconsistency tests" in md


def test_t0_checks_drop_fatal_exclusions():
    rows = [{"cond": "RC", "zone": "Z1", "chain": 0, "step": 0, "status": s,
             "eval_error": None, "typecheck_ok": True}
            for s in ("ok", "setup_error", "harness_error", "infra")]
    t0 = tables3.t0_table(rows, {})
    assert (t0["typecheck_ok"]["k"], t0["typecheck_ok"]["n"]) == (1, 1)


def test_rc_chain_without_duplication_start_is_missing_not_t0():
    chains = [{"agent": "claude", "cond": "RC", "zone": "Z1", "chain": 0,
               "duplication": {"T0": {"duplicated_lines": 20}, "T4": {"duplicated_lines": 25}}},
              {"agent": "claude", "cond": "R", "zone": "Z1", "chain": 0,
               "duplication": {"T0": {"duplicated_lines": 50}, "T4": {"duplicated_lines": 80}}}]
    keys = {(tables3.chain_id(c), 4) for c in chains}
    dv = tables3._dup_values(chains, keys)
    rc = next(d for d in dv if d["cond"] == "RC")
    assert rc["growth_start_T4"] is None and rc["growth_T0_T4"] == 5
    assert next(d for d in dv if d["cond"] == "R")["growth_start_T4"] == 30   # R: start = T0
    steps = [{"agent": "claude", "cond": a, "zone": "Z1", "chain": 0, "step": 4,
              "status": "ok", "eval_error": None} for a in ("R", "RC")]
    c = tables3.compare(steps, chains, [], "RC", ("Z1",), {}, {})
    assert c["duplication"]["rc_start_missing"] == 1
    assert c["duplication"]["growth_start_T4"]["arm"]["n"] == 0


def test_efficiency_by_step(summary):
    e = summary["comparisons"]["RL"]["all"]["efficiency_by_step"]
    assert set(e) == {"T1", "T2", "T3", "T4"}
    assert e["T2"]["tokens"]["arm"]["median"] == 1500 and e["T2"]["tokens"]["arm"]["n"] == 8
    assert e["T1"]["tokens"]["R"]["median"] == 1000
    md = tables3.render_markdown({"claude": summary})
    assert "### Efficiency by step" in md


def test_h4_seen_only_beside_registered():
    def rl(zone, trips, fires, flags=None):
        return {"cond": "RL", "zone": zone, "chain": 0, "step": 2, "ratchet_trips": trips,
                "ratchet_final": {"fires": fires}, "gaming_flags": flags or {}}
    rows = [rl("Z1", 1, False), rl("Z1", 0, True), rl("Z3", 2, False, {"x": ["a"]}),
            rl("Z3", 0, False)]
    h4 = tables3.rl_table(rows)["h4"]
    # registered: fired = seen or on the final tree -> 3 steps, 1 passes ungamed
    assert (h4["non_blind"]["k"], h4["non_blind"]["n"]) == (1, 3)
    # seen only: the two tripped steps
    assert (h4["seen_non_blind"]["k"], h4["seen_non_blind"]["n"]) == (1, 2)
    assert (h4["seen_all"]["k"], h4["seen_all"]["n"]) == (1, 2)


def test_rl_and_rg_tables_exclude_t0():
    base = {"agent": "claude", "zone": "Z1", "chain": 0, "status": "ok", "eval_error": None,
            "lint_runs": 1, "ratchet_trips": 0, "ratchet_final": {"fires": False},
            "gaming_flags": {}, "rule_cited": False}
    rows = [base | {"cond": "RC", "step": k} for k in (1, 2, 3, 4)]
    t0 = base | {"cond": "RC", "step": 0, "lint_runs": 9, "ratchet_trips": 3,
                 "ratchet_final": {"fires": True}, "gaming_flags": {"x": ["a"]},
                 "rule_cited": True}
    rl, rl0 = tables3.rl_table(rows), tables3.rl_table(rows + [t0])
    assert rl0 == rl
    assert rl0["fired"]["RC"]["n"] == 4 and rl0["lint_runs"]["RC"]["median"] == 1
    rg, rg0 = tables3.rg_table(rows), tables3.rg_table(rows + [t0])
    assert rg0 == rg and rg0["rule_cited"]["RC"]["k"] == 0


def test_kappa_pending_until_supplied(runs3, labels):
    steps, chains = tables3.load_steps(runs3), tables3.load_chains(runs3)
    lab = tables3.load_labels(labels)
    md = tables3.render_markdown(tables3.summarise(steps, chains, labels=lab))
    assert md.count("kappa pending") >= 4      # T2 reuse, one place, completeness, interface
    md = tables3.render_markdown(tables3.summarise(
        steps, chains, labels=lab,
        kappa={"t2_reuse": 0.72, "one_place": 0.6, "completeness": 0.81, "interface": 0.55}))
    assert "kappa pending" not in md
    assert "kappa 0.72" in md and "kappa 0.81" in md


def test_cli_tables3_kappa(runs3, labels, tmp_path):
    kp = tmp_path / "kappa.json"
    kp.write_text(json.dumps({"t2_reuse": 0.7}))
    out = tmp_path / "o"
    assert main(["tables3", "--runs", str(runs3), "--out", str(out), "--labels", str(labels),
                 "--f-runs", str(tmp_path / "none"), "--kappa", str(kp)]) == 0
    md = (out / "tables3.md").read_text()
    assert "kappa 0.70" in md and "kappa pending" in md       # the others still pending
