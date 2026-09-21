"""Inspect exported decisions; never repair invalid outputs or run new model calls.

This is a descriptive view of the prespecified contrasts. The primary counters
remain those in report.json. Error examples are retained in full, not sampled.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import protocol


def inspect(out):
    data = json.loads((out / "data.json").read_text())
    cases = {c["id"]: c for c in data["selection"]["cases"]}
    parsed, invalid, wrong_handoffs = {}, [], []
    for history in data["records"]:
        job, response = history["job"], history["attempts"][-1]
        if job["stage"] != "execute":
            continue
        key = (job["case_id"], job["model_id"], job["variant"], job["repetition"])
        inputs = data["execution"]["inputs"][job["case_id"]]
        if response["status"] != "ok" or response.get("truncated"):
            invalid.append({"job": job, "response": response})
            continue
        try:
            actions = protocol.parse_decisions(response["text"], inputs)
        except (ValueError, TypeError, KeyError):
            invalid.append({"job": job, "response": response})
            continue
        parsed[key] = actions
        if cases[job["case_id"]]["kind"] == "unmodified":
            for x in inputs:
                if actions[x["id"]] != x["expected"]:
                    wrong_handoffs.append({"case": job["case_id"], "model": job["model_id"],
                        "rep": job["repetition"], "input": x, "actual": actions[x["id"]]})
    effects, changes, coverage, errors = defaultdict(Counter), [], defaultdict(Counter), []
    repetitions = data["config"]["repetitions"]
    for case in cases.values():
        if case["kind"] != "synthetic":
            continue
        for model in data["config"]["models"]:
            for variant in ("original", "substituted"):
                group = effects[(case["label_category"], model["id"], variant)]
                for x in case["task"]["cases"]:
                    pairs = []
                    for rep in range(repetitions):
                        a = parsed.get((case["id"], model["id"], "eliminated", rep))
                        b = parsed.get((case["id"], model["id"], variant, rep))
                        group["expected_pairs"] += 1
                        if a is not None and b is not None:
                            pair = (a[x["id"]], b[x["id"]])
                            pairs.append(pair)
                            group["valid_pairs"] += 1
                            group["changed_pairs"] += pair[0] != pair[1]
                    if len(pairs) != repetitions:
                        group["incomplete_inputs"] += 1
                    elif len(set(pairs)) != 1:
                        group["unstable_inputs"] += 1
                    else:
                        group["stable_inputs"] += 1
                        if pairs[0][0] != pairs[0][1]:
                            group["stable_changed_inputs"] += 1
                            changes.append({"case": case["id"], "model": model["id"],
                                "variant": variant, "input": x, "without_clause": pairs[0][0],
                                "with_clause": pairs[0][1]})
    for e in data["predictions"]["entries"]:
        case = cases[e["case_id"]]
        if case["kind"] != "synthetic" or not e["parsed"]:
            continue
        for cid, actions in e["parsed"]["predictions"].items():
            coverage[e["model_id"]][actions["original"]] += 1
            for model in data["config"]["models"]:
                for variant in ("eliminated", "substituted"):
                    predicted = (actions["original"], actions[variant])
                    if "undetermined" in predicted:
                        continue
                    observed = []
                    for rep in range(repetitions):
                        a = parsed.get((case["id"], model["id"], "original", rep))
                        b = parsed.get((case["id"], model["id"], variant, rep))
                        if a is not None and b is not None:
                            observed.append((a[cid], b[cid]))
                    if len(observed) == repetitions and len(set(observed)) == 1 and predicted != observed[0]:
                        errors.append({"case": case["id"], "explainer": e["model_id"],
                            "executor": model["id"], "variant": variant, "input_id": cid,
                            "predicted": predicted, "observed": observed[0]})
    result = {"effects_against_elimination": [
        {"label_category": k[0], "executor": k[1], "variant": k[2], **v} for k, v in effects.items()],
        "stable_changed_inputs": changes, "stable_prediction_errors": errors,
        "original_prediction_coverage": {k: dict(v) for k, v in coverage.items()},
        "invalid_outputs": invalid, "wrong_handoffs": wrong_handoffs}
    (out / "diagnostics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"effects": result["effects_against_elimination"],
        "stable_prediction_errors": errors, "original_prediction_coverage": result["original_prediction_coverage"],
        "invalid_outputs": len(invalid), "wrong_handoffs": len(wrong_handoffs)}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    inspect(p.parse_args().out)
