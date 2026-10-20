"""Study 3 evaluator measures (plan Task 5, spec amendment 2026-10-11b). No agent and no
Docker: real transcript snippets from runs2 (tests/fixtures/study3/transcripts), fake
eval dirs, and (where work/variants is present) real study-2 steps read from runs2,
which stays read-only."""
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from aa import chain_eval, chain_eval3, chains, config
from aa.chain_eval3 import (SourceIndex, change_blocks, classify_changes, function_spans,
                            lint_runs, lint_segments, ratchet_kind, ratchet_measures,
                            ratchet_trips, rule_cited, rule_sites_touched, t0_outcome,
                            t2_static3)
from aa.ratchet import Clone

FIX = Path(__file__).parent / "fixtures" / "study3" / "transcripts"
LOOT_SRC = "packages/loot-core/src"


def _lines(name: str) -> list[str]:
    return (FIX / name).read_text().splitlines()


# =========================================================================== lint_runs

@pytest.mark.parametrize("agent,fixture,want", [
    # yarn lint:fix; (yarn typecheck; yarn lint); timeout 100 yarn lint; a python heredoc
    # (its body mentions lint: not a run) followed by `... ; yarn lint` (a run)
    ("claude", "claude-lint.jsonl", 4),
    # grep for "lint" in package.json (no run); `yarn lint:fix; yarn lint` twice
    ("haiku", "haiku-lint.jsonl", 4),
    # two `yarn workspace @actual-app/core run lint` items (started + completed each)
    ("codex", "codex-workspace-lint.jsonl", 2),
    # `cat package.json | rg -n '"(test|lint)'`: not a run
    ("codex", "codex-rg-lint.jsonl", 0),
    # `yarn workspace ... test:node ... && yarn workspace @actual-app/core lint`
    ("codex", "codex-compound-lint.jsonl", 1),
    ("codex", "codex-lint-fix.jsonl", 1),
])
def test_lint_runs_on_real_transcripts(agent, fixture, want):
    n, segs = lint_runs(agent, _lines(fixture))
    assert n == want, segs
    assert all(re.search(r"lint", s) for s in segs)


@pytest.mark.parametrize("cmd,want", [
    ("yarn lint", 1),
    ("cd /work/actual/packages/loot-core && yarn lint 2>&1 | tail -20", 1),
    ("timeout 300 yarn lint:fix; yarn lint", 2),
    ("yarn workspace @actual-app/core run lint && git diff --check", 1),
    ("npm run lint", 1),
    ("yarn --cwd packages/loot-core lint", 1),
    ("node packages/loot-core/bin/dup-check.mjs", 1),
    ("FOO=1 yarn lint", 1),
    ('grep -n "yarn lint" package.json', 0),
    ("cat packages/loot-core/package.json | rg lint", 0),
    ("yarn linter", 0),
    ("yarn tsgo -b", 0),
    ("python3 - <<'E'\nprint('yarn lint')\nyarn lint\nE\necho done", 0),
    ("cat > notes.md <<EOF\nyarn lint\nEOF\nyarn lint", 1),
    # runs2/haiku/R/Z1/6/T3: tests backgrounded with a single `&`, then the lint
    ("(yarn workspace @actual-app/core run test > /tmp/core-test.log 2>&1; "
     "echo \"exit $?\" >> /tmp/core-test.log) & yarn lint 2>&1 | tail -20; "
     "echo LINT_EXIT=$?", 1),
    ("yarn lint &", 1),
    ("yarn lint &>/tmp/l.log & wait", 1),     # &> and 2>&1 are redirections
    ("yarn tsgo -b 2>&1 & yarn lint:fix", 1),
])
def test_lint_segments(cmd, want):
    assert len(lint_segments(cmd)) == want


def test_codex_items_counted_once_per_id():
    started = {"type": "item.started", "item": {"id": "item_1", "type": "command_execution",
                                                 "command": "/bin/bash -lc 'yarn lint'"}}
    done = {"type": "item.completed", "item": {**started["item"], "aggregated_output": "ok"}}
    lines = [json.dumps(started), json.dumps(done)]
    assert lint_runs("codex", lines)[0] == 1
    assert lint_runs("codex", [json.dumps(done)])[0] == 1  # a completed item alone


# =========================================================================== RL trace

HEADER = chain_eval3.DUP_CHECK_HEADER


def test_ratchet_trips_both_formats():
    out = f"{HEADER}\n  a.ts:1-9 ~ b.ts:3-11 (40 tokens)\nThe check passes when ..."
    claude = [json.dumps({"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": out}]}}),
        json.dumps({"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t2",
             "content": [{"type": "text", "text": "dup-check: ok"}]}]}}),
        json.dumps({"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t3",
             "content": [{"type": "text", "text": out}]}]}})]
    assert ratchet_trips("claude", claude) == 2
    codex = [json.dumps({"type": "item.completed", "item": {
        "id": "item_3", "type": "command_execution", "command": "yarn lint",
        "aggregated_output": out, "exit_code": 1}})]
    assert ratchet_trips("codex", codex) == 1
    assert ratchet_trips("codex", _lines("codex-workspace-lint.jsonl")) == 0


def test_trip_seen_through_tail_but_not_in_the_script_source():
    P = f"{LOOT_SRC}/server/budget/actions.ts"
    full = (f"{HEADER}\n  {P}:293-314 ~ {P}:331-352 (82 tokens)\n"
            f"  {P}:346-353 ~ {P}:373-380 (42 tokens)\n{chain_eval3.DUP_CHECK_TRAILER}\n")
    tail2 = "\n".join(full.splitlines()[-2:])   # `yarn lint | tail -2`: header cut
    assert chain_eval3.is_trip(tail2)
    assert chain_eval3.trip_clones(tail2) == [(P, 346, 353, P, 373, 380)]
    tail1 = full.splitlines()[-1]                # only the closing line
    assert chain_eval3.is_trip(tail1) and chain_eval3.trip_clones(tail1) == []
    assert chain_eval3.trip_kind(tail1, []) is None
    assert len(chain_eval3.trip_clones(full)) == 2
    # `cat dup-check.mjs`: the messages are quoted literals and templates, not a trip
    src = Path(config.ROOT / "substrate" / "patches" / "study3" / "rl.patch").read_text()
    src = "\n".join(ln[1:] for ln in src.splitlines() if ln.startswith("+"))
    assert HEADER in src and not chain_eval3.is_trip(src)
    assert not chain_eval3.is_trip("dup-check: ok (no duplicated code on lines changed since "
                                   "the start of this task)\n")


def test_rule_cited():
    def claude(*texts):
        return [json.dumps({"type": "assistant", "message": {"id": f"m{i}", "content": [
            {"type": "text", "text": t}]}}) for i, t in enumerate(texts)]
    cited, d = rule_cited("claude", claude(
        "The repo says: do not copy logic, so I will extract a shared function."))
    assert cited and d["rule_quoted"] and d["reuse_mentions"] >= 1
    # ordinary reuse talk (every arm does it) is detail, not a citation of the rule
    cited, d = rule_cited("claude", claude("I'll reuse the existing selection helper."))
    assert not cited and not d["rule_quoted"] and d["reuse_talk"]
    cited, d = rule_cited("claude", claude("Adding the new action next to the others."))
    assert not cited
    codex = [json.dumps({"type": "item.completed", "item": {
        "id": "item_0", "type": "agent_message", "text": "Consolidating the copies first."}}),
        json.dumps({"type": "item.completed", "item": {
            "id": "item_1", "type": "command_execution", "command": "/bin/bash -lc 'cat AGENTS.md'",
            "aggregated_output": "Do not copy logic"}})]
    cited, d = rule_cited("codex", codex)
    assert not cited and d["agents_md_explicit_read"] and d["reuse_talk"]  # tool output is not prose
    codex[0] = codex[0].replace("Consolidating the copies first.",
                                "AGENTS.md: change it in one place, so I extract it.")
    cited, d = rule_cited("codex", codex)
    assert cited and d["rule_quoted"]
    # real codex prose of a study-2 R step: no rule, no reuse words in it
    assert rule_cited("codex", _lines("codex-workspace-lint.jsonl"))[0] is False


# =========================================================================== diffs

A = f"{LOOT_SRC}/a.ts"


def _hunk_diff(path: str, body: str) -> str:
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n{body}"


def test_change_blocks_with_context_and_a_removed_double_dash_line():
    diff = _hunk_diff(A, "@@ -1,5 +1,5 @@\n ctx1\n--- old comment\n+// new comment\n ctx3\n"
                         "-gone\n ctx5\n")
    blocks = change_blocks(diff)[A]
    assert blocks[0]["old"] == [(2, "-- old comment")] and blocks[0]["new"] == [(2, "// new comment")]
    assert blocks[1] == {"old": [(4, "gone")], "new": [], "at": 4, "old_at": 4}


def test_classify_changes_added_vs_modified():
    diff = _hunk_diff(A, "@@ -2,0 +3,2 @@\n+export const x = 1;\n+export const y = 2;\n"
                         "@@ -10 +12 @@\n-  if (cat.hidden === 1) {\n"
                         "+  if (cat.hidden === 1 || cat.group_hidden === 1) {\n"
                         "@@ -20,2 +22,3 @@\n-  return a;\n-}\n+  return a + b;\n+}\n"
                         "+export function brandNew(zz: number) { return zz * 42; }\n")
    c = classify_changes(diff)
    assert c["added"][A] == {3, 4, 24}
    assert c["modified"][A] == {12, 22, 23}
    assert c["old"][A] == {10, 20, 21}


def test_changed_post_lines_and_deletion_points():
    # git -U0: old lines 3-4 deleted -> "+2,0" (after post line 2): they sat before line 3
    diff = _hunk_diff(A, "@@ -3,2 +2,0 @@\n-a\n-b\n@@ -9 +7 @@\n-c\n+d\n")
    changed, deletions = chain_eval3.changed_post_lines(diff)
    assert changed == {A: {7}} and deletions == {A: [3]}


# =========================================================================== ratchet

def _clone(a, s1, e1, b, s2, e2):
    return Clone(a, s1, e1, b, s2, e2, e1 - s1 + 1, 40)


def test_ratchet_kind():
    added = {A: {50, 51}}
    new_side = _clone(A, 1, 10, A, 45, 55)
    old_only = _clone(A, 1, 10, A, 20, 30)
    assert ratchet_kind([], added, True) is None
    assert ratchet_kind([new_side], added, False) == "adds_new_clone_side"
    assert ratchet_kind([old_only], added, True) == "touches_preexisting_only"
    assert ratchet_kind([old_only], added, False) == "modified_into_clone"


def _jscpd(out: Path, which: str, dups, rc=0):
    (out / which).mkdir(parents=True, exist_ok=True)
    (out / which / "jscpd-report.json").write_text(json.dumps({"duplicates": [
        {"lines": e1 - s1 + 1, "tokens": 40,
         "firstFile": {"name": a.split("/")[-1], "start": s1, "end": e1},
         "secondFile": {"name": b.split("/")[-1], "start": s2, "end": e2}}
        for a, s1, e1, b, s2, e2 in dups]}))
    (out / f"{which}_rc").write_text(f"{rc}\n")


def _ratchet_dir(tmp_path, *, start, post, diff, untracked="", files=(A,)):
    ev = tmp_path / "eval"
    ev.mkdir()
    _jscpd(ev, "ratchet_start", start)
    _jscpd(ev, "ratchet_post", post)
    for w in ("start", "post"):
        (ev / f"ratchet_{w}_files").write_text("\n".join(files) + "\n")
    (ev / "ratchet_diff.patch").write_text(diff)
    (ev / "ratchet_untracked.tsv").write_text(untracked)
    return ev


def test_ratchet_measures_new_clone_on_added_lines(tmp_path):
    diff = _hunk_diff(A, "@@ -40,0 +41,10 @@\n" + "".join(f"+line {i}\n" for i in range(10)))
    ev = _ratchet_dir(tmp_path, start=[], post=[(A, 1, 10, A, 41, 50)], diff=diff)
    m = ratchet_measures(ev)
    assert m["ratchet_final"]["fires"] and m["ratchet_kind"] == "adds_new_clone_side"
    assert m["ratchet_start_fires"] is False and m["ratchet_error"] is None


def test_ratchet_measures_edit_inside_a_preexisting_clone(tmp_path):
    # the rule edit changes one line inside both halves of an old clone (Z1 T1 in R)
    diff = _hunk_diff(A, "@@ -5 +5 @@\n-  if (c.hidden === 1) {\n+  if (c.hidden === 1 || g) {\n"
                         "@@ -25 +25 @@\n-  if (c.hidden === 1) {\n+  if (c.hidden === 1 || g) {\n")
    ev = _ratchet_dir(tmp_path, start=[(A, 1, 10, A, 21, 30)], post=[(A, 1, 10, A, 21, 30)],
                      diff=diff)
    m = ratchet_measures(ev)
    assert m["ratchet_final"]["fires"] and m["ratchet_kind"] == "touches_preexisting_only"
    assert m["ratchet_start_fires"] is True


def test_ratchet_measures_untracked_file_counts_as_added(tmp_path):
    new = f"{LOOT_SRC}/copy.ts"
    ev = _ratchet_dir(tmp_path, start=[], post=[(A, 1, 10, new, 3, 12)], diff="",
                      untracked=f"{new}\t14\n", files=(A, new))
    m = ratchet_measures(ev)
    assert m["ratchet_kind"] == "adds_new_clone_side" and m["ratchet_final"]["added_lines"] == 14


def test_ratchet_measures_no_change_does_not_fire_on_old_clones(tmp_path):
    ev = _ratchet_dir(tmp_path, start=[(A, 1, 10, A, 21, 30)], post=[(A, 1, 10, A, 21, 30)],
                      diff="")
    m = ratchet_measures(ev)
    assert m["ratchet_final"]["fires"] is False and m["ratchet_kind"] is None
    assert m["ratchet_start_fires"] is False


def test_line_map_post_to_start():
    # 2 lines inserted after start line 4; start line 10 modified into 3 lines
    diff = _hunk_diff(A, "@@ -4,0 +5,2 @@\n+x\n+y\n@@ -10 +12,3 @@\n-a\n+a1\n+a2\n+a3\n")
    m = chain_eval3.LineMap(diff)
    assert [m.to_old(A, n) for n in (1, 4, 7, 11)] == [1, 4, 5, 9]
    assert (m.to_old(A, 5, "lo"), m.to_old(A, 6, "hi")) == (4, 5)    # around the insertion
    assert (m.to_old(A, 12, "lo"), m.to_old(A, 14, "hi")) == (10, 10)
    assert m.to_old(A, 15) == 11 and m.to_old("other.ts", 15) == 15


def test_lines_inserted_inside_a_preexisting_clone_touch_it(tmp_path):
    # a rule check inserted inside both halves of an old pair: the post pair is the old
    # pair grown by the inserted lines (R Z1 T1's shape), not a new clone side
    ins = "+  if (rule(c)) {\n+    continue;\n+  }\n"
    diff = _hunk_diff(A, "@@ -5,0 +6,3 @@\n" + ins + "@@ -25,0 +29,3 @@\n" + ins)
    ev = _ratchet_dir(tmp_path, start=[(A, 1, 10, A, 21, 30)], post=[(A, 1, 13, A, 24, 36)],
                      diff=diff)
    m = ratchet_measures(ev)
    assert m["ratchet_final"]["fires"] and m["ratchet_final"]["added_lines"] == 6
    assert m["ratchet_kind"] == "touches_preexisting_only" and m["ratchet_start_fires"] is True
    assert m["ratchet_final"]["preexisting"] == [True]
    # RL's trip on the same tree reads the same kind (one rule for every arm)
    m2 = ratchet_measures(ev, trips=[_trip((A, 1, 13, A, 24, 36))])
    assert m2["ratchet_trip_kinds"] == ["touches_preexisting_only"]
    assert m2["ratchet_split"] == m["ratchet_kind"]


def test_pasted_copy_next_to_a_preexisting_clone_is_new(tmp_path):
    # the file already holds an old pair; the step pastes a third copy at the end
    diff = _hunk_diff(A, "@@ -60,0 +61,10 @@\n" + "".join(f"+copy {i}\n" for i in range(10)))
    ev = _ratchet_dir(tmp_path, start=[(A, 1, 10, A, 21, 30)],
                      post=[(A, 1, 10, A, 21, 30), (A, 1, 10, A, 61, 70)], diff=diff)
    m = ratchet_measures(ev)
    assert m["ratchet_kind"] == "adds_new_clone_side" and m["ratchet_start_fires"] is False
    assert [c["b_start"] for c in m["ratchet_final"]["clones"]] == [61]
    m2 = ratchet_measures(ev, trips=[_trip((A, 1, 10, A, 61, 70))])
    assert m2["ratchet_trip_kinds"] == ["adds_new_clone_side"]


@pytest.mark.parametrize("where", ["before", "after"])
def test_copy_pasted_right_against_a_preexisting_clone_side_is_new(where, tmp_path):
    # amendment 2026-10-11d: the old pair is 1-10 ~ 21-30; a third copy is inserted
    # directly before line 21 (it takes post lines 21-30, the old side moves to 31-40)
    # or directly after line 30 (post 31-40). Its lines are all added, so it maps to no
    # start line and cannot be the old side it touches.
    copy = "".join(f"+copy {i}\n" for i in range(10))
    if where == "before":
        diff = _hunk_diff(A, "@@ -20,0 +21,10 @@\n" + copy)
        post = [(A, 1, 10, A, 31, 40), (A, 1, 10, A, 21, 30)]
        new_side = 21
    else:
        diff = _hunk_diff(A, "@@ -30,0 +31,10 @@\n" + copy)
        post = [(A, 1, 10, A, 21, 30), (A, 1, 10, A, 31, 40)]
        new_side = 31
    ev = _ratchet_dir(tmp_path, start=[(A, 1, 10, A, 21, 30)], post=post, diff=diff)
    m = ratchet_measures(ev)
    assert [c["b_start"] for c in m["ratchet_final"]["clones"]] == [new_side]
    assert m["ratchet_final"]["preexisting"] == [False]
    assert m["ratchet_kind"] == "adds_new_clone_side" and m["ratchet_start_fires"] is False
    m2 = ratchet_measures(ev, trips=[_trip((A, 1, 10, A, new_side, new_side + 9))])
    assert m2["ratchet_trip_kinds"] == ["adds_new_clone_side"]
    assert m2["ratchet_split"] == "adds_new_clone_side"


def test_line_map_range_maps_start_backed_lines_only():
    # 10 lines inserted after start line 20; start line 40 modified in place
    diff = _hunk_diff(A, "@@ -20,0 +21,10 @@\n" + "".join(f"+n{i}\n" for i in range(10)) +
                      "@@ -40 +50 @@\n-  if (cat.hidden === 1) {\n+  if (cat.hidden === 1 && x) {\n")
    m = chain_eval3.LineMap(diff)
    assert m.range_to_old(A, 21, 30) is None                 # wholly added
    assert m.range_to_old(A, 25, 32) is None                 # 6 added of 8: a new copy
    assert m.range_to_old(A, 15, 24) == (15, 20)             # 6 of 10 backed: grown range
    assert m.range_to_old(A, 31, 40) == (21, 30)
    assert m.range_to_old(A, 48, 52) == (38, 42)             # the modified line maps


REAL_RATCHET = Path(__file__).parent / "fixtures" / "study3" / "ratchet_real"


def test_real_copy_step_pasted_next_to_an_old_clone_is_new(tmp_path):
    """runs2/claude/R/Z1/1/T2 (chain 0): setLastMonthSpending is inserted after start
    line 345 of actions.ts, right before set12MonthAvg, whose lines 346-368 are a side
    of an old 92-token clone with set3MonthAvg. jscpd at 35 on the post tree finds the
    new function copying set3MonthAvg (307-320 ~ 346-359, 320-329 ~ 360-369), all on
    inserted lines. Before amendment 2026-10-11d these read touches_preexisting_only
    with start_fires True (the insertion mapped onto start lines 345-346). Fixture built
    from work/variants/R + T1's patch (start) + T2's patch (post) with aa.ratchet."""
    d = REAL_RATCHET / "R-Z1-T2"
    ev = tmp_path / "eval"
    ev.mkdir()
    for w in ("start", "post"):
        (ev / f"ratchet_{w}").mkdir()
        shutil.copy(d / f"{w}.json", ev / f"ratchet_{w}" / "jscpd-report.json")
        (ev / f"ratchet_{w}_rc").write_text("0\n")
        shutil.copy(d / "files.txt", ev / f"ratchet_{w}_files")
    shutil.copy(d / "diff.patch", ev / "ratchet_diff.patch")
    (ev / "ratchet_untracked.tsv").write_text("")
    m = ratchet_measures(ev)
    assert m["ratchet_error"] is None
    final = [(c["a_start"], c["a_end"], c["b_start"], c["b_end"])
             for c in m["ratchet_final"]["clones"]]
    assert sorted(final) == [(307, 320, 346, 359), (320, 329, 360, 369)]
    assert m["ratchet_final"]["preexisting"] == [False, False]
    assert m["ratchet_kind"] == "adds_new_clone_side" and m["ratchet_start_fires"] is False
    rows = [(c["a"], c["a_start"], c["a_end"], c["b"], c["b_start"], c["b_end"])
            for c in m["ratchet_final"]["clones"]]
    rl = ratchet_measures(ev, trips=[_trip(*rows)])
    assert rl["ratchet_trip_kinds"] == ["adds_new_clone_side"]
    assert rl["ratchet_split"] == "adds_new_clone_side"


@pytest.mark.parametrize("name", ["R-Z1-T1", "R-Z3-T1", "R-Z4-T3"])
def test_real_rule_steps_edit_preexisting_copies_in_every_arm(name, tmp_path):
    """Real runs2 R rule steps (claude, chain 0): the -U0 diff and jscpd at 35 on the
    start and post trees, kept to the clones on files the step changed (rebuilt from
    runs2 + work/variants/R with aa.ratchet once). The rule edit lands inside copies the
    start tree had, so R's counterfactual and an RL trip listing the same clones both
    read touches_preexisting_only (before amendment 2026-10-11c R read
    adds_new_clone_side with start_fires False at Z1 T1)."""
    d = REAL_RATCHET / name
    ev = tmp_path / "eval"
    ev.mkdir()
    for w in ("start", "post"):
        (ev / f"ratchet_{w}").mkdir()
        shutil.copy(d / f"{w}.json", ev / f"ratchet_{w}" / "jscpd-report.json")
        (ev / f"ratchet_{w}_rc").write_text("0\n")
        shutil.copy(d / "files.txt", ev / f"ratchet_{w}_files")
    shutil.copy(d / "diff.patch", ev / "ratchet_diff.patch")
    (ev / "ratchet_untracked.tsv").write_text("")
    m = ratchet_measures(ev)
    assert m["ratchet_error"] is None and m["ratchet_final"]["fires"]
    assert m["ratchet_kind"] == "touches_preexisting_only"
    assert m["ratchet_start_fires"] is True
    final = [(c["a"], c["a_start"], c["a_end"], c["b"], c["b_start"], c["b_end"])
             for c in m["ratchet_final"]["clones"]]
    rl = ratchet_measures(ev, trips=[_trip(*final)])
    assert rl["ratchet_trip_kinds"] == ["touches_preexisting_only"]
    assert rl["ratchet_split"] == m["ratchet_split"] == "touches_preexisting_only"


def test_ratchet_measures_missing_scan(tmp_path):
    ev = _ratchet_dir(tmp_path, start=[], post=[], diff="")
    (ev / "ratchet_post_rc").write_text("124\n")
    m = ratchet_measures(ev)
    assert m["ratchet_final"] is None and m["ratchet_error"] == "post_scan"


# =========================================================================== JS functions

TS = """\
import x from 'y';

export async function linkOne({
  id,
  fileId,
}: {
  id: string;
  fileId?: string;
}): Promise<{ ok: boolean }> {
  const s = `Account with ID ${id} not found`;
  if (!id) {
    throw new Error(s);
  }
  return shared(id, '{');
}

const shared = async (id: string, brace: string) => {
  return helperTwo(id) + brace;
};

const helperTwo = id => id.length;

function overload(a: string): string;
function overload(a: unknown) {
  return String(a);
}
"""


def test_function_spans():
    sp = function_spans(TS)
    assert sp["linkOne"] == [(3, 15)]
    assert sp["shared"] == [(17, 19)]
    assert sp["helperTwo"] == [(21, 21)]
    assert sp["overload"] == [(24, 26)]
    idx = SourceIndex({A: TS})
    assert idx.body_calls("linkOne") == {"shared", "Error"}
    assert idx.body_calls("shared") == {"helperTwo"}


def test_function_spans_on_the_real_variant():
    f = config.WORK / "variants" / "R" / LOOT_SRC / "shared" / "schedules.ts"
    if not f.exists():
        pytest.skip("work/variants/R missing")
    sp = function_spans(f.read_text())
    lines = f.read_text().splitlines()
    for name in ("getNextDate", "recurConfigToRSchedule", "getDateWithSkippedWeekend"):
        (s, e), = sp[name]
        assert name in lines[s - 1] and lines[e - 1].startswith("}"), name


# =========================================================================== T2 / rule

SITES = {"sites": [{"id": "one", "function": "setOne"}, {"id": "two", "function": "setTwo (x)"}]}
MARKERS = [r"hidden\s*===\s*1"]
F = f"{LOOT_SRC}/server/budget/actions.ts"

BASE = """\
function pick(cats) {
  return cats.filter(c => !(c.hidden === 1));
}

export async function setOne(cats) {
  for (const c of pick(cats)) {
    write(c);
  }
}

export async function setTwo(cats) {
  for (const c of pick(cats)) {
    write(c);
  }
}
"""


def _added_diff(path: str, old: str, new: str) -> str:
    import difflib
    return f"diff --git a/{path} b/{path}\n" + "".join(difflib.unified_diff(
        old.splitlines(True), new.splitlines(True), f"a/{path}", f"b/{path}"))


def test_t2_static3_helper_copy_none():
    reuse = BASE + "\nexport async function setThree(cats) {\n  for (const c of pick(cats)) {\n" \
                   "    write(c);\n  }\n}\n"
    lab, d = t2_static3(SourceIndex({F: reuse}), _added_diff(F, BASE, reuse), SITES, MARKERS)
    assert lab == "helper" and d["shared_functions"] == ["pick"]
    copy = BASE + "\nexport async function setThree(cats) {\n  for (const c of cats) {\n" \
                  "    if (c.hidden === 1) continue;\n    write(c);\n  }\n}\n"
    lab, d = t2_static3(SourceIndex({F: copy}), _added_diff(F, BASE, copy), SITES, MARKERS)
    assert lab == "copy" and d["markers"]
    calls_site = BASE + "\nexport async function setThree(cats) {\n  return setOne(cats);\n}\n"
    lab, d = t2_static3(SourceIndex({F: calls_site}), _added_diff(F, BASE, calls_site), SITES,
                        MARKERS)
    assert lab == "copy" and d["calls_copy_sites"] == ["setOne"]
    other = BASE + "\nexport async function setThree(cats) {\n  return cats.length;\n}\n"
    lab, d = t2_static3(SourceIndex({F: other}), _added_diff(F, BASE, other), SITES, MARKERS)
    assert lab is None and d["reason"] == "no_shared_call_no_marker"
    assert t2_static3(SourceIndex({F: BASE}), "", SITES, MARKERS)[0] is None
    # a function the spec excludes (Z4's shared date arithmetic) is not the decision
    lab, _ = t2_static3(SourceIndex({F: reuse}), _added_diff(F, BASE, reuse), SITES, MARKERS,
                        not_decision=("pick",))
    assert lab is None


def test_rule_sites_touched():
    one_place = BASE.replace("!(c.hidden === 1)", "!(c.hidden === 1 || c.fixed)")
    n, d = rule_sites_touched(SourceIndex({F: one_place}), _added_diff(F, BASE, one_place), SITES)
    assert n == 1 and d["helpers"] == ["pick"] and d["sites"] == []
    everywhere = BASE.replace("    write(c);", "    if (c.fixed) continue;\n    write(c);")
    n, d = rule_sites_touched(SourceIndex({F: everywhere}), _added_diff(F, BASE, everywhere), SITES)
    assert n == 2 and d["sites"] == ["setOne", "setTwo"]
    nested = BASE.replace("export async function setOne(cats) {\n",
                          "export async function setOne(cats) {\n  const keep = c => c.ok;\n")
    nested2 = nested.replace("const keep = c => c.ok;", "const keep = c => c.ok && !c.fixed;")
    n, d = rule_sites_touched(SourceIndex({F: nested2}), _added_diff(F, nested, nested2), SITES)
    assert d["functions"] == ["setOne"]  # `keep` is part of setOne


# ---- the same measures on real study-2 steps (runs2 read-only, work/variants) ---------

def _post_files(step: Path, cond: str, dirs: list[str], tmp: Path) -> dict[str, str]:
    var = config.WORK / "variants" / cond
    touched = set()
    patches = [step / "eval" / "pre_image.patch", step / "diff.patch"]
    for p in patches:
        touched |= set(re.findall(r"^diff --git a/(\S+) b/", p.read_text(), re.M))
    touched = {f for f in touched if f.startswith(LOOT_SRC + "/")}
    for d in dirs:
        shutil.copytree(var / d, tmp / d, dirs_exist_ok=True)
    for f in touched:
        if (var / f).exists() and not (tmp / f).exists():
            (tmp / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(var / f, tmp / f)
    inc = [f"--include={d}/*" for d in dirs] + [f"--include={f}" for f in touched]
    for p in patches:
        if p.read_text().strip():
            subprocess.run(["git", "apply", "--whitespace=nowarn", *inc, str(p.resolve())],
                           cwd=tmp, check=True, capture_output=True)
    return {f.relative_to(tmp).as_posix(): f.read_text() for f in tmp.rglob("*") if f.is_file()}


@pytest.mark.parametrize("step,want", [
    ("claude/F/Z1/0/T2", "helper"),   # getBulkBudgetCategories / averageToBudget
    ("claude/F/Z3/0/T2", "helper"),   # linkBankSyncAccount
    ("claude/R/Z3/0/T2", "copy"),     # the link sequence pasted
    ("claude/R/Z1/0/T2", "copy"),     # category selection re-written
    ("claude/R/Z2/0/T2", "helper"),   # getScheduledAmount -> the agent's T1 helper
])
def test_t2_static3_on_real_study2_steps(step, want, tmp_path):
    sd = Path("runs2") / step
    if not (config.WORK / "variants" / "R").exists() or not (sd / "eval" / "step.patch").exists():
        pytest.skip("work/variants or runs2 missing")
    _, cond, zone, _, _ = sd.parts[-5:]
    chain = chain_eval.load_chain(zone)
    dirs = sorted({f.rsplit("/", 1)[0] for f in chain.files_for(cond)})
    idx = SourceIndex(_post_files(sd, cond, dirs, tmp_path))
    lab, d = t2_static3(idx, (sd / "eval" / "step.patch").read_text(),
                        chains.load_t0(zone).sites, chain.t2_reuse["markers"],
                        chain_eval3.T2_NOT_DECISION.get(zone, ()))
    assert lab == want, d


@pytest.mark.parametrize("step,want", [
    ("claude/R/Z4/1/T1", ["recurConfigToRSchedule"]),          # the rule in one function
    ("claude/R/Z3/0/T1", ["linkGoCardlessAccount", "linkSimpleFinAccount", "linkPluggyAiAccount",
                          "linkAkahuAccount", "linkEnableBankingAccount",
                          "assertBankAccountNotLinked"]),
])
def test_rule_sites_touched_on_real_study2_steps(step, want, tmp_path):
    sd = Path("runs2") / step
    if not (config.WORK / "variants" / "R").exists() or not (sd / "eval" / "step.patch").exists():
        pytest.skip("work/variants or runs2 missing")
    _, cond, zone, _, _ = sd.parts[-5:]
    chain = chain_eval.load_chain(zone)
    dirs = sorted({f.rsplit("/", 1)[0] for f in chain.files_for(cond)})
    idx = SourceIndex(_post_files(sd, cond, dirs, tmp_path))
    n, d = rule_sites_touched(idx, (sd / "eval" / "step.patch").read_text(),
                              chains.load_t0(zone).sites)
    assert d["functions"] == want and n == len(want)


def test_only_z4_date_arithmetic_is_base_shared_with_the_zone_decision():
    """T2_NOT_DECISION (spec section 3) is exactly the set of functions untouched R
    already shares among >= 2 copy sites whose body carries a zone marker."""
    if not (config.WORK / "variants" / "R").exists():
        pytest.skip("work/variants/R missing")
    found = {}
    for zone in ("Z1", "Z2", "Z3", "Z4"):
        chain = chain_eval.load_chain(zone)
        var = config.WORK / "variants" / "R"
        idx = SourceIndex({f: (var / f).read_text() for f in chain.files_for("R")})
        sites = chain_eval3.site_names(chains.load_t0(zone).sites)
        assert all(s in idx.defs for s in sites), zone
        reach = [chain_eval3._reach(idx, idx.body_calls(s), set(sites)) for s in sites]
        rx = [re.compile(m) for m in chain.t2_reuse["markers"]]
        shared = {f for f in set().union(*reach) if sum(f in r for r in reach) >= 2
                  and any(r.search(idx.body(f)) for r in rx)}
        if shared:
            found[zone] = tuple(sorted(shared))
    assert found == chain_eval3.T2_NOT_DECISION


# =========================================================================== T0 outcome

def _probe_doc(rows_by_cat: dict[str, int], template_val: int = 1) -> dict:
    case = {"ok": [{"category": c, "amount": a} for c, a in rows_by_cat.items()]}
    return {"failed": [], "passed": 2,
            "db": {"Z1/envelope/setZero": case, "Z3/link/gocardless": {"ok": [1]}},
            "template": {"Z2/range": {"ok": [template_val]}}}


def _t0_eval_dir(tmp_path: Path, doc: dict, tests: dict | None, rcs=None) -> Path:
    ev = tmp_path / "eval"
    (ev / "probe").mkdir(parents=True)
    for name in ("db", "template"):
        (ev / "probe" / f"{name}.json").write_text(json.dumps(doc[name]))
    (ev / "probe" / "report.json").write_text(json.dumps({"testResults": [{
        "name": "/work/actual/packages/loot-core/src/server/aa-study2-probe-db.test.ts",
        "status": "passed", "assertionResults": [{"fullName": "probe", "status": "passed"}]}]}))
    if tests is not None:
        (ev / "tests.json").write_text(json.dumps({"testResults": [{
            "name": "/work/actual/packages/loot-core/src/server/t0.test.ts", "status": "passed",
            "assertionResults": [{"fullName": n, "status": s} for n, s in tests.items()]}]}))
    for k, v in (rcs or {"typecheck": 0, "typecheck_full": 0, "lint": 0, "lint_root": 0}).items():
        (ev / f"{k}_rc").write_text(f"{v}\n")
    return ev


REF = {"probe": _probe_doc({"c-food": -100, "c-orphan": 0}), "suite": None}


def test_t0_outcome_probe_exclusions_respected(tmp_path):
    """Review Focus 4 with the registered exclusions (tasks3/probe-exclusions.json): a
    change confined to the excluded missing-group category (c-orphan) is dropped; the
    same case changing for a real category is not."""
    t0 = chains.load_t0("Z1")
    ex = chains.load_probe_exclusions()
    name = next(iter(t0.tests))
    ok_tests = {name: "passed"}
    only_orphan = _t0_eval_dir(tmp_path / "a", _probe_doc({"c-food": -100, "c-orphan": 5}),
                               ok_tests)
    o = t0_outcome(only_orphan, t0, REF, ex)
    assert o["probe_changed_raw"] == ["db:Z1/envelope/setZero"]
    assert o["probe_changed_cases"] == [] and o["probe_unchanged"] is True
    assert o["inconsistencies_unified"] == []
    real = _t0_eval_dir(tmp_path / "b", _probe_doc({"c-food": -90, "c-orphan": 0}), ok_tests)
    o = t0_outcome(real, t0, REF, ex)
    assert o["probe_changed_cases"] == ["db:Z1/envelope/setZero"] and not o["probe_unchanged"]
    # an exclusion never hides a case it does not name
    other = _t0_eval_dir(tmp_path / "c", _probe_doc({"c-food": -100, "c-orphan": 0}, 2), ok_tests)
    assert t0_outcome(other, t0, REF, ex)["probe_changed_cases"] == ["template:Z2/range"]


def test_t0_outcome_unified_inconsistency_and_missing_tests(tmp_path):
    t0 = chains.load_t0("Z3")
    ex = chains.load_probe_exclusions()
    tests = {n: "passed" for n in t0.tests}
    flip = next(n for n, i in t0.tests.items() if i == "akahu-changed-tables")
    o = t0_outcome(_t0_eval_dir(tmp_path / "a", REF["probe"], {**tests, flip: "failed"}), t0,
                   REF, ex)
    assert o["inconsistencies_unified"] == ["akahu-changed-tables"]
    assert o["probe_unchanged"] is True and o["typecheck_ok"] is True
    o = t0_outcome(_t0_eval_dir(tmp_path / "b", REF["probe"], None), t0, REF, ex)
    assert o["inconsistencies_unified"] == sorted(set(t0.tests.values()))  # no report
    # Z4 has no inconsistency tests: nothing to unify
    o = t0_outcome(_t0_eval_dir(tmp_path / "c", REF["probe"], None), chains.load_t0("Z4"), REF, ex)
    assert o["inconsistencies_unified"] == [] and o["t0_tests"] == {}


# =========================================================================== eval script

def test_study3_script_order_and_switches():
    plan = {"from": "image", "patches": ["T1/diff.patch"]}
    s = chain_eval.chain_eval_script("T2", plan, agent_tree="diff", hidden_tests=["h.test.ts"],
                                     zone_files=[F], study3=True)
    i = {k: s.index(k) for k in ("/out/start_tree_fresh", "jscpd_pre", "ratchet_start",
                                 "/chain/T2/diff.patch", "ratchet_post", "/out/zone_post",
                                 "yarn lint", "vitest_rc")}
    assert i["/out/start_tree_fresh"] < i["jscpd_pre"] < i["ratchet_start"] < i["/chain/T2/diff.patch"]
    assert i["/chain/T2/diff.patch"] < i["ratchet_post"] < i["/out/zone_post"] < i["yarn lint"] < i["vitest_rc"]
    assert f"{chain_eval3.START_GIT_ENV} timeout" in s  # lint sees the step's start commit
    assert "tsgo -b > /out/typecheck.log" in s
    quick = chain_eval.chain_eval_script("T2", plan, agent_tree="diff", hidden_tests=["h.test.ts"],
                                         zone_files=[F], study3=True, tests=False)
    assert "/out/vitest_rc" not in quick and "--reporter=json" not in quick and quick.rstrip().endswith("echo done > /out/eval_done")
    study2 = chain_eval.chain_eval_script("T2", plan, agent_tree="diff",
                                          hidden_tests=["h.test.ts"], zone_files=[F])
    assert "aa-start.git" not in study2 and "ratchet" not in study2


def test_t0_script_runs_the_t0_reference_checks_in_order():
    plan = {"from": "image", "patches": []}
    h = f"{LOOT_SRC}/server/t0.test.ts"
    s = chain_eval.chain_eval_script("T0", plan, agent_tree="diff", hidden_tests=[h],
                                     zone_files=[F], t0=True)
    order = ["/out/start_tree_fresh", "ratchet_post", "/out/typecheck_rc", "/out/typecheck_full_rc",
             "/out/lint_root_rc", "/out/lint_rc", "/out/related_files", "test_infra_restore",
             "vitest related", "hidden_restore", "/out/tests.json", "/probe/", "/out/probe/rc",
             "eval_done"]
    pos = [s.index(k) for k in order]
    assert pos == sorted(pos), list(zip(order, pos))
    assert s.count(f"{chain_eval3.START_GIT_ENV} timeout") == 2  # both lints
    assert "/out/vitest_rc" not in s
    # Z4: no T0 tests -> no hidden restore, no tests run (an empty vitest list = whole suite)
    z4 = chain_eval.chain_eval_script("T0", plan, agent_tree="diff", hidden_tests=[],
                                      zone_files=[F], t0=True)
    assert "/out/tests.json" not in z4 and "hidden_restore" not in z4 and "/probe/" in z4
    for piece in (chains.t0_typecheck_lines(), chains.t0_probe_lines()):
        assert all(line in s for line in piece)  # aa chain t0-reference's own commands


FAKE_YARN3 = r"""#!/bin/bash
case "$1" in
  lint)
    root=$(git rev-list --max-parents=0 HEAD)
    { git log -1 --format=%s "$root"; git diff --name-only "$root"; } > "$AA_OUT/lint_git"
    exit 0;;
  tsgo) exit 0;;
  vitest)
    for a in "$@"; do case $a in --outputFile=*) OUT=${a#--outputFile=};; esac; done
    printf '{"testResults":[]}' > "$OUT"; exit 0;;
esac
exit 9
"""
FAKE_JSCPD3 = r"""#!/bin/bash
out=""
while [ $# -gt 0 ]; do case $1 in --output) out=$2; shift 2;; --min-tokens|--reporters) shift 2;; *) shift;; esac; done
mkdir -p "$out"; printf '{"duplicates":[]}' > "$out/jscpd-report.json"
"""


@pytest.mark.skipif(shutil.which("git") is None or shutil.which("node") is None,
                    reason="needs git and node")
def test_real_study3_script_start_commit_is_the_steps_own_start(tmp_path):
    """T2 of a chain carrying T1's diff: lint and the ratchet see one root commit named
    `start` at T2's start tree (T1's change is in it, not in the diff), never the
    image history; its tree id is what the runner's fresh repository gives."""
    from test_chain_eval import _exe, _git, _image_repo, _record, ZONE_FILES, hidden_path
    repo = tmp_path / "actual"
    loot = repo / "packages/loot-core"
    _image_repo(repo, ZONE_FILES)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "image")

    def t1():
        (loot / "src/server/budget/actions.ts").write_text("export const a = 2;\n")
    t1_diff, _ = _record(repo, t1)
    _git(repo, "commit", "-qm", "t1")
    runner = tmp_path / "runner"  # the runner's start of T2: a fresh repository of the tree
    shutil.copytree(repo, runner, ignore=shutil.ignore_patterns(".git"))
    _git(runner, "init", "-q", "-b", "main")
    _git(runner, "add", "-A")
    _git(runner, "commit", "-qm", "start")
    runner_start = _git(runner, "rev-parse", "HEAD^{tree}").strip()

    def t2():
        (loot / "src/shared/schedules.ts").write_text("export const s = 1;\nexport const t = 2;\n")
        (loot / "src/server/budget/copy.ts").write_text("a\nb\nc")
    t2_diff, _ = _record(repo, t2)
    _git(repo, "reset", "-q", "--hard", "HEAD~1")
    _git(repo, "reset", "-q", "--soft", "HEAD~1")
    _git(repo, "reset", "-q")
    cdir = tmp_path / "chain"
    for sid, diff in (("T1", t1_diff), ("T2", t2_diff)):
        (cdir / sid).mkdir(parents=True)
        (cdir / sid / "diff.patch").write_text(diff)
    out = tmp_path / "out"
    for k in (1, 2):
        (out / "hidden_src" / hidden_path(k)).parent.mkdir(parents=True, exist_ok=True)
        (out / "hidden_src" / hidden_path(k)).write_text(f"// HIDDEN T{k}\n")
    script = chain_eval.chain_eval_script(
        "T2", {"from": "image", "patches": ["T1/diff.patch"]}, agent_tree="diff",
        hidden_tests=[hidden_path(1), hidden_path(2)], zone_files=[ZONE_SRC3], study3=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _exe(bin_dir / "yarn", FAKE_YARN3)
    _exe(bin_dir / "jscpd", FAKE_JSCPD3)
    _exe(bin_dir / "timeout", '#!/bin/bash\nshift\nexec "$@"\n')
    stage = tmp_path / "stage"
    mounts = {"/work/actual": str(repo), "/chain/": f"{cdir}/",
              "/checker/": f"{chain_eval.SEED_SRC.parent}/", "/out": str(out),
              chain_eval3.START_GIT_DIR: str(tmp_path / "start.git"),
              chain_eval3.RATCHET_STAGE: str(stage)}
    script = re.sub("|".join(re.escape(k) for k in mounts), lambda m: mounts[m.group(0)], script)
    import os
    proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                          env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}",
                               "AA_OUT": str(out)})
    assert proc.returncode == 0, proc.stderr
    assert not (out / "eval_error").exists(), (out / "apply.log").read_text()
    assert (out / "start_tree_fresh").read_text().strip() == runner_start
    subject, *changed = (out / "lint_git").read_text().split()
    assert subject == "start"
    assert changed == ["packages/loot-core/src/shared/schedules.ts"]  # T2's tracked change only
    diff = (out / "ratchet_diff.patch").read_text()
    assert "export const t = 2;" in diff and "export const a = 2;" not in diff
    assert (out / "ratchet_untracked.tsv").read_text() == \
        "packages/loot-core/src/server/budget/copy.ts\t3\n"
    assert "packages/loot-core/src/server/budget/copy.ts" in \
        (out / "ratchet_post_files").read_text().split()
    assert (out / "ratchet_start_rc").read_text().strip() == "0"
    dumped = {p.relative_to(out / "zone_post").as_posix() for p in (out / "zone_post").rglob("*")
              if p.is_file()}
    assert {ZONE_SRC3, "packages/loot-core/src/server/budget/copy.ts"} <= dumped
    m = ratchet_measures(out)
    assert m["ratchet_error"] is None and m["ratchet_final"]["fires"] is False
    # the image repository the rest of the evaluation uses is untouched
    assert _git(repo, "log", "-1", "--format=%s").strip() == "evalbase"


ZONE_SRC3 = f"{LOOT_SRC}/server/budget/actions.ts"


# =========================================================================== evaluate_step

def _t0_tasks(root: Path, zone: str = "Z1") -> Path:
    d = root / zone / "T0"
    d.mkdir(parents=True)
    (d / "statement.md").write_text("Keep it in one place.\n")
    (d / "consumers.json").write_text("{}")
    (d / "sites.json").write_text(json.dumps({"zone": zone, "sites": [
        {"id": "copy", "function": "copyPreviousMonth"}, {"id": "zero", "function": "setZero"}]}))
    (root / "probe-exclusions.json").write_text(json.dumps({"exclusions": []}))
    return root


ZONE_POST_BEFORE = """\
export async function copyPreviousMonth() {
  if (x.hidden === 1) return;
}

export async function setZero() {
  if (x.hidden === 1) return;
}
"""


def _study3_executor(*, post_text: str, step_patch: str, ratchet_post=(), lint_rc=0,
                     calls=None, t0=None):
    from test_chain_eval import _write_jscpd

    def run(argv, timeout):
        if calls is not None:
            calls.append(argv)
        out = Path(next(a.split(":")[0] for a in argv if a.endswith(":/out")))
        for k, v in (("start_tree", "s" * 40), ("post_tree", "p" * 40),
                     ("start_tree_fresh", "s" * 40), ("start_commit", "c" * 40)):
            (out / k).write_text(v + "\n")
        (out / "pre_image.patch").write_text("")
        (out / "diff_applied").write_text("done\n")
        (out / "step.patch").write_text(step_patch)
        (out / "post_tree.patch").write_text(step_patch)
        _write_jscpd(out, "jscpd_pre", [])
        _write_jscpd(out, "jscpd_post", [])
        _jscpd(out, "ratchet_start", [])
        _jscpd(out, "ratchet_post", list(ratchet_post))
        for w in ("start", "post"):
            (out / f"ratchet_{w}_files").write_text(F + "\n")
        (out / "ratchet_diff.patch").write_text(step_patch)
        (out / "ratchet_untracked.tsv").write_text("")
        (out / "zone_post" / F).parent.mkdir(parents=True)
        (out / "zone_post" / F).write_text(post_text)
        (out / "lint_rc").write_text(f"{lint_rc}\n")
        (out / "typecheck_rc").write_text("0\n")
        if t0 is not None:
            t0(out)
        else:
            (out / "report.json").write_text(json.dumps({"testResults": []}))
        (out / "clean_done").write_text("done\n")
        (out / "eval_done").write_text("done\n")
        return 0
    return run


def test_study3_step_fields_and_rl_flags_propagated(tmp_path):
    from test_chain_eval import make_chain, make_step
    make_chain(tmp_path / "tasks2", zone_files=[F])
    t0root = _t0_tasks(tmp_path / "tasks3")
    post = ZONE_POST_BEFORE.replace("x.hidden === 1)", "x.hidden === 1 || x.fixed)") \
        + "// jscpd:ignore-start\n"
    patch = _added_diff(F, ZONE_POST_BEFORE, post)
    sd = make_step(tmp_path / "runs3", step="T1", cond="RL", diff=patch)
    meta = json.loads((sd / "agent.json").read_text())
    meta.update(study=3, start_commit="c" * 40, start_commit_after="d" * 40,
                start_commit_ancestor=False)
    (sd / "agent.json").write_text(json.dumps(meta))
    (sd / "transcript.jsonl").write_text("\n".join(_lines("claude-lint.jsonl")) + "\n")
    calls = []
    r = chain_eval.evaluate_step(sd, tasks_root=tmp_path / "tasks2", t0_root=t0root,
                                 execute=_study3_executor(post_text=post, step_patch=patch,
                                                          ratchet_post=[(F, 1, 3, F, 5, 7)],
                                                          lint_rc=1, calls=calls))
    assert r["study"] == 3 and r["lint_ok"] is False and r["lint_runs"] == 4
    assert set(r["gaming_flags"]) == {"jscpd_ignore", "start_commit_rewritten"}
    # the rule edit modified a line in each function; the start tree had no such clone
    assert r["ratchet_final"]["fires"] and r["ratchet_kind"] == "modified_into_clone"
    assert r["ratchet_start_fires"] is False
    assert r["rule_sites_touched"] == 2 and r["rule_sites_detail"]["sites"] == [
        "copyPreviousMonth", "setZero"]
    assert r["tree_check"]["start_fresh"] is True
    assert r["t2_reuses_logic"] is None  # not a consumer step
    assert "aa-actual:RL" in calls[0] and "aa-start.git" in calls[0][-1]
    assert json.loads((sd / "result.json").read_text())["ratchet_kind"] == r["ratchet_kind"]


def test_gaming_flags_read_the_evaluators_step_patch_on_a_tree_fallback(tmp_path):
    """On a tree.tar fallback step the agent's diff.patch did not reproduce its tree
    (here it misses the dup-check edit); the evaluator's step.patch (start -> agent
    tree) has it, so the flag is raised."""
    from aa.static3 import DUP_CHECK_SCRIPT
    from test_chain_eval import make_chain, make_step
    make_chain(tmp_path / "tasks2", zone_files=[F])
    t0root = _t0_tasks(tmp_path / "tasks3")
    zone = _added_diff(F, ZONE_POST_BEFORE, ZONE_POST_BEFORE + "// rule\n")
    script = _added_diff(DUP_CHECK_SCRIPT, "const MIN = 35;\n", "const MIN = 900;\n")
    sd = make_step(tmp_path / "runs3", step="T1", cond="RL", diff=zone)
    (sd / "diff_ok").unlink(missing_ok=True)
    (sd / "tree.tar").write_bytes(b"")
    meta = json.loads((sd / "agent.json").read_text())
    meta.update(study=3)
    (sd / "agent.json").write_text(json.dumps(meta))
    r = chain_eval.evaluate_step(sd, tasks_root=tmp_path / "tasks2", t0_root=t0root,
                                 execute=_study3_executor(post_text=ZONE_POST_BEFORE,
                                                          step_patch=zone + script))
    assert r["gaming_flags"].get("dup_check_script") == [DUP_CHECK_SCRIPT]


def test_study3_arm_reads_r_zone_files(tmp_path):
    from test_chain_eval import make_chain
    make_chain(tmp_path / "t2", zone_files={"R": ["server/budget/actions.ts"],
                                            "F": ["server/f.ts"]})
    c = chain_eval.load_chain("Z1", tmp_path / "t2")
    for arm in ("RG", "RL", "RC"):
        assert c.files_for(arm) == c.files_for("R") == [F]


@pytest.mark.parametrize("arm", ["R", "RG", "RL", "RC"])
def test_study3_t2_label_without_static3_is_none_and_study2_label_is_r_based(arm, tmp_path):
    """The study-2 T2 label of a study-3 arm is computed on R's helper list (RG/RL/RC
    read as R would), and it never stands in for the study-3 label: a step static3
    cannot read (here: not evaluated) gets t2_reuses_logic None."""
    from test_chain_eval import make_chain, make_step
    make_chain(tmp_path / "tasks2", zone_files=[F])
    patch = _added_diff(F, "export const a = 1;\n",
                        "export const a = 1;\nconst xs = cats.filter(c => !c.is_income);\n")
    sd = make_step(tmp_path / "runs3", step="T2", cond=arm, diff=patch, status="usage_limit")
    meta = json.loads((sd / "agent.json").read_text())
    meta["study"] = 3
    (sd / "agent.json").write_text(json.dumps(meta))
    r = chain_eval.evaluate_step(sd, tasks_root=tmp_path / "tasks2",
                                 t0_root=_t0_tasks(tmp_path / "tasks3"))
    assert r["study"] == 3 and r["t2_reuses_logic"] is None
    assert r["t2_reuse_detail"]["reason"] == "static3_not_run"
    assert r["t2_reuse_detail"]["study2_label"] == "copy"


def test_study2_step_gets_no_study3_fields(tmp_path):
    from test_chain_eval import fake_executor, make_chain, make_step
    make_chain(tmp_path / "tasks2")
    sd = make_step(tmp_path / "runs2", step="T1", cond="R")
    r = chain_eval.evaluate_step(sd, tasks_root=tmp_path / "tasks2",
                                 execute=fake_executor(rep={"testResults": []}))
    assert "ratchet_final" not in r and "lint_runs" not in r


def _t0_step(runs: Path, diff: str, zone: str = "Z1", status: str = "ok") -> Path:
    d = runs / "claude" / "RC" / zone / "0" / "T0"
    d.mkdir(parents=True)
    plan = {"from": "image", "patches": [], "expected_start_tree": None}
    (d / "start.json").write_text(json.dumps(plan))
    (d / "agent.json").write_text(json.dumps({
        "agent": "claude", "cond": "RC", "zone": zone, "chain": 0, "step": "T0", "study": 3,
        "step_index": None, "status": status, "wall_s": 600.0, "carry": plan,
        "usage": {"input_tokens": 900, "output_tokens": 90, "turns": 30, "tool_calls": 20}}))
    (d / "diff.patch").write_text(diff)
    (d / "diff_ok").write_text("")
    (d / "start_tree").write_text("s" * 40 + "\n")
    (d / "post_tree").write_text("p" * 40 + "\n")
    (d / "transcript.jsonl").write_text("")
    return d


def _t0_writer(probe_doc: dict, tests: dict):
    def write(out: Path):
        (out / "probe").mkdir()
        for name in ("db", "template"):
            (out / "probe" / f"{name}.json").write_text(json.dumps(probe_doc[name]))
        (out / "probe" / "report.json").write_text(json.dumps({"testResults": [{
            "name": "/work/actual/packages/loot-core/src/server/aa-study2-probe-db.test.ts",
            "status": "passed", "assertionResults": [{"fullName": "p", "status": "passed"}]}]}))
        (out / "tests.json").write_text(json.dumps({"testResults": [{
            "name": "/work/actual/packages/loot-core/src/server/t0.test.ts", "status": "passed",
            "assertionResults": [{"fullName": n, "status": s} for n, s in tests.items()]}]}))
        for k in ("typecheck_full", "lint_root"):
            (out / f"{k}_rc").write_text("0\n")
        (out / "related_files").write_text("src/server/budget/actions.ts\n")
        (out / "related_rc").write_text("0\n")
        (out / "related.json").write_text(json.dumps({"testResults": [{
            "name": "/work/actual/packages/loot-core/src/server/budget/actions.test.ts",
            "status": "passed", "assertionResults": [{"fullName": "a", "status": "passed"}]}]}))
    return write


SUITE = {"testResults": [{
    "name": "/work/actual/packages/loot-core/src/server/budget/actions.test.ts",
    "status": "passed", "assertionResults": [{"fullName": "a", "status": "passed"}]}]}


def test_t0_step_with_a_seeded_unified_consolidation(tmp_path):
    """Plan Task 5: T0 with the registered seeded unified patch -> inconsistencies_unified
    non-empty, not correct; the probe change is reported; packet with sites.json."""
    from test_chain_eval import make_chain
    make_chain(tmp_path / "tasks2", zone_files=[F])
    t0 = chains.load_t0("Z1")
    seed = t0.seed_patch("z1-setzero-skips-hidden").read_text()
    sd = _t0_step(tmp_path / "runs3", seed)
    name = next(iter(t0.tests))
    calls = []
    ref = {"probe": _probe_doc({"c-food": -100, "c-orphan": 0}), "suite": SUITE}
    r = chain_eval.evaluate_step(
        sd, tasks_root=tmp_path / "tasks2", t0_reference=ref,
        execute=_study3_executor(post_text=ZONE_POST_BEFORE, step_patch=seed, calls=calls,
                                 t0=_t0_writer(_probe_doc({"c-food": 0, "c-orphan": 0}),
                                               {name: "failed"})))
    assert r["step"] == 0 and r["step_id"] == "T0" and r["kind"] == "refactor"
    assert r["inconsistencies_unified"] == ["setzero-writes-hidden"]
    assert r["probe_changed_cases"] == ["db:Z1/envelope/setZero"]
    assert r["correct"] is False and r["eval_error"] is None
    assert r["typecheck_ok"] and r["typecheck_full_ok"] and r["lint_root_ok"] and r["related_ok"]
    assert r["duplication_pre"] is not None and r["duplication_post"] is not None
    assert r["ratchet_final"] is not None and r["study"] == 3
    assert any(a == f"{chain_eval3.PROBE_MOUNT}" for a in calls[0])
    pk = sd / r["t0_packet"]
    assert json.loads((pk / "sites.json").read_text()) == t0.sites
    assert (pk / "diff.patch").read_text() == seed and (pk / "statement.md").read_text() == t0.statement()


def test_t0_step_clean_refactor_is_correct(tmp_path):
    from test_chain_eval import make_chain
    make_chain(tmp_path / "tasks2", zone_files=[F])
    t0 = chains.load_t0("Z1")
    patch = _added_diff(F, ZONE_POST_BEFORE, ZONE_POST_BEFORE + "// one place\n")
    sd = _t0_step(tmp_path / "runs3", patch)
    ref = {"probe": _probe_doc({"c-food": -100, "c-orphan": 0}), "suite": SUITE}
    r = chain_eval.evaluate_step(
        sd, tasks_root=tmp_path / "tasks2", t0_reference=lambda: ref,
        execute=_study3_executor(post_text=ZONE_POST_BEFORE, step_patch=patch,
                                 t0=_t0_writer(_probe_doc({"c-food": -100, "c-orphan": 7}),
                                               {n: "passed" for n in t0.tests})))
    # the only probe change is the excluded missing-group row (Review Focus 4)
    assert r["probe_changed_raw"] == ["db:Z1/envelope/setZero"] and r["probe_changed_cases"] == []
    assert r["correct"] is True and r["inconsistencies_unified"] == []


def test_t0_step_reference_failure_is_an_eval_error(tmp_path):
    from test_chain_eval import make_chain
    make_chain(tmp_path / "tasks2", zone_files=[F])
    sd = _t0_step(tmp_path / "runs3", "")

    def boom():
        raise RuntimeError("no image")
    r = chain_eval.evaluate_step(sd, tasks_root=tmp_path / "tasks2", t0_reference=boom,
                                 execute=_study3_executor(post_text="", step_patch=""))
    assert r["eval_error"].startswith("t0_reference") and r["correct"] is False


@pytest.mark.parametrize("err", [None, "eval_timeout", "seed_install", "hidden_restore",
                                 "test_infra_restore"])
def test_t0_step_unfinished_eval_leaves_the_outcome_unknown(err, tmp_path):
    """An eval that did not finish (no eval_done: ``container``; a timeout; a restore or
    seed failure) is not a changed probe nor a unified inconsistency: those fields stay
    None, so infrastructure failures do not inflate H3's probe-changed rate."""
    from test_chain_eval import make_chain
    make_chain(tmp_path / "tasks2", zone_files=[F])
    t0 = chains.load_t0("Z1")
    patch = _added_diff(F, ZONE_POST_BEFORE, ZONE_POST_BEFORE + "// one place\n")
    sd = _t0_step(tmp_path / "runs3", patch)
    ref = {"probe": _probe_doc({"c-food": -100, "c-orphan": 0}), "suite": SUITE}

    def execute(argv, timeout):
        out = Path(next(a.split(":")[0] for a in argv if a.endswith(":/out")))
        _t0_writer(_probe_doc({"c-food": -100, "c-orphan": 0}),
                   {n: "passed" for n in t0.tests})(out)  # a half-written eval
        if err == "eval_timeout":
            raise subprocess.TimeoutExpired(argv, timeout)
        if err:
            (out / "eval_error").write_text(err + "\n")
    r = chain_eval.evaluate_step(sd, tasks_root=tmp_path / "tasks2", t0_reference=ref,
                                 execute=execute)
    assert r["eval_error"] == (err or "container")
    for k in ("probe_changed_cases", "probe_changed_raw", "probe_unchanged", "probe_passed",
              "t0_tests", "inconsistencies_unified"):
        assert r[k] is None, k
    assert r["correct"] is False


def test_t0_step_not_evaluated_statuses(tmp_path):
    from test_chain_eval import make_chain
    make_chain(tmp_path / "tasks2", zone_files=[F])
    sd = _t0_step(tmp_path / "runs3", "", status="harness_error")
    r = chain_eval.evaluate_step(sd, tasks_root=tmp_path / "tasks2", t0_reference={},
                                 execute=lambda a, t: pytest.fail("no container"))
    assert r["eval_error"] == "not_evaluated" and r["step"] == 0
    infra = _t0_step(tmp_path / "runs3b", "", status="infra")
    assert chain_eval.evaluate_step(infra, tasks_root=tmp_path / "tasks2") is None


def test_rc_chain_summary_keeps_t1_t4_apart_from_t0(tmp_path):
    from test_chain_eval import make_chain, make_step
    make_chain(tmp_path / "tasks2", zone_files=[F])
    cdir = tmp_path / "runs3" / "claude" / "RC" / "Z1" / "0"
    t0 = _t0_step(tmp_path / "runs3", "")
    (t0 / "result.json").write_text(json.dumps({
        "status": "ok", "correct": True, "probe_unchanged": True, "inconsistencies_unified": [],
        "tokens": {"input": 900, "output": 90}, "wall_s": 600.0,
        "duplication_pre": {"clones": 5, "duplicated_lines": 50, "duplicated_lines_unique": 40}}))
    (t0 / "eval").mkdir()
    (t0 / "eval" / "pre_image.patch").write_text("")
    for k in range(1, 5):
        d = make_step(tmp_path / "runs3", step=f"T{k}", cond="RC")
        (d / "result.json").write_text(json.dumps({
            "status": "ok", "correct": True, "tokens": {"input": 100 * k, "output": 10},
            "wall_s": 60.0, "diff_applies_to_pre_image": True,
            "duplication_pre": {"clones": 1, "duplicated_lines": 9, "duplicated_lines_unique": 9},
            "duplication_post": {"clones": 1, "duplicated_lines": 9, "duplicated_lines_unique": 9}}))
        (d / "eval").mkdir()
        (d / "eval" / "pre_image.patch").write_text("T0 tree\n")
    (cdir / "T4" / "eval" / "post_tree.patch").write_text("T0..T4\n")
    out = chain_eval.summarise_chain(cdir, chain_eval.load_chain("Z1", tmp_path / "tasks2"))
    assert out["complete"] and out["t0"]["correct"] is True
    assert out["duplication_T0_tree"] == "agent_t0_post"
    assert out["duplication"]["start"]["clones"] == 5 and out["duplication"]["T0"]["clones"] == 1
    assert out["cost_growth"]["t1_tokens"] == 110          # T1..T4 only
    assert out["totals"]["t1_tn"] == {"tokens": 1040, "wall_s": 240.0, "steps": 4,
                                      "tokens_missing_steps": 0}
    assert out["totals"]["all_steps"] == {"tokens": 2030, "wall_s": 840.0, "steps": 5,
                                          "tokens_missing_steps": 0}
    assert out["cumulative_diff"]["from"] == "T0"
    assert (cdir / "cumulative.patch").read_text() == "T0..T4\n"


def test_evaluate_chain_logs_an_rc_t0_result_and_goes_on_to_t1_t4(tmp_path, monkeypatch):
    """A T0 result has no consumers_* / carried_defects: logging it must not abort the
    chain (before the fix: KeyError, T1..T4 unevaluated, no chain_result.json)."""
    from test_chain_eval import make_chain, make_step
    make_chain(tmp_path / "tasks2", zone_files=[F])
    cdir = tmp_path / "runs3" / "claude" / "RC" / "Z1" / "0"
    _t0_step(tmp_path / "runs3", "")
    for k in range(1, 5):
        make_step(tmp_path / "runs3", step=f"T{k}", cond="RC")
    seen = []

    def fake_step(d, **kw):
        seen.append(d.name)
        r = {"status": "ok", "correct": True, "eval_error": None,
             "tokens": {"input": 10, "output": 1}, "wall_s": 1.0}
        if d.name == "T0":
            r.update(probe_changed_cases=[], inconsistencies_unified=[])
        else:
            r.update(consumers_passed=1, consumers_total=1, carried_defects=[])
        (d / "result.json").write_text(json.dumps(r))
        return r
    monkeypatch.setattr(chain_eval, "evaluate_step", fake_step)
    logs: list[str] = []
    out = chain_eval.evaluate_chain(cdir, tasks_root=tmp_path / "tasks2", log=logs.append)
    assert seen == ["T0", "T1", "T2", "T3", "T4"]
    assert not any("crashed" in m for m in logs)
    assert "probe_changed=0 unified=[]" in logs[0] and "consumers=1/1" in logs[1]
    assert (cdir / chain_eval.CHAIN_RESULT).exists() and out["complete"]
    assert out["duplication_T0_tree"] == "agent_t0_post"


# =========================================================================== RL trips

def _trip(*clones):
    rows = "".join(f"  {a}:{s1}-{e1} ~ {b}:{s2}-{e2} (40 tokens)\n" for a, s1, e1, b, s2, e2 in clones)
    return f"$ yarn lint\n{HEADER}\n{rows}The check passes when no duplicated block ...\n"


def test_trip_kind_against_the_start_tree_clones():
    old = _clone(A, 1, 10, A, 21, 30)
    pre = _trip((A, 3, 12, A, 23, 32))                     # the old pair, shifted by 2
    assert chain_eval3.trip_kind(pre, [old]) == "touches_preexisting_only"
    swapped = _trip((A, 21, 30, A, 1, 10))
    assert chain_eval3.trip_kind(swapped, [old]) == "touches_preexisting_only"
    new = _trip((A, 3, 12, A, 23, 32), (A, 1, 10, f"{LOOT_SRC}/b.ts", 1, 10))
    assert chain_eval3.trip_kind(new, [old]) == "adds_new_clone_side"
    assert chain_eval3.trip_kind(f"{HEADER}\n(garbled)\n", [old]) is None


def test_ratchet_split():
    assert chain_eval3.ratchet_split([None, "adds_new_clone_side"], None) == "adds_new_clone_side"
    assert chain_eval3.ratchet_split([], "touches_preexisting_only") == "touches_preexisting_only"
    assert chain_eval3.ratchet_split([], None) == "no_fire"


def test_ratchet_measures_reads_an_rl_trip_the_final_tree_no_longer_shows(tmp_path):
    # the agent pasted a copy, saw dup-check fail, then extracted a helper: final passes
    ev = _ratchet_dir(tmp_path, start=[(A, 1, 10, A, 21, 30)], post=[(A, 1, 10, A, 21, 30)],
                      diff="")
    m = ratchet_measures(ev, trips=[_trip((A, 1, 10, A, 41, 50))])
    assert m["ratchet_kind"] is None and m["ratchet_trip_kinds"] == ["adds_new_clone_side"]
    assert m["ratchet_split"] == "adds_new_clone_side"


def test_cli_chain_evaluate_passes_tasks3(monkeypatch, tmp_path):
    from aa import cli
    seen = {}
    monkeypatch.setattr(chain_eval, "evaluate_all",
                        lambda root, **kw: seen.update(root=root, kw=kw) or {})
    assert cli.main(["chain", "evaluate", "--all", "--runs", str(tmp_path / "runs3"),
                     "--tasks3", str(tmp_path / "t3")]) == 0
    assert seen["kw"]["t0_root"] == tmp_path / "t3"
    monkeypatch.setattr(chain_eval, "evaluate_step", lambda d, **kw: {
        "step_id": "T0", "status": "ok", "correct": False, "probe_changed_cases": ["db:x"],
        "inconsistencies_unified": ["u"], "eval_error": None})
    assert cli.main(["chain", "evaluate", str(tmp_path / "T0")]) == 0
