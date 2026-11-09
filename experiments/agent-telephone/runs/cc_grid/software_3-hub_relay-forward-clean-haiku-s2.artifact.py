"""GDPR clean-up planner for Tidewater Climbing member accounts.

Entry point: plan_purge(accounts, today) -> list of dicts with exactly
account_id, action, due (YYYY-MM-DD) and approved_by, sorted by account_id.

Open decisions (marked [DECIDE] in the PM spec) are named constants below,
each set to the spec's [DEFAULT]. None of them is final:
  - STAFF_EMAIL_SUFFIX / staff filter: default staff domain check.
  - SKIPPED_STATUSES: status values meaning already deleted or anonymised.
    Values are unknown, so the default skips nothing.
  - STAFF_CLOSED_TIER: delete-cap tier for staff-closed accounts (default 2).
  - DPO_APPROVER: approver name for delete and anonymise (may be None until
    approval is confirmed).
  - NONE_INVOICE_COUNT: value used when unpaid_invoices is None (default 0).
    unpaid_invoices is treated as an integer count.

Conflict with the operator house rule: the house rule asks for the account
email on every action dict. This module does not do that. The PM spec, the
original brief and the acceptance criteria all forbid email in output, and
the audit log is shared with the climbing federation. Output dicts carry
exactly the four keys. The tech lead should confirm this before release.

Interpretations to confirm:
  - Warn actions are returned for every account with due in (today, today +
    14 days], including accounts with unpaid invoices (C3). Accounts already
    due with unpaid invoices get only an anonymise action.
  - Warnings carry no wording in the output, so the "must not say deleted"
    rule cannot be violated by this module.
  - Accounts skipped for missing last_seen_at or invalid closed_by are
    recorded with logger.warning, using account_id only.
"""

import datetime
import logging

logger = logging.getLogger(__name__)

# Spec defaults for [DECIDE] items. Review before go-live.
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"
SKIPPED_STATUSES = frozenset()
STAFF_CLOSED_TIER = 2
DPO_APPROVER = "Þórdís Sveinbjörnsdóttir"
NONE_INVOICE_COUNT = 0

# Fixed spec values.
INACTIVE_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200

MEMBER_CLOSED_TIER = 1
UNCLOSED_TIER = 3


def _check_date(value, name, account_id):
    if isinstance(value, datetime.datetime) or not isinstance(value, datetime.date):
        raise TypeError(f"{name} must be datetime.date (account_id={account_id!r})")
    return value


def _is_staff(email, account_id):
    if email is None:
        return False
    if not isinstance(email, str):
        raise TypeError(f"email must be str or None (account_id={account_id!r})")
    return email.strip().lower().endswith(STAFF_EMAIL_SUFFIX)


def _unpaid_count(value, account_id):
    if value is None:
        return NONE_INVOICE_COUNT
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"unpaid_invoices must be int or None (account_id={account_id!r})")
    return value


def _tier(closed_at, closed_by):
    if closed_at is None:
        return UNCLOSED_TIER
    if closed_by == "member":
        return MEMBER_CLOSED_TIER
    return STAFF_CLOSED_TIER


def _action(account_id, action, due, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    _check_date(today, "today", None)
    accounts = list(accounts)

    seen = set()
    for acc in accounts:
        account_id = acc["id"]
        if account_id in seen:
            raise ValueError(f"duplicate account_id {account_id!r}")
        seen.add(account_id)

    results = []
    delete_candidates = []
    warn_window_end = today + datetime.timedelta(days=WARN_WINDOW_DAYS)

    for acc in accounts:
        account_id = acc["id"]
        closed_at = acc.get("closed_at")
        closed_by = acc.get("closed_by")
        last_seen_at = acc.get("last_seen_at")

        if closed_at is None:
            if closed_by is not None:
                logger.warning("skipped account_id=%s reason=closed_by without closed_at", account_id)
                continue
        elif closed_by not in ("member", "staff"):
            logger.warning("skipped account_id=%s reason=invalid closed_by", account_id)
            continue

        if last_seen_at is None:
            logger.warning("skipped account_id=%s reason=missing last_seen_at", account_id)
            continue

        _check_date(last_seen_at, "last_seen_at", account_id)
        if closed_at is not None:
            _check_date(closed_at, "closed_at", account_id)

        if _is_staff(acc.get("email"), account_id):
            continue
        if acc.get("litigation_hold"):
            continue
        if acc.get("status") in SKIPPED_STATUSES:
            continue

        unpaid = _unpaid_count(acc.get("unpaid_invoices"), account_id)

        due = last_seen_at + datetime.timedelta(days=INACTIVE_DAYS)
        if closed_at is not None:
            due = min(due, closed_at + datetime.timedelta(days=CLOSED_GRACE_DAYS))

        if due <= today:
            if unpaid > 0:
                results.append(_action(account_id, "anonymise", due, DPO_APPROVER))
            else:
                delete_candidates.append((_tier(closed_at, closed_by), due, account_id))
        elif due <= warn_window_end:
            if closed_by == "member":
                continue
            results.append(_action(account_id, "warn", due, None))

    delete_candidates.sort()
    for _tier_value, due, account_id in delete_candidates[:DELETE_CAP]:
        results.append(_action(account_id, "delete", due, DPO_APPROVER))

    results.sort(key=lambda a: a["account_id"])
    return results