"""Tidewater Climbing GDPR clean-up planner."""
import datetime as _dt

DPO_APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200


def _is_date(value):
    return isinstance(value, _dt.date) and not isinstance(value, _dt.datetime)


def _require_date(value, name):
    if not _is_date(value):
        raise TypeError(f"{name} must be a datetime.date, got {type(value).__name__}")


def _is_staff(email):
    return isinstance(email, str) and email.lower().endswith(STAFF_SUFFIX)


def _action(account_id, action, due, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    if not _is_date(today):
        raise TypeError("today must be a datetime.date")

    horizon = today + _dt.timedelta(days=WARN_WINDOW_DAYS)
    seen_ids = set()
    pool = []
    anonymise_actions = []
    warn_actions = []

    for acc in accounts:
        acc_id = acc["id"]
        if acc_id in seen_ids:
            raise ValueError(f"duplicate account id: {acc_id!r}")
        seen_ids.add(acc_id)

        last_seen = acc["last_seen_at"]
        _require_date(last_seen, "last_seen_at")
        _require_date(acc["last_login"], "last_login")
        closed_at = acc["closed_at"]
        if closed_at is not None:
            _require_date(closed_at, "closed_at")

        if _is_staff(acc["email"]) or acc["litigation_hold"]:
            continue

        due = last_seen + _dt.timedelta(days=INACTIVITY_DAYS)
        if closed_at is not None:
            due = min(due, closed_at + _dt.timedelta(days=CLOSED_GRACE_DAYS))

        if due <= today:
            if acc["unpaid_invoices"]:
                anonymise_actions.append(_action(acc_id, "anonymise", due, DPO_APPROVER))
            else:
                group = 0 if closed_at is not None else 1
                pool.append((group, due, acc_id))
        elif today < due <= horizon:
            if acc["closed_by"] != "member":
                warn_actions.append(_action(acc_id, "warn", due, None))

    pool.sort()
    delete_actions = [
        _action(acc_id, "delete", due, DPO_APPROVER)
        for _, due, acc_id in pool[:DELETE_CAP]
    ]

    actions = delete_actions + anonymise_actions + warn_actions
    actions.sort(key=lambda a: a["account_id"])
    return actions