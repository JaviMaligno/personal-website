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
    tasks = [make_task(f, 0, contexts[f][0]) for f in contexts]
    bank = {"version": 2, "language": "en", "tasks": tasks}
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
    return narrative(task)[0] + "\n" + narrative(task)[1]


def narrative(task):
    """Requirements expressed as a design conversation, without giving a decision ladder."""
    stories = {
        "access": (
            "We are building an assistant to route requests to share research data. The team "
            "wants routine sharing to proceed without a meeting, while distinguishing a request "
            "that must not proceed from one that needs someone to look at it. Consent and release "
            "timing are binding constraints: material under embargo cannot go out, and absence "
            "of consent also prevents release. Owner approval is a separate responsibility. "
            "Confidential work is often shared internally, and external collaborators routinely "
            "receive non-confidential material. Work out how these concerns should fit together. "
            "Describe a practical operating approach and the distinctions another agent would need.",
            "The project owner clarifies: confidential material going outside needs review, even "
            "when the owner has signed off. An internal destination does not itself require review. "
            "A missing owner sign-off needs review, not an automatic refusal. An embargo or lack "
            "of consent still means refusal, even when review would also be needed. When none "
            "of these obstacles applies, allow the request. Do not invent other criteria."),
        "expense": (
            "We are building an assistant for travel reimbursement. Routine claims should not "
            "wait for a person, but uncertain documentation must not be treated as proof of fraud. "
            "A confirmed fraudulent claim cannot proceed, nor can an amount above 500. We also "
            "need a way to route claims with missing receipts, unusual amounts or a currency "
            "mismatch without confusing investigation with rejection. Work out a practical "
            "operating approach and the distinctions another agent would need.",
            "The finance owner clarifies: missing receipt means review. Amounts above 100 need "
            "review, as does a currency mismatch. A value equal to either limit does not exceed "
            "it. Confirmed fraud or exceeding 500 still means refusal regardless of documentation. "
            "Otherwise the claim is allowed. Do not invent other criteria."),
        "release": (
            "We are building an assistant that decides whether a service deployment can proceed. "
            "Passing tests is not the same thing as having permission, and permission is not the "
            "same thing as having a recovery path. Some targets are protected. Some changes are "
            "irreversible. Routine reversible changes to unprotected targets should not need "
            "ceremonial approval or a restore exercise. A known vulnerability prevents release. "
            "Work out a practical operating approach and the distinctions another agent would need.",
            "The engineering owner clarifies: failing tests requires review. Protected targets "
            "need owner approval; without it, review. An irreversible change needs a tested "
            "restore procedure; without it, review. Approval cannot substitute for restore and "
            "restore cannot substitute for approval. A known vulnerability means refusal, even "
            "when other checks need review. Otherwise allow. Do not invent other criteria."),
        "retention": (
            "We are building an assistant to decide which old logs can be deleted. Age, continuing "
            "use and permission are different concerns. Keeping everything forever is not the "
            "goal, but age alone does not settle whether an artifact is safe to remove. A legal "
            "hold prevents deletion, and so does not having completed 30 days of retention. "
            "Work out a practical operating approach and the distinctions another agent would need.",
            "The operations owner clarifies: outstanding dependencies require review. Some records "
            "require approval, and those need review until approval arrives. If approval is not "
            "required, its absence is irrelevant. Exactly 30 days is old enough. A legal hold or "
            "insufficient age means refusal even if dependencies or approval also need review. "
            "When none of these obstacles applies, allow deletion. Do not invent other criteria."),
    }
    return stories[task["family"]]


def author_prompt(task, stage, history):
    first, update = narrative(task)
    if stage == "draft":
        return first + "\nThis is a simulation; take no external actions. Use at most 350 words."
    conversation = f"Initial request:\n{first}\nPrevious design response:\n{history[0]}"
    if stage == "revise":
        return conversation + "\nOwner update:\n" + update + (
            "\nRevise the approach to handle these interactions consistently. "
            "Use at most 350 words. This is a simulation; take no external actions.")
    return conversation + "\nOwner update:\n" + update + "\nRevised design response:\n" + history[1] + (
        "\nNow write a standalone operational prompt for another agent that will not see this "
        "discussion. It receives independent JSON records and returns allow, deny or review. "
        "These are simulation labels only. Preserve the agreed policy in at most 180 words. "
        "Return only the operational prompt, without commentary.\nInput field schema:\n"
        + json.dumps(task["schema"], sort_keys=True))


def synthetic_cases(tasks):
    """Undefined labels are experimental manipulations, never spontaneous findings."""
    terms = {
        "access": ("r3", "owner clearance closure", "velun index", "tavrel balance"),
        "expense": ("r3", "amount currency alignment", "navic alignment", "lomar concordance"),
        "release": ("r4", "recovery readiness gate", "tavrel balance", "velun index"),
        "retention": ("r3", "conditional approval closure", "lomar concordance", "navic alignment"),
    }
    cases = []
    for task in tasks:
        removed_rule, suggestive, opaque, replacement = terms[task["family"]]
        base = "Apply these conditions in order to each record; stop at the first match.\n" + "\n".join(
            rule for rid, rule in task["rules"].items() if rid != removed_rule)
        for category, term in (("suggestive", suggestive), ("opaque", opaque)):
            clause = f"Before issuing the final label, apply the {term}."
            prefix = clause + "\n"
            cases.append({"id": f"synthetic-{task['family']}-{category}", "kind": "synthetic",
                "label_category": category, "task": task, "term": term, "clause": clause,
                "omitted_rule": removed_rule,
                "benchmark_expected": {
                    "explicit": {x["id"]: x["expected"] for x in task["cases"]},
                    "eliminated": {x["id"]: partial_oracle(task, x["input"]) for x in task["cases"]}},
                "variants": {"original": prefix + base, "eliminated": base,
                    "substituted": prefix.replace(term, replacement) + base,
                    "explicit": "Apply these conditions in order to each record; stop at the first match.\n"
                                + "\n".join(task["rules"].values())}})
    return cases


def partial_oracle(task, x):
    validate_input(task, x)
    family, p = task["family"], task["parameters"]
    if family == "access":
        if x["embargoed"] or not x["consent"]:
            return "deny"
        if x["external"] and x["confidential"]:
            return "review"
    elif family == "expense":
        if x["fraud_confirmed"] or x["amount"] > p["hard_limit"]:
            return "deny"
        if not x["receipt"]:
            return "review"
    elif family == "release":
        if x["known_vulnerability"]:
            return "deny"
        if not x["tests_pass"] or (x["protected"] and not x["owner_approved"]):
            return "review"
    elif family == "retention":
        if x["legal_hold"] or x["age_days"] < p["retention_days"]:
            return "deny"
        if x["dependencies"]:
            return "review"
    return "allow"


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
