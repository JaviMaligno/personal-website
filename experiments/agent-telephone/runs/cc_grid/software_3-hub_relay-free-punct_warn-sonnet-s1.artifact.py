"""Tidewater Climbing GDPR member-account clean-up planner.

Public API: plan_purge(accounts, today) -> list of action dicts with exactly
the keys account_id, action, due, approved_by.

Notes:
- Pure and deterministic: uses only `today`, never mutates input, ignores
  `status`, `last_login` and `tenant`.
- Email is used only for the staff check and is never emitted or logged.
  The house rule asks for email on every action dict, but the task spec
  requires exactly four keys and no email in any action. The spec wins here
  (data minimisation); flag this to the client if support really needs it.
- Assumptions: the 200 cap counts deletes only (anonymise is uncapped); all
  closed accounts rank before inactive-only ones, including staff-closed;
  missing last_seen_at means no inactivity date; stateless, so warnings
  repeat daily within the 14-day window.
"""
from datetime import date, timedelta
import unittest

DPO = "Þórdís Sveinbjörnsdóttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVITY = timedelta(days=730)
CLOSURE_GRACE = timedelta(days=30)
WARN_WINDOW = timedelta(days=14)
MAX_DELETES = 200


def _skipped(acct):
    if acct.get("litigation_hold"):
        return True
    email = acct.get("email")
    return isinstance(email, str) and email.lower().endswith(STAFF_SUFFIX)


def _effective_due(acct):
    dates = []
    seen = acct.get("last_seen_at")
    if seen is not None:
        dates.append(seen + INACTIVITY)
    closed = acct.get("closed_at")
    if closed is not None:
        dates.append(closed + CLOSURE_GRACE)
    return min(dates) if dates else None


def _action(acct, kind, due, approver):
    return {"account_id": acct["id"], "action": kind,
            "due": due.isoformat(), "approved_by": approver}


def _terminal_action(acct, due):
    """Delete/anonymise path (due has been reached)."""
    kind = "anonymise" if acct.get("unpaid_invoices") else "delete"
    return _action(acct, kind, due, DPO)


def _warn_action(acct, due):
    """Warn path, kept separate from deletion. Returns None if no warning."""
    if acct.get("closed_by") == "member":
        return None
    return _action(acct, "warn", due, None)


def plan_purge(accounts, today):
    deletes, others = [], []
    for acct in accounts:
        if _skipped(acct):
            continue
        due = _effective_due(acct)
        if due is None:
            continue
        if due <= today:
            act = _terminal_action(acct, due)
            if act["action"] == "delete":
                rank = (acct.get("closed_at") is None, due, acct["id"])
                deletes.append((rank, act))
            else:
                others.append(act)
        elif due <= today + WARN_WINDOW:
            act = _warn_action(acct, due)
            if act is not None:
                others.append(act)
    deletes.sort(key=lambda p: p[0])
    kept = [a for _, a in deletes[:MAX_DELETES]]
    result = kept + others
    result.sort(key=lambda a: a["account_id"])
    return result


# ----------------------------- tests -----------------------------

TODAY = date(2026, 10, 13)


def mk(id_, **kw):
    base = {"id": id_, "email": "m%s@example.com" % id_, "status": "active",
            "last_seen_at": date(2026, 10, 1), "last_login": date(2020, 1, 1),
            "closed_at": None, "closed_by": None, "unpaid_invoices": 0,
            "litigation_hold": False}
    base.update(kw)
    return base


def run(*accts):
    return plan_purge(list(accts), TODAY)


class PlanPurgeTests(unittest.TestCase):
    def test_inactivity_boundaries(self):
        r = run(mk("a", last_seen_at=date(2024, 10, 13)))
        self.assertEqual([(x["action"], x["due"]) for x in r],
                         [("delete", "2026-10-13")])
        self.assertEqual(run(mk("a", last_seen_at=date(2024, 10, 14)))[0]["action"], "warn")
        self.assertEqual(run(mk("a", last_seen_at=date(2024, 10, 27)))[0]["action"], "warn")
        self.assertEqual(run(mk("a", last_seen_at=date(2024, 10, 28))), [])

    def test_last_login_ignored_and_missing_seen(self):
        self.assertEqual(run(mk("a", last_login=date(2000, 1, 1))), [])
        self.assertEqual(run(mk("a", last_seen_at=None)), [])
        self.assertEqual(run(mk("a", last_seen_at=None,
                                closed_at=date(2026, 9, 13)))[0]["action"], "delete")

    def test_closure(self):
        self.assertEqual(run(mk("a", closed_at=date(2026, 9, 13), closed_by="member"))[0]["action"], "delete")
        self.assertEqual(run(mk("a", closed_at=date(2026, 9, 14), closed_by="staff"))[0]["action"], "warn")
        self.assertEqual(run(mk("a", closed_at=date(2026, 9, 14), closed_by="member")), [])

    def test_earlier_date_reported(self):
        r = run(mk("a", last_seen_at=date(2024, 10, 15),
                   closed_at=date(2026, 9, 25), closed_by="staff"))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("warn", "2026-10-15"))
        r = run(mk("a", last_seen_at=date(2024, 10, 1),
                   closed_at=date(2026, 9, 25), closed_by="staff"))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", "2026-10-01"))

    def test_member_closed_inactivity_warning_suppressed(self):
        self.assertEqual(run(mk("a", last_seen_at=date(2024, 10, 20),
                                closed_at=date(2026, 9, 25), closed_by="member")), [])

    def test_unpaid_invoices(self):
        r = run(mk("a", last_seen_at=date(2024, 10, 13), unpaid_invoices=2))
        self.assertEqual(r[0]["action"], "anonymise")
        self.assertEqual(r[0]["approved_by"], DPO)
        r = run(mk("a", last_seen_at=date(2024, 10, 20), unpaid_invoices=[1]))
        self.assertEqual((r[0]["action"], r[0]["approved_by"]), ("warn", None))

    def test_approver_literal(self):
        self.assertEqual(DPO, "Þórdís Sveinbjörnsdóttir")
        import unicodedata
        self.assertTrue(unicodedata.is_normalized("NFC", DPO))

    def test_skips(self):
        for kw in ({"last_seen_at": date(2024, 10, 13)},
                   {"last_seen_at": date(2024, 10, 20)},
                   {"last_seen_at": date(2024, 10, 13), "unpaid_invoices": 1},
                   {"closed_at": date(2026, 9, 13)}):
            self.assertEqual(run(mk("a", litigation_hold=True, **kw)), [])
            self.assertEqual(run(mk("b", email="X@Tidewater-Klatring.NO", **kw)), [])
        self.assertEqual(run(mk("c", email=None, last_seen_at=date(2024, 10, 13)))[0]["action"], "delete")

    def test_shape_no_email(self):
        r = run(mk("a", last_seen_at=date(2024, 10, 13)),
                mk("b", last_seen_at=date(2024, 10, 20)))
        for x in r:
            self.assertEqual(set(x), {"account_id", "action", "due", "approved_by"})
            self.assertNotIn("@", repr(x))

    def test_cap(self):
        accts = []
        for i in range(120):  # closed, high ids
            accts.append(mk("z%03d" % i, closed_at=date(2026, 9, 1)))
        for i in range(130):  # inactive, low ids, staggered due dates
            accts.append(mk("a%03d" % i, last_seen_at=date(2024, 10, 13) - timedelta(days=i % 5)))
        r = plan_purge(accts, TODAY)
        self.assertEqual(len(r), 200)
        ids = [x["account_id"] for x in r]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(sum(i.startswith("z") for i in ids), 120)
        self.assertEqual(sum(i.startswith("a") for i in ids), 80)
        # top-200 differs from id-sorted first 200
        self.assertNotEqual(ids, sorted(a["id"] for a in accts)[:200])
        # earliest-due inactive kept: i%5==4 are earliest
        self.assertIn("a004", ids)

    def test_anonymise_not_counted_in_cap(self):
        accts = [mk("d%03d" % i, closed_at=date(2026, 9, 1)) for i in range(200)]
        accts += [mk("n%03d" % i, closed_at=date(2026, 9, 1), unpaid_invoices=1) for i in range(30)]
        r = plan_purge(accts, TODAY)
        self.assertEqual(sum(x["action"] == "delete" for x in r), 200)
        self.assertEqual(sum(x["action"] == "anonymise" for x in r), 30)

    def test_pure(self):
        accts = [mk("b", last_seen_at=date(2024, 10, 13), tenant="x"),
                 mk("a", last_seen_at=date(2024, 10, 20))]
        import copy
        snap = copy.deepcopy(accts)
        r1, r2 = plan_purge(accts, TODAY), plan_purge(accts, TODAY)
        self.assertEqual(r1, r2)
        self.assertEqual(accts, snap)
        for a in accts:
            a.pop("tenant", None)
        self.assertEqual(plan_purge(accts, TODAY), r1)
        self.assertEqual([x["account_id"] for x in r1], ["a", "b"])


if __name__ == "__main__":
    unittest.main()