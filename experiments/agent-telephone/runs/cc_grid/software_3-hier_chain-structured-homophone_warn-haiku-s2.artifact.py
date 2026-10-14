"""Tidewater Climbing GDPR clean-up planner.

plan_purge(accounts, today) is pure: output depends only on its inputs, and
the only side effect is logging. Log lines never contain email values.

Status: NOT EXECUTED. The accompanying tests were written but not run, because
no execution tool was available in this session. Run
`python -m unittest -v test_tidewater_purge` before relying on this code.

Assumptions beyond R1 to R27:
A1. Only the three date fields (last_seen_at, last_login, closed_at) are type-checked.
    Any non-None value that is not a datetime.date raises TypeError, including last_login.
A2. `today` must be a datetime.date. A datetime or other type raises TypeError.
A3. A non-string or blank email is treated as missing and skipped (R19).
A4. Accounts are processed in ascending id order, so logs are deterministic.
    Ids must be mutually comparable (all str or all int), or sorting raises TypeError.
A5. Log lines include account ids (not emails). Ids are assumed not to be email addresses.
A6. Staff and litigation-hold accounts are skipped silently, with no log line.
A7. Duplicate-id and TypeError messages do not include ids or values.
A8. An account with unpaid invoices that is due today is anonymised, not deleted (R23a).
A9. A warn-window account with unpaid invoices gets "warn", not "anonymise" (R23b).
A10. Deferred deletions are logged as a count only (R24).
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Iterable
from typing import Any

logger = logging.getLogger(__name__)

APPROVER: str = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN: str = "@tidewater-klatring.no"
INACTIVE_DAYS: int = 730
CLOSED_DAYS: int = 30
WARN_DAYS: int = 40
DELETE_CAP: int = 200
_DATE_FIELDS: tuple[str, ...] = ("last_seen_at", "last_login", "closed_at")


def _validate(accounts: list[dict[str, Any]], today: dt.date) -> None:
    """Raise ValueError for duplicate ids and TypeError for bad date types."""
    if not isinstance(today, dt.date) or isinstance(today, dt.datetime):
        raise TypeError("today must be a datetime.date")
    ids = [acc.get("id") for acc in accounts]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate account ids")
    for acc in accounts:
        for field in _DATE_FIELDS:
            value = acc.get(field)
            if value is None:
                continue
            if isinstance(value, dt.datetime):
                raise TypeError(f"{field} must be a date, not datetime")
            if not isinstance(value, dt.date):
                raise TypeError(f"{field} must be a date or None")


def _due_date(last_seen: dt.date | None, closed_at: dt.date | None) -> dt.date | None:
    """Return the earlier of the applicable deletion dates, or None if neither exists."""
    candidates: list[dt.date] = []
    if last_seen is not None:
        candidates.append(last_seen + dt.timedelta(days=INACTIVE_DAYS))
    if closed_at is not None:
        candidates.append(closed_at + dt.timedelta(days=CLOSED_DAYS))
    return min(candidates) if candidates else None


def _action(acc_id: Any, action: str, due: dt.date, approved_by: str | None) -> dict[str, Any]:
    return {
        "account_id": acc_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def _order(entry: tuple[dt.date, Any, bool]) -> tuple[dt.date, Any]:
    return (entry[0], entry[1])


def plan_purge(accounts: Iterable[dict[str, Any]], today: dt.date) -> list[dict[str, Any]]:
    """Return the GDPR purge actions for this run, sorted by account_id.

    Each action dict has exactly the keys account_id, action, due (ISO date)
    and approved_by. Deletes are capped at DELETE_CAP per run, closed accounts
    first; anonymise and warn actions are not capped.
    """
    rows = list(accounts)
    _validate(rows, today)
    rows.sort(key=lambda acc: acc.get("id"))

    horizon = today + dt.timedelta(days=WARN_DAYS)
    closed_due: list[tuple[dt.date, Any, bool]] = []
    open_due: list[tuple[dt.date, Any, bool]] = []
    warns: list[dict[str, Any]] = []

    for acc in rows:
        acc_id = acc.get("id")
        email = acc.get("email")
        if not isinstance(email, str) or not email.strip():
            logger.info("skip account %r: missing or invalid email", acc_id)
            continue
        if email.strip().lower().endswith(STAFF_DOMAIN):
            continue
        if acc.get("litigation_hold"):
            continue
        closed_at = acc.get("closed_at")
        due = _due_date(acc.get("last_seen_at"), closed_at)
        if due is None:
            logger.info("skip account %r: no last_seen_at or closed_at", acc_id)
            continue
        if due <= today:
            has_unpaid = bool(acc.get("unpaid_invoices"))
            entry = (due, acc_id, has_unpaid)
            (closed_due if closed_at is not None else open_due).append(entry)
        elif due <= horizon:
            closed_by = str(acc.get("closed_by") or "").strip().lower()
            if closed_by == "member":
                continue
            warns.append(_action(acc_id, "warn", due, None))

    actions: list[dict[str, Any]] = []
    deletes = 0
    deferred = 0
    for due, acc_id, has_unpaid in sorted(closed_due, key=_order) + sorted(open_due, key=_order):
        if has_unpaid:
            actions.append(_action(acc_id, "anonymise", due, APPROVER))
        elif deletes < DELETE_CAP:
            deletes += 1
            actions.append(_action(acc_id, "delete", due, APPROVER))
        else:
            deferred += 1
    if deferred:
        logger.info("deferred %d deletions over cap of %d", deferred, DELETE_CAP)

    actions.extend(warns)
    actions.sort(key=lambda a: a["account_id"])
    logger.info("purge plan: %d actions", len(actions))
    return actions


# ---- test_tidewater_purge.py (save as a separate file next to this module) ----
# NOT EXECUTED in this session. Expected command:
#   python -m unittest -v test_tidewater_purge
#
# import datetime as dt
# import random
# import unittest
#
# from tidewater_purge import APPROVER, plan_purge
#
# TODAY = dt.date(2026, 10, 13)
# EMAIL = "member.person@example.org"
#
#
# def ago(days: int) -> dt.date:
#     return TODAY - dt.timedelta(days=days)
#
#
# def ahead(days: int) -> dt.date:
#     return TODAY + dt.timedelta(days=days)
#
#
# def acct(id_, *, email=EMAIL, last_seen=None, closed_at=None, closed_by=None,
#          unpaid=0, hold=False, last_login=None):
#     return {
#         "id": id_, "email": email, "status": "active",
#         "last_seen_at": last_seen, "last_login": last_login,
#         "closed_at": closed_at, "closed_by": closed_by,
#         "unpaid_invoices": unpaid, "litigation_hold": hold,
#     }
#
#
# class PurgeTests(unittest.TestCase):
#
#     def test_due_today_is_delete(self):
#         out = plan_purge([acct("a", last_seen=ago(730))], TODAY)
#         self.assertEqual(out, [{"account_id": "a", "action": "delete",
#                                 "due": TODAY.isoformat(), "approved_by": APPROVER}])
#
#     def test_due_today_plus_40_warns(self):
#         out = plan_purge([acct("a", last_seen=ago(690))], TODAY)
#         self.assertEqual(out, [{"account_id": "a", "action": "warn",
#                                 "due": ahead(40).isoformat(), "approved_by": None}])
#
#     def test_due_today_plus_41_nothing(self):
#         self.assertEqual(plan_purge([acct("a", last_seen=ago(689))], TODAY), [])
#
#     def test_closed_member_inside_window_no_warn(self):
#         out = plan_purge([acct("a", last_seen=ago(100), closed_at=ago(20),
#                                closed_by="member")], TODAY)
#         self.assertEqual(out, [])
#
#     def test_closed_staff_inside_window_warns(self):
#         out = plan_purge([acct("a", last_seen=ago(100), closed_at=ago(20),
#                                closed_by="staff")], TODAY)
#         self.assertEqual(len(out), 1)
#         self.assertEqual(out[0]["action"], "warn")
#
#     def test_staff_with_any_dates_nothing(self):
#         out = plan_purge([
#             acct("a", email="ops@tidewater-klatring.no", last_seen=ago(2000)),
#             acct("b", email="ops@tidewater-klatring.no", last_seen=ago(100),
#                  closed_at=ago(20), closed_by="staff"),
#         ], TODAY)
#         self.assertEqual(out, [])
#
#     def test_litigation_hold_nothing(self):
#         self.assertEqual(plan_purge([acct("a", last_seen=ago(2000), hold=True)], TODAY), [])
#
#     def test_unpaid_due_anonymise_not_counted_toward_cap(self):
#         accts = [acct(f"d{i:03d}", last_seen=ago(730)) for i in range(201)]
#         accts += [acct(f"u{i}", last_seen=ago(730), unpaid=2) for i in range(5)]
#         out = plan_purge(accts, TODAY)
#         self.assertEqual(sum(1 for a in out if a["action"] == "delete"), 200)
#         self.assertEqual(sum(1 for a in out if a["action"] == "anonymise"), 5)
#
#     def test_unpaid_inside_window_warns_not_anonymise(self):
#         out = plan_purge([acct("a", last_seen=ago(690), unpaid=3)], TODAY)
#         self.assertEqual(out[0]["action"], "warn")
#
#     def test_201_due_deletes_cap_closed_first(self):
#         closed = [acct(f"c{i:03d}", last_seen=ago(100), closed_at=ago(30)) for i in range(120)]
#         opened = [acct(f"o{i:03d}", last_seen=ago(730)) for i in range(81)]
#         out = plan_purge(closed + opened, TODAY)
#         deletes = [a["account_id"] for a in out if a["action"] == "delete"]
#         self.assertEqual(len(deletes), 200)
#         self.assertEqual({i for i in deletes if i.startswith("c")},
#                          {f"c{i:03d}" for i in range(120)})
#         self.assertEqual(sorted(i for i in deletes if i.startswith("o")),
#                          [f"o{i:03d}" for i in range(80)])
#
#     def test_email_case_variants_are_staff(self):
#         out = plan_purge([
#             acct("a", email="A@Tidewater-Klatring.NO", last_seen=ago(2000)),
#             acct("b", email="  x@tidewater-klatring.no  ", last_seen=ago(2000)),
#             acct("c", email="b@TIDEWATER-KLATRING.no", last_seen=ago(2000)),
#             acct("d", email="x@eu.tidewater-klatring.no", last_seen=ago(2000)),
#         ], TODAY)
#         self.assertEqual([a["account_id"] for a in out], ["d"])
#
#     def test_last_login_ignored(self):
#         out = plan_purge([
#             acct("a", last_seen=TODAY, last_login=ago(5000)),
#             acct("b", last_seen=ago(730), last_login=TODAY),
#         ], TODAY)
#         self.assertEqual([(a["account_id"], a["action"]) for a in out], [("b", "delete")])
#
#     def test_closed_at_earlier_uses_closed_rule(self):
#         out = plan_purge([acct("a", last_seen=ago(700), closed_at=ago(30))], TODAY)
#         self.assertEqual(out, [{"account_id": "a", "action": "delete",
#                                 "due": TODAY.isoformat(), "approved_by": APPROVER}])
#
#     def test_missing_email_skipped(self):
#         out = plan_purge([acct("a", email="", last_seen=ago(2000)),
#                           acct("b", email=None, last_seen=ago(2000))], TODAY)
#         self.assertEqual(out, [])
#
#     def test_no_email_in_output_or_logs(self):
#         accts = [
#             acct("a", last_seen=ago(730)),
#             acct("b", last_seen=ago(690)),
#             acct("c"),
#         ]
#         with self.assertLogs(level="DEBUG") as cm:
#             out = plan_purge(accts, TODAY)
#         self.assertNotIn(EMAIL, repr(out))
#         self.assertNotIn(EMAIL, "".join(cm.output))
#
#     def test_output_identical_under_shuffle(self):
#         accts = [acct(f"x{i:03d}", last_seen=ago(700 + i % 60), closed_at=ago(i % 40),
#                       closed_by="member" if i % 3 == 0 else None,
#                       unpaid=i % 4 == 0) for i in range(120)]
#         baseline = plan_purge(accts, TODAY)
#         rng = random.Random(0)
#         for _ in range(5):
#             shuffled = list(accts)
#             rng.shuffle(shuffled)
#             self.assertEqual(plan_purge(shuffled, TODAY), baseline)
#
#     def test_duplicate_ids_raise(self):
#         with self.assertRaises(ValueError):
#             plan_purge([acct("a", last_seen=ago(1)), acct("a", last_seen=ago(1))], TODAY)
#
#     def test_datetime_field_rejected(self):
#         with self.assertRaises(TypeError):
#             plan_purge([acct("a", last_seen=dt.datetime(2020, 1, 1))], TODAY)
#
#
# if __name__ == "__main__":
#     unittest.main()
#
# ---- Test run output ----
# NOT RUN. No execution tool was available, so no output is reported.
# Results are unverified until the command above is executed.