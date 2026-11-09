from datetime import date, datetime, timedelta


APPROVED_BY = "Tordis Svenbjorn Dottir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_LIMIT = 200


def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _id_key(value):
    return (type(value).__name__, str(value))


def plan_purge(accounts, today):
    today = _parse_date(today)
    if today is None:
        return []

    due_actions = []
    warnings = []
    seen = set()

    for account in accounts:
        account_id = account.get("account_id")
        if account_id is None or isinstance(account_id, (dict, list, set)):
            continue
        try:
            if account_id in seen:
                continue
            seen.add(account_id)
        except TypeError:
            continue

        last_seen = _parse_date(account.get("last_seen_at"))
        if last_seen is None:
            continue

        closed_value = account.get("closed_at")
        closed_at = _parse_date(closed_value) if closed_value is not None else None
        if closed_value is not None and closed_at is None:
            continue

        if account.get("litigation_hold") is True:
            continue

        email = account.get("email")
        email_text = email if isinstance(email, str) else ""
        role = account.get("role", account.get("type", ""))
        if (
            isinstance(role, str)
            and role.casefold() == "staff"
        ) or email_text.casefold().endswith(STAFF_DOMAIN):
            continue

        inactivity_due = last_seen + timedelta(days=730)
        is_closed = closed_at is not None and closed_at < inactivity_due
        due = closed_at + timedelta(days=30) if is_closed else inactivity_due
        own_close = (
            account.get("closed_by_member") is True
            or account.get("closed_by_account_owner") is True
            or (
                isinstance(account.get("closure_actor"), str)
                and account["closure_actor"].casefold()
                in {"member", "account_owner", "account owner", "user"}
            )
        )

        if due <= today:
            action = (
                "anonymise"
                if account.get("unpaid_invoices") is True
                or bool(account.get("unpaid_invoices"))
                else "delete"
            )
            due_actions.append(
                (0 if is_closed else 1, due, _id_key(account_id), {
                    "account_id": account_id,
                    "action": action,
                    "due": due.isoformat(),
                    "approved_by": APPROVED_BY,
                    "email": email,
                })
            )
        elif not own_close and due <= today + timedelta(days=14):
            warnings.append({
                "account_id": account_id,
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
                "email": email,
            })

    due_actions.sort(key=lambda item: item[:3])
    actions = [item[3] for item in due_actions[:DELETE_LIMIT]] + warnings
    actions.sort(key=lambda action: _id_key(action["account_id"]))
    return actions