from datetime import date, timedelta
from typing import Any


_DPO = "Tordis Svenbjorn Dottir"
_DELETE_LIMIT = 200
_ACTION_ORDER = {"delete": 0, "anonymise": 1, "warn": 2}


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    """Return the purge actions due today, without modifying accounts."""
    candidates = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.endswith("@tidewater-klatring.no"):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        if account["closed_at"] is not None:
            due = min(due, account["closed_at"] + timedelta(days=30))

        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            candidates.append((account, due, action))

    deletions = [
        item for item in candidates if item[2] == "delete"
    ]
    deletions.sort(
        key=lambda item: (
            item[0]["closed_at"] is None,
            item[0]["id"],
            item[1],
            item[0]["email"],
        )
    )
    selected_deletions = {id(item[0]) for item in deletions[:_DELETE_LIMIT]}

    actions = []
    for account, due, action in candidates:
        if action == "delete" and id(account) not in selected_deletions:
            continue
        actions.append({
            "account_id": account["id"],
            "action": action,
            "due": due.isoformat(),
            "approved_by": _DPO,
            "email": account["email"],
        })

    warning_deadline = today + timedelta(days=14)
    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.endswith("@tidewater-klatring.no"):
            continue
        if account["closed_by"] == "member":
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        if account["closed_at"] is not None:
            due = min(due, account["closed_at"] + timedelta(days=30))
        if today < due <= warning_deadline:
            actions.append({
                "account_id": account["id"],
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
                "email": email,
            })

    actions.sort(key=lambda item: (item["account_id"], _ACTION_ORDER[item["action"]]))
    return actions