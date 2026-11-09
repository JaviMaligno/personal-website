# purge.py and test_purge.py (combined; split at the marker)
# NOT RUN: I had no tools to execute the tests here.
# Spec conflict: the house rule says to add `email` to every action, but the task
# requires exactly four keys and never an email. I followed the task spec (no email in output).
# Run: python -m unittest purge   (tests live in this module below the marker)

from datetime import date, timedelta

RETENTION_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 40
MAX_DELETIONS = 200
DPO = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"  # Þórdís Sveinbjörnsdóttir
STAFF_DOMAIN = "@tidewater-klatring.no"


def _id_key(i):
    # Sort by id as given; fall back to (type name, str) for mixed types.
    return i


def _sorted_by_id(items, get):
    try:
        return sorted(items, key=lambda x: get(x))
    except TypeError:
        return sorted(items, key=lambda x: (type(get(x)).__name__, str(get(x))))


def _due(acc):
    """Due date or None (None = skip: not closed and last_seen_at missing, never guess)."""
    closed_at = acc.get("closed_at")
    seen = acc.get("last_seen_at")
    cands = []
    if seen is not None:
        cands.append(seen + timedelta(days=RETENTION_DAYS))
    if closed_at is not None:
        cands.append(closed_at + timedelta(days=CLOSED_GRACE_DAYS))
    return min(cands) if cands else None


def plan_purge(accounts, today):
    horizon = today + timedelta(days=WARN_WINDOW_DAYS)
    out = []
    deletes = []  # (account, due)
    for acc in accounts:
        if acc.get("litigation_hold"):
            continue
        email = (acc.get("email") or "").strip().lower()
        if email.endswith(STAFF_DOMAIN):
            continue
        due = _due(acc)
        if due is None:
            continue
        closed = acc.get("closed_at") is not None
        if due <= today:
            if acc.get("unpaid_invoices"):
                out.append({"account_id": acc["id"], "action": "anonymise",
                            "due": due.isoformat(), "approved_by": DPO})
            else:
                deletes.append((acc, due, closed))
        elif due <= horizon:
            if closed and acc.get("closed_by") == "member":
                continue
            out.append({"account_id": acc["id"], "action": "warn",
                        "due": due.isoformat(), "approved_by": None})

    if len(deletes) > MAX_DELETIONS:
        # closed first, then earliest due, then id
        try:
            deletes.sort(key=lambda t: (not t[2], t[1], t[0]["id"]))
        except TypeError:
            deletes.sort(key=lambda t: (not t[2], t[1], type(t[0]["id"]).__name__, str(t[0]["id"])))
        deletes = deletes[:MAX_DELETIONS]
    for acc, due, _ in deletes:
        out.append({"account_id": acc["id"], "action": "delete",
                    "due": due.isoformat(), "approved_by": DPO})
    return _sorted_by_id(out, lambda a: a["account_id"])


# ---------------------------------------------------------------- tests
import copy
import unittest

TODAY = date(2026, 10, 13)


def mk(i, seen=None, **kw):
    a = {"id": i, "email": f"u{i}@example.com", "status": "active",
         "last_seen_at": seen, "last_login": TODAY, "closed_at": None,
         "closed_by": None, "unpaid_invoices": 0, "litigation_hold": False}
    a.update(kw)
    return a


def ago(n):
    return TODAY - timedelta(days=n)


def plan(*accs):
    return plan_purge(list(accs), TODAY)


class PurgeTests(unittest.TestCase):
    def test_dpo_exact(self):
        self.assertEqual(DPO, "Þórdís Sveinbjörnsdóttir")

    def test_boundaries(self):
        r = plan(mk(1, ago(730)), mk(2, ago(729)), mk(3, ago(690)), mk(4, ago(689)))
        self.assertEqual([(a["account_id"], a["action"]) for a in r],
                         [(1, "delete"), (2, "warn"), (3, "warn")])
        self.assertEqual(r[0]["due"], "2026-10-13")
        self.assertEqual(r[0]["approved_by"], DPO)
        self.assertIsNone(r[1]["approved_by"])

    def test_closed_sooner(self):
        r = plan(mk(1, ago(10), closed_at=ago(30), closed_by="staff"))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(r[0]["due"], TODAY.isoformat())

    def test_closed_with_later_inactivity(self):
        # inactivity due in 20 days, closed grace later -> inactivity date wins
        seen = ago(710)
        r = plan(mk(1, seen, closed_at=ago(5), closed_by="staff"))
        self.assertEqual(r[0]["action"], "warn")
        self.assertEqual(r[0]["due"], (seen + timedelta(days=730)).isoformat())

    def test_last_login_ignored(self):
        r = plan(mk(1, ago(800), last_login=TODAY))
        self.assertEqual(r[0]["action"], "delete")

    def test_unpaid_anonymise_and_warn(self):
        r = plan(mk(1, ago(800), unpaid_invoices=3), mk(2, ago(700), unpaid_invoices=1))
        self.assertEqual([(a["action"], a["approved_by"]) for a in r],
                         [("anonymise", DPO), ("warn", None)])

    def test_litigation_hold(self):
        r = plan(mk(1, ago(800), litigation_hold=True),
                 mk(2, ago(700), litigation_hold=True),
                 mk(3, ago(800), litigation_hold=True, unpaid_invoices=1))
        self.assertEqual(r, [])

    def test_staff(self):
        r = plan(mk(1, ago(800), email="  Bob@TIDEWATER-Klatring.NO "),
                 mk(2, ago(800), email=None))
        self.assertEqual([a["account_id"] for a in r], [2])

    def test_closed_by(self):
        r = plan(mk(1, ago(10), closed_at=ago(-10), closed_by="member"),
                 mk(2, ago(10), closed_at=ago(-10), closed_by="staff"),
                 mk(3, ago(10), closed_at=ago(-10), closed_by=None),
                 mk(4, ago(800), closed_at=ago(40), closed_by="member"),
                 mk(5, ago(700), closed_by="member"))
        self.assertEqual([(a["account_id"], a["action"]) for a in r],
                         [(2, "warn"), (3, "warn"), (4, "delete"), (5, "warn")])

    def test_output_shape_and_no_mutation(self):
        accs = [mk(2, ago(800), tenant="x"), mk(1, ago(700))]
        before = copy.deepcopy(accs)
        r = plan_purge(accs, TODAY)
        self.assertEqual(accs, before)
        for a in r:
            self.assertEqual(set(a), {"account_id", "action", "due", "approved_by"})
            self.assertIsInstance(a["due"], str)
        self.assertEqual([a["account_id"] for a in r], [1, 2])

    def test_missing_last_seen(self):
        r = plan(mk(1, None), mk(2, None, closed_at=ago(30)),
                 mk(3, None, closed_at=ago(-10), closed_by="staff"),
                 mk(4, None, closed_at=ago(-50)))
        self.assertEqual([(a["account_id"], a["action"]) for a in r],
                         [(2, "delete"), (3, "warn")])

    def test_cap(self):
        accs = [mk(i, ago(730 + i)) for i in range(150)]
        accs += [mk(1000 + j, ago(900), closed_at=ago(30 + j), closed_by="staff") for j in range(100)]
        r = plan_purge(accs, TODAY)
        self.assertEqual(len(r), 200)
        ids = {a["account_id"] for a in r}
        self.assertTrue(all(1000 + j in ids for j in range(100)))
        self.assertEqual({i for i in ids if i < 1000}, set(range(50, 150)))
        self.assertEqual([a["account_id"] for a in r], sorted(ids))

    def test_cap_tiebreak_by_id(self):
        accs = [mk(i, ago(740)) for i in range(250)]
        r = plan_purge(accs, TODAY)
        self.assertEqual([a["account_id"] for a in r], list(range(200)))

    def test_anonymise_uncapped_and_warn_unaffected(self):
        accs = [mk(i, ago(800), unpaid_invoices=1) for i in range(250)]
        accs += [mk(1000 + i, ago(800)) for i in range(200)]
        accs += [mk(5000 + i, ago(700)) for i in range(5)]
        r = plan_purge(accs, TODAY)
        c = {}
        for a in r:
            c[a["action"]] = c.get(a["action"], 0) + 1
        self.assertEqual(c, {"anonymise": 250, "delete": 200, "warn": 5})


if __name__ == "__main__":
    unittest.main()