"""purge.py - GDPR purge planner for Tidewater Climbing member accounts.

Entry point: plan_purge(accounts, today).

NOTE FOR TECH LEAD (conflict flagged, not silently resolved): a house rule given to
me says every action dict should also carry the account's `email`. The brief, the
architect's note and the audit-log requirement (log shared with the climbing
federation) all say NO email in any action. I followed the brief and left email out
(action keys are exactly account_id, action, due, approved_by). Adding it would leak
personal data to a third party; it needs an explicit decision from the client.
I had no tools, so the tests below were NOT run by me. Run: python -m unittest purge

Ambiguities and decisions:
1. Unpaid-invoice type unknown: bool -> itself, number -> >0, list/tuple/set -> non-empty, None -> False.
2. Terminal statuses "anonymised", "anonymized", "deleted" (case-insensitive) are skipped (assumption).
3. last_seen_at None: due = closed_at+30d if closed, else skipped (undeterminable).
4. Day 14 is inclusive for warnings (today < due <= today+14).
5. Anonymise-due accounts also get warnings (member still gets notice).
6. closed_at in the future is still computed by the formula.
7. The 200 cap counts delete and anonymise together. Order: closed first, due asc, id.
   Deferred accounts are not emitted and get no warning (already overdue). Warns uncapped.
8. 5-year invoice retention is not enforced here; purging invoices later is out of scope.
   An anonymise-due account whose status is not updated is re-emitted every run.
9. Mixed-type ids sort by (type name, value).
10. Unknown closed_by with closed_at set is treated as staff (warn).
"""
from datetime import date, timedelta
import unittest, json, copy

MAX_DELETIONS_PER_RUN = 200
APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
TERMINAL = {"anonymised", "anonymized", "deleted"}


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def _due(acct):
    cands = []
    if acct.get("last_seen_at") is not None:
        cands.append(acct["last_seen_at"] + timedelta(days=730))
    if acct.get("closed_at") is not None:
        cands.append(acct["closed_at"] + timedelta(days=30))
    return min(cands) if cands else None


def _has_unpaid(v):
    """Type unknown: accepts bool, number (>0), list/tuple/set (non-empty); None -> False."""
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v > 0
    if isinstance(v, (list, tuple, set)):
        return len(v) > 0
    return bool(v)


def _idkey(i):
    return (type(i).__name__, i if isinstance(i, (int, str, float)) else str(i))


def plan_purge(accounts, today):
    due_items, warns = [], []
    for a in accounts:
        if a.get("litigation_hold") or _is_staff(a.get("email")):
            continue
        st = a.get("status")
        if isinstance(st, str) and st.strip().lower() in TERMINAL:
            continue
        due = _due(a)
        if due is None:
            continue
        if due <= today:
            act = "anonymise" if _has_unpaid(a.get("unpaid_invoices")) else "delete"
            due_items.append((a.get("closed_at") is None, due, _idkey(a["id"]), a["id"], act))
        elif due <= today + timedelta(days=14):
            if a.get("closed_at") is not None and a.get("closed_by") == "member":
                continue
            warns.append((a["id"], "warn", due, None))
    due_items.sort(key=lambda t: t[:3])
    out = [{"account_id": i, "action": act, "due": d.isoformat(), "approved_by": APPROVER}
           for _, d, _, i, act in due_items[:MAX_DELETIONS_PER_RUN]]
    out += [{"account_id": i, "action": w, "due": d.isoformat(), "approved_by": None}
            for i, w, d, _ in warns]
    out.sort(key=lambda x: _idkey(x["account_id"]))
    return out


# ---------------------------------------------------------------- tests
T = date(2026, 10, 13)


def acc(i=1, **kw):
    d = dict(id=i, email=f"u{i}@x.com", status="active", last_seen_at=T - timedelta(days=100),
             last_login=None, closed_at=None, closed_by=None, unpaid_invoices=0,
             litigation_hold=False, tenant="t")
    d.update(kw)
    return d


def seen(days_until_due):
    return T + timedelta(days=days_until_due - 730)


class PurgeTests(unittest.TestCase):
    def test_precedence(self):
        old = T - timedelta(days=800)
        a = acc(1, last_seen_at=old, litigation_hold=True, email="a@tidewater-klatring.no", unpaid_invoices=2)
        b = acc(2, last_seen_at=old, email="  B@Tidewater-Klatring.NO ", unpaid_invoices=2)
        c = acc(3, last_seen_at=old, unpaid_invoices=2)
        r = plan_purge([a, b, c], T)
        self.assertEqual([(x["account_id"], x["action"]) for x in r], [(3, "anonymise")])

    def test_last_login_and_tenant_ignored(self):
        a = acc(1, last_seen_at=T, last_login=T - timedelta(days=5000), tenant="zzz")
        self.assertEqual(plan_purge([a], T), [])

    def test_boundaries(self):
        accs = [acc(i, last_seen_at=seen(d)) for i, d in enumerate([0, 14, 15, -1], 1)]
        r = {x["account_id"]: x for x in plan_purge(accs, T)}
        self.assertEqual(r[1]["action"], "delete")
        self.assertEqual(r[2]["action"], "warn")
        self.assertNotIn(3, r)
        self.assertEqual(r[4]["action"], "delete")
        self.assertIsNone(r[2]["approved_by"])

    def test_closed_sooner_and_member_no_warn(self):
        a = acc(1, closed_at=T - timedelta(days=30), closed_by="staff")
        self.assertEqual(plan_purge([a], T)[0]["action"], "delete")
        w = acc(2, closed_at=T - timedelta(days=20), closed_by="staff")
        m = acc(3, closed_at=T - timedelta(days=20), closed_by="member")
        self.assertEqual([x["account_id"] for x in plan_purge([w, m], T)], [2])

    def test_cap_closed_first_and_anonymise_counts(self):
        inactive = [acc(i, last_seen_at=T - timedelta(days=900 + i)) for i in range(1, 201)]
        inactive[0]["unpaid_invoices"] = 1
        closed = [acc(1000 + i, closed_at=T - timedelta(days=60)) for i in range(5)]
        r = plan_purge(inactive + closed, T)
        self.assertEqual(len(r), MAX_DELETIONS_PER_RUN)
        ids = {x["account_id"] for x in r}
        self.assertTrue(all(1000 + i in ids for i in range(5)))
        self.assertEqual(sum(1 for x in r if x["action"] == "anonymise"), 0 if 1 not in ids else 1)

    def test_determinism_sorted_no_email_unicode_immutable(self):
        accs = [acc(i, last_seen_at=T - timedelta(days=800)) for i in (3, 1, 2)]
        accs.append(acc("b", last_seen_at=T - timedelta(days=800)))
        snap = copy.deepcopy(accs)
        r1, r2 = plan_purge(accs, T), plan_purge(list(reversed(accs)), T)
        self.assertEqual(r1, r2)
        self.assertEqual(accs, snap)
        self.assertEqual([x["account_id"] for x in r1], [1, 2, 3, "b"])
        s = json.dumps(r1, ensure_ascii=False)
        self.assertNotIn("@", s)
        self.assertEqual(r1[0]["approved_by"], "Þórdís Sveinbjörnsdóttir")
        self.assertEqual(set(r1[0]), {"account_id", "action", "due", "approved_by"})

    def test_none_last_seen(self):
        a = acc(1, last_seen_at=None)
        b = acc(2, last_seen_at=None, closed_at=T - timedelta(days=31))
        self.assertEqual([x["account_id"] for x in plan_purge([a, b], T)], [2])

    def test_terminal_status(self):
        a = acc(1, last_seen_at=T - timedelta(days=900), status="Anonymised")
        self.assertEqual(plan_purge([a], T), [])


if __name__ == "__main__":
    unittest.main()