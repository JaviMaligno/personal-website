from datetime import date, timedelta


def plan_purge(accounts, today):
    dpo = "Tordis Svenbjorn Dottir"
    eligible = [
        account
        for account in accounts
        if not account["litigation_hold"]
        and not account["email"].lower().endswith("@tidewater-klatring.no")
    ]

    due_dates = {}
    for account in eligible:
        due = account["last_seen_at"] + timedelta(days=730)
        if account["closed_at"] is not None:
            due = min(due, account["closed_at"] + timedelta(days=30))
        due_dates[account["id"]] = due

    deletions = [
        account
        for account in eligible
        if due_dates[account["id"]] <= today and not account["unpaid_invoices"]
    ]
    deletions.sort(
        key=lambda account: (
            account["closed_at"] is None,
            due_dates[account["id"]],
            account["id"],
        )
    )

    actions = []
    for account in eligible:
        due = due_dates[account["id"]]
        if due <= today and account["unpaid_invoices"]:
            actions.append({
                "account_id": account["id"],
                "action": "anonymise",
                "due": due.isoformat(),
                "approved_by": dpo,
            })

    for account in deletions[:200]:
        due = due_dates[account["id"]]
        actions.append({
            "account_id": account["id"],
            "action": "delete",
            "due": due.isoformat(),
            "approved_by": dpo,
        })

    for account in eligible:
        due = due_dates[account["id"]]
        if (
            today < due <= today + timedelta(days=14)
            and account["closed_by"] != "member"
        ):
            actions.append({
                "account_id": account["id"],
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    return sorted(actions, key=lambda action: action["account_id"])