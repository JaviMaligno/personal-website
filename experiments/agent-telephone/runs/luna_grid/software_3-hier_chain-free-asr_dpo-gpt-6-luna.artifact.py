from datetime import date, datetime, timedelta
from typing import Any

APPROVER = "Tordis Svenbjorn Dottir"
DELETE_LIMIT = 200
WARNING_DAYS = 14
STAFF_EMAIL_DOMAIN = "@tidewater-klatring.no"


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError("account dates must be date, datetime, or ISO date strings")


def _has_unpaid_invoices(account: dict[str, Any]) -> bool:
    invoices = account.get("unpaid_invoices", ())
    if isinstance(invoices, (list, tuple, set, dict)):
        return bool(invoices)
    return bool(invoices)


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    """Plan account actions.

    The warning window is (today, today + 14 days], including the endpoint.
    The 200-action cap applies only to deletes; anonymisations are uncapped.
    When selecting deletes, closed accounts come first, then account_id order.
    """
    candidates = []
    warnings = []

    for account in accounts:
        email = account.get("email", "")
        if account.get("litigation_hold") or email.endswith(STAFF_EMAIL_DOMAIN):
            continue

        last_seen = _as_date(account["last_seen_at"])
        closed_value = account.get("closed_at")
        closed_at = _as_date(closed_value) if closed_value else None

        due = last_seen + timedelta(days=730)
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))

        account_id = account["account_id"]
        if due <= today:
            action = "anonymise" if _has_unpaid_invoices(account) else "delete"
            candidates.append(
                (action, account_id, due, email, closed_at is not None)
            )
        elif (
            closed_at is None
            and today < due <= today + timedelta(days=WARNING_DAYS)
        ):
            warnings.append(
                {
                    "account_id": account_id,
                    "action": "warn",
                    "due": due.isoformat(),
                    "approved_by": None,
                    "email": email,
                }
            )

    deletions = [item for item in candidates if item[0] == "delete"]
    anonymisations = [item for item in candidates if item[0] == "anonymise"]
    deletions.sort(key=lambda item: (not item[4], item[1]))
    selected = anonymisations + deletions[:DELETE_LIMIT]

    actions = [
        {
            "account_id": account_id,
            "action": action,
            "due": due.isoformat(),
            "approved_by": APPROVER,
            "email": email,
        }
        for action, account_id, due, email, _ in selected
    ]
    actions.extend(warnings)
    actions.sort(key=lambda action: action["account_id"])
    return actions