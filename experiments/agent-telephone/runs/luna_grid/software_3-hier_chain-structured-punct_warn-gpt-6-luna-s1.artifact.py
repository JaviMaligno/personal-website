from datetime import date, timedelta
from typing import Any

_APPROVED_BY = "Þórdís Sveinbjörnsdóttir"
_DELETION_CAP = 200
_WARNING_WINDOW = timedelta(days=14)


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    """Plan account purge, anonymisation, and warning actions."""
    due_deletions: list[tuple[bool, tuple[str, str], dict[str, Any]]] = []
    actions: list[tuple[tuple[str, str], dict[str, Any]]] = []
    warnings: list[tuple[tuple[str, str], dict[str, Any]]] = []

    def id_key(value: Any) -> tuple[str, str]:
        return (type(value).__name__, str(value))

    for account in accounts:
        email = account.get("email")
        if account.get("litigation_hold") or (
            isinstance(email, str) and email.endswith("@tidewater-klatring.no")
        ):
            continue

        inactivity_due = (
            account["last_seen_at"] + timedelta(days=730)
            if account.get("last_seen_at") is not None
            else None
        )
        closure_due = (
            account["closed_at"] + timedelta(days=30)
            if account.get("closed_at") is not None
            else None
        )

        closure_selected = closure_due is not None and (
            inactivity_due is None or closure_due < inactivity_due
        )
        due = closure_due if closure_selected else inactivity_due
        if due is None:
            continue

        account_id = account.get("id")
        key = id_key(account_id)

        if due <= today:
            action = "anonymise" if account.get("unpaid_invoices") else "delete"
            result = {
                "account_id": account_id,
                "action": action,
                "due": due.isoformat(),
                "approved_by": _APPROVED_BY,
                "email": email,
            }
            if action == "anonymise":
                actions.append((key, result))
            else:
                due_deletions.append((closure_selected, key, result))
        elif due <= today + _WARNING_WINDOW:
            closed_by = account.get("closed_by")
            identifies_member = (
                isinstance(closed_by, str) and closed_by.casefold() == "member"
            ) or (account_id is not None and closed_by == account_id)
            if not identifies_member:
                warnings.append(
                    (
                        key,
                        {
                            "account_id": account_id,
                            "action": "warn",
                            "due": due.isoformat(),
                            "approved_by": None,
                            "email": email,
                        },
                    )
                )

    due_deletions.sort(key=lambda item: (not item[0], item[1]))
    actions.extend(
        (key, action)
        for _, key, action in due_deletions[:_DELETION_CAP]
    )
    actions.extend(warnings)
    actions.sort(key=lambda item: item[0])
    return [action for _, action in actions]