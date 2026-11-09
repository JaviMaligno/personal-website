from datetime import date, timedelta
from typing import Any


_APPROVER = "DPO Þórdís Sveinbjörnsdóttir"
_STAFF_DOMAIN = "@tidewater-klatring.no"


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    """Plan due account actions and warnings."""
    actions: list[dict[str, Any]] = []
    deletions: list[tuple[bool, dict[str, Any]]] = []
    warnings: list[dict[str, Any]] = []

    for account in accounts:
        email = account.get("email", "")
        if account.get("litigation_hold") or (
            isinstance(email, str) and email.endswith(_STAFF_DOMAIN)
        ):
            continue

        inactivity_deadline = account["last_seen_at"] + timedelta(days=730)
        closed_at = account.get("closed_at")
        closed_deadline = (
            closed_at + timedelta(days=30) if closed_at is not None else None
        )
        uses_closed_deadline = (
            closed_deadline is not None and closed_deadline < inactivity_deadline
        )
        deadline = (
            closed_deadline if uses_closed_deadline else inactivity_deadline
        )

        if deadline <= today:
            action = "anonymise" if account.get("unpaid_invoices") else "delete"
            item = {
                "account_id": account["account_id"],
                "email": email,
                "action": action,
                "due": deadline.isoformat(),
                "approved_by": _APPROVER,
            }
            if action == "delete":
                deletions.append((closed_at is not None, item))
            else:
                actions.append(item)
        elif (
            deadline <= today + timedelta(days=40)
            and not account.get("closed_by_member", False)
            and not account.get("closed_by_self", False)
        ):
            warnings.append(
                {
                    "account_id": account["account_id"],
                    "email": email,
                    "action": "warn",
                    "due": deadline.isoformat(),
                    "approved_by": None,
                }
            )

    deletions.sort(key=lambda entry: (not entry[0], entry[1]["account_id"]))
    actions.extend(item for _, item in deletions[:200])
    actions.extend(warnings)
    actions.sort(key=lambda item: item["account_id"])
    return actions