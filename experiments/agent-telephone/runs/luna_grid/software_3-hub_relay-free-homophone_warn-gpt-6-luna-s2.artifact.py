from datetime import date, datetime, timedelta
from typing import Any, Iterable, Mapping

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def plan_purge(accounts: Iterable[Mapping[str, Any]], today: date) -> list[dict[str, Any]]:
    """Plan due account actions and warnings; deletion ties break by account ID."""
    today = _as_date(today)
    candidates = []

    for account in accounts:
        email = str(account.get("email") or "")
        if account.get("litigation_hold") or email.lower().endswith(STAFF_DOMAIN):
            continue

        last_seen = _as_date(account.get("last_seen_at"))
        closed = _as_date(account.get("closed_at"))
        due_dates = []
        if last_seen is not None:
            due_dates.append(last_seen + timedelta(days=730))
        if closed is not None:
            due_dates.append(closed + timedelta(days=30))
        if not due_dates:
            continue

        due = min(due_dates)
        unpaid = bool(account.get("unpaid_invoices"))
        action = "anonymise" if unpaid else "delete"
        candidates.append((str(account.get("account_id", "")), account, due, action, closed is not None))

    due_candidates = [item for item in candidates if item[2] <= today]
    deletions = sorted(
        (item for item in due_candidates if item[3] == "delete"),
        key=lambda item: (not item[4], item[0]),
    )
    allowed_deletions = {id(item) for item in deletions[:200]}

    actions = []
    for item in candidates:
        account_id, _, due, action, _ = item
        if due <= today:
            if action == "delete" and id(item) not in allowed_deletions:
                continue
            approved_by = APPROVER
        elif due <= today + timedelta(days=40):
            action = "warning"
            approved_by = None
        else:
            continue

        actions.append({
            "account_id": account_id,
            "action": action,
            "due": due.isoformat(),
            "approved_by": approved_by,
        })

    return sorted(actions, key=lambda item: item["account_id"])