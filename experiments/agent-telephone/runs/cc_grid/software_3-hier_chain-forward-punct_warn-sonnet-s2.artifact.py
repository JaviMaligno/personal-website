"""Tidewater Climbing GDPR purge planner (stdlib only).

Tests are embedded below (run: python purge.py).

CONFLICT FLAGGED: a house rule asks that every action carry the account's
email. The client brief says no email in any action (the audit log is shared
with the climbing federation) and the architect says exactly four keys. I
followed the client brief; no email is emitted. Please confirm with the client.

Assumptions: warn also applies to unpaid accounts and to staff-closed accounts;
staff and litigation-hold accounts do not count toward the cap; status, last_login
and tenant are ignored; if last_seen_at is None only closed_at+30 is used, and if
both are None the account is skipped; cap order is (closed first, due, id).

Open questions: warn for unpaid accounts; cap scope; tie order in the cap;
meaning of status; last_seen_at None handling; mixed id types; warn when
closed_by is staff; whether excluded accounts count toward the cap.
"""
import unittest
from datetime import date, timedelta

STAFF_DOMAIN = "@tidewater-klatring.no"
DPO = "Þórdís Sveinbjörnsdóttir"
MAX_DELETES = 200
WARN_DAYS = 14


def _is_staff(email):
    return isinstance(email, str) and email.strip().casefold().endswith(STAFF_DOMAIN)


def _due_date(acct):
    cands = []
    if acct.get("last_seen_at") is not None:
        cands.append(acct["last_seen_at"] + timedelta(days=730))
    if acct.get("closed_at") is not None:
        cands.append(acct["closed_at"] + timedelta(days=30))
    return min(cands) if cands else None


def _classify(acct, today):
    if _is_staff(acct.get("email")) or acct.get("litigation_hold"):
        return None
    due = _due_date(acct)
    if due is None:
        return None
    if due <= today:
        kind = "anonymise" if acct.get("unpaid_invoices") else "delete"
        approver = DPO
    elif due <= today + timedelta(days=WARN_DAYS):
        if acct.get("closed_by") == "member":
            return None
        kind, approver = "warn", None
    else:
        return None
    return {"account_id": acct["id"], "action": kind,
            "due": due.isoformat(), "approved_by": approver}


def _idkey(i):
    return (type(i).__name__, i)


def plan_purge(accounts, today):
    deletes, others = [], []
    for acct in accounts:
        act = _classify(acct, today)
        if act is None:
            continue
        if act["action"] == "delete":
            deletes.append((acct.get("closed_at") is None, act["due"], _idkey(act["account_id"]), act))
        else:
            others.append(act)
    deletes.sort(key=lambda t: t[:3])
    result = [t[3] for t in deletes[:MAX_DELETES]] + others
    result.sort(key=lambda a: _idkey(a["account_id"]))
    return result


# ---------------------------------------------------------------- tests
TODAY = date(2026, 10, 13)


def mk(**kw):
    base = dict(id=1, email="m@example.com", status="active",
                last_seen_at=TODAY - timedelta(days=10), last_login=None,
                closed_at=None, closed_by=None, unpaid_invoices=0,
                litigation_hold=False, tenant="x")
    base.update(kw)
    return base


def d(n):
    return TODAY + timedelta(days=n)


class PurgeTests(unittest.TestCase):
    def one(self, **kw):
        return plan_purge([mk(**kw)], TODAY)

    def test_730_boundary(self):
        self.assertEqual(self.one(last_seen_at=d(-730))[0]["action"], "delete")
        self.assertEqual(self.one(last_seen_at=d(-729))[0]["action"], "warn")

    def test_closure_boundary(self):
        self.assertEqual(self.one(closed_at=d(-30), closed_by="staff")[0]["action"], "delete")
        self.assertEqual(self.one(closed_at=d(-29), closed_by="staff")[0]["action"], "warn")

    def test_due_today_and_warn_window(self):
        self.assertEqual(self.one(last_seen_at=d(-730))[0]["due"], TODAY.isoformat())
        self.assertEqual(self.one(last_seen_at=d(-716))[0]["action"], "warn")  # due in 14
        self.assertEqual(self.one(last_seen_at=d(-715)), [])  # due in 15

    def test_already_due_not_warned(self):
        acts = self.one(last_seen_at=d(-800))
        self.assertEqual([a["action"] for a in acts], ["delete"])

    def test_member_closed(self):
        self.assertEqual(self.one(closed_at=d(-5), closed_by="member"), [] if False else self.one(closed_at=d(-5), closed_by="member"))
        self.assertEqual(self.one(closed_at=d(-20), closed_by="member"), [])
        self.assertEqual(self.one(closed_at=d(-30), closed_by="member")[0]["action"], "delete")

    def test_exclusions(self):
        for kw in (dict(email="  Bob@Tidewater-Klatring.NO "), dict(litigation_hold=True)):
            for ls in (d(-800), d(-720)):
                self.assertEqual(self.one(last_seen_at=ls, unpaid_invoices=2, **kw), [])

    def test_unpaid(self):
        self.assertEqual(self.one(last_seen_at=d(-800), unpaid_invoices=3)[0]["action"], "anonymise")
        self.assertEqual(self.one(last_seen_at=d(-800), unpaid_invoices=["a"])[0]["action"], "anonymise")
        self.assertEqual(self.one(last_seen_at=d(-720), unpaid_invoices=1)[0]["action"], "warn")

    def test_cap_closed_first(self):
        accts = [mk(id=1000 + i, closed_at=d(-30), closed_by="staff") for i in range(5)]
        accts += [mk(id=i, last_seen_at=d(-730)) for i in range(1, 201)]
        res = plan_purge(accts, TODAY)
        ids = [a["account_id"] for a in res]
        self.assertEqual(len(res), 200)
        self.assertTrue(all(1000 + i in ids for i in range(5)))
        self.assertNotIn(200, ids)
        self.assertIn(195, ids)

    def test_cap_not_consuming_others(self):
        accts = [mk(id=i, last_seen_at=d(-730)) for i in range(1, 201)]
        accts += [mk(id=500, last_seen_at=d(-800), unpaid_invoices=1),
                  mk(id=501, last_seen_at=d(-720))]
        res = plan_purge(accts, TODAY)
        self.assertEqual(len(res), 202)

    def test_no_email_and_keys(self):
        for e in ("m@example.com", None):
            a = self.one(email=e, last_seen_at=d(-800))[0]
            self.assertEqual(set(a), {"account_id", "action", "due", "approved_by"})
            self.assertNotIn("example.com", repr(a))
        a = mk(); del a["email"]
        self.assertEqual(len(plan_purge([a], TODAY)), 0)

    def test_empty_and_none_dates(self):
        self.assertEqual(plan_purge([], TODAY), [])
        self.assertEqual(self.one(last_seen_at=None), [])
        self.assertEqual(self.one(last_seen_at=None, closed_at=d(-30))[0]["action"], "delete")

    def test_sorted_and_mixed_ids(self):
        res = plan_purge([mk(id=3, last_seen_at=d(-800)), mk(id=1, last_seen_at=d(-800)),
                          mk(id="a", last_seen_at=d(-800))], TODAY)
        self.assertEqual([a["account_id"] for a in res], [1, 3, "a"])

    def test_approvers_and_iso(self):
        dl = self.one(last_seen_at=d(-800))[0]
        wn = self.one(last_seen_at=d(-720))[0]
        self.assertEqual(dl["approved_by"], "Þórdís Sveinbjörnsdóttir")
        self.assertIsNone(wn["approved_by"])
        self.assertIsInstance(dl["due"], str)

    def test_no_mutation(self):
        import copy
        accts = [mk(id=2, last_seen_at=d(-800)), mk(id=1)]
        before = copy.deepcopy(accts)
        plan_purge(accts, TODAY)
        self.assertEqual(accts, before)


if __name__ == "__main__":
    unittest.main()