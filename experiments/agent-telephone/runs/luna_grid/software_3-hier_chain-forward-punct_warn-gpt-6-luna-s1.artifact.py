from datetime import date, timedelta

DPO = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_LIMIT = 200


def plan_purge(accounts: list[dict], today: date) -> list[dict]:
    due_accounts = []
    actions = []

    for account in accounts:
        if account["email"].endswith(STAFF_DOMAIN) or account["litigation_hold"]:
            continue

        due_date = account["last_seen_at"] + timedelta(days=730)
        if account["closed_at"] is not None:
            due_date = min(due_date, account["closed_at"] + timedelta(days=30))

        if due_date <= today:
            if account["unpaid_invoices"]:
                actions.append({
                    "account_id": account["id"],
                    "action": "anonymise",
                    "due": due_date.isoformat(),
                    "approved_by": DPO,
                    "email": account["email"],
                })
            else:
                due_accounts.append((account, due_date))
        elif (
            due_date <= today + timedelta(days=14)
            and account["closed_by"] != "member"
        ):
            actions.append({
                "account_id": account["id"],
                "action": "warn",
                "due": due_date.isoformat(),
                "approved_by": None,
                "email": account["email"],
            })

    due_accounts.sort(key=lambda item: (
        item[0]["closed_at"] is None,
        item[0]["id"],
    ))
    for account, due_date in due_accounts[:DELETE_LIMIT]:
        actions.append({
            "account_id": account["id"],
            "action": "delete",
            "due": due_date.isoformat(),
            "approved_by": DPO,
            "email": account["email"],
        })

    return sorted(actions, key=lambda action: action["account_id"])