from datetime import date, timedelta
from typing import Any


APPROVER = "DPO Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_CAP = 200


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    candidates: list[tuple[bool, dict[str, Any]]] = []
    actions: list[dict[str, Any]] = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.lower().endswith(STAFF_DOMAIN):
            continue

        closed = account["closed_at"] is not None or str(account["status"]).lower() == "closed"
        due = account["last_seen_at"] + timedelta(days=730)
        if closed and account["closed_at"] is not None:
            due = min(due, account["closed_at"] + timedelta(days=30))

        if due <= today:
            if account["unpaid_invoices"]:
                actions.append({
                    "account_id": account["id"],
                    "email": email,
                    "action": "anonymise",
                    "due": due,
                    "approved_by": APPROVER,
                })
            else:
                candidates.append((closed, {
                    "account_id": account["id"],
                    "email": email,
                    "action": "delete",
                    "due": due,
                    "approved_by": APPROVER,
                }))
        elif due <= today + timedelta(days=14) and account["closed_by"] != "member":
            actions.append({
                "account_id": account["id"],
                "email": email,
                "action": "warn",
                "due": due,
                "approved_by": None,
            })

    candidates.sort(key=lambda item: (not item[0], item[1]["account_id"], item[1]["due"]))
    actions.extend(action for _, action in candidates[:DELETE_CAP])
    actions.sort(key=lambda action: (action["account_id"], action["action"], action["due"]))
    return actions