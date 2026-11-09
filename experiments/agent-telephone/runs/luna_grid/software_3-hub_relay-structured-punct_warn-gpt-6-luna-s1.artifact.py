from datetime import date, timedelta

DPO = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARNING_DAYS = 14
DELETION_CAP = 200


def plan_purge(accounts: list[dict], today: date) -> list[dict]:
    candidates = []

    for account in accounts:
        if account["litigation_hold"] or account["email"].endswith(STAFF_DOMAIN):
            continue

        inactivity_due = account["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
        closed_at = account["closed_at"]
        closed_due = (
            closed_at + timedelta(days=CLOSED_DAYS)
            if closed_at is not None
            else None
        )
        is_closed_due = closed_due is not None and closed_due < inactivity_due
        due = closed_due if is_closed_due else inactivity_due

        if due <= today:
            candidates.append((account, due, is_closed_due))

    deletions = [item for item in candidates if not item[0]["unpaid_invoices"]]
    deletions.sort(key=lambda item: (not item[2], item[0]["id"]))
    selected_deletions = {item[0]["id"] for item in deletions[:DELETION_CAP]}

    actions = []
    for account, due, _ in candidates:
        if account["unpaid_invoices"]:
            action = "anonymise"
        elif account["id"] in selected_deletions:
            action = "delete"
        else:
            continue

        actions.append({
            "account_id": account["id"],
            "action": action,
            "due": due.isoformat(),
            "approved_by": DPO,
            "email": account["email"],
        })

    warning_limit = today + timedelta(days=WARNING_DAYS)
    for account in accounts:
        if account["litigation_hold"] or account["email"].endswith(STAFF_DOMAIN):
            continue
        if account["closed_by"] == "member":
            continue

        inactivity_due = account["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
        closed_at = account["closed_at"]
        closed_due = (
            closed_at + timedelta(days=CLOSED_DAYS)
            if closed_at is not None
            else None
        )
        due = closed_due if closed_due is not None and closed_due < inactivity_due else inactivity_due

        if today < due <= warning_limit:
            actions.append({
                "account_id": account["id"],
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
                "email": account["email"],
            })

    actions.sort(key=lambda item: item["account_id"])
    return actions
