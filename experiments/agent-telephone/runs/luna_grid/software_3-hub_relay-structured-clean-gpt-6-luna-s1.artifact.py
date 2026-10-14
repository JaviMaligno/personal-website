from datetime import date, timedelta
from typing import Any

DPO = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_LIMIT = 200


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    candidates = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.endswith(STAFF_DOMAIN):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))

        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            candidates.append((account, action, due))
        elif (
            due <= today + timedelta(days=14)
            and account["closed_by"] != "member"
        ):
            candidates.append((account, "warn", due))

    deletes = [item for item in candidates if item[1] == "delete"]
    deletes.sort(key=lambda item: (item[0]["closed_at"] is None, item[2], item[0]["id"]))
    kept_deletes = {id(item[0]) for item in deletes[:DELETE_LIMIT]}

    actions = []
    for account, action, due in candidates:
        if action == "delete" and id(account) not in kept_deletes:
            continue
        result = {
            "account_id": account["id"],
            "email": account["email"],
            "action": action,
            "due": due.isoformat(),
            "approved_by": DPO if action in ("delete", "anonymise") else None,
        }
        actions.append(result)

    return sorted(actions, key=lambda item: item["account_id"])