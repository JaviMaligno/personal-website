"""Study 3 evaluator: T0 and the new measures (spec 2026-10-10 sections 3, 5, 6; plan
Task 5; spec amendments 2026-10-11 and 2026-10-11b).

The container side lives in :func:`aa.chain_eval.chain_eval_script` (``study3=True``,
``t0=True``); this module holds what is read back on the host, plus the T0 step.

Every study-3 step (all arms, T0..T4)
-------------------------------------
- **Start commit.** The evaluated tree gets a root commit named ``start`` at the step's
  own start tree, made exactly as the chain runner makes it (a fresh repository,
  ``git init -b main``, ``git add -A``, one commit ``start``), in a separate git dir
  (``/tmp/aa-start.git``, work tree ``/work/actual``) so the image repository the rest of
  the evaluation needs is untouched. ``yarn lint`` (``lint_ok``; in RL it runs
  dup-check) runs with that git dir, so dup-check diffs against the step start, not the
  image's ``base`` (the RL ``lint_ok`` defect of amendment 2026-10-11). Its tree id is
  checked against the runner's ``start_tree`` (``tree_check.start_fresh``).
- **Ratchet, counterfactual for every arm** (amendment 2026-10-11b): the harness
  detector (:mod:`aa.ratchet`: jscpd at :data:`aa.config.RATCHET_MIN_TOKENS` over
  loot-core's non-test sources, staged at their repo paths) on the start tree and on the
  post tree, the post tree's changes since that ``start`` commit (``git diff -U0``,
  untracked files whole). ``ratchet_final`` = clones of the post tree with a side on a
  changed line (RL's rule); ``ratchet_start_fires`` = the change touches a clone the
  start tree already had (modifies or deletes one of its lines, inserts lines inside
  it, or a firing clone is that clone grown or edited); ``ratchet_kind`` (None when
  ``ratchet_final`` does not fire; amendments 2026-10-11b and c):
  ``touches_preexisting_only`` when every firing clone is one of the start tree
  (:func:`matches_start_clone`: same two files, each side's start-backed lines mapped
  to start lines by :class:`LineMap` overlapping that clone's sides, so a rule check
  inserted in a copy edits the copy, while a copy pasted right against an old side,
  its lines mostly added, is new: amendment 2026-10-11d), else ``adds_new_clone_side`` when a new firing clone has a side on a
  line *added* by the step, else ``touches_preexisting_only`` / the residual
  ``modified_into_clone`` (only modified lines; whether a pre-existing clone was
  touched). Added vs modified: per change block of the diff, a new line is *modified*
  when it is similar (difflib ratio >= :data:`MODIFIED_SIMILARITY`) to a line the block
  removed, else *added*; blocks without removed lines are wholly added. In RL the agent
  may see the ratchet fire and fix it, so each dup-check failure in the transcript is
  classified too (``ratchet_trip_kinds``, :func:`classify_trip`: the same matcher, each
  clone against the start tree as the tree was at that trip: through the final diff
  when the clone is still in the post tree at those lines, else read as start-tree
  lines; ``ratchet_trip_basis``; pilot blocking item 4); ``ratchet_split`` (the variable
  H-RL analyses are split by) is the first trip's kind, else ``ratchet_kind``, else
  ``no_fire``; ``ratchet_trip_clones`` (:func:`trip_clone_counts`, amendment 2026-10-12b
  item 6) counts the start-tree clones the trips listed and how many remain in the post
  tree, for H4's (a) consolidation / (b) edit moved outside the clone split.
- ``lint_runs``: lint invocations in the transcript (``yarn|npm|pnpm [workspace X] [run]
  lint[:fix]`` or ``dup-check.mjs`` as a command, both CLI formats); ``ratchet_trips``:
  tool outputs showing a dup-check failure (its header, closing line or clone rows, so a
  ``| tail -N`` that cut the header still counts; :func:`is_trip`) (RL); ``gaming_flags``
  (:func:`aa.static3.step_gaming_flags`: diff + runner record); ``rule_cited`` (the
  rule quoted; reuse talk is detail).
- T2 (consumer step): ``t2_reuses_logic`` = :func:`t2_static3` (study-2's label kept in
  ``t2_reuse_detail.study2_label``); T1/T3 (rule steps): ``rule_sites_touched``
  (:func:`rule_sites_touched`). Both read the post tree's zone files and the files the
  chain changed, dumped by the container to ``eval/zone_post/``.

T0 (RC only)
------------
Built and checked like any step (verified pre-image = the image, the agent's diff or
tree.tar, the start commit, jscpd on the zone files before/after, the ratchet), then the
checks of ``aa chain t0-reference`` (:func:`aa.chains.t0_script`'s pieces): typecheck
(``tsgo -b``, loot-core ``yarn typecheck``), lint (root and loot-core ``yarn lint``),
the existing tests related to the touched sources (``vitest related``, after the test
infra is restored to the image's), the zone's T0 inconsistency tests (staged copies) and
the study-2 probe. Against the untouched-R reference (:func:`untouched_reference`, one
cached container run: the probe and the full seeded suite in ``aa-actual:R``):
``probe_changed_cases`` = probe cases that differ after ``tasks3/probe-exclusions.json``
(Review Focus 4), ``inconsistencies_unified`` = inconsistency ids whose test did not
pass, ``correct`` = both empty (and the evaluation ran). A T0 packet for the
completeness / interface judge (``eval/t0_packet/``: statement, step diff, sites.json).
"""
from __future__ import annotations

import datetime
import difflib
import json
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from aa import chains as chain_tasks
from aa import config, rg_check
from aa.chain_eval import (EVAL_DIR, NOT_SOURCE_ERE, STATEMENT, STEP_PATCH, _is_definition,
                           is_source_file)
from aa.evaluate import _SHELL_WRAP, _read_int, _read_text
from aa.probe2 import PROBE_DIR
from aa.ratchet import SCOPE, Clone, parse_clones, touching

# Arms that exist only in study 3 (R is shared with study 2 and is study 3 when the run
# says so: agent.json ``study``).
STUDY3_ONLY = tuple(c for c in config.CONDITIONS3 if c not in config.CONDITIONS2)
START_GIT_DIR = "/tmp/aa-start.git"
WORK_TREE = "/work/actual"
# for commands that run git themselves (RL's dup-check under `yarn lint`)
START_GIT_ENV = f"GIT_DIR={START_GIT_DIR} GIT_WORK_TREE={WORK_TREE}"
_G = f"git --git-dir={START_GIT_DIR} --work-tree={WORK_TREE} -c core.quotePath=false"
RATCHET_STAGE = "/tmp/aa-ratchet"
RATCHET_TIMEOUT_S = 600
MODIFIED_SIMILARITY = 0.6
ZONE_POST = "zone_post"
T0_PACKET = "t0_packet"
DUP_CHECK_HEADER = "dup-check: duplicated code on lines added or changed in this task:"
DUP_CHECK_TRAILER = ("The check passes when no duplicated block includes a line added or "
                     "changed in this task.")
# Spec section 3: Z4's date arithmetic (getDateWithSkippedWeekend) is already shared in
# base and is not the zone's decision; calling it is not reusing the weekend rule.
T2_NOT_DECISION = {"Z4": ("getDateWithSkippedWeekend",)}
RATCHET_KINDS = ("adds_new_clone_side", "touches_preexisting_only", "modified_into_clone")
PROBE_MOUNT = f"{PROBE_DIR}:/probe:ro"


def is_study3(meta: dict) -> bool:
    return meta.get("study") == 3 or meta.get("cond") in STUDY3_ONLY


# =========================================================================== container

def start_commit_lines() -> list[str]:
    """The step's ``start`` commit as the chain runner makes it, in a separate git dir;
    the working tree must be the step's start tree. /out/start_commit,
    /out/start_tree_fresh; failure -> eval_error ``start_commit``."""
    g = f"GIT_DIR={START_GIT_DIR}"
    gw = f"{g} GIT_WORK_TREE={WORK_TREE}"
    return [
        f"{{ rm -rf {START_GIT_DIR} && {g} git init -q -b main && {gw} git add -A "
        f"&& {gw} git -c user.name=aa -c user.email=aa@local -c commit.gpgsign=false commit -q "
        f"--no-verify --allow-empty -m start && {g} git rev-parse HEAD > /out/start_commit "
        f"&& {g} git rev-parse 'HEAD^{{tree}}' > /out/start_tree_fresh; }} 2>> /out/apply.log "
        "|| { echo start_commit > /out/eval_error; exit 0; }",
    ]


def ratchet_scan_lines(which: str, min_tokens: int = config.RATCHET_MIN_TOKENS) -> list[str]:
    """jscpd at ``min_tokens`` over the tree's scanned sources (tracked in the start repo,
    plus untracked for ``post``), staged at their repo paths: /out/ratchet_<which>_files,
    /out/ratchet_<which>/jscpd-report.json, /out/ratchet_<which>_rc. For ``post`` also
    the change since ``start`` (/out/ratchet_diff.patch) and the untracked files' line
    counts (/out/ratchet_untracked.tsv, the rule of dup-check's lineCount)."""
    q = shlex.quote
    listing = f"{_G} ls-files -- {SCOPE}"
    if which == "post":
        listing = f"{{ {listing}; {_G} ls-files -o --exclude-standard -- {SCOPE}; }}"
    files = f"/out/ratchet_{which}_files"
    lines = [
        f"{listing} 2>> /out/apply.log | grep -E '\\.[cm]?[jt]sx?$' | grep -vE {q(NOT_SOURCE_ERE)} "
        f'| sort -u | while IFS= read -r f; do [ -f "$f" ] && printf "%s\\n" "$f"; done > {files}',
        f"rm -rf {RATCHET_STAGE} && mkdir -p {RATCHET_STAGE}/{SCOPE} && "
        f'while IFS= read -r f; do mkdir -p "{RATCHET_STAGE}/$(dirname "$f")" '
        f'&& cp "$f" "{RATCHET_STAGE}/$f"; done < {files}',
        f"( cd {RATCHET_STAGE} && timeout {RATCHET_TIMEOUT_S} jscpd --min-tokens {int(min_tokens)} "
        f"--reporters json --silent --output /out/ratchet_{which} {SCOPE} "
        f"> /out/ratchet_{which}.log 2>&1; echo $? > /out/ratchet_{which}_rc )",
        f"rm -rf {RATCHET_STAGE}",
    ]
    if which == "post":
        count = ("const t=require('fs').readFileSync(process.argv[1]).toString('latin1');"
                 "const p=t===''?[]:t.split(/\\r\\n|\\r|\\n/);"
                 "console.log(p.length&&p[p.length-1]===''?p.length-1:p.length)")
        lines += [
            f'{_G} diff -U0 --no-renames --no-color --no-ext-diff "$(cat /out/start_commit)" '
            f"-- {SCOPE} > /out/ratchet_diff.patch 2>> /out/apply.log "
            "|| echo 1 > /out/ratchet_diff_error",
            f"{_G} ls-files -o --exclude-standard -- {SCOPE} 2>> /out/apply.log "
            f'| while IFS= read -r f; do [ -f "$f" ] && printf "%s\\t%s\\n" "$f" '
            f'"$(node -e {q(count)} "$f")"; done > /out/ratchet_untracked.tsv',
        ]
    return lines


def zone_dump_lines() -> list[str]:
    """The post tree's zone files (as jscpd_post listed them) and every source file the
    chain changed so far (vs the image), copied to /out/zone_post/<path>; run from
    /work/actual after the post tree is recorded."""
    return [
        f'{{ cat /out/jscpd_post_files 2>/dev/null; git diff --name-only --no-renames HEAD '
        f'"$(cat /out/post_tree)" -- {SCOPE} 2>/dev/null; }} | grep -E \'\\.[cm]?[jt]sx?$\' '
        f'| sort -u | while IFS= read -r f; do [ -f "$f" ] && mkdir -p "/out/{ZONE_POST}/$(dirname "$f")" '
        f'&& cp "$f" "/out/{ZONE_POST}/$f"; done',
    ]


def related_files_line() -> str:
    """loot-core-relative non-test sources the step touched (start -> post tree):
    /out/related_files (input of :func:`aa.chains.t0_related_from_file_line`)."""
    pre = config.LOOT + "/"
    return (f'git diff --name-only --no-renames "$(cat /out/start_tree)" "$(cat /out/post_tree)" '
            f"-- {config.LOOT} | grep -E '\\.[cm]?[jt]sx?$' | grep -vE '\\.(test|spec)\\.[jt]sx?$' "
            f"| sed 's#^{pre}##' > /out/related_files")


# =========================================================================== transcripts

def _events(lines: Iterable[str]) -> Iterable[dict]:
    for raw in lines:
        raw = raw.strip()
        if not raw.startswith("{"):
            continue
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(ev, dict):
            yield ev


def shell_commands(agent: str, lines: Iterable[str]) -> list[str]:
    """Shell commands the agent ran, in order: Claude Code's ``Bash`` tool uses, Codex's
    ``command_execution`` items (once per item id, started or completed; the ``bash -lc``
    wrapper removed)."""
    out: list[str] = []
    seen: set[str] = set()
    claude = config.engine(agent) == "claude"
    for ev in _events(lines):
        if claude:
            if ev.get("type") != "assistant":
                continue
            for b in (ev.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Bash":
                    out.append(str((b.get("input") or {}).get("command", "")))
        else:
            if ev.get("type") not in ("item.started", "item.completed"):
                continue
            item = ev.get("item") or {}
            if item.get("type") not in ("command_execution", "local_shell_call"):
                continue
            iid = item.get("id")
            if iid is not None:
                if iid in seen:
                    continue
                seen.add(iid)
            cmd = item.get("command", "")
            cmd = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            m = _SHELL_WRAP.match(cmd)
            out.append(m.group(2) if m else cmd)
    return out


_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n\s*\2\s*(?=\n|$)", re.S)
_SEGMENT_SPLIT = re.compile(r"&&|\|\||(?<![<>&])&(?![>&])|[;|()\n]")  # `&`, not `&>`/`2>&1`
_PREFIX = re.compile(r"^(?:\s*(?:[A-Za-z_]\w*=\S*|timeout\s+(?:-\S+\s+)*\S+|env|time|exec|command)\s+)*")
_LINT_SEGMENT = re.compile(
    r"^(?:(?:yarn|npm|pnpm)(?:\s+--cwd\s+\S+)?\s+(?:workspace\s+\S+\s+)?(?:run\s+)?lint(?::fix)?"
    r"|(?:node\s+)?\S*dup-check\.mjs)(?=\s|$)")


def lint_segments(cmd: str) -> list[str]:
    """The parts of one shell command that run a lint script (``yarn lint``,
    ``yarn lint:fix``, ``yarn workspace <ws> [run] lint``, ``npm run lint``, ...) or the
    RL check directly; heredoc bodies and text that only mentions lint (grep, rg, cat)
    are not runs."""
    body = _HEREDOC.sub("", cmd)
    out = []
    for seg in _SEGMENT_SPLIT.split(body):
        s = _PREFIX.sub("", seg.strip()).strip()
        if _LINT_SEGMENT.match(s):
            out.append(s)
    return out


def lint_runs(agent: str, lines: Iterable[str]) -> tuple[int, list[str]]:
    """(lint invocations in the transcript, the invoking command parts, first 30)."""
    segs = [s for c in shell_commands(agent, lines) for s in lint_segments(c)]
    return len(segs), segs[:30]


def tool_outputs(agent: str, lines: Iterable[str]) -> list[str]:
    """Text of every tool result: Claude Code ``tool_result`` blocks, Codex completed
    ``command_execution`` items (``aggregated_output``)."""
    out: list[str] = []
    claude = config.engine(agent) == "claude"
    for ev in _events(lines):
        if claude:
            if ev.get("type") != "user":
                continue
            for b in (ev.get("message") or {}).get("content") or []:
                if not isinstance(b, dict) or b.get("type") != "tool_result":
                    continue
                c = b.get("content")
                if isinstance(c, list):
                    c = "\n".join(str(x.get("text", "")) for x in c if isinstance(x, dict))
                out.append(str(c or ""))
        elif ev.get("type") == "item.completed":
            item = ev.get("item") or {}
            if item.get("type") in ("command_execution", "local_shell_call"):
                out.append(str(item.get("aggregated_output") or ""))
    return out


_TRIP_HEADER = re.compile(rf"^{re.escape(DUP_CHECK_HEADER)}\s*$", re.M)
_TRIP_TRAILER = re.compile(rf"^{re.escape(DUP_CHECK_TRAILER)}\s*$", re.M)
_TRIP_ROW = re.compile(r"^\s+(\S+):(\d+)-(\d+) ~ (\S+):(\d+)-(\d+) \(\d+ tokens\)", re.M)


def is_trip(output: str) -> bool:
    """Whether one tool result shows a dup-check failure: its header, its closing line
    or one of its clone rows, each as a printed line (so ``yarn lint | tail -N`` that
    cut the header still counts, and the script's source, where they are quoted string
    literals or templates, does not). Output that hides every one of them (``| tail -1``,
    ``> /dev/null``) cannot be seen; ``ratchet_split`` then falls back to the final
    tree's kind."""
    return bool(_TRIP_HEADER.search(output) or _TRIP_TRAILER.search(output)
                or _TRIP_ROW.search(output))


def trip_outputs(agent: str, lines: Iterable[str]) -> list[str]:
    """Tool results in which RL's dup-check reported clones (:func:`is_trip`)."""
    return [t for t in tool_outputs(agent, lines) if is_trip(t)]


def ratchet_trips(agent: str, lines: Iterable[str]) -> int:
    return len(trip_outputs(agent, lines))


def trip_clones(output: str) -> list[tuple[str, int, int, str, int, int]]:
    """The clones one dup-check failure lists (``  a:s-e ~ b:s-e (N tokens)``), after
    its header when the header is there."""
    m = _TRIP_HEADER.search(output)
    text = output[m.end():] if m else output
    return [(a, int(s1), int(e1), b, int(s2), int(e2))
            for a, s1, e1, b, s2, e2 in _TRIP_ROW.findall(text)]


def trip_kind(output: str, start_clones: list[Clone], lmap: "LineMap | None" = None) -> str | None:
    """Amendment 2026-10-11b/c: the kind of an RL trip the agent saw (its final tree may
    no longer fire). ``touches_preexisting_only`` when every reported clone is one of the
    step's start tree (:func:`matches_start_clone`, the rule ``ratchet_kind`` uses), else
    ``adds_new_clone_side``; None when no clone could be read. The trip's line numbers
    are those of the agent's tree at that moment; they are mapped to start lines with
    the step's final diff (``lmap``), exact when the tree at the trip is the final one
    and approximate when the agent changed the lines in between."""
    reported = trip_clones(output)
    if not reported:
        return None
    if all(matches_start_clone(r, start_clones, lmap) for r in reported):
        return "touches_preexisting_only"
    return "adds_new_clone_side"


def _same_clone(r: tuple[str, int, int, str, int, int], c: Clone) -> bool:
    t = _as_tuple(c)
    return r == t or r == (t[3], t[4], t[5], t[0], t[1], t[2])


def classify_trip(output: str, start_clones: list[Clone], post_clones: list[Clone],
                  lmap: "LineMap | None" = None) -> tuple[str | None, str | None]:
    """Study-3 pilot, blocking item 4: (kind, basis) of an RL trip, each clone it lists
    matched against the step's **start** tree with the tree as it was at that dup-check
    run, not the final one. The runner keeps no snapshot of the tree at a trip and the
    transcripts cannot rebuild it (Codex ``file_change`` items carry no content; agents
    also edit through shell scripts), so per clone:

    - ``final_tree``: the clone is still a clone of the post tree at exactly the same
      lines, so the tree at the trip is the final one there: its lines map to start
      lines through the step's final diff (``lmap``), exactly (a copy pasted right
      against an old side stays new, amendment 2026-10-11d);
    - ``start_lines``: otherwise the agent changed those lines after the trip (typically
      it consolidated the clone the trip showed); the trip's line numbers are read as
      start-tree lines, and the clone is pre-existing when its two files hold a clone
      of the start tree whose sides overlap the trip's (:func:`matches_start_clone`
      without a diff). Approximate: lines the agent inserted above a clone before the
      trip shift it, and only the overlap absorbs that.

    ``touches_preexisting_only`` when every listed clone is pre-existing, else
    ``adds_new_clone_side``; None when no clone could be read. ``basis``:
    ``final_tree``, ``start_lines`` or ``mixed``."""
    reported = trip_clones(output)
    if not reported:
        return None, None
    lmap = lmap or LineMap()
    ident = LineMap()
    pre, bases = [], set()
    for r in reported:
        if any(_same_clone(r, c) for c in post_clones):
            bases.add("final_tree")
            pre.append(matches_start_clone(r, start_clones, lmap))
        else:
            bases.add("start_lines")
            pre.append(matches_start_clone(r, start_clones, ident))
    basis = bases.pop() if len(bases) == 1 else "mixed"
    return ("touches_preexisting_only" if all(pre) else "adds_new_clone_side"), basis


def trip_clone_counts(trips: list[str], start_clones: list[Clone], post_clones: list[Clone],
                      lmap: "LineMap | None" = None) -> dict[str, int] | None:
    """``ratchet_trip_clones`` (spec amendment 2026-10-12b, item 6): what happened to the
    clones the step's dup-check trips listed, for H4's (a) / (ab) / (b) / (u) split.
    Each listed clone is matched against the start tree as in :func:`classify_trip`
    (final diff where the clone is unchanged in the post tree, else the trip's lines
    read as start lines). ``listed_preexisting`` = |L|, the start-tree clones some trip
    clone matches; ``remaining`` = |Rm|, the members of L still a clone of the post tree
    (any post-tree clone matching them through the final diff); ``new_listed`` = trip
    clones matching no start clone (clones the agent itself added); ``unreadable_trips``
    = trips with no readable clone row. None without trips."""
    trips = list(trips)
    if not trips:
        return None
    lmap = lmap or LineMap()
    ident = LineMap()
    listed: list[Clone] = []
    new = unreadable = 0
    for t in trips:
        rows = trip_clones(t)
        if not rows:
            unreadable += 1
            continue
        for r in rows:
            m = lmap if any(_same_clone(r, c) for c in post_clones) else ident
            hits = [s for s in start_clones if matches_start_clone(r, [s], m)]
            if not hits:
                new += 1
            for s in hits:
                if s not in listed:
                    listed.append(s)
    remaining = sum(1 for s in listed
                    if any(matches_start_clone(_as_tuple(p), [s], lmap) for p in post_clones))
    return {"listed_preexisting": len(listed), "remaining": remaining, "new_listed": new,
            "unreadable_trips": unreadable}


def ratchet_split(trip_kinds: list[str | None], final_kind: str | None) -> str:
    """The per-step class H-RL analyses are split by (amendment 2026-10-11b): the first
    readable trip's kind when the agent saw the ratchet fire (RL), else the final tree's
    ``ratchet_kind`` (every arm: what the ratchet would say), else ``no_fire``."""
    for k in trip_kinds:
        if k:
            return k
    return final_kind or "no_fire"


def agent_texts(agent: str, lines: Iterable[str]) -> list[str]:
    """The agent's own prose: Claude Code ``text``/``thinking`` blocks, Codex
    ``agent_message``/``reasoning`` items."""
    out: list[str] = []
    claude = config.engine(agent) == "claude"
    for ev in _events(lines):
        if claude:
            if ev.get("type") != "assistant":
                continue
            for b in (ev.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") in ("text", "thinking"):
                    out.append(str(b.get("text") or b.get("thinking") or ""))
        elif ev.get("type") == "item.completed":
            item = ev.get("item") or {}
            if item.get("type") in ("agent_message", "reasoning"):
                out.append(str(item.get("text") or ""))
    return out


# RG's rule (tasks3/rg-rule.md), by its distinctive phrases
_RULE_PHRASES = re.compile(r"do not copy logic|change it in one place|extract it into a shared "
                           r"function", re.I)
_REUSE = re.compile(r"\b(?:extract(?:s|ed|ing)?|reus(?:e|es|ed|ing)|re-us(?:e|ing)|"
                    r"shared (?:helper|function)|single (?:helper|place|source)|one place|"
                    r"deduplicat\w*|consolidat\w*)\b", re.I)


def rule_cited(agent: str, lines: Iterable[str]) -> tuple[bool, dict[str, Any]]:
    """Whether the agent's own prose quotes RG's rule (its distinctive phrases; spec
    section 6, as refined by amendment 2026-10-11c; computed for every arm, so R is the
    baseline). Talk about extracting / reusing logic is common in every arm, so it is
    only detail (``reuse_talk``, ``reuse_mentions``), as is whether it opened AGENTS.md
    with a tool call (``agents_md_explicit_read``; pilot results carry the legacy key
    ``agents_md_read``, read through :mod:`aa.rg_check`)."""
    lines = list(lines)
    texts = agent_texts(agent, lines)
    quoted = [t for t in texts if _RULE_PHRASES.search(t)]
    reuse = [m.group(0) for t in texts for m in _REUSE.finditer(t)]
    read = any(re.search(r"(?:^|[\s/'\"])AGENTS\.md\b", c) for c in shell_commands(agent, lines))
    if config.engine(agent) == "claude" and not read:
        for ev in _events(lines):
            if ev.get("type") == "assistant":
                for b in (ev.get("message") or {}).get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use" and \
                            str((b.get("input") or {}).get("file_path", "")).endswith("AGENTS.md"):
                        read = True
    detail = {"rule_quoted": bool(quoted), "reuse_talk": bool(reuse),
              "reuse_mentions": len(reuse),
              "reuse_words": sorted(set(w.lower() for w in reuse))[:20],
              # spec amendment 2026-10-12b, item 7: the agent opened AGENTS.md with a
              # tool call; descriptive, never a manipulation check (aa.rg_check)
              rg_check.EXPLICIT_KEY: read,
              "quotes": [q[:300] for q in quoted[:3]]}
    return bool(quoted), detail


# =========================================================================== diffs

_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def change_blocks(diff: str) -> dict[str, list[dict[str, Any]]]:
    """Per post-image path, the diff's change blocks (runs of removed/added lines between
    context): ``old`` [(old line no, text)], ``new`` [(new line no, text)], ``at`` = the
    post line number the block sits before (a pure deletion's position), ``old_at`` = the
    start line number it sits before (a pure insertion's position). Hunk lengths
    from the headers delimit hunks (a removed ``-- x`` line is not a header); deleted
    files and binary patches give no blocks."""
    out: dict[str, list[dict[str, Any]]] = {}
    cur: str | None = None
    lines = diff.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("diff --git "):
            cur = None
        elif ln.startswith("+++ "):
            p = ln[4:].split("\t")[0].strip()
            cur = None if p == "/dev/null" else (p[2:] if p.startswith("b/") else p)
        m = _HUNK.match(ln)
        if not m:
            i += 1
            continue
        o, oc = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
        n, nc = int(m.group(3)), int(m.group(4) if m.group(4) is not None else 1)
        if oc == 0:
            o += 1  # "-a,0": the deletion-free hunk sits after old line a
        if nc == 0:
            n += 1
        i += 1
        block: dict[str, Any] | None = None
        while i < len(lines) and (oc > 0 or nc > 0):
            t = lines[i]
            if t.startswith("\\"):
                i += 1
                continue
            tag, text = t[:1], t[1:]
            if tag == "-" and oc > 0:
                if block is None:
                    block = {"old": [], "new": [], "at": n, "old_at": o}
                block["old"].append((o, text))
                o += 1
                oc -= 1
            elif tag == "+" and nc > 0:
                if block is None:
                    block = {"old": [], "new": [], "at": n, "old_at": o}
                block["new"].append((n, text))
                n += 1
                nc -= 1
            else:  # context (or a malformed line: treated as context)
                if block is not None and cur is not None:
                    out.setdefault(cur, []).append(block)
                block = None
                o, n, oc, nc = o + 1, n + 1, oc - 1, nc - 1
            i += 1
        if block is not None and cur is not None:
            out.setdefault(cur, []).append(block)
    return out


def _similar(a: str, b: str) -> bool:
    a, b = a.strip(), b.strip()
    if a == b:
        return True
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sm.real_quick_ratio() >= MODIFIED_SIMILARITY and \
        sm.quick_ratio() >= MODIFIED_SIMILARITY and sm.ratio() >= MODIFIED_SIMILARITY


def classify_changes(diff: str) -> dict[str, dict[str, set[int]]]:
    """``added`` / ``modified`` post line numbers and ``old`` (start-tree line numbers
    removed or modified), per path. A new line of a block is *modified* when similar
    (:data:`MODIFIED_SIMILARITY`) to a line the same block removed, else *added*."""
    added: dict[str, set[int]] = {}
    modified: dict[str, set[int]] = {}
    old: dict[str, set[int]] = {}
    for path, blocks in change_blocks(diff).items():
        for b in blocks:
            if b["old"]:
                old.setdefault(path, set()).update(n for n, _ in b["old"])
            olds = [t for _, t in b["old"]]
            for n, t in b["new"]:
                kind = modified if olds and any(_similar(t, o) for o in olds) else added
                kind.setdefault(path, set()).add(n)
    return {"added": added, "modified": modified, "old": old}


def changed_post_lines(diff: str) -> tuple[dict[str, set[int]], dict[str, list[int]]]:
    """(post lines added or modified per path, pure-deletion positions per path: the
    post line the deleted lines sat before)."""
    changed: dict[str, set[int]] = {}
    deletions: dict[str, list[int]] = {}
    for path, blocks in change_blocks(diff).items():
        for b in blocks:
            if b["new"]:
                changed.setdefault(path, set()).update(n for n, _ in b["new"])
            else:
                deletions.setdefault(path, []).append(b["at"])
    return changed, deletions


class LineMap:
    """Post-tree line numbers -> start-tree line numbers, from the step's ``-U0`` diff.
    An unchanged line maps exactly; a line inside a change block maps to the start lines
    around that block: ``lo`` (start of a range) to the block's first removed line, or,
    for a pure insertion, the start line just before it; ``hi`` (end of a range) to the
    block's last removed line, or the start line just after an insertion.

    A post *range* (a clone side) maps through its start-backed lines only
    (:meth:`range_to_old`, amendment 2026-10-11d): unchanged lines and lines *modified*
    from a removed line (:func:`classify_changes`); lines the step *added* map nowhere.
    So a range grown by inserted lines (a rule check added inside or at the edge of a
    pre-existing copy) maps onto the start range it grew from, while a copy pasted
    right before or after an old clone side (its lines all added) maps to nothing and
    cannot be taken for that side."""

    def __init__(self, diff: str = ""):
        self.added = classify_changes(diff)["added"] if diff else {}
        self.blocks: dict[str, list[tuple[int, int, int, int]]] = {}
        for path, blocks in change_blocks(diff).items():
            rows = []
            for b in blocks:
                p0 = b["new"][0][0] if b["new"] else b["at"]
                rows.append((p0, len(b["new"]), b["old_at"], len(b["old"])))
            self.blocks[path] = sorted(rows)

    def to_old(self, path: str, line: int, end: str = "lo") -> int:
        delta = 0
        for p0, n_new, o0, n_old in self.blocks.get(path, ()):
            if line < p0:
                break
            if line < p0 + n_new:
                if n_old == 0:
                    return o0 - 1 if end == "lo" else o0
                return o0 if end == "lo" else o0 + n_old - 1
            delta += n_new - n_old
        return line - delta

    def range_to_old(self, path: str, start: int, end: int) -> tuple[int, int] | None:
        """The start-tree span of a post range's start-backed lines (not added by the
        step); None when added lines are the majority of the range (a new copy, even
        one that runs a line or two into unchanged code)."""
        added = self.added.get(path, set())
        backed = [n for n in range(start, end + 1) if n not in added]
        if not backed or 2 * len(backed) < end - start + 1:
            return None
        return self.to_old(path, backed[0], "lo"), self.to_old(path, backed[-1], "hi")


def matches_start_clone(clone: tuple[str, int, int, str, int, int], start_clones: list[Clone],
                        lmap: LineMap | None = None) -> bool:
    """Amendment 2026-10-11b (as refined 2026-10-11c and d): whether a clone of the post tree
    (or of an RL trip) is one the start tree already had: same two files, each side's
    start-backed lines, mapped to start-tree lines by ``lmap`` (:meth:`LineMap.range_to_old`), overlapping that
    clone's sides, in either order. One rule for every arm: the final tree's
    ``ratchet_kind`` and RL's trip kinds use it alike."""
    lmap = lmap or LineMap()
    a, s1, e1, b, s2, e2 = clone
    ma, mb = lmap.range_to_old(a, s1, e1), lmap.range_to_old(b, s2, e2)
    if ma is None or mb is None:
        return False

    def overlap(x: tuple[int, int], s: int, e: int) -> bool:
        return x[0] <= e and s <= x[1]
    return any(x == a and y == b and overlap(ma, xs, xe) and overlap(mb, ys, ye)
               for c in start_clones
               for x, xs, xe, y, ys, ye in ((c.a, c.a_start, c.a_end, c.b, c.b_start, c.b_end),
                                            (c.b, c.b_start, c.b_end, c.a, c.a_start, c.a_end)))


def _as_tuple(c: Clone) -> tuple[str, int, int, str, int, int]:
    return (c.a, c.a_start, c.a_end, c.b, c.b_start, c.b_end)


def insertions_inside(start_clones: list[Clone], diff: str) -> list[Clone]:
    """Start clones with lines inserted strictly between two of a side's lines."""
    points: dict[str, list[int]] = {}
    for path, blocks in change_blocks(diff).items():
        for b in blocks:
            if b["new"] and not b["old"]:
                points.setdefault(path, []).append(b["old_at"])  # sits before this line
    return [c for c in start_clones
            if any(s < o <= e for f, s, e in ((c.a, c.a_start, c.a_end), (c.b, c.b_start, c.b_end))
                   for o in points.get(f, ()))]


# =========================================================================== ratchet

def _scan_files(eval_dir: Path, which: str) -> list[str]:
    return [f for f in dict.fromkeys(ln.strip() for ln in
                                     _read_text(eval_dir / f"ratchet_{which}_files").splitlines())
            if f and f.startswith(SCOPE + "/") and is_source_file(f)]


def _report(eval_dir: Path, which: str) -> dict | None:
    if _read_int(eval_dir / f"ratchet_{which}_rc") != 0:
        return None
    p = eval_dir / f"ratchet_{which}" / "jscpd-report.json"
    try:
        return json.loads(p.read_text()) if p.exists() else {"duplicates": []}
    except json.JSONDecodeError:
        return None


def _clone_dict(c: Clone) -> dict[str, Any]:
    return {"a": c.a, "a_start": c.a_start, "a_end": c.a_end, "b": c.b, "b_start": c.b_start,
            "b_end": c.b_end, "lines": c.lines, "tokens": c.tokens}


def _side_hits(c: Clone, lines: dict[str, set[int]]) -> bool:
    return any(lines.get(f) and any(s <= ln <= e for ln in lines[f])
               for f, s, e in ((c.a, c.a_start, c.a_end), (c.b, c.b_start, c.b_end)))


def ratchet_kind(final: list[Clone], added: dict[str, set[int]], start_fires: bool,
                 preexisting: Callable[[Clone], bool] = lambda c: False) -> str | None:
    """Amendment 2026-10-11b/c: why the ratchet fires on a step (None: it does not).
    ``touches_preexisting_only`` when every firing clone is one the start tree already
    had (``preexisting``: :func:`matches_start_clone`), whatever the step did inside it
    (lines inserted in a copy count as editing that copy); else ``adds_new_clone_side``
    when a new firing clone has a side on an added line; else (only modified lines)
    ``touches_preexisting_only`` if the step edits a pre-existing clone, or
    ``modified_into_clone``."""
    if not final:
        return None
    new = [c for c in final if not preexisting(c)]
    if not new:
        return "touches_preexisting_only"
    if any(_side_hits(c, added) for c in new):
        return "adds_new_clone_side"
    return "touches_preexisting_only" if start_fires else "modified_into_clone"


def ratchet_measures(eval_dir: Path, min_tokens: int = config.RATCHET_MIN_TOKENS,
                     trips: Iterable[str] = ()) -> dict[str, Any]:
    """``ratchet_final``, ``ratchet_start_fires``, ``ratchet_kind``, the trips' kinds
    (``trips``: dup-check failure outputs from the transcript) and ``ratchet_split`` from
    the container's scans (:func:`ratchet_scan_lines`); None with ``ratchet_error`` when
    a scan is missing or failed."""
    trips = list(trips)
    out: dict[str, Any] = {"ratchet_final": None, "ratchet_start_fires": None,
                           "ratchet_kind": None, "ratchet_trip_kinds": None,
                           "ratchet_trip_basis": None, "ratchet_trip_clones": None,
                           "ratchet_split": None, "ratchet_error": None}
    start_rep, post_rep = _report(eval_dir, "start"), _report(eval_dir, "post")
    diff_p = eval_dir / "ratchet_diff.patch"
    if start_rep is None or post_rep is None or not diff_p.exists() or \
            (eval_dir / "ratchet_diff_error").exists():
        out["ratchet_error"] = "start_scan" if start_rep is None else \
            "post_scan" if post_rep is None else "diff"
        return out
    diff = _read_text(diff_p)
    cls = classify_changes(diff)
    added = {k: set(v) for k, v in cls["added"].items()}
    changed: dict[str, set[int]] = {}
    for d in (cls["added"], cls["modified"]):
        for k, v in d.items():
            changed.setdefault(k, set()).update(v)
    for row in _read_text(eval_dir / "ratchet_untracked.tsv").splitlines():
        path, _, n = row.partition("\t")
        try:
            k = int(n)
        except ValueError:
            continue
        if k > 0 and path:
            whole = set(range(1, k + 1))
            changed[path] = whole
            added[path] = whole
    start_files, post_files = _scan_files(eval_dir, "start"), _scan_files(eval_dir, "post")
    start_clones, start_unres = parse_clones(start_rep, start_files)
    post_clones, post_unres = parse_clones(post_rep, post_files)
    final = touching(post_clones, changed)
    lmap = LineMap(diff)

    def pre(c: Clone) -> bool:
        return matches_start_clone(_as_tuple(c), start_clones, lmap)
    # the step touches a clone the start tree had: it modifies or deletes one of its
    # lines, inserts lines inside it, or a firing clone of the post tree is that clone
    matched = [c for c in start_clones
               if any(matches_start_clone(_as_tuple(f), [c], lmap) for f in final)]
    start_touched = list(dict.fromkeys(touching(start_clones, cls["old"]) +
                                       insertions_inside(start_clones, diff) + matched))
    out["ratchet_start_fires"] = bool(start_touched)
    out["ratchet_final"] = {
        "fires": bool(final), "n_clones": len(final), "min_tokens": min_tokens,
        "clones": [_clone_dict(c) for c in final[:50]],
        "start_clones_touched": [_clone_dict(c) for c in start_touched[:20]],
        "changed_lines": sum(len(v) for v in changed.values()),
        "added_lines": sum(len(v) for v in added.values()),
        "files": {"start": len(start_files), "post": len(post_files)},
        "unresolved": {"start": start_unres, "post": post_unres}}
    out["ratchet_kind"] = ratchet_kind(final, added, bool(start_touched), pre)
    out["ratchet_final"]["preexisting"] = [pre(c) for c in final[:50]]
    classified = [classify_trip(t, start_clones, post_clones, lmap) for t in trips]
    out["ratchet_trip_kinds"] = [k for k, _ in classified]
    out["ratchet_trip_basis"] = [b for _, b in classified]
    out["ratchet_split"] = ratchet_split(out["ratchet_trip_kinds"], out["ratchet_kind"])
    out["ratchet_trip_clones"] = trip_clone_counts(trips, start_clones, post_clones, lmap)
    return out


# =========================================================================== JS functions

_IDENT = r"[A-Za-z_$][\w$]*"
_DEF_RES = (
    re.compile(rf"\bfunction\s*\*?\s*({_IDENT})\s*(?:<[^>()]*>)?\s*\("),
    re.compile(rf"(?<![\w$.])(?:const|let|var)\s+({_IDENT})\s*(?::[^=;]+)?=\s*(?:async\s+)?"
               rf"(?:function\b\s*\*?\s*(?:{_IDENT})?\s*)?(?:<[^>()]*>)?\s*\("),
    re.compile(rf"(?<![\w$.])(?:const|let|var)\s+({_IDENT})\s*(?::[^=;]+)?=\s*(?:async\s+)?"
               rf"{_IDENT}\s*=>"),
)
_CALL = re.compile(rf"(?<![\w$.])({_IDENT})\s*(?:<[^<>()]*>)?\s*\(")
_NOT_CALLS = frozenset({"if", "for", "while", "switch", "catch", "function", "return", "typeof",
                        "await", "new", "super", "import", "export", "async", "void", "in",
                        "of", "do", "else", "case", "throw", "delete", "instanceof", "yield"})


def _skip_string(text: str, i: int) -> int:
    q = text[i]
    j = i + 1
    while j < len(text):
        if text[j] == "\\":
            j += 2
            continue
        if text[j] == q:
            return j + 1
        if q != "`" and text[j] == "\n":
            return j
        j += 1
    return j


def _match(text: str, i: int, open_c: str, close_c: str) -> int:
    """Index of the bracket closing ``text[i]`` (strings and comments skipped), or -1."""
    depth = 0
    j = i
    while j < len(text):
        c = text[j]
        if c in "'\"`":
            j = _skip_string(text, j)
            continue
        if text.startswith("//", j):
            k = text.find("\n", j)
            j = len(text) if k < 0 else k
            continue
        if text.startswith("/*", j):
            k = text.find("*/", j + 2)
            j = len(text) if k < 0 else k + 2
            continue
        if c == open_c:
            depth += 1
        elif c == close_c:
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return -1


def _body_end(text: str, j: int) -> int:
    """From just after a parameter list (or an arrow's single parameter): the end of the
    function body (index of its closing brace, or of the expression body's line end)."""
    depth = 0
    k = j
    while k < len(text):
        c = text[k]
        if c in "'\"`":
            k = _skip_string(text, k)
            continue
        if c in "(<[":
            depth += 1
        elif c in ")>]" and depth > 0 and not text.startswith("=>", k - 1):
            depth -= 1
        elif depth == 0 and text.startswith("=>", k):
            m = re.compile(r"\s*").match(text, k + 2)
            s = m.end()
            if s < len(text) and text[s] == "{":
                return _match(text, s, "{", "}")
            e = text.find("\n", s)
            return len(text) - 1 if e < 0 else e
        elif depth == 0 and c == "{":
            return _match(text, k, "{", "}")
        elif depth == 0 and c == ";":
            return -1  # an overload / declaration without a body
        k += 1
    return -1


def function_spans(text: str) -> dict[str, list[tuple[int, int]]]:
    """{name: [(first line, last line)]} (1-based, inclusive) of the named functions in
    a TS/JS source: ``function f(``, ``const f = (async) (...) =>``/``function``,
    ``const f = x =>``. Approximate (no parser): enough to tell which function a line
    belongs to."""
    out: dict[str, list[tuple[int, int]]] = {}
    starts = [0]
    for m in re.finditer("\n", text):
        starts.append(m.end())

    def line_of(i: int) -> int:
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= i:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    seen: set[int] = set()
    for rx in _DEF_RES:
        for m in rx.finditer(text):
            if m.start() in seen:
                continue
            seen.add(m.start())
            if rx is _DEF_RES[2]:
                end = _body_end(text, text.index("=>", m.start()))
            else:
                close = _match(text, m.end() - 1, "(", ")")
                end = -1 if close < 0 else _body_end(text, close + 1)
            if end >= 0:
                out.setdefault(m.group(1), []).append((line_of(m.start()), line_of(end)))
    return out


def calls_on(line: str) -> set[str]:
    """Function names called on a line (``name(`` / ``name<T>(``; not methods, not the
    name a definition on that line defines)."""
    return {n for n in _CALL.findall(line) if n not in _NOT_CALLS and not _is_definition(line, n)}


class SourceIndex:
    """The post tree's dumped files (``eval/zone_post``): every named function's span and
    body, and the calls each body makes."""

    def __init__(self, files: dict[str, str]):
        self.files = files
        self.lines = {p: t.splitlines() for p, t in files.items()}
        self.defs: dict[str, list[tuple[str, int, int]]] = {}
        for p, t in files.items():
            for name, spans in function_spans(t).items():
                self.defs.setdefault(name, []).extend((p, s, e) for s, e in spans)

    def body(self, name: str) -> str:
        return "\n".join("\n".join(self.lines[p][s - 1:e]) for p, s, e in self.defs.get(name, ()))

    def body_calls(self, name: str) -> set[str]:
        return {c for p, s, e in self.defs.get(name, ())
                for ln in self.lines[p][s - 1:e] for c in calls_on(ln)} - {name}

    def spans(self, names: Iterable[str]) -> list[tuple[str, str, int, int]]:
        return [(n, p, s, e) for n in names for p, s, e in self.defs.get(n, ())]

    @classmethod
    def from_dir(cls, d: Path) -> "SourceIndex":
        files = {}
        if d.is_dir():
            for f in sorted(d.rglob("*")):
                if f.is_file():
                    files[f.relative_to(d).as_posix()] = f.read_text(errors="replace")
        return cls(files)


def site_names(sites: dict[str, Any]) -> list[str]:
    """The copy sites' function names (``sites.json``; the first word of ``function``)."""
    out: list[str] = []
    for s in sites.get("sites") or []:
        m = re.match(_IDENT, str(s.get("function") or ""))
        if m and m.group(0) not in out:
            out.append(m.group(0))
    return out


def _reach(idx: SourceIndex, start: Iterable[str], exclude: set[str], depth: int = 2) -> set[str]:
    """Zone-defined functions reachable from ``start`` through calls (``depth`` levels),
    never through an excluded one."""
    found: set[str] = set()
    frontier = {n for n in start if n in idx.defs and n not in exclude}
    for _ in range(depth):
        found |= frontier
        nxt: set[str] = set()
        for n in frontier:
            nxt |= {c for c in idx.body_calls(n) if c in idx.defs and c not in exclude}
        frontier = nxt - found
    return found | frontier


def t2_static3(idx: SourceIndex, step_diff: str, sites: dict[str, Any], markers: list[str],
               not_decision: Iterable[str] = ()) -> tuple[str | None, dict[str, Any]]:
    """Static T2 label for study 3 (plan Task 5; secondary to the judge's). The new
    consumer's code = the step's added/modified source lines outside the copy sites'
    bodies. ``helper``: it calls (directly or through one zone function) a zone-defined
    function, not itself a copy site, that a pre-existing copy site also calls (directly
    or through one) and whose body carries the zone's decision (a zone marker; Z4's
    date arithmetic excluded, spec section 3); ``copy``: else its code matches a zone
    marker or calls a copy site; else None (left to the judge)."""
    changed, _ = changed_post_lines(step_diff)
    changed = {p: v for p, v in changed.items() if is_source_file(p)}
    sites_l = site_names(sites)
    detail: dict[str, Any] = {"sites": sites_l, "changed_lines": sum(len(v) for v in changed.values())}
    if not changed:
        return None, {**detail, "reason": "no_source_change"}
    site_spans = idx.spans(sites_l)

    def in_site(p: str, ln: int) -> bool:
        return any(p == sp and s <= ln <= e for _, sp, s, e in site_spans)

    new_lines = [idx.lines[p][ln - 1] for p, lns in changed.items() if p in idx.lines
                 for ln in sorted(lns) if ln <= len(idx.lines[p]) and not in_site(p, ln)]
    new_calls = set().union(*(calls_on(t) for t in new_lines)) if new_lines else set()
    exclude = set(sites_l)
    new_reach = _reach(idx, new_calls, exclude)
    site_reach = _reach(idx, set().union(*(idx.body_calls(n) for n in sites_l)) if sites_l
                        else set(), exclude)
    rx = [re.compile(m) for m in markers]
    shared = sorted(f for f in new_reach & site_reach if f not in set(not_decision)
                    and any(r.search(idx.body(f)) for r in rx))
    hits = sorted({r.pattern for r in rx for t in new_lines if r.search(t)})
    copy_calls = sorted(new_calls & exclude)
    detail.update(new_code_lines=len(new_lines), shared_functions=shared, markers=hits,
                  calls_copy_sites=copy_calls,
                  sites_found=sorted({n for n, *_ in site_spans}))
    if not new_lines:
        return None, {**detail, "reason": "no_code_outside_sites"}
    if shared:
        return "helper", detail
    if hits or copy_calls:
        return "copy", detail
    return None, {**detail, "reason": "no_shared_call_no_marker"}


def rule_sites_touched(idx: SourceIndex, step_diff: str,
                       sites: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Rule steps (T1/T3): how many distinct functions the step changes among the copy
    sites and the zone functions they call (one level), in the post tree. A pure
    deletion counts for a function when both of its neighbouring lines are inside it."""
    changed, deletions = changed_post_lines(step_diff)
    sites_l = site_names(sites)
    helpers = sorted(set().union(*(idx.body_calls(n) for n in sites_l)) & set(idx.defs)
                     - set(sites_l)) if sites_l else []
    site_spans = idx.spans(sites_l)
    # a function nested in a site's body is part of that site, not a helper of its own
    helper_spans = [(n, p, s, e) for n, p, s, e in idx.spans(helpers)
                    if not any(p == sp and ss <= s and e <= se for _, sp, ss, se in site_spans)]
    touched: list[str] = []
    for name, p, s, e in site_spans + helper_spans:
        hit = any(s <= ln <= e for ln in changed.get(p, ())) or \
            any(s <= at - 1 and at <= e for at in deletions.get(p, ()))
        if hit and name not in touched:
            touched.append(name)
    return len(touched), {"functions": touched,
                          "sites": [n for n in touched if n in sites_l],
                          "helpers": [n for n in touched if n not in sites_l],
                          "sites_found": sorted({n for n, *_ in idx.spans(sites_l)})}


# =========================================================================== per step

def study3_fields(result: dict, *, meta: dict, chain: Any, step: Any, eval_dir: Path | None,
                  diff_text: str, transcript: list[str], sites: dict[str, Any] | None,
                  runner_trees: dict | None = None) -> dict:
    """Add the study-3 measures to a step result (T1..T4 from
    :func:`aa.chain_eval.assemble_step_result`, or T0's)."""
    from aa.static3 import step_gaming_flags
    agent = meta["agent"]
    n, segs = lint_runs(agent, transcript)
    cited, cited_detail = rule_cited(agent, transcript)
    trips = trip_outputs(agent, transcript)
    result.update({
        "study": 3, "lint_runs": n, "lint_commands": segs,
        "ratchet_trips": len(trips),
        "gaming_flags": step_gaming_flags(diff_text, meta),
        "rule_cited": cited, "rule_cited_detail": cited_detail,
        "ratchet_final": None, "ratchet_start_fires": None, "ratchet_kind": None,
        "ratchet_trip_kinds": None, "ratchet_trip_basis": None, "ratchet_split": None,
        "ratchet_trip_clones": None, "ratchet_error": None,
        "rule_sites_touched": None, "rule_sites_detail": None,
    })
    if step.kind != chain_tasks.T0_KIND:
        result.setdefault("inconsistencies_unified_step", None)
        result.setdefault("inconsistency_scope_detail", None)
    if step.kind == "consumer":
        # study 3's T2 label is the static3 one; study 2's (on R's helper list for every
        # study-3 arm, aa.chain_eval.zone_cond) is kept only as detail, so a step where
        # static3 cannot run reads None, not the study-2 label
        result["t2_reuse_detail"] = {"reason": "static3_not_run",
                                     "study2_label": result.get("t2_reuses_logic"),
                                     "study2_detail": result.get("t2_reuse_detail")}
        result["t2_reuses_logic"] = None
    if eval_dir is None:
        return result
    tc = result.get("tree_check") or {}
    fresh = _read_text(eval_dir / "start_tree_fresh").strip() or None
    rt = (runner_trees or {}).get("start")
    tc["start_fresh"] = None if not (fresh and rt) else fresh == rt
    result["tree_check"] = tc
    if result.get("eval_error") in ("evalbase", "pre_image", "start_commit"):
        return result
    if (eval_dir / "ratchet_post_rc").exists() or (eval_dir / "ratchet_start_rc").exists():
        result.update(ratchet_measures(eval_dir, trips=trips))
    step_patch = _read_text(eval_dir / STEP_PATCH)
    if step_patch.strip():
        # the evaluator's start -> agent tree patch: on a tree.tar fallback step the
        # agent's diff.patch may miss changes (flags from both, merged)
        flags = result["gaming_flags"]
        for k, v in step_gaming_flags(step_patch, meta).items():
            flags[k] = list(dict.fromkeys([*flags.get(k, []), *v]))
    if not (eval_dir / ZONE_POST).is_dir() or sites is None:
        return result
    idx = SourceIndex.from_dir(eval_dir / ZONE_POST)
    if step.kind == "consumer":
        label, det = t2_static3(idx, step_patch, sites, (chain.t2_reuse or {}).get("markers") or [],
                                T2_NOT_DECISION.get(chain.zone, ()))
        study2 = result["t2_reuse_detail"]
        det["study2_label"] = study2["study2_label"]
        det["study2_detail"] = study2["study2_detail"]
        result["t2_reuses_logic"], result["t2_reuse_detail"] = label, det
    if step.kind == "rule":
        result["rule_sites_touched"], result["rule_sites_detail"] = rule_sites_touched(
            idx, step_patch, sites)
    return result


# =========================================================================== behaviour check

SCOPE_REPORT = "scope_tests.json"


def scope_outcome(eval_dir: Path, in_scope: dict[str, str]) -> tuple[list[str] | None, dict]:
    """Study-3 pilot, blocking item 9: (``inconsistencies_unified_step``, detail) from a
    step's run of the zone's T0 inconsistency tests still in scope at that step
    (:func:`aa.chains.scope_tests`, ``tasks3/inconsistency-scope.json``). The ids whose
    test did not pass on the post tree; None when no test is in scope or the run did not
    happen (missing, not "nothing unified")."""
    detail: dict[str, Any] = {"in_scope": dict(in_scope)}
    if not in_scope:
        return None, {**detail, "reason": "no_test_in_scope"}
    rep_p = Path(eval_dir) / SCOPE_REPORT
    try:
        report = json.loads(rep_p.read_text())
    except (OSError, ValueError):
        reason = "stage_error" if (Path(eval_dir) / "scope_stage_error").exists() else "not_run"
        return None, {**detail, "reason": reason}
    results = chain_tasks.t0_test_results(report, in_scope)
    detail["results"] = results
    if any(v == "missing" for v in results.values()):
        detail["reason"] = "test_missing_in_report"
        return None, detail
    return sorted({in_scope[n] for n, v in results.items() if v != "passed"}), detail


def step_scope(zone: str, step_id: str, t0_root: Path | None = None,
               ) -> tuple[chain_tasks.T0Task | None, dict[str, str]]:
    """(the zone's T0 task, its tests in scope at ``step_id``); (None, {}) for a zone
    without T0 tests."""
    try:
        t0 = chain_tasks.load_t0(zone, t0_root)
    except chain_tasks.T0Error:
        return None, {}
    if not t0.tests:
        return t0, {}
    return t0, chain_tasks.scope_tests(t0, step_id,
                                       chain_tasks.load_inconsistency_scope(t0_root))


# =========================================================================== T0

def untouched_reference_script() -> str:
    """The untouched-R reference of the T0 evaluation, one container: the full loot-core
    suite seeded (/out/suite.json, the base of the related-tests comparison) and the
    probe (/out/probe/)."""
    from aa.checker import SEED_CONFIG_DST, SEED_CONFIG_SRC, SEED_DST, SEED_SRC, vitest_clean_cmd
    q = shlex.quote
    suite = " ".join(q(a) for a in vitest_clean_cmd("/out/suite.json", []))
    return "\n".join([
        "set -u", f"cd /work/actual/{config.LOOT}",
        f"cp /checker/{SEED_SRC.name} {SEED_DST} && cp /checker/{SEED_CONFIG_SRC.name} "
        f"{SEED_CONFIG_DST} || exit 3",
        f"ENV=node timeout 3600 {suite} > /out/suite.log 2>&1; echo $? > /out/suite_rc",
        *chain_tasks.t0_probe_lines(),
        "echo done > /out/done",
    ]) + "\n"


REFERENCE_FILE = config.WORK / "study3" / "t0-untouched-R.json"
_REF_LOCK = threading.Lock()


def untouched_reference(path: Path = REFERENCE_FILE, *, image: str = "R",
                        runner: Callable[[list[str], int], int] | None = None) -> dict[str, Any]:
    """The cached untouched-R reference ({"image", "probe", "suite", ...}), rebuilt when
    the image id changed or it is missing (one container, :func:`untouched_reference_script`)."""
    from aa.checker import SEED_SRC
    from aa.probe2 import probe_doc
    with _REF_LOCK:
        image_id = chain_tasks._image_id(image)
        try:
            ref = json.loads(Path(path).read_text())
            if ref.get("image_id") == image_id and ref.get("probe_ok"):
                return ref
        except (OSError, ValueError):
            pass
        run = runner or (lambda argv, t: subprocess.run(argv, capture_output=True, text=True,
                                                         timeout=t).returncode)
        with tempfile.TemporaryDirectory(prefix="aa-t0-ref-") as tmp:
            out = Path(tmp).resolve()
            argv = ["docker", "run", "--rm", "--name", f"aa-t0-ref-{out.name}"[:60],
                    "--network", "none", "--cpus", "2", "--memory", "6g",
                    "-v", f"{SEED_SRC.parent}:/checker:ro", "-v", PROBE_MOUNT,
                    "-v", f"{out}:/out", f"aa-actual:{image}", "bash", "-c",
                    untouched_reference_script()]
            rc = run(argv, 2 * 3600)
            suite = _load(out / "suite.json")
            probe = probe_doc(out / "probe", _load(out / "probe" / "report.json"),
                              f"/work/actual/{config.LOOT}")
            ref = {"image": f"aa-actual:{image}", "image_id": image_id,
                   "date": datetime.date.today().isoformat(), "docker_rc": rc,
                   "finished": (out / "done").exists(), "suite_rc": _read_int(out / "suite_rc"),
                   "suite": suite, "probe": probe,
                   "probe_ok": bool((out / "done").exists() and not probe.get("failed")
                                    and probe.get("db") is not None
                                    and probe.get("template") is not None)}
        if not ref["probe_ok"]:
            raise RuntimeError(f"untouched-R reference failed: rc={rc} probe={probe.get('failed')}")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(ref) + "\n")
        return ref


def _load(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def t0_outcome(eval_dir: Path, t0: chain_tasks.T0Task, reference: dict[str, Any],
               exclusions: list[dict]) -> dict[str, Any]:
    """The T0 checks read back: probe vs the untouched-R reference minus exclusions,
    inconsistency tests, typecheck, lint, related tests."""
    from aa.probe2 import diff_probe, probe_doc
    loot_root = f"/work/actual/{config.LOOT}"
    doc = probe_doc(eval_dir / "probe", _load(eval_dir / "probe" / "report.json"), loot_root)
    ref = reference["probe"]
    raw, kept = diff_probe(ref, doc), diff_probe(ref, doc, exclusions)
    tests = chain_tasks.t0_test_results(_load(eval_dir / "tests.json"), t0.tests) \
        if t0.tests else {}
    unified = sorted({t0.tests[n] for n, s in tests.items() if s != "passed"})
    rc = {k: _read_int(eval_dir / f"{k}_rc") for k in
          ("typecheck", "typecheck_full", "lint", "lint_root", "related")}
    related = None
    if (eval_dir / "related_files").exists() and _read_text(eval_dir / "related_files").strip():
        related = chain_tasks.t0_related_compare(reference.get("suite"),
                                                 _load(eval_dir / "related.json"), rc["related"],
                                                 _load(eval_dir / chain_tasks.RELATED_RETRY))
    return {
        "probe_changed_cases": kept, "probe_changed_raw": raw,
        "probe_unchanged": not kept,
        "probe_passed": doc.get("passed"),
        "t0_tests": tests, "inconsistencies_unified": unified,
        "typecheck_ok": None if rc["typecheck"] is None else rc["typecheck"] == 0,
        "typecheck_full_ok": None if rc["typecheck_full"] is None else rc["typecheck_full"] == 0,
        "lint_ok": None if rc["lint"] is None else rc["lint"] == 0,
        "lint_root_ok": None if rc["lint_root"] is None else rc["lint_root"] == 0,
        "related": related, "related_ok": None if related is None else related["ok"],
    }


def write_t0_packet(step_dir: Path, t0: chain_tasks.T0Task) -> Path | None:
    """``eval/t0_packet/``: what the completeness / interface judge reads (spec section
    3): the T0 statement, the step's diff (start -> agent tree) and the zone's copy sites
    (``sites.json``, with the inconsistencies to preserve). Blinding and batching are the
    design-review export's (plan Task 7)."""
    ev = step_dir / EVAL_DIR
    patch = _read_text(ev / STEP_PATCH)
    if not patch.strip():
        return None
    d = ev / T0_PACKET
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / STATEMENT).write_text(t0.statement())
    (d / "diff.patch").write_text(patch)
    (d / "sites.json").write_text(json.dumps(t0.sites, indent=2) + "\n")
    return d


# The T0 container: the image build, two jscpd + two ratchet scans, typecheck (tsgo -b,
# yarn typecheck), both lints, related tests, the T0 tests and the probe (their own
# in-container timeouts sum to about 3 h) + slack.
T0_HOST_TIMEOUT_S = 4 * 3600


# T0 fields that stay None when the eval did not finish (``eval_error`` set)
T0_UNFINISHED_NONE = ("probe_changed_cases", "probe_changed_raw", "probe_unchanged",
                      "probe_passed", "t0_tests", "inconsistencies_unified")


def assemble_t0_result(meta: dict, chain: Any, t0: chain_tasks.T0Task, diff_text: str,
                       eval_dir: Path | None, transcript: list[str],
                       eval_error: str | None = None, *, runner_trees: dict | None = None,
                       reference: dict[str, Any] | None = None,
                       exclusions: list[dict] = ()) -> dict:
    """Pure: RC's T0 ``result.json`` (``step`` 0, ``kind`` refactor; nothing here is a
    T1..T4 metric) from agent.json, the agent's diff and the eval outputs."""
    from aa.chain_eval import (EVAL_ERRORS_NOTHING_RAN, DIFF_APPLIED, _chain_value, read_jscpd,
                               usage_fields)
    from aa.evaluate import (EVALUATED, contamination, diff_files, diff_stats, extract_trace,
                             touches_test_infra)
    agent, cond = meta["agent"], meta["cond"]
    status = meta.get("status")
    files = chain.files_for(cond)
    result: dict[str, Any] = {
        "agent": agent, "cond": cond, "zone": chain.zone, "chain": _chain_value(meta["chain"]),
        "step": 0, "step_id": chain_tasks.T0_ID, "kind": chain_tasks.T0_KIND, "status": status,
        "correct": False,
        "probe_changed_cases": None, "probe_changed_raw": None, "probe_unchanged": None,
        "probe_passed": None, "t0_tests": None, "inconsistencies_unified": None,
        "typecheck_ok": None, "typecheck_full_ok": None, "lint_ok": None, "lint_root_ok": None,
        "related": None, "related_ok": None,
        **usage_fields(meta, transcript),
        "wall_s": meta.get("wall_s"),
        "diff": diff_stats(diff_text),
        "agent_touched_test_infra": touches_test_infra(diff_text),
        "agent_touched_hidden_paths": sorted(diff_files(diff_text) & set(t0.hidden)),
        "agent_tree_from": "tar" if meta.get("tree_fallback") and not meta.get("diff_ok")
        else "diff",
        "diff_applies_to_pre_image": None, "tree_check": None,
        "duplication_pre": None, "duplication_post": None,
        "trace": extract_trace(agent, transcript),
        "contamination_markers": contamination(agent, transcript, ()),
        "eval_error": None, "t0_packet": None,
    }
    result["contamination_flag"] = bool(result["contamination_markers"])
    if status not in EVALUATED:
        result["eval_error"] = "not_evaluated"
        return result
    if eval_error is None and eval_dir is not None:
        eval_error = _read_text(eval_dir / "eval_error").strip() or None
    if eval_error is None and (eval_dir is None or not (eval_dir / "eval_done").exists()):
        eval_error = "container"
    result["eval_error"] = eval_error
    if eval_dir is None:
        return result
    rt = runner_trees or {}
    mine = {k: _read_text(eval_dir / f"{k}_tree").strip() or None for k in ("start", "post")}
    result["tree_check"] = {k: None if not (rt.get(k) and mine[k]) else rt[k] == mine[k]
                            for k in ("start", "post")}
    result["duplication_pre"] = read_jscpd(eval_dir, "jscpd_pre", files)
    if eval_error in EVAL_ERRORS_NOTHING_RAN + ("start_commit",):
        if eval_error == "diff_apply":
            result["diff_applies_to_pre_image"] = False
        return result
    result["diff_applies_to_pre_image"] = (eval_dir / DIFF_APPLIED).exists() or None
    result["duplication_post"] = read_jscpd(eval_dir, "jscpd_post", files)
    if reference is None:
        return result
    outcome = t0_outcome(eval_dir, t0, reference, list(exclusions))
    if eval_error is not None:
        # the eval did not finish (container, eval_timeout, a restore or seed failure):
        # missing probe / test outputs are not a changed probe or a unified inconsistency
        # (that would count infrastructure failures in H3); checks that did run (their
        # rc files) are kept
        outcome.update({k: None for k in T0_UNFINISHED_NONE})
    result.update(outcome)
    ran = (eval_dir / "probe" / "report.json").exists() and \
        (not t0.tests or (eval_dir / "tests.json").exists())
    result["correct"] = bool(eval_error is None and ran and result["probe_unchanged"]
                             and not result["inconsistencies_unified"])
    return result


class T0Step:
    """T0 as :func:`study3_fields` needs it (no consumer, no rule)."""
    id = chain_tasks.T0_ID
    kind = chain_tasks.T0_KIND


def evaluate_t0_step(step_dir: Path, *, tasks_root: Path | None = None,
                     execute: Callable[[list[str], int], int] | None = None,
                     checker_dir: Path | None = None, t0_root: Path | None = None,
                     reference: Any = None, tests: bool = True) -> dict | None:
    """Evaluate RC's T0 step dir and write its ``result.json`` (and the T0 packet).
    ``reference``: the untouched-R reference dict, a callable returning it, or None
    (:func:`untouched_reference`, cached)."""
    from aa.chain_eval import (EVAL_ERRORS_NOTHING_RAN, carry_plan, chain_eval_docker_argv,
                               chain_eval_script, load_chain, step_meta)
    from aa.checker import SEED_SRC
    from aa.evaluate import EVALUATED, _write_json, docker_execute, stage_hidden_tests
    execute = execute or docker_execute
    checker_dir = checker_dir or SEED_SRC.parent
    step_dir = Path(step_dir).resolve()
    if not (step_dir / "agent.json").exists():
        return None
    meta = step_meta(step_dir)
    status = meta.get("status")
    if status == "infra":
        return None
    transcript = _read_text(step_dir / "transcript.jsonl").splitlines()
    diff_text = _read_text(step_dir / "diff.patch")
    chain = load_chain(meta["zone"], tasks_root)
    t0 = chain_tasks.load_t0(meta["zone"], t0_root)
    exclusions = chain_tasks.load_probe_exclusions(t0_root)
    runner_trees = {"start": _read_text(step_dir / "start_tree").strip()
                    or (meta.get("carry") or {}).get("start_tree"),
                    "post": _read_text(step_dir / "post_tree").strip() or meta.get("post_tree")}
    eval_error: str | None = None
    eval_dir: Path | None = None
    ref: dict | None = None
    if status in EVALUATED:
        eval_dir = step_dir / EVAL_DIR
        try:
            if eval_dir.exists():
                shutil.rmtree(eval_dir)
            eval_dir.mkdir()
            plan = carry_plan(step_dir, meta, 1)
            if plan != {"from": "image", "patches": []}:
                raise ValueError(f"T0 must start from the image, not {plan}")
            staged = stage_hidden_tests(t0.dir, list(t0.hidden), meta["cond"], eval_dir)
            if sorted(staged) != sorted(t0.hidden):
                raise ValueError("T0 hidden tests not all staged")
            tar = not (step_dir / "diff_ok").exists() and (step_dir / "tree.tar").exists()
            script = chain_eval_script(chain_tasks.T0_ID, plan,
                                       agent_tree="tar" if tar else "diff",
                                       hidden_tests=staged, zone_files=chain.files_for(meta["cond"]),
                                       zone_dirs=chain.dirs_for(meta["cond"]), t0=True,
                                       tests=tests)
            argv = chain_eval_docker_argv(meta["cond"], step_dir, eval_dir, script, checker_dir,
                                          extra=["-v", PROBE_MOUNT])
        except (OSError, KeyError, ValueError) as exc:
            eval_error = f"setup:{type(exc).__name__}: {exc}"[:300]
            eval_dir = None
        else:
            if tests:
                try:
                    ref = reference() if callable(reference) else reference or untouched_reference()
                except Exception as exc:  # noqa: BLE001 - recorded, the step is not lost
                    eval_error = f"t0_reference:{type(exc).__name__}: {exc}"[:300]
            try:
                execute(argv, T0_HOST_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                eval_error = eval_error or "eval_timeout"
            except Exception:  # docker missing / daemon down -> `container`
                pass
    meta = {**meta, "diff_ok": (step_dir / "diff_ok").exists(),
            "tree_fallback": (step_dir / "tree.tar").exists()}
    result = assemble_t0_result(meta, chain, t0, diff_text, eval_dir, transcript, eval_error,
                                runner_trees=runner_trees, reference=ref, exclusions=exclusions)
    study3_fields(result, meta=meta, chain=chain, step=T0Step(), eval_dir=eval_dir,
                  diff_text=diff_text, transcript=transcript, sites=t0.sites,
                  runner_trees=runner_trees)
    if eval_dir is not None and result["eval_error"] not in EVAL_ERRORS_NOTHING_RAN:
        pk = write_t0_packet(step_dir, t0)
        result["t0_packet"] = None if pk is None else pk.relative_to(step_dir).as_posix()
    _write_json(step_dir / "result.json", result)
    return result
