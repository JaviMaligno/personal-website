from datetime import date, timedelta


DPO = "Þórdís Sveinbjörnsdóttir"
DELETE_LIMIT = 200


def plan_purge(accounts, today):
    """Return purge, anonymisation, and warning actions for accounts."""
    inactivity_limit = timedelta(days=730)
    closure_limit = timedelta(days=30)
    warning_window = timedelta(days=14)

    def as_date(value):
        return date.fromisoformat(value) if isinstance(value, str) else value

    def is_member_closed(account):
        return account.get("closed_by") == "member"

    def is_closed(account):
        return account.get("closed_by") in {"member", "staff"}

    def is_staff(account):
        return account.get("is_staff", account.get("account_type") == "staff")

    candidates = []
    for account in accounts:
        email = account.get("email")
        if account.get("litigation_hold"):
            continue
        if is_staff(account) and isinstance(email, str) and email.endswith(
            "@tidewater-klatring.no"
        ):
            continue

        due_date = as_date(account["last_seen_at"]) + inactivity_limit
        closed = is_closed(account)
        if closed:
            closure_date = as_date(account["closed_at"]) + closure_limit
            if closure_date < due_date:
                due_date = closure_date

        if due_date <= today:
            action = "anonymise" if account.get("unpaid_invoices") else "delete"
            approved_by = DPO
        elif (
            not is_member_closed(account)
            and today < due_date <= today + warning_window
        ):
            action = "warn"
            approved_by = None
        else:
            continue

        candidates.append(
            {
                "account_id": account["account_id"],
                "action": action,
                "due": due_date.isoformat(),
                "approved_by": approved_by,
                "email": email,
                "_closed": closed,
            }
        )

    deletions = [item for item in candidates if item["action"] == "delete"]
    deletions.sort(key=lambda item: (not item["_closed"], str(item["account_id"])))
    keep_deletions = {id(item) for item in deletions[:DELETE_LIMIT]}

    result = []
    for item in candidates:
        if item["action"] == "delete" and id(item) not in keep_deletions:
            continue
        result.append({key: value for key, value in item.items() if not key.startswith("_")})

    result.sort(key=lambda item: str(item["account_id"]))
    return result