"""Tidewater Climbing GDPR clean-up planner.

plan_purge(accounts, today) returns a list of action dicts. It is pure:
no I/O, no mutation of its input, and deterministic.

Run the tests with: python3 -I <this file>

OPEN ITEMS (client has not confirmed; defaults chosen, marked OPEN-n in code):
  OPEN-1  The R8 cap counts delete plus anonymise combined.
  OPEN-2  warn is still emitted for accounts with unpaid invoices. The
          notice text must say "anonymised", not "deleted". This function
          only returns action="warn"; the wording lives downstream.
  OPEN-3  Member-closed accounts past the 30-day grace with unpaid invoices
          get "anonymise" and no warn.
  OPEN-4  Other statuses get no filter beyond R14.
  OPEN-5  The DPO name is a config constant, not proof of approval.

ASSUMPTIONS (beyond the spec):
  A-1  Accounts with a litigation hold or a staff email are skipped before
       validation of last_seen_at, since they emit nothing.
  A-2  Duplicate account ids raise ValueError, so "one action per account"
       cannot be silently violated.
  A-3  closed_by is only validated when closed_at is set.
  A-4  The "do not warn member-closed" rule applies whenever closed_by is
       "member", as written in R3.
"""

import unittest
import json
import copy
import sys
from datetime import date, datetime, timedelta
from unittest import mock

# R9: approver for delete/anonymise. OPEN-5: config constant, not proof of approval.
DPO_APPROVER = "Þórdís Sveinbjörnsdóttir"

STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14

# OPEN-1: the cap counts delete plus anonymise combined (R8).
DESTRUCTIVE_CAP = 200

# R14: statuses that mark an account as already processed.
# TODO: EMPTY UNTIL THE CLIENT SUPPLIES THE EXACT STATUS VOCABULARY.
# Do not invent values here. Fill this in once the client confirms them.
PROCESSED_STATUSES = frozenset()


def _is_plain_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _is_unpaid(value):
    # OPEN-3 / R4: an int > 0 or True means unpaid invoices.
    return value is True or (isinstance(value, int) and value > 0)


def _due(last_seen, closed_at):
    # R2: inactivity uses last_seen_at only (R1).
    inactive = last_seen + timedelta(days=INACTIVITY_DAYS)
    if closed_at is None:
        return inactive
    return min(inactive, closed_at + timedelta(days=CLOSED_GRACE_DAYS))


def plan_purge(accounts, today):
    if not _is_plain_date(today):
        raise ValueError("today must be a datetime.date (datetime is rejected)")

    horizon = today + timedelta(days=WARN_WINDOW_DAYS)
    seen_ids = set()
    destructive = []  # (tier, due, account_id, action)
    warns = []        # (account_id, due)

    for acc in accounts:
        account_id = acc.get("id")
        if account_id is None:
            raise ValueError("account is missing 'id'")
        if account_id in seen_ids:
            raise ValueError(f"duplicate account id {account_id!r}")  # A-2
        seen_ids.add(account_id)

        email = acc.get("email")
        if not isinstance(email, str) or not email.strip():
            raise ValueError(f"account {account_id!r}: missing email")

        # R14: processed accounts are skipped (see PROCESSED_STATUSES).
        if acc.get("status") in PROCESSED_STATUSES:
            continue

        # R6: staff accounts emit nothing. R5: litigation hold emits nothing.
        is_staff = email.strip().lower().endswith(STAFF_EMAIL_SUFFIX)
        if is_staff or acc.get("litigation_hold"):  # A-1
            continue

        last_seen = acc.get("last_seen_at")
        if not _is_plain_date(last_seen):
            raise ValueError(f"account {account_id!r}: missing or invalid last_seen_at")

        closed_at = acc.get("closed_at")
        closed_by = acc.get("closed_by")
        if closed_at is not None:
            if not _is_plain_date(closed_at):
                raise ValueError(f"account {account_id!r}: invalid closed_at")
            if closed_by not in ("member", "staff"):  # A-3
                raise ValueError(
                    f"account {account_id!r}: closed_by must be 'member' or 'staff'"
                )

        due = _due(last_seen, closed_at)

        if due <= today:
            # R4 / OPEN-3: unpaid invoices mean anonymise, not delete.
            action = "anonymise" if _is_unpaid(acc.get("unpaid_invoices")) else "delete"
            # R8 tiers: 0 member-closed, 1 staff-closed, 2 not closed.
            tier = 2
            if closed_at is not None:
                tier = 0 if closed_by == "member" else 1
            destructive.append((tier, due, account_id, action))
        elif due <= horizon and closed_by != "member":
            # R3: warn only when today < due <= today + 14, never for member closures.
            # OPEN-2: warn is emitted even with unpaid invoices; the notice says "anonymised".
            warns.append((account_id, due))

    # R8: cap the destructive actions, ordered by tier, then due, then account_id.
    destructive.sort(key=lambda t: (t[0], t[1], t[2]))
    selected = destructive[:DESTRUCTIVE_CAP]

    actions = [
        {
            "account_id": account_id,
            "action": action,
            "due": due.isoformat(),
            "approved_by": DPO_APPROVER,
        }
        for _tier, due, account_id, action in selected
    ]
    actions.extend(
        {
            "account_id": account_id,
            "action": "warn",
            "due": due.isoformat(),
            "approved_by": None,  # R9
        }
        for account_id, due in warns
    )
    # R10: one action per account, sorted by account_id.
    actions.sort(key=lambda a: a["account_id"])
    return actions


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

TODAY = date(2026, 10, 13)


def _acct(id_, **overrides):
    base = {
        "id": id_,
        "email": f"member{id_}@example.com",
        "status": "active",
        "last_seen_at": TODAY - timedelta(days=100),
        "last_login": None,
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
    }
    base.update(overrides)
    return base


def _seen_for_due(days_from_today):
    # last_seen_at such that the inactivity due date is TODAY + days_from_today.
    return TODAY + timedelta(days=days_from_today) - timedelta(days=INACTIVITY_DAYS)


def _delete(account_id, due=TODAY):
    return {"account_id": account_id, "action": "delete",
            "due": due.isoformat(), "approved_by": DPO_APPROVER}


class PlanPurgeTests(unittest.TestCase):

    # Acceptance scenarios
    def test_ac1_inactive_due_gives_delete(self):
        acc = _acct(1, last_seen_at=TODAY - timedelta(days=730))
        self.assertEqual(plan_purge([acc], TODAY), [_delete(1)])

    def test_ac2_member_closed_30_days_gives_delete(self):
        acc = _acct(1, closed_at=TODAY - timedelta(days=30),
                    closed_by="member", last_seen_at=TODAY - timedelta(days=10))
        self.assertEqual(plan_purge([acc], TODAY), [_delete(1)])

    def test_ac3_member_closed_due_in_10_days_gives_nothing(self):
        acc = _acct(1, closed_at=TODAY - timedelta(days=20),
                    closed_by="member", last_seen_at=TODAY - timedelta(days=10))
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_ac4_staff_email_gives_nothing(self):
        acc = _acct(1, email="  Anna.Berg@Tidewater-Klatring.NO ",
                    last_seen_at=TODAY - timedelta(days=800))
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_ac5_cap_includes_all_member_closed_first(self):
        members = [_acct(i, closed_at=TODAY - timedelta(days=30),
                         closed_by="member", last_seen_at=TODAY - timedelta(days=100))
                   for i in range(1, 51)]
        inactive = [_acct(i, last_seen_at=TODAY - timedelta(days=730))
                    for i in range(51, 251)]
        out = plan_purge(members + inactive, TODAY)
        self.assertEqual(len(out), 200)
        self.assertEqual([a["account_id"] for a in out], list(range(1, 201)))

    def test_cap_orders_staff_closed_before_not_closed(self):
        staff = [_acct(i, closed_at=TODAY - timedelta(days=30),
                       closed_by="staff", last_seen_at=TODAY - timedelta(days=100))
                 for i in range(1, 151)]
        inactive = [_acct(i, last_seen_at=TODAY - timedelta(days=730))
                    for i in range(151, 251)]
        out = plan_purge(staff + inactive, TODAY)
        self.assertEqual([a["account_id"] for a in out], list(range(1, 201)))

    def test_cap_within_tier_earliest_due_first(self):
        accounts = [_acct(i, last_seen_at=TODAY - timedelta(days=730))
                    for i in range(1, 201)]
        # Account 500 is due yesterday, so it wins a slot over id 200.
        accounts.append(_acct(500, last_seen_at=TODAY - timedelta(days=731)))
        out = plan_purge(accounts, TODAY)
        self.assertEqual([a["account_id"] for a in out],
                         list(range(1, 200)) + [500])

    def test_cap_does_not_affect_warnings(self):
        accounts = [_acct(i, last_seen_at=TODAY - timedelta(days=730))
                    for i in range(1, 202)]
        accounts.append(_acct(900, last_seen_at=_seen_for_due(5)))
        out = plan_purge(accounts, TODAY)
        destructive = [a for a in out if a["action"] != "warn"]
        warns = [a["account_id"] for a in out if a["action"] == "warn"]
        self.assertEqual(len(destructive), 200)
        self.assertEqual(warns, [900])

    def test_ac6_litigation_hold_gives_nothing(self):
        acc = _acct(1, last_seen_at=TODAY - timedelta(days=730), litigation_hold=True)
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_ac7_unpaid_invoices_gives_anonymise(self):
        acc = _acct(1, last_seen_at=TODAY - timedelta(days=730), unpaid_invoices=3)
        out = plan_purge([acc], TODAY)
        self.assertEqual(out[0]["action"], "anonymise")
        self.assertEqual(out[0]["approved_by"], DPO_APPROVER)

    def test_unpaid_true_gives_anonymise(self):
        acc = _acct(1, last_seen_at=TODAY - timedelta(days=730), unpaid_invoices=True)
        self.assertEqual(plan_purge([acc], TODAY)[0]["action"], "anonymise")

    def test_member_closed_past_grace_with_unpaid_is_anonymised_no_warn(self):
        acc = _acct(1, closed_at=TODAY - timedelta(days=40), closed_by="member",
                    last_seen_at=TODAY - timedelta(days=10), unpaid_invoices=2)
        out = plan_purge([acc], TODAY)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "anonymise")
        self.assertEqual(out[0]["due"], (TODAY - timedelta(days=10)).isoformat())

    def test_ac8_sorted_one_per_account_and_json_round_trip(self):
        accounts = [
            _acct(3, last_seen_at=TODAY - timedelta(days=730)),
            _acct(1, last_seen_at=_seen_for_due(5)),
            _acct(2, closed_at=TODAY - timedelta(days=30), closed_by="member",
                  last_seen_at=TODAY - timedelta(days=10)),
            _acct(4, email="x@tidewater-klatring.no",
                  last_seen_at=TODAY - timedelta(days=730)),
        ]
        out = plan_purge(accounts, TODAY)
        ids = [a["account_id"] for a in out]
        self.assertEqual(ids, [1, 2, 3])
        self.assertEqual(len(set(ids)), len(ids))
        for a in out:
            self.assertEqual(set(a.keys()), {"account_id", "action", "due", "approved_by"})
        self.assertEqual(json.loads(json.dumps(out)), out)

    # Boundary tests
    def test_due_today_is_actioned_not_warned(self):
        out = plan_purge([_acct(1, last_seen_at=_seen_for_due(0))], TODAY)
        self.assertEqual(out, [_delete(1)])

    def test_due_tomorrow_is_warned_not_actioned(self):
        out = plan_purge([_acct(1, last_seen_at=_seen_for_due(1))], TODAY)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "warn")
        self.assertIsNone(out[0]["approved_by"])

    def test_due_in_14_days_is_warned(self):
        out = plan_purge([_acct(1, last_seen_at=_seen_for_due(14))], TODAY)
        self.assertEqual(out[0]["action"], "warn")
        self.assertEqual(out[0]["due"], (TODAY + timedelta(days=14)).isoformat())

    def test_due_in_15_days_is_not_warned(self):
        self.assertEqual(plan_purge([_acct(1, last_seen_at=_seen_for_due(15))], TODAY), [])

    def test_staff_closed_due_soon_is_warned(self):
        acc = _acct(1, closed_at=TODAY - timedelta(days=25), closed_by="staff",
                    last_seen_at=TODAY - timedelta(days=10))
        self.assertEqual(plan_purge([acc], TODAY)[0]["action"], "warn")

    # R1: last_login is never used
    def test_r1_last_login_ignored(self):
        acc = _acct(1, last_login=date(2000, 1, 1), last_seen_at=TODAY - timedelta(days=10))
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_r1_old_last_login_does_not_hide_due_account(self):
        acc = _acct(1, last_login=TODAY, last_seen_at=TODAY - timedelta(days=730))
        self.assertEqual(plan_purge([acc], TODAY), [_delete(1)])

    # R13: malformed input
    def test_missing_last_seen_raises_with_id(self):
        with self.assertRaisesRegex(ValueError, "42"):
            plan_purge([_acct(42, last_seen_at=None)], TODAY)

    def test_bad_closed_by_raises_with_id(self):
        with self.assertRaisesRegex(ValueError, "43"):
            plan_purge([_acct(43, closed_at=TODAY - timedelta(days=10), closed_by="bot")], TODAY)

    def test_datetime_today_rejected(self):
        with self.assertRaises(ValueError):
            plan_purge([], datetime(2026, 10, 13))

    def test_string_today_rejected(self):
        with self.assertRaises(ValueError):
            plan_purge([], "2026-10-13")

    def test_missing_email_raises_with_id(self):
        acc = _acct(44)
        del acc["email"]
        with self.assertRaisesRegex(ValueError, "44"):
            plan_purge([acc], TODAY)

    def test_none_email_raises_with_id(self):
        with self.assertRaisesRegex(ValueError, "45"):
            plan_purge([_acct(45, email=None)], TODAY)

    # R14: processed statuses, with the constant populated
    def test_r14_processed_status_skipped_when_populated(self):
        accounts = [
            _acct(1, status="erased", last_seen_at=TODAY - timedelta(days=730)),
            _acct(2, last_seen_at=TODAY - timedelta(days=730)),
        ]
        with mock.patch.object(sys.modules[__name__], "PROCESSED_STATUSES",
                               frozenset({"erased"})):
            out = plan_purge(accounts, TODAY)
        self.assertEqual(out, [_delete(2)])

    # R5/R6/R7 and immutability
    def test_output_contains_no_personal_data(self):
        acc = _acct(1, email="private.person@example.com",
                    last_seen_at=TODAY - timedelta(days=730))
        out = plan_purge([acc], TODAY)
        self.assertNotIn("@", json.dumps(out))
        self.assertNotIn("private.person", json.dumps(out))

    def test_input_not_mutated(self):
        accounts = [
            _acct(1, last_seen_at=TODAY - timedelta(days=730), unpaid_invoices=1),
            _acct(2, closed_at=TODAY - timedelta(days=30), closed_by="member",
                  last_seen_at=TODAY - timedelta(days=10)),
        ]
        snapshot = copy.deepcopy(accounts)
        plan_purge(accounts, TODAY)
        self.assertEqual(accounts, snapshot)

    def test_deterministic(self):
        accounts = [_acct(i, last_seen_at=TODAY - timedelta(days=730)) for i in range(1, 6)]
        self.assertEqual(plan_purge(accounts, TODAY), plan_purge(accounts, TODAY))


if __name__ == "__main__":
    unittest.main()