from datetime import date, datetime, timedelta

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_LIMIT = 200


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def plan_purge(accounts, today):
    today = _as_date(today)
    candidates = []

    for account in accounts:
        email = account.get("email", "")
        if account.get("litigation_hold") or email.lower().endswith(STAFF_DOMAIN):
            continue

        last_seen = _as_date(account["last_seen_at"])
        due = last_seen + timedelta(days=730)
        closed_at = account.get("closed_at")
        if closed_at:
            due = min(due, _as_date(closed_at) + timedelta(days=30))

        unpaid = bool(account.get("unpaid_invoices"))
        if due <= today:
            candidates.append((account, due, unpaid))
        elif (
            not account.get("closed_by_member")
            and 0 < (due - today).days <= 14
        ):
            candidates.append((account, due, unpaid))

    deletions = [
        item for item in candidates if item[1] <= today and not item[2]
    ]
    deletions.sort(
        key=lambda item: (
            item[0].get("closed_at") is None,
            item[1],
            str(item[0]["account_id"]),
        )
    )
    allowed_deletions = {id(item[0]) for item in deletions[:DELETE_LIMIT]}

    actions = []
    for account, due, unpaid in candidates:
        if due <= today:
            if unpaid:
                action, approved_by = "anonymise", APPROVER
            elif id(account) in allowed_deletions:
                action, approved_by = "delete", APPROVER
            else:
                continue
        else:
            action, approved_by = "warn", None

        actions.append(
            {
                "account_id": account["account_id"],
                "action": action,
                "due": due.isoformat(),
                "approved_by": approved_by,
            }
        )

    actions.sort(key=lambda item: str(item["account_id"]))
    return actions