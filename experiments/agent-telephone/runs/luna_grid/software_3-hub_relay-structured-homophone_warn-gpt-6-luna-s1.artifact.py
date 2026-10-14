from datetime import date, timedelta
from typing import Any


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    approver = "Þórdís Sveinbjörnsdóttir"
    candidates = []

    for account in accounts:
        if account["litigation_hold"] or account["email"].endswith("@tidewater-klatring.no"):
            continue

        inactivity_due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account["closed_at"]
        closed_due = closed_at + timedelta(days=30) if closed_at is not None else None
        is_closed_due_first = closed_due is not None and closed_due < inactivity_due
        due = closed_due if is_closed_due_first else inactivity_due
        action = "anonymise" if account["unpaid_invoices"] else "delete"

        if due <= today:
            candidates.append((account, due, action, is_closed_due_first))

    deletions = [
        item for item in candidates
        if item[2] == "delete"
    ]
    deletions.sort(key=lambda item: (not item[3], item[1], str(item[0]["id"])))
    selected_deletions = {id(item[0]) for item in deletions[:200]}

    actions = []
    for account, due, action, _ in candidates:
        if action == "anonymise" or id(account) in selected_deletions:
            actions.append({
                "account_id": account["id"],
                "action": action,
                "due": due.isoformat(),
                "approved_by": approver,
                "email": account["email"],
            })

    for account in accounts:
        if account["litigation_hold"] or account["email"].endswith("@tidewater-klatring.no"):
            continue

        inactivity_due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account["closed_at"]
        closed_due = closed_at + timedelta(days=30) if closed_at is not None else None
        due = min(inactivity_due, closed_due) if closed_due is not None else inactivity_due

        if today < due <= today + timedelta(days=40) and account["closed_by"] != "member":
            actions.append({
                "account_id": account["id"],
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
                "email": account["email"],
            })

    actions.sort(key=lambda item: str(item["account_id"]))
    return actions