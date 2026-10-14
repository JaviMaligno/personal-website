from datetime import date, timedelta
from typing import Any


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    """Plan account deletion, anonymisation, and warning actions for today."""
    eligible: list[tuple[dict[str, Any], date]] = []

    for account in accounts:
        if account["litigation_hold"] or account["email"].endswith(
            "@tidewater-klatring.no"
        ):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))
        eligible.append((account, due))

    actions: list[dict[str, Any]] = []
    deletes: list[tuple[dict[str, Any], date]] = []

    for account, due in eligible:
        if due <= today:
            if account["unpaid_invoices"]:
                actions.append(
                    {
                        "account_id": account["id"],
                        "email": account["email"],
                        "action": "anonymise",
                        "due": due.isoformat(),
                        "approved_by": "Tordis Svenbjorn Dottir",
                    }
                )
            else:
                deletes.append((account, due))
        elif due <= today + timedelta(days=14) and account["closed_by"] != "member":
            actions.append(
                {
                    "account_id": account["id"],
                    "email": account["email"],
                    "action": "warn",
                    "due": due.isoformat(),
                    "approved_by": None,
                }
            )

    deletes.sort(key=lambda item: (item[0]["closed_at"] is None, item[0]["id"]))
    for account, due in deletes[:200]:
        actions.append(
            {
                "account_id": account["id"],
                "email": account["email"],
                "action": "delete",
                "due": due.isoformat(),
                "approved_by": "Tordis Svenbjorn Dottir",
            }
        )

    actions.sort(key=lambda action: action["account_id"])
    return actions