from datetime import date, datetime, timedelta
from typing import Any, Iterable


APPROVED_BY = "Þórdís Sveinbjörnsdóttir"
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"
DELETE_LIMIT = 200


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def plan_purge(accounts: Iterable[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    """Plan account purge actions and warnings without modifying account data."""
    today_date = _as_date(today)
    if today_date is None:
        raise ValueError("today must be a date or ISO date string")

    deletes: list[tuple[bool, str, dict[str, Any]]] = []
    anonymisations: list[tuple[str, dict[str, Any]]] = []
    warnings: list[tuple[str, dict[str, Any]]] = []

    for account in accounts:
        if not isinstance(account, dict):
            continue

        account_id = account.get("account_id")
        if account_id is None or not isinstance(account_id, (str, int)):
            continue
        account_key = str(account_id)

        last_seen = _as_date(account.get("last_seen_at"))
        if last_seen is None:
            continue

        email = account.get("email")
        if isinstance(email, str) and email.casefold().endswith(STAFF_EMAIL_SUFFIX.casefold()):
            continue
        if account.get("litigation_hold"):
            continue

        due = last_seen + timedelta(days=730)
        closed_at = _as_date(account.get("closed_at"))
        if closed_at is not None:
            closed_due = closed_at + timedelta(days=30)
            if closed_due < due:
                due = closed_due

        if due <= today_date:
            action = {
                "account_id": account_id,
                "action": "anonymise" if account.get("unpaid_invoices") else "delete",
                "due": due.isoformat(),
                "approved_by": APPROVED_BY,
            }
            if account.get("unpaid_invoices"):
                anonymisations.append((account_key, action))
            else:
                deletes.append((closed_at is not None, account_key, action))
        elif today_date < due <= today_date + timedelta(days=14):
            closed_by = account.get("closed_by")
            closed_by_member = account.get("closed_by_member") or (
                isinstance(closed_by, str) and closed_by.casefold() == "member"
            )
            if not closed_by_member:
                warnings.append(
                    (
                        account_key,
                        {
                            "account_id": account_id,
                            "action": "warn",
                            "due": due.isoformat(),
                            "approved_by": None,
                        },
                    )
                )

    deletes.sort(key=lambda item: (not item[0], item[1]))
    selected = [item[2] for item in deletes[:DELETE_LIMIT]]
    selected.extend(action for _, action in anonymisations)
    selected.extend(action for _, action in warnings)
    selected.sort(key=lambda action: str(action["account_id"]))
    return selected
