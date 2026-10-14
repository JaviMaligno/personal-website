from datetime import date, timedelta
from typing import Any


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    approver = "DPO Þórdís Sveinbjörnsdóttir"
    candidates = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.lower().endswith("@tidewater-klatring.no"):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        if account["closed_at"] is not None:
            closed_due = account["closed_at"] + timedelta(days=30)
            due = min(due, closed_due)

        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            candidates.append((account, action, due))
        elif (
            due <= today + timedelta(days=14)
            and account["closed_by"] != "member"
        ):
            candidates.append((account, "warn", due))

    deletions = [
        item for item in candidates if item[1] == "delete"
    ]
    deletions.sort(
        key=lambda item: (
            item[0]["closed_at"] is None,
            item[0]["id"],
        )
    )
    allowed_deletions = {item[0]["id"] for item in deletions[:200]}

    actions = []
    for account, action, due in candidates:
        if action == "delete" and account["id"] not in allowed_deletions:
            continue
        actions.append(
            {
                "account_id": account["id"],
                "email": account["email"],
                "action": action,
                "due": due.isoformat(),
                "approved_by": approver if action in ("delete", "anonymise") else None,
            }
        )

    return sorted(actions, key=lambda item: item["account_id"])