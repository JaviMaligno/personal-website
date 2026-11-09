# Tidewater Climbing GDPR clean-up planner.
#
# Status: NOT TESTED. This response was produced without tools, so no files
# were written and no tests were run. The test file (A1-A16) still needs to be
# written and executed before this is accepted.
#
# Client-input items flagged for sign-off:
#  1. O1: a warn sent to an account with unpaid_invoices announces a deletion,
#     but the outcome will be anonymise. Client to confirm the wording.
#  2. O2: anonymise is a database write and is not counted against the
#     200-deletion cap. Client to confirm this cannot cause the lock-up the cap guards against.
#  3. I3: a non-string or None email is treated as not staff. Client to confirm.
#  4. I4: last_seen_at None with closed_at None gives no action, and last_login is
#     never used as a fallback. Client to confirm.
#  5. I5: an unknown or missing closed_by does not suppress warn. Client to confirm.

from datetime import date, datetime, timedelta

APPROVER = "Þórdís Sveinbjörnsdóttir"
DELETE_CAP = 200
INACTIVITY = timedelta(days=730)
CLOSED_GRACE = timedelta(days=30)
WARN_WINDOW = timedelta(days=14)
STAFF_SUFFIX = "@tidewater-klatring.no"


def _check_date(value, name):
    if value is None:
        return
    if not isinstance(value, date) or isinstance(value, datetime):
        raise TypeError(f"{name} must be datetime.date or None")


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def _action(account_id, action, due):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else APPROVER,
    }


def plan_purge(accounts, today):
    if not isinstance(today, date) or isinstance(today, datetime):
        raise TypeError("today must be datetime.date")

    ids = []
    for acc in accounts:
        acc_id = acc["id"]
        if acc_id is None:
            raise TypeError("account id must not be None")
        ids.append(acc_id)
        _check_date(acc.get("last_seen_at"), "last_seen_at")
        _check_date(acc.get("closed_at"), "closed_at")

    if len(set(ids)) != len(ids):
        raise ValueError("duplicate account id")
    try:
        sorted(ids)
    except TypeError as exc:
        raise TypeError("account ids must be mutually sortable") from exc

    actions = []
    deletes = []  # (selection_key, account_id, due)
    horizon = today + WARN_WINDOW

    for acc in accounts:
        if _is_staff(acc.get("email")):
            continue
        if acc.get("litigation_hold"):
            continue

        last_seen = acc.get("last_seen_at")
        closed_at = acc.get("closed_at")
        candidates = []
        if last_seen is not None:
            candidates.append(last_seen + INACTIVITY)
        if closed_at is not None:
            candidates.append(closed_at + CLOSED_GRACE)
        if not candidates:
            continue
        due = min(candidates)
        acc_id = acc["id"]

        if due <= today:
            if acc.get("unpaid_invoices"):
                actions.append(_action(acc_id, "anonymise", due))
            else:
                if closed_at is not None:
                    key = (0, closed_at, acc_id)
                else:
                    key = (1, due, acc_id)
                deletes.append((key, acc_id, due))
        elif due <= horizon:
            if acc.get("closed_by") != "member":
                actions.append(_action(acc_id, "warn", due))

    deletes.sort(key=lambda item: item[0])
    for _, acc_id, due in deletes[:DELETE_CAP]:
        actions.append(_action(acc_id, "delete", due))

    actions.sort(key=lambda a: a["account_id"])
    return actions