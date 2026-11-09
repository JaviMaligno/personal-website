from datetime import date, timedelta
from typing import Any

DPO = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_CAP = 200
WARNING_WINDOW = timedelta(days=40)


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    candidates: list[tuple[dict[str, Any], date, bool]] = []

    for account in accounts:
        if account["litigation_hold"] or account["email"].endswith(STAFF_DOMAIN):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))

        if due <= today:
            candidates.append((account, due, closed_at is not None))
        elif (
            due <= today + WARNING_WINDOW
            and account["closed_by"] != "member"
        ):
            candidates.append((account, due, False))

    deletions = [
        item for item in candidates
        if item[1] <= today and not item[0]["unpaid_invoices"]
    ]
    deletions.sort(key=lambda item: (not item[2], item[1], item[0]["id"]))
    selected_deletions = {id(item[0]) for item in deletions[:DELETE_CAP]}

    actions = []
    for account, due, _closed in candidates:
        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            if action == "delete" and id(account) not in selected_deletions:
                continue
            approved_by = DPO
        else:
            action = "warn"
            approved_by = None

        actions.append(
            {
                "account_id": account["id"],
                "email": account["email"],
                "action": action,
                "due": due.isoformat(),
                "approved_by": approved_by,
            }
        )

    return sorted(actions, key=lambda action: action["account_id"])