from datetime import date, datetime, timedelta
from typing import Any, Iterable, Mapping


def _as_date(value: date | datetime | None) -> date | None:
    if value is None:
        return None
    return value.date() if isinstance(value, datetime) else value


def plan_purge(
    accounts: Iterable[Mapping[str, Any]], today: date | datetime
) -> list[dict[str, Any]]:
    today_date = _as_date(today)
    assert today_date is not None

    actions: list[dict[str, Any]] = []
    for account in accounts:
        if account.get("litigation_hold"):
            continue

        email = account.get("email")
        domain = email.rpartition("@")[2].lower() if isinstance(email, str) else ""
        if account.get("is_staff") and domain == "tidewater-klatring.no":
            continue

        candidates = []
        last_seen = _as_date(account.get("last_seen_at"))
        closed_at = _as_date(account.get("closed_at"))
        if last_seen is not None:
            candidates.append(last_seen + timedelta(days=730))
        if closed_at is not None:
            candidates.append(closed_at + timedelta(days=30))
        if not candidates:
            continue

        due = min(candidates)
        if due <= today_date:
            action = "anonymise" if account.get("has_unpaid_invoices") else "delete"
            approved_by = "Tordis Svenbjorn Dottir"
        elif (
            due <= today_date + timedelta(days=14)
            and account.get("closed_by") != "member"
        ):
            action = "warn"
            approved_by = None
        else:
            continue

        actions.append(
            {
                "account_id": account.get("account_id"),
                "action": action,
                "due": due.isoformat(),
                "approved_by": approved_by,
                "email": email,
            }
        )

    deletions = [item for item in actions if item["action"] == "delete"]
    if len(deletions) > 200:
        deletions.sort(
            key=lambda item: (
                _as_date(
                    next(
                        (
                            account.get("closed_at")
                            for account in accounts
                            if account.get("account_id") == item["account_id"]
                        ),
                        None,
                    )
                )
                is None,
                str(item["account_id"]),
            )
        )
        keep = {id(item) for item in deletions[:200]}
        actions = [
            item
            for item in actions
            if item["action"] != "delete" or id(item) in keep
        ]

    actions.sort(key=lambda item: str(item["account_id"]))
    return actions