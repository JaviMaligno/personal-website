from datetime import date, datetime, timedelta
from typing import Iterable


def plan_purge(accounts: Iterable[dict], today: date) -> list[dict]:
    if not isinstance(today, date) or isinstance(today, datetime):
        raise TypeError("today must be a datetime.date")

    candidates = []
    for index, account in enumerate(accounts):
        if not isinstance(account, dict):
            continue

        email = account.get("email")
        if isinstance(email, str) and email.lower().endswith("@tidewater-klatring.no"):
            continue
        if account.get("litigation_hold") is True:
            continue

        last_seen = account.get("last_seen_at")
        if not isinstance(last_seen, date) or isinstance(last_seen, datetime):
            continue

        closed_at = account.get("closed_at")
        if not isinstance(closed_at, date) or isinstance(closed_at, datetime):
            closed_at = None

        due = last_seen + timedelta(days=730)
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))

        account_id = account.get("account_id")
        approved_by = "Þórdís Sveinbjörnsdóttir"
        if due <= today:
            if "unpaid_invoices" in account:
                action = "anonymise"
            else:
                action = "delete"
            candidates.append(
                {
                    "account_id": account_id,
                    "action": action,
                    "due": due.isoformat(),
                    "approved_by": approved_by,
                    "_closed": closed_at is not None,
                    "_index": index,
                }
            )
        elif (
            account.get("closed_by_member") is not True
            and due <= today + timedelta(days=14)
        ):
            candidates.append(
                {
                    "account_id": account_id,
                    "action": "warning",
                    "due": due.isoformat(),
                    "approved_by": None,
                    "_closed": closed_at is not None,
                    "_index": index,
                }
            )

    deletes = [item for item in candidates if item["action"] == "delete"]
    if len(deletes) > 200:
        deletes.sort(
            key=lambda item: (
                not item["_closed"],
                type(item["account_id"]).__name__,
                repr(item["account_id"]),
                item["_index"],
            )
        )
        kept = {item["_index"] for item in deletes[:200]}
        candidates = [
            item
            for item in candidates
            if item["action"] != "delete" or item["_index"] in kept
        ]

    candidates.sort(
        key=lambda item: (
            type(item["account_id"]).__name__,
            repr(item["account_id"]),
            item["_index"],
        )
    )
    return [
        {key: item[key] for key in ("account_id", "action", "due", "approved_by")}
        for item in candidates
    ]