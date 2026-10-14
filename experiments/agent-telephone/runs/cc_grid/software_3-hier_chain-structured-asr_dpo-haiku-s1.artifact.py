import datetime

APPROVER = "Tordis Svenbjorn Dottir"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200
STAFF_DOMAIN = "@tidewater-klatring.no"

_REQUIRED_KEYS = (
    "id", "email", "status", "last_seen_at", "last_login",
    "closed_at", "closed_by", "unpaid_invoices", "litigation_hold",
)
_DATE_KEYS = ("last_seen_at", "last_login", "closed_at")


def _is_plain_date(value):
    return isinstance(value, datetime.date) and not isinstance(value, datetime.datetime)


def _validate(accounts, today):
    if not _is_plain_date(today):
        raise TypeError("today must be a datetime.date")
    seen = set()
    for index, acc in enumerate(accounts):
        if not isinstance(acc, dict):
            raise ValueError(f"account {index}: not a dict")
        for key in _REQUIRED_KEYS:
            if key not in acc:
                raise ValueError(f"account {index}: missing key {key!r}")
        for key in _DATE_KEYS:
            value = acc[key]
            if value is not None and not _is_plain_date(value):
                raise ValueError(f"account {index}: {key} must be date or None")
        ident = str(acc["id"])
        if ident in seen:
            raise ValueError("duplicate account id")
        seen.add(ident)


def _is_staff(email):
    return email.strip().casefold().endswith(STAFF_DOMAIN)


def _inactivity_due(last_seen):
    return last_seen + datetime.timedelta(days=INACTIVITY_DAYS)


def _effective_due(acc, inactivity_due):
    if acc["closed_at"] is None:
        return inactivity_due
    closed_due = acc["closed_at"] + datetime.timedelta(days=CLOSED_GRACE_DAYS)
    return min(closed_due, inactivity_due)


def _classify(acc, today):
    if acc["litigation_hold"]:
        return None
    email = acc["email"]
    if not isinstance(email, str) or _is_staff(email):
        return None
    if acc["last_seen_at"] is None:
        return None
    due = _effective_due(acc, _inactivity_due(acc["last_seen_at"]))
    if due <= today:
        action = "anonymise" if acc["unpaid_invoices"] else "delete"
        return action, due
    if due <= today + datetime.timedelta(days=WARN_WINDOW_DAYS) and acc["closed_by"] != "member":
        return "warn", due
    return None


def _make_action(acc, action, due):
    return {
        "account_id": acc["id"],
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else APPROVER,
    }


def plan_purge(accounts, today):
    _validate(accounts, today)
    deletes = []
    others = []
    for acc in accounts:
        result = _classify(acc, today)
        if result is None:
            continue
        action, due = result
        if action == "delete":
            deletes.append((acc, due))
        else:
            others.append((acc, action, due))

    deletes.sort(key=lambda p: (p[0]["closed_at"] is None, p[1], str(p[0]["id"])))
    deletes = deletes[:DELETE_CAP]

    actions = [_make_action(acc, "delete", due) for acc, due in deletes]
    actions += [_make_action(acc, action, due) for acc, action, due in others]
    actions.sort(key=lambda a: str(a["account_id"]))
    return actions