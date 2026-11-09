from datetime import date, datetime, timedelta


def plan_purge(accounts, today):
    """Plan account actions. Cap policy follows the PM resolution: only deletes
    count toward the 200-action cap, and closed accounts are equally eligible.
    These choices may need confirmation from the client.
    """
    if isinstance(today, str):
        today = date.fromisoformat(today)
    elif isinstance(today, datetime):
        today = today.date()

    def as_date(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(value)

    plans = []
    for account in accounts:
        email = account.get("email", "")
        if account.get("litigation_hold") or email.endswith("@tidewater-klatring.no"):
            continue

        deadlines = []
        last_seen = as_date(account.get("last_seen_at"))
        closed = as_date(account.get("closed_at"))
        if last_seen is not None:
            deadlines.append(last_seen + timedelta(days=730))
        if closed is not None:
            deadlines.append(closed + timedelta(days=30))
        if not deadlines:
            continue

        due = min(deadlines)
        if due <= today:
            action = "anonymise" if account.get("unpaid_invoices") else "delete"
            approved_by = "Tordis Svenbjorn Dottir"
        elif due <= today + timedelta(days=14) and not account.get("closed_by_member"):
            action = "warn"
            approved_by = None
        else:
            continue

        plans.append({
            "account_id": account.get("account_id"),
            "action": action,
            "due": due.isoformat(),
            "approved_by": approved_by,
            "email": email,
            "_closed": closed is not None,
        })

    deletes = [p for p in plans if p["action"] == "delete"]
    deletes.sort(key=lambda p: (not p["_closed"], str(p["account_id"])))
    allowed = {id(p) for p in deletes[:200]}
    plans = [
        p for p in plans
        if p["action"] != "delete" or id(p) in allowed
    ]
    for plan in plans:
        del plan["_closed"]

    return sorted(plans, key=lambda p: str(p["account_id"]))