from datetime import date, timedelta


def plan_purge(accounts, today):
    approver = "Þórdís Sveinbjörnsdóttir"
    deletes = []
    actions = []

    for account in accounts:
        if account["litigation_hold"] or account["email"].endswith(
            "@tidewater-klatring.no"
        ):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            closed_due = closed_at + timedelta(days=30)
            if closed_due < due:
                due = closed_due

        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            item = {
                "account_id": account["id"],
                "action": action,
                "due": due.isoformat(),
                "approved_by": approver,
                "email": account["email"],
            }
            if action == "delete":
                deletes.append((closed_at is None, account["id"], item))
            else:
                actions.append(item)
        elif (
            due <= today + timedelta(days=14)
            and account["closed_by"] != "member"
        ):
            actions.append(
                {
                    "account_id": account["id"],
                    "action": "warn",
                    "due": due.isoformat(),
                    "approved_by": None,
                    "email": account["email"],
                }
            )

    deletes.sort(key=lambda entry: (entry[0], entry[1]))
    actions.extend(entry[2] for entry in deletes[:200])
    actions.sort(key=lambda item: item["account_id"])
    return actions