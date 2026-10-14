"""Purge planner for member accounts (GDPR clean-up).

Notes and assumptions:
- Actions contain exactly account_id, action, due, approved_by. The account email
  is deliberately NOT included: the brief says the audit log is shared with the
  climbing federation and must not contain member emails. This overrides the house
  rule of adding `email` to each action. Support can look the email up by account_id.
- Anonymise actions are uncapped; only deletes are capped at 200.
- closed_by None (or anything other than "member") still gets a warn.
- Already-anonymised accounts are re-emitted on every run, since status is ignored.
- Inputs are never mutated.
- The tests below were written without the ability to execute them here, so run
  `python -I purge.py` to verify.
"""
from datetime import date, timedelta
import json
import unittest

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
MAX_DELETES = 200
WARN_DAYS = 40


def _is_staff(email):
    return email is not None and email.strip().lower().endswith(STAFF_SUFFIX)


def _due(acc):
    cands = []
    if acc.get("last_seen_at") is not None:
        cands.append(acc["last_seen_at"] + timedelta(days=730))
    if acc.get("closed_at") is not None:
        cands.append(acc["closed_at"] + timedelta(days=30))
    return min(cands) if cands else None


def plan_purge(accounts, today):
    horizon = today + timedelta(days=WARN_DAYS)
    deletes, others = [], []
    for acc in accounts:
        if acc.get("litigation_hold") or _is_staff(acc.get("email")):
            continue
        due = _due(acc)
        if due is None:
            continue
        aid = acc["id"]
        closed = acc.get("closed_at") is not None
        if due <= today:
            if acc.get("unpaid_invoices"):
                others.append((aid, "anonymise", due))
            else:
                deletes.append((not closed, due, aid))
        elif due <= horizon:
            if closed and acc.get("closed_by") == "member":
                continue
            others.append((aid, "warn", due))

    deletes.sort()
    result = [(aid, "delete", due) for _, due, aid in deletes[:MAX_DELETES]]
    result += others
    result.sort(key=lambda t: t[0])
    return [
        {
            "account_id": aid,
            "action": action,
            "due": due.isoformat(),
            "approved_by": None if action == "warn" else APPROVER,
        }
        for aid, action, due in result
    ]


class PurgeTests(unittest.TestCase):
    T = date(2026, 10, 13)

    def acc(self, id, **kw):
        base = dict(id=id, email="a@example.com", status="active",
                    last_seen_at=self.T, last_login=None, closed_at=None,
                    closed_by=None, unpaid_invoices=False, litigation_hold=False)
        base.update(kw)
        return base

    def test_boundary_delete(self):
        r = plan_purge([self.acc(1, last_seen_at=self.T - timedelta(days=730))], self.T)
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(r[0]["approved_by"], APPROVER)
        self.assertEqual(set(r[0]), {"account_id", "action", "due", "approved_by"})
        json.dumps(r)

    def test_warn_window(self):
        r40 = plan_purge([self.acc(1, last_seen_at=self.T - timedelta(days=690))], self.T)
        r41 = plan_purge([self.acc(1, last_seen_at=self.T - timedelta(days=689))], self.T)
        self.assertEqual(r40[0]["action"], "warn")
        self.assertIsNone(r40[0]["approved_by"])
        self.assertEqual(r41, [])

    def test_member_closed_no_warn(self):
        c = self.T - timedelta(days=20)
        self.assertEqual(plan_purge([self.acc(1, closed_at=c, closed_by="member")], self.T), [])
        r = plan_purge([self.acc(1, closed_at=c, closed_by="staff")], self.T)
        self.assertEqual(r[0]["action"], "warn")

    def test_exclusions_and_anonymise(self):
        old = self.T - timedelta(days=800)
        accs = [self.acc(1, last_seen_at=old, litigation_hold=True),
                self.acc(2, last_seen_at=old, email=" X@Tidewater-Klatring.no "),
                self.acc(3, last_seen_at=old, email=None, unpaid_invoices=True)]
        r = plan_purge(accs, self.T)
        self.assertEqual([(x["account_id"], x["action"]) for x in r], [(3, "anonymise")])

    def test_cap(self):
        old = self.T - timedelta(days=800)
        accs = [self.acc(i, last_seen_at=old) for i in range(1000, 1200)]
        accs += [self.acc(i, last_seen_at=old) for i in range(1200, 1250)]
        accs += [self.acc(i, last_seen_at=self.T, closed_at=self.T - timedelta(days=30))
                 for i in range(1, 51)]
        accs = accs[200:] + accs[:200]
        before = [dict(a) for a in accs]
        r = plan_purge(accs, self.T)
        self.assertEqual(accs, before)
        self.assertEqual(len(r), 200)
        self.assertTrue(set(range(1, 51)) <= {x["account_id"] for x in r})
        self.assertEqual([x["account_id"] for x in r], sorted(x["account_id"] for x in r))


if __name__ == "__main__":
    unittest.main()