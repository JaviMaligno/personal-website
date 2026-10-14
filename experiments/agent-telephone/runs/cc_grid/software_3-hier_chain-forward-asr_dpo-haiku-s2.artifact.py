"""
Tidewater Climbing GDPR purge planner.

Entry point: plan_purge(accounts, today) -> list of action dicts sorted by account_id.

FLAG decisions for PM (defaults implemented):
- FLAG A: a missing, None, empty, or non-string email raises ValueError. The staff check cannot run, so the run fails closed.
- FLAG B: duplicate account ids raise ValueError.
- FLAG C: an anonymised account that is still due and unpaid gets anonymise again on every run. The spec does not say when this stops, so the rule applies unchanged each run.
- FLAG D: mixed int and str account ids are not normalised. The TypeError from sorting propagates naturally.

Additional decisions (not FLAGged, for review):
- closed_by None with closed_at set is accepted and is not treated as "member", so warn is allowed.
- Negative unpaid_invoices raises ValueError. Otherwise it would be treated as zero and deleted.
- Email is stripped and lowercased before the staff-domain check, so trailing whitespace cannot bypass the staff exclusion.
- Date arithmetic can raise OverflowError near date.max. This is left as a fail-closed error.

Verification by reasoning (today = 2026-10-13 unless stated):
1. Inactive delete at exactly today. last_seen_at 2024-10-13 gives due 2026-10-13 = today, unpaid 0, so delete with due "2026-10-13".
2. Closed delete beats later inactivity. closed_at 2026-09-13 gives closed due 2026-10-13. last_seen_at 2024-10-20 gives inactive due 2026-10-20. min is 2026-10-13, so delete with due "2026-10-13".
3. Unpaid anonymise. last_seen_at 2024-10-13, unpaid 3, so anonymise with due "2026-10-13" and approver set.
4. Warn at today+1. last_seen_at 2024-10-14 gives due 2026-10-14, so warn with due "2026-10-14" and approved_by None.
5. Warn at today+14 inclusive. last_seen_at 2024-10-27 gives due 2026-10-27, so warn.
6. No warn at today+15. last_seen_at 2024-10-28 gives due 2026-10-28, so no action.
7. Due today is never a warn. Case 1 gives delete, not warn.
8. No warn for member-closed. closed_at 2026-09-20 gives due 2026-10-20 (today+7). closed_by "member" blocks warn, so no action.
9. Staff-closed warn. Same dates with closed_by "staff" gives warn with due "2026-10-20".
10. Staff email in mixed case. "Ada.Lovelace@Tidewater-Klatring.NO" is lowercased and excluded, so no action even when due today. Trailing whitespace is also stripped before the check.
11. Litigation hold with due and unpaid. Excluded before due logic, so no action.
12. 201 due deletes, 100 closed and 101 inactive, all due today. Sorted closed first, then due asc, then id asc. The first 200 get delete. The 201st (the inactive account with the latest due and largest id) gets no action. It is not anonymised or warned, even if it has unpaid invoices, because unpaid accounts are routed to anonymise before the cap.
13. Output ordering. Accounts with ids 3, 1, 2 are returned in order 1, 2, 3.
14. Leap-year arithmetic. last_seen_at 2024-02-29 plus 730 days gives 2026-02-28, because 2024-02-29 plus 365 is 2025-02-28 and that plus 365 is 2026-02-28. With today 2026-02-28 this is a delete.
15. last_seen_at None raises ValueError before any action is produced. Validation runs over all accounts first, so one bad record fails the whole run.
16. Non-date today (including datetime) raises TypeError.

Remaining concerns:
- FLAG C is open. Anonymised accounts will be re-anonymised every run until the PM sets a stop condition.
- Cap deferrals are silent. The 201st+ account gets no action and no log entry. Ops may want a count of deferred accounts.
"""

from collections.abc import Mapping
from datetime import date, datetime, timedelta

STAFF_DOMAIN = "@tidewater-klatring.no"
APPROVER = "Tordis Svenbjorn Dottir"
INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
DELETE_CAP = 200
REQUIRED_KEYS = (
    "id",
    "email",
    "last_seen_at",
    "closed_at",
    "closed_by",
    "unpaid_invoices",
    "litigation_hold",
)


def _check_date(value, field):
    if isinstance(value, datetime) or not isinstance(value, date):
        raise TypeError(f"{field} must be datetime.date")


def _validate(accounts):
    seen = set()
    for index, acc in enumerate(accounts):
        if not isinstance(acc, Mapping):
            raise TypeError(f"account at position {index} is not a mapping")
        for key in REQUIRED_KEYS:
            if key not in acc:
                raise ValueError(f"account at position {index} missing field {key}")

        acc_id = acc["id"]
        if acc_id in seen:
            raise ValueError("duplicate account id")
        seen.add(acc_id)

        email = acc["email"]
        if not isinstance(email, str) or not email.strip():
            raise ValueError(f"account at position {index} has missing or invalid email")

        if acc["last_seen_at"] is None:
            raise ValueError(f"account at position {index} has last_seen_at None")
        _check_date(acc["last_seen_at"], "last_seen_at")

        closed_at = acc["closed_at"]
        if closed_at is not None:
            _check_date(closed_at, "closed_at")
            if acc["closed_by"] not in (None, "member", "staff"):
                raise ValueError(f"account at position {index} has invalid closed_by")

        unpaid = acc["unpaid_invoices"]
        if not isinstance(unpaid, int) or isinstance(unpaid, bool):
            raise TypeError(f"account at position {index} unpaid_invoices must be int")
        if unpaid < 0:
            raise ValueError(f"account at position {index} unpaid_invoices is negative")

        if not isinstance(acc["litigation_hold"], bool):
            raise TypeError(f"account at position {index} litigation_hold must be bool")


def _action(acc_id, action, due, approved_by):
    return {
        "account_id": acc_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    if isinstance(today, datetime) or not isinstance(today, date):
        raise TypeError("today must be datetime.date")

    accounts = list(accounts)
    _validate(accounts)

    warn_horizon = today + timedelta(days=WARN_DAYS)
    actions = []
    deletes = []

    for acc in accounts:
        if acc["email"].strip().lower().endswith(STAFF_DOMAIN):
            continue
        if acc["litigation_hold"]:
            continue

        closed_at = acc["closed_at"]
        due = acc["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=CLOSED_DAYS))

        acc_id = acc["id"]
        if due <= today:
            if acc["unpaid_invoices"] == 0:
                group = 0 if closed_at is not None else 1
                deletes.append((group, due, acc_id))
            else:
                actions.append(_action(acc_id, "anonymise", due, APPROVER))
        elif due <= warn_horizon and acc["closed_by"] != "member":
            actions.append(_action(acc_id, "warn", due, None))

    deletes.sort(key=lambda d: (d[0], d[1], d[2]))
    for _, due, acc_id in deletes[:DELETE_CAP]:
        actions.append(_action(acc_id, "delete", due, APPROVER))

    actions.sort(key=lambda a: a["account_id"])
    return actions