"""GDPR purge planner for Tidewater Climbing member accounts.

plan_purge(accounts, today) returns today's actions as dicts with exactly the
keys account_id, action, due (ISO string) and approved_by.

Notes:
- The client brief forbids the member's email in any action (the audit log is
  shared with the climbing federation), so no email key is emitted. This
  overrides the house rule asking for an email on every action; support can
  look the email up by account_id.
- datetime values are reduced to their date part (datetime is a date subclass).
- Rows that are malformed (non-dict, unhashable or missing id, invalid date
  types, non-string email, date overflow) are skipped, never abort the run.
  Held and staff rows are skipped before any other validation.
- Stateless: warnings repeat on every run during the 14-day window.
- Only deletes are capped at 200; anonymisations are not.
"""
import unicodedata
import unittest
from datetime import date, datetime, timedelta

APPROVER = unicodedata.normalize("NFC", "Þórdís Sveinbjörnsdóttir")
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVITY = timedelta(days=730)
CLOSED_GRACE = timedelta(days=30)
WARN_WINDOW = timedelta(days=14)
DELETE_CAP = 200


def _as_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    raise TypeError("not a date")


def _idkey(i):
    return (type(i).__name__, i)


def plan_purge(accounts, today):
    today = _as_date(today)
    seen = set()
    cands = []  # (account_id, action, due, closed)
    for acc in accounts:
        try:
            if not isinstance(acc, dict):
                continue
            if acc.get("litigation_hold"):
                continue
            email = acc.get("email")
            if email is not None:
                if not isinstance(email, str):
                    continue
                if email.strip().lower().endswith(STAFF_SUFFIX):
                    continue
            aid = acc["id"]
            if aid is None or aid in seen:
                continue
            last_seen = acc.get("last_seen_at")
            closed_at = acc.get("closed_at")
            last_seen = None if last_seen is None else _as_date(last_seen)
            closed_at = None if closed_at is None else _as_date(closed_at)
            dues = []
            if last_seen is not None:
                dues.append(last_seen + INACTIVITY)
            if closed_at is not None:
                dues.append(closed_at + CLOSED_GRACE)
            if not dues:
                continue
            due = min(dues)
            if due <= today:
                action = "anonymise" if acc.get("unpaid_invoices") else "delete"
            elif due <= today + WARN_WINDOW:
                if closed_at is not None and acc.get("closed_by") != "staff":
                    seen.add(aid)
                    continue
                action = "warn"
            else:
                seen.add(aid)
                continue
            seen.add(aid)
            cands.append((aid, action, due, closed_at is not None))
        except (KeyError, TypeError, OverflowError, ValueError):
            continue

    deletes = sorted(
        (c for c in cands if c[1] == "delete"),
        key=lambda c: (0 if c[3] else 1, c[2], _idkey(c[0])),
    )[:DELETE_CAP]
    kept = [c for c in cands if c[1] != "delete"] + deletes
    kept.sort(key=lambda c: _idkey(c[0]))
    return [
        {
            "account_id": aid,
            "action": action,
            "due": due.isoformat(),
            "approved_by": None if action == "warn" else APPROVER,
        }
        for aid, action, due, _ in kept
    ]


class PurgeTests(unittest.TestCase):
    T = date(2026, 10, 13)

    def acc(self, i, **kw):
        base = dict(id=i, email="m@example.com", status="x", last_seen_at=date(2026, 1, 1),
                    last_login=None, closed_at=None, closed_by=None,
                    unpaid_invoices=False, litigation_hold=False)
        base.update(kw)
        return base

    def run_one(self, **kw):
        return plan_purge([self.acc(1, **kw)], self.T)

    def test_delete_and_boundaries(self):
        r = self.run_one(last_seen_at=self.T - timedelta(days=730))
        self.assertEqual(r, [{"account_id": 1, "action": "delete",
                              "due": self.T.isoformat(), "approved_by": APPROVER}])
        self.assertEqual(self.run_one(last_seen_at=self.T - timedelta(days=729))[0]["action"], "warn")
        self.assertEqual(self.run_one(last_seen_at=self.T - timedelta(days=716))[0]["action"], "warn")
        self.assertEqual(self.run_one(last_seen_at=self.T - timedelta(days=715)), [])

    def test_warn_has_no_approver_and_no_email(self):
        r = self.run_one(last_seen_at=self.T - timedelta(days=720))[0]
        self.assertIsNone(r["approved_by"])
        self.assertEqual(set(r), {"account_id", "action", "due", "approved_by"})

    def test_anonymise_and_warn_unpaid(self):
        r = self.run_one(last_seen_at=date(2020, 1, 1), unpaid_invoices=True)
        self.assertEqual(r[0]["action"], "anonymise")
        r = self.run_one(last_seen_at=self.T - timedelta(days=720), unpaid_invoices=True)
        self.assertEqual(r[0]["action"], "warn")

    def test_closed_earlier_due(self):
        r = self.run_one(closed_at=self.T - timedelta(days=30), closed_by="member")
        self.assertEqual(r[0]["action"], "delete")

    def test_warn_suppression_for_closed(self):
        c = self.T - timedelta(days=20)
        self.assertEqual(self.run_one(closed_at=c, closed_by="member"), [])
        self.assertEqual(self.run_one(closed_at=c, closed_by=None), [])
        self.assertEqual(self.run_one(closed_at=c, closed_by="staff")[0]["action"], "warn")

    def test_exclusions(self):
        old = date(2000, 1, 1)
        self.assertEqual(self.run_one(last_seen_at=old, litigation_hold=True), [])
        self.assertEqual(self.run_one(last_seen_at=old, email=" X@Tidewater-Klatring.no "), [])
        self.assertEqual(len(self.run_one(last_seen_at=old, email=None)), 1)

    def test_no_last_seen_nor_closed(self):
        self.assertEqual(self.run_one(last_seen_at=None), [])

    def test_cap_priority_and_sort(self):
        accs = [self.acc(i, last_seen_at=date(2000, 1, 1)) for i in range(1, 201)]
        accs.append(self.acc(500, last_seen_at=date(2026, 1, 1), closed_at=date(2026, 1, 1)))
        accs.append(self.acc(501, last_seen_at=date(2000, 1, 1), unpaid_invoices=True))
        r = plan_purge(accs, self.T)
        ids = [a["account_id"] for a in r]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(sum(a["action"] == "delete" for a in r), 200)
        self.assertIn(500, ids)
        self.assertNotIn(200, ids)
        self.assertIn(501, ids)

    def test_defensive_and_no_mutation(self):
        good = self.acc(2, last_seen_at=date(2000, 1, 1))
        bad = [None, {"email": "a"}, self.acc(3, last_seen_at="2000-01-01"),
               self.acc([1]), self.acc(4, last_seen_at=date(9999, 12, 31), closed_at=None)]
        snapshot = dict(good)
        r = plan_purge(bad + [good, dict(good)], datetime(2026, 10, 13, 5, 0))
        self.assertEqual([a["account_id"] for a in r], [2])
        self.assertEqual(good, snapshot)

    def test_datetime_inputs(self):
        r = self.run_one(last_seen_at=datetime(2000, 1, 1, 12))
        self.assertEqual(r[0]["due"], "2001-12-31")


if __name__ == "__main__":
    unittest.main()