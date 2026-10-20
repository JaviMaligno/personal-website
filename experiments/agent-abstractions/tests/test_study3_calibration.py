"""Study 3 ratchet calibration rule (spec §5, amendment 2026-10-11): the threshold choice in
``scripts/study3_calibrate_ratchet.py``, on synthetic counts (no replay)."""
import importlib.util
import json

from aa import config

_spec = importlib.util.spec_from_file_location(
    "study3_calibrate_ratchet", config.ROOT / "scripts" / "study3_calibrate_ratchet.py")
cal = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cal)


def test_first_clause_highest_threshold_with_low_fpr_and_enough_sensitivity():
    sens = {50: (45, 80), 35: (60, 80), 25: (70, 80)}
    fpr = {50: (2, 80), 35: (5, 80), 25: (30, 80)}
    assert cal.choose(sens, fpr)[0] == 50
    fpr[50] = (20, 80)
    assert cal.choose(sens, fpr)[0] == 35


def test_second_clause_takes_the_highest_threshold_with_sensitivity_at_least_half():
    # The study-2 counts: no FPR <= 10 %; 35 and 25 both reach 50 % sensitivity.
    sens = {50: (28, 93), 35: (47, 93), 25: (56, 93)}
    fpr = {50: (20, 91), 35: (29, 91), 25: (50, 91)}
    t, why = cal.choose(sens, fpr)
    assert t == 35
    assert "highest threshold with sensitivity >= 50 %" in why


def test_second_clause_when_the_low_fpr_threshold_is_not_sensitive_enough():
    sens = {50: (10, 80), 35: (45, 80), 25: (60, 80)}
    fpr = {50: (1, 80), 35: (20, 80), 25: (40, 80)}
    assert cal.choose(sens, fpr)[0] == 35


def test_no_threshold_qualifies():
    sens = {50: (1, 80), 35: (2, 80), 25: (3, 80)}
    fpr = {50: (1, 80), 35: (2, 80), 25: (3, 80)}
    assert cal.choose(sens, fpr)[0] is None


def test_registered_report_matches_config():
    summary = json.loads((config.ROOT / "out" / "study3" / "ratchet-calibration-summary.json")
                         .read_text())
    assert summary["chosen_min_tokens"] == config.RATCHET_MIN_TOKENS == 35
    assert summary["lint_blind_zones"] == ["Z2", "Z4"]
    assert summary["non_discriminating_zones"] == ["Z3"]


def _rec(cond, zone, step_id, fires, with_id=True):
    r = {"cond": cond, "zone": zone, "agent": "claude", "chain": 0,
         "step": f"runs2/claude/{cond}/{zone}/0/{step_id}",
         "t35": {"fires": fires, "new": int(fires), "clones": []}}
    if with_id:
        r["step_id"] = step_id
    return r


def test_firing_table_counts_per_cond_zone_step():
    # T2 records predate step_id (taken from the path); T1/T3/T4 carry it.
    t2 = [_rec("R", "Z1", "T2", True, with_id=False), _rec("R", "Z1", "T2", False, with_id=False)]
    other = [_rec("R", "Z1", "T1", True), _rec("R", "Z1", "T3", False),
             _rec("F", "Z2", "T4", True)]
    tab = cal.firing_table(t2, other)
    assert tab == {"R": {"Z1": {"T2": [1, 2], "T1": [1, 1], "T3": [0, 1]}},
                   "F": {"Z2": {"T4": [1, 1]}}}
    md = cal.firing_section(t2, other)
    assert "| Z1 | 1/1 = 100 %" in md and "lint blind" in md


def test_firing_steps_are_r_and_f_t1_t3_t4():
    got = cal.firing_steps()
    if not got:
        import pytest
        pytest.skip("runs2 not present")
    assert {p.name for p in got} == {"T1", "T3", "T4"}
    assert {p.parts[-4] for p in got} == {"R", "F"}
    assert len(got) == 3 * 2 * 4 * 8 * 3
