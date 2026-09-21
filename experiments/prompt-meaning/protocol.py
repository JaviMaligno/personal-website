"""Prompts, strict output validation and exact text interventions."""
from __future__ import annotations

import json
import random

from bank import ACTIONS, brief, digest, validate_input


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json(text):
    # Accept a single code fence, not arbitrary prose followed by guessed JSON.
    text = text.strip()
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    return json.loads(text, object_pairs_hook=object_pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def variants(text, entry, task):
    term, clause, replacement = (entry[k] for k in ("term", "clause", "replacement"))
    if not all(isinstance(x, str) and x.strip() for x in (term, clause, replacement)):
        raise ValueError("Eligible cases require a term, exact clause and replacement")
    if text.count(clause) != 1 or clause.count(term) != 1 or text.count(term) != 1:
        raise ValueError("Select one unambiguous occurrence; record other cases as excluded")
    if term.casefold() in brief(task).casefold():
        raise ValueError("Term already occurs in the original brief")
    if replacement == term or replacement in text:
        raise ValueError("Replacement must be distinct and absent from original")
    refs = entry.get("rule_ids", [])
    if not isinstance(refs, list) or len(set(refs)) != len(refs) or any(
            r not in task["rules"] for r in refs):
        raise ValueError("Unknown or repeated reference rule")
    result = {"original": text, "eliminated": text.replace(clause, "", 1),
              "substituted": text.replace(term, replacement, 1)}
    if refs:
        explicit = " ".join(task["rules"][r] for r in task["rules"] if r in refs)
        result["explicit"] = text.replace(clause, explicit, 1)
    elif not entry.get("explicit_na_reason", "").strip():
        raise ValueError("Explain why no original requirement maps to this clause")
    if not result["eliminated"].strip():
        raise ValueError("Elimination removes the whole prompt")
    return result


def slots(case, model_id):
    names = list(case["variants"])
    random.Random(digest([case["id"], model_id])).shuffle(names)
    return dict(zip("ABCD", names))


def explain_prompt(case, slot_map):
    task = case["task"]
    shown = {slot: case["variants"][name] for slot, name in slot_map.items()}
    inputs = [{"case_id": c["id"], "input": c["input"]} for c in task["cases"]]
    max_probes = 0 if case["kind"] != "natural" else 3
    return ("Assess these alternative agent instructions. No executions have been observed.\n"
            f"Original assignment:\n{brief(task)}\n"
            f"Alternative instructions:\n{json.dumps(shown, ensure_ascii=False)}\n"
            f"Expression to interpret: {json.dumps(case['term'])}\n"
            f"Inputs:\n{json.dumps(inputs, ensure_ascii=False)}\n"
            "Explain the expression and cite the words supporting your interpretation. "
            "Predict the exact action under EACH alternative for EACH input. "
            "Identical predictions, redundancy and uncertainty are valid findings. "
            "Use 'undetermined' when a decision cannot be inferred. Do not invent a difference. "
            f"Optionally propose at most {max_probes} additional valid inputs where you expect "
            "different actions, with predictions for every alternative.\n"
            "Return a single JSON object with exactly these keys:\n"
            '{"meaning":"...","evidence":"...","comparison":"...",'
            '"predictions":[{"case_id":"c01","actions":{"A":"allow","B":"undetermined"}}],'
            '"probes":[{"input":{},"actions":{"A":"allow","B":"deny"},"reason":"..."}]}\n'
            f"Use these actual alternative keys in every actions object: {list(slot_map)}. "
            "Actions: allow, deny, review, undetermined. Include every listed case exactly once.")


def action_map(value, keys, abstain=False):
    allowed = set(ACTIONS) | ({"undetermined"} if abstain else set())
    if (not isinstance(value, dict) or set(value) != set(keys)
            or any(not isinstance(a, str) or a not in allowed for a in value.values())):
        raise ValueError("Actions have invalid labels or missing/extra IDs")
    return value


def parse_explanation(text, case, slot_map):
    data = parse_json(text)
    keys = {"meaning", "evidence", "comparison", "predictions", "probes"}
    if not isinstance(data, dict) or set(data) != keys:
        raise ValueError("Explanation schema mismatch")
    if any(not isinstance(data[k], str) for k in ("meaning", "evidence", "comparison")):
        raise ValueError("Explanation prose must be strings")
    if not isinstance(data["predictions"], list) or not isinstance(data["probes"], list):
        raise ValueError("Predictions/probes must be arrays")
    predictions = {}
    for row in data["predictions"]:
        if not isinstance(row, dict) or set(row) != {"case_id", "actions"}:
            raise ValueError("Prediction schema mismatch")
        cid = row["case_id"]
        if not isinstance(cid, str) or cid in predictions:
            raise ValueError("Invalid or duplicate case ID")
        actions = action_map(row["actions"], slot_map, abstain=True)
        predictions[cid] = {slot_map[s]: a for s, a in actions.items()}
    if set(predictions) != {c["id"] for c in case["task"]["cases"]}:
        raise ValueError("Missing or extra predicted cases")
    if len(data["probes"]) > (3 if case["kind"] == "natural" else 0):
        raise ValueError("Too many probes")
    probes = []
    for probe in data["probes"]:
        if not isinstance(probe, dict) or set(probe) != {"input", "actions", "reason"}:
            raise ValueError("Probe schema mismatch")
        validate_input(case["task"], probe["input"])
        actions = action_map(probe["actions"], slot_map, abstain=True)
        if not isinstance(probe["reason"], str):
            raise ValueError("Probe reason must be a string")
        probes.append({**probe, "actions": {slot_map[s]: a for s, a in actions.items()}})
    return {**data, "predictions": predictions, "probes": probes}


def execute_prompt(case, variant, inputs):
    # No brief, rule list, gold labels, explanations, model identities or variant labels.
    return ("Follow the agent instructions below for independent input records. "
            "Actions are labels only; do not perform external actions.\n"
            f"Instructions:\n{case['variants'][variant]}\n"
            f"Field schema: {json.dumps(case['task']['schema'], sort_keys=True)}\n"
            f"Records: {json.dumps([{'case_id': c['id'], 'input': c['input']} for c in inputs])}\n"
            'Return only {"decisions":{"case_id":"action",...}} with every input ID exactly '
            "once. Each action must be allow, deny, or review.")


def parse_decisions(text, inputs):
    data = parse_json(text)
    if not isinstance(data, dict) or set(data) != {"decisions"}:
        raise ValueError("Decision schema mismatch")
    return action_map(data["decisions"], [c["id"] for c in inputs])
