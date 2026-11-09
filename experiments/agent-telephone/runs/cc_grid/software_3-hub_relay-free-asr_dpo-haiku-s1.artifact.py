"""Pure planning of account purge actions for Tidewater Climbing.

plan_purge(accounts, today) returns a list of action dicts sorted by account_id.
It writes, deletes and sends nothing. plan_purge_with_stats returns the same
actions plus a stats dict (including the deferred count and data problems).

Client rules:
- Inactivity due date is last_seen_at + 730 days. If closed_at is set, the closed
  due date is closed_at + 30 days. The account's due date is the earlier of the two.
- due <= today: delete, or anonymise if unpaid_invoices > 0.
- today < due <= today + 14: warn, unless closed_by == "member".
- litigation_hold true: no action. Staff email domain: no action.
- At most 200 deletes per run. Closed accounts first, then earlier due date, then
  account_id. Anonymise and warn are not capped.
- Output has exactly account_id, action, due (ISO string) and approved_by.
  approved_by is the DPO for delete and anonymise, and None for warn.
  Output is sorted by account_id.

Product manager decisions:
- One action per account. Order: hold, staff, due action, warn.
- Staff domain match is case-insensitive.
- closed_by "member" with closed_at None: treated as not closed (no closed due date,
  no warn exemption). Logged as an anomaly.
- closed_at set with closed_by None or other: closed due date applies, warn exemption does not.
- last_seen_at None or not a date, unpaid_invoices None or not a non-negative int,
  litigation_hold not a bool, or email not text: error. The account gets no action
  and is listed in stats["errors"].
- Future last_seen_at or closed_at: no special handling beyond the due rules.
  Logged as an anomaly.
- Duplicate account ids, and today not a plain datetime.date (datetime is rejected
  too): whole run rejected.
- All offsets use timedelta, so leap years are handled by real day counts.
- Warnings are stateless and repeat daily while an account stays in the window.

Privacy: output, stats, log lines and error messages never contain an account email.
They refer to accounts by account_id only.

House rule conflict: the team house rule asks that every action dict carry the
account email so support can follow up. The client requirement (exactly four keys,
no email in output, audit log shared with the climbing federation) takes precedence,
so the email is omitted. Support can look up the member by account_id.

Open questions for the client and DPO (not blocking):
1. A closed account with unpaid invoices: anonymise or delete?
2. Should the 200 cap also cover anonymise actions?
3. Should warnings be sent for accounts that will be anonymised? The notice would
   say deletion, which is inaccurate.
4. approved_by is a hard-coded name. The code cannot verify that approval happened.
5. How are already anonymised or deleted accounts excluded on later runs? No input
   field marks them.
6. Does status mean anything? It is currently ignored.
7. Should bad records fail the run, or be skipped and reported? Currently skipped
   and reported in stats["errors"].
8. Warn timing: with due = last_seen_at + 730 days, a member closed on day 0 gets
   deleted on day 30. Their warn is suppressed, so no notice precedes that deletion.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, NamedTuple

__all__ = ["plan_purge", "plan_purge_with_stats", "PurgeInputError"]

LOG = logging.getLogger(__name__)

INACTIVITY_PERIOD = timedelta(days=730)
CLOSED_GRACE_PERIOD = timedelta(days=30)
WARN_WINDOW = timedelta(days=14)
DELETE_CAP = 200
DPO_APPROVER = "Tordis Svenbjorn Dottir"
STAFF_DOMAIN = "@tidewater-klatring.no"


class PurgeInputError(ValueError):
    """Raised when the whole run must be rejected."""


class _Candidate(NamedTuple):
    account_id: int | str
    action: str
    due: date
    closed: bool


class _Problems:
    """Collects per-account errors and anomalies. Never records emails."""

    def __init__(self) -> None:
        self.errors: list[dict[str, Any]] = []
        self.anomalies: list[dict[str, Any]] = []

    def error(self, account_id: int | str, reason: str) -> None:
        self.errors.append({"account_id": account_id, "reason": reason})
        LOG.error("account %s rejected: %s", account_id, reason)

    def anomaly(self, account_id: int | str, reason: str) -> None:
        self.anomalies.append({"account_id": account_id, "reason": reason})
        LOG.warning("account %s anomaly: %s", account_id, reason)


def _is_plain_date(value: object) -> bool:
    """True for datetime.date but not for datetime.datetime."""
    return isinstance(value, date) and not isinstance(value, datetime)


def _id_key(account_id: int | str) -> tuple[int, Any]:
    """Total ordering over mixed int and str ids: ints first, then strings."""
    return (0, account_id) if type(account_id) is int else (1, str(account_id))


def _check_records(records: list[Any]) -> None:
    """Reject the run on structural problems. Messages carry no record contents."""
    first_seen: dict[Any, int] = {}
    for index, acct in enumerate(records):
        if not isinstance(acct, dict):
            raise PurgeInputError(f"record {index} is not a dict")
        if "id" not in acct:
            raise PurgeInputError(f"record {index} has no id")
        account_id = acct["id"]
        if type(account_id) not in (int, str):
            raise PurgeInputError(f"record {index} id must be int or str")
        if account_id in first_seen:
            raise PurgeInputError(
                f"duplicate account id at records {first_seen[account_id]} and {index}"
            )
        first_seen[account_id] = index


def _evaluate(acct: dict[str, Any], today: date, problems: _Problems) -> _Candidate | None:
    """Apply the rules to one validated account. Returns at most one candidate."""
    account_id = acct["id"]

    # 1. Litigation hold: no action of any kind.
    hold = acct.get("litigation_hold")
    if not isinstance(hold, bool):
        problems.error(account_id, "litigation_hold must be a bool")
        return None
    if hold:
        return None

    # 2. Staff accounts: no action of any kind.
    email = acct.get("email")
    if not isinstance(email, str):
        problems.error(account_id, "email missing or not text")
        return None
    if email.strip().lower().endswith(STAFF_DOMAIN):
        return None

    # 3. Data validation. Failures are errors, never silently treated as zero or as not due.
    last_seen = acct.get("last_seen_at")
    if not _is_plain_date(last_seen):
        problems.error(account_id, "last_seen_at missing or not a date")
        return None

    closed_at = acct.get("closed_at")
    if closed_at is not None and not _is_plain_date(closed_at):
        problems.error(account_id, "closed_at is not a date or None")
        return None
    closed_by = acct.get("closed_by")

    unpaid = acct.get("unpaid_invoices")
    if type(unpaid) is not int or unpaid < 0:
        problems.error(account_id, "unpaid_invoices must be a non-negative int")
        return None

    # 4. Anomalies that do not stop processing.
    if last_seen > today:
        problems.anomaly(account_id, "last_seen_at is in the future")
    if closed_at is not None and closed_at > today:
        problems.anomaly(account_id, "closed_at is in the future")
    if closed_at is None and closed_by == "member":
        problems.anomaly(account_id, "closed_by is member but closed_at is missing")
    if closed_at is not None and closed_by not in ("member", "staff"):
        problems.anomaly(account_id, "closed_at set but closed_by is not member or staff")

    # 5. Due date: the earlier of inactivity and closed-grace deadlines.
    try:
        due = last_seen + INACTIVITY_PERIOD
        if closed_at is not None:
            due = min(due, closed_at + CLOSED_GRACE_PERIOD)
        window_end = today + WARN_WINDOW
    except OverflowError:
        problems.error(account_id, "date arithmetic out of range")
        return None

    closed = closed_at is not None
    member_closed = closed and closed_by == "member"

    # 6. Due action, then warning. Each account gets at most one action.
    if due <= today:
        action = "anonymise" if unpaid > 0 else "delete"
        return _Candidate(account_id, action, due, closed)
    if due <= window_end and not member_closed:
        return _Candidate(account_id, "warn", due, closed)
    return None


def plan_purge_with_stats(
    accounts: Any, today: date
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return (actions, stats) for one run.

    stats keys: delete, anonymise, warn (planned counts), deferred (deletes cut by
    the cap), errors and anomalies (lists of {"account_id", "reason"}).
    Raises TypeError if today is not a plain date, and PurgeInputError on
    duplicate ids or malformed records.
    """
    if not _is_plain_date(today):
        raise TypeError("today must be a datetime.date (datetime is not accepted)")

    records = list(accounts)
    _check_records(records)

    problems = _Problems()
    planned: list[_Candidate] = []
    deletes: list[_Candidate] = []
    for acct in records:
        cand = _evaluate(acct, today, problems)
        if cand is None:
            continue
        if cand.action == "delete":
            deletes.append(cand)
        else:
            planned.append(cand)

    # Cap: closed first, then earlier due date, then account_id.
    deletes.sort(key=lambda c: (not c.closed, c.due, _id_key(c.account_id)))
    selected = deletes[:DELETE_CAP]
    deferred = deletes[DELETE_CAP:]
    if deferred:
        LOG.warning("delete cap of %d reached: %d deletions deferred", DELETE_CAP, len(deferred))

    planned.extend(selected)
    planned.sort(key=lambda c: _id_key(c.account_id))

    actions = [
        {
            "account_id": c.account_id,
            "action": c.action,
            "due": c.due.isoformat(),
            "approved_by": None if c.action == "warn" else DPO_APPROVER,
        }
        for c in planned
    ]

    counts = {"delete": 0, "anonymise": 0, "warn": 0}
    for c in planned:
        counts[c.action] += 1

    stats: dict[str, Any] = {
        **counts,
        "deferred": len(deferred),
        "errors": problems.errors,
        "anomalies": problems.anomalies,
    }
    return actions, stats


def plan_purge(accounts: Any, today: date) -> list[dict[str, Any]]:
    """Return the sorted action list for one run. See plan_purge_with_stats."""
    actions, _stats = plan_purge_with_stats(accounts, today)
    return actions


# ---------------------------------------------------------------------------
# Tests (standard library unittest). Run with: python3 -I <this file>
# ---------------------------------------------------------------------------

import json
import random
import unittest

TODAY = date(2026, 10, 13)


def make(account_id: int | str = 1, **overrides: Any) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "id": account_id,
        "email": f"member{account_id}@example.org",
        "status": "active",
        "last_seen_at": TODAY - timedelta(days=100),
        "last_login": None,
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
        "tenant": "legacy",
    }
    rec.update(overrides)
    return rec


def days_ago(n: int) -> date:
    return TODAY - timedelta(days=n)


class PlanPurgeTests(unittest.TestCase):
    # AC1
    def test_ac1_exactly_730_days_inactive_deletes_today(self):
        actions = plan_purge([make(1, last_seen_at=days_ago(730))], TODAY)
        self.assertEqual(
            actions,
            [{"account_id": 1, "action": "delete", "due": "2026-10-13", "approved_by": DPO_APPROVER}],
        )

    # AC2
    def test_ac2_729_days_inactive_warns_tomorrow(self):
        actions = plan_purge([make(2, last_seen_at=days_ago(729))], TODAY)
        self.assertEqual(
            actions,
            [{"account_id": 2, "action": "warn", "due": "2026-10-14", "approved_by": None}],
        )

    def test_ac2_member_closed_is_not_warned(self):
        acc = make(3, last_seen_at=days_ago(729), closed_at=days_ago(10), closed_by="member")
        self.assertEqual(plan_purge([acc], TODAY), [])

    # AC3
    def test_ac3_staff_closed_30_days_ago_deletes(self):
        acc = make(4, last_seen_at=days_ago(100), closed_at=days_ago(30), closed_by="staff")
        actions = plan_purge([acc], TODAY)
        self.assertEqual(
            actions,
            [{"account_id": 4, "action": "delete", "due": "2026-10-13", "approved_by": DPO_APPROVER}],
        )

    # AC4
    def test_ac4_member_closed_10_days_ago_no_action(self):
        acc = make(5, last_seen_at=days_ago(100), closed_at=days_ago(10), closed_by="member")
        self.assertEqual(plan_purge([acc], TODAY), [])

    # AC5
    def test_ac5_staff_closed_10_days_ago_no_action(self):
        # closed_at + 30 days = (today - 10) + 30 = today + 20, outside the 14-day window.
        self.assertEqual(days_ago(10) + timedelta(days=30), date(2026, 11, 2))
        acc = make(6, last_seen_at=days_ago(100), closed_at=days_ago(10), closed_by="staff")
        self.assertEqual(plan_purge([acc], TODAY), [])

    # AC6
    def test_ac6_unpaid_invoices_anonymise_with_same_due(self):
        acc = make(7, last_seen_at=days_ago(730), unpaid_invoices=2)
        actions = plan_purge([acc], TODAY)
        self.assertEqual(
            actions,
            [{"account_id": 7, "action": "anonymise", "due": "2026-10-13", "approved_by": DPO_APPROVER}],
        )

    def test_ac6_closed_unpaid_invoices_anonymise(self):
        acc = make(8, closed_at=days_ago(30), closed_by="staff", unpaid_invoices=1)
        actions = plan_purge([acc], TODAY)
        self.assertEqual(actions[0]["action"], "anonymise")
        self.assertEqual(actions[0]["due"], "2026-10-13")

    # AC7
    def test_ac7_litigation_hold_no_action_even_when_past_due(self):
        acc = make(9, last_seen_at=days_ago(3000), litigation_hold=True)
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_hold_suppresses_warn_too(self):
        acc = make(10, last_seen_at=days_ago(729), litigation_hold=True)
        self.assertEqual(plan_purge([acc], TODAY), [])

    # AC8
    def test_ac8_staff_domain_no_action_case_insensitive(self):
        acc = make(11, email="Ops.Lead@Tidewater-Klatring.NO", last_seen_at=days_ago(3000))
        self.assertEqual(plan_purge([acc], TODAY), [])

    # AC9
    def test_ac9_due_exactly_today_plus_14_warns(self):
        acc = make(12, last_seen_at=TODAY + timedelta(days=14) - INACTIVITY_PERIOD)
        actions = plan_purge([acc], TODAY)
        self.assertEqual(actions, [{"account_id": 12, "action": "warn", "due": "2026-10-27", "approved_by": None}])

    def test_ac9_due_today_plus_15_no_action(self):
        acc = make(13, last_seen_at=TODAY + timedelta(days=15) - INACTIVITY_PERIOD)
        self.assertEqual(plan_purge([acc], TODAY), [])

    # AC10
    def test_ac10_cap_closed_first_and_deferred_count(self):
        accounts = []
        for j in range(120):
            accounts.append(make(f"c{j:03d}", last_seen_at=days_ago(100),
                                 closed_at=days_ago(30), closed_by="staff"))
        for j in range(130):
            # due = today - j, so larger j means earlier due.
            accounts.append(make(f"i{j:03d}", last_seen_at=days_ago(730 + j)))

        actions, stats = plan_purge_with_stats(accounts, TODAY)
        deletes = {a["account_id"] for a in actions if a["action"] == "delete"}
        closed_ids = {f"c{j:03d}" for j in range(120)}
        expected_inactive = {f"i{j:03d}" for j in range(50, 130)}

        self.assertEqual(len(deletes), 200)
        self.assertTrue(closed_ids <= deletes)
        self.assertEqual(deletes - closed_ids, expected_inactive)
        self.assertEqual(stats["deferred"], 50)
        self.assertEqual(stats["delete"], 200)

    def test_anonymise_not_capped(self):
        accounts = [make(i, last_seen_at=days_ago(730), unpaid_invoices=1) for i in range(250)]
        actions, stats = plan_purge_with_stats(accounts, TODAY)
        self.assertEqual(len(actions), 250)
        self.assertTrue(all(a["action"] == "anonymise" for a in actions))
        self.assertEqual(stats["deferred"], 0)

    def test_warn_not_capped(self):
        accounts = [make(i, last_seen_at=days_ago(729)) for i in range(250)]
        actions, _ = plan_purge_with_stats(accounts, TODAY)
        self.assertEqual(len(actions), 250)
        self.assertTrue(all(a["action"] == "warn" for a in actions))

    # AC11
    def test_ac11_sorted_by_id_and_deterministic(self):
        accounts = [make(i, last_seen_at=days_ago(730)) for i in (5, 3, 9, 1)]
        shuffled = list(accounts)
        random.Random(7).shuffle(shuffled)
        first = plan_purge(accounts, TODAY)
        self.assertEqual([a["account_id"] for a in first], [1, 3, 5, 9])
        self.assertEqual(first, plan_purge(shuffled, TODAY))
        self.assertEqual(first, plan_purge(accounts, TODAY))

    # AC12
    def test_ac12_output_shape_and_due_is_iso_string(self):
        actions = plan_purge(
            [make(1, last_seen_at=days_ago(730)), make(2, last_seen_at=days_ago(729))], TODAY
        )
        for a in actions:
            self.assertEqual(set(a), {"account_id", "action", "due", "approved_by"})
            self.assertIsInstance(a["due"], str)
        warn = [a for a in actions if a["action"] == "warn"]
        self.assertEqual(len(warn), 1)
        self.assertIsNone(warn[0]["approved_by"])

    # AC13
    def test_ac13_no_email_in_output_stats_or_logs(self):
        secret = "secret.person@example.org"
        accounts = [
            make(1, email=secret, last_seen_at=days_ago(730)),
            make(2, email=secret, last_seen_at=None),
            make(3, email=secret, unpaid_invoices=None, last_seen_at=days_ago(730)),
            make(4, email=secret, closed_at=days_ago(5), closed_by="member",
                 last_seen_at=TODAY + timedelta(days=3)),
        ]
        with self.assertLogs(LOG, level="WARNING") as captured:
            actions, stats = plan_purge_with_stats(accounts, TODAY)
        blob = json.dumps({"actions": actions, "stats": stats}, default=str)
        self.assertNotIn(secret, blob)
        self.assertNotIn(secret, "\n".join(captured.output))

    # AC14
    def test_ac14_empty_input_returns_empty_list(self):
        self.assertEqual(plan_purge([], TODAY), [])

    # Edge cases
    def test_none_last_seen_is_reported_error_not_action(self):
        actions, stats = plan_purge_with_stats([make(1, last_seen_at=None)], TODAY)
        self.assertEqual(actions, [])
        self.assertEqual([e["account_id"] for e in stats["errors"]], [1])

    def test_none_unpaid_invoices_is_error_not_zero(self):
        acc = make(2, last_seen_at=days_ago(730), unpaid_invoices=None)
        actions, stats = plan_purge_with_stats([acc], TODAY)
        self.assertEqual(actions, [])
        self.assertEqual([e["account_id"] for e in stats["errors"]], [2])

    def test_duplicate_ids_reject_whole_run(self):
        with self.assertRaises(PurgeInputError):
            plan_purge([make(1), make(1)], TODAY)
        self.assertTrue(issubclass(PurgeInputError, ValueError))

    def test_today_must_be_plain_date(self):
        with self.assertRaises(TypeError):
            plan_purge([], datetime(2026, 10, 13))
        with self.assertRaises(TypeError):
            plan_purge([], "2026-10-13")

    def test_leap_year_arithmetic_uses_real_days(self):
        self.assertEqual(date(2024, 2, 29) + INACTIVITY_PERIOD, date(2026, 2, 28))
        acc = make(1, last_seen_at=date(2024, 2, 29))
        self.assertEqual(
            plan_purge([acc], date(2026, 2, 28)),
            [{"account_id": 1, "action": "delete", "due": "2026-02-28", "approved_by": DPO_APPROVER}],
        )
        self.assertEqual(
            plan_purge([acc], date(2026, 2, 27)),
            [{"account_id": 1, "action": "warn", "due": "2026-02-28", "approved_by": None}],
        )

    def test_closed_member_without_closed_at_flagged_and_not_exempt(self):
        acc = make(1, last_seen_at=days_ago(729), closed_by="member", closed_at=None)
        actions, stats = plan_purge_with_stats([acc], TODAY)
        self.assertEqual([a["action"] for a in actions], ["warn"])
        self.assertEqual(len(stats["anomalies"]), 1)

    def test_closed_at_without_member_closer_has_no_warn_exemption(self):
        acc = make(2, last_seen_at=days_ago(729), closed_at=days_ago(10), closed_by=None)
        actions = plan_purge([acc], TODAY)
        self.assertEqual(actions, [{"account_id": 2, "action": "warn", "due": "2026-10-14", "approved_by": None}])

    def test_future_last_seen_no_action_and_anomaly(self):
        actions, stats = plan_purge_with_stats([make(3, last_seen_at=TODAY + timedelta(days=1))], TODAY)
        self.assertEqual(actions, [])
        self.assertEqual(len(stats["anomalies"]), 1)


if __name__ == "__main__":
    unittest.main()