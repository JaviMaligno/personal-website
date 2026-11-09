# -*- coding: utf-8 -*-
"""Tidewater Klatring GDPR purge planner (standard library only).

Single file: planner plus unittest suite (run: python purge_planner.py).

Note for the client: the brief says "never include the email in any action",
but the house rule for this team says every action dict carries the account's
`email` so support can follow up. This module follows the house rule (key
`email` is added). To drop it, remove the "email" entry in _action().

Assumptions / questions:
 1. The 200 cap applies to delete actions only; anonymise is uncapped (question for client).
 2. warn has approved_by None.
 3. Cap selection by (closed first, earliest due, id), then output sorted by id.
    Ids may be int or str; mixed types are not supported.
 4. Accounts cut by the cap are deferred and not warned.
 5. Closed means closed_at is not None. last_seen_at None: closed rule only; else skipped.
 6. Missing/None email is treated as non-staff. Staff match is stripped, case-insensitive.
 7. One action per account; no filtering on status (values unknown).
"""
import datetime as dt
import json
import unittest

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
MAX_DELETES = 200
WARN_DAYS = 14


def _action(a, action, due):
    return {
        "account_id": a["id"],
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else APPROVER,
        "email": a.get("email"),
    }


def plan_purge(accounts, today):
    deletes, others = [], []
    for a in accounts:
        email = (a.get("email") or "").strip().lower()
        if email.endswith(STAFF_DOMAIN) or a.get("litigation_hold"):
            continue
        seen, closed = a.get("last_seen_at"), a.get("closed_at")
        dues = []
        if seen is not None:
            dues.append(seen + dt.timedelta(days=730))
        if closed is not None:
            dues.append(closed + dt.timedelta(days=30))
        if not dues:
            continue
        due = min(dues)
        if due <= today:
            if a.get("unpaid_invoices"):
                others.append(_action(a, "anonymise", due))
            else:
                deletes.append((closed is None, due, a["id"], _action(a, "delete", due)))
        elif due <= today + dt.timedelta(days=WARN_DAYS):
            if closed is not None and a.get("closed_by") == "member":
                continue
            others.append(_action(a, "warn", due))
    deletes.sort(key=lambda t: t[:3])
    out = others + [t[3] for t in deletes[:MAX_DELETES]]
    return sorted(out, key=lambda x: x["account_id"])


# ----------------------------- tests -----------------------------
TODAY = dt.date(2026, 10, 13)
D = dt.timedelta


def acct(i=1, seen=None, **kw):
    base = dict(id=i, email="m%s@example.com" % i, status="active",
                last_seen_at=seen, last_login=TODAY, closed_at=None,
                closed_by="member", unpaid_invoices=0, litigation_hold=False,
                tenant="x")
    base.update(kw)
    return base


class PlanTests(unittest.TestCase):
    def one(self, **kw):
        return plan_purge([acct(**kw)], TODAY)

    def test_boundaries(self):
        r = self.one(seen=TODAY - D(days=730))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(r[0]["due"], "2026-10-13")
        self.assertEqual(self.one(seen=TODAY - D(days=729))[0]["action"], "warn")
        self.assertEqual(self.one(seen=TODAY - D(days=716))[0]["action"], "warn")
        self.assertEqual(self.one(seen=TODAY - D(days=715)), [])

    def test_last_login_ignored(self):
        self.assertEqual(self.one(seen=TODAY - D(days=100), last_login=TODAY - D(days=900)), [])

    def test_closed_min(self):
        r = self.one(seen=TODAY, closed_at=TODAY - D(days=30))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", "2026-10-13"))

    def test_member_vs_staff_closed_warn(self):
        kw = dict(seen=TODAY, closed_at=TODAY - D(days=20))
        self.assertEqual(self.one(closed_by="member", **kw), [])
        self.assertEqual(self.one(closed_by="staff", **kw)[0]["action"], "warn")

    def test_unpaid_anonymise_uncapped(self):
        old = TODAY - D(days=800)
        accts = [acct(i, old, unpaid_invoices=[1]) for i in range(250)]
        r = plan_purge(accts, TODAY)
        self.assertEqual(len(r), 250)
        self.assertTrue(all(x["action"] == "anonymise" for x in r))
        self.assertEqual(self.one(seen=TODAY - D(days=725), unpaid_invoices=2)[0]["action"], "warn")

    def test_hold_and_staff(self):
        old = TODAY - D(days=800)
        self.assertEqual(self.one(seen=old, litigation_hold=True), [])
        self.assertEqual(self.one(seen=old, email="  A@Tidewater-Klatring.NO "), [])

    def test_missing_email(self):
        old = TODAY - D(days=800)
        self.assertEqual(len(self.one(seen=old, email=None)), 1)

    def test_email_is_house_rule_field(self):
        r = self.one(seen=TODAY - D(days=800))
        self.assertEqual(r[0]["email"], "m1@example.com")
        self.assertEqual(set(r[0]), {"account_id", "action", "due", "approved_by", "email"})

    def test_cap_priority_and_cut_not_warned(self):
        old = TODAY - D(days=800)
        accts = [acct(i, old) for i in range(1, 201)]
        accts.append(acct(500, old - D(days=50)))                      # open, earliest due
        accts.append(acct(900, old, closed_at=TODAY - D(days=40)))      # closed
        r = plan_purge(accts, TODAY)
        ids = [x["account_id"] for x in r]
        self.assertEqual(len(r), 200)
        self.assertIn(900, ids)
        self.assertIn(500, ids)
        self.assertNotIn(200, ids)   # latest id among ties is cut
        self.assertNotIn(199, [i for i in range(0)])  # no warn entries for cut
        self.assertTrue(all(x["action"] == "delete" for x in r))
        self.assertEqual(ids, sorted(ids))

    def test_approvers(self):
        r = plan_purge([acct(1, TODAY - D(days=800)), acct(2, TODAY - D(days=725))], TODAY)
        self.assertEqual(r[0]["approved_by"], "Þórdís Sveinbjörnsdóttir")
        self.assertIsNone(r[1]["approved_by"])

    def test_no_mutation(self):
        import copy
        accts = [acct(2, TODAY - D(days=800)), acct(1, TODAY - D(days=725))]
        before = copy.deepcopy(accts)
        plan_purge(accts, TODAY)
        self.assertEqual(accts, before)

    def test_seen_none(self):
        self.assertEqual(self.one(seen=None), [])
        r = self.one(seen=None, closed_at=TODAY - D(days=30))
        self.assertEqual(r[0]["action"], "delete")

    def test_json(self):
        r = self.one(seen=TODAY - D(days=800))
        self.assertIsInstance(r[0]["due"], str)
        self.assertIn("Þórdís", json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()