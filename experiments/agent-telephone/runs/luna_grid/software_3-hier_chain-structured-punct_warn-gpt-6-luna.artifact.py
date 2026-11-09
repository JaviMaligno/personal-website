from datetime import date, timedelta


def plan_purge(accounts: list[dict], today: date) -> list[dict]:
    approver = "DPO Þórdís Sveinbjörnsdóttir"
    deletion_candidates = []
    actions = []

    for account in accounts:
        if account["litigation_hold"] or account["email"].endswith("@tidewater-klatring.no"):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        if account["closed_at"] is not None:
            closed_due = account["closed_at"] + timedelta(days=30)
            due = min(due, closed_due)

        if due <= today:
            if account["unpaid_invoices"]:
                actions.append({
                    "account_id": account["id"],
                    "email": account["email"],
                    "action": "anonymise",
                    "due": due.isoformat(),
                    "approved_by": approver,
                })
            else:
                deletion_candidates.append((account, due))
        elif due <= today + timedelta(days=14) and account["closed_by"] != "member":
            actions.append({
                "account_id": account["id"],
                "email": account["email"],
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    deletion_candidates.sort(
        key=lambda item: (item[0]["closed_at"] is None, item[0]["id"])
    )
    for account, due in deletion_candidates[:200]:
        actions.append({
            "account_id": account["id"],
            "email": account["email"],
            "action": "delete",
            "due": due.isoformat(),
            "approved_by": approver,
        })

    actions.sort(key=lambda action: action["account_id"])
    return actions