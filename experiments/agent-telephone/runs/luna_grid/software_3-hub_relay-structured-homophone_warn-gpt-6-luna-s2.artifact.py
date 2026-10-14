from datetime import date, timedelta
from typing import Any

APPROVER = "DPO Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETION_CAP = 200


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    candidates = []
    warnings = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.endswith(STAFF_DOMAIN):
            continue

        last_seen = account["last_seen_at"]
        inactivity_due = last_seen + timedelta(days=730)
        closed_at = account["closed_at"]
        due = min(inactivity_due, closed_at + timedelta(days=30)) if closed_at else inactivity_due

        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            candidates.append((account, due, action))
        elif (
            due <= today + timedelta(days=40)
            and account["closed_by"] != "member"
        ):
            warnings.append((account, due))

    # Closed accounts take precedence when the destructive-action cap is reached.
    candidates.sort(
        key=lambda item: (
            item[0]["closed_at"] is None,
            item[0]["id"],
        )
    )
    actions = [
        {
            "account_id": account["id"],
            "email": account["email"],
            "action": action,
            "due": due.isoformat(),
            "approved_by": APPROVER,
        }
        for account, due, action in candidates[:DELETION_CAP]
    ]

    actions.extend(
        {
            "account_id": account["id"],
            "email": account["email"],
            "action": "warn",
            "due": due.isoformat(),
            "approved_by": None,
        }
        for account, due in warnings
    )
    actions.sort(key=lambda action: action["account_id"])
    return actions