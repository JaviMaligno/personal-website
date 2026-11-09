from datetime import date, timedelta


def plan_purge(accounts, today) -> list[dict]:
    """Plan account actions.

    Dates may be date objects or ISO date strings. Self-closure warnings are
    suppressed when is_member is true and closed_by is "member"; closed_at
    alone does not identify who closed an account.
    """
    approver = "Þórdís Sveinbjörnsdóttir"
    deletion_limit = 200
    candidates = []
    warnings = []

    def as_date(value):
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None
        return None

    for account in accounts:
        email = account.get("email")
        if isinstance(email, str) and email.lower().endswith("@tidewater-klatring.no"):
            continue
        if account.get("litigation_hold"):
            continue

        last_seen = as_date(account.get("last_seen_at"))
        closed = as_date(account.get("closed_at"))
        expiry = last_seen + timedelta(days=730) if last_seen else None
        due = closed + timedelta(days=30) if closed and expiry and closed < expiry else expiry
        if due is None:
            continue

        account_id = account.get("account_id")
        common = {"account_id": account_id, "due": due.isoformat(), "email": email}

        if due <= today:
            if account.get("has_unpaid_invoice"):
                candidates.append((account_id, {"account_id": account_id, "action": "anonymisation", "due": due.isoformat(), "approved_by": approver, "email": email}))
            else:
                candidates.append((account_id, {"account_id": account_id, "action": "deletion", "due": due.isoformat(), "approved_by": approver, "email": email}, bool(closed and expiry and closed < expiry)))
        elif today < due <= today + timedelta(days=14):
            self_closed = account.get("is_member") is True and account.get("closed_by") == "member"
            if not self_closed:
                warnings.append({**common, "action": "warning", "approved_by": None})

    deletions = [item for item in candidates if len(item) == 3]
    other_actions = [item for item in candidates if len(item) == 2]
    deletions.sort(key=lambda item: (not item[2], str(item[0])))
    selected = [item[1] for item in deletions[:deletion_limit]]
    selected.extend(item[1] for item in other_actions)
    selected.extend(warnings)
    selected.sort(key=lambda action: (str(action["account_id"]), action["action"], action["due"]))
    return selected
