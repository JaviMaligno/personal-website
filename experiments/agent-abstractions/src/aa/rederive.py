"""Re-derive fields of finished steps through harness code (study-3 pilot, blocking items
1-3), without touching the runner's raw outputs (transcript.jsonl, diff.patch, stderr).

- ``aa chain reclassify --runs DIR``: re-apply the run-status rule of
  :func:`aa.runner.classify_status` (network stall / no agent activity at the wall limit
  = ``infra``) to finished steps. Only the change to ``infra`` is applied (that is the
  rule that changed); agent.json's ``status`` is rewritten and the change kept in
  ``status_reclassified`` ({from, to, reason, ...}); result.json and chain.json follow.
  A step that becomes ``infra`` is re-run by ``aa chain run``, which removes the later
  steps of its chain (they were built on its tree).
- ``aa chain reparse --runs DIR``: re-parse every step's transcript with the current
  parser (:func:`aa.chain_eval.usage_fields`: Claude usage summed over every ``result``,
  Codex usage missing without ``turn.completed``) into result.json's ``tokens`` /
  ``turns`` / ``tool_calls`` (+ ``usage_missing``, ``usage_source``, ``usage_reparsed``),
  then re-summarise the chain (``chain_result.json`` totals). agent.json keeps the
  runner's record.

Every applied change is appended to ``<runs>/rederive-log.jsonl`` and kept on the
rewritten record (``status_reclassified``, ``rederived``). Derived chain files have a
log record too (amendment 2026-10-12c): a reclassification records the chain.json
``status`` change (``chain_status``), and every chain summary rewritten by a re-derivation
(``chain_result.json`` + ``cumulative.patch``) a ``resummarise_chain`` record (changed
keys with old/new values, the patch's sha256 before/after). ``aa chain record-summaries``
writes the same records, marked ``retrospective``, for summaries rewritten before this
rule, from a backup of the derived files taken before them.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aa import config

LOG_FILE = "rederive-log.jsonl"
RECLASSIFY_RULE = ("aa.runner.classify_status 2026-10-12: transport stall at the end of the "
                   "transcript, or no agent activity at the wall limit, is infra")
USAGE_RULE = ("aa.chain_eval.usage_fields 2026-10-12: Claude usage/turns summed over every "
              "result event; Codex tokens None without turn.completed")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def _write_json(p: Path, obj: dict) -> None:
    p.write_text(json.dumps(obj, indent=2) + "\n")


def _transcript(step_dir: Path) -> list[str]:
    p = step_dir / "transcript.jsonl"
    return p.read_text(errors="replace").splitlines() if p.exists() else []


def step_dirs(root: Path) -> list[Path]:
    """Every ``<agent>/<cond>/<zone>/<chain>/T<k>`` with an agent.json, sorted."""
    return sorted(p.parent for p in Path(root).glob("*/*/*/*/T*/agent.json"))


def _rel(root: Path, d: Path) -> str:
    return d.resolve().relative_to(Path(root).resolve()).as_posix()


def _log(root: Path, records: list[dict]) -> None:
    if not records:
        return
    with (Path(root) / LOG_FILE).open("a") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


# --------------------------------------------------------------------------- item 1

def reclassify_step(step_dir: Path) -> dict | None:
    """The status change the current rule makes on a finished (``ok``/``timeout``) step,
    or None. Only a change to ``infra`` is returned (``reason``: ``transport_stall`` or
    ``no_agent_activity``); any other difference is reported under ``other``."""
    from aa.agents import parse_stream, transport_stalled
    from aa.runner import classify_status, no_agent_activity
    meta = _read_json(step_dir / "agent.json")
    if not meta or meta.get("status") not in ("ok", "timeout"):
        return None
    lines = _transcript(step_dir)
    agent = meta["agent"]
    usage, outcome = parse_stream(agent, lines)
    stalled = transport_stalled(agent, lines)
    turn_limit = int((meta.get("limits") or {}).get("turns") or config.TURN_LIMIT)
    new = classify_status(outcome, meta.get("exit_code"), usage, turn_limit, stalled=stalled)
    if new == meta["status"]:
        return None
    rec = {"from": meta["status"], "to": new, "outcome": outcome,
           "exit_code": meta.get("exit_code"), "stalled": stalled,
           "usage_parsed": asdict(usage)}
    if new != "infra":
        return {**rec, "other": True}
    rec["reason"] = "transport_stall" if stalled else (
        "no_agent_activity" if no_agent_activity(usage) else "parsed_infra")
    return rec


def _set_chain_status(chain_dir: Path, step_id: str, status: str) -> dict | None:
    """Set one step's status in chain.json; returns the chain ``status`` change
    ({from, to}), or None when chain.json has no such step."""
    from aa.chain_runner import chain_status
    p = chain_dir / "chain.json"
    rec = _read_json(p)
    if not rec or step_id not in (rec.get("steps") or {}):
        return None
    before = rec.get("status")
    rec["steps"][step_id] = status
    rec["status"] = chain_status(rec["steps"])
    _write_json(p, rec)
    return {"from": before, "to": rec["status"]}


def reclassify_runs(root: Path, apply: bool = True,
                    log: Callable[[str], None] = print) -> dict[str, list[dict]]:
    """``aa chain reclassify``: {"applied": [...], "other": [...]} (``other``: status
    differences of a rule that did not change, reported only)."""
    root = Path(root)
    applied: list[dict] = []
    other: list[dict] = []
    for d in step_dirs(root):
        ch = reclassify_step(d)
        if ch is None:
            continue
        ch = {"step": _rel(root, d), **ch}
        if ch.pop("other", False):
            other.append(ch)
            log(f"{ch['step']}: {ch['from']} -> {ch['to']} (not applied: rule unchanged)")
            continue
        ch.update({"at": _now(), "by": "aa chain reclassify", "rule": RECLASSIFY_RULE})
        applied.append(ch)
        log(f"{ch['step']}: {ch['from']} -> infra ({ch['reason']})"
            + ("" if apply else " [dry run]"))
        if not apply:
            continue
        record = {k: ch[k] for k in ("from", "to", "reason", "outcome", "exit_code", "at",
                                     "by", "rule")}
        meta = _read_json(d / "agent.json")
        meta["status"] = "infra"
        meta["status_reclassified"] = record
        _write_json(d / "agent.json", meta)
        res = _read_json(d / "result.json")
        if res is not None:
            res["status"] = "infra"
            res["status_reclassified"] = record
            _write_json(d / "result.json", res)
        ch["chain_status"] = _set_chain_status(d.parent, d.name, "infra")
    if apply:
        _log(root, [{"kind": "reclassify", **r} for r in applied])
    return {"applied": applied, "other": other}


# --------------------------------------------------------------------------- chain files

SUMMARY_FILES = ("chain_result.json", "cumulative.patch")


def _sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def _dict_changes(old: dict | None, new: dict | None) -> dict:
    old, new = old or {}, new or {}
    return {k: {"old": old.get(k), "new": new.get(k)}
            for k in sorted(set(old) | set(new)) if old.get(k) != new.get(k)}


def resummarise_chain(root: Path, chain_dir: Path, tasks_root: Path | None, *, by: str,
                      rule: str) -> dict | None:
    """Rewrite a chain's summary (:func:`aa.chain_eval.summarise_chain`:
    ``chain_result.json`` and ``cumulative.patch``) and return its log record, or None
    when neither file changed: the top-level keys of chain_result.json that changed
    (old / new) and cumulative.patch's sha256 before / after."""
    from aa import chain_eval
    cr = chain_dir / "chain_result.json"
    cum = chain_dir / "cumulative.patch"
    old, sha_before = _read_json(cr), _sha(cum)
    chain_eval.summarise_chain(chain_dir, chain_eval.load_chain(chain_dir.parts[-2], tasks_root))
    new, sha_after = _read_json(cr), _sha(cum)
    changed = _dict_changes(old, new)
    if not changed and sha_before == sha_after:
        return None
    return {"kind": "resummarise_chain", "chain": _rel(root, chain_dir), "changed": changed,
            "cumulative_patch": {"sha256_before": sha_before, "sha256_after": sha_after,
                                 "changed": sha_before != sha_after},
            "at": _now(), "by": by, "rule": rule}


SUMMARY_RULE = ("aa.chain_eval.summarise_chain: chain_result.json and cumulative.patch "
                "rewritten from the chain's step results (cumulative.patch is the last "
                "step's eval/post_tree.patch, copied verbatim since ae85094, 2026-10-08)")


def record_past_summaries(root: Path, before: Path, *, last_step: str | None = None,
                          tasks_root: Path | None = None,
                          log: Callable[[str], None] = print) -> list[dict]:
    """``aa chain record-summaries``: retrospective ``resummarise_chain`` records for chain
    summaries rewritten without one (amendment 2026-10-12c), from ``before``, a backup of
    the derived chain files (same relative layout) taken before the rewrite. Per chain:
    chain_result.json and chain.json differences against the backup; cumulative.patch
    (not in the backup) checked against its source, the last step's
    ``eval/post_tree.patch``: equal bytes now, and the source older than the backup's
    chain_result.json (so the content it replaced, written from the same unchanged file
    by the same code, was the same), and its files / added / removed counts equal to
    the backup's. A chain already recorded is skipped; nothing but the log is written."""
    from aa.chain_eval import load_chain
    root, before = Path(root), Path(before)
    logp = root / LOG_FILE
    done = set()
    if logp.exists():
        for line in logp.read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("kind") == "resummarise_chain" and r.get("retrospective"):
                done.add(r.get("chain"))
    out: list[dict] = []
    for cr in sorted(root.glob("*/*/*/*/chain_result.json")):
        c = cr.parent
        rel = _rel(root, c)
        b_cr = before / rel / "chain_result.json"
        if rel in done or not b_cr.exists():
            continue
        old, new = _read_json(b_cr), _read_json(cr)
        cr_changed = _dict_changes(old, new)
        b_ch = before / rel / "chain.json"
        ch_changed = _dict_changes(_read_json(b_ch), _read_json(c / "chain.json")) \
            if b_ch.exists() else None
        cum = c / "cumulative.patch"
        cum_rec = None
        if cum.exists():
            last = last_step or load_chain(c.parts[-2], tasks_root).steps[-1].id
            src = c / last / "eval" / "post_tree.patch"
            b_mtime = b_cr.stat().st_mtime
            stats_old = (old or {}).get("cumulative_diff") or {}
            stats_new = (new or {}).get("cumulative_diff") or {}
            keys = [k for k in ("files", "added", "removed") if k in stats_old]
            cum_rec = {
                "sha256": _sha(cum), "source": f"{last}/eval/post_tree.patch",
                "equals_source": src.exists() and src.read_bytes() == cum.read_bytes(),
                "source_older_than_backup": src.exists() and src.stat().st_mtime < b_mtime,
                "rewritten_after_backup": cum.stat().st_mtime > b_mtime,
                "stats_equal_before": bool(keys) and all(
                    stats_old.get(k) == stats_new.get(k) for k in keys),
                "previous_content_kept": False}
        if not cr_changed and not ch_changed and not (cum_rec and cum_rec["rewritten_after_backup"]):
            continue
        rec = {"kind": "resummarise_chain", "retrospective": True, "chain": rel,
               "chain_result_changed": cr_changed, "chain_json_changed": ch_changed,
               "cumulative_patch": cum_rec, "at": _now(), "by": "aa chain record-summaries",
               "rule": SUMMARY_RULE, "backup": str(before)}
        out.append(rec)
        log(f"{rel}: chain_result keys {sorted(cr_changed)}; chain.json "
            f"{sorted(ch_changed or {})}; cumulative.patch "
            + ("-" if cum_rec is None else
               f"equals source {cum_rec['equals_source']}, stats equal {cum_rec['stats_equal_before']}"))
    _log(root, out)
    return out


# --------------------------------------------------------------------------- items 2-3

USAGE_RESULT_KEYS = ("tokens", "turns", "tool_calls")


def reparse_step(step_dir: Path) -> tuple[dict, dict] | None:
    """(old, new) usage fields of a step's result.json, or None without a result."""
    from aa.chain_eval import usage_fields
    res = _read_json(step_dir / "result.json")
    meta = _read_json(step_dir / "agent.json")
    if res is None or meta is None:
        return None
    new = usage_fields(meta, _transcript(step_dir))
    old = {k: res.get(k) for k in USAGE_RESULT_KEYS}
    return old, new


def reparse_runs(root: Path, apply: bool = True, tasks_root: Path | None = None,
                 engines: tuple[str, ...] | None = None,
                 log: Callable[[str], None] = print) -> list[dict]:
    """``aa chain reparse``: rewrite result.json usage fields from the transcripts;
    returns the steps whose tokens / turns / tool calls changed (``old``, ``new``).
    ``engines``: only agents of these engines (``claude``, ``codex``)."""
    root = Path(root)
    changed: list[dict] = []
    chains: set[Path] = set()
    for d in step_dirs(root):
        meta = _read_json(d / "agent.json") or {}
        if engines and config.engine(meta.get("agent", "")) not in engines:
            continue
        got = reparse_step(d)
        if got is None:
            continue
        old, new = got
        new_vals = {k: new[k] for k in USAGE_RESULT_KEYS}
        if old != new_vals:
            rec = {"step": _rel(root, d), "old": old, "new": new_vals,
                   "usage_missing": new["usage_missing"], "at": _now(),
                   "by": "aa chain reparse", "rule": USAGE_RULE}
            changed.append(rec)
            log(f"{rec['step']}: tokens {old.get('tokens')} -> {new['tokens']}; turns "
                f"{old.get('turns')} -> {new['turns']}" + ("" if apply else " [dry run]"))
        if not apply:
            continue
        res = _read_json(d / "result.json")
        before = {k: res.get(k) for k in (*USAGE_RESULT_KEYS, "usage_missing", "usage_source",
                                          "usage_reparsed")}
        res.update(new)
        if old != new_vals:
            res.setdefault("rederived", []).append(
                {"what": "usage", "old": old, "new": new_vals, "at": changed[-1]["at"],
                 "by": "aa chain reparse", "rule": USAGE_RULE})
        after = {k: res.get(k) for k in before}
        if after != before:
            _write_json(d / "result.json", res)
            chains.add(d.parent)
    if apply:
        summaries = []
        for c in sorted(chains):
            try:
                rec = resummarise_chain(root, c, tasks_root, by="aa chain reparse",
                                        rule=SUMMARY_RULE)
            except Exception as exc:  # noqa: BLE001 - one chain never stops the batch
                log(f"{c}: chain summary not rewritten: {type(exc).__name__}: {exc}")
                continue
            if rec is not None:
                summaries.append(rec)
        _log(root, [{"kind": "reparse_usage", **r} for r in changed] + summaries)
    return changed


def usage_change_summary(changed: list[dict]) -> dict[str, Any]:
    """Per agent: steps changed, steps now missing, and the token / turn deltas."""
    out: dict[str, Any] = {}
    for r in changed:
        agent = r["step"].split("/")[0]
        o, n = r["old"], r["new"]
        a = out.setdefault(agent, {"steps": 0, "now_missing": 0, "input_delta": 0,
                                   "output_delta": 0, "turns_delta": 0})
        a["steps"] += 1
        if n["tokens"]["input"] is None:
            a["now_missing"] += 1
        else:
            a["input_delta"] += n["tokens"]["input"] - int((o.get("tokens") or {}).get("input") or 0)
            a["output_delta"] += n["tokens"]["output"] - int((o.get("tokens") or {}).get("output") or 0)
        a["turns_delta"] += int(n["turns"] or 0) - int(o.get("turns") or 0)
    return out


# --------------------------------------------------------------------------- item 4

TRIP_RULE = ("aa.chain_eval3.classify_trip 2026-10-12: each RL trip's clones against the "
             "start tree as at the trip (final diff only where the clone is unchanged in "
             "the post tree, else the trip's lines read as start-tree lines)")
TRIP_FIELDS = ("ratchet_trip_kinds", "ratchet_trip_basis", "ratchet_split",
               "ratchet_trip_clones")
TRIP_CLONES_RULE = ("aa.chain_eval3.trip_clone_counts 2026-10-12c: start-tree clones the "
                    "trips listed (L), those still a clone of the post tree (Rm), trip "
                    "clones matching no start clone, unreadable trips (amendment "
                    "2026-10-12b, item 6)")


def retrip_step(step_dir: Path) -> tuple[dict, dict] | None:
    """(old, new) trip fields of a study-3 step from its eval outputs (host only, no
    container); None without a result, an eval dir with both ratchet scans, or trips
    and a recorded split. The final-tree fields are recomputed too and must not change
    (``ratchet_final`` / ``ratchet_kind``: same inputs, same rule)."""
    from aa import chain_eval3 as ce3
    res = _read_json(step_dir / "result.json")
    ev = step_dir / "eval"
    if res is None or res.get("study") != 3 or not (ev / "ratchet_post_rc").exists():
        return None
    meta = _read_json(step_dir / "agent.json") or {}
    trips = ce3.trip_outputs(meta.get("agent", res.get("agent")), _transcript(step_dir))
    m = ce3.ratchet_measures(ev, trips=trips)
    if m.get("ratchet_error") or m.get("ratchet_kind") != res.get("ratchet_kind"):
        raise ValueError(f"{step_dir}: final-tree ratchet fields differ on recompute "
                         f"({res.get('ratchet_kind')} -> {m.get('ratchet_kind')}, "
                         f"error {m.get('ratchet_error')})")
    return {k: res.get(k) for k in TRIP_FIELDS}, {k: m.get(k) for k in TRIP_FIELDS}


def retrip_runs(root: Path, apply: bool = True,
                log: Callable[[str], None] = print) -> list[dict]:
    """``aa chain rederive-trips``: rewrite ``ratchet_trip_kinds`` / ``ratchet_split`` (+
    ``ratchet_trip_basis``, ``ratchet_trip_clones``) of study-3 steps from their eval
    outputs and transcripts; returns (and records) every step whose fields changed."""
    root = Path(root)
    changed: list[dict] = []
    for d in step_dirs(root):
        got = retrip_step(d)
        if got is None:
            continue
        old, new = got
        if old == new:
            continue
        # every field change is recorded (amendment 2026-10-12c), not only kind changes
        rule = TRIP_RULE if (old["ratchet_trip_kinds"], old["ratchet_split"],
                             old["ratchet_trip_basis"]) != (
            new["ratchet_trip_kinds"], new["ratchet_split"], new["ratchet_trip_basis"]) \
            else TRIP_CLONES_RULE
        rec = {"step": _rel(root, d), "old": old, "new": new, "at": _now(),
               "by": "aa chain rederive-trips", "rule": rule}
        changed.append(rec)
        log(f"{rec['step']}: trips {old['ratchet_trip_kinds']} -> "
            f"{new['ratchet_trip_kinds']} ({new['ratchet_trip_basis']}); split "
            f"{old['ratchet_split']} -> {new['ratchet_split']}; trip clones "
            f"{old['ratchet_trip_clones']} -> {new['ratchet_trip_clones']}"
            + ("" if apply else " [dry run]"))
        if not apply:
            continue
        res = _read_json(d / "result.json")
        res.update(new)
        res.setdefault("rederived", []).append(
            {"what": "ratchet_trips", "old": old, "new": new, "at": rec["at"],
             "by": "aa chain rederive-trips", "rule": rule})
        _write_json(d / "result.json", res)
    if apply:
        _log(root, [{"kind": "rederive_trips", **r} for r in changed])
    return changed


# --------------------------------------------------------------------------- item 9

BEHAVIOUR_DIR = "eval_behaviour"
BEHAVIOUR_RULE = ("aa.chain_eval3.scope_outcome 2026-10-12: the zone's T0 inconsistency "
                  "tests not superseded at the step (tasks3/inconsistency-scope.json) on the "
                  "step's post tree")
BEHAVIOUR_FIELDS = ("inconsistencies_unified_step", "inconsistency_scope_detail")


def behaviour_check_step(step_dir: Path, *, execute: Callable | None = None,
                         tasks_root: Path | None = None, t0_root: Path | None = None,
                         checker_dir: Path | None = None) -> tuple[dict, dict] | None:
    """(old, new) behaviour-check fields of one evaluated study-3 T1..T4 step. The post
    tree is rebuilt in a fresh container of the arm's image exactly as the evaluator
    does (``eval_behaviour/``; the step's ``eval/`` is left as it is) and only the
    in-scope T0 inconsistency tests run on it; no container when none is in scope.
    None for steps that are not evaluated T1..T4 study-3 steps."""
    from aa import chain_eval3 as ce3
    from aa.chain_eval import (EVAL_ERRORS_NOTHING_RAN, HOST_TIMEOUT_S, carry_plan,
                               chain_eval_docker_argv, chain_eval_script, load_chain)
    from aa.checker import SEED_SRC
    from aa.evaluate import EVALUATED, docker_execute, stage_hidden_tests
    res = _read_json(step_dir / "result.json")
    meta = _read_json(step_dir / "agent.json")
    if not res or not meta or res.get("study") != 3 or meta.get("status") not in EVALUATED \
            or res.get("step_id") not in ("T1", "T2", "T3", "T4") \
            or res.get("eval_error") is not None:
        return None
    old = {k: res.get(k) for k in BEHAVIOUR_FIELDS}
    chain = load_chain(meta["zone"], tasks_root)
    step = chain.step(res["step_id"])
    t0, in_scope = ce3.step_scope(chain.zone, step.id, t0_root)
    if not in_scope:
        unified, det = ce3.scope_outcome(step_dir / BEHAVIOUR_DIR, {})
        return old, {"inconsistencies_unified_step": unified, "inconsistency_scope_detail": det}
    out = step_dir / BEHAVIOUR_DIR
    if out.exists():
        import shutil
        shutil.rmtree(out)
    out.mkdir()
    files = stage_hidden_tests(t0.dir, list(t0.hidden), meta["cond"], out)
    plan = carry_plan(step_dir, meta, step.index)
    tar = not (step_dir / "diff_ok").exists() and (step_dir / "tree.tar").exists()
    script = chain_eval_script(step.id, plan, agent_tree="tar" if tar else "diff",
                               hidden_tests=[], zone_files=chain.files_for(meta["cond"]),
                               zone_dirs=chain.dirs_for(meta["cond"]), study3=True,
                               scope_tests=files, behaviour_only=True)
    argv = chain_eval_docker_argv(meta["cond"], step_dir, out, script,
                                  checker_dir or SEED_SRC.parent)
    (execute or docker_execute)(argv, HOST_TIMEOUT_S)
    err = (out / "eval_error").read_text().strip() if (out / "eval_error").exists() else None
    post = (out / "post_tree").read_text().strip() if (out / "post_tree").exists() else None
    # the evaluator's own post tree (eval/post_tree): built the same way in the same
    # image (the image commit, the carried patches, the agent's diff), so equal ids mean
    # the same tree it evaluated. The runner's post_tree is a different repository
    # (fresh `git add -A` in the agent container) and is not comparable in study 3
    # (the evaluator's own tree_check.post is false there).
    ref_p = step_dir / "eval" / "post_tree"
    ref_post = ref_p.read_text().strip() if ref_p.exists() else None
    tree_ok = None if not (post and ref_post) else post == ref_post
    if err in EVAL_ERRORS_NOTHING_RAN or err or tree_ok is False:
        unified, det = None, {"in_scope": dict(in_scope),
                              "reason": f"eval_error:{err}" if err else "post_tree_mismatch"}
    else:
        unified, det = ce3.scope_outcome(out, in_scope)
    det["post_tree_check"] = tree_ok
    det["dir"] = BEHAVIOUR_DIR
    return old, {"inconsistencies_unified_step": unified, "inconsistency_scope_detail": det}


def behaviour_check_runs(root: Path, apply: bool = True, zones: tuple[str, ...] | None = None,
                         log: Callable[[str], None] = print, **kw: Any) -> list[dict]:
    """``aa chain behaviour-check``: steps one at a time (one loot-core container), each
    result.json updated with ``inconsistencies_unified_step`` and its detail, with a
    record. ``apply=False`` lists the steps that would run a container."""
    from aa import chain_eval3 as ce3
    root = Path(root)
    out: list[dict] = []
    for d in step_dirs(root):
        res = _read_json(d / "result.json") or {}
        if zones and res.get("zone") not in zones:
            continue
        if not apply:
            if res.get("study") == 3 and res.get("step_id") in ("T1", "T2", "T3", "T4") \
                    and res.get("eval_error") is None and not str(res.get("status")).startswith("infra"):
                _, sc = ce3.step_scope(res["zone"], res["step_id"], kw.get("t0_root"))
                log(f"{_rel(root, d)}: {len(sc)} test(s) in scope"
                    + (" -> container" if sc else ""))
            continue
        got = behaviour_check_step(d, **kw)
        if got is None:
            continue
        old, new = got
        rec = {"step": _rel(root, d), "old": old["inconsistencies_unified_step"],
               "new": new["inconsistencies_unified_step"],
               "reason": new["inconsistency_scope_detail"].get("reason"), "at": _now(),
               "by": "aa chain behaviour-check", "rule": BEHAVIOUR_RULE}
        out.append(rec)
        log(f"{rec['step']}: inconsistencies_unified_step = {rec['new']}"
            + (f" ({rec['reason']})" if rec["reason"] else ""))
        res = _read_json(d / "result.json")
        res.update(new)
        res.setdefault("rederived", []).append(
            {"what": "inconsistencies_unified_step", "old": old, "new": rec["new"],
             "at": rec["at"], "by": rec["by"], "rule": BEHAVIOUR_RULE})
        _write_json(d / "result.json", res)
    if apply:
        _log(root, [{"kind": "behaviour_check", **r} for r in out])
    return out
