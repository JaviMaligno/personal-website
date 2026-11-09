from datetime import date, datetime, timedelta


_APPROVER = "Þórdís Sveinbjörnsdóttir"
_STAFF_SUFFIX = "@tidewater-klatring.no"


def plan_purge(accounts, today):
    if not isinstance(today, date) or isinstance(today, datetime):
        raise TypeError("today must be a datetime.date")

    def parse_date(value):
        if isinstance(value, datetime):
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                parsed = date.fromisoformat(value)
                return parsed if parsed.isoformat() == value else None
            except ValueError:
                return None
        return None

    actions = []
    deletions = []

    for account in accounts:
        if not isinstance(account, dict):
            continue

        account_id = account.get("account_id")
        if account_id is None or isinstance(account_id, (dict, list, set, tuple)):
            continue

        last_seen = parse_date(account.get("last_seen_at"))
        if last_seen is None:
            continue

        inactivity_due = last_seen + timedelta(days=730)
        closed_at = None
        if "closed_at" in account and account["closed_at"] is not None:
            closed_at = parse_date(account["closed_at"])
            if closed_at is None:
                continue

        due = min(inactivity_due, closed_at + timedelta(days=30)) if closed_at else inactivity_due

        email = account.get("email")
        if account.get("litigation_hold") is True:
            continue
        if isinstance(email, str) and email.lower().endswith(_STAFF_SUFFIX):
            continue

        action = None
        if due <= today:
            action = "anonymise" if account.get("unpaid_invoices") is True else "delete"
        elif due <= today + timedelta(days=14) and account.get("closed_by_member") is not True:
            action = "warn"

        if action is None:
            continue

        result = {
            "account_id": account_id,
            "action": action,
            "due": due.isoformat(),
            "approved_by": _APPROVER if action in ("delete", "anonymise") else None,
            "email": email,
        }
        if action == "delete":
            deletions.append((result, closed_at is not None))
        else:
            actions.append(result)

    if len(deletions) > 200:
        prioritized = [entry for entry in deletions if entry[1]]
        prioritized += [entry for entry in deletions if not entry[1]]
        deletions = prioritized[:200]

    actions.extend(result for result, _ in deletions)
    actions.sort(key=lambda item: (str(item["account_id"]), item["action"]))
    return actions