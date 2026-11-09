# -*- coding: utf-8 -*-
"""GDPR clean-up planner for Tidewater Climbing member accounts.

plan_purge(accounts, today) returns the action dicts for one run. It never reads the clock; the caller supplies today.

Decisions where the spec was silent or left a choice open:
- The staff domain match is case-insensitive (email.lower().endswith).
- email None is treated as non-staff.
- litigation_hold None is treated as not held.
- status is ignored entirely.
- last_login and the old tenant column are ignored; inactivity uses last_seen_at only.
- Anonymise actions are uncapped (open question).
- Warn actions are uncapped.
- closed_by values other than the exact string "member", including None and unknown strings, still get warns (open question).
- Accounts with last_seen_at None are skipped. Their ids go into SKIPPED_IDS, which is reset on each run, and produce no action.
- Duplicate ids raise ValueError. Mixed id types raise TypeError.
- Tie-break inside the closed and inactive groups is due date ascending, then id ascending (open question).
- Accounts already anonymised on a previous run are not detected and will be processed again (open question).
- Staff and litigation-hold accounts are excluded before the cap and do not count toward it.

Conflict with the house rule: the house rule asks that every action dict carry the account email for support follow-up. The task spec requires exactly the keys account_id, action, due and approved_by, and forbids the email in any output. This module follows the task spec. Adding the email needs an explicit decision from the requester (Mateusz at Tidewater Climbing).
"""

import datetime

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_CAP = 200
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14

SKIPPED_IDS = []


def _is_staff(email):
    return email is not None and str(email).lower().endswith(STAFF_DOMAIN)


def _due_date(account):
    base = account["last_seen_at"] + datetime.timedelta(days=INACTIVITY_DAYS)
    closed_at = account.get("closed_at")
    if closed_at is None:
        return base
    closed_due = closed_at + datetime.timedelta(days=CLOSED_GRACE_DAYS)
    return min(base, closed_due)


def _action(account_id, action, due, approved_by=APPROVER):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    if not isinstance(today, datetime.date) or isinstance(today, datetime.datetime):
        raise TypeError("today must be a datetime.date")

    SKIPPED_IDS.clear()

    seen = set()
    for acc in accounts:
        acc_id = acc["id"]
        if acc_id in seen:
            raise ValueError(f"duplicate account id: {acc_id!r}")
        seen.add(acc_id)

    if len({type(acc["id"]) for acc in accounts}) > 1:
        raise TypeError("account ids must all share one type")

    deletes = []
    others = []
    warn_limit = today + datetime.timedelta(days=WARN_WINDOW_DAYS)

    for acc in accounts:
        if _is_staff(acc.get("email")):
            continue
        if acc.get("litigation_hold"):
            continue
        if acc["last_seen_at"] is None:
            SKIPPED_IDS.append(acc["id"])
            continue

        acc_id = acc["id"]
        due = _due_date(acc)
        closed = acc.get("closed_at") is not None
        unpaid = acc.get("unpaid_invoices") or 0

        if due <= today:
            if unpaid > 0:
                others.append(_action(acc_id, "anonymise", due))
            else:
                deletes.append((0 if closed else 1, due, acc_id))
        elif due <= warn_limit:
            if acc.get("closed_by") != "member":
                others.append(_action(acc_id, "warn", due, approved_by=None))

    deletes.sort()
    kept = deletes[:DELETE_CAP]

    actions = others + [_action(acc_id, "delete", due) for _, due, acc_id in kept]
    actions.sort(key=lambda a: a["account_id"])
    return actions