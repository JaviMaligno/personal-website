#!/usr/bin/env python3
"""Descriptive pilot report: correctness, paired changes, and predicted actions."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import protocol
import run
import storage


def analyze(root):
    data = run.manifest(root)
    selected = run.selection(root, data)
    predicted = run.predictions(root, selected)
    execution = run.execution(root, data)
    cases = {c["id"]: c for c in selected["cases"]}
    parsed_calls, rows, failures, controls = {}, [], Counter(), []
    for job in execution["jobs"]:
        case = cases[job["case_id"]]
        inputs = execution["inputs"][case["id"]]
        response = storage.latest(root, job)
        status, decisions = "missing", None
        if response:
            status = response["status"]
            if status == "ok":
                if response.get("truncated"):
                    status = "truncated"
                else:
                    try:
                        decisions = protocol.parse_decisions(response.get("text", ""), inputs)
                        status = "valid"
                    except (ValueError, TypeError, KeyError):
                        status = "invalid_output"
        failures[status] += 1
        key = (case["id"], job["model_id"], job["variant"], job["repetition"])
        if decisions is not None:
            parsed_calls[key] = decisions
        for source in sorted({x["source"] for x in inputs}):
            subset = [x for x in inputs if x["source"] == source]
            correct = sum(decisions[x["id"]] == x["expected"] for x in subset) if decisions else 0
            rows.append({"case_id": case["id"], "task_id": case["task"]["id"],
                         "family": case["task"]["family"], "kind": case["kind"],
                         "model_id": job["model_id"], "variant": job["variant"],
                         "repetition": job["repetition"], "source": source, "status": status,
                         "valid_decisions": len(subset) if decisions is not None else 0,
                         "expected_decisions": len(subset), "correct": correct})
        if case["kind"] != "natural":
            controls.append({"case_id": case["id"], "model_id": job["model_id"],
                             "variant": job["variant"], "repetition": job["repetition"],
                             "passed": decisions == case["expected_by_variant"][job["variant"]]})

    # Compare both exact predicted actions, not just whether some change occurred.
    comparisons = []
    for explanation in predicted["entries"]:
        if not explanation["parsed"]:
            continue
        cid = explanation["case_id"]
        case = cases[cid]
        probes = [p for p in execution["accepted_probes"]
                  if p["case_id"] == cid and p["model_id"] == explanation["model_id"]]
        populations = {
            "fixed": list(explanation["parsed"]["predictions"].items()),
            "proposed": [(p["input_id"], p["probe"]["actions"]) for p in probes],
        }
        for model in data["config"]["models"]:
            for variant in case["variants"]:
                if variant == "original":
                    continue
                for source, pairs in populations.items():
                    if not pairs:
                        continue
                    counts = Counter(expected_pairs=len(pairs) * data["config"]["repetitions"])
                    for rep in range(data["config"]["repetitions"]):
                        a = parsed_calls.get((cid, model["id"], "original", rep))
                        b = parsed_calls.get((cid, model["id"], variant, rep))
                        for input_id, actions in pairs:
                            pa, pb = actions["original"], actions[variant]
                            if pa == "undetermined" or pb == "undetermined":
                                counts["abstained_pairs"] += 1
                                continue
                            if a is None or b is None:
                                counts["missing_or_invalid_pairs"] += 1
                                continue
                            counts["scorable_pairs"] += 1
                            aa, ab = a[input_id], b[input_id]
                            counts["observed_changes"] += aa != ab
                            counts["predicted_changes"] += pa != pb
                            counts["exact_action_pair_matches"] += (pa, pb) == (aa, ab)
                            counts["change_detection_matches"] += (pa != pb) == (aa != ab)
                            counts["always_no_change_baseline_matches"] += aa == ab
                            if pa != pb:
                                counts["predicted_change_realized_exactly"] += (pa, pb) == (aa, ab)
                    comparisons.append({"case_id": cid, "kind": case["kind"],
                        "task_id": case["task"]["id"], "family": case["task"]["family"],
                        "explainer": explanation["model_id"], "executor": model["id"],
                        "variant": variant, "source": source, **counts})

    within = []
    for case in selected["cases"]:
        for model in data["config"]["models"]:
            for variant in case["variants"]:
                for x in execution["inputs"][case["id"]]:
                    observations = [actions[x["id"]] for key, actions in parsed_calls.items()
                                    if key[:3] == (case["id"], model["id"], variant)]
                    within.append({"case_id": case["id"], "kind": case["kind"],
                        "model_id": model["id"], "variant": variant, "input_id": x["id"],
                        "source": x["source"], "counts": dict(Counter(observations)),
                        "valid_repetitions": len(observations)})
    usage, attempts = {}, Counter()
    for path in (root / "calls").glob("*.json"):
        history = storage.read(path)
        mid = history["job"]["model_id"]
        usage.setdefault(mid, Counter())
        for attempt in history["attempts"]:
            attempts[mid] += 1
            for name, value in attempt.get("usage", {}).items():
                if type(value) in (int, float):
                    usage[mid][name] += value
    return {"scope": "Descriptive feasibility pilot; no equivalence or human-trust inference.",
            "selected_cases": sum(c["kind"] == "natural" for c in cases.values()),
            "reviewed_candidates": len(selected["ledger"]),
            "eligible_candidates": sum(r["decision"] == "eligible" for r in selected["ledger"]),
            "status_counts": dict(failures), "complete": not any(failures[s] for s in ("missing", "interrupted")),
            "invalid_explanations": sum(e["parsed"] is None for e in predicted["entries"]),
            "controls_passed": bool(controls) and all(c["passed"] for c in controls),
            "controls": controls, "correctness": rows, "prediction_comparisons": comparisons,
            "within_variant_frequencies": within,
            "attempts": dict(attempts), "usage": {k: dict(v) for k, v in usage.items()}}


def markdown(report):
    lines = ["# Pilot report", "", report["scope"], "",
             f"Selected {report['selected_cases']} cases from {report['reviewed_candidates']} candidates "
             f"({report['eligible_candidates']} eligible).", "",
             f"Execution status: {report['status_counts']}. Invalid explanations: {report['invalid_explanations']}.",
             f"All sensitivity controls passed: {report['controls_passed']}.", "",
             "Correctness below uses the original assignment as reference. Invalid calls remain "
             "in the expected denominator. Controls have their own variant-specific check in JSON.", "",
             "| Kind | Task | Executor | Variant | Rep | Set | Correct / expected | Status |",
             "|---|---|---|---|---|---|---|---|"]
    for r in report["correctness"]:
        lines.append(f"| {r['kind']} | {r['task_id']} | {r['model_id']} | {r['variant']} | "
                     f"{r['repetition']} | {r['source']} | {r['correct']}/{r['expected_decisions']} | {r['status']} |")
    lines += ["", "## Do the explanations predict the change?", "",
              "Exact matches require both predicted actions, before and after the intervention, "
              "to match. Compare change detection to the always-no-change baseline; many tasks "
              "may be unchanged. With one repetition these are descriptive counts only.", "",
              "| Kind | Task | Explainer → executor | Variant | Set | Scorable / expected | Exact pairs | Change detection | No-change baseline | Abstentions |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in report["prediction_comparisons"]:
        lines.append(f"| {r['kind']} | {r['task_id']} | {r['explainer']} → {r['executor']} | "
                     f"{r['variant']} | {r['source']} | {r.get('scorable_pairs', 0)}/{r['expected_pairs']} | "
                     f"{r.get('exact_action_pair_matches', 0)} | {r.get('change_detection_matches', 0)} | "
                     f"{r.get('always_no_change_baseline_matches', 0)} | {r.get('abstained_pairs', 0)} |")
    lines += ["", "Within-variant frequencies and raw provider usage are in report.json. "
              "Fixed and proposed cases are kept separate. Repeated decisions are not independent concepts.", "",
              "No monetary total is inferred from token counts. Configure and document provider "
              "pricing separately before budgeting a larger study.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    try:
        with storage.lock(args.run):
            report = analyze(args.run)
            storage.write(args.run / "report.json", report)
            (args.run / "report.md").write_text(markdown(report))
            print(f"Saved {args.run / 'report.md'}")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
