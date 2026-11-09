from datetime import date as _date, timedelta as _timedelta
from typing import Any as _Any

_DPO = "Þórdís Sveinbjörnsdóttir"
_STAFF_DOMAIN = "@tidewater-klatring.no"
_DELETE_CAP = 200


def plan_purge(accounts: list[dict[str, _Any]], today: _date) -> list[dict[str, _Any]]:
    candidates = []
    actions = []
    warning_end = today + _timedelta(days=14)

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.lower().endswith(_STAFF_DOMAIN):
            continue

        due = account["last_seen_at"] + _timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            due = min(due, closed_at + _timedelta(days=30))

        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            item = {
                "account_id": account["id"],
                "action": action,
                "due": due.isoformat(),
                "approved_by": _DPO,
            }
            if action == "delete":
                candidates.append((closed_at is not None, account["id"], item))
            else:
                actions.append(item)
        elif (
            due <= warning_end
            and not (closed_at is not None and account["closed_by"] == "member")
        ):
            actions.append({
                "account_id": account["id"],
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    candidates.sort(key=lambda candidate: (not candidate[0], candidate[1]))
    actions.extend(item for _, _, item in candidates[:_DELETE_CAP])
    actions.sort(key=lambda item: item["account_id"])
    return actions