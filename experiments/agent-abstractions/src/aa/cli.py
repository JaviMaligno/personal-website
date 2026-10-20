"""`aa <subcommand>` entry point. Later tasks register more subcommands here."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aa import config


def _cmd_substrate_fetch(args: argparse.Namespace) -> int:
    from aa.substrate import fetch_base
    print(fetch_base())
    return 0


def _cmd_variant_build(args: argparse.Namespace) -> int:
    from aa.substrate import build_variant
    print(build_variant(args.cond))
    return 0


def _cmd_variant_install(args: argparse.Namespace) -> int:
    from aa.substrate import install_variant
    print(install_variant(args.cond))
    return 0


# Host vitest runs keep their JSON report + stdout/stderr here on any failure
# (aa.suite.keep_logs), next to work/baseline-*.json.
LOG_DIR = config.WORK / "logs"


def _suite_tree(cond: str) -> Path:
    # Condition A runs on the base checkout itself (the lint-script patch does not
    # touch tests and base already has node_modules); other conditions run on
    # their variant tree, which must have been built and installed first.
    return config.WORK / "actual-base" if cond == "A" else config.WORK / "variants" / cond


def _baseline_dir(study2: bool) -> Path:
    """Study-1 baselines in work/, study-2 ones (seeded, incl. a seeded A) in work/study2/."""
    return config.STUDY2_WORK if study2 else config.WORK


def _cmd_suite_baseline(args: argparse.Namespace) -> int:
    from aa.suite import node_mismatch, run_suite
    study2 = args.study2 or args.cond in config.CONDITIONS2
    tree = _suite_tree(args.cond)
    if not (tree / "node_modules").exists():
        print(f"{tree} has no node_modules; run `yarn install --immutable` there first",
              file=sys.stderr)
        return 2
    if (mm := node_mismatch(tree)) is not None:
        print(f"node {mm[1]} on PATH, but {tree} pins {mm[0]} (.nvmrc)", file=sys.stderr)
        return 2
    res = run_suite(tree, timeout=args.timeout, log_dir=LOG_DIR, label=f"suite-{args.cond}")
    out = _baseline_dir(study2) / f"baseline-{args.cond}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res.to_json(), indent=2) + "\n")
    print(f"{out}: passed={len(res.passed)} failed={len(res.failed)} skipped={len(res.skipped)}")
    for t in sorted(res.failed):
        print(f"  FAILED {t}")
    return 0


def _cmd_equivalence(args: argparse.Namespace) -> int:
    """Compare work/baseline-<a>.json with work/baseline-<b>.json (Task 3, Step 7).

    Study 2 (either side R/F, or --study2): reads work/study2/, and no new test is
    allowed on either side (the A+ domain-test allowance is study 1 only)."""
    from aa.equivalence import DOMAIN_TEST_PREFIX, compare
    from aa.suite import SuiteResult
    study2 = args.study2 or bool({args.a, args.b} & set(config.CONDITIONS2))
    res = {}
    for cond in (args.a, args.b):
        path = _baseline_dir(study2) / f"baseline-{cond}.json"
        if not path.exists():
            hint = " --study2" if study2 and cond not in config.CONDITIONS2 else ""
            print(f"{path} missing; run `aa suite baseline --cond {cond}{hint}` first",
                  file=sys.stderr)
            return 2
        res[cond] = SuiteResult.from_json(json.loads(path.read_text()))
    diff = compare(res[args.a], res[args.b], excluded=config.EXCLUDED_TESTS,
                   allow_new_passing_prefix=None if study2 else DOMAIN_TEST_PREFIX)
    if not diff:
        print("equivalent (0 differences)")
        return 0
    print(f"NOT equivalent ({len(diff)} differences)")
    for t in diff:
        print(f"  {t}")
    return 1


def _cmd_probe2(args: argparse.Namespace) -> int:
    """Study 2 behavioural probe on each condition's tree; diff every one against the
    first. Writes work/study2/probe-<cond>/{db,template}.json."""
    from aa.probe2 import diff_probe, run_probe
    from aa.suite import node_mismatch
    conds = args.conds.split(",")
    docs = {}
    for cond in conds:
        tree = _suite_tree(cond)
        if not (tree / "node_modules").exists():
            print(f"{tree} has no node_modules; install it first", file=sys.stderr)
            return 2
        if (mm := node_mismatch(tree)) is not None:
            print(f"node {mm[1]} on PATH, but {tree} pins {mm[0]} (.nvmrc)", file=sys.stderr)
            return 2
        docs[cond] = run_probe(tree, config.STUDY2_WORK / f"probe-{cond}", timeout=args.timeout)
        d = docs[cond]
        print(f"{cond}: probe tests passed={d['passed']} failed={len(d['failed'])} "
              f"cases db={len(d['db'] or {})} template={len(d['template'] or {})}")
    rc = 0
    ref = conds[0]
    for cond in conds[1:]:
        diff = diff_probe(docs[ref], docs[cond])
        print(f"{ref} vs {cond}: " + ("identical" if not diff else f"{len(diff)} differences"))
        for k in diff:
            print(f"  {k}")
        rc = rc or (1 if diff else 0)
    return rc


# --- checker (Task 5) -------------------------------------------------------------

def _cmd_checker_baseline(args: argparse.Namespace) -> int:
    """Per condition: canary (must see its events), full suite with the probe and vitest
    timeouts raised x10 (checker.PROBE_TIMEOUT_FACTOR), and a pass/fail comparison with
    the probe-free suite baseline at default timeouts (the probe must not change
    behaviour; spec section 6 two-pass rule: probe runs only collect violations, so
    they get the raised timeouts). Union raw writers into baseline-writers.json (informational; nothing
    is discounted). Refuses to write on a canary failure, a suite difference or a
    non_integer_money event outside the canary."""
    from aa import checker
    from aa.equivalence import compare
    from aa.suite import SuiteResult, run_suite
    entries: dict[tuple[str, str], dict] = {}
    runs: dict[str, dict] = {}
    problems: list[str] = []
    for cond in args.conds.split(","):
        tree = _suite_tree(cond)
        if not (tree / "node_modules").exists():
            print(f"{tree} has no node_modules; install it first", file=sys.stderr)
            return 2
        r = checker.run_canary(tree, log_dir=LOG_DIR, label=f"canary-{cond}")
        if not r.ok:
            print(f"{cond}: canary failed; not writing baseline", file=sys.stderr)
            for prob in r.problems:
                print(f"  {prob}", file=sys.stderr)
            return 2
        canary_events = len([e for e in r.events if checker.is_canary_event(e)])
        ref_path = config.WORK / f"baseline-{cond}.json"
        if ref_path.exists():
            ref = SuiteResult.from_json(json.loads(ref_path.read_text()))
        else:
            ref = run_suite(tree, timeout=args.timeout, log_dir=LOG_DIR, label=f"suite-{cond}")
            ref_path.write_text(json.dumps(ref.to_json(), indent=2) + "\n")
        suite, events = checker.run_with_probe(tree, timeout=args.timeout, log_dir=LOG_DIR,
                                               label=f"probe-{cond}")
        # probe-on pass/fail sets, so repeated runs can be compared (determinism check)
        (config.WORK / f"probe-baseline-{cond}.json").write_text(
            json.dumps(suite.to_json(), indent=2) + "\n")
        diff = compare(ref, suite, excluded=config.EXCLUDED_TESTS)
        money = checker.money_events(events)
        writers = checker.baseline_entries(events)
        for e in writers:
            entries[(e["caller"], e["sql"])] = e
        runs[cond] = {"passed": len(suite.passed), "failed": len(suite.failed),
                      "skipped": len(suite.skipped), "differences_vs_no_probe": len(diff),
                      "canary_events_seen": canary_events,
                      "raw_write_events": sum(e.get("kind") == "raw_write" for e in events),
                      "raw_writers": len(writers), "non_integer_money_events": len(money),
                      "probe_test_timeout_ms": checker.PROBE_TEST_TIMEOUT_MS,
                      "probe_hook_timeout_ms": checker.PROBE_HOOK_TIMEOUT_MS}
        print(f"{cond}: passed={len(suite.passed)} failed={len(suite.failed)} "
              f"skipped={len(suite.skipped)} diff_vs_no_probe={len(diff)} "
              f"canary_events={canary_events} raw_writers={len(writers)} "
              f"non_integer_money={len(money)}")
        for t in diff:
            problems.append(f"{cond}: probe changed test result: {t}")
        for e in money:
            problems.append(f"{cond}: non_integer_money on base: {json.dumps(e)}")
    if problems:
        print("not writing baseline:", file=sys.stderr)
        for prob in problems:
            print(f"  {prob}", file=sys.stderr)
        return 1
    doc = checker.baseline_document(runs, [entries[k] for k in sorted(entries)])
    checker.BASELINE_WRITERS.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"{checker.BASELINE_WRITERS}: {len(entries)} writers")
    return 0


def _cmd_checker_canary(args: argparse.Namespace) -> int:
    from aa import checker
    rc = 0
    for cond in args.conds.split(","):
        r = checker.run_canary(_suite_tree(cond), timeout=args.timeout, log_dir=LOG_DIR,
                               label=f"canary-{cond}")
        print(f"{cond}: {'ok' if r.ok else 'FAILED'}")
        for prob in r.problems:
            print(f"  {prob}")
        rc = rc or (0 if r.ok else 1)
    return rc


# --- issue tasks (aa.issue_tasks) ---------------------------------------------------

def _cmd_issues_init(args: argparse.Namespace) -> int:
    from aa.issue_tasks import init_issue_task
    d = init_issue_task(args.issue, args.title, args.date, args.hidden)
    print(d)
    return 0


def _cmd_issues_check(args: argparse.Namespace) -> int:
    """Sanity check of issue tasks on all four conditions: untouched + hidden must
    fail, + the family's reference must pass with lint and typecheck green."""
    from aa.issue_tasks import check_issue_task, issue_task_dirs
    from aa.runner import image_digest, image_tag
    conds = tuple(args.conds.split(","))
    missing = [image_tag(c) for c in conds if image_digest(image_tag(c)) is None]
    if missing:
        print(f"docker image(s) missing: {', '.join(missing)}; "
              "run `aa image build <cond>` first", file=sys.stderr)
        return 2
    dirs = issue_task_dirs(config.TASKS)
    if args.task:
        dirs = [d for d in dirs if d.name in set(args.task)]
    rc = 0
    for d in dirs:
        if not args.force and (d / "sanity.json").exists():
            prev = json.loads((d / "sanity.json").read_text())
            print(f"{d.name}\t{'ok' if prev.get('ok') else ','.join(prev.get('reasons') or [])}"
                  "\t(cached; --force to rerun)")
            continue
        try:
            doc = check_issue_task(d, conds=conds, workers=args.workers, tasks_root=config.TASKS)
        except Exception as e:  # one broken task must not stop the batch
            print(f"{d.name}\tERROR {type(e).__name__}: {e}", file=sys.stderr)
            rc = 1
            continue
        line = "ok" if doc["ok"] else ",".join(doc["reasons"])
        if doc["warnings"]:
            line += "\twarnings: " + ",".join(doc["warnings"])
        print(f"{d.name}\t{line}", flush=True)
        rc = rc or (0 if doc["ok"] else 1)
    return rc


def _cmd_issues_eligibility(args: argparse.Namespace) -> int:
    """Eligibility rule (spec 4.2, decision 2026-10-06): reference.A.patch must change
    a function with a protected call; ineligible -> dropped invariant_not_at_stake."""
    from aa.issue_tasks import issue_task_dirs, record_eligibility
    dirs = issue_task_dirs(config.TASKS)
    if args.task:
        dirs = [d for d in dirs if d.name in set(args.task)]
    for d in dirs:
        r = record_eligibility(d, tasks_root=config.TASKS)
        print(f"{d.name}\t{'eligible' if r['eligible'] else 'ineligible'}\t"
              f"{r['protected_hits_A']}\t{','.join(r['protected_units_A'])}")
    return 0


# --- tasks (Task 6) ---------------------------------------------------------------

def _cmd_tasks_preview(args: argparse.Namespace) -> int:
    from aa.tasks import preview
    for reason, n in sorted(preview(since=args.since).items(), key=lambda kv: -kv[1]):
        print(f"{reason}\t{n}")
    return 0


def _cmd_tasks_mine(args: argparse.Namespace) -> int:
    from aa.tasks import filter_reason, mine
    for c in mine(since=args.since):
        print(f"{c.sha[:10]}\t{c.date}\t{filter_reason(c) or 'ok'}\t{c.subject}")
    return 0


def _cmd_tasks_materialise(args: argparse.Namespace) -> int:
    from aa.tasks import DropReason, filter_reason, materialise, mine, task_id
    cands = mine(since=args.since)
    if args.sha:
        cands = [c for c in cands if any(c.sha.startswith(s) for s in args.sha)]
    ledger_path = config.TASKS / "_ledger.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    for c in cands:
        reason = filter_reason(c)
        if reason is None:
            res = materialise(c)
            reason = res.reason if isinstance(res, DropReason) else None
        entry = ledger.setdefault(task_id(c), {})
        entry.update({"sha": c.sha, "date": c.date, "subject": c.subject, "ai_label": c.ai_label,
                      "status": "ok" if reason is None else "dropped", "reason": reason})
        print(f"{task_id(c)}\t{reason or 'ok'}")
    config.TASKS.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    return 0


def _cmd_tasks_check(args: argparse.Namespace) -> int:
    """Sanity check (plan Task 6 Step 4) of every materialised task, in the condition
    images, on all four conditions; verdicts go to sanity.json, task.json and the ledger."""
    from aa.runner import image_digest, image_tag
    from aa.tasks import check_and_record
    missing = [image_tag(c) for c in config.CONDITIONS if image_digest(image_tag(c)) is None]
    if missing:
        print(f"docker image(s) missing: {', '.join(missing)}; "
              "run `aa image build <cond>` first", file=sys.stderr)
        return 2
    from aa.issue_tasks import issue_task_dirs
    issue_dirs = set(issue_task_dirs(config.TASKS))  # checked by `aa issues check`
    dirs = sorted(tj.parent for tj in config.TASKS.glob("*/task.json")
                  if tj.parent not in issue_dirs)
    if args.task:
        dirs = [d for d in dirs if d.name in set(args.task)]
    rc = 0
    for d in dirs:
        if not args.force and (d / "sanity.json").exists():
            prev = json.loads((d / "sanity.json").read_text()).get("reason")
            print(f"{d.name}\t{prev or 'ok'}\t(cached; --force to rerun)")
            continue
        try:
            reason = check_and_record(d, root=config.TASKS)
        except Exception as e:  # one broken task must not stop the batch
            print(f"{d.name}\tERROR {type(e).__name__}: {e}", file=sys.stderr)
            rc = 1
            continue
        print(f"{d.name}\t{reason.reason if reason else 'ok'}", flush=True)
    return rc


def _cmd_tasks_check_statements(args: argparse.Namespace) -> int:
    """Leak check (plan Task 6 Step 5): every surviving task has a statement.md that
    names no protected API, no A+ layer and no file path."""
    from aa.tasks import check_statements
    probs = check_statements(config.TASKS)
    for tid, ps in probs.items():
        for p in ps:
            print(f"{tid}\t{p}")
    print("statements: " + ("FAIL" if probs else "ok"))
    return 1 if probs else 0


def _cmd_tasks_select_preview(args: argparse.Namespace) -> int:
    from collections import Counter

    from aa.tasks import selection_preview
    rows = selection_preview(config.TASKS)
    surv = [r for r in rows if r["survives"]]
    print(f"survivors: {len(surv)} / {len(rows)}")
    for r in surv:
        memo = {True: "memorised", False: "clean", None: "not probed"}[r["memo"]]
        print(f"  {r['id']}\t{r['date']}\tmemo={memo}\t{r['subject']}")
    print("dropped / pending:")
    for reason, n in sorted(Counter(r["reason"] for r in rows if not r["survives"]).items(),
                            key=lambda kv: (-kv[1], kv[0])):
        print(f"  {reason}\t{n}")
    if args.verbose:
        for r in rows:
            if not r["survives"]:
                print(f"  {r['id']}\t{r['reason']}\t{r['subject']}")
    return 0


# --- memo probe (Task 7) ----------------------------------------------------------

def _cmd_memo_estimate(args: argparse.Namespace) -> int:
    from aa.memo_probe import estimate
    from aa.tasks import load_tasks
    print(estimate(len(load_tasks(selected_only=False)), workers=args.workers))
    return 0


def _cmd_memo_run(args: argparse.Namespace) -> int:
    from aa.memo_probe import PROBE_IMAGE, estimate, run_probe
    from aa.runner import image_digest
    from aa.tasks import load_tasks
    if image_digest(PROBE_IMAGE) is None:
        print(f"docker image {PROBE_IMAGE} missing; run `aa image build-cli` first", file=sys.stderr)
        return 2
    from aa.memo_probe import MEMO_AGENTS, missing_entries
    tasks = load_tasks(selected_only=False)
    if args.task:
        tasks = [t for t in tasks if t.id in set(args.task)]
    only = missing_entries(tasks) if args.missing_only else None
    if args.agents:
        agents = set(args.agents.split(","))
        unknown = agents - set(MEMO_AGENTS)
        if unknown:
            print(f"unknown agent(s): {sorted(unknown)}", file=sys.stderr)
            return 2
        pairs = {(t.id, a) for t in tasks for a in agents}
        only = pairs if only is None else only & pairs
    if only is not None:
        print(f"re-probing {len(only)} missing entr{'y' if len(only) == 1 else 'ies'}: "
              f"{sorted(only)} (~1 min/call)")
    else:
        print(estimate(len(tasks), workers=args.workers))
    verdicts = run_probe(tasks, workers=args.workers, only=only)
    for tid, v in sorted(verdicts.items()):
        print(f"{tid}\t{'memorised' if v else 'clean' if v is False else 'RETRY (call failed)'}")
    return 1 if any(v is None for v in verdicts.values()) else 0


# --- docker + agents (Task 8) -----------------------------------------------------

def _cmd_image_build(args: argparse.Namespace) -> int:
    from aa.runner import build_image
    print(build_image(args.cond))
    return 0


def _cmd_image_build_study3(args: argparse.Namespace) -> int:
    from aa import images3
    rec = images3.build_study3(build=not args.inspect_only)
    for arm, img in rec["images"].items():
        print(f"aa-actual:{arm}\t{img.get('image_id')}")
    checks = rec["checks"]
    print("checks: " + ("ok" if checks.get("ok") else "FAILED") + f" ({images3.MANIFEST})")
    return 0 if checks.get("ok") else 1


def _cmd_image_build_cli(args: argparse.Namespace) -> int:
    from aa.runner import build_cli_image
    print(build_cli_image())
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    from aa.runner import run_all
    conds = args.conds.split(",")
    bad = [c for c in conds if c not in config.CONDITIONS]
    if bad:
        print(f"unknown condition(s): {bad}", file=sys.stderr)
        return 2
    tasks = "all" if args.tasks == "all" else args.tasks.split(",")
    results = run_all(args.agent, conds, tasks, args.passes, workers=args.workers)
    for job, status in sorted(results.items(), key=lambda kv: str(kv[0])):
        print(f"{job}\t{status}")
    return 0


def _cmd_run_one(args: argparse.Namespace) -> int:
    from aa.runner import run_one
    print(run_one(args.agent, args.cond, args.task, args.pass_idx))
    return 0



# --- studies 2 and 3: chain runner (study-2 plan Task 3, study-3 plan Task 4) -------

def _chain_study(args: argparse.Namespace, conds: list[str] | None) -> tuple[int, list[str]] | None:
    """(study, conds) from --study/--conds: study 3 when asked or when an RG/RL/RC arm is
    named; default conds are the study's (R,F or R,RG,RL,RC). None (printed) if invalid."""
    from aa import chain_runner as cr
    try:
        study = cr.study_of(conds or [], args.study)
        conds = conds or list(cr.STUDY_CONDITIONS[study])
        cr.study_of(conds, study)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return None
    return study, conds


def _chain_runs(args: argparse.Namespace, study: int) -> Path:
    """--runs, else the study's pilot or main dir; always absolute (docker -v)."""
    from aa import chain_runner as cr
    runs = args.runs or (cr.RUNS_PILOT[study] if args.pilot else cr.STUDY_RUNS[study])
    return Path(runs).resolve()


def _chain_args(args: argparse.Namespace) -> tuple[int, list[str], list[str]] | None:
    from aa.chains import list_zones
    sel = _chain_study(args, args.conds.split(",") if args.conds else None)
    if sel is None:
        return None
    zones = list_zones(args.tasks) if args.zones == "all" else args.zones.split(",")
    if not zones:
        print(f"no chains under {args.tasks}", file=sys.stderr)
        return None
    return sel[0], sel[1], zones


def _cmd_chain_run(args: argparse.Namespace) -> int:
    from aa import chain_runner as cr
    from aa import runner
    sel = _chain_args(args)
    if sel is None:
        return 2
    study, conds, zones = sel
    if config.engine(args.agent) == "codex" and not args.dry_run:
        problem = runner.codex_auth_problem(args.min_codex_auth_hours)
        if problem:
            print(problem, file=sys.stderr)
            return 2
    if args.dry_run:
        for job, plan in cr.plan_all_chains(args.agent, conds, zones,
                                            cr.parse_indices(args.chains),
                                            runs_root=_chain_runs(args, study),
                                            tasks_root=args.tasks.resolve(), study=study,
                                            t0_root=args.t0_tasks.resolve()):
            what = ("complete" if plan["resume_from"] is None and plan["status"] == "ok"
                    else f"stopped at {plan.get('stopped_at')} ({plan['status']})"
                    if plan["resume_from"] is None
                    else f"resume {plan['resume_from']} ({plan['status'] or 'not run'})"
                    + (f", discard {','.join(plan['discard'])}" if plan["discard"] else ""))
            print(f"{job.agent}/{job.cond}/{job.zone}/{job.chain_idx}\t{what}")
        return 0
    workers = args.workers if args.workers is not None else cr.STUDY_WORKERS[study]
    results = cr.run_all_chains(args.agent, conds, zones, cr.parse_indices(args.chains),
                                workers=workers, runs_root=_chain_runs(args, study),
                                tasks_root=args.tasks.resolve(), study=study,
                                t0_root=args.t0_tasks.resolve())
    for job, status in sorted(results.items(), key=lambda kv: str(kv[0])):
        print(f"{job}\t{status}")
    return 0


def _cmd_chain_run_one(args: argparse.Namespace) -> int:
    from aa import chain_runner as cr
    sel = _chain_study(args, [args.cond])
    if sel is None:
        return 2
    res = cr.run_chain(args.agent, args.cond, args.zone, args.chain,
                       runs_root=_chain_runs(args, sel[0]), tasks_root=args.tasks.resolve(),
                       only_step=args.step, study=sel[0], t0_root=args.t0_tasks.resolve())
    print(f"{res.status}\t{res.step_path}")
    return 0 if res.status == "ok" else 1

# --- study 2: chain evaluator (plan Task 4) ---------------------------------------

def _eval_runs(args: argparse.Namespace) -> Path:
    """`aa chain evaluate` / `packets`: --runs, else the --study's runs dir (pilot with
    --pilot); study 2 when neither is given. Always absolute."""
    from aa import chain_runner as cr
    if args.runs is not None:
        return Path(args.runs).resolve()
    if args.pilot and args.study is None:
        print("--pilot needs --study (2: runs2-pilot/, 3: runs3-pilot/)", file=sys.stderr)
        raise SystemExit(2)
    study = args.study or 2
    return Path(cr.RUNS_PILOT[study] if args.pilot else cr.STUDY_RUNS[study]).resolve()


def _cmd_chain_evaluate(args: argparse.Namespace) -> int:
    from aa import chain_eval
    if args.all == bool(args.step_dirs):
        print("give STEP_DIR... or --all (not both)", file=sys.stderr)
        return 2
    if args.all:
        results = chain_eval.evaluate_all(_eval_runs(args), tasks_root=args.tasks,
                                          force=args.force,
                                          workers=args.workers, t0_root=args.tasks3)
        print(f"evaluated {len(results)} chain(s)")
        return 0
    for d in args.step_dirs:
        r = chain_eval.evaluate_step(Path(d), tasks_root=args.tasks, t0_root=args.tasks3)
        if r is None:
            print(f"{d}\tnot final")
        elif r.get("step_id") == "T0":
            print(f"{d}\t{r['status']}\tcorrect={r['correct']}"
                  f"\tprobe_changed={len(r.get('probe_changed_cases') or [])}"
                  f"\tunified={r.get('inconsistencies_unified')}\teval_error={r['eval_error']}")
        else:
            print(f"{d}\t{r['status']}\tcorrect={r['correct']}"
                  f"\tconsumers={r['consumers_passed']}/{r['consumers_total']}"
                  f"\tcarried={r['carried_defects']}\teval_error={r['eval_error']}")
    return 0


def _cmd_chain_packets(args: argparse.Namespace) -> int:
    if args.study == 3:
        return _chain_packets3(args)
    from aa.chain_eval import export_review_packets
    out = args.out or config.WORK / "review2"
    mapping = args.mapping or config.WORK / "review2-mapping.json"
    args.out = out
    rep = export_review_packets(_eval_runs(args), out, mapping, tasks_root=args.tasks,
                                variants_root=args.variants)
    print(f"{len(rep['ok'])} packet(s) in {args.out / 'packets'}; "
          f"{len(rep['bad'])} failed the pre-image check (apply-check.json)")
    return 0 if not rep["bad"] else 1


def _chain_packets3(args: argparse.Namespace) -> int:
    """Study 3: the study-3 exporter (aa.review3: blind to arm, one neutral repository of
    per-packet trees, the study-2 F chains, batches), never study 2's, into
    work/review3 and work/review3-mapping.json by default."""
    from aa import review3
    from aa.chains import TASKS3
    out = args.out or review3.REVIEW3
    mapping = args.mapping or review3.MAPPING3
    tasks3 = getattr(args, "tasks3", None) or TASKS3
    rep, _, batches = review3.export_and_batch(
        _eval_runs(args), out, mapping, f_runs=Path(args.f_runs).resolve(),
        tasks_root=args.tasks, tasks3_root=tasks3, variants_root=args.variants)
    print(f"{len(rep['ok'])} packet(s) in {out / 'packets'}; {len(rep['bad'])} not "
          f"exported (apply-check.json); {len(batches['main'])} main batch(es)")
    return 0 if not rep["bad"] else 1


def _cmd_chain_check_statements(args: argparse.Namespace) -> int:
    """Study-2 statement leak check: study-1 rules + exhaustive-search hints +
    consumer enumerations (spec amendment 2026-10-08)."""
    from aa.chains import check_statements2, check_statements_t0
    probs = check_statements2(args.tasks)
    probs.update({f"tasks3/{k}": v for k, v in check_statements_t0(args.tasks3).items()})
    for sid, ps in probs.items():
        for p in ps:
            print(f"{sid}\t{p}")
    print("statements: " + ("FAIL" if probs else "ok"))
    return 1 if probs else 0


def _cmd_chain_sanity(args: argparse.Namespace) -> int:
    from concurrent.futures import ThreadPoolExecutor

    from aa.chains import list_zones, sanity
    zones = args.zones or list_zones(args.tasks)

    def one(z: str) -> tuple[str, dict]:
        return z, sanity(z, root=args.tasks, work=args.work / z,
                         untouched=not args.no_untouched, references=not args.no_references)
    bad = 0
    with ThreadPoolExecutor(max(1, args.workers)) as ex:
        for z, r in ex.map(one, zones):
            for cond, c in r["conds"].items():
                u = (c.get("untouched") or {}).get("all_fail_individually")
                ref = (c.get("references") or {}).get("all_ok")
                leaks = any(v.get("hidden_or_test_files") or v.get("test_names")
                            for v in c["leaks"].values())
                print(f"{z}\t{cond}\tuntouched_fail={u}\treferences_ok={ref}\tleaks={leaks}")
                bad += (u is False) + (ref is False) + leaks
    return 1 if bad else 0


def _cmd_chain_t0_sanity(args: argparse.Namespace) -> int:
    """Study 3 T0 sanity in Docker: inconsistency tests pass on untouched R and F; each
    seeded consolidation fails its test and is flagged by the probe minus exclusions;
    each excluded difference is invisible after the exclusions."""
    from aa.chains import t0_sanity
    res = t0_sanity(args.zones or None, root=args.tasks3, work=args.work, workers=args.workers)
    bad = 0
    for z, r in res.items():
        seeds = " ".join(f"{n}={'ok' if s['ok'] else 'FAIL'}" for n, s in r["seeds"].items())
        print(f"{z}\tuntouched_R={r['untouched']['R']['all_pass']}\t"
              f"untouched_F={r['untouched']['F']['all_pass']}\t"
              f"F_vs_R={len(r['probe_F_vs_R']['raw'])}\t{seeds}\tall_ok={r['all_ok']}")
        bad += not r["all_ok"]
    return 1 if bad else 0


def _cmd_chain_t0_reference(args: argparse.Namespace) -> int:
    """Study 3 T0 blind references in Docker (aa-actual:R): each zone's
    reference.R.patch typechecks, lints, passes its inconsistency tests and the existing
    tests related to the touched files, leaves the probe minus exclusions unchanged and
    carries no hidden-test content; writes <zone>/T0/reference_check.json."""
    from aa.chains import t0_reference_check
    res = t0_reference_check(args.zones or None, root=args.tasks3, work=args.work,
                             workers=args.workers)
    for z, r in res.items():
        rel = r.get("related") or {}
        print(f"{z}\ttypecheck={r.get('typecheck_ok')}\tlint={r.get('lint_ok')}\t"
              f"tests={r.get('tests_pass')}\trelated={r.get('related_ok')}"
              f"({rel.get('passed')} passed, new_failures={len(rel.get('new_failures') or [])})\t"
              f"probe_same={r.get('probe_same')}\tleaks_clean={r['leaks'].get('clean')}\t"
              f"ok={r['ok']}" + (f"\twhy={r['why']}" if r.get("why") else ""))
    return 0 if all(r["ok"] for r in res.values()) else 1


def _cmd_chain_reclassify(args: argparse.Namespace) -> int:
    """Study-3 pilot blocking item 1: re-apply the run-status rule (network stall / no
    agent activity at the wall limit = infra) to finished steps (aa.rederive)."""
    from aa.rederive import reclassify_runs
    out = reclassify_runs(Path(args.runs), apply=not args.dry_run)
    print(f"{len(out['applied'])} step(s) -> infra"
          + (" (dry run, nothing written)" if args.dry_run else "")
          + f"; {len(out['other'])} other status difference(s) not applied")
    return 0


def _cmd_chain_reparse(args: argparse.Namespace) -> int:
    """Study-3 pilot blocking items 2-3: re-parse the transcripts' usage into result.json
    (Claude summed over every result; Codex missing without turn.completed)."""
    from aa.rederive import reparse_runs, usage_change_summary
    engines = tuple(args.engines.split(",")) if args.engines else None
    changed = reparse_runs(Path(args.runs), apply=not args.dry_run, tasks_root=args.tasks,
                           engines=engines)
    for agent, v in usage_change_summary(changed).items():
        print(f"{agent}\tsteps={v['steps']}\tnow_missing={v['now_missing']}\t"
              f"input_delta={v['input_delta']}\toutput_delta={v['output_delta']}\t"
              f"turns_delta={v['turns_delta']}")
    print(f"{len(changed)} step(s) changed" + (" (dry run)" if args.dry_run else ""))
    return 0


def _cmd_chain_rederive_trips(args: argparse.Namespace) -> int:
    """Study-3 pilot blocking item 4: re-classify RL trips from the eval outputs already
    on disk (no container)."""
    from aa.rederive import retrip_runs
    changed = retrip_runs(Path(args.runs), apply=not args.dry_run)
    print(f"{len(changed)} step(s) changed" + (" (dry run)" if args.dry_run else ""))
    return 0


def _cmd_chain_record_summaries(args: argparse.Namespace) -> int:
    """Amendment 2026-10-12c: retrospective log records for chain summaries
    (chain_result.json, cumulative.patch, chain.json status) rewritten before every
    rewrite had one, from a backup of those files taken before (writes the log only)."""
    from aa.rederive import record_past_summaries
    recs = record_past_summaries(Path(args.runs), Path(args.before), tasks_root=args.tasks)
    bad = [r["chain"] for r in recs if r["cumulative_patch"] and not (
        r["cumulative_patch"]["equals_source"] and r["cumulative_patch"]["stats_equal_before"]
        and r["cumulative_patch"]["source_older_than_backup"])]
    print(f"{len(recs)} chain(s) recorded; cumulative.patch not shown identical: "
          f"{len(bad)}" + (f" ({', '.join(bad[:10])})" if bad else ""))
    return 1 if bad else 0


def _cmd_chain_behaviour_check(args: argparse.Namespace) -> int:
    """Study-3 pilot blocking item 9: the zone's in-scope T0 inconsistency tests on every
    evaluated T1-T4 post tree (one container at a time)."""
    from aa.rederive import behaviour_check_runs
    zones = tuple(args.zones.split(",")) if args.zones else None
    out = behaviour_check_runs(Path(args.runs).resolve(), apply=not args.dry_run, zones=zones,
                               tasks_root=args.tasks, t0_root=args.tasks3)
    unified = [r for r in out if r["new"]]
    print(f"{len(out)} step(s) checked, {len(unified)} with an inconsistency unified"
          + (" (dry run)" if args.dry_run else ""))
    return 0


def _cmd_chain_scope_sanity(args: argparse.Namespace) -> int:
    """Study 3 (pilot blocking item 9): the T0 inconsistency tests on the chains'
    reference trees, step by step (Docker, one container at a time)."""
    from aa.chains import scope_sanity
    res = scope_sanity(args.zones or None, root=args.tasks3, tasks_root=args.tasks,
                       work=args.work)
    for z, r in res.items():
        for cond, c in r["conds"].items():
            for st, v in c["steps"].items():
                print(f"{z}\t{cond}\t{st}\tok={v['ok']}\t"
                      f"superseded_failing={v.get('superseded_failing')}")
    return 0 if all(r["all_ok"] for r in res.values()) else 1


def _chain_subcommands(sub: argparse._SubParsersAction) -> argparse._SubParsersAction:
    """The `aa chain` group (created by the chain runner's CLI when present)."""
    parent = sub.choices.get("chain")
    if parent is None:
        return sub.add_parser("chain", help="study 2: task chains").add_subparsers(
            dest="cmd", required=True)
    return next(a for a in parent._actions if isinstance(a, argparse._SubParsersAction))


def _add_chain_eval_parsers(sub: argparse._SubParsersAction) -> None:
    from aa.chain_eval import TASKS2
    from aa.chains import TASKS3
    chs = _chain_subcommands(sub)
    ce = chs.add_parser("evaluate", help="evaluate chain steps (result.json) and chains "
                        "(chain_result.json)")
    ce.add_argument("step_dirs", nargs="*")
    ce.add_argument("--all", action="store_true")
    ce.add_argument("--force", action="store_true")
    ce.add_argument("--workers", type=int, default=2,
                    help="chains in parallel (one loot-core container each; the Docker VM "
                    "holds two at most); an RC T0 evaluation always runs alone "
                    "(chain_eval.GATE)")
    ce.add_argument("--tasks3", type=Path, default=TASKS3,
                    help="study 3: T0 tasks, copy sites and probe exclusions")
    ce.set_defaults(func=_cmd_chain_evaluate)
    cpk = chs.add_parser("packets", help="blind design-review packets, pre-images verified")
    cpk.add_argument("--out", type=Path, default=None,
                     help="default work/review2 (study 3: work/review3)")
    cpk.add_argument("--mapping", type=Path, default=None,
                     help="default work/review2-mapping.json (study 3: review3-mapping.json)")
    cpk.add_argument("--variants", type=Path, default=config.WORK / "variants")
    cpk.add_argument("--f-runs", type=Path, default=config.ROOT / "runs2",
                     help="study 3: the study-2 F chains re-judged in the same batches")
    cpk.add_argument("--tasks3", type=Path, default=TASKS3,
                     help="study 3: T0 statements and copy sites")
    cpk.set_defaults(func=_cmd_chain_packets)
    for c in (ce, cpk):
        c.add_argument("--study", type=int, choices=(2, 3), default=None,
                       help="runs dir of the study when --runs is not given (default 2: "
                       "runs2/; 3: runs3/)")
        c.add_argument("--pilot", action="store_true",
                       help="the study's pilot runs dir (runs2-pilot/, runs3-pilot/)")
        c.add_argument("--runs", type=Path, default=None,
                       help="explicit runs dir (overrides --study/--pilot); made absolute")
        c.add_argument("--tasks", type=Path, default=TASKS2)
    cs = chs.add_parser("sanity", help="untouched trees fail every consumer test alone; "
                        "references pass cumulatively; no hidden content in references")
    cs.add_argument("zones", nargs="*")
    cs.add_argument("--tasks", type=Path, default=TASKS2)
    cs.add_argument("--work", type=Path, default=config.WORK / "sanity2")
    cs.add_argument("--no-untouched", action="store_true")
    cs.add_argument("--no-references", action="store_true")
    cs.add_argument("--workers", type=int, default=2)
    cs.set_defaults(func=_cmd_chain_sanity)
    cst = chs.add_parser("check-statements", help="leak-check every chain step's statement.md "
                         "(paths, APIs, exhaustive-search hints, consumer enumerations)")
    cst.add_argument("--tasks", type=Path, default=TASKS2)
    cst.add_argument("--tasks3", type=Path, default=TASKS3)
    cst.set_defaults(func=_cmd_chain_check_statements)
    ct0 = chs.add_parser("t0-sanity", help="study 3: T0 inconsistency tests and probe "
                         "exclusions on untouched R/F and on the seeded patches (Docker)")
    ct0.add_argument("zones", nargs="*")
    ct0.add_argument("--tasks3", type=Path, default=TASKS3)
    ct0.add_argument("--work", type=Path, default=config.WORK / "sanity3")
    ct0.add_argument("--workers", type=int, default=2)  # Docker VM: <= 2 loot-core containers
    ct0.set_defaults(func=_cmd_chain_t0_sanity)
    crc = chs.add_parser("reclassify", help="re-apply the run-status rule (network stall or "
                         "no activity at the wall limit = infra) to finished steps; rewrites "
                         "status fields only, with a record (status_reclassified)")
    crc.add_argument("--runs", type=Path, required=True)
    crc.add_argument("--dry-run", action="store_true")
    crc.set_defaults(func=_cmd_chain_reclassify)
    crp = chs.add_parser("reparse", help="re-parse step transcripts' usage into result.json "
                         "(and chain_result.json totals), with a record")
    crp.add_argument("--runs", type=Path, required=True)
    crp.add_argument("--tasks", type=Path, default=TASKS2)
    crp.add_argument("--engines", default=None, help="comma list: claude,codex (default all)")
    crp.add_argument("--dry-run", action="store_true")
    crp.set_defaults(func=_cmd_chain_reparse)
    crt = chs.add_parser("rederive-trips", help="study 3: re-classify RL dup-check trips "
                         "against the start tree from the eval outputs on disk (no container)")
    crt.add_argument("--runs", type=Path, required=True)
    crt.add_argument("--dry-run", action="store_true")
    crt.set_defaults(func=_cmd_chain_rederive_trips)
    crs = chs.add_parser("record-summaries", help="log retrospective records for chain "
                         "summaries rewritten without one, against a backup of the derived "
                         "chain files taken before (writes rederive-log.jsonl only)")
    crs.add_argument("--runs", type=Path, required=True)
    crs.add_argument("--before", type=Path, required=True,
                     help="backup root with the same <agent>/<arm>/<zone>/<chain>/ layout")
    crs.add_argument("--tasks", type=Path, default=TASKS2)
    crs.set_defaults(func=_cmd_chain_record_summaries)
    cbc = chs.add_parser("behaviour-check", help="study 3: the zone's T0 inconsistency tests "
                         "still in scope (tasks3/inconsistency-scope.json) on every evaluated "
                         "T1-T4 post tree, one container at a time")
    cbc.add_argument("--runs", type=Path, required=True)
    cbc.add_argument("--zones", default=None)
    cbc.add_argument("--tasks", type=Path, default=TASKS2)
    cbc.add_argument("--tasks3", type=Path, default=TASKS3)
    cbc.add_argument("--dry-run", action="store_true")
    cbc.set_defaults(func=_cmd_chain_behaviour_check)
    css = chs.add_parser("scope-sanity", help="study 3: the T0 inconsistency tests on the "
                         "chains' reference trees, step by step (checks "
                         "tasks3/inconsistency-scope.json; Docker, one container at a time)")
    css.add_argument("zones", nargs="*")
    css.add_argument("--tasks", type=Path, default=TASKS2)
    css.add_argument("--tasks3", type=Path, default=TASKS3)
    css.add_argument("--work", type=Path, default=config.WORK / "scope-sanity3")
    css.set_defaults(func=_cmd_chain_scope_sanity)
    ctr = chs.add_parser("t0-reference", help="study 3: check the blind T0 reference "
                         "patches (typecheck, lint, tests, probe, leak audit) in Docker")
    ctr.add_argument("zones", nargs="*")
    ctr.add_argument("--tasks3", type=Path, default=TASKS3)
    ctr.add_argument("--work", type=Path, default=config.WORK / "reference3")
    # one container: the Docker VM (6 GB) runs out of memory with two reference runs
    ctr.add_argument("--workers", type=int, default=1)
    ctr.set_defaults(func=_cmd_chain_t0_reference)


# --- evaluator (Task 9) ----------------------------------------------------------

def _cmd_evaluate(args: argparse.Namespace) -> int:
    from aa.evaluate import evaluate_all, evaluate_run
    if args.all == bool(args.run_dirs):
        print("give RUN_DIR... or --all (not both)", file=sys.stderr)
        return 2
    if args.all:
        results = evaluate_all(config.RUNS, force=args.force, workers=args.workers)
        print(f"evaluated {len(results)} run(s)")
        return 0
    for d in args.run_dirs:
        r = evaluate_run(Path(d))
        if r is None:
            print(f"{d}\tnot final")
        else:
            print(f"{d}\t{r.get('status')}\tcorrect={r.get('correct')}"
                  f"\tviolations={len(r.get('violations', []))}\teval_error={r.get('eval_error')}")
    return 0


# --- viewer / status (Task 10) ----------------------------------------------------

def _cmd_view(args: argparse.Namespace) -> int:
    from aa.viewer import write_run_view
    print(write_run_view(Path(args.run_dir), tasks_dir=args.tasks_dir))
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    from aa.status import watch, write_status
    if args.watch:
        watch(config.RUNS, interval=args.interval, total_per_cell=args.total_per_cell)
    else:
        print(write_status(config.RUNS, total_per_cell=args.total_per_cell))
    return 0


# --- tables (Task 11) -------------------------------------------------------------

def _cmd_tables(args: argparse.Namespace) -> int:
    from aa.tables import build
    build(args.runs, args.out, by=args.by)
    print(args.out / "tables.md")
    return 0


def _cmd_tables2(args: argparse.Namespace) -> int:
    from aa.tables2 import build
    build(args.runs, args.out)
    print(args.out / "tables2.md")
    return 0


def _cmd_tables3(args: argparse.Namespace) -> int:
    from aa.tables3 import build
    build(args.runs, args.out, f_runs=args.f_runs, labels=args.labels, kappa=args.kappa,
          calibration=args.calibration)
    print(args.out / "tables3.md")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aa")
    sub = p.add_subparsers(dest="group", required=True)

    sp = sub.add_parser("substrate", help="Actual checkout").add_subparsers(dest="cmd", required=True)
    sp.add_parser("fetch", help="clone Actual and check out BASE").set_defaults(func=_cmd_substrate_fetch)

    vp = sub.add_parser("variant", help="condition trees").add_subparsers(dest="cmd", required=True)
    vb = vp.add_parser("build", help="build work/variants/<cond>")
    vb.add_argument("cond", choices=config.ALL_CONDITIONS)
    vb.set_defaults(func=_cmd_variant_build)
    vi = vp.add_parser("install", help="install work/variants/<cond> as the Docker image does "
                                       "(yarn install --immutable + pinned eslint devDependencies)")
    vi.add_argument("cond", choices=config.ALL_CONDITIONS)
    vi.set_defaults(func=_cmd_variant_install)

    sup = sub.add_parser("suite", help="loot-core vitest suite").add_subparsers(dest="cmd", required=True)
    sb = sup.add_parser("baseline", help="run full suite, write work/baseline-<cond>.json")
    sb.add_argument("--cond", default="A", choices=config.ALL_CONDITIONS)
    sb.add_argument("--study2", action="store_true",
                    help="write to work/study2/ (implied for R/F; use with --cond A for the "
                         "seeded study-2 reference)")
    sb.add_argument("--timeout", type=int, default=3600)
    sb.set_defaults(func=_cmd_suite_baseline)

    eq = sub.add_parser("equivalence", help="compare two suite baselines (A vs AP, R vs F)")
    eq.add_argument("a", choices=config.ALL_CONDITIONS)
    eq.add_argument("b", choices=config.ALL_CONDITIONS)
    eq.add_argument("--study2", action="store_true",
                    help="read work/study2/ (implied when either side is R/F)")
    eq.set_defaults(func=_cmd_equivalence)

    pr = sub.add_parser("probe2", help="study 2: behavioural probe of the zones on A/R/F "
                                       "(substrate/study2/probe), diffed against the first")
    pr.add_argument("--conds", default="A,R,F")
    pr.add_argument("--timeout", type=int, default=1800)
    pr.set_defaults(func=_cmd_probe2)

    cp = sub.add_parser("checker", help="runtime probe").add_subparsers(dest="cmd", required=True)
    cb = cp.add_parser("baseline", help="write substrate/checker/baseline-writers.json")
    cb.add_argument("--conds", default=",".join(config.CONDITIONS))
    cb.add_argument("--timeout", type=int, default=3600)
    cb.set_defaults(func=_cmd_checker_baseline)
    cc = cp.add_parser("canary", help="check the probe catches the canary's writes")
    cc.add_argument("--conds", default=",".join(config.CONDITIONS))
    cc.add_argument("--timeout", type=int, default=600)
    cc.set_defaults(func=_cmd_checker_canary)

    tp = sub.add_parser("tasks", help="mine tasks from history").add_subparsers(dest="cmd", required=True)
    for name, fn, hlp in (("preview", _cmd_tasks_preview, "count candidates per drop reason"),
                          ("mine", _cmd_tasks_mine, "list candidates (needs aplus-frozen)"),
                          ("materialise", _cmd_tasks_materialise, "write tasks/<id>/ + _ledger.json")):
        t = tp.add_parser(name, help=hlp)
        t.add_argument("--since", default="2024-10-01")
        if name == "materialise":
            t.add_argument("--sha", nargs="*", default=[])
        t.set_defaults(func=fn)
    tc = tp.add_parser("check", help="sanity-check every materialised task in the condition "
                                     "images (all four conditions); records to the ledger")
    tc.add_argument("--task", nargs="*", default=[])
    tc.add_argument("--force", action="store_true", help="rerun tasks that have sanity.json")
    tc.set_defaults(func=_cmd_tasks_check)
    tp.add_parser("check-statements", help="leak-check every surviving task's statement.md"
                  ).set_defaults(func=_cmd_tasks_check_statements)
    ts = tp.add_parser("select-preview", help="survivors + ledger drop reasons (read-only)")
    ts.add_argument("-v", "--verbose", action="store_true", help="list every non-survivor")
    ts.set_defaults(func=_cmd_tasks_select_preview)

    isp = sub.add_parser("issues", help="tasks authored from open GitHub issues"
                         ).add_subparsers(dest="cmd", required=True)
    ii = isp.add_parser("init", help="scaffold tasks/issue-<n>/ (task.json, empty reverts)")
    ii.add_argument("--issue", type=int, required=True)
    ii.add_argument("--title", required=True)
    ii.add_argument("--date", required=True, help="issue creation date, YYYY-MM-DD")
    ii.add_argument("--hidden", nargs="+", required=True,
                    help="new hidden test paths under packages/loot-core")
    ii.set_defaults(func=_cmd_issues_init)
    ic = isp.add_parser("check", help="sanity-check issue tasks in the condition images; "
                                      "writes sanity.json and the ledger")
    ic.add_argument("--task", nargs="*", default=[])
    ic.add_argument("--conds", default=",".join(config.CONDITIONS))
    ic.add_argument("--workers", type=int, default=1, help="containers in parallel")
    ic.add_argument("--force", action="store_true", help="rerun tasks that have sanity.json")
    ic.set_defaults(func=_cmd_issues_check)
    ie = isp.add_parser("eligibility", help="protected-call eligibility of reference.A.patch "
                                            "(records task.json + ledger)")
    ie.add_argument("--task", nargs="*", default=[])
    ie.set_defaults(func=_cmd_issues_eligibility)

    mp = sub.add_parser("memo-probe", help="memorisation probe").add_subparsers(dest="cmd", required=True)
    for name, fn in (("estimate", _cmd_memo_estimate), ("run", _cmd_memo_run)):
        m = mp.add_parser(name)
        m.add_argument("--workers", type=int, default=4)
        if name == "run":
            m.add_argument("--missing-only", action="store_true",
                           help="only re-probe (task, agent) pairs without a similarity")
            m.add_argument("--agents", default="",
                           help="comma-separated agents to probe (default: all); the other "
                                "agents' entries are left as they are")
            m.add_argument("--task", nargs="*", default=[], help="only these task ids")
        m.set_defaults(func=fn)

    ip = sub.add_parser("image", help="docker images").add_subparsers(dest="cmd", required=True)
    ib = ip.add_parser("build", help="build aa-actual:<cond>")
    ib.add_argument("cond", choices=config.ALL_CONDITIONS)
    ib.set_defaults(func=_cmd_image_build)
    ip.add_parser("build-cli", help="build the repo-free aa-cli image (memo probe)"
                  ).set_defaults(func=_cmd_image_build_cli)
    i3 = ip.add_parser("build-study3", help="study 3: rebuild R, RG, RL, RC together (fresh "
                       "variants, install stages uncached, one cli stage), verify them and "
                       "write out/study3/images.json")
    i3.add_argument("--inspect-only", action="store_true",
                    help="no build: inspect the current images and rewrite the manifest")
    i3.set_defaults(func=_cmd_image_build_study3)

    ev = sub.add_parser("evaluate", help="evaluate run dirs, write result.json")
    ev.add_argument("run_dirs", nargs="*")
    ev.add_argument("--all", action="store_true")
    ev.add_argument("--force", action="store_true")
    ev.add_argument("--workers", type=int, default=2)
    ev.set_defaults(func=_cmd_evaluate)

    rp = sub.add_parser("run", help="run agents (resumable)")
    rp.add_argument("--agent", required=True, choices=config.AGENTS)
    rp.add_argument("--conds", default=",".join(config.CONDITIONS))
    rp.add_argument("--tasks", default="all")
    rp.add_argument("--passes", type=int, default=config.PASSES)
    rp.add_argument("--workers", type=int, default=config.CONCURRENCY)
    rp.set_defaults(func=_cmd_run)

    r1 = sub.add_parser("run-one", help="one run, for debugging")
    r1.add_argument("--agent", required=True, choices=config.AGENTS)
    r1.add_argument("--cond", required=True, choices=config.CONDITIONS)
    r1.add_argument("--task", required=True)
    r1.add_argument("--pass", dest="pass_idx", type=int, default=0)
    r1.set_defaults(func=_cmd_run_one)

    from aa.chain_runner import CHAINS, CONDITIONS2
    from aa.chains import TASKS2, TASKS3
    chp = sub.add_parser("chain", help="studies 2 and 3: task chains (state carried between "
                         "steps)").add_subparsers(dest="cmd", required=True)
    cr_ = chp.add_parser("run", help="run chains in parallel, steps in series (resumable); "
                         "study 3 interleaves the arms per chain index")
    cr_.add_argument("--agent", required=True, choices=config.AGENTS)
    cr_.add_argument("--conds", default=None,
                     help="comma list; default the study's (R,F; study 3: R,RG,RL,RC)")
    cr_.add_argument("--zones", default="all", help="comma list or 'all' (tasks2/*/chain.json)")
    cr_.add_argument("--chains", default=str(CHAINS),
                     help="count ('8' = 0..7) or indices ('0,2-3')")
    cr_.add_argument("--workers", type=int, default=None,
                     help="chains in parallel; default study 2: 3, study 3: 2 (Docker VM)")
    cr_.add_argument("--min-codex-auth-hours", type=float, default=24.0,
                     help="codex: refuse to start unless the login lasts this long")
    cr_.add_argument("--dry-run", action="store_true",
                     help="list what each chain would do (resume step, later step dirs "
                     "discarded); runs nothing")
    cr_.set_defaults(func=_cmd_chain_run)
    c1 = chp.add_parser("run-one", help="one chain (resumable), or one step with --step")
    c1.add_argument("--agent", required=True, choices=config.AGENTS)
    c1.add_argument("--cond", required=True,
                    choices=tuple(dict.fromkeys(CONDITIONS2 + config.CONDITIONS3)))
    c1.add_argument("--zone", required=True)
    c1.add_argument("--chain", type=int, default=0)
    c1.add_argument("--step", default=None, help="run only this step (e.g. T2); later steps "
                    "are removed")
    c1.set_defaults(func=_cmd_chain_run_one)
    for c in (cr_, c1):
        c.add_argument("--study", type=int, choices=(2, 3), default=None,
                       help="default: 3 if an RG/RL/RC arm is named, else 2")
        c.add_argument("--runs", type=Path, default=None,
                       help="default runs2/ (study 3: runs3/); made absolute")
        c.add_argument("--pilot", action="store_true",
                       help="default runs dir runs2-pilot/ or runs3-pilot/")
        c.add_argument("--tasks", type=Path, default=TASKS2)
        c.add_argument("--t0-tasks", type=Path, default=TASKS3,
                       help="study 3: RC's T0 statements (<dir>/<zone>/T0/statement.md)")

    _add_chain_eval_parsers(sub)

    vw = sub.add_parser("view", help="render <run_dir>/view.html")
    vw.add_argument("run_dir")
    vw.add_argument("--tasks-dir", type=Path, default=None)
    vw.set_defaults(func=_cmd_view)

    st = sub.add_parser("status", help="render runs/status.html")
    st.add_argument("--watch", action="store_true")
    st.add_argument("--interval", type=float, default=30.0)
    st.add_argument("--total-per-cell", type=int, default=None)
    st.set_defaults(func=_cmd_status)

    tb = sub.add_parser("tables", help="write out/tables.md and out/summary.json")
    tb.add_argument("--runs", type=Path, default=config.RUNS)
    tb.add_argument("--out", type=Path, default=config.ROOT / "out")
    tb.add_argument("--by", choices=("source", "ai_label", "contaminated"), default=None,
                    help="split every table by this per-task field of result.json")
    tb.set_defaults(func=_cmd_tables)

    t2 = sub.add_parser("tables2", help="study 2: write out2/tables2.md and out2/summary2.json")
    t2.add_argument("--runs", type=Path, default=config.ROOT / "runs2")
    t2.add_argument("--out", type=Path, default=config.ROOT / "out2")
    t2.set_defaults(func=_cmd_tables2)

    t3 = sub.add_parser("tables3", help="study 3: write out/study3/tables3.md and summary3.json")
    t3.add_argument("--runs", type=Path, default=config.ROOT / "runs3")
    t3.add_argument("--out", type=Path, default=config.ROOT / "out" / "study3")
    t3.add_argument("--f-runs", type=Path, default=config.ROOT / "runs2",
                    help="study-2 runs for the descriptive F column (cond F only)")
    t3.add_argument("--labels", type=Path, default=None,
                    help="judge labels JSON (plan Task 7), keyed agent/arm/zone/chain/T<k>")
    t3.add_argument("--kappa", type=Path, default=None,
                    help="JSON {t2_reuse|one_place|completeness|interface: kappa}; judged "
                    "rows without one are printed 'kappa pending'")
    t3.add_argument("--calibration", type=Path,
                    default=config.ROOT / "out" / "study3" / "ratchet-calibration-summary.json",
                    help="ratchet calibration summary (firing_by_step_at_chosen.R), the "
                    "benchmark of ratchet firing (amendment 2026-10-12b, item 5)")
    t3.set_defaults(func=_cmd_tables3)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
