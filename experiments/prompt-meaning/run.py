#!/usr/bin/env python3
"""Staged pilot. Network calls only with --live and an explicit per-invocation cap."""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import bank
import protocol
import storage
import transport

HERE = Path(__file__).resolve().parent
SOURCE_FILES = ("bank.py", "protocol.py", "run.py", "storage.py", "transport.py", "analyze.py")


def source_hashes():
    return {name: bank.digest((HERE / name).read_text()) for name in SOURCE_FILES}


def initialize(root, config_path):
    config = storage.read(config_path)
    if set(config) != {"models", "selection_limit", "repetitions"}:
        raise ValueError("Config keys: models, selection_limit, repetitions")
    if not isinstance(config["models"], list) or len(config["models"]) != 2:
        raise ValueError("Pilot requires exactly two configured models")
    for model in config["models"]:
        transport.validate_model(model)
    if len({m["id"] for m in config["models"]}) != 2:
        raise ValueError("Model IDs must differ")
    if len({(m["transport"], m["endpoint"], m["model"]) for m in config["models"]}) != 2:
        raise ValueError("Configure two distinct model deployments, not two aliases of one deployment")
    if (type(config["selection_limit"]) is not int or not 1 <= config["selection_limit"] <= 10
            or type(config["repetitions"]) is not int or config["repetitions"] < 1):
        raise ValueError("selection_limit must be 1..10; repetitions must be positive")
    storage.freeze(root / "manifest.json", {"created": storage.now(), "config": config,
                                           "bank": bank.build_bank(), "sources": source_hashes()})


def manifest(root):
    data = storage.frozen(root / "manifest.json")
    if data["sources"] != source_hashes():
        raise ValueError("Harness changed since init. Use a new run; do not mix instruments.")
    bank.validate_bank(data["bank"])
    return data


def generation_jobs(data):
    jobs = []
    for i, task in enumerate(data["bank"]["tasks"]):
        # Counterbalance which writer gets first consideration within an assignment.
        models = data["config"]["models"][::1 if i % 2 == 0 else -1]
        for model in models:
            jobs.append({"stage": "generate", "task_id": task["id"], "model_id": model["id"],
                         "prompt": bank.brief(task)})
    return jobs


def require_complete(root, jobs):
    records = []
    for job in jobs:
        response = storage.latest(root, job)
        if response is None or response["status"] == "interrupted":
            raise ValueError("Stage is incomplete. Resolve missing/interrupted calls before freezing.")
        records.append({"job": job, "response": response})
    return records


def usable(response):
    return (response["status"] == "ok" and not response.get("truncated", False)
            and isinstance(response.get("text"), str) and bool(response["text"].strip()))


def prepare_review(root, data):
    records = require_complete(root, generation_jobs(data))
    rows = []
    for record in records:
        job, response = record["job"], record["response"]
        rows.append({"candidate_id": bank.digest(job), "task_id": job["task_id"],
                     "writer_id": job["model_id"], "response_sha256": bank.digest(response),
                     "response_status": response["status"], "truncated": response.get("truncated"),
                     "prompt_text": response.get("text", ""),
                     "decision": "pending", "reason": "", "term": "", "clause": "",
                     "replacement": "", "rule_ids": [], "explicit_na_reason": "",
                     "terminology_provenance": "unverified"})
    storage.write(root / "review.json", {"reviewer": "", "entries": rows}, exclusive=True)


def freeze_selection(root, data):
    if (root / "selection.json").exists():
        raise ValueError("Selection already frozen")
    review = storage.read(root / "review.json")
    if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
        raise ValueError("Record who reviewed the candidate ledger")
    records = require_complete(root, generation_jobs(data))
    rows = review["entries"]
    if [r["candidate_id"] for r in rows] != [bank.digest(r["job"]) for r in records]:
        raise ValueError("Review must retain every candidate in prespecified order")
    tasks = {t["id"]: t for t in data["bank"]["tasks"]}
    cases, selected_tasks, ledger = [], set(), []
    for entry, record in zip(rows, records):
        response, job = record["response"], record["job"]
        if (entry["response_sha256"] != bank.digest(response)
                or entry["prompt_text"] != response.get("text", "")
                or entry["task_id"] != job["task_id"] or entry["writer_id"] != job["model_id"]):
            raise ValueError("Candidate response changed after review was prepared")
        if entry["decision"] not in {"eligible", "excluded"} or not entry["reason"].strip():
            raise ValueError("Every candidate needs an eligibility decision and a reason")
        selected = False
        if entry["decision"] == "eligible":
            if not usable(response):
                raise ValueError("Failed/truncated/empty generations cannot be eligible")
            task = tasks[job["task_id"]]
            edited = protocol.variants(response["text"], entry, task)
            if len(cases) < data["config"]["selection_limit"] and task["id"] not in selected_tasks:
                cases.append({"id": entry["candidate_id"], "kind": "natural", "task": task,
                              "writer_id": job["model_id"], "term": entry["term"],
                              "clause": entry["clause"], "variants": edited})
                selected_tasks.add(task["id"])
                selected = True
        ledger.append({**entry, "selected": selected})
    storage.freeze(root / "selection.json", {
        "manifest_sha256": bank.digest(data), "frozen": storage.now(),
        "reviewer": review["reviewer"], "ledger": ledger, "cases": cases + bank.controls()})


def selection(root, data):
    result = storage.frozen(root / "selection.json")
    if result["manifest_sha256"] != bank.digest(data):
        raise ValueError("Selection belongs to another manifest")
    return result


def explanation_jobs(selected, data):
    jobs = []
    for case in selected["cases"]:
        for model in data["config"]["models"]:
            slots = protocol.slots(case, model["id"])
            jobs.append({"stage": "explain", "case_id": case["id"], "model_id": model["id"],
                         "slots": slots, "prompt": protocol.explain_prompt(case, slots)})
    return jobs


def freeze_predictions(root, data):
    selected = selection(root, data)
    records = require_complete(root, explanation_jobs(selected, data))
    cases = {c["id"]: c for c in selected["cases"]}
    predictions = []
    for record in records:
        job, response = record["job"], record["response"]
        parsed, error = None, None
        if usable(response):
            try:
                parsed = protocol.parse_explanation(response["text"], cases[job["case_id"]], job["slots"])
            except (ValueError, TypeError, KeyError) as exc:
                error = str(exc)
        else:
            error = "Failed, empty or truncated explanation"
        predictions.append({"case_id": job["case_id"], "model_id": job["model_id"],
                            "job_sha256": bank.digest(job), "response_sha256": bank.digest(response),
                            "parsed": parsed, "error": error})
    storage.freeze(root / "predictions.json", {"selection_sha256": bank.digest(selected),
                                               "frozen": storage.now(), "entries": predictions})


def predictions(root, selected):
    data = storage.frozen(root / "predictions.json")
    if data["selection_sha256"] != bank.digest(selected):
        raise ValueError("Predictions belong to another selection")
    return data


def probe_rows(predicted):
    rows = []
    for entry in predicted["entries"]:
        if entry["parsed"]:
            for i, probe in enumerate(entry["parsed"]["probes"]):
                rows.append({"id": bank.digest([entry["case_id"], entry["model_id"], i]),
                             "case_id": entry["case_id"], "model_id": entry["model_id"],
                             "probe": probe, "decision": "pending", "reason": ""})
    return rows


def prepare_probes(root, data):
    selected = selection(root, data)
    predicted = predictions(root, selected)
    storage.write(root / "probe-review.json", {"reviewer": "", "entries": probe_rows(predicted)},
                  exclusive=True)


def freeze_execution(root, data):
    selected = selection(root, data)
    predicted = predictions(root, selected)
    review = storage.read(root / "probe-review.json")
    if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
        raise ValueError("Record who reviewed the probes (even when no probes were proposed)")
    expected = probe_rows(predicted)
    if len(expected) != len(review["entries"]):
        raise ValueError("Probe review must retain every proposed probe")
    cases = {c["id"]: c for c in selected["cases"]}
    inputs = {c["id"]: [{**x, "source": "fixed"} for x in c["task"]["cases"]]
              for c in selected["cases"]}
    accepted = []
    for original, row in zip(expected, review["entries"]):
        if any(row.get(k) != original[k] for k in ("id", "case_id", "model_id", "probe")):
            raise ValueError("Probe content changed after predictions were frozen")
        if row["decision"] not in {"accept", "reject"} or not row["reason"].strip():
            raise ValueError("Every probe requires an accept/reject decision and reason")
        if row["decision"] == "accept":
            case = cases[row["case_id"]]
            x = row["probe"]["input"]
            gold = bank.oracle(case["task"], x)
            # Reuse fixed or already proposed identical inputs; retain each prediction separately.
            existing = next((r for r in inputs[case["id"]] if r["input"] == x), None)
            if existing:
                input_id = existing["id"]
            else:
                input_id = "p-" + bank.digest(x)[:16]
                inputs[case["id"]].append({"id": input_id, "input": x,
                                          "expected": gold, "source": "probe"})
            accepted.append({**row, "input_id": input_id})
    jobs = []
    for case in selected["cases"]:
        for model in data["config"]["models"]:
            for repetition in range(data["config"]["repetitions"]):
                ordered = list(inputs[case["id"]])
                random.Random(bank.digest([case["id"], model["id"], repetition])).shuffle(ordered)
                for variant in case["variants"]:
                    jobs.append({"stage": "execute", "case_id": case["id"],
                                 "model_id": model["id"], "variant": variant,
                                 "repetition": repetition,
                                 "input_ids": [x["id"] for x in ordered],
                                 "prompt": protocol.execute_prompt(case, variant, ordered)})
    # Interleave variants/models to avoid running one whole condition during a transient outage.
    random.Random(20260921).shuffle(jobs)
    storage.freeze(root / "execution.json", {"predictions_sha256": bank.digest(predicted),
        "selection_sha256": bank.digest(selected), "frozen": storage.now(),
        "review": review, "accepted_probes": accepted, "inputs": inputs, "jobs": jobs})


def execution(root, data):
    selected = selection(root, data)
    predicted = predictions(root, selected)
    result = storage.frozen(root / "execution.json")
    if (result["predictions_sha256"] != bank.digest(predicted)
            or result["selection_sha256"] != bank.digest(selected)):
        raise ValueError("Execution belongs to other frozen inputs")
    return result


def perform(root, data, stage, live=False, max_calls=0, retry_errors=False,
            complete=transport.complete):
    if stage == "generate":
        if (root / "selection.json").exists():
            raise ValueError("Generation frozen by selection; use a new run for changes")
        jobs = generation_jobs(data)
    elif stage == "explain":
        if (root / "predictions.json").exists():
            raise ValueError("Explanations already frozen; use a new run for changes")
        jobs = explanation_jobs(selection(root, data), data)
    else:
        jobs = execution(root, data)["jobs"]
    pending, errors = [], 0
    for job in jobs:
        previous = storage.latest(root, job)
        if previous is None:
            pending.append(job)
        elif previous["status"] in {"transport_error", "interrupted"}:
            errors += 1
            if retry_errors:
                pending.append(job)
    summary = {"stage": stage, "jobs": len(jobs), "pending": len(pending),
               "transport_or_interrupted": errors, "live": live}
    print(summary)
    if not live:
        return summary
    if max_calls < 1:
        raise ValueError("Live execution requires --max-calls greater than zero")
    models = {m["id"]: m for m in data["config"]["models"]}
    # Validate all needed credentials before spending on any call.
    if complete is transport.complete:
        for model_id in {j["model_id"] for j in pending[:max_calls]}:
            transport.request_parts(models[model_id], "preflight")
    for i, job in enumerate(pending[:max_calls], 1):
        result = storage.call(root, job, models[job["model_id"]], complete)
        print(f"{i}/{min(len(pending), max_calls)} {stage} {job['model_id']} {result['status']}", flush=True)
        if result.get("error") in {"HTTP 401", "HTTP 403"}:
            raise ValueError("Authentication/permission failure: stopped before spending on the rest of the stage")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "validate-bank", "generate", "prepare-review",
        "freeze-selection", "explain", "freeze-predictions", "prepare-probes", "freeze-execution",
        "execute", "status"])
    parser.add_argument("--run", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--max-calls", type=int, default=0)
    parser.add_argument("--retry-errors", action="store_true")
    args = parser.parse_args()
    if args.command == "validate-bank":
        b = bank.build_bank()
        print(f"{len(b['tasks'])} tasks, 4 families, {sum(len(t['cases']) for t in b['tasks'])} gold cases OK")
        return
    if args.run is None:
        parser.error("--run is required")
    try:
        with storage.lock(args.run):
            if args.command == "init":
                if args.config is None:
                    parser.error("init requires --config")
                initialize(args.run, args.config)
                print("Manifest frozen. No network calls made.")
                return
            data = manifest(args.run)
            if args.command in {"generate", "explain", "execute"}:
                perform(args.run, data, args.command, args.live, args.max_calls, args.retry_errors)
            elif args.command == "status":
                print({"snapshots": [p.name for p in args.run.glob("*.json")],
                       "call_histories": len(list((args.run / "calls").glob("*.json")))})
            else:
                commands = {"prepare-review": prepare_review, "freeze-selection": freeze_selection,
                            "freeze-predictions": freeze_predictions, "prepare-probes": prepare_probes,
                            "freeze-execution": freeze_execution}
                commands[args.command](args.run, data)
                print(f"{args.command}: saved")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
