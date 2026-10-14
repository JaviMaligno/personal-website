from datetime import date, timedelta
from typing import Any


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    approver = "Tordis Svenbjorn Dottir"
    deletions: list[tuple[dict[str, Any], bool]] = []
    other_actions: list[dict[str, Any]] = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.lower().endswith("@tidewater-klatring.no"):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        if account["closed_at"] is not None:
            closed_due = account["closed_at"] + timedelta(days=30)
            due = min(due, closed_due)

        account_id = account["id"]
        if due <= today:
            if account["unpaid_invoices"]:
                other_actions.append({
                    "account_id": account_id,
                    "email": email,
                    "action": "anonymise",
                    "due": due.isoformat(),
                    "approved_by": approver,
                })
            else:
                deletions.append(({
                    "account_id": account_id,
                    "email": email,
                    "action": "delete",
                    "due": due.isoformat(),
                    "approved_by": approver,
                }, account["closed_at"] is not None))
        elif (
            due <= today + timedelta(days=14)
            and account["closed_by"] != "member"
        ):
            other_actions.append({
                "account_id": account_id,
                "email": email,
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    deletions.sort(key=lambda item: (not item[1], item[0]["account_id"]))
    actions = [action for action, _ in deletions[:200]]
    actions.extend(other_actions)
    actions.sort(key=lambda action: action["account_id"])
    return actions