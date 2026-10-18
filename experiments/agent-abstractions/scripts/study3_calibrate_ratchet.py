"""Study 3 ratchet calibration on study-2 data (spec §5, plan Task 1). No agent runs.

For every study-2 T2 step (runs2/<agent>/{R,F}/<zone>/<chain>/T2, read-only):
start tree = work/variants/<cond> HEAD + eval/pre_image.patch (staged; its tree id is
the start revision), post tree = start + diff.patch (working tree; new files untracked).
Both live in a temporary detached worktree of work/variants/<cond>, removed afterwards.
The detector (:func:`aa.ratchet.clones_by_threshold`: pinned jscpd 5.4.0 in
aa-actual:R over loot-core non-test sources) runs at min-tokens 50, 35, 25.

Labels from result.json ``t2_reuses_logic``: R steps labelled ``copy`` give the
sensitivity (detector fires = at least one new clone touching the agent's lines);
F steps labelled ``helper`` give the false-positive rate. Other labels are listed and
left out. Rule as amended on 2026-10-11: the highest threshold with pooled FPR <= 10 %;
if its pooled sensitivity is < 50 % (or none qualifies), the highest threshold whose
pooled sensitivity is >= 50 %, i.e. the least noisy detector that still sees half the
copies. This deviates from the registered rule, whose second clause says "lowest" (well
defined: it gives 25, applied by amendment 2026-10-10); the change to "highest" was made
after sensitivity and FPR at every threshold were known, before any study-3 agent run,
and is disclosed as a deviation (spec, amendment 2026-10-11). Zones where the
chosen threshold's sensitivity is < 50 % are "lint blind"; in-zone zones whose FPR is
not below their sensitivity are noted as "non-discriminating" (descriptive only).

Firing by step (``--firing``, review of plan Tasks 1-3): the same replay at the chosen
min-tokens (35) over the study-2 R and F steps T1, T3 and T4 (all 4 zones x 3 agents x
8 chains, no labels): how often the per-change ratchet fires at each step type, rule
steps included (the rule counts a clone with a side on any added or modified line,
also a line edited inside a clone that existed at the start). Written to
out/study3/ratchet-firing-by-step.json and as a section of the report.

Run: uv run python scripts/study3_calibrate_ratchet.py [--workers 6] [--limit N] [--firing]
Writes out/study3/ratchet-calibration.json (per step) and out/study3/ratchet-calibration.md.
Re-running reuses the per-step JSON (``--fresh`` recomputes)."""
from __future__ import annotations

import argparse
import collections
import json
import math
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

from aa import config, ratchet

THRESHOLDS = (50, 35, 25)
FIRING_STEPS = ("T1", "T3", "T4")
FIRING_THRESHOLD = 35  # config.RATCHET_MIN_TOKENS (amendment 2026-10-11)
STEP_IDS = ("T1", "T2", "T3", "T4")
FPR_MAX = 0.10
SENS_MIN = 0.50
LABEL = {"R": "copy", "F": "helper"}
AGENTS = ("claude", "codex", "haiku")
ZONES = ("Z1", "Z2", "Z3", "Z4")
RUNS2 = config.ROOT / "runs2"
VARIANTS = config.WORK / "variants"
OUT = config.ROOT / "out" / "study3"
_wt_lock = threading.Lock()  # git worktree add/remove share the variant repo's admin dir


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout.strip()


def steps() -> list[Path]:
    return sorted(p for p in RUNS2.glob("*/*/*/*/T2") if p.parts[-4] in LABEL)


def firing_steps() -> list[Path]:
    return sorted(p for s in FIRING_STEPS for p in RUNS2.glob(f"*/*/*/*/{s}")
                  if p.parts[-4] in LABEL)


def replay(step: Path, thresholds: tuple[int, ...] = THRESHOLDS) -> dict:
    r = json.loads((step / "result.json").read_text())
    rec = {k: r[k] for k in ("agent", "cond", "zone", "chain")}
    rec["step_id"] = step.name
    rec["label"] = r.get("t2_reuses_logic")
    rec["step"] = str(step.relative_to(config.ROOT))
    variant = VARIANTS / r["cond"]
    tmp = Path(tempfile.mkdtemp(prefix="aa-cal-"))
    wt = tmp / "tree"
    with _wt_lock:
        _git(variant, "worktree", "add", "--detach", "-q", str(wt), "HEAD")
    try:
        # --allow-empty: a T1 pre-image (the untouched image) or a no-op step is empty
        _git(wt, "apply", "--allow-empty", "--whitespace=nowarn",
             str(step / "eval" / "pre_image.patch"))
        _git(wt, "add", "-A")
        start = _git(wt, "write-tree")
        _git(wt, "apply", "--allow-empty", "--whitespace=nowarn", str(step / "diff.patch"))
        res = ratchet.clones_by_threshold(wt, start, thresholds)
    finally:
        with _wt_lock:
            subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=variant,
                           capture_output=True)
            subprocess.run(["git", "worktree", "prune"], cwd=variant, capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)
    rec["start_tree"] = start
    for t, v in res.items():
        rec[f"t{t}"] = {"fires": bool(v["new"]), "new": len(v["new"]), "all": v["all"],
                        "unresolved": v["unresolved"], "files": v["files"],
                        "changed_lines": v["changed_lines"],
                        "clones": [asdict(c) for c in v["new"][:20]]}
    return rec


# --------------------------------------------------------------------------- analysis

def wilson(k: int, n: int, z: float = 1.96) -> str:
    if not n:
        return "—"
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"{k}/{n} = {100 * p:.0f} % [{100 * max(0, c - h):.0f}–{100 * min(1, c + h):.0f}]"


def rate(recs: list[dict], t: int) -> tuple[int, int]:
    return sum(r[f"t{t}"]["fires"] for r in recs), len(recs)


def frac(kn: tuple[int, int]) -> float | None:
    return kn[0] / kn[1] if kn[1] else None


def choose(sens: dict[int, tuple[int, int]], fpr: dict[int, tuple[int, int]]) -> tuple[int | None, str]:
    """Spec §5 rule, read as amendment 2026-10-11 registers it. Thresholds in min-tokens
    (higher = stricter, less noisy detector); both clauses take the highest qualifying one."""
    ok_fpr = [t for t in sorted(THRESHOLDS, reverse=True) if frac(fpr[t]) is not None
              and frac(fpr[t]) <= FPR_MAX]
    if ok_fpr and frac(sens[ok_fpr[0]]) >= SENS_MIN:
        t = ok_fpr[0]
        return t, (f"min-tokens {t} is the highest threshold with FPR <= 10 % "
                   f"({100 * frac(fpr[t]):.0f} %) and its sensitivity "
                   f"({100 * frac(sens[t]):.0f} %) is >= 50 %: chosen by the first clause.")
    first = (f"the highest threshold with FPR <= 10 % is min-tokens {ok_fpr[0]} "
             f"(sensitivity {100 * frac(sens[ok_fpr[0]]):.0f} % < 50 %)"
             if ok_fpr else "no threshold has FPR <= 10 %")
    ok_sens = [t for t in sorted(THRESHOLDS, reverse=True) if frac(sens[t]) is not None
               and frac(sens[t]) >= SENS_MIN]
    if ok_sens:
        t = ok_sens[0]
        return t, (f"{first}; second clause: min-tokens {t} is the highest threshold with "
                   f"sensitivity >= 50 % ({100 * frac(sens[t]):.0f} %, FPR "
                   f"{100 * frac(fpr[t]):.0f} %).")
    return None, f"{first}; no threshold reaches sensitivity >= 50 %: no detector qualifies."


def report(recs: list[dict]) -> tuple[str, dict]:
    pos = [r for r in recs if r["cond"] == "R" and r["label"] == "copy"]
    neg = [r for r in recs if r["cond"] == "F" and r["label"] == "helper"]
    left = collections.Counter((r["agent"], r["cond"], r["zone"], r["label"]) for r in recs
                               if r not in pos and r not in neg)
    sens = {t: rate(pos, t) for t in THRESHOLDS}
    fpr = {t: rate(neg, t) for t in THRESHOLDS}
    chosen, why = choose(sens, fpr)

    def by(rs, key):
        g = collections.defaultdict(list)
        for r in rs:
            g[r[key]].append(r)
        return g

    L = ["# Study 3 — ratchet calibration on study-2 T2 steps", "",
         "Generated by `scripts/study3_calibrate_ratchet.py` (spec §5, plan Task 1). No "
         "study-3 outcome was seen. Detector: `aa.ratchet` — jscpd 5.4.0 pinned in "
         "`aa-actual:R` (run with `docker run --network none`), over the non-test sources "
         "under `packages/loot-core/src` of the agent's post tree; a step *fires* when at "
         "least one clone has a side on a line the agent added or modified relative to the "
         "step's start tree (`git diff -U0`, new files whole).", "",
         "Trees: start = `work/variants/<cond>` HEAD + `eval/pre_image.patch`; post = start "
         "+ `diff.patch`; rebuilt in temporary worktrees, removed after each step.", "",
         f"Steps: {len(recs)} T2 steps (3 agents × 2 conditions × 4 zones × 8 chains). "
         f"Sensitivity over R steps labelled `copy` (n = {len(pos)}); false-positive rate "
         f"over F steps labelled `helper` (n = {len(neg)}). Labels are study 2's static "
         "`t2_reuses_logic`.", ""]
    if left:
        L += ["Left out (other labels):", ""]
        L += [f"- {a} {c} {z}: `{lab}` × {n}" for (a, c, z, lab), n in sorted(left.items(), key=str)]
        L.append("")
    L += ["## Pooled", "", "| min-tokens | sensitivity (R copy) | FPR (F helper) |",
          "|---|---|---|"]
    L += [f"| {t} | {wilson(*sens[t])} | {wilson(*fpr[t])} |" for t in THRESHOLDS]
    L += ["", "## Decision (spec §5 rule, amendment 2026-10-11)", "", why, ""]
    alt = [t for t in sorted(THRESHOLDS) if frac(sens[t]) is not None
           and frac(sens[t]) >= SENS_MIN]
    if chosen is not None and alt and alt[0] != chosen:
        L += [f"Deviation from the registered rule: its second clause, \"the lowest "
              f"threshold whose sensitivity >= 50 %\", is well defined and gives min-tokens "
              f"{alt[0]} (sensitivity {wilson(*sens[alt[0]])}, FPR {wilson(*fpr[alt[0]])}); "
              f"amendment 2026-10-10 applied it. Amendment 2026-10-11 replaced \"lowest\" "
              f"by \"highest\" after sensitivity and FPR at every threshold were known "
              f"(at {alt[0]} the detector fires on "
              f"{wilson(*rate([r for r in neg if r['zone'] == 'Z1'], alt[0]))} of Z1 "
              f"helper-reuse steps, 0 % at {chosen}), before any "
              f"study-3 agent run. It is a disclosed deviation, not a reading of the rule; "
              f"RL results are reported with it noted. min-tokens {chosen} is borderline "
              f"(sensitivity {wilson(*sens[chosen])}).", ""]
    blind: list[str] = []
    nondisc: list[str] = []
    zone_rows = {}
    for title, key, keys in (("zone", "zone", ZONES), ("agent", "agent", AGENTS)):
        pz, nz = by(pos, key), by(neg, key)
        L += [f"## Per {title}", "",
              f"| {title} | " + " | ".join(f"sens {t}" for t in THRESHOLDS) + " | "
              + " | ".join(f"FPR {t}" for t in THRESHOLDS) + " |",
              "|---|" + "---|" * (2 * len(THRESHOLDS))]
        for k in keys:
            s = [rate(pz[k], t) for t in THRESHOLDS]
            f = [rate(nz[k], t) for t in THRESHOLDS]
            L.append(f"| {k} | " + " | ".join(wilson(*x) for x in s) + " | "
                     + " | ".join(wilson(*x) for x in f) + " |")
            if key == "zone" and chosen is not None:
                zs, zf = rate(pz[k], chosen), rate(nz[k], chosen)
                zone_rows[k] = {"sensitivity": list(zs), "fpr": list(zf)}
                if frac(zs) is None or frac(zs) < SENS_MIN:
                    blind.append(k)
                elif frac(zf) is not None and frac(zf) >= frac(zs):
                    nondisc.append(k)
        L.append("")
    L += ["## Per zone × agent (sensitivity / FPR at each threshold)", "",
          "| zone | agent | " + " | ".join(f"sens {t}" for t in THRESHOLDS) + " | "
          + " | ".join(f"FPR {t}" for t in THRESHOLDS) + " |",
          "|---|---|" + "---|" * (2 * len(THRESHOLDS))]
    for z in ZONES:
        for a in AGENTS:
            ps = [r for r in pos if r["zone"] == z and r["agent"] == a]
            ns = [r for r in neg if r["zone"] == z and r["agent"] == a]
            L.append(f"| {z} | {a} | "
                     + " | ".join("{}/{}".format(*rate(ps, t)) for t in THRESHOLDS) + " | "
                     + " | ".join("{}/{}".format(*rate(ns, t)) for t in THRESHOLDS) + " |")
    L.append("")
    if chosen is not None:
        L += [f"## Lint-blind zones at min-tokens {chosen}", "",
              (", ".join(blind) + " (sensitivity < 50 %): excluded from RL's confirmatory "
               "analyses, kept descriptively.") if blind else "None.", ""]
        if nondisc:
            L += [", ".join(f"{k} (sensitivity {wilson(*zone_rows[k]['sensitivity'])}, FPR "
                            f"{wilson(*zone_rows[k]['fpr'])})" for k in nondisc)
                  + ": non-discriminating (the lint fires on helper steps at least as "
                  "often as on copies). Descriptive note only: kept in RL's confirmatory "
                  "analyses as registered, since sensitivity >= 50 %.", ""]
    unres = sum(r[f"t{t}"]["unresolved"] for r in recs for t in THRESHOLDS)
    L += ["## Checks", "",
          f"- Clones dropped as unresolved jscpd names (all steps, all thresholds): {unres}.",
          f"- Scanned files per post tree: {min(r['t50']['files'] for r in recs)}–"
          f"{max(r['t50']['files'] for r in recs)}.",
          "- Steps where the detector fires on an F `helper` step, at the chosen threshold "
          "(read before trusting the FPR):", ""]
    if chosen is not None:
        for r in neg:
            v = r[f"t{chosen}"]
            if v["fires"]:
                cl = "; ".join(f"{c['a'].split('/')[-1]}:{c['a_start']}-{c['a_end']} ~ "
                               f"{c['b'].split('/')[-1]}:{c['b_start']}-{c['b_end']} "
                               f"({c['tokens']} tok)" for c in v["clones"][:3])
                L.append(f"  - `{r['step']}`: {v['new']} clone(s): {cl}")
    L.append("")
    summary = {"chosen_min_tokens": chosen, "reason": why, "lint_blind_zones": blind,
               "non_discriminating_zones": nondisc,
               "per_zone_at_chosen": zone_rows,
               "pooled": {t: {"sensitivity": list(sens[t]), "fpr": list(fpr[t])}
                          for t in THRESHOLDS},
               "n_sensitivity": len(pos), "n_fpr": len(neg)}
    return "\n".join(L), summary


def firing_table(t2: list[dict], other: list[dict], t: int = FIRING_THRESHOLD) -> dict:
    """{cond: {zone: {step: [fired, n]}}} at min-tokens ``t`` (T2 from the calibration
    replay, every T2 step whatever its label; T1/T3/T4 from the firing replay)."""
    out: dict = {}
    for r in [*t2, *other]:
        sid = r.get("step_id") or r["step"].rsplit("/", 1)[-1]
        cell = out.setdefault(r["cond"], {}).setdefault(r["zone"], {}).setdefault(sid, [0, 0])
        cell[0] += bool(r[f"t{t}"]["fires"])
        cell[1] += 1
    return out


def firing_section(t2: list[dict], other: list[dict], t: int = FIRING_THRESHOLD) -> str:
    tab = firing_table(t2, other, t)
    L = [f"## Firing by step type at min-tokens {t} (R and F, all study-2 steps)", "",
         "Replay of every study-2 R and F step at the chosen threshold (T2 from the "
         "calibration data above, all labels; T1, T3, T4 replayed with the same trees and "
         "detector). A step *fires* when a clone has a side on a line the agent added or "
         "modified, including a line edited inside a clone that was already there: the "
         "registered per-change rule (as SonarQube's duplication on new code). Rule steps "
         "are T1 and T3, T2 adds a consumer, T4 is the last change of the chain.", ""]
    for cond in ("R", "F"):
        L += [f"**{cond}** (fired / steps, Wilson 95 %)", "",
              "| zone | " + " | ".join(STEP_IDS) + " |", "|---|" + "---|" * len(STEP_IDS)]
        for z in ZONES:
            row = tab.get(cond, {}).get(z, {})
            L.append(f"| {z} | " + " | ".join(wilson(*row.get(s, (0, 0))) for s in STEP_IDS)
                     + " |")
        L.append("")
    L += ["Clones on R rule steps (first firing steps per zone × step, up to 3 clones each):",
          ""]
    for z in ZONES:
        for sid in ("T1", "T3"):
            fired = [r for r in other if r["cond"] == "R" and r["zone"] == z
                     and r["step_id"] == sid and r[f"t{t}"]["fires"]]
            for r in fired[:2]:
                v = r[f"t{t}"]
                cl = "; ".join(f"{c['a'].split('/')[-1]}:{c['a_start']}-{c['a_end']} ~ "
                               f"{c['b'].split('/')[-1]}:{c['b_start']}-{c['b_end']} "
                               f"({c['tokens']} tok)" for c in v["clones"][:3])
                L.append(f"- `{r['step']}`: {v['new']} clone(s): {cl}")
    L += ["", "Reading: \"lint blind\" keeps its registered meaning (T2 copy sensitivity "
          "< 50 %); it is not \"never fires\". Where a zone's rule edits touch duplicated "
          "blocks, the ratchet fires at T1/T3 and so can force consolidation there.", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0, help="first N steps only (smoke)")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--firing", action="store_true",
                    help=f"replay R/F steps {', '.join(FIRING_STEPS)} at min-tokens "
                         f"{FIRING_THRESHOLD} (firing by step type)")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.firing:
        return firing_main(a)
    data_p = OUT / "ratchet-calibration.json"
    done: dict[str, dict] = {}
    if data_p.exists() and not a.fresh:
        done = {r["step"]: r for r in json.loads(data_p.read_text())["steps"]}
    todo = [s for s in steps() if str(s.relative_to(config.ROOT)) not in done]
    if a.limit:
        todo = todo[:a.limit]
    t0 = time.time()
    errors = []
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(replay, s): s for s in todo}
        for i, f in enumerate(as_completed(futs), 1):
            s = futs[f]
            try:
                r = f.result()
                done[r["step"]] = r
            except Exception as e:  # noqa: BLE001 - reported, not hidden
                errors.append((str(s), repr(e)[:500]))
            print(f"[{i}/{len(todo)}] {s.relative_to(RUNS2)} {time.time() - t0:.0f}s",
                  file=sys.stderr, flush=True)
    recs = sorted(done.values(), key=lambda r: r["step"])
    data_p.write_text(json.dumps({"thresholds": THRESHOLDS, "jscpd": ratchet.JSCPD_VERSION,
                                  "image": ratchet.JSCPD_IMAGE, "errors": errors,
                                  "steps": recs}, indent=1) + "\n")
    if errors:
        for e in errors:
            print("ERROR", *e, file=sys.stderr)
    if len(recs) == len(steps()) and not errors:
        write_report(recs)
        summary = report(recs)[1]
        print(json.dumps(summary, indent=1))
    else:
        print(f"{len(recs)}/{len(steps())} steps replayed, {len(errors)} errors: no report",
              file=sys.stderr)
    return 1 if errors else 0


FIRING_JSON = OUT / "ratchet-firing-by-step.json"


def _firing_records() -> list[dict] | None:
    if not FIRING_JSON.exists():
        return None
    d = json.loads(FIRING_JSON.read_text())
    recs = d["steps"]
    return recs if len(recs) == len(firing_steps()) and not d["errors"] else None


def write_report(recs: list[dict]) -> None:
    """The report from the T2 calibration records, plus the firing section when the
    firing replay is complete."""
    md, summary = report(recs)
    other = _firing_records()
    if other is not None:
        md = md.rstrip("\n") + "\n\n" + firing_section(recs, other)
        summary["firing_by_step_at_chosen"] = firing_table(recs, other)
    (OUT / "ratchet-calibration.md").write_text(md)
    (OUT / "ratchet-calibration-summary.json").write_text(json.dumps(summary, indent=1) + "\n")


def firing_main(a: argparse.Namespace) -> int:
    done: dict[str, dict] = {}
    if FIRING_JSON.exists() and not a.fresh:
        done = {r["step"]: r for r in json.loads(FIRING_JSON.read_text())["steps"]}
    todo = [s for s in firing_steps() if str(s.relative_to(config.ROOT)) not in done]
    if a.limit:
        todo = todo[:a.limit]
    t0 = time.time()
    errors = []
    lock = threading.Lock()

    def save() -> None:
        recs = sorted(done.values(), key=lambda r: r["step"])
        FIRING_JSON.write_text(json.dumps({"thresholds": [FIRING_THRESHOLD],
                                           "jscpd": ratchet.JSCPD_VERSION,
                                           "image": ratchet.JSCPD_IMAGE, "errors": errors,
                                           "steps": recs}, indent=1) + "\n")

    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(replay, s, (FIRING_THRESHOLD,)): s for s in todo}
        for i, f in enumerate(as_completed(futs), 1):
            s = futs[f]
            try:
                r = f.result()
                with lock:
                    done[r["step"]] = r
            except Exception as e:  # noqa: BLE001 - reported, not hidden
                errors.append((str(s), repr(e)[:500]))
            if i % 20 == 0:
                save()
            print(f"[{i}/{len(todo)}] {s.relative_to(RUNS2)} {time.time() - t0:.0f}s",
                  file=sys.stderr, flush=True)
    save()
    for e in errors:
        print("ERROR", *e, file=sys.stderr)
    cal = OUT / "ratchet-calibration.json"
    t2 = json.loads(cal.read_text())["steps"]
    if _firing_records() is not None and len(t2) == len(steps()):
        write_report(t2)
        print(json.dumps(firing_table(t2, sorted(done.values(), key=lambda r: r["step"])),
                         indent=1))
    else:
        print(f"{len(done)}/{len(firing_steps())} firing steps replayed, {len(errors)} "
              "errors: report not updated", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
