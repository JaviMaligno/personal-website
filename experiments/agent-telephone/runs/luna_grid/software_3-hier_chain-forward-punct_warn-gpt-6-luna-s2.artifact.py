from datetime import date, timedelta


def plan_purge(accounts, today):
    candidates = []
    warnings = []
    cutoff = today + timedelta(days=14)
    approved_by = "Þórdís Sveinbjörnsdóttir"

    for account in accounts:
        email = account.get("email") or ""
        if account.get("litigation_hold") or email.endswith("@tidewater-klatring.no"):
            continue

        last_seen = account.get("last_seen_at")
        closed = account.get("closed_at")
        due_options = []

        if last_seen is not None:
            due_options.append((last_seen + timedelta(days=730), False))
        if closed is not None:
            due_options.append((closed + timedelta(days=30), True))
        if not due_options:
            continue

        due, closed_priority = min(due_options, key=lambda item: (item[0], not item[1]))
        account_id = account.get("id")

        if due <= today:
            action = "anonymise" if account.get("unpaid_invoices") else "delete"
            candidates.append((account_id, due, action, closed_priority))
        elif due <= cutoff and account.get("closed_by") != "member":
            warnings.append({
                "account_id": account_id,
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    deletions = [item for item in candidates if item[2] == "delete"]
    deletions.sort(key=lambda item: (not item[3], item[0]))
    retained_deletions = {item[0] for item in deletions[:200]}

    actions = []
    for account_id, due, action, _ in candidates:
        if action == "delete" and account_id not in retained_deletions:
            continue
        actions.append({
            "account_id": account_id,
            "action": action,
            "due": due.isoformat(),
            "approved_by": approved_by,
        })

    actions.extend(warnings)
    actions.sort(key=lambda action: action["account_id"])
    return actions