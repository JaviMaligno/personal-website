from datetime import date, timedelta
from typing import Any

_DPO = "Þórdís Sveinbjörnsdóttir"
_DELETE_LIMIT = 200


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    candidates = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.endswith("@tidewater-klatring.no"):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            closed_due = closed_at + timedelta(days=30)
            due = min(due, closed_due)

        candidates.append((account, due, closed_at is not None))

    deletions = [
        item for item in candidates
        if item[1] <= today and not item[0]["unpaid_invoices"]
    ]
    deletions.sort(key=lambda item: (not item[2], item[1], item[0]["id"]))
    allowed_deletions = {id(item[0]) for item in deletions[:_DELETE_LIMIT]}

    actions = []
    for account, due, is_closed in candidates:
        if due <= today:
            if account["unpaid_invoices"]:
                action = "anonymise"
            elif id(account) in allowed_deletions:
                action = "delete"
            else:
                continue
            approved_by = _DPO
        elif today < due <= today + timedelta(days=14):
            if account["closed_by"] == "member":
                continue
            action = "warn"
            approved_by = None
        else:
            continue

        actions.append({
            "account_id": account["id"],
            "action": action,
            "due": due.isoformat(),
            "approved_by": approved_by,
            "email": account["email"],
        })

    actions.sort(key=lambda item: item["account_id"])
    return actions