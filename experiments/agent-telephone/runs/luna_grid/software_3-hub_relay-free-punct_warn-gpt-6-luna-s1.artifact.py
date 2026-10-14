from datetime import date, timedelta
from typing import Any


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    candidates = []

    for account in accounts:
        email = account["email"]
        if account.get("litigation_hold") or email.endswith("@tidewater-klatring.no"):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account.get("closed_at")
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))

        candidates.append((account, due))

    overdue = [(account, due) for account, due in candidates if due <= today]
    overdue.sort(
        key=lambda item: (
            item[0].get("closed_at") is None,
            item[0]["account_id"],
        )
    )

    actions = []
    for account, due in overdue[:200]:
        actions.append(
            {
                "account_id": account["account_id"],
                "action": "anonymise" if account.get("unpaid_invoices") else "delete",
                "due": due.isoformat(),
                "approved_by": "Þórdís Sveinbjörnsdóttir",
            }
        )

    warning_end = today + timedelta(days=14)
    for account, due in candidates:
        if today < due <= warning_end and account.get("closed_at") is None:
            actions.append(
                {
                    "account_id": account["account_id"],
                    "action": "warn",
                    "due": due.isoformat(),
                    "approved_by": None,
                }
            )

    actions.sort(key=lambda action: action["account_id"])
    return actions