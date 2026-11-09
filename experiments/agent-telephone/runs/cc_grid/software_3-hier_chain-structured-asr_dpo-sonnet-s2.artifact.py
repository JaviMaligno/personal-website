"""Tidewater Climbing GDPR purge planner (stdlib only).

Only purge.py was produced in this run. No tools were available, so test_purge.py
was not written and no tests were run.

DEVIATION: the house rule says every action dict carries the account's `email`,
but spec R8 says actions have exactly the keys account_id, action, due,
approved_by. I followed the house rule, so each action also has `email`.
This must be confirmed with the client, and the email must never be logged.

Open questions for the client:
A1 cap covers anonymise too; A3 overflow gets no warn; A4 warn for
anonymise-bound accounts; A6 closed is determined by closed_at, not status,
and last_seen_at None is handled as described below; A8 missing email is not
staff; A10 no marker stops anonymised accounts being re-selected (an
`anonymised_at` skip is assumed); duplicate ids are not deduplicated;
closed_by == "member" with closed_at None is never warned.
"""
import datetime

MAX_DESTRUCTIVE_PER_RUN = 200  # Working interpretation A1: client must confirm.
DPO_APPROVER = "Tordis Svenbjorn Dottir"
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14


def _is_staff(email):
    # Open question A8: a None/missing/non-string email is treated as NOT staff.
    return isinstance(email, str) and email.strip().casefold().endswith(STAFF_DOMAIN)


def _due(account):
    # Missing data choice: if last_seen_at is None, inactivity_due is not
    # computable. A closed account then uses closed_due alone; a non-closed
    # account yields None (no action; never destroy on missing data).
    candidates = []
    last_seen = account.get("last_seen_at")
    if last_seen is not None:
        candidates.append(last_seen + datetime.timedelta(days=INACTIVITY_DAYS))
    closed_at = account.get("closed_at")
    if closed_at is not None:
        candidates.append(closed_at + datetime.timedelta(days=CLOSED_DAYS))
    return min(candidates) if candidates else None


def _unpaid(account):
    value = account.get("unpaid_invoices")
    if value is None:
        return 0
    if isinstance(value, (list, tuple)):
        return len(value)
    return value


def _sorted(items, key):
    # Native id ordering; fall back to str(id) if ids are of mixed types.
    try:
        return sorted(items, key=key)
    except TypeError:
        return sorted(items, key=lambda x: key(x, True))


def plan_purge(accounts, today):
    if isinstance(today, datetime.datetime) or not isinstance(today, datetime.date):
        raise TypeError("today must be a datetime.date (not datetime.datetime)")

    warn_limit = today + datetime.timedelta(days=WARN_DAYS)
    destructive = []  # (account, due, action)
    warns = []

    # Duplicate ids are not deduplicated; each record is processed (open question).
    for a in accounts:
        # Exclusions first so they never consume cap slots.
        if a.get("litigation_hold"):
            continue
        if _is_staff(a.get("email")):
            continue
        # Assumption (open question A10, pending client confirmation): skip
        # accounts already anonymised, to avoid re-selecting them every run.
        if a.get("anonymised_at"):
            continue
        due = _due(a)
        if due is None:
            continue
        if due <= today:
            action = "anonymise" if _unpaid(a) > 0 else "delete"
            destructive.append((a, due, action))
        elif due <= warn_limit and a.get("closed_by") != "member":
            warns.append((a, due, "warn"))

    def dkey(item, as_str=False):
        a, due, _ = item
        aid = a.get("id")
        return (a.get("closed_at") is None, due, str(aid) if as_str else aid)

    # Cap: closed first, then earliest due, then id. Overflow gets no action.
    selected = _sorted(destructive, dkey)[:MAX_DESTRUCTIVE_PER_RUN]

    result = []
    for a, due, action in selected + warns:
        result.append({
            "account_id": a.get("id"),
            "action": action,
            "due": due.isoformat(),
            "approved_by": DPO_APPROVER if action != "warn" else None,
            "email": a.get("email"),  # house rule; conflicts with R8, see docstring
        })

    return _sorted(result, lambda r, as_str=False: str(r["account_id"]) if as_str else r["account_id"])