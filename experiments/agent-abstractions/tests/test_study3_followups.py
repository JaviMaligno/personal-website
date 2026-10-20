"""Study-3 follow-ups registered by spec amendment 2026-10-12b and the review of the pilot
fixes (amendment 2026-10-12c): RG's explicit-read key, the H4 decomposition
(``ratchet_trip_clones``), the calibration benchmark of ratchet firing, and a record for
every derived file the re-derivation commands rewrite."""
import hashlib
import json
from pathlib import Path

from aa import chain_eval3 as ce3
from aa import rederive, tables3
from aa.ratchet import Clone

F = Path(__file__).parent / "fixtures"
A = "packages/loot-core/src/server/x.ts"
B = "packages/loot-core/src/server/y.ts"


def _clone(a, s1, e1, b, s2, e2):
    return Clone(a, s1, e1, b, s2, e2, e1 - s1 + 1, 40)


def _trip(*rows: tuple) -> str:
    body = "\n".join(f"  {a}:{s1}-{e1} ~ {b}:{s2}-{e2} (40 tokens)" for a, s1, e1, b, s2, e2 in rows)
    return f"{ce3.DUP_CHECK_HEADER}\n{body}\n{ce3.DUP_CHECK_TRAILER}\n"


# --------------------------------------------------------------------------- item 7 (RG)

def test_rule_cited_writes_the_explicit_read_key():
    codex = [json.dumps({"type": "item.completed", "item": {
        "id": "item_1", "type": "command_execution", "command": "/bin/bash -lc 'cat AGENTS.md'",
        "aggregated_output": "x"}})]
    _, d = ce3.rule_cited("codex", codex)
    assert d["agents_md_explicit_read"] is True
    assert "agents_md_read" not in d


def _rg_row(arm, step, detail):
    return {"agent": "claude", "cond": arm, "zone": "Z1", "chain": 0, "step": step,
            "status": "ok", "eval_error": None, "rule_cited": False,
            "rule_cited_detail": detail}


def test_rg_table_reports_explicit_read_from_either_key():
    rows = [_rg_row("RG", 1, {"agents_md_read": True}),            # pilot result.json
            _rg_row("RG", 2, {"agents_md_explicit_read": False}),
            _rg_row("RG", 3, {}),                                   # not recorded
            _rg_row("R", 1, {"agents_md_explicit_read": False})]
    rg = tables3.rg_table(rows)
    assert rg["explicit_read"]["RG"]["k"] == 1 and rg["explicit_read"]["RG"]["n"] == 2
    assert rg["explicit_read"]["R"]["n"] == 1
    md = "\n".join(tables3._render_rg(rg))
    assert "agents_md_explicit_read" in md and "not a manipulation check" in md


# --------------------------------------------------------------------------- item 6 (H4)

def test_trip_clone_counts_consolidation():
    """Two start copies form a clone; the trip lists it (grown); the agent replaces both
    copies with one helper: the listed pre-existing clone is gone from the post tree."""
    start = [_clone(A, 10, 20, A, 30, 40)]
    trip = _trip((A, 10, 21, A, 31, 42))
    diff = (f"diff --git a/{A} b/{A}\n--- a/{A}\n+++ b/{A}\n@@ -10,31 +10,8 @@\n"
            + "".join(f"-old {i}\n" for i in range(10, 41))
            + "".join(f"+helper {i}\n" for i in range(8)))
    got = ce3.trip_clone_counts([trip], start, [], ce3.LineMap(diff))
    assert got == {"listed_preexisting": 1, "remaining": 0, "new_listed": 0,
                   "unreadable_trips": 0}


def test_trip_clone_counts_edit_moved_outside_the_clone():
    """The trip lists a start clone the agent edited inside; the agent reverts the edit
    and puts its check in a new wrapper elsewhere: the clone is still in the post tree."""
    start = [_clone(A, 10, 20, B, 10, 20)]
    trip = _trip((A, 10, 21, B, 10, 20))
    diff = (f"diff --git a/{A} b/{A}\n--- a/{A}\n+++ b/{A}\n@@ -50,0 +51,3 @@\n"
            + "".join(f"+wrapper {i}\n" for i in range(3)))
    post = [_clone(A, 10, 20, B, 10, 20)]
    got = ce3.trip_clone_counts([trip], start, post, ce3.LineMap(diff))
    assert got == {"listed_preexisting": 1, "remaining": 1, "new_listed": 0,
                   "unreadable_trips": 0}


def test_trip_clone_counts_new_clone_only_and_unreadable():
    start = [_clone(A, 10, 20, A, 30, 40)]
    pasted = _trip((A, 10, 20, B, 50, 60))  # a paste into another file, removed again
    unreadable = f"{ce3.DUP_CHECK_HEADER}\n(output cut)\n"
    got = ce3.trip_clone_counts([pasted, unreadable], start, [], ce3.LineMap())
    assert got == {"listed_preexisting": 0, "remaining": 0, "new_listed": 1,
                   "unreadable_trips": 1}
    assert ce3.trip_clone_counts([], start, [], ce3.LineMap()) is None


def test_trip_clone_counts_real_pilot_consolidations():
    """Amendment 2026-10-12b's read-only check: haiku RL Z1 T1 and claude RL Z3 T1 are (a)."""
    for name in ("haiku-RL-Z1-T1", "claude-RL-Z3-T1"):
        d = json.loads((F / "study3" / "trips_real" / f"{name}.json").read_text())
        cl = [Clone(**{k: c[k] for k in ("a", "a_start", "a_end", "b", "b_start", "b_end",
                                         "lines", "tokens")}) for c in d["start_clones"]]
        pc = [Clone(**{k: c[k] for k in ("a", "a_start", "a_end", "b", "b_start", "b_end",
                                         "lines", "tokens")}) for c in d["post_clones"]]
        got = ce3.trip_clone_counts(d["trips"], cl, pc, ce3.LineMap(d["diff"]))
        assert got["listed_preexisting"] >= 1 and got["remaining"] == 0, (name, got)


def _rl(zone, step, *, trips=0, fires=False, lint=1, gaming=None, tc=None, kinds=None,
        unified=None):
    return {"agent": "haiku", "cond": "RL", "zone": zone, "chain": 0, "step": step,
            "status": "ok", "eval_error": None, "ratchet_trips": trips,
            "ratchet_final": {"fires": fires}, "lint_runs": lint,
            "gaming_flags": gaming or {}, "ratchet_trip_clones": tc,
            "ratchet_trip_kinds": kinds if kinds is not None else ["x"] * trips,
            "inconsistencies_unified_step": unified}


def test_h4_class_order_and_split():
    tc = lambda L, R, N=0, u=0: {"listed_preexisting": L, "remaining": R, "new_listed": N,
                                 "unreadable_trips": u}
    assert tables3.h4_class(_rl("Z1", 1)) is None                       # not fired
    assert tables3.h4_class(_rl("Z1", 1, trips=1, gaming={"jscpd_ignore": ["a"]},
                                tc=tc(1, 0))) == "g"
    assert tables3.h4_class(_rl("Z1", 1, fires=True, lint=0)) == "d0"
    assert tables3.h4_class(_rl("Z1", 1, fires=True, lint=2)) == "d1"
    assert tables3.h4_class(_rl("Z1", 1, trips=2, fires=True, tc=tc(1, 1))) == "c"
    assert tables3.h4_class(_rl("Z1", 1, trips=1, tc=tc(2, 0))) == "a"
    assert tables3.h4_class(_rl("Z1", 1, trips=1, tc=tc(0, 0, N=1))) == "a"  # own paste gone
    assert tables3.h4_class(_rl("Z1", 1, trips=1, tc=tc(7, 7))) == "b"
    assert tables3.h4_class(_rl("Z1", 1, trips=1, tc=tc(3, 1))) == "ab"
    assert tables3.h4_class(_rl("Z1", 1, trips=1, tc=tc(1, 0, u=1))) == "u"
    assert tables3.h4_class(_rl("Z1", 1, trips=1, tc=tc(1, 0), kinds=[None])) == "u"
    # not yet derived: one "seen, passing" class
    assert tables3.h4_class(_rl("Z1", 1, trips=1)) == "seen_passing"
    # ratchet not computed on the final tree: outside H4's denominator
    r = _rl("Z1", 1, trips=1)
    r["ratchet_final"] = None
    assert tables3.h4_class(r) is None


def test_rl_table_h4_decomposition():
    tc = lambda L, R: {"listed_preexisting": L, "remaining": R, "new_listed": 0,
                       "unreadable_trips": 0}
    rows = [_rl("Z1", 1, trips=1, tc=tc(1, 0), unified=[]),             # a
            _rl("Z3", 1, trips=1, tc=tc(7, 7)),                         # b
            _rl("Z3", 2, trips=4, tc=tc(2, 0), unified=["akahu"]),      # a, unified
            _rl("Z1", 2, trips=1, fires=True, tc=tc(1, 1)),             # c
            _rl("Z1", 1, fires=True, lint=0),                           # d0 (another chain)
            _rl("Z4", 3, trips=1, tc=tc(1, 0)),                         # a, lint blind
            _rl("Z3", 3)]                                               # not fired
    rows[4]["chain"] = 1
    rows[5]["zone"] = "Z4"
    rl = tables3.rl_table(rows)
    dec = rl["h4_decomposition"]
    nb = dec["non_blind"]["all_steps"]
    assert nb["fired"] == 5 and nb["counts"]["a"] == 2 and nb["counts"]["b"] == 1
    assert nb["counts"]["c"] == 1 and nb["counts"]["d0"] == 1 and nb["counts"]["d1"] == 0
    assert nb["h4"]["k"] == 3 and nb["h4"]["n"] == 5
    assert nb["success_unified"] == 1
    assert dec["non_blind"]["T1"]["fired"] == 3 and dec["non_blind"]["T2_T4"]["fired"] == 2
    assert dec["all"]["all_steps"]["fired"] == 6
    # the registered H4 is unchanged by the decomposition
    assert rl["h4"]["non_blind"]["k"] == 3 and rl["h4"]["non_blind"]["n"] == 5
    md = "\n".join(tables3._render_h4_decomposition(dec))
    assert "(a) consolidation" in md and "(d0)" in md


# --------------------------------------------------------------------------- item 5

CALIB = {"Z1": {"T1": [24, 24], "T2": [19, 24], "T3": [10, 24], "T4": [24, 24]},
         "Z2": {"T1": [2, 24], "T2": [1, 24], "T3": [1, 24], "T4": [0, 24]},
         "Z3": {"T1": [24, 24], "T2": [24, 24], "T3": [1, 24], "T4": [24, 24]},
         "Z4": {"T1": [7, 24], "T2": [3, 24], "T3": [22, 24], "T4": [2, 24]}}


def _cal_row(arm, zone, step, fires, chain=0, trips=0):
    return {"agent": "codex", "cond": arm, "zone": zone, "chain": chain, "step": step,
            "status": "ok", "eval_error": None, "ratchet_trips": trips,
            "ratchet_final": {"fires": fires}}


def test_calibration_benchmark_cells_and_off_flag():
    rows = ([_cal_row("R", "Z2", 1, True, c) for c in range(6)]         # 6/6 vs 2/24: off
            + [_cal_row("R", "Z1", 1, True, c) for c in range(3)]       # 3/3 vs 24/24
            + [_cal_row("RL", "Z1", 1, False, c, trips=1) for c in range(3)]  # seen: fired
            + [_cal_row("RL", "Z2", 2, True, c) for c in range(6)]      # T2: not benchmarked
            + [_cal_row("RG", "Z2", 3, True, c) for c in range(6)])     # RG: benchmarked
    cal = tables3.calibration_table(rows, CALIB)
    assert cal["cells"]["Z2"]["T1"]["R"]["off"] is True
    assert cal["cells"]["Z1"]["T1"]["R"]["off"] is False
    assert cal["cells"]["Z1"]["T1"]["RL"]["rate"]["k"] == 3      # a trip counts as fired
    assert cal["cells"]["Z1"]["T1"]["RL"]["benchmarked"] is True
    assert cal["cells"]["Z2"]["T2"]["RL"]["benchmarked"] is False
    assert cal["cells"]["Z2"]["T2"]["RL"]["off"] is None          # never flagged
    assert cal["cells"]["Z2"]["T3"]["RG"]["off"] is True
    assert ("Z2", "T1", "R") in {tuple(x) for x in cal["off"]}
    assert cal["calibration"]["Z2"]["T1"]["k"] == 2
    md = "\n".join(tables3._render_calibration(cal))
    assert "off calibration" in md and "treatment outcome" in md
    assert tables3.calibration_table(rows, None) is None


def test_load_calibration_reads_the_r_cells(tmp_path):
    p = tmp_path / "cal.json"
    p.write_text(json.dumps({"firing_by_step_at_chosen": {"R": CALIB, "F": {}}}))
    assert tables3.load_calibration(p) == CALIB
    assert tables3.load_calibration(tmp_path / "missing.json") is None


# --------------------------------------------------------------------------- records

def _chain(root: Path, rel: str, *, post_patch: str = "diff --git a/x b/x\n") -> Path:
    """A minimal evaluated one-step chain (Z1 has four steps; only T1 exists here)."""
    c = root / rel
    t1 = c / "T1"
    (t1 / "eval").mkdir(parents=True)
    (t1 / "eval" / "pre_image.patch").write_text("")
    (t1 / "eval" / "post_tree.patch").write_text(post_patch)
    return c


def test_resummarise_records_chain_result_and_cumulative_patch(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    c = _chain(runs, "claude/R/Z1/0")
    (c / "chain_result.json").write_text(json.dumps({"agent": "claude", "cost_growth": None,
                                                     "duplication_T0_tree": None}))
    (c / "cumulative.patch").write_text("old content\n")

    def fake_summarise(chain_dir, chain):
        (chain_dir / "cumulative.patch").write_text("new content\n")
        out = {"agent": "claude", "cost_growth": None,
               "duplication_T0_tree": "untouched_variant"}
        (chain_dir / "chain_result.json").write_text(json.dumps(out))
        return out
    monkeypatch.setattr("aa.chain_eval.summarise_chain", fake_summarise)
    monkeypatch.setattr("aa.chain_eval.load_chain", lambda zone, root=None: None)
    rec = rederive.resummarise_chain(runs, c, None, by="test", rule="r")
    assert rec["kind"] == "resummarise_chain" and rec["chain"] == "claude/R/Z1/0"
    assert rec["changed"] == {"duplication_T0_tree": {"old": None, "new": "untouched_variant"}}
    cp = rec["cumulative_patch"]
    assert cp["sha256_before"] == hashlib.sha256(b"old content\n").hexdigest()
    assert cp["sha256_after"] == hashlib.sha256(b"new content\n").hexdigest()
    assert cp["changed"] is True
    # nothing changed -> no record
    assert rederive.resummarise_chain(runs, c, None, by="test", rule="r") is None


def test_reclassify_logs_the_chain_status_change(tmp_path):
    runs = tmp_path / "runs"
    d = runs / "codex/R/Z3/0/T1"
    d.mkdir(parents=True)
    net = F / "study3" / "network" / "codex-R-Z3-T1-stall.jsonl"
    (d / "transcript.jsonl").write_text(net.read_text())
    (d / "agent.json").write_text(json.dumps({
        "agent": "codex", "cond": "R", "zone": "Z3", "chain": 0, "step": "T1",
        "status": "timeout", "exit_code": 124,
        "usage": {"input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0,
                  "turns": 13, "tool_calls": 10}}))
    (d.parent / "chain.json").write_text(json.dumps({
        "agent": "codex", "cond": "R", "zone": "Z3", "chain": 0,
        "steps": {"T1": "timeout", "T2": "ok", "T3": "ok", "T4": "ok"}, "status": "ok"}))
    out = rederive.reclassify_runs(runs, log=lambda s: None)
    assert out["applied"][0]["chain_status"] == {"from": "ok", "to": None}
    log = [json.loads(x) for x in (runs / rederive.LOG_FILE).read_text().splitlines()]
    assert log[0]["chain_status"] == {"from": "ok", "to": None}


def test_record_past_summaries_from_a_backup(tmp_path):
    """Retrospective records for chain summaries rewritten without one: chain_result.json
    and chain.json differences against a backup, and cumulative.patch checked against the
    file it is copied from (the last step's eval/post_tree.patch)."""
    runs, before = tmp_path / "runs", tmp_path / "before"
    for root in (runs, before):
        (root / "claude/R/Z1/0").mkdir(parents=True)
    c = _chain(runs, "claude/R/Z1/1", post_patch="P\n")
    (before / "claude/R/Z1/1").mkdir(parents=True)
    (c / "cumulative.patch").write_text("P\n")
    (c / "chain_result.json").write_text(json.dumps(
        {"duplication_T0_tree": "untouched_variant",
         "cumulative_diff": {"path": "cumulative.patch", "from": "T1", "files": 1}}))
    (before / "claude/R/Z1/1/chain_result.json").write_text(json.dumps(
        {"cumulative_diff": {"path": "cumulative.patch", "files": 1}}))
    (c / "chain.json").write_text(json.dumps({"status": None}))
    (before / "claude/R/Z1/1/chain.json").write_text(json.dumps({"status": "ok"}))
    recs = rederive.record_past_summaries(runs, before, last_step="T1", log=lambda s: None)
    assert len(recs) == 1
    r = recs[0]
    assert r["retrospective"] is True and r["chain"] == "claude/R/Z1/1"
    assert r["chain_result_changed"]["duplication_T0_tree"] == {"old": None,
                                                                "new": "untouched_variant"}
    assert r["chain_result_changed"]["cumulative_diff"]["new"]["from"] == "T1"
    assert r["chain_json_changed"] == {"status": {"old": "ok", "new": None}}
    assert r["cumulative_patch"]["equals_source"] is True
    assert r["cumulative_patch"]["stats_equal_before"] is True
    log = (runs / rederive.LOG_FILE).read_text().splitlines()
    assert len(log) == 1
    # idempotent: an already recorded chain is not recorded again
    assert rederive.record_past_summaries(runs, before, last_step="T1", log=lambda s: None) == []
