from datetime import date, timedelta


def plan_purge(accounts: list[dict], today: date) -> list[dict]:
    """Plan account purge, anonymisation, and warning actions for today."""
    eligible = []
    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.endswith("@tidewater-klatring.no"):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))
        eligible.append((account, due))

    due_deletes = [
        (account, due)
        for account, due in eligible
        if due <= today and not account["unpaid_invoices"]
    ]
    due_deletes.sort(
        key=lambda item: (
            item[0]["closed_at"] is None,
            item[1],
            item[0]["id"],
        )
    )
    selected_delete_ids = {id(account) for account, _ in due_deletes[:200]}

    actions = []
    for account, due in eligible:
        if due <= today:
            if account["unpaid_invoices"]:
                action = "anonymise"
            elif id(account) in selected_delete_ids:
                action = "delete"
            else:
                continue
            approved_by = "Þórdís Sveinbjörnsdóttir"
        elif (
            due <= today + timedelta(days=14)
            and account["closed_by"] != "member"
        ):
            action = "warn"
            approved_by = None
        else:
            continue

        actions.append(
            {
                "account_id": account["id"],
                "email": account["email"],
                "action": action,
                "due": due.isoformat(),
                "approved_by": approved_by,
            }
        )

    return sorted(actions, key=lambda item: item["account_id"])