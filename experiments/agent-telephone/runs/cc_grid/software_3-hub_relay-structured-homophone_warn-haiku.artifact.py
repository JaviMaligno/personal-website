# Tidewater Climbing GDPR purge planner. Stateless: returns planned actions only.
#
# Status: no tests were written or run in this turn (no execution tools available).
#
# OPEN items, implemented on the stated default:
#   O1  The 200 cap applies to deletes only. Anonymise is uncapped.
#   O8  "Closed" for R12 means closed_at is set, regardless of closed_by.
#   O9  Idempotency across runs is NOT handled. No state is kept. Repeat runs re-plan the same actions.
#   O13 STAFF_EMAIL_SUFFIX is used as given. Confirm it, since it may differ from the brand name.
#
# PROPOSED items, implemented on the stated default:
#   O2  Unpaid-invoice accounts in the warn window still get a warn. No extra field.
#   O3  Delete/anonymise: due <= today. Warn: today < due <= today + 40 days.
#   O4  `due` is always the account's R5 due date.
#   O5  `status` is not used.
#   O6  Over-cap deletion candidates get no action this run.
#   O7  Within each R12 group: due ascending, then account_id ascending.
#   O10 Warn is emitted on every run in the window. Deduplication is the sender's job.
#   O11 Fail loud: ValueError on a missing/invalid last_seen_at, a non-string email, or a bad closed_by.
#   O12 APPROVER is a fixed attribution. Per-run approval is outside this module.
#   O14 Warn output has only account_id, action, due, approved_by. No notice lookup or delivery.
#
# Ambiguity: closed_by may be None only when closed_at is None (open account). Any other
# value outside ("member", "staff") raises.

import datetime as _dt

STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"  # OPEN O13: confirm before go-live
APPROVER = "Þórdís Sveinbjörnsdóttir"  # O12: fixed DPO attribution
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 40
DELETE_CAP = 200
_CLOSED_BY_VALUES = ("member", "staff")


def _check_date(value, field, account_id):
    if not isinstance(value, _dt.date) or isinstance(value, _dt.datetime):
        raise ValueError(f"account {account_id!r}: {field} must be datetime.date, got {value!r}")


def _validate(acc):
    aid = acc["id"]
    if not isinstance(acc["email"], str):
        raise ValueError(f"account {aid!r}: email is missing or not a string")
    _check_date(acc["last_seen_at"], "last_seen_at", aid)
    closed_at = acc["closed_at"]
    closed_by = acc["closed_by"]
    if closed_at is not None:
        _check_date(closed_at, "closed_at", aid)
    if closed_by not in _CLOSED_BY_VALUES and not (closed_at is None and closed_by is None):
        raise ValueError(f"account {aid!r}: closed_by must be 'member' or 'staff', got {closed_by!r}")


def _is_staff(email):
    return email.lower().endswith(STAFF_EMAIL_SUFFIX.lower())


def _due_date(acc):
    dues = [acc["last_seen_at"] + _dt.timedelta(days=INACTIVITY_DAYS)]
    if acc["closed_at"] is not None:
        dues.append(acc["closed_at"] + _dt.timedelta(days=CLOSED_GRACE_DAYS))
    return min(dues)


def _action(account_id, action, due, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    if not isinstance(today, _dt.date) or isinstance(today, _dt.datetime):
        raise ValueError("today must be datetime.date")
    for acc in accounts:
        _validate(acc)

    warn_end = today + _dt.timedelta(days=WARN_WINDOW_DAYS)
    delete_candidates = []
    anonymise_actions = []
    warn_actions = []

    for acc in accounts:
        if acc["litigation_hold"] or _is_staff(acc["email"]):
            continue
        due = _due_date(acc)
        if due <= today:
            if acc["unpaid_invoices"]:
                anonymise_actions.append(_action(acc["id"], "anonymise", due, APPROVER))
            else:
                delete_candidates.append((acc, due))
        elif due <= warn_end and acc["closed_by"] != "member":
            warn_actions.append(_action(acc["id"], "warn", due, None))

    # R12/O7: closed accounts first, then by due date, then account_id.
    delete_candidates.sort(key=lambda p: (p[0]["closed_at"] is None, p[1], p[0]["id"]))
    delete_actions = [
        _action(acc["id"], "delete", due, APPROVER)
        for acc, due in delete_candidates[:DELETE_CAP]
    ]

    actions = delete_actions + anonymise_actions + warn_actions
    actions.sort(key=lambda a: a["account_id"])
    return actions