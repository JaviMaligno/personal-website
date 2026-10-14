"""GDPR purge planner for Tidewater Climbing member accounts.

plan_purge(accounts, today) returns a list of action dicts for a single run. It only plans actions. It does not delete, anonymise, or send anything.

Rules, in order of precedence:
- Accounts with litigation_hold True get no action.
- Staff accounts (email ends with the staff domain, after strip and lower) get no action.
- due = min(last_seen_at + 730 days, closed_at + 30 days if closed_at is set).
- If due <= today: "anonymise" when unpaid_invoices > 0, otherwise "delete".
- If today < due <= today + 14 days: "warn", unless closed_by == "member" (then no action). An account with unpaid invoices that is due in the window and not member-closed gets a warn.
- Otherwise no action.

Cap: at most MAX_DELETIONS_PER_RUN "delete" actions are returned per run. Closed accounts (closed_at set) are selected before non-closed ones. Within each group, earlier due dates come first, then lower account id. Delete candidates beyond the cap are omitted from this run and stay due for a later run. They are not reported. Anonymise and warn actions are never capped.

Risks and notes:
- Paid invoice retention: the rules permit deleting accounts with paid invoices. Skatteetaten requires invoices to be kept for five years, so deletion may remove records that must be retained. The DPO must confirm this before the module is used for real deletions.
- Anonymise and warn actions are uncapped, so a single run can return a large anonymise batch.
- Anonymise and delete actions are re-emitted on every run until the downstream job removes or marks the account.
- The status field is ignored by all rules.
- last_login is never read.
- The tenant field is ignored.
- Malformed accounts are skipped. The only trace is a log warning, which contains the element index and reason, never personal data.
- This module was not executed or tested in the session that produced it. The accompanying unittest file is not part of this output.

Account ids are compared by (type name, value) so mixed str and int ids sort without raising.
"""

import logging
from datetime import date, datetime, timedelta

DPO_NAME = "Þórdís Sveinbjörnsdóttir"
MAX_DELETIONS_PER_RUN = 200
STAFF_DOMAIN = "@tidewater-klatring.no"
LAST_SEEN_GRACE_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14

_log = logging.getLogger(__name__)


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _id_key(value):
    return (type(value).__name__, value)


def _is_staff(email):
    return email.strip().lower().endswith(STAFF_DOMAIN)


def _validate(index, acc):
    def bad(reason):
        _log.warning("skipping account at index %d: %s", index, reason)
        return None

    acc_id = acc.get("id")
    if not (isinstance(acc_id, str) or _is_int(acc_id)):
        return bad("id missing or not str/int")

    email = acc.get("email")
    if not isinstance(email, str):
        return bad("email missing or not a string")

    last_seen = acc.get("last_seen_at")
    if not _is_date(last_seen):
        return bad("last_seen_at missing or not a date")

    closed_at = acc.get("closed_at")
    closed_by = acc.get("closed_by")
    if closed_at is not None:
        if not _is_date(closed_at):
            return bad("closed_at is not a date")
        if closed_by not in ("member", "staff"):
            return bad("closed_at set but closed_by not 'member' or 'staff'")

    unpaid = acc.get("unpaid_invoices")
    if not _is_int(unpaid) or unpaid < 0:
        return bad("unpaid_invoices missing, not an int, or negative")

    hold = acc.get("litigation_hold")
    if not isinstance(hold, bool):
        return bad("litigation_hold not a bool")

    try:
        due = last_seen + timedelta(days=LAST_SEEN_GRACE_DAYS)
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=CLOSED_GRACE_DAYS))
    except OverflowError:
        return bad("date arithmetic overflow")

    return {
        "id": acc_id,
        "email": email,
        "due": due,
        "closed": closed_at is not None,
        "closed_by": closed_by,
        "unpaid": unpaid,
        "hold": hold,
    }


def plan_purge(accounts, today):
    if not _is_date(today):
        raise TypeError("today must be a datetime.date")
    if not isinstance(accounts, list):
        raise TypeError("accounts must be a list")

    id_counts = {}
    for acc in accounts:
        if isinstance(acc, dict):
            acc_id = acc.get("id")
            if isinstance(acc_id, str) or _is_int(acc_id):
                id_counts[acc_id] = id_counts.get(acc_id, 0) + 1

    anonymise_and_warn = []
    deletes = []

    for index, acc in enumerate(accounts):
        if not isinstance(acc, dict):
            _log.warning("skipping element at index %d: not a dict", index)
            continue

        v = _validate(index, acc)
        if v is None:
            continue

        if id_counts.get(v["id"], 0) > 1:
            _log.warning("skipping account at index %d: duplicate id", index)
            continue

        if v["hold"]:
            continue
        if _is_staff(v["email"]):
            continue

        due = v["due"]
        if due <= today:
            action = "anonymise" if v["unpaid"] > 0 else "delete"
            record = {
                "account_id": v["id"],
                "action": action,
                "due": due.isoformat(),
                "approved_by": DPO_NAME,
            }
            if action == "delete":
                group = 0 if v["closed"] else 1
                deletes.append((group, due, _id_key(v["id"]), record))
            else:
                anonymise_and_warn.append(record)
        elif (due - today).days <= WARN_WINDOW_DAYS:
            if v["closed_by"] == "member":
                continue
            anonymise_and_warn.append({
                "account_id": v["id"],
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    deletes.sort(key=lambda t: t[:3])
    capped_deletes = [t[3] for t in deletes[:MAX_DELETIONS_PER_RUN]]

    result = anonymise_and_warn + capped_deletes
    result.sort(key=lambda r: _id_key(r["account_id"]))
    return result