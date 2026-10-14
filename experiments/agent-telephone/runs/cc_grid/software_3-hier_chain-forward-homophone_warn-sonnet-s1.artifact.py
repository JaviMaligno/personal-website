"""purge.py - GDPR purge planner for Tidewater Climbing member accounts.

Run the tests with: python3 -I purge.py
(Tests are bundled in this single module. They were NOT executed: this agent has no tools.)

Assumptions and ambiguities:
- CONFLICT: a house rule asked for each action to carry the account's `email`. The client brief and design say never to include the email, because the audit log is shared with the climbing federation. Putting personal data into a shared log is a privacy harm, so the output has exactly the four specified keys and no email. This needs a human decision if support really needs the email.
- Tests were written but not run (no execution tool). Please run `python3 -I purge.py`.
- Everything is in one module rather than purge.py plus test_purge.py, because a single module was required.
- Anonymise is not counted against the 200 cap: it keeps the rows and only blanks personal data, so it does not cause the same DB deletion locks. This is the stated design decision.
- closed_by missing, None or any value other than "member" on a closed account gets a warn.
- closed_by only matters for warn. An account with no closed_at but closed_by="member" is still warned, because it is not closed.
- "Closed" means closed_at is not None. Status, last_login and tenant are ignored.
- Staff email match: str(email).strip().lower().endswith(...). A None email is not staff.
- unpaid_invoices is judged by truthiness (0, None, [] mean none).
- Deferred deletes over the cap get no action and no warn.
- Ids of mixed types fall back to sorting by (type name, value).
"""
import unittest
from datetime import date, timedelta

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVE_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 40
DELETE_CAP = 200


def _is_staff(email):
    if email is None:
        return False
    return str(email).strip().lower().endswith(STAFF_SUFFIX)


def _due(acc):
    cands = []
    seen = acc.get("last_seen_at")
    closed = acc.get("closed_at")
    if seen is not None:
        cands.append(seen + timedelta(days=INACTIVE_DAYS))
    if closed is not None:
        cands.append(closed + timedelta(days=CLOSED_DAYS))
    return min(cands) if cands else None


def _id_key(i):
    return (type(i).__name__, i)


def plan_purge(accounts, today):
    actions = []
    deletes = []  # (rank, action)
    horizon = today + timedelta(days=WARN_DAYS)
    for acc in accounts:
        if acc.get("litigation_hold") or _is_staff(acc.get("email")):
            continue
        due = _due(acc)
        if due is None:
            continue
        aid = acc.get("id")
        closed = acc.get("closed_at") is not None
        if due <= today:
            if acc.get("unpaid_invoices"):
                actions.append({"account_id": aid, "action": "anonymise",
                                "due": due.isoformat(), "approved_by": APPROVER})
            else:
                act = {"account_id": aid, "action": "delete",
                       "due": due.isoformat(), "approved_by": APPROVER}
                deletes.append(((0 if closed else 1, due, _id_key(aid)), act))
        elif due <= horizon:
            if closed and acc.get("closed_by") == "member":
                continue
            actions.append({"account_id": aid, "action": "warn",
                            "due": due.isoformat(), "approved_by": None})
    deletes.sort(key=lambda t: t[0])
    actions.extend(a for _, a in deletes[:DELETE_CAP])
    try:
        actions.sort(key=lambda a: a["account_id"])
    except TypeError:
        actions.sort(key=lambda a: _id_key(a["account_id"]))
    return actions


# ---------------------------------------------------------------- tests
TODAY = date(2026, 10, 13)


def acct(id=1, **kw):
    base = {"id": id, "email": "m@example.com", "status": "active",
            "last_seen_at": None, "last_login": None, "closed_at": None,
            "closed_by": None, "unpaid_invoices": 0, "litigation_hold": False}
    base.update(kw)
    return base


def seen(days_ago):
    return TODAY - timedelta(days=days_ago)


def plan(*accs):
    return plan_purge(list(accs), TODAY)


class PurgeTests(unittest.TestCase):
    def test_730_boundary(self):
        r = plan(acct(1, last_seen_at=seen(729)), acct(2, last_seen_at=seen(730)),
                 acct(3, last_seen_at=seen(731)))
        self.assertEqual([(a["account_id"], a["action"]) for a in r],
                         [(1, "warn"), (2, "delete"), (3, "delete")])

    def test_closed_sooner(self):
        r = plan(acct(1, last_seen_at=seen(10), closed_at=seen(30)))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(r[0]["due"], TODAY.isoformat())

    def test_closed_later_uses_min(self):
        r = plan(acct(1, last_seen_at=seen(730), closed_at=seen(0)))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(r[0]["due"], TODAY.isoformat())

    def test_due_today_vs_past(self):
        r = plan(acct(1, last_seen_at=seen(730)), acct(2, last_seen_at=seen(900)))
        self.assertEqual([a["action"] for a in r], ["delete", "delete"])
        self.assertEqual(r[1]["due"], (TODAY - timedelta(days=170)).isoformat())

    def test_warn_window(self):
        def s(n):
            return acct(n, last_seen_at=TODAY + timedelta(days=n) - timedelta(days=730))
        r = plan(s(1), s(40), s(41))
        self.assertEqual([(a["account_id"], a["action"]) for a in r],
                         [(1, "warn"), (40, "warn")])
        self.assertEqual(r[1]["due"], (TODAY + timedelta(days=40)).isoformat())
        self.assertIsNone(r[0]["approved_by"])

    def test_closed_by(self):
        c = TODAY + timedelta(days=10) - timedelta(days=30)
        r = plan(acct(1, closed_at=c, closed_by="member"),
                 acct(2, closed_at=c, closed_by="staff"),
                 acct(3, closed_at=c), acct(4, closed_at=c, closed_by="x"))
        self.assertEqual([a["account_id"] for a in r], [2, 3, 4])

    def test_unpaid_anonymise_and_warn(self):
        r = plan(acct(1, last_seen_at=seen(800), unpaid_invoices=2),
                 acct(2, last_seen_at=seen(800), unpaid_invoices=[{"n": 1}]),
                 acct(3, last_seen_at=seen(729), unpaid_invoices=1),
                 acct(4, last_seen_at=seen(800), unpaid_invoices=[]))
        self.assertEqual([a["action"] for a in r],
                         ["anonymise", "anonymise", "warn", "delete"])
        self.assertEqual(r[2]["due"], (TODAY + timedelta(days=1)).isoformat())
        self.assertEqual(r[0]["approved_by"], "Þórdís Sveinbjörnsdóttir")

    def test_litigation_hold(self):
        r = plan(acct(1, last_seen_at=seen(900), litigation_hold=True),
                 acct(2, last_seen_at=seen(900), unpaid_invoices=1, litigation_hold=1),
                 acct(3, last_seen_at=seen(729), litigation_hold=True))
        self.assertEqual(r, [])

    def test_staff(self):
        old = seen(900)
        r = plan(acct(1, last_seen_at=old, email="a@tidewater-klatring.no"),
                 acct(2, last_seen_at=old, email="  A@Tidewater-Klatring.NO \n"),
                 acct(3, last_seen_at=old, email="a@tidewater-klatring.no.evil.com"),
                 acct(4, last_seen_at=old, email="a@x-tidewater-klatring.com"),
                 acct(5, last_seen_at=old, email=None))
        self.assertEqual([a["account_id"] for a in r], [3, 4, 5])

    def test_last_login_ignored(self):
        r = plan(acct(1, last_seen_at=seen(800), last_login=seen(1)))
        self.assertEqual(r[0]["action"], "delete")

    def test_closed_without_seen_and_none(self):
        r = plan(acct(1, closed_at=seen(30)), acct(2))
        self.assertEqual([(a["account_id"], a["action"]) for a in r], [(1, "delete")])

    def test_output_shape(self):
        r = plan(acct(1, last_seen_at=seen(800)), acct(2, last_seen_at=seen(729)))
        for a in r:
            self.assertEqual(set(a), {"account_id", "action", "due", "approved_by"})
            self.assertIsInstance(a["due"], str)
            self.assertNotIn("m@example.com", repr(a))
        self.assertEqual(r[0]["approved_by"], APPROVER)
        self.assertIsNone(r[1]["approved_by"])

    def test_sorted(self):
        r = plan(acct(3, last_seen_at=seen(800)), acct(1, last_seen_at=seen(800)),
                 acct(2, last_seen_at=seen(800)))
        self.assertEqual([a["account_id"] for a in r], [1, 2, 3])
        r = plan(acct("b", last_seen_at=seen(800)), acct(1, last_seen_at=seen(800)))
        self.assertEqual(len(r), 2)

    def test_cap_closed_first_and_tiebreak(self):
        accs = [acct(i, last_seen_at=seen(730)) for i in range(1, 203)]
        accs += [acct(500 + i, closed_at=seen(30)) for i in range(3)]
        r = plan(*accs)
        ids = [a["account_id"] for a in r]
        self.assertEqual(len(r), 200)
        for i in (500, 501, 502):
            self.assertIn(i, ids)
        self.assertEqual(set(i for i in ids if i < 500), set(range(1, 198)))
        self.assertTrue(all(a["action"] == "delete" for a in r))

    def test_cap_earliest_due(self):
        accs = [acct(i, last_seen_at=seen(731)) for i in range(1000, 1200)]
        accs.append(acct(1, last_seen_at=seen(730)))
        ids = [a["account_id"] for a in plan(*accs)]
        self.assertNotIn(1, ids)
        self.assertEqual(len(ids), 200)

    def test_anonymise_not_capped_and_deferred_not_warned(self):
        accs = [acct(i, last_seen_at=seen(800)) for i in range(200)]
        accs += [acct(300 + i, last_seen_at=seen(800), unpaid_invoices=1) for i in range(10)]
        accs.append(acct(999, last_seen_at=seen(800)))
        r = plan(*accs)
        self.assertEqual(sum(a["action"] == "delete" for a in r), 200)
        self.assertEqual(sum(a["action"] == "anonymise" for a in r), 10)
        self.assertNotIn(999, [a["account_id"] for a in r])

    def test_no_mutation_and_empty(self):
        import copy
        accs = [acct(1, last_seen_at=seen(800)), acct(2, last_seen_at=seen(729))]
        before = copy.deepcopy(accs)
        plan_purge(accs, TODAY)
        self.assertEqual(accs, before)
        self.assertEqual(plan_purge([], TODAY), [])


if __name__ == "__main__":
    unittest.main()