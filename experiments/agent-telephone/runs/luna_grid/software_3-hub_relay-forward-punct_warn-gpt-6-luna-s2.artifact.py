from datetime import date, timedelta
from typing import Any

_DPO = "Þórdís Sveinbjörnsdóttir"


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    candidates: list[tuple[dict[str, Any], date, bool, str]] = []
    warnings: list[dict[str, Any]] = []

    for account in accounts:
        if account["litigation_hold"]:
            continue
        email = account["email"]
        if email.lower().endswith("@tidewater-klatring.no"):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account["closed_at"]
        is_closed = closed_at is not None
        if is_closed:
            due = min(due, closed_at + timedelta(days=30))

        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            candidates.append((account, due, is_closed, action))
        elif (
            due <= today + timedelta(days=14)
            and account["closed_by"] != "member"
        ):
            warnings.append(
                {
                    "account_id": account["id"],
                    "action": "warn",
                    "due": due.isoformat(),
                    "approved_by": None,
                    "email": email,
                }
            )

    deletions = [item for item in candidates if item[3] == "delete"]
    deletions.sort(key=lambda item: (not item[2], item[1], item[0]["id"]))
    allowed_deletions = {id(item[0]) for item in deletions[:200]}

    actions = warnings
    for account, due, _, action in candidates:
        if action == "delete" and id(account) not in allowed_deletions:
            continue
        actions.append(
            {
                "account_id": account["id"],
                "action": action,
                "due": due.isoformat(),
                "approved_by": _DPO,
                "email": account["email"],
            }
        )

    return sorted(actions, key=lambda action: action["account_id"])