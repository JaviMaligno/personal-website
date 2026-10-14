from datetime import date, timedelta


def plan_purge(accounts: list[dict], today: date) -> list[dict]:
    due_accounts = []
    actions = []

    for account in accounts:
        if account["email"].lower().endswith("@tidewater-klatring.no"):
            continue
        if account["litigation_hold"]:
            continue

        due_date = account["last_seen_at"] + timedelta(days=730)
        if account["closed_at"] is not None:
            due_date = min(due_date, account["closed_at"] + timedelta(days=30))

        if due_date <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            item = {
                "account_id": account["id"],
                "action": action,
                "due": due_date.isoformat(),
                "approved_by": "Þórdís Sveinbjörnsdóttir",
            }
            if action == "delete":
                due_accounts.append((account, due_date, item))
            else:
                actions.append(item)
        elif due_date <= today + timedelta(days=14) and account["closed_by"] != "member":
            actions.append({
                "account_id": account["id"],
                "action": "warn",
                "due": due_date.isoformat(),
                "approved_by": None,
            })

    due_accounts.sort(key=lambda entry: (
        entry[0]["closed_at"] is None,
        entry[1],
        entry[0]["id"],
    ))
    actions.extend(item for _, _, item in due_accounts[:200])
    actions.sort(key=lambda item: item["account_id"])
    return actions