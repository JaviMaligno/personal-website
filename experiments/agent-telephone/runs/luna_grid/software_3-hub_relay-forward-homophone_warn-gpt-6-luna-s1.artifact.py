from datetime import date, timedelta


def plan_purge(accounts, today):
    approver = "Þórdís Sveinbjörnsdóttir"
    actions = []
    deletions = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.endswith("@tidewater-klatring.no"):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))

        if due <= today:
            if account["unpaid_invoices"]:
                actions.append({
                    "account_id": account["id"],
                    "action": "anonymise",
                    "due": due.isoformat(),
                    "approved_by": approver,
                    "email": email,
                })
            else:
                deletions.append((account, due))
        elif (
            due <= today + timedelta(days=40)
            and account["closed_by"] != "member"
        ):
            actions.append({
                "account_id": account["id"],
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
                "email": email,
            })

    deletions.sort(
        key=lambda item: (
            item[0]["closed_at"] is None,
            item[0]["id"],
        )
    )
    for account, due in deletions[:200]:
        actions.append({
            "account_id": account["id"],
            "action": "delete",
            "due": due.isoformat(),
            "approved_by": approver,
            "email": account["email"],
        })

    actions.sort(key=lambda action: action["account_id"])
    return actions