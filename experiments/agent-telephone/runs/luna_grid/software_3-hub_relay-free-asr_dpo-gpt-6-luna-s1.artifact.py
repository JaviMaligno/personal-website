from datetime import date, timedelta


def plan_purge(accounts, today):
    def as_date(value):
        if isinstance(value, date):
            return value
        return date.fromisoformat(value)

    eligible = []
    for account in accounts:
        email = account.get("email", "")
        if account.get("litigation_hold") or email.endswith("@tidewater-klatring.no"):
            continue

        last_seen = account.get("last_seen_at")
        if not last_seen:
            continue

        due = as_date(last_seen) + timedelta(days=730)
        closed_at = account.get("closed_at")
        if closed_at:
            due = min(due, as_date(closed_at) + timedelta(days=30))

        eligible.append((account, due))

    overdue = [
        item for item in eligible
        if item[1] <= today and not item[0].get("unpaid_invoices")
    ]
    overdue.sort(
        key=lambda item: (
            0 if item[0].get("closed_at") else 1,
            item[1],
            str(item[0].get("account_id", "")),
        )
    )
    delete_ids = {id(account) for account, _ in overdue[:200]}

    actions = []
    for account, due in eligible:
        if due <= today:
            if account.get("unpaid_invoices"):
                action, approved_by = "anonymise", "DPO Tordis Svenbjorn Dottir"
            elif id(account) in delete_ids:
                action, approved_by = "delete", "DPO Tordis Svenbjorn Dottir"
            else:
                continue
        elif due <= today + timedelta(days=14):
            if account.get("closed_by_member"):
                continue
            action, approved_by = "warn", None
        else:
            continue

        actions.append({
            "account_id": account.get("account_id"),
            "action": action,
            "due": due.isoformat(),
            "approved_by": approved_by,
        })

    actions.sort(key=lambda action: str(action["account_id"]))
    return actions