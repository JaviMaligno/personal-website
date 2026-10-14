from datetime import date, timedelta
from typing import Any

APPROVER = "DPO Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_LIMIT = 200


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    due_accounts = []
    warning_actions = []

    for account in accounts:
        email = account.get("email", "")
        if account.get("litigation_hold") or email.endswith(STAFF_DOMAIN):
            continue

        last_seen = account.get("last_seen_at")
        deadlines = []
        if last_seen is not None:
            deadlines.append((last_seen + timedelta(days=730), False))

        closed_at = account.get("closed_at")
        if closed_at is not None:
            deadlines.append((closed_at + timedelta(days=30), True))

        if not deadlines:
            continue

        due, is_closed = min(deadlines, key=lambda item: item[0])
        if due <= today:
            due_accounts.append((account, due, is_closed))
        elif due <= today + timedelta(days=14) and account.get("closed_by") != "member":
            warning_actions.append({
                "account_id": account["account_id"],
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
                "email": email,
            })

    due_accounts.sort(key=lambda item: (not item[2], item[1], item[0]["account_id"]))
    actions = []
    deletion_count = 0

    for account, due, is_closed in due_accounts:
        action = "anonymise" if account.get("unpaid_invoices") else "delete"
        if action == "delete":
            if deletion_count >= DELETE_LIMIT:
                continue
            deletion_count += 1

        actions.append({
            "account_id": account["account_id"],
            "action": action,
            "due": due.isoformat(),
            "approved_by": APPROVER,
            "email": account.get("email", ""),
        })

    actions.extend(warning_actions)
    actions.sort(key=lambda item: item["account_id"])
    return actions