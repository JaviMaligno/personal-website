from datetime import date, datetime, timedelta


def plan_purge(accounts, today):
    def as_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                return None
        return None

    candidates = []
    warnings = []

    for account in accounts:
        if account.get("litigation_hold"):
            continue

        email = account.get("email") or ""
        if account.get("is_staff") and email.endswith("@tidewater-klatring.no"):
            continue

        closed = account.get("is_closed", account.get("status") == "closed")
        due_dates = []
        last_seen = as_date(account.get("last_seen_at"))
        if last_seen:
            due_dates.append(last_seen + timedelta(days=730))

        closed_at = as_date(account.get("closed_at"))
        if closed and closed_at:
            due_dates.append(closed_at + timedelta(days=30))

        if not due_dates:
            continue
        due = min(due_dates)

        if due <= today:
            unpaid = account.get("unpaid_invoices", account.get("has_unpaid_invoices", False))
            if isinstance(unpaid, (list, tuple, set, dict)):
                unpaid = bool(unpaid)
            action = "anonymise" if unpaid else "delete"
            candidates.append((not closed, due, str(account.get("account_id", "")), account, action))
        elif (
            due <= today + timedelta(days=40)
            and not account.get("closed_by_member", account.get("closure_initiated_by") == "member")
        ):
            warnings.append((account, due, "warn"))

    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    actions = [
        {
            "account_id": account.get("account_id"),
            "action": action,
            "due": due.isoformat(),
            "approved_by": "DPO Þórdís Sveinbjörnsdóttir",
        }
        for _, due, _, account, action in candidates[:200]
    ]
    actions.extend(
        {
            "account_id": account.get("account_id"),
            "action": action,
            "due": due.isoformat(),
            "approved_by": None,
        }
        for account, due, action in warnings
    )
    actions.sort(key=lambda item: (str(item["account_id"]), item["action"], item["due"]))
    return actions