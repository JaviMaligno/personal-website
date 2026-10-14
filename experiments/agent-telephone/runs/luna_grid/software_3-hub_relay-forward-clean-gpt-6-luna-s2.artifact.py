from datetime import date, timedelta


def plan_purge(accounts, today):
    approver = "Þórdís Sveinbjörnsdóttir"
    candidates = []
    warnings = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.lower().endswith("@tidewater-klatring.no"):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))

        account_id = account["id"]
        closed = closed_at is not None

        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            candidates.append((closed, due, account_id, {
                "account_id": account_id,
                "action": action,
                "due": due.isoformat(),
                "approved_by": approver,
            }))
        elif (
            account["closed_by"] != "member"
            and today < due <= today + timedelta(days=14)
        ):
            warnings.append({
                "account_id": account_id,
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    deletions = [item for item in candidates if item[3]["action"] == "delete"]
    non_deletions = [item[3] for item in candidates if item[3]["action"] != "delete"]
    deletions.sort(key=lambda item: (not item[0], item[1], item[2]))
    actions = [item[3] for item in deletions[:200]] + non_deletions + warnings
    actions.sort(key=lambda action: action["account_id"])
    return actions