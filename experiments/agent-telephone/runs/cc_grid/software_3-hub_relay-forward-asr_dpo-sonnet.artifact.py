"""Purge planner for Tidewater Climbing member accounts.

Defaults chosen where the PM marked Q:
- Over-cap ranking: closed first, then earliest due, then account_id.
- Unpaid invoices accept int, bool or list (truthy / > 0).
- Accounts with no usable date are skipped.

Note: actions deliberately do NOT carry the member's email. The client brief
and PM decisions say the audit log is shared with the climbing federation and
the email must never appear, with exactly the keys account_id, action, due,
approved_by. This conflicts with the house rule asking for an `email` key;
the privacy requirement was followed. Please confirm with the client.
"""
import unittest
from datetime import date, datetime, timedelta

APPROVER = "Tordis Svenbjorn Dottir"
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVE_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
MAX_DELETES = 200


def _d(v):
    if isinstance(v, datetime):
        return v.date()
    return v if isinstance(v, date) else None


def _is_staff(acc):
    email = acc.get("email")
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def _unpaid(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v > 0
    return bool(v)


def plan_purge(accounts, today):
    today = _d(today)
    warn_limit = today + timedelta(days=WARN_DAYS)
    deletes, others = [], []
    for acc in accounts:
        if acc.get("litigation_hold") or _is_staff(acc):
            continue
        seen = _d(acc.get("last_seen_at"))
        closed = _d(acc.get("closed_at"))
        cands = []
        if seen is not None:
            cands.append(seen + timedelta(days=INACTIVE_DAYS))
        if closed is not None:
            cands.append(closed + timedelta(days=CLOSED_DAYS))
        if not cands:
            continue
        due = min(cands)
        aid = acc.get("id")
        if due <= today:
            if _unpaid(acc.get("unpaid_invoices")):
                others.append({"account_id": aid, "action": "anonymise",
                               "due": due.isoformat(), "approved_by": APPROVER})
            else:
                deletes.append(((closed is None, due, aid),
                                {"account_id": aid, "action": "delete",
                                 "due": due.isoformat(), "approved_by": APPROVER}))
        elif due <= warn_limit:
            if acc.get("closed_by") == "member" and closed is not None:
                continue
            others.append({"account_id": aid, "action": "warn",
                           "due": due.isoformat(), "approved_by": None})
    deletes.sort(key=lambda t: t[0])
    others.extend(a for _, a in deletes[:MAX_DELETES])
    others.sort(key=lambda a: a["account_id"])
    return others


class PlanPurgeTests(unittest.TestCase):
    T = date(2026, 10, 13)

    def acc(self, i="a", ago=0, **kw):
        base = {"id": i, "email": "m@example.com", "status": "x",
                "last_seen_at": self.T - timedelta(days=ago), "last_login": None,
                "closed_at": None, "closed_by": None, "unpaid_invoices": 0,
                "litigation_hold": False}
        base.update(kw)
        return base

    def act(self, a):
        r = plan_purge([a], self.T)
        return r[0] if r else None

    def test_empty(self):
        self.assertEqual(plan_purge([], self.T), [])

    def test_delete_and_keys(self):
        r = self.act(self.acc(ago=730))
        self.assertEqual(r["action"], "delete")
        self.assertEqual(r["due"], self.T.isoformat())
        self.assertEqual(set(r), {"account_id", "action", "due", "approved_by"})
        self.assertEqual(r["approved_by"], APPROVER)

    def test_warn_window(self):
        for ago in (729, 716):
            r = self.act(self.acc(ago=ago))
            self.assertEqual(r["action"], "warn")
            self.assertIsNone(r["approved_by"])
        self.assertIsNone(self.act(self.acc(ago=715)))

    def test_overdue_not_warned(self):
        self.assertEqual(self.act(self.acc(ago=800))["action"], "delete")

    def test_closed(self):
        r = self.act(self.acc(ago=1, closed_at=self.T - timedelta(days=30)))
        self.assertEqual(r["action"], "delete")

    def test_member_vs_staff_closed(self):
        c = self.T - timedelta(days=25)
        self.assertIsNone(self.act(self.acc(ago=1, closed_at=c, closed_by="member")))
        self.assertEqual(self.act(self.acc(ago=1, closed_at=c, closed_by="staff"))["action"], "warn")

    def test_anonymise_and_warn_unpaid(self):
        self.assertEqual(self.act(self.acc(ago=730, unpaid_invoices=[1]))["action"], "anonymise")
        self.assertEqual(self.act(self.acc(ago=725, unpaid_invoices=2))["action"], "warn")

    def test_exclusions(self):
        self.assertIsNone(self.act(self.acc(ago=900, litigation_hold=True)))
        self.assertIsNone(self.act(self.acc(ago=900, email=" X@Tidewater-Klatring.no ")))

    def test_no_dates(self):
        self.assertIsNone(self.act(self.acc(last_seen_at=None)))

    def test_cap(self):
        accs = [self.acc(i=f"o{n:03d}", ago=800) for n in range(150)]
        accs += [self.acc(i=f"z{n:03d}", ago=1, closed_at=self.T - timedelta(days=31))
                 for n in range(100)]
        r = plan_purge(accs, self.T)
        self.assertEqual(len(r), 200)
        self.assertTrue(all(a["account_id"].startswith("z") for a in r) is False)
        self.assertEqual(sum(a["account_id"].startswith("z") for a in r), 100)
        self.assertEqual([a["account_id"] for a in r], sorted(a["account_id"] for a in r))

    def test_no_mutation(self):
        a = self.acc(ago=730)
        import copy
        b = copy.deepcopy(a)
        plan_purge([a], self.T)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()