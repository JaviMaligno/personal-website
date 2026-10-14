"""Tidewater Climbing GDPR purge planner.

Note: R9 (no email in actions) conflicts with the house rule that every action
dict carries the account's `email`. The house rule is followed here, so action
keys are R1's four keys plus `email`. Remove the "email" entry in _act to
restore strict R9.
"""
import datetime as dt
import json
import unittest

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
CAP = 200


def _chk(v, name, allow_none=False):
    if v is None and allow_none:
        return None
    if isinstance(v, dt.datetime) or not isinstance(v, dt.date):
        raise TypeError(f"{name} must be a datetime.date (not datetime), got {v!r}")
    return v


def _act(a, action, due, approved):
    return {"account_id": a["id"], "action": action, "due": due.isoformat(),
            "approved_by": approved, "email": a.get("email")}


def plan_purge(accounts, today):
    _chk(today, "today")
    horizon = today + dt.timedelta(days=40)
    removals, warns = [], []
    for a in accounts:
        seen = _chk(a.get("last_seen_at"), "last_seen_at", True)
        closed = _chk(a.get("closed_at"), "closed_at", True)
        if a.get("litigation_hold"):
            continue
        email = a.get("email")
        if isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN):
            continue
        if seen is None:
            continue
        due = seen + dt.timedelta(days=730)
        if closed is not None:
            due = min(due, closed + dt.timedelta(days=30))
        if due <= today:
            kind = "anonymise" if a.get("unpaid_invoices") else "delete"
            removals.append(((0 if closed is not None else 1, due, a["id"]),
                             _act(a, kind, due, APPROVER)))
        elif due <= horizon and a.get("closed_by") != "member":
            warns.append(_act(a, "warn", due, None))
    removals.sort(key=lambda r: r[0])
    out = [r[1] for r in removals[:CAP]] + warns
    out.sort(key=lambda x: x["account_id"])
    return out


# ---------------------------------------------------------------- tests
T = dt.date(2026, 10, 13)
D = dt.timedelta


def acc(id=1, **kw):
    base = dict(id=id, email="m@example.com", status="active",
                last_seen_at=T, last_login=None, closed_at=None,
                closed_by=None, unpaid_invoices=0, litigation_hold=False)
    base.update(kw)
    return base


class PurgeTests(unittest.TestCase):
    def one(self, **kw):
        return plan_purge([acc(**kw)], T)

    def test_empty(self):
        self.assertEqual(plan_purge([], T), [])

    def test_inactivity_edges(self):
        r = self.one(last_seen_at=dt.date(2024, 10, 13))
        self.assertEqual((r[0]["action"], r[0]["due"], r[0]["approved_by"]),
                         ("delete", "2026-10-13", APPROVER))
        r = self.one(last_seen_at=dt.date(2024, 10, 14))
        self.assertEqual(r[0]["action"], "warn")
        self.assertIsNone(r[0]["approved_by"])

    def test_overdue(self):
        self.assertEqual(self.one(last_seen_at=dt.date(2000, 1, 1))[0]["action"], "delete")

    def test_closed_edges(self):
        r = self.one(closed_at=dt.date(2026, 9, 13), closed_by="staff")
        self.assertEqual(r[0]["action"], "delete")
        r = self.one(closed_at=dt.date(2026, 9, 14), closed_by="staff")
        self.assertEqual(r[0]["action"], "warn")

    def test_warn_window(self):
        self.assertEqual(self.one(last_seen_at=T - D(730) + D(40))[0]["due"], "2026-11-22")
        self.assertEqual(self.one(last_seen_at=T - D(730) + D(41)), [])

    def test_member_closed_no_warn(self):
        self.assertEqual(self.one(closed_at=T - D(10), closed_by="member"), [])

    def test_unpaid(self):
        self.assertEqual(self.one(last_seen_at=T - D(730), unpaid_invoices=[1])[0]["action"],
                         "anonymise")
        self.assertEqual(self.one(last_seen_at=T - D(700), unpaid_invoices=2)[0]["action"], "warn")

    def test_hold(self):
        self.assertEqual(self.one(last_seen_at=T - D(900), litigation_hold=1), [])

    def test_staff_email(self):
        old = T - D(900)
        self.assertEqual(self.one(last_seen_at=old, email="  A@Tidewater-Klatring.NO "), [])
        self.assertEqual(self.one(last_seen_at=old, email=None)[0]["action"], "delete")

    def test_keys_and_email(self):
        r = self.one(last_seen_at=T - D(900))[0]
        self.assertEqual(set(r), {"account_id", "action", "due", "approved_by", "email"})
        self.assertEqual(r["email"], "m@example.com")

    def test_cap_closed_first(self):
        accs = [acc(id=i, last_seen_at=T - D(1000 + i)) for i in range(1, 201)]
        accs += [acc(id=1000 + i, closed_at=T - D(31), closed_by="member") for i in range(5)]
        accs += [acc(id=5000, litigation_hold=True, last_seen_at=T - D(2000))]
        r = plan_purge(accs, T)
        ids = {x["account_id"] for x in r}
        self.assertEqual(len(r), 200)
        self.assertTrue({1000 + i for i in range(5)} <= ids)
        self.assertNotIn(5000, ids)
        self.assertNotIn(1, ids)  # youngest-due inactive dropped (id 1 has latest due)

    def test_sorting(self):
        r = plan_purge([acc(id=10, last_seen_at=T - D(800)), acc(id=9, last_seen_at=T - D(800))], T)
        self.assertEqual([x["account_id"] for x in r], [9, 10])

    def test_json_tenant_nomutation(self):
        a = acc(last_seen_at=T - D(800), tenant="x")
        b = dict(a)
        r = plan_purge([a], T)
        self.assertEqual(a, b)
        json.dumps(r)
        a.pop("tenant")
        self.assertEqual(plan_purge([a], T), r)

    def test_datetime_rejected_and_none_seen(self):
        with self.assertRaises(TypeError):
            self.one(last_seen_at=dt.datetime(2020, 1, 1))
        with self.assertRaises(TypeError):
            plan_purge([], dt.datetime(2026, 1, 1))
        self.assertEqual(self.one(last_seen_at=None), [])

    def test_last_login_ignored(self):
        self.assertEqual(self.one(last_seen_at=T - D(800), last_login=T)[0]["action"], "delete")


if __name__ == "__main__":
    unittest.main()