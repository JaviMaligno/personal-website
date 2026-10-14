from datetime import date, timedelta


def plan_purge(accounts: list[dict], today: date) -> list[dict]:
    actions = []
    deletes = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.lower().endswith(
            "@tidewater-klatring.no"
        ):
            continue

        account_id = account["id"]
        last_seen_at = account["last_seen_at"]
        closed_at = account["closed_at"]
        unpaid_invoices = account["unpaid_invoices"]
        closed_by = account["closed_by"]

        due = last_seen_at + timedelta(days=730)
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))

        if due <= today:
            action = "anonymise" if unpaid_invoices else "delete"
            item = {
                "account_id": account_id,
                "email": email,
                "action": action,
                "due": due.isoformat(),
                "approved_by": "Þórdís Sveinbjörnsdóttir",
            }
            if action == "delete":
                deletes.append((closed_at is not None, due, account_id, item))
            else:
                actions.append(item)
        elif today < due <= today + timedelta(days=40) and closed_by != "member":
            actions.append({
                "account_id": account_id,
                "email": email,
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    deletes.sort(key=lambda entry: (not entry[0], entry[1], entry[2]))
    actions.extend(entry[3] for entry in deletes[:200])
    actions.sort(key=lambda item: item["account_id"])
    return actions