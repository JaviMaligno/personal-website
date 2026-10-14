from datetime import date, datetime, timedelta
from typing import Any, Iterable, Mapping


APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_LIMIT = 200


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _has_unpaid_invoices(value: Any) -> bool:
    return bool(value)


def plan_purge(accounts: Iterable[Mapping[str, Any]], today: date) -> list[dict[str, Any]]:
    """Plan account actions.

    The 200-action cap applies only to deletions; anonymisations do not consume
    it. Product clarification is needed to confirm this interpretation.
    """
    today = _as_date(today)
    due_records = []
    warnings = []

    for account in accounts:
        if account.get("litigation_hold"):
            continue

        email = str(account.get("email", ""))
        if account.get("is_staff") and email.lower().endswith(STAFF_DOMAIN):
            continue

        last_seen = _as_date(account["last_seen_at"])
        due = last_seen + timedelta(days=730)
        closed_at = account.get("closed_at")
        is_closed = closed_at is not None
        if is_closed:
            due = min(due, _as_date(closed_at) + timedelta(days=30))

        account_id = account["account_id"]
        if due <= today:
            action = "anonymise" if _has_unpaid_invoices(account.get("unpaid_invoices")) else "delete"
            due_records.append((account_id, action, due, is_closed))
        elif not is_closed and due <= today + timedelta(days=14):
            warnings.append({
                "account_id": account_id,
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    deletions = [record for record in due_records if record[1] == "delete"]
    deletions.sort(key=lambda record: (not record[3], str(record[0])))
    selected_deletions = {id(record) for record in deletions[:DELETE_LIMIT]}

    actions = []
    for record in due_records:
        account_id, action, due, _ = record
        if action == "delete" and id(record) not in selected_deletions:
            continue
        actions.append({
            "account_id": account_id,
            "action": action,
            "due": due.isoformat(),
            "approved_by": APPROVER,
        })

    actions.extend(warnings)
    actions.sort(key=lambda item: str(item["account_id"]))
    return actions