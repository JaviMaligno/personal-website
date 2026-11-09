from datetime import date, timedelta
from typing import Any


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    candidates = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.endswith("@tidewater-klatring.no"):
            continue

        last_seen = account["last_seen_at"]
        if last_seen is None:
            continue

        due = last_seen + timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            closed_due = closed_at + timedelta(days=30)
            if closed_due < due:
                due = closed_due

        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            candidates.append((account, due, action))

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
            "approved_by": "Tordis Svenbjorn Dottir",
        }
        for account, due, action in candidates[:200]
    ]

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.endswith("@tidewater-klatring.no"):
            continue

        last_seen = account["last_seen_at"]
        if last_seen is None:
            continue

        due = last_seen + timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            closed_due = closed_at + timedelta(days=30)
            if closed_due < due:
                due = closed_due

        days_until_due = (due - today).days
        if (
            1 <= days_until_due <= 14
            and account["closed_by"] != "member"
        ):
            actions.append(
                {
                    "account_id": account["id"],
                    "email": email,
                    "action": "warn",
                    "due": due.isoformat(),
                    "approved_by": None,
                }
            )

    actions.sort(key=lambda action: action["account_id"])
    return actions