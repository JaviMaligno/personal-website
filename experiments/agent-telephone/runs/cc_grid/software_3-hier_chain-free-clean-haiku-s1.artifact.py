# /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-apzwwolz/purge_plan.py
# -*- coding: utf-8 -*-
"""Tidewater Climbing GDPR clean-up: plan the purge actions for one run.

plan_purge(accounts, today, skipped=None) returns a list of action dicts with
exactly the keys account_id, action, due, approved_by, sorted by account_id.
No personal fields (email, tenant, status, last_login) appear in the output.

Settled decisions:
1. An already-past-due account keeps its computed due date. It is not
   replaced with today.
2. A closed account with unpaid invoices that is past the warn window becomes
   "anonymise" with its computed due date, not "delete".
3. The 200 cap applies to "delete" actions only. Anonymise actions are never
   capped. ASSUMPTION: confirm with the client.
4. Cap ordering: at most 200 delete actions per run. Candidates are ranked
   closed first (closed_at is not None before closed_at is None), then due
   date ascending, then account id ascending. The first 200 are kept.
   Overflow accounts get no action this run and remain due for the next run.
5. Unpaid invoices only switch deletion to anonymisation. Warnings still apply
   to unpaid accounts in the warn window.
6. Warn window: today < due <= today + 14 days. Due exactly today is a removal,
   not a warning. Due at today + 15 days gets nothing.
7. status is not referenced by any rule and never influences a decision. It is
   not validated.
8. The staff email check strips whitespace and lowercases the email before
   testing the suffix "@tidewater-klatring.no". Staff accounts produce no
   actions.

Core rules:
- Inactivity is measured on last_seen_at only. last_login is ignored entirely.
  It is not validated and may hold any value.
- due = last_seen_at + 730 days. If closed_at is set, due = min(due,
  closed_at + 30 days).
- Accounts with litigation_hold True produce no actions.
- Removal (due <= today): unpaid_invoices > 0 gives "anonymise", otherwise
  "delete". Both carry the approver APPROVER.
- Warn (inside the window): only when closed_by is not "member". Warn actions
  have approved_by None.
- The account gets at most one action.

Additional choices beyond the settled list:
A. Skipped accounts produce no action. Each skip appends the account id to
   `skipped` (if given) and logs a WARNING on logger "purge_plan". The log
   carries the id and reason only, never the email.
B. Skip conditions: the account is not a dict; a required key is missing
   (required: id, email, last_seen_at, closed_at, closed_by, unpaid_invoices,
   litigation_hold; status, tenant and last_login are not required); id is not
   a string (needed for sorting); email is None or not a string; last_seen_at
   is None or not a date; closed_at is present, not None and not a date;
   closed_at is set but closed_by is not exactly "member" or "staff";
   unpaid_invoices is not an int (bool excluded) or is negative; litigation_hold
   is not a bool; a datetime.datetime is given where a date is expected; the id
   appears more than once (every instance is skipped and its id is appended
   once per instance); the due date overflows the representable date range.
C. When closed_at is None, closed_by is not validated. Any value other than
   "member" counts as not member-closed, so the warn applies.
D. Validation runs before the staff and litigation-hold exclusions, so an
   invalid staff or held account is still reported as skipped.
E. today must be a datetime.date and not a datetime.datetime. Otherwise
   TypeError is raised, since that is a caller bug.
"""

import logging
from collections import Counter
from datetime import date, datetime, timedelta

log = logging.getLogger(__name__)

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
DELETE_CAP = 200
RETENTION = timedelta(days=730)
CLOSED_GRACE = timedelta(days=30)
WARN_DAYS = 14
REQUIRED_KEYS = (
    "id",
    "email",
    "last_seen_at",
    "closed_at",
    "closed_by",
    "unpaid_invoices",
    "litigation_hold",
)


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _validate(account):
    """Return None if the account is usable, otherwise a short reason."""
    if not isinstance(account, dict):
        return "not a mapping"
    missing = [k for k in REQUIRED_KEYS if k not in account]
    if missing:
        return "missing key(s): " + ", ".join(missing)
    if not isinstance(account["id"], str):
        return "id is not a string"
    if not isinstance(account["email"], str):
        return "email is missing or not a string"
    if not _is_date(account["last_seen_at"]):
        return "last_seen_at is not a date"
    closed_at = account["closed_at"]
    if closed_at is not None:
        if not _is_date(closed_at):
            return "closed_at is not a date"
        if account["closed_by"] not in ("member", "staff"):
            return "closed_by is not 'member' or 'staff'"
    unpaid = account["unpaid_invoices"]
    if isinstance(unpaid, bool) or not isinstance(unpaid, int) or unpaid < 0:
        return "unpaid_invoices is not a non-negative int"
    if not isinstance(account["litigation_hold"], bool):
        return "litigation_hold is not a bool"
    return None


def _due_date(last_seen_at, closed_at):
    due = last_seen_at + RETENTION
    if closed_at is not None:
        due = min(due, closed_at + CLOSED_GRACE)
    return due


def _is_staff(email):
    return email.strip().lower().endswith(STAFF_SUFFIX)


def _action(account_id, action, due, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def _skip(account_id, reason, skipped):
    log.warning("purge_plan: skipping account %r: %s", account_id, reason)
    if skipped is not None:
        skipped.append(account_id)


def _select_deletes(candidates):
    """candidates: list of (closed_rank, due, account_id). Keep the first cap."""
    ranked = sorted(candidates, key=lambda c: (c[0], c[1], c[2]))
    return ranked[:DELETE_CAP]


def plan_purge(accounts, today, skipped=None):
    if not _is_date(today):
        raise TypeError("today must be a datetime.date")
    accounts = list(accounts)
    ids = [a.get("id") if isinstance(a, dict) else None for a in accounts]
    counts = Counter(i for i in ids if isinstance(i, str))
    duplicated = {i for i, n in counts.items() if n > 1}

    results = []
    delete_candidates = []
    for account, account_id in zip(accounts, ids):
        if isinstance(account_id, str) and account_id in duplicated:
            _skip(account_id, "duplicate id", skipped)
            continue
        reason = _validate(account)
        if reason is not None:
            _skip(account_id, reason, skipped)
            continue
        if _is_staff(account["email"]) or account["litigation_hold"]:
            continue
        try:
            due = _due_date(account["last_seen_at"], account["closed_at"])
        except OverflowError:
            _skip(account_id, "due date out of range", skipped)
            continue

        days_left = (due - today).days
        if days_left <= 0:
            if account["unpaid_invoices"] > 0:
                results.append(_action(account_id, "anonymise", due, APPROVER))
            else:
                closed_rank = 0 if account["closed_at"] is not None else 1
                delete_candidates.append((closed_rank, due, account_id))
        elif days_left <= WARN_DAYS and account["closed_by"] != "member":
            results.append(_action(account_id, "warn", due, None))

    for _, due, account_id in _select_deletes(delete_candidates):
        results.append(_action(account_id, "delete", due, APPROVER))

    results.sort(key=lambda r: r["account_id"])
    return results

# /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-apzwwolz/test_purge_plan.py
# -*- coding: utf-8 -*-
# Run with an absolute path:
#   python3 -I -m unittest discover -s /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-apzwwolz -p "test_purge_plan.py" -v
# Note: this file was written without executing it. The test run has not been performed yet.
"""Tests for purge_plan. Fake data only."""

import json
import unittest
from datetime import date, datetime, timedelta
from unittest import mock

import purge_plan
from purge_plan import plan_purge

APPROVER = "Þórdís Sveinbjörnsdóttir"
TODAY = date(2026, 10, 13)


def days(n):
    return timedelta(days=n)


def acct(**overrides):
    base = {
        "id": "a1",
        "email": "member@example.test",
        "status": "active",
        "tenant": "legacy-tenant",
        "last_seen_at": TODAY - days(730),
        "last_login": date(2000, 1, 1),
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
    }
    base.update(overrides)
    return base


class PurgePlanTests(unittest.TestCase):

    def test_due_today_is_delete(self):
        out = plan_purge([acct()], TODAY)
        self.assertEqual(out, [{
            "account_id": "a1",
            "action": "delete",
            "due": TODAY.isoformat(),
            "approved_by": APPROVER,
        }])

    def test_due_today_plus_14_is_warn(self):
        due = TODAY + days(14)
        out = plan_purge([acct(last_seen_at=due - days(730))], TODAY)
        self.assertEqual(out, [{
            "account_id": "a1",
            "action": "warn",
            "due": due.isoformat(),
            "approved_by": None,
        }])

    def test_due_today_plus_15_gets_nothing(self):
        due = TODAY + days(15)
        self.assertEqual(plan_purge([acct(last_seen_at=due - days(730))], TODAY), [])

    def test_member_closed_in_warn_window_gets_no_warn(self):
        out = plan_purge([acct(closed_at=TODAY - days(16), closed_by="member",
                               last_seen_at=TODAY - days(10))], TODAY)
        self.assertEqual(out, [])

    def test_staff_closed_in_warn_window_gets_warn(self):
        due = TODAY + days(14)
        out = plan_purge([acct(closed_at=TODAY - days(16), closed_by="staff",
                               last_seen_at=TODAY - days(10))], TODAY)
        self.assertEqual(out, [{
            "account_id": "a1",
            "action": "warn",
            "due": due.isoformat(),
            "approved_by": None,
        }])

    def test_thirty_day_closed_rule_wins_over_730(self):
        out = plan_purge([acct(last_seen_at=TODAY - days(100),
                               closed_at=TODAY - days(40),
                               closed_by="member")], TODAY)
        due = TODAY - days(10)
        self.assertEqual(out, [{
            "account_id": "a1",
            "action": "delete",
            "due": due.isoformat(),
            "approved_by": APPROVER,
        }])

    def test_past_due_open_account_keeps_computed_date(self):
        out = plan_purge([acct(last_seen_at=TODAY - days(800))], TODAY)
        self.assertEqual(out[0]["due"], (TODAY - days(70)).isoformat())
        self.assertEqual(out[0]["action"], "delete")

    def test_litigation_hold_produces_nothing(self):
        self.assertEqual(plan_purge([acct(litigation_hold=True)], TODAY), [])
        held_in_window = acct(litigation_hold=True,
                              last_seen_at=TODAY + days(14) - days(730))
        self.assertEqual(plan_purge([held_in_window], TODAY), [])

    def test_staff_accounts_produce_nothing(self):
        emails = [
            "staff@tidewater-klatring.no",
            "Staff@TIDEWATER-Klatring.NO",
            "  mixed.Case@Tidewater-Klatring.no  ",
        ]
        accounts = [acct(id=f"s{i}", email=e) for i, e in enumerate(emails)]
        self.assertEqual(plan_purge(accounts, TODAY), [])

    def test_lookalike_domain_is_not_staff(self):
        out = plan_purge([acct(email="x@tidewater-klatring.no.example.test")], TODAY)
        self.assertEqual([r["action"] for r in out], ["delete"])

    def test_unpaid_invoices_turn_delete_into_anonymise(self):
        out = plan_purge([acct(unpaid_invoices=2)], TODAY)
        self.assertEqual(out, [{
            "account_id": "a1",
            "action": "anonymise",
            "due": TODAY.isoformat(),
            "approved_by": APPROVER,
        }])

    def test_unpaid_account_still_warned_in_window(self):
        due = TODAY + days(7)
        out = plan_purge([acct(unpaid_invoices=3, closed_at=TODAY - days(23),
                               closed_by="staff", last_seen_at=TODAY - days(10))], TODAY)
        self.assertEqual(out, [{
            "account_id": "a1",
            "action": "warn",
            "due": due.isoformat(),
            "approved_by": None,
        }])

    def test_closed_unpaid_past_due_is_anonymise_with_computed_date(self):
        out = plan_purge([acct(closed_at=TODAY - days(40), closed_by="member",
                               unpaid_invoices=1, last_seen_at=TODAY - days(100))], TODAY)
        due = TODAY - days(10)
        self.assertEqual(out, [{
            "account_id": "a1",
            "action": "anonymise",
            "due": due.isoformat(),
            "approved_by": APPROVER,
        }])

    def test_cap_keeps_200_deletes_closed_first_then_due_then_id(self):
        accounts = []
        for i in range(10):
            accounts.append(acct(id=f"c{i:03d}", last_seen_at=TODAY - days(100),
                                 closed_at=TODAY - days(40 + i), closed_by="staff"))
        for j in range(195):
            accounts.append(acct(id=f"o{j:03d}", last_seen_at=TODAY - days(730 + j)))
        for k in range(5):
            accounts.append(acct(id=f"u{k:03d}", unpaid_invoices=1,
                                 last_seen_at=TODAY - days(730)))
        out = plan_purge(accounts, TODAY)

        by_action = {}
        for r in out:
            by_action.setdefault(r["action"], []).append(r["account_id"])

        deletes = sorted(by_action.get("delete", []))
        expected = sorted([f"c{i:03d}" for i in range(10)] +
                          [f"o{j:03d}" for j in range(5, 195)])
        self.assertEqual(len(deletes), 200)
        self.assertEqual(deletes, expected)

        # Anonymise actions are never capped.
        self.assertEqual(sorted(by_action["anonymise"]),
                         [f"u{k:03d}" for k in range(5)])

        # Overflow accounts (the five least overdue open accounts) get no action.
        overflow = {f"o{j:03d}" for j in range(5)}
        self.assertTrue(overflow.isdisjoint({r["account_id"] for r in out}))

    def test_cap_tie_breaks_closed_then_due_then_id(self):
        accounts = [
            acct(id="x1", last_seen_at=TODAY - days(735)),  # due today - 5
            acct(id="b2", last_seen_at=TODAY - days(735)),  # due today - 5
            acct(id="z3", last_seen_at=TODAY - days(100),
                 closed_at=TODAY - days(31), closed_by="member"),  # due today - 1, closed
            acct(id="a4", last_seen_at=TODAY - days(739)),  # due today - 9
        ]
        with mock.patch.object(purge_plan, "DELETE_CAP", 3):
            out = plan_purge(accounts, TODAY)
        self.assertEqual([r["account_id"] for r in out], ["a4", "b2", "z3"])

    def test_output_sorted_by_account_id(self):
        accounts = [
            acct(id="m2"),
            acct(id="a9"),
            acct(id="z0", unpaid_invoices=1),
            acct(id="c5", last_seen_at=TODAY + days(14) - days(730)),
        ]
        out = plan_purge(accounts, TODAY)
        self.assertEqual([r["account_id"] for r in out], ["a9", "c5", "m2", "z0"])

    def test_no_email_or_personal_fields_in_output(self):
        secret_email = "jon.doe.test@example.test"
        accounts = [
            acct(id="p1", email=secret_email, unpaid_invoices=1,
                 tenant="tenant-xyz", status="suspended"),
            acct(id="p2", email="w@example.test", closed_at=TODAY - days(16),
                 closed_by="staff", last_seen_at=TODAY - days(10)),
        ]
        out = plan_purge(accounts, TODAY)
        text = json.dumps(out)
        for needle in (secret_email, "example.test", "jon.doe",
                       "tenant-xyz", "legacy-tenant", "suspended"):
            self.assertNotIn(needle, text)
        for r in out:
            self.assertEqual(set(r), {"account_id", "action", "due", "approved_by"})

    def test_approved_by_values(self):
        accounts = [
            acct(id="d"),
            acct(id="n", unpaid_invoices=1),
            acct(id="w", last_seen_at=TODAY + days(14) - days(730)),
        ]
        by_id = {r["account_id"]: r for r in plan_purge(accounts, TODAY)}
        self.assertEqual(by_id["d"]["approved_by"], "Þórdís Sveinbjörnsdóttir")
        self.assertEqual(by_id["n"]["approved_by"], "Þórdís Sveinbjörnsdóttir")
        self.assertIsNone(by_id["w"]["approved_by"])

    def test_last_login_is_ignored(self):
        recent_seen_old_login = acct(id="r1", last_seen_at=TODAY - days(10),
                                     last_login=date(2000, 1, 1))
        old_seen_recent_login = acct(id="r2", last_seen_at=TODAY - days(730),
                                     last_login=TODAY)
        garbage_login = acct(id="r3", last_login="not-a-date")
        out = plan_purge([recent_seen_old_login, old_seen_recent_login, garbage_login], TODAY)
        self.assertEqual([(r["account_id"], r["action"]) for r in out],
                         [("r2", "delete"), ("r3", "delete")])

    def test_invalid_accounts_are_skipped_logged_and_reported(self):
        cases = {
            "last_seen_none": acct(id="s1", last_seen_at=None),
            "last_seen_datetime": acct(id="s1", last_seen_at=datetime(2024, 1, 1)),
            "closed_at_string": acct(id="s1", closed_at="2026-01-01"),
            "closed_at_datetime": acct(id="s1", closed_at=datetime(2026, 1, 1)),
            "closed_by_unknown": acct(id="s1", closed_at=TODAY - days(40), closed_by="Member"),
            "closed_by_none_with_closed_at": acct(id="s1", closed_at=TODAY - days(40),
                                                  closed_by=None),
            "email_none": acct(id="s1", email=None),
            "email_not_str": acct(id="s1", email=12),
            "unpaid_negative": acct(id="s1", unpaid_invoices=-1),
            "unpaid_bool": acct(id="s1", unpaid_invoices=True),
            "unpaid_float": acct(id="s1", unpaid_invoices=1.0),
            "hold_not_bool": acct(id="s1", litigation_hold="no"),
            "hold_int": acct(id="s1", litigation_hold=0),
        }
        for label, account in cases.items():
            with self.subTest(label):
                skipped = []
                with self.assertLogs("purge_plan", level="WARNING"):
                    out = plan_purge([account], TODAY, skipped=skipped)
                self.assertEqual(out, [])
                self.assertEqual(skipped, ["s1"])

    def test_missing_key_is_skipped(self):
        account = acct(id="s2")
        del account["unpaid_invoices"]
        skipped = []
        with self.assertLogs("purge_plan", level="WARNING"):
            out = plan_purge([account], TODAY, skipped=skipped)
        self.assertEqual(out, [])
        self.assertEqual(skipped, ["s2"])

    def test_skip_without_skipped_list_does_not_crash(self):
        with self.assertLogs("purge_plan", level="WARNING"):
            self.assertEqual(plan_purge([acct(id="s3", last_seen_at=None)], TODAY), [])

    def test_duplicate_ids_skip_every_instance(self):
        accounts = [acct(id="d1"), acct(id="d1", unpaid_invoices=2), acct(id="ok")]
        skipped = []
        with self.assertLogs("purge_plan", level="WARNING"):
            out = plan_purge(accounts, TODAY, skipped=skipped)
        self.assertEqual([r["account_id"] for r in out], ["ok"])
        self.assertEqual(sorted(skipped), ["d1", "d1"])

    def test_non_date_today_raises_type_error(self):
        with self.assertRaises(TypeError):
            plan_purge([acct()], "2026-10-13")
        with self.assertRaises(TypeError):
            plan_purge([acct()], datetime(2026, 10, 13))


if __name__ == "__main__":
    unittest.main()