"""Tidewater Climbing GDPR member-account clean-up planner.

Note: the spec requires exactly four keys per action and forbids the member's
email in any output, so the email house rule is deliberately not applied here.
"""
import json
import unittest
from datetime import date, timedelta

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200
CAPPED_ACTIONS = {"delete"}  # one-line change to also cap e.g. "anonymise"
STAFF_SUFFIX = "@tidewater-klatring.no"
DPO_NAME = "Tordis Svenbjorn Dottir"


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def _due_date(acc):
    candidates = []
    last_seen = acc.get("last_seen_at")
    if last_seen is not None:
        candidates.append(last_seen + timedelta(days=INACTIVITY_DAYS))
    closed_at = acc.get("closed_at")
    if closed_at is not None:
        candidates.append(closed_at + timedelta(days=CLOSED_GRACE_DAYS))
    return min(candidates) if candidates else None


def plan_purge(accounts, today):
    candidates = []  # (account_id, action, due, is_closed)
    seen = set()
    for acc in accounts:
        acc_id = acc.get("id")
        if acc_id in seen:
            continue
        if _is_staff(acc.get("email")) or acc.get("litigation_hold"):
            continue
        due = _due_date(acc)
        if due is None:
            continue
        is_closed = acc.get("closed_at") is not None
        if due <= today:
            action = "anonymise" if acc.get("unpaid_invoices") else "delete"
        elif due <= today + timedelta(days=WARN_WINDOW_DAYS):
            if acc.get("closed_by") == "member":
                continue
            action = "warn"
        else:
            continue
        seen.add(acc_id)
        candidates.append((acc_id, action, due, is_closed))

    capped = [c for c in candidates if c[1] in CAPPED_ACTIONS]
    others = [c for c in candidates if c[1] not in CAPPED_ACTIONS]
    if len(capped) > DELETE_CAP:
        capped.sort(key=lambda c: (0 if c[3] else 1, c[2], c[0]))
        capped = capped[:DELETE_CAP]

    selected = sorted(capped + others, key=lambda c: c[0])
    return [
        {
            "account_id": acc_id,
            "action": action,
            "due": due.isoformat(),
            "approved_by": None if action == "warn" else DPO_NAME,
        }
        for acc_id, action, due, _ in selected
    ]


TODAY = date(2026, 10, 13)


def acct(i=1, **kw):
    base = {
        "id": i, "email": "m%s@example.com" % i, "status": "active",
        "last_seen_at": TODAY, "last_login": TODAY, "closed_at": None,
        "closed_by": "staff", "unpaid_invoices": 0, "litigation_hold": False,
    }
    base.update(kw)
    return base


def d(n):
    return TODAY + timedelta(days=n)


def one(**kw):
    return plan_purge([acct(**kw)], TODAY)


class PlanPurgeTests(unittest.TestCase):
    def test_inactivity_boundaries(self):
        r = one(last_seen_at=d(-730))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", TODAY.isoformat()))
        r = one(last_seen_at=d(-729))
        self.assertEqual(r[0]["action"], "warn")
        self.assertEqual(r[0]["due"], d(1).isoformat())
        self.assertEqual(one(last_seen_at=d(-716))[0]["action"], "warn")
        self.assertEqual(one(last_seen_at=d(-715)), [])

    def test_last_login_ignored(self):
        r = one(last_seen_at=d(-800), last_login=TODAY)
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(one(last_seen_at=None, last_login=d(-900)), [])

    def test_closed_rules(self):
        self.assertEqual(one(closed_at=d(-30))[0]["action"], "delete")
        self.assertEqual(one(closed_at=d(-29), closed_by="member"), [])
        self.assertEqual(one(closed_at=d(-29), closed_by="staff")[0]["action"], "warn")
        r = one(last_seen_at=d(-800), closed_at=d(-5))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", d(-70).isoformat()))

    def test_closed_none_last_seen(self):
        self.assertEqual(one(last_seen_at=None, closed_at=d(-30))[0]["action"], "delete")
        self.assertEqual(one(last_seen_at=None), [])

    def test_member_closed_inactivity_warn(self):
        self.assertEqual(one(last_seen_at=d(-720), closed_at=d(-1), closed_by="member"), [])
        r = one(last_seen_at=d(-720), closed_at=d(-1), closed_by="staff")
        self.assertEqual((r[0]["action"], r[0]["due"]), ("warn", d(10).isoformat()))
        r = one(last_seen_at=d(-720), closed_at=d(-1))
        self.assertEqual(r[0]["action"], "warn")

    def test_unpaid(self):
        r = one(last_seen_at=d(-800), unpaid_invoices=3)
        self.assertEqual((r[0]["action"], r[0]["approved_by"]), ("anonymise", DPO_NAME))
        self.assertEqual(one(last_seen_at=d(-720), unpaid_invoices=3)[0]["action"], "warn")

    def test_litigation_hold(self):
        for kw in ({"last_seen_at": d(-800)}, {"last_seen_at": d(-720)},
                   {"closed_at": d(-40)}, {"last_seen_at": d(-800), "unpaid_invoices": 1}):
            self.assertEqual(one(litigation_hold=True, **kw), [])
        accts = [acct(i, last_seen_at=d(-800), litigation_hold=True) for i in range(300)]
        accts += [acct(1000 + i, last_seen_at=d(-800)) for i in range(200)]
        self.assertEqual(len(plan_purge(accts, TODAY)), 200)

    def test_staff_email(self):
        old = d(-800)
        self.assertEqual(one(email="Anna@Tidewater-Klatring.NO", last_seen_at=old), [])
        self.assertEqual(one(email="  a@tidewater-klatring.no  ", last_seen_at=old), [])
        self.assertEqual(len(one(email="x@mail.tidewater-klatring.no", last_seen_at=old)), 1)
        self.assertEqual(len(one(email=None, last_seen_at=old)), 1)

    def test_shape_and_privacy(self):
        accts = [acct(1, last_seen_at=d(-800)), acct(2, last_seen_at=d(-720)),
                 acct(3, last_seen_at=d(-800), unpaid_invoices=1)]
        res = plan_purge(accts, TODAY)
        for r in res:
            self.assertEqual(set(r), {"account_id", "action", "due", "approved_by"})
            self.assertEqual(r["approved_by"], None if r["action"] == "warn" else DPO_NAME)
        s = json.dumps(res)
        self.assertNotIn("example.com", s)
        self.assertNotIn("@", s)

    def test_cap_mixed(self):
        accts = [acct(i, last_seen_at=TODAY, closed_at=d(-30)) for i in range(100)]
        accts += [acct(1000 + i, last_seen_at=d(-731 - i)) for i in range(150)]
        res = plan_purge(accts, TODAY)
        self.assertEqual(len(res), 200)
        ids = {r["account_id"] for r in res}
        self.assertTrue(set(range(100)) <= ids)
        self.assertEqual(ids - set(range(100)), {1000 + i for i in range(50, 150)})

    def test_cap_closed_only(self):
        accts = [acct(i, closed_at=d(-30 - i)) for i in range(230)]
        self.assertEqual(len(plan_purge(accts, TODAY)), 200)

    def test_cap_not_for_anonymise_or_warn(self):
        accts = [acct(i, last_seen_at=d(-800)) for i in range(200)]
        accts += [acct(500 + i, last_seen_at=d(-800), unpaid_invoices=1) for i in range(50)]
        accts += [acct(900 + i, last_seen_at=d(-720)) for i in range(30)]
        res = plan_purge(accts, TODAY)
        self.assertEqual(len(res), 280)
        self.assertEqual(sum(r["action"] == "anonymise" for r in res), 50)
        accts = accts[:200] + accts[250:] + [acct(2000 + i, last_seen_at=d(-800)) for i in range(20)]
        res = plan_purge(accts, TODAY)
        self.assertEqual(sum(r["action"] == "delete" for r in res), 200)

    def test_sorted_pure_deterministic(self):
        accts = [acct(i, last_seen_at=d(-800 + i % 3)) for i in (5, 3, 9, 1, 7)]
        accts.append(acct(4, last_seen_at=d(-720)))
        accts.append({"id": 0})
        snapshot = [dict(a) for a in accts]
        r1 = plan_purge(accts, TODAY)
        self.assertEqual(accts, snapshot)
        self.assertEqual(r1, plan_purge(accts, TODAY))
        ids = [r["account_id"] for r in r1]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))

    def test_empty_and_missing_keys(self):
        self.assertEqual(plan_purge([], TODAY), [])
        self.assertEqual(plan_purge([{"id": 1}, {}], TODAY), [])


if __name__ == "__main__":
    unittest.main()