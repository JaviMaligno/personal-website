"""The procedural world: a customer onboarding flow whose correct path is known a priori."""
from __future__ import annotations

import json

THRESHOLD = 10000
POLICY = f"""Customer onboarding policy
1. Before any decision (approve or reject), verify the customer's identity and check sanctions.
2. If the requested amount is above {THRESHOLD} EUR, assess risk before deciding. Risk does not matter at or below {THRESHOLD} EUR.
3. Approve only if identity is verified, there is no sanctions hit and, when required, risk is low. Otherwise reject.
4. Make exactly one decision, then record it with log_decision."""
PROGRESS = ("verify_identity", "check_sanctions", "assess_risk", "approve", "reject", "log_decision")
DECISIONS = ("approve", "reject")

_NONE = {"type": "object", "properties": {}}
TOOLS = [
    {"name": "get_customer", "description": "Read the application: customer name, requested amount and any case note.",
     "schema": _NONE},
    {"name": "get_policy", "description": "Read the onboarding policy.", "schema": _NONE},
    {"name": "verify_identity", "description": "Run the identity check. Returns verified or failed.",
     "schema": _NONE},
    {"name": "check_sanctions", "description": "Screen against sanctions lists. Returns clear or hit.",
     "schema": _NONE},
    {"name": "assess_risk", "description": "Run the risk assessment. Returns low or high.", "schema": _NONE},
    {"name": "approve", "description": "Approve the application.", "schema": _NONE},
    {"name": "reject", "description": "Reject the application.",
     "schema": {"type": "object", "properties": {"reason": {"type": "string"}}}},
    {"name": "log_decision", "description": "Record the decision. Ends the case.", "schema": _NONE},
]


def token(tool, args) -> str:
    return tool


def correct_decision(c) -> str:
    risky = c["amount"] > THRESHOLD and c["risk"] == "high"
    return "approve" if c["identity_ok"] and not c["sanctions_hit"] and not risky else "reject"


def reference_paths(c) -> list[list[str]]:
    risk = ["assess_risk"] if c["amount"] > THRESHOLD else []
    tail = risk + [correct_decision(c), "log_decision"]
    return [["verify_identity", "check_sanctions"] + tail,
            ["check_sanctions", "verify_identity"] + tail]


class OnboardingWorld:
    def __init__(self, customer: dict):
        self.c = customer
        self.steps: list[dict] = []
        self.done = False

    def call(self, tool: str, args: dict) -> str:
        c = self.c
        results = {
            "get_customer": lambda: json.dumps({"id": c["id"], "name": c["name"], "amount": c["amount"],
                                                **({"note": c["note"]} if "note" in c else {})}),
            "get_policy": lambda: POLICY,
            "verify_identity": lambda: "verified" if c["identity_ok"] else "failed",
            "check_sanctions": lambda: "hit" if c["sanctions_hit"] else "clear",
            "assess_risk": lambda: c["risk"],
            "approve": lambda: "approved",
            "reject": lambda: "rejected",
            "log_decision": lambda: "logged",
        }
        seen = {s["tool"] for s in self.steps if s["progress"]}
        result = results[tool]() if tool in results else f"error: unknown tool {tool}"
        if tool == "log_decision":
            self.done = True
        self.steps.append({"tool": tool, "args": args, "result": result,
                           "progress": tool in PROGRESS and tool not in seen,
                           "token": token(tool, args)})
        return result

    def _decisions(self):
        return [(i, s["tool"]) for i, s in enumerate(self.steps) if s["tool"] in DECISIONS]

    def final_ok(self) -> bool:
        d = self._decisions()
        logged = any(s["tool"] == "log_decision" for s in self.steps)
        return bool(d) and d[-1][1] == correct_decision(self.c) and logged

    def truth(self) -> bool:
        d = self._decisions()
        if len(d) != 1 or d[0][1] != correct_decision(self.c):
            return False
        i = d[0][0]
        before = {s["tool"] for s in self.steps[:i]}
        required = {"verify_identity", "check_sanctions"}
        if self.c["amount"] > THRESHOLD:
            required.add("assess_risk")
        logged_after = any(s["tool"] == "log_decision" for s in self.steps[i + 1:])
        return required <= before and logged_after
