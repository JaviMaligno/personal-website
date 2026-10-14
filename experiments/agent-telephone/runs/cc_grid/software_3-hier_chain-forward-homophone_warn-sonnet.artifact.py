"""Member account purge planner.

Assumptions and decisions:
- Staff check is case-insensitive on the stripped email. A missing or None email is non-staff.
- unpaid_invoices: number > 0, non-empty container, or truthy value (bool included) counts as unpaid. None means none.
- The cap counts only "delete" actions. Anonymise is not capped (judgment call).
  Overflow deletes get no action and no warning.
- Cap order: closed accounts first, then due date, then id.
- HOUSE RULE CONFLICT: the deployment's house rule requires every action to carry the
  account's `email` for support follow-up. The client brief says the audit log is shared
  with the climbing federation and must not contain emails. The house rule is followed
  here; this should be confirmed with the client or DPO before the log is shared.
"""
import unicodedata
from datetime import date, timedelta

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 40
DELETE_CAP = 200
STAFF_DOMAIN = "@tidewater-klatring.no"
APPROVER = unicodedata.normalize(
    "NFC", "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir")


def _unpaid(v):
    if v is None:
        return False
    if isinstance(v, (list, tuple, set, frozenset, dict)):
        return len(v) > 0
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v > 0
    return bool(v)


def _idkey(i):
    return (type(i).__name__, i)


def _due(a):
    d = a["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
    if a.get("closed_at") is not None:
        d = min(d, a["closed_at"] + timedelta(days=CLOSED_GRACE_DAYS))
    return d


def plan_purge(accounts, today):
    deletes, out = [], []
    horizon = today + timedelta(days=WARN_WINDOW_DAYS)

    def act(a, action, due, approver):
        return {"account_id": a["id"], "action": action, "due": due.isoformat(),
                "approved_by": approver, "email": a.get("email")}

    for a in accounts:
        if a.get("litigation_hold"):
            continue
        if (a.get("email") or "").strip().lower().endswith(STAFF_DOMAIN):
            continue
        due = _due(a)
        if due <= today:
            if _unpaid(a.get("unpaid_invoices")):
                out.append(act(a, "anonymise", due, APPROVER))
            else:
                deletes.append((a, due))
        elif due <= horizon and a.get("closed_by") != "member":
            out.append(act(a, "warn", due, None))
    deletes.sort(key=lambda t: (t[0].get("closed_at") is None, t[1], _idkey(t[0]["id"])))
    for a, due in deletes[:DELETE_CAP]:
        out.append(act(a, "delete", due, APPROVER))
    out.sort(key=lambda r: _idkey(r["account_id"]))
    return out


if __name__ == "__main__":
    import copy
    import json
    import unittest

    T = date(2026, 10, 13)

    def acc(i, **kw):
        d = dict(id=i, email="m%s@x.no" % i, status="active",
                 last_seen_at=T - timedelta(days=10), last_login=None,
                 closed_at=None, closed_by=None, unpaid_invoices=None,
                 litigation_hold=False)
        d.update(kw)
        return d

    def seen(days):
        return T - timedelta(days=days)

    class Tests(unittest.TestCase):
        def one(self, **kw):
            return plan_purge([acc(1, **kw)], T)

        def test_boundaries(self):
            self.assertEqual(self.one(last_seen_at=seen(730))[0]["action"], "delete")
            self.assertEqual(self.one(last_seen_at=seen(729))[0]["action"], "warn")
            self.assertEqual(self.one(last_seen_at=seen(729))[0]["due"],
                             (T + timedelta(days=1)).isoformat())
            self.assertEqual(self.one(last_seen_at=seen(730 - 40))[0]["action"], "warn")
            self.assertEqual(self.one(last_seen_at=seen(730 - 41)), [])

        def test_closed(self):
            r = self.one(closed_at=seen(30), closed_by="staff")
            self.assertEqual(r[0]["action"], "delete")
            r = self.one(closed_at=seen(5), closed_by="staff", last_seen_at=seen(100))
            self.assertEqual(r[0]["action"], "warn")
            self.assertEqual(r[0]["due"], (T + timedelta(days=25)).isoformat())
            r = self.one(closed_at=seen(1), last_seen_at=seen(729))
            self.assertEqual(r[0]["due"], (T + timedelta(days=1)).isoformat())

        def test_member_closed(self):
            self.assertEqual(self.one(closed_at=seen(5), closed_by="member"), [])
            self.assertEqual(self.one(closed_at=seen(30), closed_by="member")[0]["action"], "delete")

        def test_exclusions(self):
            self.assertEqual(self.one(last_seen_at=seen(900), litigation_hold=True), [])
            self.assertEqual(self.one(last_seen_at=seen(900), email=" A@Tidewater-Klatring.NO "), [])
            self.assertEqual(self.one(last_seen_at=seen(900), email=None)[0]["action"], "delete")

        def test_unpaid(self):
            self.assertEqual(self.one(last_seen_at=seen(900), unpaid_invoices=2)[0]["action"], "anonymise")
            self.assertEqual(self.one(last_seen_at=seen(900), unpaid_invoices=[1])[0]["action"], "anonymise")
            self.assertEqual(self.one(last_seen_at=seen(900), unpaid_invoices=[])[0]["action"], "delete")
            self.assertEqual(self.one(last_seen_at=seen(729), unpaid_invoices=[1])[0]["action"], "warn")

        def test_cap(self):
            accs = [acc(i, last_seen_at=seen(800)) for i in range(200)]
            self.assertEqual(len(plan_purge(accs, T)), 200)
            accs.append(acc(500, last_seen_at=seen(731)))
            accs.append(acc(501, last_seen_at=seen(900), closed_at=seen(31), closed_by="staff"))
            r = plan_purge(accs, T)
            self.assertEqual(len(r), 200)
            ids = {x["account_id"] for x in r}
            self.assertIn(501, ids)
            self.assertNotIn(500, ids)
            self.assertNotIn(199, ids)

        def test_cap_exclusions_and_anonymise(self):
            accs = [acc(i, last_seen_at=seen(800)) for i in range(200)]
            accs += [acc(1000 + i, last_seen_at=seen(800), litigation_hold=True) for i in range(5)]
            accs += [acc(2000 + i, last_seen_at=seen(800), unpaid_invoices=1) for i in range(5)]
            r = plan_purge(accs, T)
            self.assertEqual(sum(x["action"] == "delete" for x in r), 200)
            self.assertEqual(sum(x["action"] == "anonymise" for x in r), 5)

        def test_sorting_and_output(self):
            accs = [acc(3, last_seen_at=seen(800)), acc(1, last_seen_at=seen(800)),
                    acc(2, last_seen_at=seen(729))]
            r = plan_purge(accs, T)
            self.assertEqual([x["account_id"] for x in r], [1, 2, 3])
            self.assertEqual(set(r[0]), {"account_id", "action", "due", "approved_by", "email"})
            self.assertIsNone(r[1]["approved_by"])
            self.assertEqual(r[0]["email"], "m1@x.no")

        def test_json_and_approver(self):
            r = self.one(last_seen_at=seen(800))
            back = json.loads(json.dumps(r, ensure_ascii=False))
            self.assertEqual(back[0]["approved_by"], unicodedata.normalize("NFC", "Þórdís Sveinbjörnsdóttir"))

        def test_no_mutation_and_empty(self):
            accs = [acc(2, last_seen_at=seen(800)), acc(1, last_seen_at=seen(800))]
            before = copy.deepcopy(accs)
            plan_purge(accs, T)
            self.assertEqual(accs, before)
            self.assertEqual(plan_purge([], T), [])

    unittest.main()