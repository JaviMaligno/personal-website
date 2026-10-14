# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-e18ogn87/gdpr_purge/purge_plan.py
# NOTE: NOT EXECUTED. This run had no tool access, so the file was not written and the tests were not run.
# Assumptions beyond the spec:
#  - Any closed_at (including closed_by "staff") gets closed priority in the deletion cap ordering.
#  - Warn is suppressed only when closed_by == "member".
#  - A datetime value for last_seen_at or closed_at is normalised to its date part.
#  - unpaid_invoices of True counts as unpaid (True > 0).
#  - account_id values must be mutually comparable, because output is sorted by account_id.
# Open: tests/__init__.py (empty) is needed so that `python3 -m unittest` discovers the tests package.

"""GDPR clean-up planner for Tidewater Climbing member accounts.

plan_purge(accounts, today) returns a list of action dicts with the keys
account_id, action, due and approved_by. It is a pure function: the input is
not mutated, nothing is logged, and no email address appears in the output.

Standard library only.
"""

from datetime import datetime, timedelta

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
MAX_DELETIONS_PER_RUN = 200
DPO_APPROVER = "Tordis Svenbjorn Dottir"
STAFF_DOMAIN = "@tidewater-klatring.no"


def _as_date(value):
    # Normalise a datetime to its date part so comparisons with date never raise.
    if isinstance(value, datetime):
        return value.date()
    return value


def is_staff(email):
    # Staff if the stripped, lowercased email ends with STAFF_DOMAIN.
    # Lookalikes such as "x@tidewater-klatring.no.example.com" or
    # "x@nottidewater-klatring.no" do not end with "@tidewater-klatring.no",
    # so they are not staff. A missing or None email is not staff.
    if not email:
        return False
    return email.strip().lower().endswith(STAFF_DOMAIN)


def _has_unpaid(unpaid_invoices):
    # 0, None and False mean no unpaid invoices. Any positive count means unpaid.
    return bool(unpaid_invoices) and unpaid_invoices > 0


def _due_date(last_seen_at, closed_at):
    # Earliest of last_seen_at + 730 days and closed_at + 30 days.
    # Uses timedelta, not calendar years. Returns None when neither date is usable.
    candidates = []
    if last_seen_at is not None:
        candidates.append(last_seen_at + timedelta(days=INACTIVITY_DAYS))
    if closed_at is not None:
        candidates.append(closed_at + timedelta(days=CLOSED_GRACE_DAYS))
    return min(candidates) if candidates else None


def _action(account_id, action, due, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    actions = []
    delete_candidates = []  # entries of (sort_key, account_id, due)

    for acct in accounts:
        # Rule 1: a litigation hold blocks every action for the account.
        if acct.get("litigation_hold"):
            continue
        # Rule 2: staff accounts are never processed.
        if is_staff(acct.get("email")):
            continue

        last_seen = _as_date(acct.get("last_seen_at"))
        closed_at = _as_date(acct.get("closed_at"))
        due = _due_date(last_seen, closed_at)
        if due is None:
            # No usable date: do not guess.
            continue

        account_id = acct["id"]

        # Classification boundaries (each account gets at most one action):
        #   due <= today               -> due now: delete, or anonymise if unpaid
        #   today < due <= today + 14  -> warn window: warn unless closed_by == "member"
        #   due > today + 14           -> nothing
        if due <= today:
            if _has_unpaid(acct.get("unpaid_invoices")):
                # Anonymise is not subject to the cap.
                actions.append(_action(account_id, "anonymise", due, DPO_APPROVER))
            else:
                # Sort key: closed accounts (closed_at set) first, then earlier due, then id.
                priority = 0 if closed_at is not None else 1
                delete_candidates.append(((priority, due, account_id), account_id, due))
        elif due <= today + timedelta(days=WARN_WINDOW_DAYS):
            if acct.get("closed_by") != "member":
                actions.append(_action(account_id, "warn", due, None))

    # Only deletes count toward MAX_DELETIONS_PER_RUN. Candidates beyond the cap
    # get no action in this run and stay due for a later run.
    delete_candidates.sort(key=lambda c: c[0])
    for _, account_id, due in delete_candidates[:MAX_DELETIONS_PER_RUN]:
        actions.append(_action(account_id, "delete", due, DPO_APPROVER))

    actions.sort(key=lambda a: a["account_id"])
    return actions

# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-e18ogn87/gdpr_purge/tests/test_purge_plan.py
# NOTE: NOT EXECUTED. Run with `python3 -m unittest` from the gdpr_purge directory once tests/__init__.py exists (empty file).

import copy
import unittest
from collections import Counter
from datetime import date, timedelta

import purge_plan as pp

TODAY = date(2026, 10, 13)
DPO = "Tordis Svenbjorn Dottir"
EMAIL = "zq.member@zqdomain.test"


def make(**overrides):
    account = {
        "id": "acc-1",
        "email": EMAIL,
        "status": "active",
        "last_seen_at": TODAY,
        "last_login": None,
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
        "tenant": "tenant-x",
    }
    account.update(overrides)
    return account


def days_ago(n):
    return TODAY - timedelta(days=n)


def run(accounts):
    return pp.plan_purge(accounts, TODAY)


def by_id(accounts):
    return {a["account_id"]: a for a in run(accounts)}


class LastLoginIgnoredTests(unittest.TestCase):
    def test_old_last_login_with_recent_last_seen_produces_nothing(self):
        acct = make(last_login=date(2000, 1, 1), last_seen_at=days_ago(1))
        self.assertEqual(run([acct]), [])

    def test_recent_last_login_with_old_last_seen_is_inactive(self):
        acct = make(last_login=TODAY, last_seen_at=days_ago(730))
        self.assertEqual(by_id([acct])["acc-1"]["action"], "delete")


class InactivityAndClosureBoundaryTests(unittest.TestCase):
    def test_last_seen_exactly_730_days_ago_is_delete(self):
        plan = by_id([make(last_seen_at=days_ago(730))])
        self.assertEqual(plan["acc-1"]["action"], "delete")
        self.assertEqual(plan["acc-1"]["due"], TODAY.isoformat())

    def test_last_seen_729_days_ago_is_not_delete(self):
        plan = by_id([make(last_seen_at=days_ago(729))])
        self.assertNotEqual(plan["acc-1"]["action"], "delete")
        self.assertEqual(plan["acc-1"]["action"], "warn")  # due tomorrow

    def test_closed_exactly_30_days_ago_is_delete(self):
        plan = by_id([make(closed_at=days_ago(30), closed_by="member")])
        self.assertEqual(plan["acc-1"]["action"], "delete")

    def test_closed_29_days_ago_gives_nothing_when_not_otherwise_due(self):
        acct = make(closed_at=days_ago(29), closed_by="member")
        self.assertEqual(run([acct]), [])

    def test_closed_and_inactive_earlier_inactive_date_is_reported(self):
        acct = make(last_seen_at=days_ago(740), closed_at=days_ago(5), closed_by="member")
        plan = by_id([acct])
        self.assertEqual(plan["acc-1"]["action"], "delete")
        self.assertEqual(plan["acc-1"]["due"], days_ago(10).isoformat())

    def test_closed_and_inactive_earlier_closed_date_is_reported(self):
        acct = make(last_seen_at=days_ago(720), closed_at=days_ago(31), closed_by="staff")
        plan = by_id([acct])
        self.assertEqual(plan["acc-1"]["action"], "delete")
        self.assertEqual(plan["acc-1"]["due"], days_ago(1).isoformat())


class WarnWindowBoundaryTests(unittest.TestCase):
    def test_due_exactly_14_days_ahead_is_warn(self):
        plan = by_id([make(last_seen_at=days_ago(716))])
        self.assertEqual(plan["acc-1"]["action"], "warn")
        self.assertEqual(plan["acc-1"]["due"], (TODAY + timedelta(days=14)).isoformat())

    def test_due_15_days_ahead_gives_nothing(self):
        self.assertEqual(run([make(last_seen_at=days_ago(715))]), [])

    def test_due_today_is_delete_and_not_warn(self):
        actions = run([make(last_seen_at=days_ago(730))])
        self.assertEqual([a["action"] for a in actions], ["delete"])

    def test_due_tomorrow_is_warn(self):
        plan = by_id([make(last_seen_at=days_ago(729))])
        self.assertEqual(plan["acc-1"]["action"], "warn")

    def test_member_closed_account_in_window_is_not_warned(self):
        acct = make(closed_at=days_ago(20), closed_by="member")
        self.assertEqual(run([acct]), [])

    def test_staff_closed_account_in_window_is_warned(self):
        acct = make(closed_at=days_ago(20), closed_by="staff")
        plan = by_id([acct])
        self.assertEqual(plan["acc-1"]["action"], "warn")
        self.assertEqual(plan["acc-1"]["due"], (TODAY + timedelta(days=10)).isoformat())


class UnpaidInvoiceTests(unittest.TestCase):
    def test_unpaid_due_today_is_anonymise_not_delete(self):
        plan = by_id([make(last_seen_at=days_ago(730), unpaid_invoices=3)])
        self.assertEqual(plan["acc-1"]["action"], "anonymise")
        self.assertEqual(plan["acc-1"]["approved_by"], DPO)

    def test_unpaid_in_warn_window_still_warns(self):
        plan = by_id([make(last_seen_at=days_ago(729), unpaid_invoices=2)])
        self.assertEqual(plan["acc-1"]["action"], "warn")
        self.assertIsNone(plan["acc-1"]["approved_by"])

    def test_zero_none_and_false_unpaid_mean_delete(self):
        for value in (0, None, False):
            with self.subTest(value=value):
                plan = by_id([make(last_seen_at=days_ago(730), unpaid_invoices=value)])
                self.assertEqual(plan["acc-1"]["action"], "delete")


class LitigationHoldTests(unittest.TestCase):
    def test_hold_blocks_due_unpaid_and_warn_window_accounts(self):
        accounts = [
            make(id="due", last_seen_at=days_ago(730), litigation_hold=True),
            make(id="unpaid", last_seen_at=days_ago(730), unpaid_invoices=4, litigation_hold=True),
            make(id="warn", last_seen_at=days_ago(729), litigation_hold=True),
        ]
        self.assertEqual(run(accounts), [])


class StaffExclusionTests(unittest.TestCase):
    def test_staff_email_produces_nothing(self):
        acct = make(email="a.b@tidewater-klatring.no", last_seen_at=days_ago(730))
        self.assertEqual(run([acct]), [])

    def test_uppercase_staff_domain_produces_nothing(self):
        acct = make(email="A@TIDEWATER-KLATRING.NO", last_seen_at=days_ago(730))
        self.assertEqual(run([acct]), [])

    def test_lookalike_domains_are_not_staff_and_are_processed(self):
        accounts = [
            make(id="l1", email="x@tidewater-klatring.no.example.com", last_seen_at=days_ago(730)),
            make(id="l2", email="x@nottidewater-klatring.no", last_seen_at=days_ago(730)),
        ]
        plan = by_id(accounts)
        self.assertEqual(plan["l1"]["action"], "delete")
        self.assertEqual(plan["l2"]["action"], "delete")

    def test_missing_email_is_not_staff(self):
        plan = by_id([make(email=None, last_seen_at=days_ago(730))])
        self.assertEqual(plan["acc-1"]["action"], "delete")


class OutputShapeTests(unittest.TestCase):
    def test_actions_have_exactly_four_keys_and_no_email_fragments(self):
        accounts = [
            make(id="d", last_seen_at=days_ago(730)),
            make(id="u", last_seen_at=days_ago(730), unpaid_invoices=1),
            make(id="w", last_seen_at=days_ago(729)),
        ]
        actions = run(accounts)
        self.assertEqual(len(actions), 3)
        local, _, domain = EMAIL.partition("@")
        for action in actions:
            with self.subTest(account_id=action["account_id"]):
                self.assertEqual(set(action), {"account_id", "action", "due", "approved_by"})
                text = repr(action)
                self.assertNotIn(EMAIL, text)
                self.assertNotIn(local, text)
                self.assertNotIn(domain, text)


class DeletionCapTests(unittest.TestCase):
    def test_cap_keeps_exactly_200_deletes_and_drops_latest_due_extras(self):
        # Due date for index i is today - i, so the earliest due is the largest i.
        # Keeping the first 200 by due keeps i = 5..204 and drops i = 0..4.
        accounts = [make(id=f"a{i:03d}", last_seen_at=days_ago(730 + i)) for i in range(205)]
        actions = run(accounts)
        ids = {a["account_id"] for a in actions}
        self.assertEqual(sum(1 for a in actions if a["action"] == "delete"), 200)
        dropped = {f"a{i:03d}" for i in range(5)}
        self.assertEqual(ids & dropped, set())
        self.assertEqual(len(ids), 200)

    def test_closed_candidate_is_kept_over_inactive_candidate(self):
        accounts = [make(id=f"i{i:03d}", last_seen_at=days_ago(740)) for i in range(200)]
        accounts.append(
            make(id="c-closed", last_seen_at=TODAY, closed_at=days_ago(30), closed_by="staff")
        )
        actions = run(accounts)
        ids = {a["account_id"] for a in actions}
        self.assertEqual(sum(1 for a in actions if a["action"] == "delete"), 200)
        self.assertIn("c-closed", ids)
        self.assertNotIn("i199", ids)
        self.assertIn("i198", ids)

    def test_anonymise_does_not_count_toward_cap(self):
        accounts = [make(id=f"d{i:03d}", last_seen_at=days_ago(730)) for i in range(200)]
        accounts += [
            make(id=f"u{i:03d}", last_seen_at=days_ago(730), unpaid_invoices=1) for i in range(5)
        ]
        counts = Counter(a["action"] for a in run(accounts))
        self.assertEqual(counts, Counter({"delete": 200, "anonymise": 5}))


class ApprovalTests(unittest.TestCase):
    def test_delete_and_anonymise_approved_by_dpo_and_warn_has_none(self):
        accounts = [
            make(id="d", last_seen_at=days_ago(730)),
            make(id="u", last_seen_at=days_ago(730), unpaid_invoices=2),
            make(id="w", last_seen_at=days_ago(729)),
        ]
        plan = by_id(accounts)
        self.assertEqual(plan["d"]["approved_by"], DPO)
        self.assertEqual(plan["u"]["approved_by"], DPO)
        self.assertIsNone(plan["w"]["approved_by"])


class OrderingAndEdgeCaseTests(unittest.TestCase):
    def test_output_sorted_by_account_id_for_shuffled_input(self):
        accounts = [
            make(id="c-3", last_seen_at=days_ago(730), unpaid_invoices=1),
            make(id="a-1", last_seen_at=days_ago(730)),
            make(id="b-2", last_seen_at=days_ago(729)),
        ]
        self.assertEqual([a["account_id"] for a in run(accounts)], ["a-1", "b-2", "c-3"])

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(run([]), [])

    def test_input_is_not_mutated(self):
        accounts = [make(last_seen_at=days_ago(730), unpaid_invoices=1, closed_at=days_ago(3))]
        snapshot = copy.deepcopy(accounts)
        run(accounts)
        self.assertEqual(accounts, snapshot)

    def test_no_usable_dates_produces_nothing(self):
        self.assertEqual(run([make(last_seen_at=None, closed_at=None)]), [])

    def test_missing_last_seen_with_old_closure_is_delete(self):
        plan = by_id([make(last_seen_at=None, closed_at=days_ago(30), closed_by="member")])
        self.assertEqual(plan["acc-1"]["action"], "delete")
        self.assertEqual(plan["acc-1"]["due"], TODAY.isoformat())


if __name__ == "__main__":
    unittest.main()