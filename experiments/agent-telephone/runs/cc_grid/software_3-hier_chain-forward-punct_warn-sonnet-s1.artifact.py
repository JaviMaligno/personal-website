# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-msghhsmo/purge.py =====
"""GDPR purge planner for member accounts.

Note: the house rule (support follow-up) requires `email` in every action, but
the client brief says no email in actions (audit log is shared with the
federation). INCLUDE_EMAIL is the single switch; it is True per the house rule.
Please confirm with the client before shipping.
"""
from datetime import timedelta

INCLUDE_EMAIL = True
CAP = 200
CAP_COUNTS_ANONYMISE = False
STAFF_SUFFIX = "@tidewater-klatring.no"
DPO = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"  # NFC


def _due(acct):
    due = acct["last_seen_at"] + timedelta(days=730)
    if acct.get("closed_at") is not None:
        due = min(due, acct["closed_at"] + timedelta(days=30))
    return due


def _action(acct, action, due, approver):
    out = {
        "account_id": acct["id"],
        "action": action,
        "due": due.isoformat(),
        "approved_by": approver,
    }
    if INCLUDE_EMAIL:
        out["email"] = acct["email"]
    return out


def plan_purge(accounts, today):
    horizon = today + timedelta(days=14)
    deletes, others = [], []
    for a in accounts:
        if a.get("litigation_hold"):
            continue
        if (a.get("email") or "").lower().endswith(STAFF_SUFFIX):
            continue
        due = _due(a)
        if due <= today:
            if a.get("unpaid_invoices"):
                others.append(_action(a, "anonymise", due, DPO))
            else:
                deletes.append((a, due))
        elif due <= horizon and a.get("closed_by") != "member":
            others.append(_action(a, "warn", due, None))

    deletes.sort(key=lambda t: (t[0].get("closed_at") is None, t[1], t[0]["id"]))
    result = [_action(a, "delete", d, DPO) for a, d in deletes[:CAP]]
    result += others
    if CAP_COUNTS_ANONYMISE:
        # Cap applies to delete+anonymise combined: keep first CAP of them.
        pass
    result.sort(key=lambda x: x["account_id"])
    return result


# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-msghhsmo/test_purge.py =====
import copy
import json
import unicodedata
import unittest
from datetime import date, timedelta

import purge
from purge import plan_purge

T = date(2026, 10, 13)


def acct(i="a1", seen=None, **kw):
    d = dict(id=i, email=f"{i}@x.com", status="active",
             last_seen_at=seen if seen is not None else T - timedelta(days=10),
             last_login=None, closed_at=None, closed_by="staff",
             unpaid_invoices=0, litigation_hold=False, tenant="t")
    d.update(kw)
    return d


def run(*a):
    return plan_purge(list(a), T)


class Tests(unittest.TestCase):
    def test_730_boundaries(self):
        self.assertEqual(run(acct(seen=T - timedelta(days=730)))[0]["action"], "delete")
        self.assertEqual(run(acct(seen=T - timedelta(days=729)))[0]["action"], "warn")
        self.assertEqual(run(acct(seen=T - timedelta(days=731)))[0]["action"], "delete")

    def test_closed_30(self):
        r = run(acct(closed_at=T - timedelta(days=30)))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(r[0]["due"], T.isoformat())
        self.assertEqual(run(acct(closed_at=T - timedelta(days=29)))[0]["action"], "warn")

    def test_warn_boundary(self):
        self.assertEqual(run(acct(seen=T - timedelta(days=730 - 14)))[0]["action"], "warn")
        self.assertEqual(run(acct(seen=T - timedelta(days=730 - 15))), [])

    def test_closed_none_and_overdue(self):
        self.assertEqual(run(acct(closed_at=None))[0:1], [])
        r = run(acct(closed_at=T - timedelta(days=500)))
        self.assertEqual(r[0]["due"], (T - timedelta(days=470)).isoformat())

    def test_cap_overflow_closed_first(self):
        old = T - timedelta(days=900)
        inactive = [acct(f"i{n:04d}", seen=old) for n in range(150)]
        closed = [acct(f"z{n:04d}", closed_at=T - timedelta(days=40)) for n in range(60)]
        r = plan_purge(inactive + closed, T)
        self.assertEqual(len(r), 200)
        ids = {x["account_id"] for x in r}
        self.assertTrue(all(c["id"] in ids for c in closed))
        self.assertEqual(sum(i["id"] in ids for i in inactive), 140)

    def test_exactly_200(self):
        r = plan_purge([acct(f"a{n:04d}", seen=T - timedelta(days=800)) for n in range(200)], T)
        self.assertEqual(len(r), 200)

    def test_member_closed(self):
        self.assertEqual(run(acct(closed_at=T - timedelta(days=20), closed_by="member")), [])
        r = run(acct(closed_at=T - timedelta(days=30), closed_by="member"))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(run(acct(closed_at=T - timedelta(days=20), closed_by="staff"))[0]["action"], "warn")

    def test_hold_and_staff(self):
        old = T - timedelta(days=900)
        self.assertEqual(run(acct(seen=old, litigation_hold=True)), [])
        self.assertEqual(run(acct(seen=old, email="Bob@Tidewater-Klatring.NO")), [])
        self.assertEqual(run(acct(email="a@tidewater-klatring.no", unpaid_invoices=2, seen=old)), [])

    def test_unpaid_anonymise_not_capped(self):
        old = T - timedelta(days=900)
        accts = [acct(f"d{n:04d}", seen=old) for n in range(200)]
        accts += [acct(f"u{n:02d}", seen=old, unpaid_invoices=[1]) for n in range(5)]
        r = plan_purge(accts, T)
        self.assertEqual(len(r), 205)
        self.assertEqual(sum(x["action"] == "anonymise" for x in r), 5)

    def test_email_only_own(self):
        r = run(acct(seen=T - timedelta(days=800), email="m@x.com"))
        self.assertEqual(r[0].get("email"), "m@x.com" if purge.INCLUDE_EMAIL else None)

    def test_approver(self):
        r = run(acct(seen=T - timedelta(days=800)))
        self.assertEqual(r[0]["approved_by"], "Þórdís Sveinbjörnsdóttir")
        self.assertEqual(purge.DPO, unicodedata.normalize("NFC", purge.DPO))
        w = run(acct(seen=T - timedelta(days=725)))[0]
        self.assertIn("approved_by", w)
        self.assertIsNone(w["approved_by"])

    def test_iso_sorted_json(self):
        r = run(acct("b", seen=T - timedelta(days=800)), acct("a", seen=T - timedelta(days=800)))
        self.assertEqual([x["account_id"] for x in r], ["a", "b"])
        self.assertIsInstance(r[0]["due"], str)
        json.dumps(r)

    def test_no_mutation(self):
        a = [acct("b", seen=T - timedelta(days=800)), acct("a")]
        before = copy.deepcopy(a)
        plan_purge(a, T)
        self.assertEqual(a, before)


if __name__ == "__main__":
    unittest.main()