"""Tidewater Climbing GDPR clean-up planner.

plan_purge(accounts, today) returns the actions due on `today`. It is pure:
no I/O, no mutation of input, deterministic.

Open items for the tech lead, kept here because only code was requested:
- CONFLICT: the house rule requires every action dict to carry the account's
  `email`, while spec rule 9 forbids email addresses in output. This module
  follows the house rule and includes `email` on every action dict. Resolve
  before deployment. The no-email acceptance test is replaced by a check that
  output carries only the listed fields plus the house-rule email.
- Warning wording is contradictory in the client brief. Implemented reading:
  member-closed accounts never get warn; every other account in the window does.
  Still being confirmed with the client.
- Defaults for open client questions:
  (a) repeated warnings: a warn is emitted on every run inside the window.
  (b) anonymised accounts have no status marker and are picked up again later.
  (c) the 14-day warning window is inclusive of day 14.
  (d) the 200-delete cap counts only delete actions.
- Data errors raise ValueError: duplicate ids, missing email, non-date values,
  closed_at in the future, closed_by inconsistent with closed_at.
- unpaid_invoices None or missing is treated as unknown and anonymised.
- last_seen_at None with closed_at set uses the closure rule alone.
- Both dates None: no action.
- litigation_hold must be exactly False to be eligible. None, missing, or truthy blocks.
- Staff detection: email.strip().lower() ends with "@tidewater-klatring.no".
"""

import copy
import unittest
from datetime import date, datetime, timedelta

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSURE_DAYS = 30
WARN_DAYS = 14
DELETE_CAP = 200


def _opt_date(value, acc_id, field):
    if value is None:
        return None
    if isinstance(value, datetime) or not isinstance(value, date):
        raise ValueError("account %r: %s must be a date or None" % (acc_id, field))
    return value


def _action(acc_id, action, due, email):
    return {
        "account_id": acc_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else APPROVER,
        "email": email,
    }


def plan_purge(accounts, today):
    if not isinstance(today, date) or isinstance(today, datetime):
        raise TypeError("today must be a datetime.date")
    horizon = today + timedelta(days=WARN_DAYS)
    seen = set()
    deletes = []  # (closed_group, due, account_id, email)
    actions = []
    for acc in accounts:
        acc_id = acc["id"]
        if acc_id in seen:
            raise ValueError("duplicate account id: %r" % (acc_id,))
        seen.add(acc_id)

        email = acc.get("email")
        if not isinstance(email, str):
            raise ValueError("account %r: email missing" % (acc_id,))

        last_seen = _opt_date(acc.get("last_seen_at"), acc_id, "last_seen_at")
        closed_at = _opt_date(acc.get("closed_at"), acc_id, "closed_at")
        closed_by = acc.get("closed_by")
        if closed_at is None:
            if closed_by is not None:
                raise ValueError("account %r: closed_by set without closed_at" % (acc_id,))
        else:
            if closed_by not in ("member", "staff"):
                raise ValueError("account %r: closed_by inconsistent with closed_at" % (acc_id,))
            if closed_at > today:
                raise ValueError("account %r: closed_at is in the future" % (acc_id,))

        if acc.get("litigation_hold") is not False:
            continue
        if email.strip().lower().endswith(STAFF_DOMAIN):
            continue

        cands = []
        if last_seen is not None:
            cands.append(last_seen + timedelta(days=INACTIVITY_DAYS))
        if closed_at is not None:
            cands.append(closed_at + timedelta(days=CLOSURE_DAYS))
        if not cands:
            continue
        due = min(cands)

        if due <= today:
            unpaid = acc.get("unpaid_invoices")
            if unpaid is None or unpaid:
                actions.append(_action(acc_id, "anonymise", due, email))
            else:
                deletes.append((0 if closed_at is not None else 1, due, acc_id, email))
        elif due <= horizon and closed_by != "member":
            actions.append(_action(acc_id, "warn", due, email))

    deletes.sort(key=lambda t: (t[0], t[1], t[2]))
    for _, due, acc_id, email in deletes[:DELETE_CAP]:
        actions.append(_action(acc_id, "delete", due, email))

    actions.sort(key=lambda a: a["account_id"])
    return actions


TODAY = date(2026, 10, 13)


def _d(offset):
    return TODAY + timedelta(days=offset)


def _acct(acc_id, **kw):
    base = {
        "id": acc_id,
        "email": "member%s@example.com" % (acc_id,),
        "status": "active",
        "last_seen_at": None,
        "last_login": None,
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
    }
    base.update(kw)
    return base


class PlanPurgeTests(unittest.TestCase):

    def test_delete_exactly_730_days(self):
        out = plan_purge([_acct(1, last_seen_at=_d(-730))], TODAY)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], TODAY.isoformat())
        self.assertEqual(out[0]["approved_by"], APPROVER)

    def test_warn_at_day_14(self):
        out = plan_purge([_acct(1, last_seen_at=_d(14 - 730))], TODAY)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "warn")
        self.assertEqual(out[0]["due"], _d(14).isoformat())
        self.assertIsNone(out[0]["approved_by"])

    def test_nothing_at_day_15(self):
        self.assertEqual(plan_purge([_acct(1, last_seen_at=_d(15 - 730))], TODAY), [])

    def test_last_login_ignored(self):
        acc = _acct(1, last_seen_at=_d(-10), last_login=date(2000, 1, 1))
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_member_closed_is_delete_without_earlier_warning(self):
        due_now = _acct(1, closed_at=_d(-30), closed_by="member", last_seen_at=_d(-100))
        out = plan_purge([due_now], TODAY)
        self.assertEqual([o["action"] for o in out], ["delete"])
        self.assertEqual(out[0]["due"], TODAY.isoformat())
        in_window = _acct(2, closed_at=_d(-20), closed_by="member")
        self.assertEqual(plan_purge([in_window], TODAY), [])

    def test_staff_closed_in_window_warns(self):
        acc = _acct(1, closed_at=_d(-20), closed_by="staff")
        out = plan_purge([acc], TODAY)
        self.assertEqual(out[0]["action"], "warn")
        self.assertEqual(out[0]["due"], _d(10).isoformat())

    def test_closure_earlier_than_inactivity_uses_closure_date(self):
        acc = _acct(1, last_seen_at=_d(-700), closed_at=_d(-40), closed_by="staff")
        out = plan_purge([acc], TODAY)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], _d(-10).isoformat())

    def test_unpaid_invoices_anonymise(self):
        acc = _acct(1, last_seen_at=_d(-730), unpaid_invoices=2)
        out = plan_purge([acc], TODAY)
        self.assertEqual(out[0]["action"], "anonymise")
        self.assertEqual(out[0]["approved_by"], APPROVER)

    def test_unpaid_none_anonymise(self):
        out = plan_purge([_acct(1, last_seen_at=_d(-730), unpaid_invoices=None)], TODAY)
        self.assertEqual(out[0]["action"], "anonymise")

    def test_litigation_hold_blocks_everything(self):
        due = _acct(1, last_seen_at=_d(-730), litigation_hold=True)
        not_due = _acct(2, last_seen_at=_d(-730 + 5), litigation_hold=True)
        missing = _acct(3, last_seen_at=_d(-730), litigation_hold=None)
        self.assertEqual(plan_purge([due, not_due, missing], TODAY), [])

    def test_staff_email_any_case_blocked(self):
        accs = [
            _acct(1, email="Anna.K@Tidewater-Klatring.NO", last_seen_at=_d(-800)),
            _acct(2, email="x@tidewater-klatring.no", last_seen_at=_d(-800)),
        ]
        self.assertEqual(plan_purge(accs, TODAY), [])

    def test_delete_cap_and_ordering(self):
        accs = []
        for i in range(50):
            accs.append(_acct("c%03d" % i, closed_at=_d(-30), closed_by="member"))
        for i in range(200):
            accs.append(_acct("n%03d" % i, last_seen_at=_d(-730 - i)))
        for i in range(3):
            accs.append(_acct("a%03d" % i, last_seen_at=_d(-800), unpaid_invoices=2))
        out = plan_purge(accs, TODAY)
        deletes = [o for o in out if o["action"] == "delete"]
        anon = [o for o in out if o["action"] == "anonymise"]
        self.assertEqual(len(deletes), DELETE_CAP)
        self.assertEqual(len(anon), 3)
        got = {o["account_id"] for o in deletes}
        closed_ids = {"c%03d" % i for i in range(50)}
        self.assertTrue(closed_ids <= got)
        # Unclosed deletes: earliest due first. Due for n<i> is TODAY - i,
        # so the 150 kept are the largest i values.
        expected_unclosed = {"n%03d" % i for i in range(50, 200)}
        self.assertEqual(got - closed_ids, expected_unclosed)

    def test_sorted_output_and_house_rule_fields(self):
        accs = [_acct(i, last_seen_at=_d(-730)) for i in (5, 2, 9)]
        out = plan_purge(accs, TODAY)
        self.assertEqual([o["account_id"] for o in out], [2, 5, 9])
        for o in out:
            self.assertEqual(set(o), {"account_id", "action", "due", "approved_by", "email"})
            self.assertEqual(o["email"], "member%s@example.com" % o["account_id"])

    def test_both_dates_none_no_action(self):
        self.assertEqual(plan_purge([_acct(1)], TODAY), [])

    def test_missing_last_seen_uses_closure_rule(self):
        acc = _acct(1, last_seen_at=None, closed_at=_d(-30), closed_by="member")
        out = plan_purge([acc], TODAY)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], TODAY.isoformat())

    def test_duplicate_ids_raise(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct(1), _acct(1)], TODAY)

    def test_future_closed_at_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct(1, closed_at=_d(1), closed_by="member")], TODAY)

    def test_inconsistent_closed_by_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct(1, closed_at=_d(-5), closed_by=None)], TODAY)
        with self.assertRaises(ValueError):
            plan_purge([_acct(1, closed_at=None, closed_by="member")], TODAY)

    def test_input_not_mutated_and_deterministic(self):
        accs = [
            _acct(1, last_seen_at=_d(-730)),
            _acct(2, closed_at=_d(-20), closed_by="staff"),
        ]
        snapshot = copy.deepcopy(accs)
        first = plan_purge(accs, TODAY)
        second = plan_purge(accs, TODAY)
        self.assertEqual(accs, snapshot)
        self.assertEqual(first, second)

    def test_approver_is_utf8_exact(self):
        out = plan_purge([_acct(1, last_seen_at=_d(-730))], TODAY)
        self.assertEqual(out[0]["approved_by"], "Þórdís Sveinbjörnsdóttir")


if __name__ == "__main__":
    unittest.main()