"""Plan GDPR purge actions for Tidewater Climbing member accounts.

This module is stateless. It does not record which actions have been executed.
Callers must exclude accounts that were already processed on a previous run
before calling plan_purge, or the same actions may be repeated.

Rules:
- Inactivity is measured on last_seen_at only (730 days). last_login is never used.
- A closed account (closed_at set) is due 30 days after closure if that is earlier.
- Due accounts (due <= today) get "delete", or "anonymise" when they have unpaid invoices.
- Warnings are issued when due is after today and within 40 days, except for accounts closed by the member.
- Litigation-hold accounts get no action.
- Staff accounts (email ending in "@tidewater-klatring.no", case-insensitive) get no action.
- Cap: at most 200 "delete" actions per run. Only deletes count toward the cap. Anonymise and warn actions are never capped. Closed accounts are prioritised, then earlier due date, then lower account_id. Excess deletes are omitted and remain due for a later run.
- Output is sorted by account_id. Input is never mutated and no email address appears in any output.

Open questions for the client:
1. Should "anonymise" actions count toward the 200 cap? Anonymisation also writes to the database, but the rule only mentions deletions.
2. Re-run safety: the caller must exclude accounts already processed, otherwise actions can repeat.
3. last_login is not validated and is ignored by all rules.
4. A closed account with closed_by None is still treated as closed.
5. closed_at None with closed_by set is treated as not closed, which may be ambiguous.
6. Litigation-hold accounts are skipped before date validation, so a litigation-hold account with invalid dates produces no error.

Status: this module was written without tool access. No test file was created and no tests were run.
"""

from datetime import date, datetime, timedelta

APPROVER = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 40
DELETE_CAP = 200


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _is_staff(account):
    email = account.get("email")
    if not isinstance(email, str):
        raise ValueError(f"account {account.get('id')!r}: email must be a string")
    return email.lower().endswith(STAFF_DOMAIN)


def _has_unpaid(account):
    value = account.get("unpaid_invoices")
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value > 0
    raise ValueError(
        f"account {account.get('id')!r}: unpaid_invoices must be a count, a boolean or None"
    )


def _due_date(account):
    account_id = account.get("id")
    last_seen = account.get("last_seen_at")
    if not _is_date(last_seen):
        raise ValueError(f"account {account_id!r}: last_seen_at must be a date")
    due = last_seen + timedelta(days=INACTIVITY_DAYS)
    closed_at = account.get("closed_at")
    if closed_at is not None:
        if not _is_date(closed_at):
            raise ValueError(f"account {account_id!r}: closed_at must be a date or None")
        due = min(due, closed_at + timedelta(days=CLOSED_GRACE_DAYS))
    return due


def _action(account_id, action, due):
    approved_by = None if action == "warn" else APPROVER
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    if not _is_date(today):
        raise ValueError("today must be a datetime.date")

    warn_limit = today + timedelta(days=WARN_WINDOW_DAYS)
    others = []
    deletes = []

    for account in accounts:
        if _is_staff(account):
            continue
        if bool(account.get("litigation_hold")):
            continue

        account_id = account.get("id")
        due = _due_date(account)
        unpaid = _has_unpaid(account)

        if due <= today:
            if unpaid:
                others.append(_action(account_id, "anonymise", due))
            else:
                closed_rank = 0 if account.get("closed_at") is not None else 1
                deletes.append((closed_rank, due, account_id))
        elif due <= warn_limit and account.get("closed_by") != "member":
            others.append(_action(account_id, "warn", due))

    deletes.sort()
    actions = others
    for _closed_rank, due, account_id in deletes[:DELETE_CAP]:
        actions.append(_action(account_id, "delete", due))

    actions.sort(key=lambda item: item["account_id"])
    return actions