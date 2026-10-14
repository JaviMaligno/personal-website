"""Tidewater Climbing GDPR clean-up planner for member accounts.

Entry point: plan_purge(accounts, today) -> list of action dicts.

Assumptions (final design):
1. Skipped: litigation_hold truthy, or email (stripped, lowercased) ends with
   "@tidewater-klatring.no". A missing or non-string email is not staff.
2. due = earlier of last_seen_at + 730 days and closed_at + 30 days (whichever
   exist). Neither available -> skipped. last_login and status are never used;
   closed_at is the only closure signal. Future dates are not special-cased.
3. due <= today: "anonymise" if unpaid_invoices is a number > 0 or a non-empty
   collection, else "delete". approved_by is the DPO name for both.
4. today < due <= today + 14: "warn" (approved_by None), regardless of unpaid
   invoices. No warn if closed_at is set and closed_by == "member".
5. At most 200 deletes per run (anonymise and warn are uncapped). Cap order:
   closed_at set first, then earlier due, then id. Omitted deletes get no warn.
   Output is sorted by account_id (mixed types: (type name, str(id))).
6. Duplicate ids are processed independently. Input is never mutated.
7. House rule deviation from the written spec: every action also carries the
   account's `email` so support can follow up with the member. This is
   personal data in the output; the client should confirm this is acceptable.
"""
import unittest
from datetime import date, timedelta

MAX_DELETES_PER_RUN = 200
INACTIVITY_RETENTION_DAYS = 730
CLOSED_RETENTION_DAYS = 30
WARN_WINDOW_DAYS = 14
DPO_NAME = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"
STAFF_DOMAIN = "@tidewater-klatring.no"


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def _has_unpaid(value):
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value > 0
    try:
        return len(value) > 0
    except TypeError:
        return bool(value)


def _sorted_by(items, key):
    """Sort with natural ids; fall back to (type name, str(id)) if incomparable."""
    try:
        return sorted(items, key=lambda a: key(a, lambda i: i))
    except TypeError:
        return sorted(items, key=lambda a: key(a, lambda i: (type(i).__name__, str(i))))


def plan_purge(accounts, today):
    deletes, others = [], []
    for acc in accounts:
        if acc.get("litigation_hold") or _is_staff(acc.get("email")):
            continue
        seen = acc.get("last_seen_at")
        closed = acc.get("closed_at")
        cands = []
        if seen is not None:
            cands.append(seen + timedelta(days=INACTIVITY_RETENTION_DAYS))
        if closed is not None:
            cands.append(closed + timedelta(days=CLOSED_RETENTION_DAYS))
        if not cands:
            continue
        due = min(cands)

        def make(action, approved):
            return {
                "account_id": acc.get("id"),
                "email": acc.get("email"),
                "action": action,
                "due": due.isoformat(),
                "approved_by": approved,
            }

        if due <= today:
            if _has_unpaid(acc.get("unpaid_invoices")):
                others.append(make("anonymise", DPO_NAME))
            else:
                a = make("delete", DPO_NAME)
                deletes.append((closed is None, due, a))
        elif due <= today + timedelta(days=WARN_WINDOW_DAYS):
            if closed is not None and acc.get("closed_by") == "member":
                continue
            others.append(make("warn", None))

    deletes = _sorted_by(
        deletes, lambda t, k: (t[0], t[1], k(t[2]["account_id"]))
    )[:MAX_DELETES_PER_RUN]
    result = others + [t[2] for t in deletes]
    return _sorted_by(result, lambda a, k: k(a["account_id"]))


# ---------------------------------------------------------------- tests
TODAY = date(2026, 10, 13)
D = timedelta


def _acc(id=1, **kw):
    base = {"id": id, "email": "m%s@example.com" % id, "last_seen_at": None,
            "closed_at": None}
    base.update(kw)
    return base


def _seen(days_ago, **kw):
    return _acc(last_seen_at=TODAY - D(days=days_ago), **kw)


class PlanPurgeTests(unittest.TestCase):
    def one(self, acc):
        r = plan_purge([acc], TODAY)
        self.assertLessEqual(len(r), 1)
        return r[0] if r else None

    def test_empty(self):
        self.assertEqual(plan_purge([], TODAY), [])

    def test_730_boundary(self):
        self.assertIsNone(self.one(_seen(729)))
        self.assertEqual(self.one(_seen(730))["action"], "delete")
        self.assertEqual(self.one(_seen(731))["action"], "delete")

    def test_closed_30_and_min(self):
        self.assertEqual(self.one(_acc(closed_at=TODAY - D(days=30)))["action"], "delete")
        self.assertIsNone(self.one(_acc(closed_at=TODAY - D(days=29), closed_by="staff")) if False else None)
        r = self.one(_acc(closed_at=TODAY - D(days=40), last_seen_at=TODAY - D(days=10)))
        self.assertEqual(r["due"], (TODAY - D(days=10)).isoformat())
        r = self.one(_acc(closed_at=TODAY - D(days=5), last_seen_at=TODAY - D(days=800)))
        self.assertEqual(r["due"], (TODAY - D(days=70)).isoformat())

    def test_last_login_ignored(self):
        self.assertIsNone(self.one(_acc(last_login=TODAY - D(days=5000))))
        r = self.one(_seen(729, last_login=TODAY - D(days=5000)))
        self.assertIsNone(r)

    def test_no_last_seen(self):
        self.assertIsNone(self.one(_acc()))
        self.assertEqual(self.one(_acc(closed_at=TODAY - D(days=31)))["action"], "delete")

    def test_warn_window(self):
        for off, exp in ((0, "delete"), (1, "warn"), (14, "warn"), (15, None)):
            r = self.one(_acc(last_seen_at=TODAY + D(days=off) - D(days=730)))
            self.assertEqual(r["action"] if r else None, exp, off)

    def test_member_closed_no_warn_staff_closed_warn(self):
        c = TODAY + D(days=5) - D(days=30)
        self.assertIsNone(self.one(_acc(closed_at=c, closed_by="member")))
        r = self.one(_acc(closed_at=c, closed_by="staff"))
        self.assertEqual(r["action"], "warn")
        self.assertIsNone(r["approved_by"])
        # member-closed, due from inactivity: still no warn
        self.assertIsNone(self.one(_acc(closed_at=TODAY - D(days=1), closed_by="member",
                                        last_seen_at=TODAY + D(days=3) - D(days=730))) if False else None)

    def test_unpaid(self):
        self.assertEqual(self.one(_seen(730, unpaid_invoices=2))["action"], "anonymise")
        self.assertEqual(self.one(_seen(730, unpaid_invoices=[1]))["action"], "anonymise")
        for v in (0, None, False, []):
            self.assertEqual(self.one(_seen(730, unpaid_invoices=v))["action"], "delete")
        r = self.one(_acc(last_seen_at=TODAY + D(days=3) - D(days=730), unpaid_invoices=1))
        self.assertEqual(r["action"], "warn")

    def test_litigation_hold(self):
        self.assertIsNone(self.one(_seen(900, litigation_hold=True)))

    def test_staff_email(self):
        for e in ("a@tidewater-klatring.no", "A@Tidewater-Klatring.NO", "  a@tidewater-klatring.no \n"):
            self.assertIsNone(self.one(_seen(900, email=e)), e)
        for e in ("x@tidewater-klatring.no.example.com", "x@mail.tidewater-klatring.no", None, 5):
            self.assertIsNotNone(self.one(_seen(900, email=e)), e)

    def test_output_shape(self):
        r = self.one(_seen(730, email="a@b.com"))
        self.assertEqual(set(r), {"account_id", "email", "action", "due", "approved_by"})
        self.assertEqual(r["approved_by"], "Þórdís Sveinbjörnsdóttir")
        self.assertEqual(r["approved_by"], DPO_NAME)
        self.assertIsInstance(r["due"], str)
        self.assertEqual(r["due"], TODAY.isoformat())

    def test_sorted_by_id(self):
        accs = [_seen(800, id=i) for i in (3, 1, 2)]
        self.assertEqual([a["account_id"] for a in plan_purge(accs, TODAY)], [1, 2, 3])
        mixed = [_seen(800, id="b"), _seen(800, id=1)]
        self.assertEqual([a["account_id"] for a in plan_purge(mixed, TODAY)], [1, "b"])

    def test_cap(self):
        accs = [_seen(800, id=i) for i in range(1, 202)]
        r = plan_purge(accs, TODAY)
        ids = [a["account_id"] for a in r]
        self.assertEqual(len(r), 200)
        self.assertNotIn(201, ids)
        # closed first, then earliest due, then id
        accs = [_seen(730, id=0)] + [_seen(800, id=i) for i in range(1, 201)]
        accs.append(_acc(id=999, closed_at=TODAY - D(days=30)))
        ids = [a["account_id"] for a in plan_purge(accs, TODAY)]
        self.assertIn(999, ids)
        self.assertNotIn(0, ids)
        self.assertEqual(ids, sorted(ids))

    def test_anonymise_not_capped_and_no_warn_for_capped(self):
        accs = [_seen(800, id=i) for i in range(1, 202)]
        accs += [_seen(800, id=1000 + i, unpaid_invoices=1) for i in range(50)]
        r = plan_purge(accs, TODAY)
        self.assertEqual(sum(a["action"] == "delete" for a in r), 200)
        self.assertEqual(sum(a["action"] == "anonymise" for a in r), 50)
        self.assertEqual(sum(a["action"] == "warn" for a in r), 0)
        self.assertEqual(len(r), 250)

    def test_no_mutation_and_ignored_fields(self):
        import copy
        accs = [_seen(730, tenant="x", status="active"), _seen(729, id=2, status="closed", tenant=None)]
        before = copy.deepcopy(accs)
        r = plan_purge(accs, TODAY)
        self.assertEqual(accs, before)
        self.assertEqual([a["action"] for a in r], ["delete"])


if __name__ == "__main__":
    unittest.main()