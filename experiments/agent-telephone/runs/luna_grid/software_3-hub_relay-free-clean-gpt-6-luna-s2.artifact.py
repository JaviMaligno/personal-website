from datetime import date, timedelta

_APPROVED_BY = "DPO Þórdís Sveinbjörnsdóttir"
_STAFF_DOMAIN = "@tidewater-klatring.no"
_DELETE_LIMIT = 200


def plan_purge(accounts: list[dict], today: date) -> list[dict]:
    actions = []
    overdue = []

    for account in accounts:
        if account["litigation_hold"]:
            continue
        if account["email"].endswith(_STAFF_DOMAIN):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))

        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            item = {
                "account_id": account["account_id"],
                "action": action,
                "due": due.isoformat(),
                "approved_by": _APPROVED_BY,
            }
            if action == "delete":
                overdue.append((closed_at is not None, item))
            else:
                actions.append(item)
        elif (
            due <= today + timedelta(days=14)
            and not (
                closed_at is not None
                and account["closed_by"] == "member"
            )
        ):
            actions.append({
                "account_id": account["account_id"],
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    overdue.sort(key=lambda entry: (not entry[0], entry[1]["account_id"]))
    actions.extend(item for _, item in overdue[:_DELETE_LIMIT])
    actions.sort(key=lambda item: item["account_id"])
    return actions