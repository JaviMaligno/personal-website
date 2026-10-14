"""GDPR purge planner for Tidewater Climbing member accounts.

Pure function module: no I/O and no clock reads. Every decision derives from
the `today` argument. Run this file directly to execute the unit tests.

Ambiguities resolved with defaults (for tech lead confirmation):
- Warnings go to member-closed accounts too. The brief contradicts itself on
  this, so the implementation warns them.
- The 200-delete cap applies only to delete actions. Anonymise is uncapped.
- Held and staff accounts are still validated (id, dates) before exclusion,
  so malformed records fail loudly even when they would be skipped.
- litigation_hold is checked for truthiness, so a hold fails closed.
- A non-None closed_at that is not a datetime.date raises ValueError.
- datetime.datetime values are rejected wherever a date is required.
"""

import datetime as _dt
import json
import unittest
from datetime import date, timedelta

DPO = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200


def _require_date(value, field, account_id):
    if not isinstance(value, date) or isinstance(value, _dt.datetime):
        raise ValueError(
            f"account {account_id!r}: {field} must be a datetime.date, got {value!r}"
        )
    return value


def _action(account_id, action, due, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    if not isinstance(today, date) or isinstance(today, _dt.datetime):
        raise ValueError("today must be a datetime.date")

    seen_ids = set()
    candidates = []
    for acc in accounts:
        acc_id = acc.get("id")
        if acc_id is None:
            raise ValueError("account is missing id")
        if acc_id in seen_ids:
            raise ValueError(f"duplicate account id {acc_id!r}")
        seen_ids.add(acc_id)

        last_seen = _require_date(acc.get("last_seen_at"), "last_seen_at", acc_id)
        closed_at = acc.get("closed_at")
        if closed_at is not None:
            closed_at = _require_date(closed_at, "closed_at", acc_id)

        if acc.get("litigation_hold"):
            continue
        email = acc.get("email")
        if isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN):
            continue

        due = last_seen + timedelta(days=INACTIVITY_DAYS)
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=CLOSED_GRACE_DAYS))
        owes = (acc.get("unpaid_invoices") or 0) > 0
        candidates.append((acc_id, due, closed_at is not None, owes))

    actions = []
    deletes = []
    warn_horizon = today + timedelta(days=WARN_WINDOW_DAYS)
    for acc_id, due, closed, owes in candidates:
        if due <= today:
            if owes:
                actions.append(_action(acc_id, "anonymise", due, DPO))
            else:
                deletes.append((closed, due, acc_id))
        elif due <= warn_horizon:
            actions.append(_action(acc_id, "warn", due, None))

    # Closed accounts first (True sorts after False, so negate), then due, then id.
    deletes.sort(key=lambda t: (not t[0], t[1], t[2]))
    for closed, due, acc_id in deletes[:DELETE_CAP]:
        actions.append(_action(acc_id, "delete", due, DPO))

    actions.sort(key=lambda a: a["account_id"])
    return actions


def _acc(i, last_seen, closed_at=None, unpaid=0, hold=False, email=None):
    return {
        "id": i,
        "email": email if email is not None else f"member{i}@example.com",
        "status": "active",
        "last_seen_at": last_seen,
        "last_login": None,
        "closed_at": closed_at,
        "closed_by": "member" if closed_at else None,
        "unpaid_invoices": unpaid,
        "litigation_hold": hold,
        "tenant": "legacy",
    }


TODAY = date(2026, 10, 13)
DUE_TODAY_SEEN = TODAY - timedelta(days=INACTIVITY_DAYS)


class PlanPurgeTests(unittest.TestCase):
    def test_due_exactly_today_deletes(self):
        out = plan_purge([_acc(1, DUE_TODAY_SEEN)], TODAY)
        self.assertEqual(out, [
            {"account_id": 1, "action": "delete", "due": TODAY.isoformat(), "approved_by": DPO}
        ])

    def test_warn_at_fourteen_days(self):
        seen = TODAY + timedelta(days=14) - timedelta(days=INACTIVITY_DAYS)
        out = plan_purge([_acc(1, seen)], TODAY)
        self.assertEqual(out, [
            {"account_id": 1, "action": "warn",
             "due": (TODAY + timedelta(days=14)).isoformat(), "approved_by": None}
        ])

    def test_nothing_at_fifteen_days(self):
        seen = TODAY + timedelta(days=15) - timedelta(days=INACTIVITY_DAYS)
        self.assertEqual(plan_purge([_acc(1, seen)], TODAY), [])

    def test_closed_earlier_than_730_uses_closed_date(self):
        acc = _acc(1, TODAY - timedelta(days=100), closed_at=TODAY - timedelta(days=30))
        out = plan_purge([acc], TODAY)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], TODAY.isoformat())

    def test_closed_later_than_730_does_not_extend(self):
        acc = _acc(1, DUE_TODAY_SEEN, closed_at=TODAY)
        out = plan_purge([acc], TODAY)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], TODAY.isoformat())

    def test_deletes_capped_at_200_closed_first(self):
        accounts = []
        for i in range(250):
            if i >= 200:
                accounts.append(_acc(i, DUE_TODAY_SEEN, closed_at=TODAY - timedelta(days=100)))
            else:
                accounts.append(_acc(i, DUE_TODAY_SEEN))
        out = plan_purge(accounts, TODAY)
        deleted = {a["account_id"] for a in out if a["action"] == "delete"}
        self.assertEqual(len(deleted), 200)
        self.assertTrue(set(range(200, 250)).issubset(deleted))
        self.assertEqual(deleted - set(range(200, 250)), set(range(0, 150)))

    def test_anonymise_is_uncapped(self):
        accounts = [_acc(i, DUE_TODAY_SEEN, unpaid=1) for i in range(250)]
        out = plan_purge(accounts, TODAY)
        self.assertEqual(len(out), 250)
        self.assertTrue(all(a["action"] == "anonymise" for a in out))
        self.assertTrue(all(a["approved_by"] == DPO for a in out))

    def test_held_account_with_unpaid_invoices_yields_nothing(self):
        acc = _acc(1, DUE_TODAY_SEEN, unpaid=2, hold=True)
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_mixed_case_staff_domain_yields_nothing(self):
        acc = _acc(1, DUE_TODAY_SEEN, email="  Ana@Tidewater-Klatring.NO ")
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_no_email_in_output(self):
        accounts = [
            _acc(1, DUE_TODAY_SEEN, email="secret.member@example.com"),
            _acc(2, DUE_TODAY_SEEN, unpaid=1, email="other.member@example.com"),
        ]
        dumped = json.dumps(plan_purge(accounts, TODAY))
        self.assertNotIn("@", dumped)
        self.assertNotIn("example.com", dumped)

    def test_sorted_by_account_id(self):
        accounts = [_acc(i, DUE_TODAY_SEEN) for i in (5, 1, 3)]
        out = plan_purge(accounts, TODAY)
        self.assertEqual([a["account_id"] for a in out], [1, 3, 5])

    def test_json_round_trip_of_approver_name(self):
        out = plan_purge([_acc(1, DUE_TODAY_SEEN, unpaid=1)], TODAY)
        for ensure_ascii in (True, False):
            text = json.dumps(out, ensure_ascii=ensure_ascii)
            self.assertEqual(json.loads(text), out)
            self.assertEqual(json.loads(text)[0]["approved_by"], DPO)

    def test_missing_last_seen_raises(self):
        acc = _acc(1, DUE_TODAY_SEEN)
        acc["last_seen_at"] = None
        with self.assertRaises(ValueError):
            plan_purge([acc], TODAY)
        del acc["last_seen_at"]
        with self.assertRaises(ValueError):
            plan_purge([acc], TODAY)

    def test_duplicate_ids_raise(self):
        with self.assertRaises(ValueError):
            plan_purge([_acc(1, DUE_TODAY_SEEN), _acc(1, DUE_TODAY_SEEN)], TODAY)

    def test_closed_at_none_is_valid(self):
        out = plan_purge([_acc(1, DUE_TODAY_SEEN, closed_at=None)], TODAY)
        self.assertEqual(out[0]["action"], "delete")


if __name__ == "__main__":
    unittest.main()