from datetime import date, timedelta
from typing import Any


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    """Plan account purge actions for today."""
    candidates: list[tuple[dict[str, Any], date, str]] = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.endswith("@tidewater-klatring.no"):
            continue

        closed_at = account["closed_at"]
        due_date = account["last_seen_at"] + timedelta(days=730)
        if closed_at is not None:
            due_date = min(due_date, closed_at + timedelta(days=30))

        account_id = account["id"]
        if due_date <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            candidates.append((account, due_date, action))
        elif due_date <= today + timedelta(days=40) and account["closed_by"] != "member":
            candidates.append((account, due_date, "warn"))

    deletions = [
        item for item in candidates if item[2] == "delete"
    ]
    deletions.sort(
        key=lambda item: (item[0]["closed_at"] is None, item[0]["id"])
    )
    allowed_deletions = {id(item[0]) for item in deletions[:200]}

    actions = []
    for account, due_date, action in candidates:
        if action == "delete" and id(account) not in allowed_deletions:
            continue
        actions.append(
            {
                "account_id": account["id"],
                "email": account["email"],
                "action": action,
                "due": due_date.isoformat(),
                "approved_by": (
                    "Þórdís Sveinbjörnsdóttir" if action != "warn" else None
                ),
            }
        )

    actions.sort(key=lambda item: item["account_id"])
    return actions