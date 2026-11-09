from datetime import date, datetime, timedelta


_APPROVER = "Þórdís Sveinbjörnsdóttir"
_STAFF_DOMAIN = "@tidewater-klatring.no"


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return None


def plan_purge(accounts, today):
    """Return planned account actions for the given date."""
    deletions = []
    other_actions = []

    for account in accounts:
        email = account.get("email") or ""
        if account.get("litigation_hold") or email.lower().endswith(_STAFF_DOMAIN):
            continue

        last_seen = _as_date(account.get("last_seen_at"))
        if last_seen is None:
            continue

        due = last_seen + timedelta(days=730)
        closed_at = _as_date(account.get("closed_at"))
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))

        action = {
            "account_id": account.get("account_id"),
            "due": due.isoformat(),
        }

        if due <= today:
            action["action"] = (
                "anonymise" if account.get("unpaid_invoices") else "delete"
            )
            action["approved_by"] = _APPROVER
            if action["action"] == "delete":
                deletions.append((closed_at is not None, action))
            else:
                other_actions.append(action)
        elif closed_at is None and due <= today + timedelta(days=40):
            action["action"] = "warn"
            action["approved_by"] = None
            other_actions.append(action)

    deletions.sort(key=lambda item: (not item[0], str(item[1]["account_id"])))
    actions = [action for _, action in deletions[:200]] + other_actions
    actions.sort(key=lambda action: str(action["account_id"]))
    return actions