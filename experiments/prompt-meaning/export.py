#!/usr/bin/env python3
"""Export a completed run without endpoints, project IDs, credential paths or response IDs.

Original provider envelopes stay in the ignored run directory. Public records
contain exact textual answers and native token counts; the original hashes are
retained as provenance, not claimed to hash the redacted representation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import analyze
import bank
import run
import storage

PUBLIC_MODEL_FIELDS = {"id", "transport", "max_tokens", "temperature", "thinking"}
RESPONSE_FIELDS = {"status", "text", "truncated", "finish_reason", "usage", "latency_s",
                   "error", "attempt", "started", "finished"}


def export(root, out):
    manifest = run.manifest(root)
    selected = run.selection(root, manifest)
    predictions = run.predictions(root, selected)
    execution = run.execution(root, manifest)
    report = analyze.analyze(root)
    if not report["complete"]:
        raise ValueError("Finish or account for every execution before exporting")
    records = []
    jobs = (run.generation_jobs(manifest) + run.explanation_jobs(selected, manifest)
            + execution["jobs"])
    for job in jobs:
        history = storage.read(storage.job_path(root, job))
        records.append({"job": job, "original_history_sha256": bank.digest(history),
                        "attempts": [{k: v for k, v in a.items() if k in RESPONSE_FIELDS}
                                     for a in history["attempts"]]})
    models = [{k: v for k, v in m.items() if k in PUBLIC_MODEL_FIELDS}
              for m in manifest["config"]["models"]]
    payload = {"notice": "Redacted export: provider envelopes and private routing remain local. "
                         "Public IDs label the models; private deployment aliases are omitted.",
               "original_manifest_sha256": bank.digest(manifest),
               "created": manifest["created"], "sources": manifest["sources"],
               "config": {**manifest["config"], "models": models}, "bank": manifest["bank"],
               "selection": selected, "predictions": predictions, "execution": execution,
               "records": records}
    encoded = json.dumps(payload, ensure_ascii=False)
    for model in manifest["config"]["models"]:
        private_values = [model[k] for k in ("endpoint", "billing_project", "key_file") if k in model]
        if any(value and value in encoded for value in private_values):
            raise ValueError("Private routing data found in public payload; inspect locally")
    out.mkdir(parents=True, exist_ok=True)
    storage.write(out / "data.json", payload, exclusive=True)
    storage.write(out / "report.json", report, exclusive=True)
    (out / "report.md").write_text(analyze.markdown(report))
    print(f"Exported {len(records)} call histories to {out}; private routing omitted.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    with storage.lock(args.run):
        export(args.run, args.out)


if __name__ == "__main__":
    main()
