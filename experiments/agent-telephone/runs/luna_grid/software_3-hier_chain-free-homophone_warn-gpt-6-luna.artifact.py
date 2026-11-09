from collections.abc import Mapping
from datetime import date, datetime, timedelta, timezone
from typing import Any


def plan_purge(accounts, today):
    """Plan account warnings and purge actions.

    Date values must all be dates or all be datetimes. Datetimes are converted
    to dates in UTC; naive datetimes are treated as UTC. Calendar-day arithmetic
    is used. ``unpaid_invoices`` is an optional boolean, defaulting to False.
    ``closed_by_member`` is an optional boolean used only to suppress warnings;
    when absent, no member closure is inferred from ``closed_at``.
    """
    def normalize(value):
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).date() if value.tzinfo else value.replace(
                tzinfo=timezone.utc
            ).date()
        if isinstance(value, date):
            return value
        raise TypeError("date inputs must be dates or datetimes")

    if not isinstance(today, (date, datetime)):
        raise TypeError("today must be a date or datetime")
    input_kind = datetime if isinstance(today, datetime) else date
    today_date = normalize(today)
    candidates = []
    warnings = []
    seen = set()

    for account in accounts:
        if not isinstance(account, Mapping):
            raise TypeError("each account must be a mapping")
        account_id = account["account_id"]
        if account_id is None or account_id in seen:
            raise ValueError("account_id values must be unique and non-null")
        seen.add(account_id)

        last_seen = account["last_seen_at"]
        closed_at = account.get("closed_at")
        for value in (last_seen, closed_at):
            if value is not None:
                if not isinstance(value, (date, datetime)) or (
                    datetime if isinstance(value, datetime) else date
                ) is not input_kind:
                    raise TypeError("date inputs must be valid and consistently dates or datetimes")

        if account.get("litigation_hold", False):
            continue
        email = account.get("email")
        if isinstance(email, str) and email.lower().endswith("@tidewater-klatring.no"):
            continue

        due = normalize(last_seen) + timedelta(days=730)
        if closed_at is not None:
            due = min(due, normalize(closed_at) + timedelta(days=30))

        if due <= today_date:
            candidates.append((closed_at is not None, due, account_id, account))
        elif (
            today_date < due <= today_date + timedelta(days=40)
            and not account.get("closed_by_member", False)
        ):
            warnings.append({
                "account_id": account_id,
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    try:
        candidates.sort(key=lambda item: (not item[0], item[1], item[2]))
        warnings.sort(key=lambda action: action["account_id"])
    except TypeError as exc:
        raise TypeError("account_id values must be mutually comparable") from exc

    actions = []
    for _, due, account_id, account in candidates[:200]:
        actions.append({
            "account_id": account_id,
            "action": "anonymise" if account.get("unpaid_invoices", False) else "delete",
            "due": due.isoformat(),
            "approved_by": "DPO Þórdís Sveinbjörnsdóttir",
        })
    actions.extend(warnings)
    try:
        actions.sort(key=lambda action: action["account_id"])
    except TypeError as exc:
        raise TypeError("account_id values must be mutually comparable") from exc
    return actions