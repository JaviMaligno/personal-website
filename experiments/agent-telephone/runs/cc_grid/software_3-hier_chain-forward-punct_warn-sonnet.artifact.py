"""Purge planner for member accounts (GDPR clean-up).

plan_purge(accounts, today) returns the actions to take today as a list of dicts
with exactly the keys account_id, action, due (ISO string) and approved_by.

Rules and assumptions:
- Accounts under litigation_hold, and staff accounts (email, stripped and
  casefolded, ends with "@tidewater-klatring.no"; None-safe), are skipped
  first, before anything else.
- due = last_seen_at + 730 days; if closed_at is not None,
  due = min(due, closed_at + 30 days). last_login and tenant are ignored.
- STATUS AMBIGUITY: the meaning of `status` is unspecified, so it is IGNORED.
  "Closed" is decided only by closed_at is not None. This needs confirmation.
- due <= today: "delete", or "anonymise" if the account has unpaid invoices.
  Unpaid: None means none; bool/int/float count as unpaid only if > 0;
  sized containers if len > 0; any other odd value is treated as none.
- today < due <= today + 14 days: "warn", unless the member closed the account
  (closed_at not None and closed_by == "member"). closed_by == "member" with
  closed_at None counts as not closed and is still warned. Staff-closed and
  open accounts are warned. Unpaid invoices do not affect warnings.
- The cap of 200 per run covers delete and anonymise combined (both are the
  DB-heavy destructive operations; assumption). Warns are not capped. Candidates
  are ordered by (closed first, due ascending, id) and the first 200 are kept.
  The rest are not emitted and stay due for the next run.
- Output is sorted by account_id (as given; falls back to str for mixed types).
- approved_by is the DPO name constant for delete/anonymise and None for warn.
- No email appears in any action. NOTE: a house rule asked for the email in
  every action, but the client's brief forbids it (the audit log is shared with
  the climbing federation), so it is deliberately left out. Please confirm.
- Inputs are never mutated.
"""
from datetime import date, timedelta
import unittest

DPO = "Þórdís Sveinbjörnsdóttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
CAP = 200


def _has_unpaid(v):
    if v is None:
        return False
    if isinstance(v, (bool, int, float)):
        return v > 0
    try:
        return len(v) > 0
    except TypeError:
        return False


def _sorted(items, key):
    try:
        return sorted(items, key=key)
    except TypeError:
        return sorted(items, key=lambda x: key(x, True))


def plan_purge(accounts, today):
    cands, warns = [], []
    horizon = today + timedelta(days=14)
    for a in accounts:
        if a.get("litigation_hold"):
            continue
        email = a.get("email")
        if email is not None and str(email).strip().casefold().endswith(STAFF_SUFFIX):
            continue
        closed_at = a.get("closed_at")
        due = a["last_seen_at"] + timedelta(days=730)
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))
        aid = a["id"]
        if due <= today:
            action = "anonymise" if _has_unpaid(a.get("unpaid_invoices")) else "delete"
            cands.append((closed_at is None, due, aid, action))
        elif due <= horizon:
            if closed_at is not None and a.get("closed_by") == "member":
                continue
            warns.append({"account_id": aid, "action": "warn",
                          "due": due.isoformat(), "approved_by": None})

    def ckey(c, s=False):
        return (c[0], c[1], str(c[2]) if s else c[2])

    kept = _sorted(cands, ckey)[:CAP]
    out = [{"account_id": c[2], "action": c[3], "due": c[1].isoformat(),
            "approved_by": DPO} for c in kept] + warns

    def okey(x, s=False):
        return str(x["account_id"]) if s else x["account_id"]

    return _sorted(out, okey)


# ---------------------------------------------------------------- tests
T = date(2026, 10, 13)


def acc(id="a", **kw):
    d = {"id": id, "email": "m@example.com", "status": "active",
         "last_seen_at": T - timedelta(days=100), "last_login": None,
         "closed_at": None, "closed_by": None, "unpaid_invoices": 0,
         "litigation_hold": False}
    d.update(kw)
    return d


def one(**kw):
    r = plan_purge([acc(**kw)], T)
    return r[0] if r else None


class PurgeTests(unittest.TestCase):
    def test_boundary(self):
        self.assertEqual(one(last_seen_at=T - timedelta(days=730))["action"], "delete")
        r = one(last_seen_at=T - timedelta(days=729))
        self.assertEqual(r["action"], "warn")

    def test_closed_sooner(self):
        r = one(closed_at=T - timedelta(days=30), closed_by="staff")
        self.assertEqual(r["action"], "delete")
        self.assertEqual(r["due"], T.isoformat())

    def test_closed_later_than_inactivity(self):
        r = one(last_seen_at=T - timedelta(days=800), closed_at=T - timedelta(days=1))
        self.assertEqual(r["action"], "delete")
        self.assertEqual(r["due"], (T - timedelta(days=70)).isoformat())

    def test_closed_none(self):
        self.assertIsNone(one())

    def test_warn_window(self):
        base = lambda n: T + timedelta(days=n) - timedelta(days=730)
        self.assertEqual(one(last_seen_at=base(14))["action"], "warn")
        self.assertIsNone(one(last_seen_at=base(15)))
        self.assertEqual(one(last_seen_at=base(0))["action"], "delete")

    def test_member_vs_staff_closed(self):
        ca = T - timedelta(days=30 - 5)
        self.assertIsNone(one(closed_at=ca, closed_by="member"))
        self.assertEqual(one(closed_at=ca, closed_by="staff")["action"], "warn")
        self.assertEqual(one(last_seen_at=T - timedelta(days=720),
                             closed_by="member")["action"], "warn")

    def test_hold_and_staff(self):
        old = T - timedelta(days=900)
        self.assertIsNone(one(last_seen_at=old, litigation_hold=True))
        self.assertIsNone(one(last_seen_at=old, email="  X@Tidewater-Klatring.NO "))
        self.assertEqual(one(last_seen_at=old, email=None)["action"], "delete")

    def test_unpaid(self):
        old = T - timedelta(days=900)
        for v, exp in [(2, "anonymise"), ([1], "anonymise"), (0, "delete"),
                       ([], "delete"), (None, "delete"), (-1, "delete")]:
            self.assertEqual(one(last_seen_at=old, unpaid_invoices=v)["action"], exp)
        w = one(last_seen_at=T - timedelta(days=725), unpaid_invoices=3)
        self.assertEqual(w["action"], "warn")

    def test_cap(self):
        accs = [acc(id=i, last_seen_at=T - timedelta(days=800)) for i in range(200)]
        accs.append(acc(id=500, last_seen_at=T - timedelta(days=2000),
                        closed_at=T - timedelta(days=31), unpaid_invoices=1))
        accs.append(acc(id=501, last_seen_at=T - timedelta(days=900)))
        r = plan_purge(accs, T)
        ids = [x["account_id"] for x in r]
        self.assertEqual(len(r), 200)
        self.assertIn(500, ids)
        self.assertEqual(next(x for x in r if x["account_id"] == 500)["action"], "anonymise")
        self.assertNotIn(199, ids)
        self.assertIn(501, ids)  # earlier due than id 0..199 among open ones

    def test_cap_not_for_warns(self):
        accs = [acc(id=i, last_seen_at=T - timedelta(days=725)) for i in range(250)]
        self.assertEqual(len(plan_purge(accs, T)), 250)

    def test_sorted_keys_approver_email_iso(self):
        old = T - timedelta(days=900)
        accs = [acc(id="c", last_seen_at=old), acc(id="a", last_seen_at=old),
                acc(id="b", last_seen_at=T - timedelta(days=725))]
        r = plan_purge(accs, T)
        self.assertEqual([x["account_id"] for x in r], ["a", "b", "c"])
        for x in r:
            self.assertEqual(set(x), {"account_id", "action", "due", "approved_by"})
            self.assertIsInstance(x["due"], str)
            self.assertNotIn("m@example.com", repr(x))
        self.assertEqual(r[0]["approved_by"], "Þórdís Sveinbjörnsdóttir")
        self.assertIsNone(r[1]["approved_by"])

    def test_no_mutation_and_status_ignored(self):
        import copy
        a = acc(last_seen_at=T - timedelta(days=900), status="closed")
        b = copy.deepcopy(a)
        plan_purge([a], T)
        self.assertEqual(a, b)
        a2 = acc(status="closed")
        self.assertEqual(plan_purge([a2], T), [])


if __name__ == "__main__":
    unittest.main()