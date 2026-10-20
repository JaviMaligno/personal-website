import json
from pathlib import Path

import pytest

from aa import tables2
from aa.cli import main

# Synthetic study-2 runs, agent "claude", zones Z1/Z2, chains 0/1, steps T1..T4, R and F.
# Hand-counted expectations:
#   R: chain 0 misses a copy on every rule step (2/5 consumers) -> missed 4/8 on T1+T3;
#      chain 0 carries 1 defect at T2..T4 -> carried any 2/4 per step;
#      tokens 2000 per step except T4 = 4000 -> T4/T1 = 2.0; lines added 40.
#   F: no `missed_copy` field (derived from consumers): Z1 chain 1 T3 = 1/3 -> missed;
#      Z2 chain 1 T1 = 0/3 -> incorrect, NOT a missed copy -> missed 1/8;
#      Z1 chain 0 T2 timed out with correct=true -> not correct; tokens 1000, lines 10.
#   One extra R step with status infra -> excluded, never counted.
#   Duplication: R T0 100 -> T4 160 lines; F 20 -> 20.


def _step(cond, zone, chain, step):
    r = {"agent": "claude", "cond": cond, "zone": zone, "chain": chain, "step": step,
         "status": "ok", "correct": True, "consumers_total": 5 if cond == "R" else 3,
         "carried_defects": 0, "diff": {"added": 40 if cond == "R" else 10, "removed": 2},
         "tokens": {"input": 1800 if cond == "R" else 900,
                    "output": 200 if cond == "R" else 100, "cached_input": 5000},
         "turns": 10, "tool_calls": 20, "wall_s": 300}
    r["consumers_passed"] = r["consumers_total"]
    if cond == "R":
        r["missed_copy"] = False
        if chain == 0 and step in (1, 3):
            r.update(consumers_passed=2, missed_copy=True, correct=False)
        if chain == 0 and step >= 2:
            r["carried_defects"] = ["T1::consumer-3"]
        if step == 4:
            r["tokens"] = {"input": 3600, "output": 400, "cached_input": 9000}
    else:
        if (zone, chain, step) == ("Z1", 1, 3):
            r.update(consumers_passed=1, correct=False)
        if (zone, chain, step) == ("Z2", 1, 1):
            r.update(consumers_passed=0, correct=False)
        if (zone, chain, step) == ("Z1", 0, 2):
            r["status"] = "timeout"
    if step == 2:
        r["t2_reuses_logic"] = "helper" if cond == "F" else "copy"
    return r


def _write(root: Path, r: dict) -> None:
    d = root / r["agent"] / r["cond"] / r["zone"] / str(r["chain"]) / f"T{r['step']}"
    d.mkdir(parents=True)
    (d / "result.json").write_text(json.dumps(r))


@pytest.fixture
def runs(tmp_path):
    root = tmp_path / "runs2"
    for cond in ("R", "F"):
        for zone in ("Z1", "Z2"):
            for chain in (0, 1):
                for step in (1, 2, 3, 4):
                    _write(root, _step(cond, zone, chain, step))
                dup = ({"T0": {"clones": 5, "duplicated_lines": 100},
                        "T4": {"clones": 8, "duplicated_lines": 160}} if cond == "R" else
                       {"T0": {"clones": 1, "duplicated_lines": 20},
                        "T4": {"clones": 1, "duplicated_lines": 20}})
                (root / "claude" / cond / zone / str(chain) / "chain_result.json"
                 ).write_text(json.dumps({"duplication": dup}))
    infra = _step("R", "Z1", 2, 1) | {"status": "infra"}
    _write(root, infra)
    return root


@pytest.fixture
def summary(runs):
    return tables2.summarise(tables2.load_steps(runs), tables2.load_chains(runs))["claude"]


def test_missed_copy_rates_and_wilson(summary):
    m = summary["missed_copy"]
    assert (m["R"]["k"], m["R"]["n"]) == (4, 8)
    assert (m["F"]["k"], m["F"]["n"]) == (1, 8)
    lo, hi = m["R"]["ci"]
    assert lo < 0.5 < hi
    assert m["R"]["cell"].startswith("50% [")
    assert summary["missed_copy_by_step"]["T3"]["F"]["k"] == 1
    assert summary["missed_copy_by_step"]["T1"]["F"]["k"] == 0


def test_zero_consumers_is_incorrect_not_missed():
    r = {"consumers_passed": 0, "consumers_total": 3}
    assert not tables2.missed_copy(r)
    assert tables2.missed_copy({"consumers_passed": 2, "consumers_total": 3})
    assert not tables2.missed_copy({"consumers_passed": 3, "consumers_total": 3})
    # The evaluator's own field wins when present.
    assert tables2.missed_copy({"missed_copy": True, "consumers_passed": 0,
                                "consumers_total": 3})


def test_infra_excluded_and_timeout_not_correct(summary):
    assert summary["excluded_infra"] == 1
    assert sum(summary["n_by_status"]["R"].values()) == 16
    assert summary["n_by_status"]["F"] == {"ok": 15, "timeout": 1}
    assert summary["correct_by_step"]["T2"]["F"]["k"] == 3
    assert summary["correct_by_step"]["T1"]["R"]["k"] == 2


def test_carried_defects_condition_by_step(summary):
    for s in ("T2", "T3", "T4"):
        assert (summary["carried_defects"][s]["R"]["k"],
                summary["carried_defects"][s]["R"]["n"]) == (2, 4)
        assert summary["carried_defects"][s]["F"]["k"] == 0
        assert summary["carried_defects"][s]["R"]["mean_count"] == 0.5
    assert "T1" not in summary["carried_defects"]


def test_efficiency_and_cost_growth(summary):
    tok = summary["efficiency"]["tokens"]
    assert tok["by_step"]["T1"]["R"]["median"] == 2000
    assert tok["by_step"]["T4"]["R"]["median"] == 4000
    assert tok["by_step"]["T1"]["F"]["median"] == 1000
    assert tok["mann_whitney_R_vs_F"]["p"] < 0.001
    assert (tok["zones_F_lower"], tok["zones_F_higher"]) == (2, 0)
    assert tok["sign_p"] == 0.5
    assert summary["efficiency"]["lines_added"]["all"]["F"]["median"] == 10
    assert summary["cost_growth_T4_over_T1"]["R"]["median"] == 2
    assert summary["cost_growth_T4_over_T1"]["F"]["median"] == 1


def test_duplication_condition_by_step(summary):
    d = summary["duplication"]
    assert d["T0"]["R"] == {"n": 4, "clones_mean": 5, "dup_lines_mean": 100}
    assert d["T4"]["R"]["dup_lines_mean"] == 160
    assert d["T4"]["F"]["dup_lines_mean"] == 20
    assert summary["duplication_growth_T0_to_T4"]["R"]["median"] == 60
    assert summary["duplication_growth_T0_to_T4"]["F"]["median"] == 0
    dm = summary["duplication_model"]
    assert dm["available"], dm
    # F grows 60 lines/4 steps less than R: F:step = -15.
    assert dm["coef"]["F:step"]["mean"] == pytest.approx(-15, abs=1e-6)


def test_mixed_models_fit(summary):
    m = summary["missed_copy_model"]
    assert m["available"], m
    assert m["n"] == 16
    assert m["coef"]["F"]["mean"] < 0
    assert set(m["vc_log_sd"]) == {"zone", "chain"}
    assert summary["carried_defects_model"]["available"]


def test_models_unavailable_without_variation():
    rows = [{"cond": c, "zone": "Z1", "chain": i, "step": 1, "consumers_passed": 3,
             "consumers_total": 3} for c in ("R", "F") for i in range(3)]
    m = tables2.missed_copy_model(rows)
    assert m == {"available": False, "reason": "no variation in outcome"}


def test_per_zone_and_t2_reuse(summary):
    z1 = summary["per_zone"]["Z1"]
    assert (z1["R"]["missed_copy"]["k"], z1["R"]["missed_copy"]["n"]) == (2, 4)
    assert (z1["F"]["missed_copy"]["k"], z1["F"]["missed_copy"]["n"]) == (1, 4)
    assert summary["per_zone"]["Z2"]["F"]["missed_copy"]["k"] == 0
    assert summary["t2_reuse"]["F"]["helper"] == 4
    assert summary["t2_reuse"]["R"]["copy"] == 4


def test_chain_ids_distinguish_conditions():
    a = {"zone": "Z1", "cond": "R", "chain": 0}
    b = {"zone": "Z1", "cond": "F", "chain": 0}
    assert tables2.chain_id(a) != tables2.chain_id(b)


def test_load_chains_fills_keys_from_path(runs):
    chains = tables2.load_chains(runs)
    assert len(chains) == 8
    assert {(c["agent"], c["cond"]) for c in chains} == {("claude", "R"), ("claude", "F")}


def test_sign_test():
    assert tables2.sign_test(0, 0) == 1.0
    assert tables2.sign_test(4, 0) == pytest.approx(0.125)
    assert tables2.sign_test(5, 5) == 1.0


def test_cli_writes_tables(runs, tmp_path, capsys):
    out = tmp_path / "out2"
    assert main(["tables2", "--runs", str(runs), "--out", str(out)]) == 0
    md = (out / "tables2.md").read_text()
    assert "## claude" in md
    assert "Missed copy on rule steps" in md
    assert "| T1+T3 | 50% [" in md
    assert "Per zone" in md
    data = json.loads((out / "summary2.json").read_text())
    assert data["claude"]["missed_copy"]["F"]["k"] == 1


# --- evaluated-only counting, pre-existing consumers, conditional T2, flags -------------

def _mini(cond="R", zone="Z1", chain=0, step=1, **kw):
    r = {"agent": "claude", "cond": cond, "zone": zone, "chain": chain, "step": step,
         "status": "ok", "eval_error": None, "correct": True, "consumers_passed": 5,
         "consumers_total": 5, "missed_copy": False, "carried_defects": 0,
         "diff": {"added": 1, "removed": 0},
         "tokens": {"input": 10, "output": 1, "cached_input": 0},
         "turns": 1, "tool_calls": 1, "wall_s": 1}
    return r | kw


def test_only_evaluated_steps_are_counted(tmp_path):
    rows = [_mini(chain=i) for i in range(2)] + [
        _mini(chain=2, status="setup_error", correct=False, eval_error="not_evaluated"),
        _mini(chain=3, status="harness_error", eval_error="not_evaluated"),
        _mini(chain=4, status="infra"),
        _mini(chain=5, status="infra_exhausted", eval_error="not_evaluated"),
        _mini(chain=6, eval_error="test_infra_restore", missed_copy=True),
        _mini(chain=7, eval_error="container"),
        _mini(cond="F", chain=0)]
    s = tables2.summarise(rows)["claude"]
    assert s["n_by_status"]["R"] == {"ok": 2}
    assert s["missed_copy"]["R"]["n"] == 2 and s["missed_copy"]["R"]["k"] == 0
    assert s["excluded"]["total"] == 6
    assert s["excluded"]["by_reason"] == {"eval_error": 2, "harness_error": 1, "infra": 1,
                                          "infra_exhausted": 1, "setup_error": 1}
    assert s["excluded"]["eval_errors"] == {"container": 1, "test_infra_restore": 1}
    assert s["excluded"]["by_cond"] == {"R": 6, "F": 0}
    assert s["excluded_infra"] == 2
    md = tables2.render_markdown({"claude": s})
    assert "excluded: 6 (eval_error 2, harness_error 1" in md
    assert "eval errors: container 1, test_infra_restore 1" in md
    assert "`error`" not in tables2.__doc__ and "|`error`|" not in tables2.__doc__


def test_missed_copy_primary_is_preexisting_consumers():
    # T3 in a chain whose T2 consumer is broken: every T1 consumer updated, the T2-added
    # one not -> missed copy on all consumers, not on the pre-existing ones.
    t3 = _mini(step=3, consumers_passed=5, consumers_total=6, missed_copy=True,
               consumers_preexisting_passed=5, consumers_preexisting_total=5,
               missed_copy_preexisting=False, t2_consumer_ok=False, correct=False)
    t3b = _mini(chain=1, step=3, consumers_passed=5, consumers_total=6, missed_copy=True,
                consumers_preexisting_passed=4, consumers_preexisting_total=5,
                missed_copy_preexisting=True, t2_consumer_ok=True, correct=False)
    rows = [_mini(), _mini(chain=1), t3, t3b, _mini(cond="F"), _mini(cond="F", step=3)]
    s = tables2.summarise(rows)["claude"]
    assert (s["missed_copy"]["R"]["k"], s["missed_copy"]["R"]["n"]) == (1, 4)
    assert s["missed_copy_by_step"]["T3"]["R"]["k"] == 1
    assert s["missed_copy_all_consumers"]["R"]["k"] == 2
    assert (s["t2_consumer_ok"]["T3"]["R"]["k"], s["t2_consumer_ok"]["T3"]["R"]["n"]) == (1, 2)
    assert s["t2_consumer_ok"]["T3"]["F"]["n"] == 0
    assert s["per_zone"]["Z1"]["R"]["missed_copy"]["k"] == 1
    assert s["coverage"]["R"]["median"] == 1          # 1, 1, 1, 0.8
    # derived from the split counts when the boolean is absent
    assert tables2.missed_copy_preexisting({"consumers_preexisting_passed": 2,
                                            "consumers_preexisting_total": 3,
                                            "missed_copy": False})
    assert not tables2.missed_copy_preexisting({"consumers_preexisting_passed": 0,
                                                "consumers_preexisting_total": 3})
    md = tables2.render_markdown({"claude": s})
    assert "| secondary: all consumers, T1+T3 |" in md
    assert "| T2-added consumer updated at T3 |" in md


def test_t2_correct_conditional_on_t1():
    rows = [_mini(chain=0, step=1), _mini(chain=0, step=2),
            _mini(chain=1, step=1), _mini(chain=1, step=2, correct=False),
            _mini(chain=2, step=1, correct=False), _mini(chain=2, step=2),
            _mini(chain=3, step=1, status="infra"), _mini(chain=3, step=2),
            _mini(cond="F", chain=0, step=1), _mini(cond="F", chain=0, step=2)]
    s = tables2.summarise(rows)["claude"]
    g = s["t2_correct_given_t1"]
    assert (g["T1_correct"]["R"]["k"], g["T1_correct"]["R"]["n"]) == (1, 2)
    assert (g["T1_incorrect"]["R"]["k"], g["T1_incorrect"]["R"]["n"]) == (1, 1)
    assert s["correct_by_step"]["T2"]["R"]["n"] == 4   # chain 3's T2 counts unconditionally
    assert (g["T1_correct"]["F"]["k"], g["T1_correct"]["F"]["n"]) == (1, 1)
    assert "| T2 given T1 correct |" in tables2.render_markdown({"claude": s})


def test_contamination_flagged_and_z4_weak_contrast():
    rows = [_mini(), _mini(chain=1, contamination_flag=True),
            _mini(zone="Z4"), _mini(cond="F"), _mini(cond="F", zone="Z4")]
    s = tables2.summarise(rows)["claude"]
    assert s["contamination"]["by_cond"] == {"R": 1, "F": 0}
    assert s["contamination"]["steps"] == ["R/Z1/1/T1"]
    assert set(s["per_zone_notes"]) == {"Z4"}
    md = tables2.render_markdown({"claude": s})
    assert "**Contamination flagged**" in md and "R/Z1/1/T1" in md
    assert "| Z4 (weak contrast) | R |" in md and "| Z1 | R |" in md
    assert "Z4: weak contrast" in md


def test_duplication_only_for_counted_steps():
    rows = [_mini(step=k) for k in (1, 2, 3)] + [_mini(step=4, eval_error="container")]
    chains = [{"agent": "claude", "cond": "R", "zone": "Z1", "chain": "0",
               "duplication": {f"T{k}": {"clones": k, "duplicated_lines": k}
                               for k in range(5)}}]
    s = tables2.summarise(rows, chains)["claude"]
    assert set(s["duplication"]) == {"T0", "T1", "T2", "T3"}
    assert s["duplication_growth_T0_to_T4"]["R"]["n"] == 0


def test_denominators_and_sensitivity_excluding_timeouts():
    # Counted rule steps form the denominator: a timeout is counted on its tree (here
    # a missed copy), zero consumers updated stays in as not missed; the sensitivity
    # table drops the timeout.
    rows = [_mini(step=1, status="timeout", correct=True, consumers_passed=2,
                  missed_copy=None),
            _mini(chain=1, step=1, consumers_passed=0, missed_copy=None, correct=False),
            _mini(chain=2, step=1),
            _mini(chain=3, step=1, status="infra"),
            _mini(chain=0, step=2, status="timeout"),
            _mini(cond="F", step=1)]
    s = tables2.summarise(rows)["claude"]
    assert (s["missed_copy"]["R"]["k"], s["missed_copy"]["R"]["n"]) == (1, 3)
    assert s["correct_by_step"]["T1"]["R"]["k"] == 1       # the timeout is not correct
    sv = s["sensitivity_excluding_timeouts"]
    assert sv["timeouts_dropped"] == {"R": 2, "F": 0}
    assert (sv["missed_copy"]["R"]["k"], sv["missed_copy"]["R"]["n"]) == (0, 2)
    assert (sv["missed_copy_by_step"]["T1"]["R"]["k"],
            sv["missed_copy_by_step"]["T1"]["R"]["n"]) == (0, 2)
    assert (sv["correct_by_step"]["T1"]["R"]["k"], sv["correct_by_step"]["T1"]["R"]["n"]) \
        == (1, 2)
    assert sv["correct_by_step"]["T2"]["R"]["n"] == 0
    assert sv["missed_copy"]["F"]["n"] == 1
    md = tables2.render_markdown({"claude": s})
    assert "### Sensitivity: without timed-out steps" in md
    assert "Timed-out steps dropped: R 2, F 0." in md


def test_f_comment_fact_split():
    rows = [_mini(zone="Z4", step=1, depends_on_f_comment_fact=False),
            _mini(zone="Z4", step=3, depends_on_f_comment_fact=True, consumers_passed=1,
                  missed_copy=None, correct=False),
            _mini(zone="Z4", step=2, depends_on_f_comment_fact=True),
            _mini(cond="F", zone="Z4", step=3, depends_on_f_comment_fact=True),
            _mini(cond="F", zone="Z1", step=1, depends_on_f_comment_fact=False)]
    s = tables2.summarise(rows)["claude"]
    sp = s["f_comment_fact_split"]
    assert set(sp) == {"depends", "independent"}            # no untagged step
    assert (sp["depends"]["missed_copy"]["R"]["k"], sp["depends"]["missed_copy"]["R"]["n"]) \
        == (1, 1)
    assert (sp["depends"]["correct"]["R"]["k"], sp["depends"]["correct"]["R"]["n"]) == (1, 2)
    assert (sp["independent"]["missed_copy"]["R"]["k"],
            sp["independent"]["missed_copy"]["R"]["n"]) == (0, 1)
    assert sp["depends"]["missed_copy"]["F"]["n"] == 1
    assert tables2.comment_fact_group({}) == "untagged"
    s2 = tables2.summarise(rows + [_mini(chain=9)])["claude"]
    assert s2["f_comment_fact_split"]["untagged"]["correct"]["R"]["n"] == 1
    md = tables2.render_markdown({"claude": s})
    assert "### Doc-comment confound" in md and "| depends |" in md
