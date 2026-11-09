from datetime import date, timedelta
from typing import Any

DPO = "Þórdís Sveinbjörnsdóttir"
DELETE_LIMIT = 200
WARNING_WINDOW = timedelta(days=40)


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    due_accounts = []
    warnings = []

    for account in accounts:
        if account["litigation_hold"] or account["email"].endswith("@tidewater-klatring.no"):
            continue

        due_date = account["last_seen_at"] + timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            due_date = min(due_date, closed_at + timedelta(days=30))

        if due_date <= today:
            if account["unpaid_invoices"]:
                due_accounts.append((account, due_date, "anonymise"))
            else:
                due_accounts.append((account, due_date, "delete"))
        elif (
            today < due_date <= today + WARNING_WINDOW
            and account["closed_by"] != "member"
        ):
            warnings.append((account, due_date, "warn"))

    deletes = [item for item in due_accounts if item[2] == "delete"]
    deletes.sort(
        key=lambda item: (
            item[0]["closed_at"] is None,
            item[1],
            item[0]["id"],
        )
    )
    selected_deletes = deletes[:DELETE_LIMIT]
    actions = [
        {
            "account_id": account["id"],
            "action": action,
            "due": due_date.isoformat(),
            "approved_by": DPO,
        }
        for account, due_date, action in due_accounts
        if action == "anonymise"
    ]
    actions.extend(
        {
            "account_id": account["id"],
            "action": "delete",
            "due": due_date.isoformat(),
            "approved_by": DPO,
        }
        for account, due_date, _ in selected_deletes
    )
    actions.extend(
        {
            "account_id": account["id"],
            "action": "warn",
            "due": due_date.isoformat(),
            "approved_by": None,
        }
        for account, due_date, _ in warnings
    )
    actions.sort(key=lambda action: action["account_id"])
    return actions