"""Four stipulated workflow policies, exhaustive core cases, frozen visible subset."""
import hashlib
import itertools
import json


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":")).encode()).hexdigest()


SPECS = [
    ("recovery", ["db_snapshot", "db_restore_tested", "external_writes", "compensation_tested"],
     "active_data_loss", "Recovery of a change with database and external effects.",
     "Deny if active_data_loss is true. Otherwise allow only if db_snapshot and "
     "db_restore_tested are both true AND either external_writes is false or "
     "compensation_tested is true. Otherwise review. A database restore alone does "
     "not establish recovery of external effects. All fields refer to this change.",
     {12, 13, 15}),
    ("approval", ["owner_signoff", "revision_matches", "nonsemantic_change", "scope_matches"],
     "prohibited_change", "Approval attached to a specific change and scope.",
     "Deny if prohibited_change is true. Otherwise allow only if owner_signoff and "
     "scope_matches are both true AND either revision_matches or nonsemantic_change "
     "is true. Otherwise review. A nonsemantic revision may reuse the sign-off, but "
     "never extends its scope. All fields refer to this change.", {11, 13, 15}),
    ("evidence", ["first_pass", "second_pass", "shared_source", "blind_recheck"],
     "known_contradiction", "Corroboration of a validation claim.",
     "Deny if known_contradiction is true. Otherwise allow if first_pass and "
     "second_pass are true and shared_source is false; also allow if blind_recheck "
     "is true and at least one of first_pass or second_pass is true. Otherwise "
     "review. blind_recheck means a successful independent blind remeasurement. "
     "Shared-source reports alone are insufficient; the recheck is a separate route.",
     {5, 7, 9, 11, 12, 13, 15}),
    ("retry", ["receipt_present", "receipt_matches", "key_valid", "operation_idempotent"],
     "nonretryable_failure", "Permission to retry a failed operation.",
     "Deny if nonretryable_failure is true. Otherwise allow if receipt_present and "
     "receipt_matches are both true OR if key_valid and operation_idempotent are "
     "both true. Otherwise review. A matching receipt confirms this exact operation "
     "was never applied, allowing a retry even for a non-idempotent operation. "
     "A key without idempotence or an unmatched receipt is insufficient.",
     {3, 7, 11, 12, 13, 14, 15}),
]


def oracle(task, x, simplified=False):
    if set(x) != set(task["schema"]) or any(type(v) is not bool for v in x.values()):
        raise ValueError("Invalid input")
    if x[task["block"]]:
        return "deny"
    a, b, c, d = [x[f] for f in task["fields"]]
    if simplified:
        allow = {"recovery": a, "approval": a, "evidence": a and b, "retry": a or c}[task["id"]]
    else:
        allow = {"recovery": a and b and (not c or d),
                 "approval": a and d and (b or c),
                 "evidence": (a and b and not c) or (d and (a or b)),
                 "retry": (a and b) or (c and d)}[task["id"]]
    return "allow" if allow else "review"


def build_bank():
    tasks = []
    for tid, fields, block, context, rules, truth in SPECS:
        task = dict(id=tid, fields=fields, block=block, context=context, rules=rules,
                    schema={f: "boolean" for f in fields + [block]})
        cases = []
        for i, bits in enumerate(itertools.product([False, True], repeat=4)):
            x = dict(zip(fields, bits)); x[block] = False
            expected = "allow" if i in truth else "review"
            assert oracle(task, x) == expected
            cases.append(dict(id=f"c{i:02}", input=x, expected=expected,
                              simplified=oracle(task, x, True)))
        visible = set()
        for action in ["allow", "review"]:
            eligible = [c["id"] for c in cases if c["expected"] == c["simplified"] == action]
            assert len(eligible) >= 2
            visible.update([eligible[0], eligible[-1]])
        for i in [0, 5, 10, 15]:
            x = {**cases[i]["input"], block: True}
            assert oracle(task, x) == "deny"
            cases.append(dict(id=f"b{i:02}", input=x, expected="deny", simplified="deny"))
        visible.update(["b00", "b15"])
        for c in cases:
            c["visible"] = c["id"] in visible
            c["separating"] = c["expected"] != c["simplified"]
            assert not (c["visible"] and c["separating"])
        task["cases"] = cases
        tasks.append(task)
    return tasks
