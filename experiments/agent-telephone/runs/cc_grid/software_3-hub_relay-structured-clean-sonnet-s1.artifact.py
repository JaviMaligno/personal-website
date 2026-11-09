"""Tidewater Climbing GDPR member-account purge planner.

Note: the house rule (every action dict carries the account's `email`) is
followed, so action dicts have the extra key `email`. This conflicts with the
"exactly keys" wording of R1 and with R9, so the client should confirm it.
Exception messages never contain the email.
"""
import datetime as _dt
import json
import unittest

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
MAX_DELETES_PER_RUN = 200
STAFF_DOMAIN = "@tidewater-klatring.no"
DPO_NAME = "Þórdís Sveinbjörnsdóttir"


def _idkey(i):
    return (type(i).__name__, i)


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def _check_date(value, field, acc_id):
    if not isinstance(value, _dt.date):
        raise ValueError(f"Account {acc_id!r}: missing or invalid {field}")
    return value


def plan_purge(accounts, today):
    deletes, others = [], []
    for a in accounts:
        if a.get("litigation_hold") or _is_staff(a.get("email")):
            continue
        aid = a.get("id")
        seen = _check_date(a.get("last_seen_at"), "last_seen_at", aid)
        closed = a.get("closed_at")
        if closed is not None:
            _check_date(closed, "closed_at", aid)
        due = seen + _dt.timedelta(days=INACTIVITY_DAYS)
        if closed is not None:
            due = min(due, closed + _dt.timedelta(days=CLOSED_GRACE_DAYS))
        act = {"account_id": aid, "due": due.isoformat(), "email": a.get("email")}
        if due <= today:
            if a.get("unpaid_invoices"):
                act.update(action="anonymise", approved_by=DPO_NAME)
                others.append(act)
            else:
                act.update(action="delete", approved_by=DPO_NAME)
                deletes.append((0 if closed is not None else 1, due, _idkey(aid), act))
        elif (due <= today + _dt.timedelta(days=WARN_WINDOW_DAYS)
              and a.get("closed_by") != "member"):
            act.update(action="warn", approved_by=None)
            others.append(act)
    deletes.sort(key=lambda t: t[:3])
    result = others + [t[3] for t in deletes[:MAX_DELETES_PER_RUN]]
    result.sort(key=lambda r: _idkey(r["account_id"]))
    return result


class PurgeTests(unittest.TestCase):
    T = _dt.date(2026, 10, 13)

    def acc(self, i=1, **kw):
        d = dict(id=i, email="m@example.com", status="active",
                 last_seen_at=self.T - _dt.timedelta(days=10),
                 last_login=None, closed_at=None, closed_by=None,
                 unpaid_invoices=0, litigation_hold=False)
        d.update(kw)
        return d

    def run1(self, **kw):
        return plan_purge([self.acc(**kw)], self.T)

    def days(self, n):
        return self.T - _dt.timedelta(days=n)

    def test_empty(self):
        self.assertEqual(plan_purge([], self.T), [])

    def test_inactivity_boundary(self):
        r = self.run1(last_seen_at=self.days(730))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(r[0]["approved_by"], DPO_NAME)
        self.assertEqual(r[0]["due"], self.T.isoformat())
        r = self.run1(last_seen_at=self.days(729))
        self.assertEqual(r[0]["action"], "warn")
        self.assertEqual(r[0]["approved_by"], None)

    def test_closed_boundary(self):
        self.assertEqual(self.run1(closed_at=self.days(30))[0]["action"], "delete")
        self.assertEqual(self.run1(closed_at=self.days(29), closed_by="member"), [])

    def test_overdue_real_due(self):
        r = self.run1(last_seen_at=self.days(800))
        self.assertEqual(r[0]["due"], (self.days(800) + _dt.timedelta(days=730)).isoformat())

    def test_warn_window(self):
        self.assertEqual(self.run1(last_seen_at=self.days(730 - 14))[0]["action"], "warn")
        self.assertEqual(self.run1(last_seen_at=self.days(730 - 15)), [])

    def test_member_closed_no_warn(self):
        self.assertEqual(self.run1(closed_at=self.days(20), closed_by="member"), [])
        self.assertEqual(self.run1(closed_at=self.days(20), closed_by="staff")[0]["action"], "warn")
        self.assertEqual(self.run1(closed_at=self.days(20))[0]["action"], "warn")

    def test_unpaid(self):
        r = self.run1(last_seen_at=self.days(731), unpaid_invoices=2)
        self.assertEqual(r[0]["action"], "anonymise")
        self.assertEqual(r[0]["approved_by"], DPO_NAME)
        r = self.run1(last_seen_at=self.days(720), unpaid_invoices=2)
        self.assertEqual(r[0]["action"], "warn")

    def test_hold_and_staff(self):
        old = self.days(900)
        self.assertEqual(self.run1(last_seen_at=old, litigation_hold=True), [])
        self.assertEqual(self.run1(last_seen_at=old, email="  A@Tidewater-Klatring.NO "), [])
        self.assertEqual(len(self.run1(last_seen_at=old, email="x@tidewater-klatring.no.evil.com")), 1)
        self.assertEqual(len(self.run1(last_seen_at=old, email="x@notidewater-klatring.no")), 1)
        self.assertEqual(len(self.run1(last_seen_at=old, email=None)), 1)

    def test_last_login_ignored(self):
        old = self.days(900)
        a = self.run1(last_seen_at=old, last_login=self.T)
        b = self.run1(last_seen_at=old, last_login=None)
        self.assertEqual(a, b)

    def test_cap(self):
        accs = [self.acc(i, last_seen_at=self.days(800)) for i in range(205)]
        accs.append(self.acc(999, last_seen_at=self.days(731), closed_at=self.days(40)))
        accs.append(self.acc(1000, last_seen_at=self.days(900), unpaid_invoices=1))
        r = plan_purge(accs, self.T)
        dels = [x for x in r if x["action"] == "delete"]
        self.assertEqual(len(dels), 200)
        self.assertIn(999, [x["account_id"] for x in dels])
        self.assertIn(1000, [x["account_id"] for x in r])
        self.assertEqual([x["account_id"] for x in r], sorted(x["account_id"] for x in r))

    def test_sort_mixed_and_json(self):
        accs = [self.acc("b", last_seen_at=self.days(800)),
                self.acc(2, last_seen_at=self.days(800)),
                self.acc("a", last_seen_at=self.days(800))]
        r = plan_purge(accs, self.T)
        self.assertEqual([x["account_id"] for x in r], [2, "a", "b"])
        json.dumps(r)

    def test_bad_data(self):
        for bad in (None, "2020-01-01"):
            with self.assertRaises(ValueError) as cm:
                plan_purge([self.acc(7, last_seen_at=bad, email="secret@x.com")], self.T)
            self.assertIn("7", str(cm.exception))
            self.assertNotIn("secret", str(cm.exception))
        with self.assertRaises(ValueError):
            plan_purge([{"id": 1, "email": "e@x.com"}], self.T)

    def test_pure_and_tenant(self):
        a = self.acc(last_seen_at=self.days(800))
        a["tenant"] = "x"
        before = dict(a)
        plan_purge([a], self.T)
        self.assertEqual(a, before)


if __name__ == "__main__":
    unittest.main()