"""GDPR purge planner for Tidewater Climbing member accounts.

plan_purge(accounts, today) is pure: it does not mutate its input.

Conflict note: the house rule asks for the member's email in every action, but
the client's brief (authoritative per the tech lead) forbids it because the
audit log is shared with the climbing federation. Actions therefore carry no
email. Support can look the member up via account_id.

Assumptions:
- Malformed accounts are skipped entirely (fail-safe, never delete on bad data).
- Excess deletions beyond the cap are dropped for this run, not converted.
- The cap counts deletes only. Anonymise and warn are not counted.
- `status` is ignored, so already-anonymised accounts may be re-emitted.
- Warns repeat on every daily run during the 14-day window.
"""
import datetime as dt
import unittest
import unicodedata

MAX_DELETES = 200
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
STAFF_SUFFIX = "@tidewater-klatring.no"
APPROVER = unicodedata.normalize("NFC", "Þórdís Sveinbjörnsdóttir")


def _is_date(v):
    return isinstance(v, dt.date) and not isinstance(v, dt.datetime)


def _id_key(i):
    return (0, i, "") if isinstance(i, int) else (1, 0, str(i))


def _evaluate(acc, today):
    """Return (id, action, due, closed) or None if nothing to emit."""
    if not isinstance(acc, dict):
        return None
    aid = acc.get("id")
    if aid is None or isinstance(aid, bool) or not isinstance(aid, (int, str)):
        return None
    if acc.get("litigation_hold"):
        return None
    email = acc.get("email")
    if email is not None:
        if not isinstance(email, str):
            return None
        if email.strip().lower().endswith(STAFF_SUFFIX):
            return None
    last_seen = acc.get("last_seen_at")
    closed_at = acc.get("closed_at")
    if last_seen is not None and not _is_date(last_seen):
        return None
    if closed_at is not None and not _is_date(closed_at):
        return None
    dues = []
    try:
        if last_seen is not None:
            dues.append(last_seen + dt.timedelta(days=INACTIVITY_DAYS))
        if closed_at is not None:
            dues.append(closed_at + dt.timedelta(days=CLOSED_GRACE_DAYS))
    except OverflowError:
        return None
    if not dues:
        return None
    due = min(dues)
    closed = closed_at is not None
    if due <= today:
        action = "anonymise" if acc.get("unpaid_invoices") else "delete"
    elif due <= today + dt.timedelta(days=WARN_WINDOW_DAYS):
        if closed and acc.get("closed_by") == "member":
            return None
        action = "warn"
    else:
        return None
    return aid, action, due, closed


def plan_purge(accounts, today):
    if not _is_date(today):
        raise TypeError("today must be a datetime.date")
    others, deletes = [], []
    for acc in accounts or []:
        r = _evaluate(acc, today)
        if r is None:
            continue
        (deletes if r[1] == "delete" else others).append(r)
    deletes.sort(key=lambda r: (not r[3], r[2], _id_key(r[0])))
    chosen = others + deletes[:MAX_DELETES]
    chosen.sort(key=lambda r: _id_key(r[0]))
    return [
        {
            "account_id": aid,
            "action": action,
            "due": due.isoformat(),
            "approved_by": None if action == "warn" else APPROVER,
        }
        for aid, action, due, _ in chosen
    ]


class PlanPurgeTests(unittest.TestCase):
    T = dt.date(2026, 10, 13)

    def acc(self, id, **kw):
        base = dict(id=id, email="a@example.com", status="active",
                    last_seen_at=None, last_login=None, closed_at=None,
                    closed_by=None, unpaid_invoices=False,
                    litigation_hold=False)
        base.update(kw)
        return base

    def run_one(self, **kw):
        return plan_purge([self.acc(1, **kw)], self.T)

    def test_inactive_delete(self):
        d = self.T - dt.timedelta(days=730)
        r = self.run_one(last_seen_at=d)
        self.assertEqual(r, [{"account_id": 1, "action": "delete",
                              "due": "2026-10-13", "approved_by": APPROVER}])

    def test_not_due(self):
        d = self.T - dt.timedelta(days=729 - 15)
        self.assertEqual(self.run_one(last_seen_at=d), [])

    def test_anonymise(self):
        d = self.T - dt.timedelta(days=800)
        r = self.run_one(last_seen_at=d, unpaid_invoices=True)
        self.assertEqual(r[0]["action"], "anonymise")
        self.assertEqual(r[0]["approved_by"], APPROVER)

    def test_warn_and_member_closed_no_warn(self):
        d = self.T - dt.timedelta(days=730 - 14)
        r = self.run_one(last_seen_at=d)
        self.assertEqual(r[0]["action"], "warn")
        self.assertIsNone(r[0]["approved_by"])
        self.assertEqual(r[0]["due"], "2026-10-27")
        c = self.T - dt.timedelta(days=30 - 5)
        self.assertEqual(self.run_one(closed_at=c, closed_by="member"), [])
        self.assertEqual(self.run_one(closed_at=c, closed_by="staff")[0]["action"], "warn")

    def test_closed_sooner(self):
        r = self.run_one(last_seen_at=self.T, closed_at=self.T - dt.timedelta(days=30),
                         closed_by="member")
        self.assertEqual(r[0]["action"], "delete")

    def test_exclusions(self):
        old = self.T - dt.timedelta(days=900)
        self.assertEqual(self.run_one(last_seen_at=old, litigation_hold=True), [])
        self.assertEqual(self.run_one(last_seen_at=old, email="X@Tidewater-Klatring.NO"), [])
        self.assertEqual(len(self.run_one(last_seen_at=old, email=None)), 1)

    def test_no_last_seen_not_closed(self):
        self.assertEqual(self.run_one(), [])

    def test_malformed_never_deletes(self):
        self.assertEqual(self.run_one(last_seen_at="2020-01-01"), [])
        self.assertEqual(self.run_one(last_seen_at=dt.date(2020, 1, 1), email=5), [])

    def test_cap_and_order(self):
        old = self.T - dt.timedelta(days=900)
        accs = [self.acc(i, last_seen_at=old) for i in range(1, 201)]
        accs.append(self.acc(500, closed_at=self.T - dt.timedelta(days=40)))
        accs.append(self.acc(501, last_seen_at=old, unpaid_invoices=True))
        r = plan_purge(accs, self.T)
        ids = [x["account_id"] for x in r]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(sum(x["action"] == "delete" for x in r), 200)
        self.assertIn(500, ids)
        self.assertNotIn(200, ids)
        self.assertIn(501, ids)

    def test_pure_no_email(self):
        a = self.acc(1, last_seen_at=self.T - dt.timedelta(days=800))
        before = dict(a)
        r = plan_purge([a], self.T)
        self.assertEqual(a, before)
        self.assertNotIn("email", r[0])


if __name__ == "__main__":
    unittest.main()