from datetime import date, datetime, timedelta
from typing import Any

APPROVER = "DPO Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETION_CAP = 200
WARNING_WINDOW_DAYS = 14


def _as_date(value: date | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def plan_purge(accounts: list[dict[str, Any]], today: date | str) -> list[dict[str, Any]]:
    current_date = _as_date(today)
    candidates: list[tuple[dict[str, Any], date, bool]] = []

    for account in accounts:
        email = account.get("email", "")
        if account.get("litigation_hold") or email.lower().endswith(STAFF_DOMAIN):
            continue

        last_seen = account.get("last_seen_at")
        if last_seen is None:
            continue

        due = _as_date(last_seen) + timedelta(days=730)
        is_closed = account.get("closed_at") is not None
        if is_closed:
            due = min(due, _as_date(account["closed_at"]) + timedelta(days=30))
        candidates.append((account, due, is_closed))

    deletions = sorted(
        (item for item in candidates if item[1] <= current_date),
        key=lambda item: (not item[2], str(item[0].get("account_id", ""))),
    )[:DELETION_CAP]

    actions: list[dict[str, Any]] = []
    for account, due, _ in deletions:
        actions.append(
            {
                "account_id": account.get("account_id"),
                "email": account.get("email"),
                "action": "anonymise" if account.get("unpaid_invoices") else "delete",
                "due": due.isoformat(),
                "approved_by": APPROVER,
            }
        )

    warning_end = current_date + timedelta(days=WARNING_WINDOW_DAYS)
    for account, due, _ in candidates:
        if (
            current_date < due <= warning_end
            and account.get("closed_by") != "member"
        ):
            actions.append(
                {
                    "account_id": account.get("account_id"),
                    "email": account.get("email"),
                    "action": "warn",
                    "due": due.isoformat(),
                }
            )

    return sorted(actions, key=lambda action: str(action["account_id"]))