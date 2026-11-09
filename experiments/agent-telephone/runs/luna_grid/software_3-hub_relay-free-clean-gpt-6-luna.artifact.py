from datetime import date, datetime, timedelta


def plan_purge(accounts, today):
    """Return purge actions for account mappings."""
    if isinstance(today, datetime):
        today = today.date()
    elif isinstance(today, str):
        today = date.fromisoformat(today)

    dpo = "DPO Þórdís Sveinbjörnsdóttir"
    candidates = []
    warnings = []

    def as_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(value)

    for account in accounts:
        email = str(account.get("email", ""))
        if account.get("litigation_hold") or email.lower().endswith(
            "@tidewater-klatring.no"
        ):
            continue

        last_seen = account.get("last_seen_at")
        if last_seen is None:
            continue

        due = as_date(last_seen) + timedelta(days=730)
        closed_at = account.get("closed_at")
        if closed_at is not None:
            due = min(due, as_date(closed_at) + timedelta(days=30))

        action = {
            "account_id": account["account_id"],
            "action": "",
            "due": due.isoformat(),
            "approved_by": None,
        }

        if due <= today:
            if "unpaid_invoices" in account:
                action["action"] = "anonymise"
                action["approved_by"] = dpo
                candidates.append((None, action))
            else:
                action["action"] = "delete"
                action["approved_by"] = dpo
                candidates.append((closed_at is not None, action))
        elif due <= today + timedelta(days=14) and closed_at is None:
            action["action"] = "warn"
            warnings.append(action)

    deletions = [item for item in candidates if item[0] is not None]
    other_due = [item[1] for item in candidates if item[0] is None]
    deletions.sort(
        key=lambda item: (
            not item[0],
            item[1]["due"],
            str(item[1]["account_id"]),
        )
    )

    actions = other_due + [item[1] for item in deletions[:200]] + warnings
    actions.sort(key=lambda item: (str(item["account_id"]), item["action"]))
    return actions