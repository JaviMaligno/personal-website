from datetime import date, timedelta
from typing import Any


DPO = "Þórdís Sveinbjörnsdóttir"
DELETE_LIMIT = 200
WARNING_WINDOW_DAYS = 40


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    candidates: list[tuple[dict[str, Any], date, str]] = []

    for account in accounts:
        if account["litigation_hold"]:
            continue
        if account["email"].lower().endswith("@tidewater-klatring.no"):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account.get("closed_at")
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))

        action = "anonymise" if account["unpaid_invoices"] else "delete"
        candidates.append((account, due, action))

    deletions = [
        item for item in candidates
        if item[2] == "delete" and item[1] <= today
    ]
    deletions.sort(
        key=lambda item: (
            item[0].get("closed_at") is None,
            item[0]["id"],
        )
    )
    selected_deletions = {id(item[0]) for item in deletions[:DELETE_LIMIT]}

    actions: list[dict[str, Any]] = []
    for account, due, action in candidates:
        if due <= today:
            if action == "delete" and id(account) not in selected_deletions:
                continue
            actions.append({
                "account_id": account["id"],
                "action": action,
                "due": due.isoformat(),
                "approved_by": DPO,
            })
        elif (
            due <= today + timedelta(days=WARNING_WINDOW_DAYS)
            and account.get("closed_by") != "member"
        ):
            actions.append({
                "account_id": account["id"],
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    actions.sort(key=lambda item: item["account_id"])
    return actions