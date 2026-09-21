"""Fixed synthetic policies and independently specified expected boundary cases.

No model creates the gold labels. These are four task families, not twenty
independent domains. All actions are labels; nothing is actually executed.
"""
from __future__ import annotations

import hashlib
import json

ACTIONS = ("allow", "deny", "review")
SCHEMAS = {
    "access": {"embargoed": "boolean", "consent": "boolean", "external": "boolean",
               "confidential": "boolean", "owner_approved": "boolean"},
    "expense": {"fraud_confirmed": "boolean", "amount": "nonnegative integer",
                "receipt": "boolean", "currency_matches": "boolean"},
    "release": {"known_vulnerability": "boolean", "tests_pass": "boolean",
                "protected": "boolean", "owner_approved": "boolean",
                "irreversible": "boolean", "restore_tested": "boolean"},
    "retention": {"legal_hold": "boolean", "age_days": "nonnegative integer",
                  "dependencies": "boolean", "approval_required": "boolean",
                  "approved": "boolean"},
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def validate_input(task, data):
    schema = SCHEMAS[task["family"]]
    if not isinstance(data, dict) or set(data) != set(schema):
        raise ValueError("Input fields do not match the task schema")
    for key, kind in schema.items():
        value = data[key]
        if kind == "boolean" and type(value) is not bool:
            raise ValueError(f"{key} must be a boolean")
        if kind == "nonnegative integer" and (type(value) is not int or value < 0):
            raise ValueError(f"{key} must be a nonnegative integer")


def oracle(task, x):
    validate_input(task, x)
    family, p = task["family"], task["parameters"]
    if family == "access":
        if x["embargoed"] or not x["consent"]:
            return "deny"
        if (x["external"] and x["confidential"]) or not x["owner_approved"]:
            return "review"
    elif family == "expense":
        if x["fraud_confirmed"] or x["amount"] > p["hard_limit"]:
            return "deny"
        if (not x["receipt"] or x["amount"] > p["review_limit"]
                or not x["currency_matches"]):
            return "review"
    elif family == "release":
        if x["known_vulnerability"]:
            return "deny"
        if (not x["tests_pass"] or (x["protected"] and not x["owner_approved"])
                or (x["irreversible"] and not x["restore_tested"])):
            return "review"
    elif family == "retention":
        if x["legal_hold"] or x["age_days"] < p["retention_days"]:
            return "deny"
        if x["dependencies"] or (x["approval_required"] and not x["approved"]):
            return "review"
    else:
        raise ValueError("Unknown family")
    return "allow"


def make_task(family, index, context):
    p = {"review_limit": 100 + index * 25, "hard_limit": 500 + index * 50,
         "retention_days": 30 + index * 15}
    if family == "access":
        rules = ["Deny if embargoed is true or consent is false.",
                 "Otherwise, review if external and confidential are both true.",
                 "Otherwise, review if owner_approved is false.", "Otherwise, allow."]
        base = dict(embargoed=False, consent=True, external=False,
                    confidential=False, owner_approved=True)
        cases = [({}, "allow"), ({"embargoed": True}, "deny"),
                 ({"consent": False}, "deny"), ({"external": True}, "allow"),
                 ({"confidential": True}, "allow"),
                 ({"external": True, "confidential": True}, "review"),
                 ({"owner_approved": False}, "review"),
                 ({"embargoed": True, "owner_approved": False}, "deny"),
                 ({"consent": False, "external": True, "confidential": True}, "deny"),
                 ({"confidential": True, "owner_approved": False}, "review"),
                 ({"external": True, "owner_approved": False}, "review"),
                 ({"embargoed": True, "consent": False}, "deny")]
    elif family == "expense":
        r, h = p["review_limit"], p["hard_limit"]
        rules = [f"Deny if fraud_confirmed is true or amount exceeds {h}.",
                 "Otherwise, review if receipt is false.",
                 f"Otherwise, review if amount exceeds {r} or currency_matches is false.",
                 "Otherwise, allow. Equality to a limit does not exceed it."]
        base = dict(fraud_confirmed=False, amount=0, receipt=True, currency_matches=True)
        cases = [({}, "allow"), ({"amount": r - 1}, "allow"),
                 ({"amount": r}, "allow"), ({"amount": r + 1}, "review"),
                 ({"amount": h}, "review"), ({"amount": h + 1}, "deny"),
                 ({"receipt": False}, "review"), ({"currency_matches": False}, "review"),
                 ({"fraud_confirmed": True}, "deny"),
                 ({"fraud_confirmed": True, "receipt": False}, "deny"),
                 ({"amount": h + 1, "currency_matches": False}, "deny"),
                 ({"amount": r, "receipt": False}, "review")]
    elif family == "release":
        rules = ["Deny if known_vulnerability is true.",
                 "Otherwise, review if tests_pass is false.",
                 "Otherwise, review if protected is true and owner_approved is false.",
                 "Otherwise, review if irreversible is true and restore_tested is false.",
                 "Otherwise, allow."]
        base = dict(known_vulnerability=False, tests_pass=True, protected=False,
                    owner_approved=False, irreversible=False, restore_tested=False)
        cases = [({}, "allow"), ({"known_vulnerability": True}, "deny"),
                 ({"tests_pass": False}, "review"), ({"protected": True}, "review"),
                 ({"protected": True, "owner_approved": True}, "allow"),
                 ({"irreversible": True}, "review"),
                 ({"irreversible": True, "restore_tested": True}, "allow"),
                 ({"known_vulnerability": True, "tests_pass": False}, "deny"),
                 ({"known_vulnerability": True, "protected": True}, "deny"),
                 ({"protected": True, "owner_approved": True, "tests_pass": False}, "review"),
                 ({"protected": True, "irreversible": True, "restore_tested": True}, "review"),
                 ({"owner_approved": True, "restore_tested": True}, "allow")]
    else:
        d = p["retention_days"]
        rules = [f"Deny if legal_hold is true or age_days is less than {d}.",
                 "Otherwise, review if dependencies is true.",
                 "Otherwise, review if approval_required is true and approved is false.",
                 "Otherwise, allow. Equality to the retention period is old enough."]
        base = dict(legal_hold=False, age_days=d, dependencies=False,
                    approval_required=False, approved=False)
        cases = [({}, "allow"), ({"age_days": 0}, "deny"),
                 ({"age_days": d - 1}, "deny"), ({"age_days": d + 1}, "allow"),
                 ({"legal_hold": True}, "deny"), ({"dependencies": True}, "review"),
                 ({"approval_required": True}, "review"),
                 ({"approval_required": True, "approved": True}, "allow"),
                 ({"legal_hold": True, "dependencies": True}, "deny"),
                 ({"age_days": d - 1, "approval_required": True}, "deny"),
                 ({"dependencies": True, "approved": True}, "review"),
                 ({"age_days": d + 1, "approved": True}, "allow")]
    return {"id": f"{family}-{index + 1:02}", "family": family,
            "context": context, "parameters": p, "schema": SCHEMAS[family],
            "rules": {f"r{i+1}": rule for i, rule in enumerate(rules)},
            "cases": [{"id": f"c{i+1:02}", "input": {**base, **patch}, "expected": expected}
                      for i, (patch, expected) in enumerate(cases)]}


def build_bank():
    contexts = {
        "access": ["research data sharing", "supplier document access", "press material release",
                   "partner report access", "archive disclosure"],
        "expense": ["travel reimbursement", "equipment reimbursement", "training reimbursement",
                    "conference reimbursement", "fieldwork reimbursement"],
        "release": ["service deployments", "database migration releases", "batch job releases",
                    "configuration rollouts", "integration releases"],
        "retention": ["log deletion", "archive deletion", "backup deletion",
                      "document deletion", "export deletion"],
    }
    tasks = [make_task(f, i, contexts[f][i]) for i in range(5) for f in contexts]
    bank = {"version": 1, "language": "en", "tasks": tasks}
    validate_bank(bank)
    return bank


def validate_bank(bank):
    if len({t["id"] for t in bank["tasks"]}) != len(bank["tasks"]):
        raise ValueError("Duplicate task ID")
    for task in bank["tasks"]:
        if len({c["id"] for c in task["cases"]}) != len(task["cases"]):
            raise ValueError("Duplicate case ID")
        for case in task["cases"]:
            if oracle(task, case["input"]) != case["expected"]:
                raise ValueError(f"Gold mismatch: {task['id']}/{case['id']}")


def brief(task):
    return (f"Write reusable instructions for an agent making decisions about {task['context']}. "
            "Return only the finished instructions. The agent will receive independent JSON "
            "records and must return one action per record: allow, deny, or review. "
            "These are labels in a simulation, not permission to perform any real action.\n"
            f"Input fields: {json.dumps(task['schema'], sort_keys=True)}\n"
            "Requirements, applied in the following priority order:\n"
            + "\n".join(task["rules"].values()))


def controls():
    """Handwritten sensitivity checks; never counted as spontaneous terminology."""
    task = make_task("access", 0, "control record routing")
    task["id"] = "control"
    task["cases"] = [
        {"id": "c01", "input": dict(embargoed=False, consent=True, external=False,
                                    confidential=False, owner_approved=True), "expected": "allow"},
        {"id": "c02", "input": dict(embargoed=True, consent=True, external=False,
                                    confidential=False, owner_approved=True), "expected": "deny"},
    ]
    task["rules"] = {"r1": "Deny if embargoed is true. Otherwise allow. Ignore all other fields."}
    clause = "Deny if embargoed is true."
    return [
        {"id": "control-positive", "kind": "positive", "task": task,
         "term": "embargoed", "clause": clause,
         "variants": {"original": clause + " Otherwise allow. Ignore all other fields.",
                      "eliminated": "Allow every record. Ignore all other fields."},
         "expected_by_variant": {"original": {"c01": "allow", "c02": "deny"},
                                 "eliminated": {"c01": "allow", "c02": "allow"}}},
        {"id": "control-redundant", "kind": "redundant", "task": task,
         "term": "embargoed", "clause": clause,
         "variants": {"original": "If embargoed is true, deny; otherwise allow. " + clause,
                      "eliminated": "If embargoed is true, deny; otherwise allow."},
         "expected_by_variant": {"original": {"c01": "allow", "c02": "deny"},
                                 "eliminated": {"c01": "allow", "c02": "deny"}}},
    ]
