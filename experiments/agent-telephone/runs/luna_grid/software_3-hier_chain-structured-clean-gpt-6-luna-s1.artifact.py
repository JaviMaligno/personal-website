from datetime import date, timedelta
from typing import Any


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    approver = "Þórdís Sveinbjörnsdóttir"
    deletions: list[tuple[dict[str, Any], date]] = []
    actions: list[dict[str, Any]] = []

    for account in accounts:
        if account["litigation_hold"]:
            continue
        if account["email"].endswith("@tidewater-klatring.no"):
            continue

        due_dates = [account["last_seen_at"] + timedelta(days=730)]
        if account["closed_at"] is not None:
            due_dates.append(account["closed_at"] + timedelta(days=30))
        due = min(due_dates)

        if due <= today:
            if account["unpaid_invoices"]:
                actions.append({
                    "account_id": account["id"],
                    "action": "anonymise",
                    "due": due.isoformat(),
                    "approved_by": approver,
                })
            else:
                deletions.append((account, due))
        elif (due - today).days <= 14 and account["closed_by"] != "member":
            actions.append({
                "account_id": account["id"],
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    deletions.sort(key=lambda item: (
        item[0]["closed_at"] is None,
        item[0]["id"],
    ))
    for account, due in deletions[:200]:
        actions.append({
            "account_id": account["id"],
            "action": "delete",
            "due": due.isoformat(),
            "approved_by": approver,
        })

    actions.sort(key=lambda item: (item["account_id"], item["action"]))
    return actions