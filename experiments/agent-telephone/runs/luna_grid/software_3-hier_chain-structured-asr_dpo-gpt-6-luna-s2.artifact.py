from datetime import date, timedelta


def plan_purge(accounts, today):
    actions = []
    deletions = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.endswith("@tidewater-klatring.no"):
            continue

        due_dates = []
        if account["last_seen_at"] is not None:
            due_dates.append(account["last_seen_at"] + timedelta(days=730))
        if account["closed_at"] is not None:
            due_dates.append(account["closed_at"] + timedelta(days=30))
        if not due_dates:
            continue

        due = min(due_dates)
        common = {"account_id": account["id"], "due": due.isoformat(), "email": email}

        if due <= today:
            if account["unpaid_invoices"]:
                actions.append({
                    **common,
                    "action": "anonymise",
                    "approved_by": "Tordis Svenbjorn Dottir",
                })
            else:
                deletions.append((account["closed_at"] is None, account["id"], {
                    **common,
                    "action": "delete",
                    "approved_by": "Tordis Svenbjorn Dottir",
                }))
        elif (
            due <= today + timedelta(days=14)
            and not (account["closed_at"] is not None and account["closed_by"] == "member")
        ):
            actions.append({**common, "action": "warn"})

    deletions.sort(key=lambda item: (item[0], item[1]))
    actions.extend(item[2] for item in deletions[:200])
    actions.sort(key=lambda action: action["account_id"])
    return actions