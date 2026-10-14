"""Retention purge planner (single module, stdlib only).

Run tests:  python3 -m unittest /absolute/path/to/purge.py
            (or: python3 purge.py)

plan_purge(accounts, today) is pure and stateless: an account inside its
warning window is warned on EVERY run until it becomes due (R26).

DEVIATION (R1/R9 vs house rule): the task says actions contain exactly four
keys and never the email. The standing house rule says every action dict also
carries the account's `email` for support follow-up. The house rule was
followed, so each action has a fifth key `email`. To restore the four-key
contract, delete the "email" entry in _action() and adjust the R9 test.
Not executed here (no tools available), so the tests have not been run.
"""
import datetime as _dt
import json
import unittest

INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
DELETE_CAP = 200
STAFF_DOMAIN = "@tidewater-klatring.no"
APPROVER = "Þórdís Sveinbjörnsdóttir"
REQUIRED = ("id", "email", "status", "last_seen_at", "last_login", "closed_at",
            "closed_by", "unpaid_invoices", "litigation_hold")


def _counts_toward_cap(action):
    """Single counting predicate. Add `or action == "anonymise"` to count both."""
    return action == "delete"


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def _check(acc):
    aid = acc.get("id", "<unknown>") if isinstance(acc, dict) else "<unknown>"
    if not isinstance(acc, dict):
        raise ValueError("account %s: not a dict" % aid)
    for k in REQUIRED:
        if k not in acc:
            raise ValueError("account %s: missing required key %r" % (aid, k))
    for k in ("last_seen_at", "closed_at"):
        v = acc[k]
        if v is not None and (not isinstance(v, _dt.date) or isinstance(v, _dt.datetime)):
            raise ValueError("account %s: %s must be a date or None" % (aid, k))


def _action(acc, action, due, approved):
    return {"account_id": acc["id"], "action": action, "due": due.isoformat(),
            "approved_by": approved, "email": acc["email"]}


def plan_purge(accounts, today):
    """Return the list of purge actions for `accounts` as of `today`."""
    candidates = []  # (group, due, id, action dict) for delete/anonymise
    out = []         # warnings
    for acc in accounts:
        _check(acc)
        if acc["litigation_hold"] or _is_staff(acc["email"]):
            continue
        dues = []
        try:
            if acc["last_seen_at"] is not None:  # last_login deliberately unused
                dues.append(acc["last_seen_at"] + _dt.timedelta(days=INACTIVITY_DAYS))
            closed_at = acc["closed_at"]
            closed_due = None
            if closed_at is not None and closed_at <= today:  # future closed_at ignored
                closed_due = closed_at + _dt.timedelta(days=CLOSED_DAYS)
                dues.append(closed_due)
        except OverflowError:
            raise ValueError("account %s: date out of range" % acc["id"])
        if not dues:
            continue
        due = min(dues)
        if due <= today:
            # Unpaid invoices: Norwegian bookkeeping rules (Skatteetaten) require
            # invoice records to be kept for five years, so we anonymise the
            # personal data instead of deleting the record.
            kind = "anonymise" if acc["unpaid_invoices"] else "delete"
            group = 0 if (closed_due is not None and closed_due <= today) else 1
            candidates.append((group, due, acc["id"], _action(acc, kind, due, APPROVER)))
        elif due <= today + _dt.timedelta(days=WARN_DAYS):
            if acc["closed_at"] is not None and acc["closed_by"] == "member":
                continue
            out.append(_action(acc, "warn", due, None))

    candidates.sort(key=lambda c: (c[0], c[1], c[2]))
    taken = 0
    for _, _, _, act in candidates:
        if _counts_toward_cap(act["action"]):
            if taken >= DELETE_CAP:
                continue
            taken += 1
        out.append(act)
    out.sort(key=lambda a: a["account_id"])
    return out


# ----------------------------- tests -----------------------------
T = _dt.date(2026, 10, 13)


def D(n):
    return T + _dt.timedelta(days=n)


def acc(i=1, **kw):
    a = {"id": i, "email": "m%s@example.com" % i, "status": "active",
         "last_seen_at": D(-10), "last_login": None, "closed_at": None,
         "closed_by": "member", "unpaid_invoices": 0, "litigation_hold": False}
    a.update(kw)
    return a


def one(**kw):
    return plan_purge([acc(**kw)], T)


class PurgeTests(unittest.TestCase):
    def test_keys_and_json(self):
        r = one(last_seen_at=D(-730))[0]
        self.assertEqual(set(r), {"account_id", "action", "due", "approved_by", "email"})
        self.assertEqual(r["due"], D(0).isoformat())
        json.dumps(r)

    def test_inactivity_boundary(self):
        self.assertEqual(one(last_seen_at=D(-730))[0]["action"], "delete")
        self.assertEqual(one(last_seen_at=D(-729))[0]["action"], "warn")

    def test_closed_boundary(self):
        self.assertEqual(one(closed_at=D(-30))[0]["action"], "delete")
        self.assertEqual(one(closed_at=D(-29), closed_by="staff")[0]["action"], "warn")

    def test_last_login_ignored(self):
        self.assertEqual(one(last_login=D(-900)), [])
        self.assertEqual(one(last_seen_at=D(-800), last_login=D(0))[0]["action"], "delete")

    def test_both_rules_earlier_due(self):
        r = one(last_seen_at=D(-800), closed_at=D(-10))[0]
        self.assertEqual(r["due"], D(-70).isoformat())

    def test_future_closed_at(self):
        self.assertEqual(one(closed_at=D(5)), [])

    def test_last_seen_none(self):
        self.assertEqual(one(last_seen_at=None, last_login=D(-900)), [])
        self.assertEqual(one(last_seen_at=None, closed_at=D(-30))[0]["action"], "delete")

    def test_warn_window(self):
        self.assertEqual(one(last_seen_at=D(-716))[0]["due"], D(14).isoformat())
        self.assertEqual(one(last_seen_at=D(-715)), [])
        r = one(last_seen_at=D(-716))[0]
        self.assertEqual(r["action"], "warn")
        self.assertIsNone(r["approved_by"])

    def test_member_closed_no_warn(self):
        self.assertEqual(one(closed_at=D(-20), closed_by="member"), [])
        self.assertEqual(one(closed_at=D(-20), closed_by="staff")[0]["action"], "warn")

    def test_unpaid(self):
        for v in (3, [1], True):
            self.assertEqual(one(last_seen_at=D(-800), unpaid_invoices=v)[0]["action"], "anonymise")
        self.assertEqual(one(last_seen_at=D(-800), unpaid_invoices=[])[0]["action"], "delete")
        self.assertEqual(one(last_seen_at=D(-716), unpaid_invoices=2)[0]["action"], "warn")

    def test_hold(self):
        for ls in (-800, -716):
            self.assertEqual(one(last_seen_at=D(ls), litigation_hold=True), [])

    def test_staff(self):
        s = "@tidewater-klatring.no"
        self.assertEqual(one(email="  X" + s.upper() + " ", last_seen_at=D(-800)), [])
        for e in ("x@evil-tidewater-klatring.no", "x@sub.tidewater-klatring.no", None):
            self.assertEqual(len(one(email=e, last_seen_at=D(-800))), 1)

    def test_approver(self):
        self.assertEqual(APPROVER, "Þórdís Sveinbjörnsdóttir")
        self.assertEqual(one(last_seen_at=D(-800))[0]["approved_by"], APPROVER)
        self.assertEqual(one(last_seen_at=D(-800), unpaid_invoices=1)[0]["approved_by"], APPROVER)

    def test_cap_and_order(self):
        accs = [acc(i, last_seen_at=D(-731 - i)) for i in range(1, 201)]   # group B
        accs += [acc(1000 + i, last_seen_at=None, closed_at=D(-30 - i)) for i in range(5)]  # A
        accs += [acc(2000, last_seen_at=D(-5000), unpaid_invoices=1)]
        r = plan_purge(accs, T)
        ids = [a["account_id"] for a in r]
        self.assertEqual(ids, sorted(ids))
        dels = [a for a in r if a["action"] == "delete"]
        self.assertEqual(len(dels), DELETE_CAP)
        self.assertTrue(all((1000 + i) in ids for i in range(5)))
        self.assertIn(2000, ids)              # anonymise not capped
        self.assertNotIn(1, ids)              # oldest-due? id1 due -1d, latest -> deferred
        self.assertIn(200, ids)

    def test_cap_warnings_uncapped(self):
        accs = [acc(i, last_seen_at=D(-800)) for i in range(250)]
        accs += [acc(1000 + i, last_seen_at=D(-720)) for i in range(10)]
        r = plan_purge(accs, T)
        self.assertEqual(sum(a["action"] == "warn" for a in r), 10)
        self.assertEqual(sum(a["action"] == "delete" for a in r), DELETE_CAP)

    def test_no_mutation_and_tenant(self):
        a = acc(last_seen_at=D(-800))
        before = dict(a)
        r1 = plan_purge([a], T)
        a["tenant"] = "x"
        self.assertEqual(a, dict(before, tenant="x"))
        self.assertEqual(r1, plan_purge([a], T))

    def test_errors_no_email(self):
        bad = acc(7, email="secret@example.com")
        del bad["closed_by"]
        with self.assertRaises(ValueError) as c:
            plan_purge([bad], T)
        self.assertIn("7", str(c.exception))
        self.assertNotIn("secret", str(c.exception))
        with self.assertRaises(ValueError) as c:
            plan_purge([acc(8, email="secret@example.com", last_seen_at="2020-01-01")], T)
        self.assertIn("8", str(c.exception))
        self.assertNotIn("secret", str(c.exception))

    def test_stateless_warning(self):
        a = acc(last_seen_at=D(-720))
        self.assertEqual(plan_purge([a], T), plan_purge([a], T))


if __name__ == "__main__":
    unittest.main()