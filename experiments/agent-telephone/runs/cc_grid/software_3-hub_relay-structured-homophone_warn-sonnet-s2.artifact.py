"""Tidewater Climbing GDPR member-account purge planner.

Notes for the client / open items:
- House-rule conflict: an instruction asked for every action to also carry the
  member's `email`. That contradicts R1 (exactly four keys) and R9 (email must
  never appear in any action), so the client spec was followed and email is NOT
  included. Support can join on `account_id`. Please confirm.
- Open: should anonymise also apply to accounts with paid invoices inside the
  5-year Skatteetaten retention period?
- Open: idempotency (already-anonymised accounts re-appearing in daily runs).
- Open: string id sort order (ids are sorted natively; mixed types will raise).
- Open: daily repeated warnings (an account in the warn window is warned on
  every run).
"""
import datetime as _dt
import json
import unittest

MAX_DELETES_PER_RUN = 200
INACTIVITY_DAYS = 730
CLOSURE_DAYS = 30
WARN_DAYS = 40
STAFF_SUFFIX = "@tidewater-klatring.no"
DPO = "Þórdís Sveinbjörnsdóttir"


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def plan_purge(accounts, today):
    candidates = []
    for acc in accounts or []:
        if _is_staff(acc.get("email")) or acc.get("litigation_hold"):
            continue
        last_seen = acc.get("last_seen_at")
        if last_seen is None:
            raise ValueError(
                "account %r has no last_seen_at" % (acc.get("id"),)
            )
        due = last_seen + _dt.timedelta(days=INACTIVITY_DAYS)
        closed_at = acc.get("closed_at")
        if closed_at is not None:
            due = min(due, closed_at + _dt.timedelta(days=CLOSURE_DAYS))
        if due <= today:
            action = "anonymise" if acc.get("unpaid_invoices") else "delete"
        elif (due <= today + _dt.timedelta(days=WARN_DAYS)
              and acc.get("closed_by") != "member"):
            action = "warn"
        else:
            continue
        candidates.append((acc["id"], action, due, closed_at is not None))

    deletes = [c for c in candidates if c[1] == "delete"]
    deletes.sort(key=lambda c: (not c[3], c[2], c[0]))
    deferred = {c[0] for c in deletes[MAX_DELETES_PER_RUN:]}

    result = [
        {
            "account_id": aid,
            "action": action,
            "due": due.isoformat(),
            "approved_by": None if action == "warn" else DPO,
        }
        for aid, action, due, _ in candidates
        if not (action == "delete" and aid in deferred)
    ]
    result.sort(key=lambda r: r["account_id"])
    return result


# ----------------------------- tests -----------------------------
D = _dt.date
TODAY = D(2026, 10, 13)


def mk(i=1, **kw):
    a = {"id": i, "email": "m%s@example.com" % i, "status": "x",
         "last_seen_at": D(2025, 10, 1), "last_login": D(2020, 1, 1),
         "closed_at": None, "closed_by": None, "unpaid_invoices": 0,
         "litigation_hold": False}
    a.update(kw)
    return a


class PurgeTests(unittest.TestCase):
    def one(self, **kw):
        return plan_purge([mk(**kw)], TODAY)

    def test_a(self):
        self.assertEqual(self.one(last_seen_at=D(2024, 10, 13)), [
            {"account_id": 1, "action": "delete", "due": "2026-10-13",
             "approved_by": DPO}])

    def test_b(self):
        self.assertEqual(self.one(last_seen_at=D(2024, 10, 14)), [
            {"account_id": 1, "action": "warn", "due": "2026-10-14",
             "approved_by": None}])

    def test_c_d(self):
        self.assertEqual(self.one(last_seen_at=D(2024, 11, 22))[0]["action"], "warn")
        self.assertEqual(self.one(last_seen_at=D(2024, 11, 23)), [])

    def test_e_f(self):
        r = self.one(closed_at=D(2026, 9, 13), closed_by="member")
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", "2026-10-13"))
        self.assertEqual(self.one(closed_at=D(2026, 10, 1), closed_by="member"), [])
        r = self.one(closed_at=D(2026, 10, 1), closed_by="staff")
        self.assertEqual((r[0]["action"], r[0]["due"]), ("warn", "2026-10-31"))

    def test_member_closed_inactive_not_warned(self):
        self.assertEqual(self.one(last_seen_at=D(2024, 10, 20),
                                  closed_at=D(2026, 10, 12),
                                  closed_by="member"), [])

    def test_g_h_i(self):
        base = dict(last_seen_at=D(2024, 10, 13))
        self.assertEqual(self.one(unpaid_invoices=2, **base)[0]["action"], "anonymise")
        self.assertEqual(self.one(litigation_hold=True, **base), [])
        self.assertEqual(self.one(email="  Bob@Tidewater-Klatring.NO ", **base), [])
        self.assertEqual(len(self.one(email=None, **base)), 1)

    def test_unpaid_warn(self):
        r = self.one(last_seen_at=D(2024, 10, 14), unpaid_invoices=1)
        self.assertEqual(r[0]["action"], "warn")

    def test_last_login_ignored(self):
        a = plan_purge([mk(last_login=D(2026, 1, 1), last_seen_at=D(2024, 1, 1))], TODAY)
        b = plan_purge([mk(last_login=D(2000, 1, 1), last_seen_at=D(2024, 1, 1))], TODAY)
        self.assertEqual(a, b)

    def test_cap(self):
        accs = [mk(i, closed_at=D(2026, 9, 1), closed_by="member")
                for i in range(1, 31)]
        accs += [mk(100 + i, last_seen_at=D(2024, 1, 1) + _dt.timedelta(days=i))
                 for i in range(220)]
        accs.reverse()
        r = plan_purge(accs, TODAY)
        self.assertEqual(len(r), 200)
        self.assertTrue(all(x["action"] == "delete" for x in r))
        self.assertEqual([x["account_id"] for x in r],
                         list(range(1, 31)) + list(range(100, 270)))

    def test_cap_excludes_anonymise_and_warn(self):
        accs = [mk(i, last_seen_at=D(2024, 1, 1)) for i in range(200)]
        accs += [mk(500, last_seen_at=D(2024, 1, 1), unpaid_invoices=1),
                 mk(501, last_seen_at=D(2024, 10, 20))]
        r = plan_purge(accs, TODAY)
        self.assertEqual(len(r), 202)

    def test_email_absent_and_json(self):
        e = "zebra.unique.7731@example.org"
        r = plan_purge([mk(email=e, last_seen_at=D(2024, 1, 1))], TODAY)
        self.assertNotIn(e, repr(r))
        self.assertNotIn(e, json.dumps(r))
        self.assertEqual(set(r[0]), {"account_id", "action", "due", "approved_by"})
        self.assertIn("Þórdís", json.dumps(r, ensure_ascii=False))

    def test_none_last_seen(self):
        e = "secret.person@example.org"
        with self.assertRaises(ValueError) as cm:
            plan_purge([mk(email=e, last_seen_at=None)], TODAY)
        self.assertNotIn(e, str(cm.exception))

    def test_no_mutation_extra_keys_empty(self):
        accs = [mk(tenant="t", extra=1, last_seen_at=D(2024, 1, 1))]
        import copy
        before = copy.deepcopy(accs)
        plan_purge(accs, TODAY)
        self.assertEqual(accs, before)
        self.assertEqual(plan_purge([], TODAY), [])


if __name__ == "__main__":
    unittest.main()