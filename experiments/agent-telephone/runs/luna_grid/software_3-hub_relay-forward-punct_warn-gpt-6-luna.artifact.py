from datetime import date, timedelta
from typing import Any

DPO = "Þórdís Sveinbjörnsdóttir"
DELETE_CAP = 200


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    actions = []
    deletions = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.lower().endswith(
            "@tidewater-klatring.no"
        ):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))

        if due <= today:
            if account["unpaid_invoices"]:
                actions.append({
                    "account_id": account["id"],
                    "email": email,
                    "action": "anonymise",
                    "due": due.isoformat(),
                    "approved_by": DPO,
                })
            else:
                deletions.append((account, due))
        elif (
            due <= today + timedelta(days=14)
            and account["closed_by"] != "member"
        ):
            actions.append({
                "account_id": account["id"],
                "email": email,
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    deletions.sort(
        key=lambda item: (
            item[0]["closed_at"] is None,
            str(item[0]["id"]),
        )
    )
    for account, due in deletions[:DELETE_CAP]:
        actions.append({
            "account_id": account["id"],
            "email": account["email"],
            "action": "delete",
            "due": due.isoformat(),
            "approved_by": DPO,
        })

    actions.sort(key=lambda action: str(action["account_id"]))
    return actions