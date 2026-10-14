# -*- coding: utf-8 -*-
"""GDPR retention purge planner for Tidewater Climbing.

Pure standard library. Entry point: plan_purge(accounts, today).
Unit tests are embedded at the bottom; run with: python3 -I gdpr_purge.py
"""
from copy import deepcopy
from datetime import date, datetime, timedelta
import unittest

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
MAX_DELETIONS_PER_RUN = 200
DPO_APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"
# UNCONFIRMED: pending client confirmation. When False, accounts closed by the
# member themselves get no warn action.
SEND_WARNING_TO_SELF_CLOSED = False

_REQUIRED_KEYS = (
    "id", "email", "last_seen_at", "closed_at",
    "closed_by", "unpaid_invoices", "litigation_hold",
)


def _is_plain_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _validate(accounts, today):
    if not isinstance(accounts, list):
        raise TypeError("accounts must be a list")
    if not _is_plain_date(today):
        raise TypeError("today must be a datetime.date")
    for account in accounts:
        if not isinstance(account, dict):
            raise TypeError("every account must be a dict")

    seen_ids = set()
    id_kind = None
    for account in accounts:
        for key in _REQUIRED_KEYS:
            if key not in account:
                raise ValueError(
                    f"account {account.get('id')!r} is missing key {key!r}")

        acct_id = account["id"]
        if isinstance(acct_id, str) and acct_id:
            kind = str
        elif isinstance(acct_id, int) and not isinstance(acct_id, bool):
            kind = int
        else:
            raise ValueError(
                f"invalid account id {acct_id!r}: must be a non-empty str or int")
        if id_kind is None:
            id_kind = kind
        elif kind is not id_kind:
            raise ValueError(f"account {acct_id!r} mixes str and int ids")
        if acct_id in seen_ids:
            raise ValueError(f"duplicate account id {acct_id!r}")
        seen_ids.add(acct_id)

        if not isinstance(account["email"], str):
            raise ValueError(f"account {acct_id!r}: email must be a str")
        if not _is_plain_date(account["last_seen_at"]):
            raise ValueError(f"account {acct_id!r}: last_seen_at must be a date")

        closed_at = account["closed_at"]
        closed_by = account["closed_by"]
        if closed_at is None:
            if closed_by is not None:
                raise ValueError(
                    f"account {acct_id!r}: closed_by must be None when closed_at is None")
        else:
            if not _is_plain_date(closed_at):
                raise ValueError(
                    f"account {acct_id!r}: closed_at must be None or a date")
            if closed_by not in ("member", "staff"):
                raise ValueError(
                    f"account {acct_id!r}: closed_by must be 'member' or 'staff'")

        unpaid = account["unpaid_invoices"]
        if not isinstance(unpaid, int) or isinstance(unpaid, bool) or unpaid < 0:
            raise ValueError(
                f"account {acct_id!r}: unpaid_invoices must be a non-negative int")

        if not isinstance(account["litigation_hold"], bool):
            raise ValueError(f"account {acct_id!r}: litigation_hold must be a bool")


def _effective_due(account):
    due = account["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
    if account["closed_at"] is not None:
        due = min(due, account["closed_at"] + timedelta(days=CLOSED_GRACE_DAYS))
    return due


def _is_staff(email):
    return email.strip().lower().endswith(STAFF_EMAIL_SUFFIX)


def _action(account_id, action, due, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def _decide(account, today):
    """Return an action dict, or None. Deletions are returned as candidates
    and are capped later in plan_purge."""
    if _is_staff(account["email"]):
        return None
    if account["litigation_hold"]:
        return None

    due = _effective_due(account)
    acct_id = account["id"]

    if due <= today:
        if account["unpaid_invoices"] > 0:
            return _action(acct_id, "anonymise", due, DPO_APPROVER)
        return _action(acct_id, "delete", due, DPO_APPROVER)

    if due <= today + timedelta(days=WARN_WINDOW_DAYS):
        if account["closed_by"] == "member" and not SEND_WARNING_TO_SELF_CLOSED:
            return None
        return _action(acct_id, "warn", due, None)

    return None


def _deletion_sort_key(account):
    if account["closed_at"] is not None:
        return (0, account["closed_at"], account["id"])
    return (1, account["last_seen_at"], account["id"])


def _select_deletions(candidates):
    """candidates: list of (account, delete_action) pairs. Returns at most
    MAX_DELETIONS_PER_RUN actions, oldest first."""
    ordered = sorted(candidates, key=lambda pair: _deletion_sort_key(pair[0]))
    return [action for _, action in ordered[:MAX_DELETIONS_PER_RUN]]


def plan_purge(accounts, today):
    _validate(accounts, today)

    actions = []
    deletion_candidates = []
    for account in accounts:
        action = _decide(account, today)
        if action is None:
            continue
        if action["action"] == "delete":
            deletion_candidates.append((account, action))
        else:
            actions.append(action)

    actions.extend(_select_deletions(deletion_candidates))
    actions.sort(key=lambda a: a["account_id"])
    return actions


# ---------------------------------------------------------------------------
# Tests (unittest, embedded in the module)
# ---------------------------------------------------------------------------

TODAY = date(2026, 10, 13)
DAY = timedelta(days=1)


def _acct(acct_id, last_seen=TODAY, closed_at=None, closed_by=None,
          unpaid=0, hold=False, email=None):
    return {
        "id": acct_id,
        "email": f"m{acct_id}@example.com" if email is None else email,
        "status": "active",
        "last_seen_at": last_seen,
        "last_login": None,
        "closed_at": closed_at,
        "closed_by": closed_by,
        "unpaid_invoices": unpaid,
        "litigation_hold": hold,
    }


def _seen_for_due(due):
    return due - timedelta(days=INACTIVITY_DAYS)


class PlanPurgeTests(unittest.TestCase):

    def test_empty_input(self):
        self.assertEqual(plan_purge([], TODAY), [])

    def test_staff_due_produces_nothing(self):
        for email in ("a@tidewater-klatring.no", "A@Tidewater-Klatring.NO"):
            with self.subTest(email=email):
                a = _acct(1, last_seen=TODAY - 800 * DAY, email=email)
                self.assertEqual(plan_purge([a], TODAY), [])

    def test_lookalike_domain_is_treated_as_member(self):
        a = _acct(1, last_seen=TODAY - 800 * DAY,
                  email="x@tidewater-klatring.no.example.com")
        out = plan_purge([a], TODAY)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "delete")

    def test_litigation_hold_produces_nothing(self):
        due_now = _acct(1, last_seen=TODAY - 800 * DAY, hold=True)
        warn_soon = _acct(2, last_seen=_seen_for_due(TODAY + 5 * DAY), hold=True)
        self.assertEqual(plan_purge([due_now, warn_soon], TODAY), [])

    def test_self_closed_member_due_in_10_days_gets_no_warn(self):
        a = _acct(1, last_seen=TODAY - DAY, closed_at=TODAY - 20 * DAY,
                  closed_by="member")
        self.assertEqual(plan_purge([a], TODAY), [])

    def test_self_closed_member_due_today_gets_delete(self):
        a = _acct(1, last_seen=TODAY - DAY, closed_at=TODAY - 30 * DAY,
                  closed_by="member")
        out = plan_purge([a], TODAY)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "delete")

    def test_staff_closed_due_in_10_days_gets_warn(self):
        a = _acct(1, last_seen=TODAY - DAY, closed_at=TODAY - 20 * DAY,
                  closed_by="staff")
        out = plan_purge([a], TODAY)
        self.assertEqual([x["action"] for x in out], ["warn"])

    def test_invoice_due_anonymised_and_outside_cap(self):
        accounts = [_acct(i, last_seen=TODAY - 800 * DAY) for i in range(200)]
        accounts.append(_acct(999, last_seen=TODAY - 800 * DAY, unpaid=1))
        out = plan_purge(accounts, TODAY)
        deletes = [a for a in out if a["action"] == "delete"]
        anon = [a for a in out if a["action"] == "anonymise"]
        self.assertEqual(len(deletes), 200)
        self.assertEqual(len(anon), 1)
        self.assertEqual(anon[0]["account_id"], 999)
        self.assertEqual(anon[0]["approved_by"], DPO_APPROVER)

    def test_boundaries(self):
        cases = [(-5, "delete"), (0, "delete"), (1, "warn"),
                 (14, "warn"), (15, None)]
        for i, (offset, expected) in enumerate(cases):
            with self.subTest(offset=offset):
                due = TODAY + offset * DAY
                a = _acct(i, last_seen=_seen_for_due(due))
                out = plan_purge([a], TODAY)
                if expected is None:
                    self.assertEqual(out, [])
                else:
                    self.assertEqual(len(out), 1)
                    self.assertEqual(out[0]["action"], expected)
                    self.assertEqual(out[0]["due"], due.isoformat())

    def test_closed_earlier_date_is_used(self):
        a = _acct(1, last_seen=TODAY - 10 * DAY, closed_at=TODAY - 60 * DAY,
                  closed_by="staff")
        out = plan_purge([a], TODAY)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], (TODAY - 30 * DAY).isoformat())

    def test_cap_prefers_closed_then_oldest_inactive(self):
        inactive = [_acct(i, last_seen=TODAY - timedelta(days=730 + i))
                    for i in range(250)]
        closed = _acct(1000, last_seen=TODAY, closed_at=TODAY - 40 * DAY,
                       closed_by="staff")
        out = plan_purge(inactive + [closed], TODAY)
        deletes = {a["account_id"] for a in out if a["action"] == "delete"}
        self.assertEqual(len(deletes), 200)
        self.assertIn(1000, deletes)
        # Oldest 199 inactive accounts are i = 51..249 (largest i = oldest).
        self.assertEqual(deletes - {1000}, set(range(51, 250)))
        # Leftovers get no action at all.
        self.assertTrue({a["account_id"] for a in out}.isdisjoint(range(0, 51)))

    def test_output_sorted_by_account_id(self):
        accounts = [_acct(i, last_seen=TODAY - 800 * DAY) for i in [9, 1, 5, 3]]
        out = plan_purge(accounts, TODAY)
        self.assertEqual([a["account_id"] for a in out], [1, 3, 5, 9])

    def test_no_leakage_of_personal_data(self):
        accounts = [
            _acct(1, last_seen=TODAY - 800 * DAY, email="secret1@example.com"),
            _acct(2, last_seen=_seen_for_due(TODAY + 3 * DAY),
                  email="secret2@example.com"),
        ]
        out = plan_purge(accounts, TODAY)
        self.assertEqual(len(out), 2)
        for a in out:
            self.assertEqual(set(a.keys()),
                             {"account_id", "action", "due", "approved_by"})
        text = str(out)
        self.assertNotIn("secret1@example.com", text)
        self.assertNotIn("secret2@example.com", text)

    def test_field_types_and_approvers(self):
        due_now = _acct(1, last_seen=TODAY - 800 * DAY)
        warn_soon = _acct(2, last_seen=_seen_for_due(TODAY + 2 * DAY))
        out = {a["account_id"]: a for a in plan_purge([due_now, warn_soon], TODAY)}
        self.assertIsInstance(out[1]["due"], str)
        self.assertEqual(out[1]["approved_by"], DPO_APPROVER)
        self.assertIsNone(out[2]["approved_by"])

    def test_tenant_key_ignored(self):
        a = _acct(1, last_seen=TODAY - 800 * DAY)
        a["tenant"] = object()
        self.assertEqual(len(plan_purge([a], TODAY)), 1)

    def test_input_not_mutated(self):
        accounts = [
            _acct(1, last_seen=TODAY - 800 * DAY),
            _acct(2, last_seen=TODAY - DAY, closed_at=TODAY - 20 * DAY,
                  closed_by="staff"),
        ]
        before = deepcopy(accounts)
        plan_purge(accounts, TODAY)
        self.assertEqual(accounts, before)

    def test_type_errors(self):
        cases = [
            ("tuple accounts", lambda: plan_purge(tuple(), TODAY)),
            ("non-dict element", lambda: plan_purge(["x"], TODAY)),
            ("datetime today", lambda: plan_purge([], datetime(2026, 10, 13))),
            ("str today", lambda: plan_purge([], "2026-10-13")),
        ]
        for name, call in cases:
            with self.subTest(name):
                with self.assertRaises(TypeError):
                    call()

    def test_value_errors(self):
        cases = []
        a = _acct(1)
        del a["email"]
        cases.append(("missing key", [a]))
        cases.append(("duplicate id", [_acct(1), _acct(1)]))
        cases.append(("None last_seen", [_acct(1, last_seen=None)]))
        cases.append(("closed_by without closed_at", [_acct(1, closed_by="member")]))
        cases.append(("bad closed_by", [_acct(1, closed_at=TODAY - DAY, closed_by="robot")]))
        cases.append(("negative invoices", [_acct(1, unpaid=-1)]))
        cases.append(("bool invoices", [_acct(1, unpaid=True)]))
        cases.append(("non-bool hold", [_acct(1, hold="yes")]))
        cases.append(("non-str email", [_acct(1, email=123)]))
        cases.append(("mixed id types", [_acct(1), _acct("2")]))
        cases.append(("empty id", [_acct("")]))
        cases.append(("datetime last_seen", [_acct(1, last_seen=datetime(2026, 10, 13))]))
        cases.append(("datetime closed_at",
                      [_acct(1, closed_at=datetime(2026, 10, 1), closed_by="member")]))
        for name, accounts in cases:
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    plan_purge(accounts, TODAY)

    def test_error_names_offending_id(self):
        with self.assertRaises(ValueError) as cm:
            plan_purge([_acct(42), _acct(42)], TODAY)
        self.assertIn("42", str(cm.exception))


if __name__ == "__main__":
    unittest.main()