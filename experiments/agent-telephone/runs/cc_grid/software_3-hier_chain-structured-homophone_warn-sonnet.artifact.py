# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-7u0cpmyy/purge.py
"""Tidewater Climbing GDPR member-account clean-up planner.

Decisions (D1-D8):
D1. MAX_PURGES_PER_RUN (200) counts delete AND anonymise combined. Over cap:
    closed accounts first, then earlier due, then id ascending; excess accounts
    get no action at all (not even warn). Warns are not capped. Output is
    sorted by account id as given (no coercion).
D2. Warn only if today < due <= today + 40 days (inclusive). Applies also to
    unpaid accounts. Warn `due` is the future due date.
D3. last_seen_at None/missing: no inactivity due date; never use last_login.
D4. Staff email: case-insensitive, stripped, suffix @tidewater-klatring.no.
D5. unpaid_invoices: truthy means unpaid (count or list).
D6. litigation_hold: truthy means hold.
D7. Closed means closed_at is not None; status ignored. closed_by == "member"
    suppresses warn only; a due member-closed account is still deleted.
D8. due is date.isoformat(); arithmetic via timedelta.

Deviation: the team house rule says to add `email` to each action, but R9
(and the exact-four-keys requirement) forbids it, so email is NOT included.
The specific, privacy-protecting requirement was followed.
"""
import datetime as _dt

DPO_NAME = "Þórdís Sveinbjörnsdóttir"
MAX_PURGES_PER_RUN = 200
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 40
STAFF_SUFFIX = "@tidewater-klatring.no"


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def _due(acc):
    cands = []
    seen = acc.get("last_seen_at")
    if seen is not None:
        cands.append(seen + _dt.timedelta(days=INACTIVITY_DAYS))
    closed = acc.get("closed_at")
    if closed is not None:
        cands.append(closed + _dt.timedelta(days=CLOSED_GRACE_DAYS))
    return min(cands) if cands else None


def plan_purge(accounts, today):
    horizon = today + _dt.timedelta(days=WARN_WINDOW_DAYS)
    purges = []  # (closed_rank, due, id, action)
    warns = []
    for acc in accounts:
        if acc.get("litigation_hold") or _is_staff(acc.get("email")):
            continue
        due = _due(acc)
        if due is None:
            continue
        aid = acc.get("id")
        closed = acc.get("closed_at") is not None
        if due <= today:
            kind = "anonymise" if acc.get("unpaid_invoices") else "delete"
            purges.append((0 if closed else 1, due, aid, {
                "account_id": aid, "action": kind,
                "due": due.isoformat(), "approved_by": DPO_NAME}))
        elif due <= horizon:
            if closed and acc.get("closed_by") == "member":
                continue
            warns.append({"account_id": aid, "action": "warn",
                          "due": due.isoformat(), "approved_by": None})
    purges.sort(key=lambda p: (p[0], p[1], p[2]))
    result = [p[3] for p in purges[:MAX_PURGES_PER_RUN]] + warns
    result.sort(key=lambda a: a["account_id"])
    return result


# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-7u0cpmyy/test_purge.py
import copy
import datetime as dt
import unittest

from purge import DPO_NAME, MAX_PURGES_PER_RUN, plan_purge

TODAY = dt.date(2026, 10, 13)
D = dt.timedelta


def acc(id=1, **kw):
    base = dict(id=id, email="m@example.com", status="active",
                last_seen_at=TODAY - D(days=10), last_login=TODAY - D(days=10),
                closed_at=None, closed_by=None, unpaid_invoices=0,
                litigation_hold=False)
    base.update(kw)
    return base


def seen_due(days_until):
    """last_seen_at such that due = TODAY + days_until."""
    return TODAY + D(days=days_until) - D(days=730)


def plan(*a):
    return plan_purge(list(a), TODAY)


class T(unittest.TestCase):
    def test_r1_last_login_ignored(self):
        self.assertEqual(plan(acc(last_seen_at=TODAY - D(days=5),
                                  last_login=TODAY - D(days=2000))), [])
        r = plan(acc(last_seen_at=TODAY - D(days=730),
                     last_login=TODAY - D(days=1)))
        self.assertEqual(r[0]["action"], "delete")

    def test_boundary(self):
        self.assertEqual(plan(acc(last_seen_at=seen_due(0)))[0]["action"], "delete")
        self.assertEqual(plan(acc(last_seen_at=seen_due(1)))[0]["action"], "warn")

    def test_closed_sooner(self):
        a = acc(last_seen_at=TODAY - D(days=100), closed_at=TODAY - D(days=30))
        self.assertEqual(plan(a)[0]["action"], "delete")
        a = acc(last_seen_at=TODAY - D(days=100), closed_at=TODAY - D(days=29))
        r = plan(a)
        self.assertEqual(r[0]["action"], "warn")
        self.assertEqual(r[0]["due"], (TODAY + D(days=1)).isoformat())

    def test_closed_not_sooner(self):
        a = acc(last_seen_at=seen_due(-5), closed_at=TODAY - D(days=1))
        r = plan(a)
        self.assertEqual(r[0]["due"], (TODAY - D(days=5)).isoformat())

    def test_warn_window(self):
        self.assertEqual(plan(acc(last_seen_at=seen_due(1)))[0]["action"], "warn")
        self.assertEqual(plan(acc(last_seen_at=seen_due(40)))[0]["action"], "warn")
        self.assertEqual(plan(acc(last_seen_at=seen_due(41))), [])

    def test_member_closed(self):
        a = acc(last_seen_at=TODAY, closed_at=TODAY - D(days=20), closed_by="member")
        self.assertEqual(plan(a), [])
        a = acc(closed_at=TODAY - D(days=30), closed_by="member")
        self.assertEqual(plan(a)[0]["action"], "delete")

    def test_staff_closed_warns(self):
        a = acc(closed_at=TODAY - D(days=20), closed_by="staff")
        self.assertEqual(plan(a)[0]["action"], "warn")

    def test_unpaid(self):
        for v in (2, ["inv1"]):
            r = plan(acc(last_seen_at=seen_due(-1), unpaid_invoices=v))
            self.assertEqual(r[0]["action"], "anonymise")
            self.assertEqual(r[0]["approved_by"], DPO_NAME)
        r = plan(acc(last_seen_at=seen_due(5), unpaid_invoices=1))
        self.assertEqual(r[0]["action"], "warn")

    def test_hold(self):
        self.assertEqual(plan(acc(last_seen_at=seen_due(-1), litigation_hold=True)), [])
        self.assertEqual(plan(acc(last_seen_at=seen_due(5), litigation_hold=True)), [])

    def test_staff_email(self):
        for e in ("a@tidewater-klatring.no", "A@Tidewater-Klatring.NO ",
                  " x@TIDEWATER-KLATRING.no"):
            self.assertEqual(plan(acc(email=e, last_seen_at=seen_due(-1))), [])
        self.assertEqual(len(plan(acc(email=None, last_seen_at=seen_due(-1)))), 1)

    def test_keys_no_email(self):
        r = plan(acc(1, last_seen_at=seen_due(-1)), acc(2, last_seen_at=seen_due(3)))
        for a in r:
            self.assertEqual(set(a), {"account_id", "action", "due", "approved_by"})
            self.assertNotIn("m@example.com", repr(a))

    def test_approved_by_and_iso(self):
        r = plan(acc(1, last_seen_at=seen_due(-1)), acc(2, last_seen_at=seen_due(3)))
        self.assertEqual(r[0]["approved_by"], "Þórdís Sveinbjörnsdóttir")
        self.assertIsNone(r[1]["approved_by"])
        self.assertIsInstance(r[1]["due"], str)
        self.assertEqual(r[1]["due"], (TODAY + D(days=3)).isoformat())

    def test_cap(self):
        accs = [acc(i, last_seen_at=TODAY - D(days=800 + i)) for i in range(1, 151)]
        accs += [acc(1000 + i, last_seen_at=TODAY, closed_at=TODAY - D(days=30 + i))
                 for i in range(60)]
        warn = acc(5000, last_seen_at=seen_due(5))
        r = plan_purge(accs + [warn], TODAY)
        purges = [a for a in r if a["action"] != "warn"]
        self.assertEqual(len(purges), MAX_PURGES_PER_RUN)
        ids = {a["account_id"] for a in purges}
        self.assertTrue(all(1000 + i in ids for i in range(60)))
        # earliest-due unclosed kept: highest i has earliest due
        self.assertIn(150, ids)
        self.assertIn(11, ids)
        self.assertNotIn(10, ids)
        self.assertNotIn(1, ids)
        self.assertEqual(sum(1 for a in r if a["action"] == "warn"), 1)
        self.assertEqual([a["account_id"] for a in r],
                         sorted(a["account_id"] for a in r))

    def test_cap_combined_anonymise(self):
        accs = [acc(i, last_seen_at=seen_due(-1), unpaid_invoices=1 if i % 2 else 0)
                for i in range(250)]
        self.assertEqual(len(plan_purge(accs, TODAY)), 200)

    def test_sorted(self):
        r = plan(acc(3, last_seen_at=seen_due(-1)), acc(1, last_seen_at=seen_due(2)),
                 acc(2, last_seen_at=seen_due(-3)))
        self.assertEqual([a["account_id"] for a in r], [1, 2, 3])

    def test_tenant_ignored(self):
        a = acc(last_seen_at=seen_due(-1))
        b = dict(a, tenant="x")
        self.assertEqual(plan(a), plan(b))

    def test_last_seen_none(self):
        self.assertEqual(plan(acc(last_seen_at=None, last_login=TODAY - D(days=3000))), [])
        a = acc(last_seen_at=None, closed_at=TODAY - D(days=30))
        self.assertEqual(plan(a)[0]["action"], "delete")
        a = acc(closed_at=TODAY - D(days=30))
        del a["last_seen_at"]
        self.assertEqual(plan(a)[0]["action"], "delete")

    def test_no_mutation(self):
        accs = [acc(1, last_seen_at=seen_due(-1), tenant="t"),
                acc(2, last_seen_at=seen_due(4))]
        snap = copy.deepcopy(accs)
        plan_purge(accs, TODAY)
        self.assertEqual(accs, snap)


if __name__ == "__main__":
    unittest.main()

# NOTE: I had no tools in this run, so the files were not written to disk and the tests were not executed. Save the two sections above as purge.py and test_purge.py in the target directory and run `python3 -I -m unittest test_purge` from there.