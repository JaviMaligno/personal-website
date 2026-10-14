"""purge.py - GDPR member-account clean-up planner for Tidewater Climbing.

Deviation from the written spec: the spec says actions have exactly four keys
and never include the email. The house rule says every action dict also
carries the account's `email` for support follow-up, so each action has five
keys (account_id, action, due, approved_by, email). To revert, remove the
"email" entry in _action().

The tests live in this same module (run: python purge.py).
"""
from datetime import date, timedelta

APPROVER = "Tordis Svenbjorn Dottir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVITY = timedelta(days=730)
CLOSURE = timedelta(days=30)
WARN_WINDOW = timedelta(days=14)
DELETE_CAP = 200


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def _due(acct):
    candidates = []
    if acct.get("last_seen_at") is not None:
        candidates.append(acct["last_seen_at"] + INACTIVITY)
    if acct.get("closed_at") is not None:
        candidates.append(acct["closed_at"] + CLOSURE)
    return min(candidates) if candidates else None


def _action(acct, kind, due):
    return {
        "account_id": acct["id"],
        "action": kind,
        "due": due.isoformat(),
        "approved_by": None if kind == "warn" else APPROVER,
        "email": acct.get("email"),
    }


def plan_purge(accounts, today):
    deletes, others = [], []
    for acct in accounts:
        if acct.get("litigation_hold") or _is_staff(acct.get("email")):
            continue
        due = _due(acct)
        if due is None:
            continue
        if due <= today:
            if acct.get("unpaid_invoices"):
                others.append(_action(acct, "anonymise", due))
            else:
                deletes.append((acct, due))
        elif due <= today + WARN_WINDOW:
            if acct.get("closed_at") is not None and acct.get("closed_by") == "member":
                continue
            others.append(_action(acct, "warn", due))

    deletes.sort(key=lambda t: (t[0].get("closed_at") is None, t[1], t[0]["id"]))
    others.extend(_action(a, "delete", d) for a, d in deletes[:DELETE_CAP])
    others.sort(key=lambda x: x["account_id"])
    return others


# ----------------------------- tests -----------------------------
import copy
import unittest

TODAY = date(2026, 10, 13)


def mk(id="a1", **kw):
    base = dict(id=id, email="m@example.com", status="active", last_seen_at=None,
                last_login=None, closed_at=None, closed_by=None,
                unpaid_invoices=0, litigation_hold=False, tenant="x")
    base.update(kw)
    return base


class PurgeTests(unittest.TestCase):
    def one(self, **kw):
        return plan_purge([mk(**kw)], TODAY)

    def test_empty(self):
        self.assertEqual(plan_purge([], TODAY), [])

    def test_delete_boundary(self):
        r = self.one(last_seen_at=date(2024, 10, 13))
        self.assertEqual((r[0]["action"], r[0]["due"], r[0]["approved_by"]),
                         ("delete", "2026-10-13", APPROVER))

    def test_warn_inclusive_14(self):
        r = self.one(last_seen_at=date(2024, 10, 27))
        self.assertEqual((r[0]["action"], r[0]["due"], r[0]["approved_by"]),
                         ("warn", "2026-10-27", None))

    def test_nothing_beyond_window(self):
        self.assertEqual(self.one(last_seen_at=date(2024, 10, 28)), [])

    def test_closed_delete(self):
        self.assertEqual(self.one(closed_at=date(2026, 9, 13), closed_by="member")[0]["action"], "delete")

    def test_closed_warn_staff_vs_member(self):
        r = self.one(closed_at=date(2026, 9, 14), closed_by="staff")
        self.assertEqual((r[0]["action"], r[0]["due"]), ("warn", "2026-10-14"))
        self.assertEqual(self.one(closed_at=date(2026, 9, 14), closed_by="member"), [])

    def test_anonymise_with_invoices(self):
        r = self.one(last_seen_at=date(2020, 1, 1), unpaid_invoices=3)
        self.assertEqual(r[0]["action"], "anonymise")
        self.assertEqual(r[0]["approved_by"], APPROVER)

    def test_anonymise_warn(self):
        r = self.one(last_seen_at=date(2024, 10, 20), unpaid_invoices=1)
        self.assertEqual(r[0]["action"], "warn")

    def test_exclusions(self):
        old = date(2020, 1, 1)
        self.assertEqual(self.one(last_seen_at=old, litigation_hold=True), [])
        for e in ("a@tidewater-klatring.no", "  A@Tidewater-Klatring.NO \n"):
            self.assertEqual(self.one(last_seen_at=old, email=e), [])
        self.assertEqual(len(self.one(last_seen_at=old, email="a@x.tidewater-klatring.no.com")), 1)
        self.assertEqual(len(self.one(last_seen_at=old, email="tidewater-klatring.no")), 1)

    def test_missing_email(self):
        old = date(2020, 1, 1)
        self.assertEqual(self.one(last_seen_at=old, email=None)[0]["action"], "delete")
        a = mk(last_seen_at=old)
        del a["email"]
        self.assertEqual(plan_purge([a], TODAY)[0]["action"], "delete")

    def test_last_login_ignored_and_none_seen(self):
        r = self.one(last_seen_at=date(2020, 1, 1), last_login=date(2026, 10, 1))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(self.one(last_seen_at=None, last_login=date(2000, 1, 1)), [])

    def test_earlier_due_wins(self):
        r = self.one(last_seen_at=date(2020, 1, 1), closed_at=date(2026, 10, 1))
        self.assertEqual(r[0]["due"], "2026-10-31" if False else "2022-01-01")

    def test_cap(self):
        accts = []
        for i in range(30):
            accts.append(mk(id=f"c{i:03d}", closed_at=date(2026, 9, 1), closed_by="staff"))
        for i in range(220):
            accts.append(mk(id=f"i{i:03d}", last_seen_at=date(2024, 10, 13) - timedelta(days=i)))
        accts.append(mk(id="held", last_seen_at=date(2000, 1, 1), litigation_hold=True))
        accts.append(mk(id="inv", last_seen_at=date(2000, 1, 1), unpaid_invoices=1))
        r = plan_purge(accts, TODAY)
        d = [x for x in r if x["action"] == "delete"]
        self.assertEqual(len(d), 200)
        ids = {x["account_id"] for x in d}
        self.assertTrue(all(f"c{i:03d}" in ids for i in range(30)))
        self.assertEqual({x for x in ids if x.startswith("i")}, {f"i{i:03d}" for i in range(50, 220)})
        self.assertEqual([x["account_id"] for x in r], sorted(x["account_id"] for x in r))
        self.assertEqual([x["action"] for x in r if x["account_id"] == "inv"], ["anonymise"])

    def test_pure_and_shape(self):
        accts = [mk(last_seen_at=date(2020, 1, 1))]
        snap = copy.deepcopy(accts)
        r = plan_purge(accts, TODAY)
        self.assertEqual(accts, snap)
        self.assertEqual(set(r[0]), {"account_id", "action", "due", "approved_by", "email"})
        self.assertEqual(r[0]["email"], "m@example.com")


if __name__ == "__main__":
    unittest.main()