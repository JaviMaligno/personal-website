from datetime import date, timedelta


def plan_purge(accounts, today):
    """Plan account actions due today or within the next 40 days."""
    candidates = []
    warnings = []

    for account in accounts:
        email = account.get("email", "")
        if account.get("litigation_hold") or email.lower().endswith(
            "@tidewater-klatring.no"
        ):
            continue

        inactivity_due = (
            account["last_seen_at"] + timedelta(days=730)
            if account.get("last_seen_at") is not None
            else None
        )
        closed_due = (
            account["closed_at"] + timedelta(days=30)
            if account.get("closed_at") is not None
            else None
        )
        dates = [d for d in (inactivity_due, closed_due) if d is not None]
        if not dates:
            continue

        due = min(dates)
        selected_closed = closed_due == due
        unpaid = bool(account.get("unpaid_invoices"))

        if due <= today:
            action = "anonymise" if unpaid else "delete"
            candidates.append((account, due, action, selected_closed))
        elif (
            due <= today + timedelta(days=40)
            and account.get("closed_by") != "member"
        ):
            warnings.append((account, due))

    deletions = sorted(
        (item for item in candidates if item[2] == "delete"),
        key=lambda item: (not item[3], item[1], item[0]["account_id"]),
    )[:200]
    anonymisations = [item for item in candidates if item[2] == "anonymise"]

    actions = [
        {
            "account_id": account["account_id"],
            "action": action,
            "due": due.isoformat(),
            "approved_by": "Þórdís Sveinbjörnsdóttir",
            "email": account.get("email"),
        }
        for account, due, action, _ in deletions + anonymisations
    ]
    actions.extend(
        {
            "account_id": account["account_id"],
            "action": "warn",
            "due": due.isoformat(),
            "approved_by": None,
            "email": account.get("email"),
        }
        for account, due in warnings
    )
    return sorted(actions, key=lambda action: action["account_id"])