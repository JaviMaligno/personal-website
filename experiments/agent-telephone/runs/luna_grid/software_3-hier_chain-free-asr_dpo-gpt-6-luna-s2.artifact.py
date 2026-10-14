from datetime import date, datetime, timedelta
from typing import Iterable, Mapping, Any


_APPROVER = "Tordis Svenbjorn Dottir"
_STAFF_DOMAIN = "@tidewater-klatring.no"
_DELETE_LIMIT = 200


def _parse_date(value: Any, field: str) -> date:
    """Accept date/datetime objects or ISO-8601 strings; invalid values raise ValueError."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            try:
                return datetime.fromisoformat(value).date()
            except ValueError as exc:
                raise ValueError(f"{field} must be an ISO date or datetime") from exc
    raise ValueError(f"{field} must be a date, datetime, or ISO string")


def plan_purge(accounts: Iterable[Mapping[str, Any]], today: Any) -> list[dict]:
    """Plan account actions.

    ``today`` and non-missing date fields accept ``date``/``datetime`` objects or
    ISO-8601 strings. Datetimes are reduced to their calendar date. Invalid values
    raise ValueError. Missing or None ``closed_at`` means the account is not closed.
    Missing or None ``last_seen_at`` means there is no inactivity deadline; a
    closed account can still use its ``closed_at + 30 days`` deadline. If both
    dates are unavailable, the account gets no action. A member-initiated closure
    is indicated by ``closed_by`` equal to ``"member"`` (case-insensitive).
    """
    today_date = _parse_date(today, "today")
    candidates: list[tuple[Any, dict, bool, bool]] = []

    for account in accounts:
        account_id = account["id"]
        email = account.get("email")
        if account.get("litigation_hold") or (
            isinstance(email, str) and email.lower().endswith(_STAFF_DOMAIN)
        ):
            continue

        last_seen = account.get("last_seen_at")
        closed_at = account.get("closed_at")
        due_dates = []
        if last_seen is not None:
            due_dates.append(_parse_date(last_seen, "last_seen_at") + timedelta(days=730))
        if closed_at is not None:
            due_dates.append(_parse_date(closed_at, "closed_at") + timedelta(days=30))
        if not due_dates:
            continue

        due = min(due_dates)
        closed = closed_at is not None
        self_closed = str(account.get("closed_by", "")).lower() == "member"

        if due <= today_date:
            if account.get("unpaid_invoices"):
                action, approved_by = "anonymise", _APPROVER
            else:
                action, approved_by = "delete", _APPROVER
            result = {
                "account_id": account_id,
                "action": action,
                "due": due.isoformat(),
                "approved_by": approved_by,
            }
            candidates.append((account_id, result, closed, action == "delete"))
        elif 1 <= (due - today_date).days <= 14 and not self_closed:
            result = {
                "account_id": account_id,
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            }
            candidates.append((account_id, result, closed, False))

    deletes = sorted(
        (item for item in candidates if item[3]),
        key=lambda item: item[0],
    )
    retained_deletes = {
        id(item[1]) for item in sorted(
            deletes, key=lambda item: (not item[2], item[0])
        )[:_DELETE_LIMIT]
    }

    results = [
        result
        for _, result, _, is_delete in candidates
        if not is_delete or id(result) in retained_deletes
    ]
    results.sort(key=lambda result: (result["account_id"], result["action"]))
    return results