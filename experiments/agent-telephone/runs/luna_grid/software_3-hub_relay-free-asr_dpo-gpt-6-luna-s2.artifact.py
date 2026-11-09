from datetime import date, timedelta
from typing import Any


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    approver = "Tordis Svenbjorn Dottir"
    due_accounts = []
    warnings = []

    for account in accounts:
        email = account.get("email", "")
        if account.get("litigation_hold") or email.endswith("@tidewater-klatring.no"):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account.get("closed_at")
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))

        common = {"account_id": account["account_id"], "due": due.isoformat(), "email": email}
        if due <= today:
            if account.get("unpaid_invoices"):
                due_accounts.append({**common, "action": "anonymise", "approved_by": approver})
            else:
                due_accounts.append({
                    **common,
                    "action": "delete",
                    "approved_by": approver,
                    "_closed": closed_at is not None,
                })
        elif due <= today + timedelta(days=14) and account.get("closed_by") != "member":
            warnings.append({**common, "action": "warn", "approved_by": None})

    deletes = [a for a in due_accounts if a["action"] == "delete"]
    deletes.sort(key=lambda a: (not a["_closed"], a["account_id"]))
    kept_deletes = deletes[:200]
    actions = [a for a in due_accounts if a["action"] == "anonymise"] + kept_deletes + warnings

    for action in actions:
        action.pop("_closed", None)

    return sorted(actions, key=lambda action: action["account_id"])