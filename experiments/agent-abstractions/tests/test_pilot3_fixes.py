"""Study-3 pilot blocking items 1-3 (docs/study3-pilot-report.md section 6): network
stalls are infra, Claude usage summed over every `result`, Codex usage missing (not 0)
when no `turn.completed` arrived."""
import json
from pathlib import Path

from aa import config
from aa.agents import Usage, parse_claude_stream, parse_codex_stream, parse_stream, transport_stalled
from aa.runner import classify_status

F = Path(__file__).parent / "fixtures"
NET = F / "study3" / "network"


def _lines(p: Path) -> list[str]:
    return p.read_text().splitlines()


def _cl(*events: dict) -> list[str]:
    return [json.dumps(e) for e in events]


# --------------------------------------------------------------------------- item 1

def test_real_codex_network_stalls_are_infra_not_timeout():
    # runs3-pilot codex/R/Z3/0/T1 and codex/RC/Z3/0/T2: DNS outage, 25 / 23
    # "Reconnecting... waiting for network" events, killed at the wall limit (exit 124)
    for name in ("codex-R-Z3-T1-stall.jsonl", "codex-RC-Z3-T2-stall.jsonl"):
        lines = _lines(NET / name)
        usage, outcome = parse_codex_stream(lines)
        assert transport_stalled("codex", lines)
        assert classify_status(outcome, 124, usage, stalled=True) == "infra"
        # before the fix: exit 124 won over the parsed infra outcome
        assert classify_status(outcome, 124, usage) == "timeout"


def test_real_codex_agent_timeout_stays_timeout():
    # runs2 codex/F/Z3/1/T1: the agent was still running commands when killed
    lines = _lines(NET / "codex-F-Z3-T1-agent-timeout.jsonl")
    usage, outcome = parse_codex_stream(lines)
    assert not transport_stalled("codex", lines)
    assert usage.input_tokens is None  # no turn.completed: missing, not 0 (item 3)
    assert classify_status(outcome, 124, usage, stalled=False) == "timeout"


def test_codex_stall_followed_by_progress_is_not_stalled():
    lines = _lines(NET / "codex-R-Z3-T1-stall.jsonl") + _cl(
        {"type": "item.started", "item": {"id": "item_99", "type": "command_execution",
                                          "command": "yarn lint"}},
        {"type": "item.completed", "item": {"id": "item_99", "type": "command_execution",
                                            "command": "yarn lint", "aggregated_output": "ok"}})
    assert not transport_stalled("codex", lines)


def test_codex_transcript_without_transport_errors_is_not_stalled():
    assert not transport_stalled("codex", _lines(F / "codex-ok.jsonl"))
    assert not transport_stalled("codex", [])


def _asst(mid: str, content: list, model: str = "claude-sonnet-5-5") -> dict:
    return {"type": "assistant", "message": {"id": mid, "model": model, "content": content,
                                             "usage": {"input_tokens": 1, "output_tokens": 1}}}


def test_claude_connection_errors_at_the_end_are_a_stall():
    # Synthetic (no Claude Code outage in the pilot or study 2): the CLI's API retry
    # notices, or its synthetic "API Error: Connection error." message, after the last
    # real agent message.
    work = [{"type": "system", "subtype": "init"},
            _asst("m1", [{"type": "tool_use", "id": "t1", "name": "Bash",
                          "input": {"command": "ls"}}]),
            {"type": "user", "message": {"content": [{"type": "tool_result",
                                                      "tool_use_id": "t1", "content": "x"}]}}]
    retry = {"type": "system", "subtype": "api_retry", "attempt": 3, "max_retries": 10,
             "error": "Connection error."}
    assert transport_stalled("claude", _cl(*work, retry, retry))
    synthetic = _asst("m2", [{"type": "text", "text": "API Error: Connection error."}],
                      model="<synthetic>")
    assert transport_stalled("haiku", _cl(*work, synthetic))
    # an error that the agent recovered from is not a stall
    assert not transport_stalled("claude", _cl(*work, retry, _asst("m3", [
        {"type": "text", "text": "Continuing."}])))
    # a normal stream is not a stall
    assert not transport_stalled("claude", _lines(F / "claude-stream-ok.jsonl"))
    # a real answer that merely mentions a connection error is not a stall
    assert not transport_stalled("claude", _cl(*work, _asst("m4", [
        {"type": "text", "text": "Handled the connection error case in sync.ts."}])))


def test_no_agent_activity_at_the_wall_limit_is_infra():
    assert classify_status("infra", 124, Usage()) == "infra"
    assert classify_status("infra", 124, Usage(input_tokens=None, output_tokens=None,
                                               cached_input_tokens=None)) == "infra"
    # Codex never reports usage before turn.completed: missing usage with real tool
    # calls is an agent timeout, not infra
    assert classify_status("infra", 124, Usage(input_tokens=None, output_tokens=None,
                                               cached_input_tokens=None, turns=29,
                                               tool_calls=24)) == "timeout"
    assert classify_status("ok", 124, Usage(input_tokens=5, output_tokens=1, turns=1)) == "timeout"


# --------------------------------------------------------------------------- item 2

def test_claude_usage_and_turns_summed_over_every_result():
    # runs3-pilot claude/RL/Z4/0/T1: three `result` events (Claude Code woke the agent
    # after background tasks); before the fix only the last was kept (2 turns, 102,715
    # input, 361 output)
    usage, outcome = parse_claude_stream(_lines(F / "study3" / "claude-RL-Z4-T1-multi-result.jsonl"))
    assert outcome == "ok"
    assert usage.turns == 23 + 3 + 2
    assert usage.input_tokens == 1_114_530
    assert usage.output_tokens == 9457 + 870 + 361
    assert usage.cached_input_tokens == 833_212 + 141_434 + 100_405


def test_claude_messages_after_the_last_result_are_added():
    u = {"input_tokens": 10, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
         "output_tokens": 5}
    res = {"type": "result", "subtype": "success", "is_error": False, "num_turns": 2,
           "result": "done", "usage": u}
    tail = {"type": "assistant", "message": {"id": "late", "model": "claude-sonnet-5-5",
                                             "content": [{"type": "text", "text": "woke"}],
                                             "usage": u}}
    usage, _ = parse_claude_stream(_cl(res, tail))
    assert (usage.input_tokens, usage.output_tokens, usage.turns) == (20, 10, 3)


def test_claude_single_result_unchanged():
    usage, _ = parse_claude_stream(_lines(F / "claude-stream-ok.jsonl"))
    assert (usage.input_tokens, usage.cached_input_tokens, usage.output_tokens) == (48955, 34751, 144)
    assert usage.turns == 2


# --------------------------------------------------------------------------- item 3

def test_codex_without_turn_completed_has_missing_usage():
    usage, outcome = parse_codex_stream(_lines(NET / "codex-R-Z3-T1-stall.jsonl"))
    assert (usage.input_tokens, usage.output_tokens, usage.cached_input_tokens) == (None, None, None)
    assert usage.tool_calls >= 1 and outcome == "infra"


def test_codex_with_turn_completed_keeps_usage():
    usage, _ = parse_codex_stream(_lines(F / "codex-ok.jsonl"))
    assert (usage.input_tokens, usage.cached_input_tokens, usage.output_tokens) == (19256, 11008, 20)


def test_parse_stream_dispatch_unchanged():
    assert parse_stream("haiku", _lines(F / "claude-stream-ok.jsonl"))[1] == "ok"
    assert config.engine("haiku") == "claude"


# --------------------------------------------------------------------------- result.json usage

def test_usage_fields_reparse_the_transcript_and_keep_the_runner_record():
    from aa.chain_eval import step_tokens, usage_fields
    lines = _lines(F / "study3" / "claude-RL-Z4-T1-multi-result.jsonl")
    meta = {"agent": "claude", "usage": {"input_tokens": 102715, "output_tokens": 361,
                                         "cached_input_tokens": 100405, "turns": 2,
                                         "tool_calls": 25}}
    u = usage_fields(meta, lines)
    assert u["tokens"] == {"input": 1_114_530, "output": 10_688, "cached_input": 1_075_051}
    assert u["turns"] == 28 and u["usage_source"] == "transcript" and not u["usage_missing"]
    assert u["usage_reparsed"]["agent_json"]["turns"] == 2
    assert step_tokens(u) == 1_114_530 + 10_688
    # no transcript: agent.json as recorded
    v = usage_fields(meta, [])
    assert v["tokens"]["input"] == 102715 and v["usage_source"] == "agent_json"
    # codex killed before turn.completed: missing, not 0
    w = usage_fields({"agent": "codex", "usage": {"input_tokens": 0, "output_tokens": 0,
                                                  "cached_input_tokens": 0, "turns": 24,
                                                  "tool_calls": 21}},
                     _lines(NET / "codex-R-Z3-T1-stall.jsonl"))
    assert w["tokens"] == {"input": None, "output": None, "cached_input": None}
    assert w["usage_missing"] and step_tokens(w) is None


def _step(root: Path, rel: str, agent_meta: dict, transcript: Path, result: dict) -> Path:
    d = root / rel
    d.mkdir(parents=True)
    (d / "agent.json").write_text(json.dumps(agent_meta))
    (d / "transcript.jsonl").write_text(transcript.read_text())
    (d / "result.json").write_text(json.dumps(result))
    return d


def test_reparse_rewrites_result_usage_with_a_record(tmp_path):
    from aa import rederive
    runs = tmp_path / "runs"
    old_c = {"input_tokens": 102715, "output_tokens": 361, "cached_input_tokens": 100405,
             "turns": 2, "tool_calls": 25}
    c = _step(runs, "claude/RL/Z4/0/T1",
              {"agent": "claude", "cond": "RL", "zone": "Z4", "chain": 0, "step": "T1",
               "status": "ok", "usage": old_c},
              F / "study3" / "claude-RL-Z4-T1-multi-result.jsonl",
              {"agent": "claude", "cond": "RL", "zone": "Z4", "chain": 0, "step": 1,
               "step_id": "T1", "status": "ok", "wall_s": 1365,
               "tokens": {"input": 102715, "output": 361, "cached_input": 100405},
               "turns": 2, "tool_calls": 25})
    x = _step(runs, "codex/R/Z3/0/T1",
              {"agent": "codex", "cond": "R", "zone": "Z3", "chain": 0, "step": "T1",
               "status": "timeout", "usage": {"input_tokens": 0, "output_tokens": 0,
                                              "cached_input_tokens": 0, "turns": 13,
                                              "tool_calls": 10}},
              NET / "codex-R-Z3-T1-stall.jsonl",
              {"agent": "codex", "cond": "R", "zone": "Z3", "chain": 0, "step": 1,
               "step_id": "T1", "status": "timeout", "wall_s": 1513,
               "tokens": {"input": 0, "output": 0, "cached_input": 0}, "turns": 2,
               "tool_calls": 2})
    agent_before = (c / "agent.json").read_text()
    changed = rederive.reparse_runs(runs, apply=False)
    assert sorted(r["step"] for r in changed) == ["claude/RL/Z4/0/T1", "codex/R/Z3/0/T1"]
    assert json.loads((c / "result.json").read_text())["turns"] == 2  # dry run
    changed = rederive.reparse_runs(runs)
    rc = json.loads((c / "result.json").read_text())
    assert rc["tokens"] == {"input": 1_114_530, "output": 10_688, "cached_input": 1_075_051}
    assert rc["turns"] == 28 and rc["usage_missing"] is False
    assert rc["rederived"][0]["old"]["turns"] == 2 and rc["rederived"][0]["by"] == "aa chain reparse"
    assert (c / "agent.json").read_text() == agent_before  # the runner's record is kept
    rx = json.loads((x / "result.json").read_text())
    assert rx["tokens"] == {"input": None, "output": None, "cached_input": None}
    assert rx["usage_missing"] is True
    s = rederive.usage_change_summary(changed)
    assert s["claude"]["steps"] == 1 and s["claude"]["turns_delta"] == 26
    assert s["claude"]["input_delta"] == 1_114_530 - 102_715
    assert s["codex"]["now_missing"] == 1
    # chain summaries rewritten from the new values; missing tokens are not a 0
    cr_c = json.loads((c.parent / "chain_result.json").read_text())
    assert cr_c["totals"]["t1_tn"]["tokens"] == 1_114_530 + 10_688
    cr_x = json.loads((x.parent / "chain_result.json").read_text())
    assert cr_x["totals"]["t1_tn"]["tokens"] is None
    assert cr_x["totals"]["t1_tn"]["tokens_missing_steps"] == 1
    log = [json.loads(x) for x in (runs / "rederive-log.jsonl").read_text().splitlines()]
    assert [r["kind"] for r in log] == ["reparse_usage"] * 2 + ["resummarise_chain"] * 2
    # the rewritten chain summaries are recorded too (amendment 2026-10-12c)
    assert {r["chain"] for r in log[2:]} == {"claude/RL/Z4/0", "codex/R/Z3/0"}
    # idempotent
    assert rederive.reparse_runs(runs) == []
    assert len((runs / "rederive-log.jsonl").read_text().splitlines()) == 4


# --------------------------------------------------------------------------- tables

def test_dist_excludes_missing_and_counts_it():
    from aa.tables2 import _dist, _fmt_dist, total_tokens
    d = _dist([10, None, 30])
    assert d["n"] == 2 and d["median"] == 20 and d["missing"] == 1
    assert _fmt_dist(d).endswith("(n=2, 1 missing)")
    assert _dist([1, 2])["missing"] == 0 and _fmt_dist(_dist([1, 2])).endswith("(n=2)")
    assert total_tokens({"tokens": {"input": None, "output": None}}) is None
    assert total_tokens({"tokens": {"input": 3, "output": 4}}) == 7


def test_tables2_efficiency_excludes_missing_tokens(tmp_path):
    import test_tables2 as t2t
    from aa import tables2
    root = tmp_path / "runs2"
    for cond in ("R", "F"):
        for zone in ("Z1", "Z2"):
            for chain in (0, 1):
                for step in (1, 2, 3, 4):
                    r = t2t._step(cond, zone, chain, step)
                    if (cond, zone, chain, step) == ("R", "Z1", 1, 2):
                        r["tokens"] = {"input": None, "output": None, "cached_input": None}
                        r["usage_missing"] = True
                    t2t._write(root, r)
    s = tables2.summarise(tables2.load_steps(root), tables2.load_chains(root))
    tok = s["claude"]["efficiency"]["tokens"]
    assert tok["all"]["R"]["n"] == 15 and tok["all"]["R"]["missing"] == 1
    assert tok["by_step"]["T2"]["R"]["n"] == 3
    assert s["claude"]["efficiency"]["turns"]["all"]["R"]["n"] == 16  # turns observed
    assert "1 missing" in tables2.render_markdown(s)


def test_tables3_steps_after_an_infra_step_are_excluded_and_totals_skip_missing():
    from aa import tables3
    from aa.tables2 import exclusion, mark_after_infra
    rows = [{"agent": "codex", "cond": "R", "zone": "Z3", "chain": 0, "step": k,
             "status": "ok", "tokens": {"input": 10, "output": 1}, "wall_s": 1}
            for k in (1, 2, 3, 4)]
    rows[0]["status"] = "infra"
    rows[0]["tokens"] = {"input": None, "output": None}
    mark_after_infra(rows)
    assert [exclusion(r) for r in rows] == ["infra", "after_infra", "after_infra", "after_infra"]
    ok = [{"agent": "codex", "cond": "R", "zone": "Z1", "chain": 0, "step": k, "status": "ok",
           "tokens": {"input": 10, "output": 1}, "wall_s": 1} for k in (1, 2, 3, 4)]
    ok[2]["tokens"] = {"input": None, "output": None}
    tot = tables3.chain_totals(ok)
    assert tot[0]["tokens_t1_t4"] is None and tot[0]["tokens_missing_steps"] == 1
    assert tot[0]["wall_s_t1_t4"] == 4
    d = tables3._pair_dist({"R": [1, None, 3], "arm": [2, 4]},
                           {"R": ["Z1", "Z1", "Z1"], "arm": ["Z1", "Z1"]})
    assert d["R"]["n"] == 2 and d["R"]["missing"] == 1 and d["mann_whitney"]["p"] is not None


# --------------------------------------------------------------------------- item 4

def _clone(a, s1, e1, b, s2, e2):
    from aa.ratchet import Clone
    return Clone(a, s1, e1, b, s2, e2, e1 - s1 + 1, 40)


def _trip(*rows: tuple) -> str:
    from aa.chain_eval3 import DUP_CHECK_HEADER, DUP_CHECK_TRAILER
    body = "\n".join(f"  {a}:{s1}-{e1} ~ {b}:{s2}-{e2} (40 tokens)" for a, s1, e1, b, s2, e2 in rows)
    return f"{DUP_CHECK_HEADER}\n{body}\n{DUP_CHECK_TRAILER}\n"


A = "packages/loot-core/src/server/x.ts"


def test_trip_then_consolidate_reads_preexisting():
    """Start tree: two copies (lines 10-20 and 30-40) form a clone. The agent inserts a
    check in each copy; dup-check trips on the grown pair (10-21 ~ 31-42); the agent then
    replaces both copies with one helper. The final diff removes the copies, so mapping the
    trip's lines with it (the old rule) called the pre-existing pair new."""
    from aa import chain_eval3 as ce3
    start = [_clone(A, 10, 20, A, 30, 40)]
    trip = _trip((A, 10, 21, A, 31, 42))
    # final: lines 10-40 replaced by a 6-line helper + 2 thin callers
    final_diff = (f"diff --git a/{A} b/{A}\n--- a/{A}\n+++ b/{A}\n@@ -10,31 +10,8 @@\n"
                  + "".join(f"-old {i}\n" for i in range(10, 41))
                  + "".join(f"+helper {i}\n" for i in range(8)))
    lmap = ce3.LineMap(final_diff)
    assert ce3.trip_kind(trip, start, lmap) == "adds_new_clone_side"  # the old reading
    kind, basis = ce3.classify_trip(trip, start, [], lmap)
    assert (kind, basis) == ("touches_preexisting_only", "start_lines")
    # a copy pasted elsewhere and removed again before the end stays new
    pasted = _trip((A, 10, 20, A, 50, 60))
    assert ce3.classify_trip(pasted, start, [], lmap)[0] == "adds_new_clone_side"


def test_trip_still_in_the_final_tree_uses_the_final_diff():
    """When the trip's clone is still a clone of the post tree at the same lines, the tree
    at the trip is the final one there: the final diff maps it exactly (a copy pasted right
    after an old side stays new, amendment 2026-10-11d)."""
    from aa import chain_eval3 as ce3
    start = [_clone(A, 10, 20, A, 30, 40)]
    # 11 lines pasted after line 40 (post 41-51), copying 30-40
    diff = (f"diff --git a/{A} b/{A}\n--- a/{A}\n+++ b/{A}\n@@ -40,0 +41,11 @@\n"
            + "".join(f"+copy {i}\n" for i in range(11)))
    post = [_clone(A, 10, 20, A, 30, 40), _clone(A, 30, 40, A, 41, 51)]
    trip = _trip((A, 30, 40, A, 41, 51))
    kind, basis = ce3.classify_trip(trip, start, post, ce3.LineMap(diff))
    assert (kind, basis) == ("adds_new_clone_side", "final_tree")


def _real(name: str):
    from aa import chain_eval3 as ce3
    from aa.ratchet import Clone
    d = json.loads((F / "study3" / "trips_real" / f"{name}.json").read_text())
    cl = [Clone(c["a"], c["a_start"], c["a_end"], c["b"], c["b_start"], c["b_end"],
                c["lines"], c["tokens"]) for c in d["start_clones"]]
    pc = [Clone(c["a"], c["a_start"], c["a_end"], c["b"], c["b_start"], c["b_end"],
                c["lines"], c["tokens"]) for c in d["post_clones"]]
    return d["trips"], cl, pc, ce3.LineMap(d["diff"])


def test_real_pilot_trips_before_a_consolidation_read_preexisting():
    """Pilot report section 3.2: rebuilding the tree at the trip flips haiku RL Z1 T1
    (trip 0) and claude RL Z3 T1 (trips 0-1) to touches_preexisting_only; claude's trips
    2-3 also list clones of its new helper and stay new."""
    from aa import chain_eval3 as ce3
    trips, start, post, lmap = _real("haiku-RL-Z1-T1")
    assert [ce3.trip_kind(t, start, lmap) for t in trips] == ["adds_new_clone_side"]
    assert [ce3.classify_trip(t, start, post, lmap)[0] for t in trips] == \
        ["touches_preexisting_only"]
    trips, start, post, lmap = _real("claude-RL-Z3-T1")
    assert [ce3.classify_trip(t, start, post, lmap)[0] for t in trips] == \
        ["touches_preexisting_only", "touches_preexisting_only", "adds_new_clone_side",
         "adds_new_clone_side"]
    assert ce3.ratchet_split([ce3.classify_trip(t, start, post, lmap)[0] for t in trips],
                             None) == "touches_preexisting_only"


# --------------------------------------------------------------------------- item 9

def test_inconsistency_scope_file_covers_every_t0_test_with_a_reason():
    from aa.chains import list_t0_zones, load_inconsistency_scope, load_t0, scope_tests
    scope = load_inconsistency_scope()
    for z in list_t0_zones():
        t0 = load_t0(z)
        assert set(scope[z]) == set(t0.inconsistencies)
        for v in scope[z].values():
            assert len(v["reason"]) > 40
    z1, z2, z3 = (load_t0(z) for z in ("Z1", "Z2", "Z3"))
    for step in ("T1", "T2", "T3", "T4"):
        assert scope_tests(z1, step, scope) == {}
        assert scope_tests(z2, step, scope) == {}
        assert set(scope_tests(z3, step, scope).values()) == {
            "pluggyai-file-id", "gocardless-mask-official-name", "akahu-changed-tables"}
    assert scope_tests(load_t0("Z4"), "T2", scope) == {}


def test_inconsistency_scope_validation(tmp_path):
    import pytest as _pt
    from aa.chains import T0Error, load_inconsistency_scope
    p = tmp_path / "inconsistency-scope.json"
    p.write_text(json.dumps({"zones": {"Z1": {"x": {"superseded_at": ["T5"], "reason": "r"}}}}))
    with _pt.raises(T0Error):
        load_inconsistency_scope(tmp_path)
    p.write_text(json.dumps({"zones": {"Z1": {"x": {"superseded_at": ["T1"]}}}}))
    with _pt.raises(T0Error):
        load_inconsistency_scope(tmp_path)


def test_eval_script_runs_the_scoped_t0_tests_after_the_hidden_ones():
    from aa.chain_eval import chain_eval_script
    hid = "packages/loot-core/src/server/accounts/z3-inconsistencies.test.ts"
    plan = {"from": "image", "patches": ["T1/diff.patch"]}
    full = chain_eval_script("T2", plan, agent_tree="diff",
                             hidden_tests=["packages/loot-core/src/x/t1.test.ts"],
                             zone_files=["packages/loot-core/src/server/accounts/app.ts"],
                             study3=True, scope_tests=[hid])
    assert full.index("/out/report.json") < full.index("/out/scope_tests.json")
    assert "src/server/accounts/z3-inconsistencies.test.ts" in full
    only = chain_eval_script("T2", plan, agent_tree="diff", hidden_tests=[],
                             zone_files=["packages/loot-core/src/server/accounts/app.ts"],
                             study3=True, scope_tests=[hid], behaviour_only=True)
    assert "/out/scope_tests.json" in only and "/out/report.json" not in only
    assert "jscpd" not in only and "yarn lint" not in only and "tsgo" not in only
    assert "git apply" in only and "test_infra_restore" in only and "/out/post_tree" in only
    no_scope = chain_eval_script("T2", plan, agent_tree="diff", hidden_tests=[],
                                 zone_files=["a.ts"], study3=True)
    assert "scope_tests" not in no_scope


def test_scope_outcome_lists_the_unified_inconsistencies(tmp_path):
    from aa.chain_eval3 import scope_outcome
    names = {"Z3 T0 a": "akahu-changed-tables", "Z3 T0 b": "pluggyai-file-id"}
    f = "/work/actual/packages/loot-core/src/server/accounts/z3-inconsistencies.test.ts"
    (tmp_path / "scope_tests.json").write_text(json.dumps({"testResults": [{
        "name": f, "status": "failed", "assertionResults": [
            {"fullName": "Z3 T0 a", "status": "failed"},
            {"fullName": "Z3 T0 b", "status": "passed"}]}]}))
    unified, det = scope_outcome(tmp_path, names)
    assert unified == ["akahu-changed-tables"]
    assert det["results"] == {"Z3 T0 a": "failed", "Z3 T0 b": "passed"}
    assert scope_outcome(tmp_path / "nope", names)[0] is None  # did not run: missing
    assert scope_outcome(tmp_path, {})[0] is None  # nothing in scope


def _z3_step(runs: Path, step: str = "T2", status: str = "ok") -> Path:
    d = runs / "haiku" / "RL" / "Z3" / "0" / step
    d.mkdir(parents=True)
    plan = {"from": "image", "patches": ["T1/diff.patch"], "expected_start_tree": "s"}
    (d / "start.json").write_text(json.dumps(plan))
    (d / "agent.json").write_text(json.dumps({"agent": "haiku", "cond": "RL", "zone": "Z3",
                                              "chain": 0, "step": step, "study": 3,
                                              "status": status, "post_tree": "abc"}))
    (d / "post_tree").write_text("runner-tree\n")
    (d / "eval").mkdir()
    (d / "eval" / "post_tree").write_text("abc\n")  # the evaluator's own post tree
    (d / "diff.patch").write_text("")
    (d / "diff_ok").write_text("")
    (d / "result.json").write_text(json.dumps({"agent": "haiku", "cond": "RL", "zone": "Z3",
                                               "chain": 0, "step": 2, "step_id": step,
                                               "study": 3, "status": status,
                                               "eval_error": None}))
    return d


def test_behaviour_check_step_with_a_fake_container(tmp_path):
    from aa import rederive
    from aa.chains import load_t0
    names = load_t0("Z3").tests
    seen = []

    def fake(argv, timeout):
        seen.append(argv)
        out = Path(next(a.split(":")[0] for a in argv if a.endswith(":/out")))
        (out / "post_tree").write_text("abc\n")
        (out / "scope_tests.json").write_text(json.dumps({"testResults": [{
            "name": "/work/actual/packages/loot-core/src/server/accounts/z3-inconsistencies.test.ts",
            "status": "failed", "assertionResults": [
                {"fullName": n, "status": "failed" if i == "akahu-changed-tables" else "passed"}
                for n, i in names.items()]}]}))
        return 0

    d = _z3_step(tmp_path / "runs3")
    out = rederive.behaviour_check_runs(tmp_path / "runs3", execute=fake)
    assert len(seen) == 1 and "aa-actual:RL" in seen[0]
    script = seen[0][-1]
    assert "/out/scope_tests.json" in script and "/out/report.json" not in script
    assert out[0]["new"] == ["akahu-changed-tables"]
    r = json.loads((d / "result.json").read_text())
    assert r["inconsistencies_unified_step"] == ["akahu-changed-tables"]
    assert r["inconsistency_scope_detail"]["post_tree_check"] is True
    assert r["rederived"][-1]["what"] == "inconsistencies_unified_step"
    assert sorted(p.name for p in (d / "eval").iterdir()) == ["post_tree"]  # untouched
    # a tree that does not rebuild to the runner's post tree is not read
    def bad(argv, timeout):
        o = Path(next(a.split(":")[0] for a in argv if a.endswith(":/out")))
        (o / "post_tree").write_text("other\n")
        return 0
    assert rederive.behaviour_check_step(d, execute=bad)[1]["inconsistencies_unified_step"] is None


def test_behaviour_check_without_tests_in_scope_runs_no_container(tmp_path):
    from aa import rederive
    d = _z3_step(tmp_path / "runs3")
    for f in ("agent.json", "result.json"):
        r = json.loads((d / f).read_text())
        r["zone"] = "Z1"
        (d / f).write_text(json.dumps(r))

    def boom(argv, timeout):
        raise AssertionError("no container expected")
    old, new = rederive.behaviour_check_step(d, execute=boom)
    assert new["inconsistencies_unified_step"] is None
    assert new["inconsistency_scope_detail"]["reason"] == "no_test_in_scope"


def test_tables3_behaviour_check_beside_h4_and_the_t2_label():
    from aa import tables3
    def row(arm, zone, step, unified, **kw):
        r = {"agent": "haiku", "cond": arm, "zone": zone, "chain": 0, "step": step,
             "status": "ok", "eval_error": None, "inconsistencies_unified_step": unified,
             "ratchet_trips": 0, "ratchet_final": {"fires": False}, "gaming_flags": {}}
        r.update(kw)
        return r
    rows = [row("RL", "Z3", 2, ["akahu-changed-tables"], ratchet_trips=2,
                t2_reuses_logic="helper"),
            row("RL", "Z3", 1, [], ratchet_trips=1),
            row("RL", "Z3", 3, []), row("RL", "Z1", 1, None, ratchet_trips=1),
            row("R", "Z3", 2, [], t2_reuses_logic="copy"), row("R", "Z3", 1, [])]
    b = tables3.behaviour_table(rows)
    assert b["unified"]["RL"]["k"] == 1 and b["unified"]["RL"]["n"] == 3
    assert b["not_checked"]["RL"] == 1 and b["unified"]["R"]["n"] == 2
    assert b["ids"]["RL"] == {"akahu-changed-tables": 1}
    assert b["h4_fired"]["non_blind"]["k"] == 1 and b["h4_fired"]["non_blind"]["n"] == 2
    assert b["h4_success_unified"]["non_blind"] == 1
    assert b["t2_label"]["RL"]["helper"]["k"] == 1 and b["t2_label"]["R"]["copy"]["n"] == 1
    md = tables3.render_behaviour(b)
    assert "inconsistencies_unified_step" in md and "akahu-changed-tables" in md


def test_scope_sanity_with_a_fake_container(tmp_path):
    from aa.chains import load_t0, scope_sanity
    t0 = load_t0("Z2")
    (name,) = t0.tests
    seen = []

    def fake(argv, timeout):
        out = Path(next(a.split(":")[0] for a in argv if a.endswith(":/out")))
        seen.append(argv)
        assert "/refs/T1.patch" in argv[-1] and "yarn lint" not in argv[-1]
        for k in (1, 2, 3, 4):  # the reference trees change the rounding from T1 on
            (out / f"T{k}").mkdir(parents=True, exist_ok=True)
            (out / f"T{k}" / "report.json").write_text(json.dumps({"testResults": [{
                "name": "/work/actual/packages/loot-core/src/server/study3-z2/z2-inconsistencies.test.ts",
                "status": "failed", "assertionResults": [{"fullName": name, "status": "failed"}]}]}))
        return 0
    res = scope_sanity(["Z2"], conds=("R",), work=tmp_path, runner=fake, write=False)
    st = res["Z2"]["conds"]["R"]["steps"]
    assert len(seen) == 1 and res["Z2"]["all_ok"]
    assert st["T1"]["in_scope"] == [] and st["T1"]["superseded_failing"] == ["template-half-of-rounded-sum"]
