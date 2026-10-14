# Note: no tools were available, so the files below are not written to disk and the tests have not been run. The first block is purge_plan.py. The second block, after the separator comment, is test_purge_plan.py.
# -*- coding: utf-8 -*-
"""Tidewater Climbing GDPR clean-up planner.

plan_purge(accounts, today) returns a list of action dicts, one per decided
account, sorted by account_id ascending. Each action has exactly the keys
"account_id", "action", "due" (ISO 8601 date string) and "approved_by".
No member email or other personal field is ever included in an action.

Decisions (documented defaults):
- Due date: last_seen_at + 730 days. If closed_at is set, due is the earlier
  of that and closed_at + 30 days. last_login, the old tenant column and
  status are never read.
- Boundary: due == today counts as due (inclusive, due <= today).
- Warn window: today < due <= today + 14 days. Warn actions have
  approved_by None.
- Unpaid invoices do not suppress warnings by default
  (WARN_WHEN_UNPAID_INVOICES = True). When it is False, accounts with unpaid
  invoices (including unknown/None) get no warn action.
- A due account gets exactly one of delete or anonymise. unpaid_invoices > 0
  or None (unknown) gives anonymise; otherwise delete.
- Anonymise actions are NOT counted against MAX_DELETES_PER_RUN (assumption,
  flagged for confirmation).
- Delete cap: at most MAX_DELETES_PER_RUN delete actions per run. Candidates
  are ordered closed accounts first, then open ones; within each group by due
  date ascending, then account id ascending. Deferred (over-cap) candidates
  produce no action this run and do NOT get a warn action. They are picked up
  on a later run.
- Staff exclusion: an email that, after strip() and lower(), ends with
  "@tidewater-klatring.no" produces no action. The "@" makes the match exact,
  so subdomains such as "@example.tidewater-klatring.no" do not match.
  Emails are never logged.
- Litigation hold (truthy) produces no action.
- Malformed records: last_seen_at None skips the account with a warning log
  naming only the account id. closed_at None means open. closed_by "member"
  suppresses warn even when closed_at is None; the due date is then computed
  as for an open account.
- Type errors: a datetime.datetime (or any non-date value) in last_seen_at or
  closed_at, or a non-date today, raises TypeError. The message names only
  the account id.
- Duplicate account ids raise ValueError naming the id.
- Account ids must be all int or all str. Mixed types raise TypeError.
"""

import logging
from datetime import date, timedelta

APPROVED_BY = "Þórdís Sveinbjörnsdóttir"
MAX_DELETES_PER_RUN = 200
WARN_WHEN_UNPAID_INVOICES = True
RETENTION_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"

logger = logging.getLogger(__name__)


def _is_staff(email):
    if not isinstance(email, str):
        return False
    return email.strip().lower().endswith(STAFF_EMAIL_SUFFIX)


def _as_date(value, field, account_id):
    if value is None or type(value) is date:
        return value
    raise TypeError(
        f"account {account_id!r}: {field} must be datetime.date or None, "
        f"got {type(value).__name__}"
    )


def _validate_ids(accounts):
    ids = [a["id"] for a in accounts]
    kinds = {type(i) for i in ids}
    if len(kinds) > 1 or not kinds <= {int, str}:
        raise TypeError("account ids must all be int or all be str")
    seen = set()
    for i in ids:
        if i in seen:
            raise ValueError(f"duplicate account id: {i!r}")
        seen.add(i)


def _action(account_id, action, due, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    """Return the sorted list of GDPR clean-up actions for this run."""
    if type(today) is not date:
        raise TypeError("today must be a datetime.date")
    _validate_ids(accounts)

    horizon = today + timedelta(days=WARN_WINDOW_DAYS)
    actions = []
    candidates = []  # (group, due, account_id); group 0 = closed, 1 = open

    for acct in accounts:
        aid = acct["id"]
        if _is_staff(acct.get("email")):
            continue
        if acct.get("litigation_hold"):
            continue
        last_seen = _as_date(acct.get("last_seen_at"), "last_seen_at", aid)
        closed = _as_date(acct.get("closed_at"), "closed_at", aid)
        if last_seen is None:
            logger.warning("skipping account %r: missing last_seen_at", aid)
            continue

        due = last_seen + timedelta(days=RETENTION_DAYS)
        if closed is not None:
            due = min(due, closed + timedelta(days=CLOSED_GRACE_DAYS))

        unpaid = acct.get("unpaid_invoices")
        has_unpaid = unpaid is None or unpaid > 0

        if due <= today:
            if has_unpaid:
                actions.append(_action(aid, "anonymise", due, APPROVED_BY))
            else:
                candidates.append((0 if closed is not None else 1, due, aid))
        elif due <= horizon:
            if acct.get("closed_by") == "member":
                continue
            if has_unpaid and not WARN_WHEN_UNPAID_INVOICES:
                continue
            actions.append(_action(aid, "warn", due, None))

    candidates.sort(key=lambda c: (c[0], c[1], c[2]))
    for _, due, aid in candidates[:MAX_DELETES_PER_RUN]:
        actions.append(_action(aid, "delete", due, APPROVED_BY))
    for _, _, aid in candidates[MAX_DELETES_PER_RUN:]:
        logger.info("deferred delete for account %r: over per-run cap", aid)

    actions.sort(key=lambda a: a["account_id"])
    return actions

# ===== test_purge_plan.py =====
# Run command (not executed in the authoring environment):
#   python3 -I /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-9g_jfso2/gdpr_purge/test_purge_plan.py -v
# -I isolates sys.path, so this file adds its own directory to sys.path.

import os
import sys
import unittest
from datetime import date, datetime, timedelta
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import purge_plan  # noqa: E402
from purge_plan import plan_purge  # noqa: E402

D = date(2026, 10, 13)
APPROVED_ESCAPED = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"


def n(k):
    return timedelta(days=k)


def make(i, last_seen, closed_at=None, closed_by=None, unpaid=0, hold=False,
         email=None, last_login=None):
    return {
        "id": i,
        "email": email if email is not None else f"member{i}@example.com",
        "status": "active",
        "last_seen_at": last_seen,
        "last_login": last_login,
        "closed_at": closed_at,
        "closed_by": closed_by,
        "unpaid_invoices": unpaid,
        "litigation_hold": hold,
    }


def open_due(i, offset, **kw):
    """Open account whose due date is D + offset days."""
    return make(i, D + n(offset) - n(730), **kw)


def closed_due(i, offset, closed_by="staff", **kw):
    """Closed account whose due date is closed_at + 30 = D + offset."""
    return make(i, D - n(10), closed_at=D + n(offset) - n(30),
                closed_by=closed_by, **kw)


def only(result, action):
    return [a for a in result if a["action"] == action]


class TestDueComputation(unittest.TestCase):
    def test_open_due_is_last_seen_plus_730(self):
        r = plan_purge([open_due(1, 5)], D)
        self.assertEqual(r, [{"account_id": 1, "action": "warn",
                              "due": (D + n(5)).isoformat(),
                              "approved_by": None}])

    def test_closed_plus_30_sooner_than_last_seen(self):
        a = make(1, D - n(10), closed_at=D - n(20), closed_by="staff")
        r = plan_purge([a], D)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["action"], "warn")
        self.assertEqual(r[0]["due"], (D + n(10)).isoformat())

    def test_last_seen_plus_730_sooner_than_closed_plus_30(self):
        a = make(1, D + n(3) - n(730), closed_at=D - n(1), closed_by="staff")
        r = plan_purge([a], D)
        self.assertEqual(r[0]["action"], "warn")
        self.assertEqual(r[0]["due"], (D + n(3)).isoformat())


class TestBoundaries(unittest.TestCase):
    def test_last_seen_plus_730_equal_today_is_deleted(self):
        r = plan_purge([make(1, D - n(730))], D)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(r[0]["due"], D.isoformat())

    def test_due_tomorrow_is_not_deleted(self):
        r = plan_purge([open_due(1, 1)], D)
        self.assertEqual(only(r, "delete"), [])
        self.assertEqual([a["action"] for a in r], ["warn"])

    def test_warn_at_today_plus_14(self):
        r = plan_purge([open_due(1, 14)], D)
        self.assertEqual([a["action"] for a in r], ["warn"])

    def test_no_warn_at_today_plus_15(self):
        self.assertEqual(plan_purge([open_due(1, 15)], D), [])

    def test_no_warn_when_due_today(self):
        r = plan_purge([open_due(1, 0)], D)
        self.assertEqual(only(r, "warn"), [])
        self.assertEqual([a["action"] for a in r], ["delete"])

    def test_closed_plus_30_equal_today_is_deleted(self):
        a = make(1, D - n(10), closed_at=D - n(30), closed_by="staff")
        r = plan_purge([a], D)
        self.assertEqual([x["action"] for x in r], ["delete"])
        self.assertEqual(r[0]["due"], D.isoformat())

    def test_closed_plus_30_equal_today_plus_14_warns_for_staff(self):
        r = plan_purge([closed_due(1, 14, closed_by="staff")], D)
        self.assertEqual([a["action"] for a in r], ["warn"])
        self.assertEqual(r[0]["due"], (D + n(14)).isoformat())


class TestLitigationHold(unittest.TestCase):
    def test_hold_suppresses_due_warn_and_anonymise(self):
        accounts = [
            open_due(1, 0, hold=True),
            open_due(2, 5, hold=True),
            open_due(3, 0, unpaid=3, hold=True),
        ]
        self.assertEqual(plan_purge(accounts, D), [])


class TestStaffExclusion(unittest.TestCase):
    def test_staff_emails_produce_no_action(self):
        emails = [
            "ops@tidewater-klatring.no",
            "OPS@TIDEWATER-KLATRING.NO",
            "  ops@tidewater-klatring.no  ",
            "Ops@Tidewater-Klatring.no\n",
        ]
        for email in emails:
            with self.subTest(email=email):
                self.assertEqual(plan_purge([open_due(1, 0, email=email)], D), [])
                self.assertEqual(plan_purge([open_due(1, 5, email=email)], D), [])

    def test_lookalike_domains_are_not_staff(self):
        emails = [
            "ops@tidewater-klatring.no.example",
            "ops@example.tidewater-klatring.no",
        ]
        for email in emails:
            with self.subTest(email=email):
                r = plan_purge([open_due(1, 0, email=email)], D)
                self.assertEqual([a["action"] for a in r], ["delete"])


class TestMemberClosed(unittest.TestCase):
    def test_member_closed_in_warn_window_gets_no_warn(self):
        a = make(1, D - n(10), closed_at=D - n(20), closed_by="member")
        self.assertEqual(plan_purge([a], D), [])

    def test_member_closed_due_still_deleted(self):
        a = make(1, D - n(10), closed_at=D - n(30), closed_by="member")
        r = plan_purge([a], D)
        self.assertEqual([x["action"] for x in r], ["delete"])

    def test_member_closed_with_null_closed_at_treated_as_open_no_warn(self):
        r = plan_purge([open_due(1, 5, closed_by="member")], D)
        self.assertEqual(r, [])


class TestAnonymise(unittest.TestCase):
    def test_due_with_unpaid_invoices_is_anonymised(self):
        r = plan_purge([open_due(1, 0, unpaid=2)], D)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["action"], "anonymise")
        self.assertEqual(r[0]["approved_by"], purge_plan.APPROVED_BY)

    def test_due_with_unknown_unpaid_is_anonymised(self):
        r = plan_purge([open_due(1, 0, unpaid=None)], D)
        self.assertEqual([a["action"] for a in r], ["anonymise"])


class TestWarnWithUnpaid(unittest.TestCase):
    def test_warn_window_unpaid_warns_by_default(self):
        r = plan_purge([open_due(1, 5, unpaid=1)], D)
        self.assertEqual([a["action"] for a in r], ["warn"])

    def test_warn_window_unpaid_suppressed_when_flag_false(self):
        with mock.patch.object(purge_plan, "WARN_WHEN_UNPAID_INVOICES", False):
            r = plan_purge([open_due(1, 5, unpaid=1)], D)
        self.assertEqual(r, [])


class TestDeleteCap(unittest.TestCase):
    def test_cap_defers_extra_deletes_with_no_action(self):
        accounts = [open_due(i, 0) for i in range(1, 206)]
        r = plan_purge(accounts, D)
        self.assertEqual(len(r), 200)
        self.assertEqual({a["action"] for a in r}, {"delete"})
        self.assertEqual({a["account_id"] for a in r}, set(range(1, 201)))

    def test_closed_first_then_earliest_due_open(self):
        closed = [closed_due(1000 + k, 0) for k in range(150)]
        opened = [open_due(i, -i) for i in range(1, 101)]
        r = plan_purge(closed + opened, D)
        deletes = {a["account_id"] for a in only(r, "delete")}
        self.assertEqual(len(deletes), 200)
        expected = set(range(1000, 1150)) | set(range(51, 101))
        self.assertEqual(deletes, expected)
        deferred = set(range(1, 51))
        self.assertTrue(all(a["account_id"] not in deferred for a in r))

    def test_anonymise_not_counted_against_cap(self):
        accounts = [open_due(i, 0) for i in range(1, 201)]
        accounts += [open_due(500 + k, 0, unpaid=1) for k in range(10)]
        r = plan_purge(accounts, D)
        self.assertEqual(len(only(r, "delete")), 200)
        self.assertEqual(len(only(r, "anonymise")), 10)

    def test_tie_break_by_id_regardless_of_input_order(self):
        accounts = [open_due(i, 0) for i in range(201, 0, -1)]
        r = plan_purge(accounts, D)
        deletes = {a["account_id"] for a in only(r, "delete")}
        self.assertEqual(deletes, set(range(1, 201)))


class TestOrdering(unittest.TestCase):
    def test_output_sorted_by_int_id(self):
        accounts = [open_due(3, 5), open_due(1, 6), open_due(2, 7)]
        r = plan_purge(accounts, D)
        self.assertEqual([a["account_id"] for a in r], [1, 2, 3])

    def test_output_sorted_by_str_id(self):
        accounts = [open_due(k, 5) for k in ("b", "c", "a")]
        r = plan_purge(accounts, D)
        self.assertEqual([a["account_id"] for a in r], ["a", "b", "c"])


class TestApprovedBy(unittest.TestCase):
    def test_constant_matches_literal_and_codepoints(self):
        self.assertEqual(purge_plan.APPROVED_BY, "Þórdís Sveinbjörnsdóttir")
        self.assertEqual(purge_plan.APPROVED_BY, APPROVED_ESCAPED)
        non_ascii = [ord(c) for c in purge_plan.APPROVED_BY if ord(c) > 127]
        self.assertEqual(non_ascii, [0xDE, 0xF3, 0xED, 0xF6, 0xF3])

    def test_delete_and_anonymise_carry_approved_by_warn_none(self):
        accounts = [
            open_due(1, 0),
            open_due(2, 0, unpaid=4),
            open_due(3, 5),
        ]
        r = plan_purge(accounts, D)
        by_id = {a["account_id"]: a for a in r}
        self.assertEqual(by_id[1]["approved_by"], APPROVED_ESCAPED)
        self.assertEqual(by_id[2]["approved_by"], APPROVED_ESCAPED)
        self.assertIsNone(by_id[3]["approved_by"])


class TestNoEmailLeak(unittest.TestCase):
    def test_no_email_in_any_output(self):
        accounts = [
            open_due(1, 0, email="alpha.one@example.com"),
            open_due(2, 0, unpaid=1, email="beta.two@example.com"),
            open_due(3, 5, email="gamma.three@example.com"),
            open_due(4, 0, email="delta.four@tidewater-klatring.no"),
            open_due(5, 0, hold=True, email="epsilon.five@example.com"),
            make(6, None, email="zeta.six@example.com"),
        ]
        r = plan_purge(accounts, D)
        emails = [a["email"] for a in accounts]
        text = str(r)
        for email in emails:
            self.assertNotIn(email, text)
        for action in r:
            self.assertEqual(set(action), {"account_id", "action", "due", "approved_by"})
            for value in action.values():
                for email in emails:
                    self.assertNotIn(email, str(value))


class TestMalformed(unittest.TestCase):
    def test_missing_last_seen_skips_with_warning_and_no_email(self):
        acct = make(1, None, email="omega.seven@example.com")
        with self.assertLogs("purge_plan", level="WARNING") as cm:
            r = plan_purge([acct], D)
        self.assertEqual(r, [])
        logged = "\n".join(cm.output)
        self.assertIn("1", logged)
        self.assertNotIn("omega.seven@example.com", logged)

    def test_duplicate_ids_raise_value_error(self):
        with self.assertRaises(ValueError) as cm:
            plan_purge([open_due(7, 0), open_due(7, 5)], D)
        self.assertIn("7", str(cm.exception))

    def test_datetime_for_last_seen_raises(self):
        acct = make(1, datetime(2026, 10, 1, 12, 0))
        with self.assertRaises(TypeError):
            plan_purge([acct], D)

    def test_datetime_for_closed_at_raises(self):
        acct = make(1, D - n(10), closed_at=datetime(2026, 9, 1, 0, 0))
        with self.assertRaises(TypeError):
            plan_purge([acct], D)

    def test_mixed_id_types_raise_type_error(self):
        with self.assertRaises(TypeError):
            plan_purge([open_due(1, 0), open_due("2", 0)], D)

    def test_datetime_today_raises(self):
        with self.assertRaises(TypeError):
            plan_purge([], datetime(2026, 10, 13, 0, 0))


class TestLastLoginIgnored(unittest.TestCase):
    def test_old_last_login_does_not_trigger_delete(self):
        acct = make(1, D - n(10), last_login=D - n(2000))
        self.assertEqual(plan_purge([acct], D), [])


if __name__ == "__main__":
    unittest.main()