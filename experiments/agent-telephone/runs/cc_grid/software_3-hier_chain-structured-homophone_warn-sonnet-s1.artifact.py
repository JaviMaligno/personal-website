# purge.py  (UTF-8)
#
# Open questions (not blocking):
#  - Cap scope for anonymise: assumed NOT capped or counted (R11).
#  - Status values are unknown; status is never consulted (R4).
#  - last_seen_at None: inactivity rule skipped; closed rule only; else no action.
#  - unpaid_invoices may be an int or a collection; truthiness is used (R7).
#  - Whether warns should go to accounts that will be anonymised: yes, as normal (R7).
#
# Deviation from R1/R10: house rule requires every action dict to carry the
# account's `email` for support follow-up, so actions have five keys, not four.
# This conflicts with R10 (no email in output) and needs client confirmation.
#
# Sorting (R14): ids are keyed on (type name, value) so mixed int/str ids
# sort deterministically without TypeError.
import datetime

MAX_DELETIONS = 200
APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 40


def _id_key(account_id):
    return (type(account_id).__name__, account_id)


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def _due(acct):
    candidates = []
    seen = acct.get("last_seen_at")  # R3: never last_login
    if seen is not None:
        candidates.append(seen + datetime.timedelta(days=INACTIVITY_DAYS))
    closed = acct.get("closed_at")  # R4: status not consulted
    if closed is not None:
        candidates.append(closed + datetime.timedelta(days=CLOSED_DAYS))
    return min(candidates) if candidates else None


def plan_purge(accounts, today):
    deletes = []  # (sort key, action)
    others = []
    horizon = today + datetime.timedelta(days=WARN_DAYS)
    for acct in accounts:
        if acct.get("litigation_hold") or _is_staff(acct.get("email")):  # R8, R9
            continue
        due = _due(acct)
        if due is None:
            continue
        aid = acct.get("id")
        closed = acct.get("closed_at") is not None
        action = {"account_id": aid, "email": acct.get("email"), "due": due.isoformat()}
        if due <= today:
            if acct.get("unpaid_invoices"):  # R7
                action.update(action="anonymise", approved_by=APPROVER)
                others.append(action)
            else:
                action.update(action="delete", approved_by=APPROVER)
                deletes.append(((0 if closed else 1, due, _id_key(aid)), action))
        elif due <= horizon:
            # R6: closed_by missing/None is treated as not "member", so warn.
            if closed and acct.get("closed_by") == "member":
                continue
            action.update(action="warn", approved_by=None)
            others.append(action)
    deletes.sort(key=lambda t: t[0])
    chosen = [a for _, a in deletes[:MAX_DELETIONS]]  # R11: deferred get nothing
    result = chosen + others
    result.sort(key=lambda a: _id_key(a["account_id"]))  # R14
    return result