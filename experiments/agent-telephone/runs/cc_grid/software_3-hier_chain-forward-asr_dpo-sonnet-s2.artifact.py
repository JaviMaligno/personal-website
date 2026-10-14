"""Member account purge planner for Tidewater Climbing (GDPR clean-up).

Entry point: plan_purge(accounts, today) -> list of action dicts.
Run the embedded tests with: python purge.py

CONFLICT FLAGGED (needs a human decision):
  The client brief and the architect note say actions must NOT contain the member's
  email (the audit log is shared with the climbing federation). A house rule says every
  action dict must carry `email` for support follow-up. The house rule is followed here,
  so INCLUDE_EMAIL = True. Set it to False to get the key set
  {account_id, action, due, approved_by} with no personal data.

Decisions and assumptions:
  - Staff: email.strip().lower().endswith("@tidewater-klatring.no"); missing email is not staff.
  - litigation_hold truthy -> no action at all. Staff and held accounts are excluded
    before any date logic, so bad data on them never raises.
  - due = last_seen_at + 730 days; if closed_at is set, due = min(due, closed_at + 30 days).
    last_login is never used. `status` and `tenant` are ignored (flagged).
  - Missing/None last_seen_at: ValueError naming the account id, unless closed_at is set,
    in which case due = closed_at + 30 days (flagged fallback).
  - due <= today -> "anonymise" if unpaid_invoices is truthy (count or non-empty list),
    else "delete".
  - today < due <= today + 14 -> "warn", except when closed_at is set and closed_by == "member".
    Accounts with unpaid invoices that are not yet due are still warned (flagged).
  - Cap: at most 200 deletes. Anonymise does not count and is never cut (flagged). Overflow
    deletes keep closed accounts first, then inactive, each ordered by (due, account_id);
    the deferred ones are omitted. Warnings are uncapped.
  - Final output is sorted by account id after capping. Sort key is
    (type name, id), safe for mixed id types (ints sort numerically among ints,
    strings among strings, groups ordered by type name).
  - Only datetime.date is supported; timedelta arithmetic handles leap years.
  - Input is not mutated.
"""
from datetime import date, timedelta
import unittest

INCLUDE_EMAIL = True
STAFF_SUFFIX = "@tidewater-klatring.no"
APPROVER = "Tordis Svenbjorn Dottir"
INACTIVITY = timedelta(days=730)
CLOSED_GRACE = timedelta(days=30)
WARN_WINDOW = timedelta(days=14)
MAX_DELETES = 200


def _idkey(account_id):
    return (type(account_id).__name__, account_id)


def _is_staff(acct):
    email = acct.get("email")
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def _due(acct):
    closed_at = acct.get("closed_at")
    seen = acct.get("last_seen_at")
    if seen is None:
        if closed_at is None:
            raise ValueError(f"account {acct.get('id')!r}: missing last_seen_at")
        return closed_at + CLOSED_GRACE
    due = seen + INACTIVITY
    if closed_at is not None:
        due = min(due, closed_at + CLOSED_GRACE)
    return due


def _action(acct, action, due):
    out = {
        "account_id": acct["id"],
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else APPROVER,
    }
    if INCLUDE_EMAIL:
        out["email"] = acct.get("email")
    return out


def plan_purge(accounts, today):
    deletes, others = [], []
    for acct in accounts:
        if acct.get("litigation_hold") or _is_staff(acct):
            continue
        due = _due(acct)
        closed = acct.get("closed_at") is not None
        if due <= today:
            if acct.get("unpaid_invoices"):
                others.append(_action(acct, "anonymise", due))
            else:
                deletes.append((0 if closed else 1, due, _idkey(acct["id"]),
                                _action(acct, "delete", due)))
        elif due <= today + WARN_WINDOW:
            if closed and acct.get("closed_by") == "member":
                continue
            others.append(_action(acct, "warn", due))
    deletes.sort(key=lambda t: t[:3])
    kept = [t[3] for t in deletes[:MAX_DELETES]]
    result = kept + others
    result.sort(key=lambda a: _idkey(a["account_id"]))
    return result


# ---------------------------------------------------------------- tests
TODAY = date(2026, 10, 13)


def mk(i, **kw):
    base = dict(id=i, email=f"m{i}@example.com", status="active",
                last_seen_at=TODAY, last_login=None, closed_at=None,
                closed_by=None, unpaid_invoices=0, litigation_hold=False)
    base.update(kw)
    return base


def seen_for_due(d):
    return d - INACTIVITY


class PurgeTests(unittest.TestCase):
    def one(self, **kw):
        return plan_purge([mk(1, **kw)], TODAY)

    def test_due_today_deletes(self):
        r = self.one(last_seen_at=seen_for_due(TODAY))
        self.assertEqual([(a["action"], a["due"]) for a in r], [("delete", TODAY.isoformat())])
        self.assertEqual(r[0]["approved_by"], APPROVER)

    def test_due_tomorrow_warns_and_boundaries(self):
        r = self.one(last_seen_at=seen_for_due(TODAY + timedelta(days=14)))
        self.assertEqual(r[0]["action"], "warn")
        self.assertIsNone(r[0]["approved_by"])
        self.assertEqual(self.one(last_seen_at=seen_for_due(TODAY + timedelta(days=15))), [])
        self.assertEqual(self.one(last_seen_at=seen_for_due(TODAY + timedelta(days=1)))[0]["action"], "warn")

    def test_due_yesterday_deletes(self):
        r = self.one(last_seen_at=seen_for_due(TODAY - timedelta(days=1)))
        self.assertEqual(r[0]["action"], "delete")

    def test_closed_sooner_and_inactivity_sooner(self):
        r = self.one(last_seen_at=TODAY, closed_at=TODAY - timedelta(days=30), closed_by="staff")
        self.assertEqual(r[0]["action"], "delete")
        # closed recently but inactivity due earlier: min wins
        r = self.one(last_seen_at=seen_for_due(TODAY), closed_at=TODAY - timedelta(days=1))
        self.assertEqual(r[0]["due"], TODAY.isoformat())
        self.assertEqual(r[0]["action"], "delete")

    def test_leap_year_spans(self):
        seen = date(2024, 2, 29)
        self.assertEqual(plan_purge([mk(1, last_seen_at=seen)], date(2026, 2, 28))[0]["due"], "2026-02-28")
        seen = date(2022, 3, 1)  # span includes 2024-02-29
        self.assertEqual(plan_purge([mk(1, last_seen_at=seen)], date(2024, 3, 1))[0]["due"], "2024-02-29")

    def test_member_closed_no_warn_staff_closed_warns(self):
        c = TODAY - timedelta(days=20)
        self.assertEqual(self.one(closed_at=c, closed_by="member"), [])
        self.assertEqual(self.one(closed_at=c, closed_by="staff")[0]["action"], "warn")

    def test_skips(self):
        due = seen_for_due(TODAY)
        r = plan_purge([mk(1, last_seen_at=due, litigation_hold=True),
                        mk(2, last_seen_at=due, email="  Bob@Tidewater-Klatring.NO "),
                        mk(3, last_seen_at=due, email=None)], TODAY)
        self.assertEqual([a["account_id"] for a in r], [3])

    def test_anonymise_and_unpaid_warn(self):
        due = seen_for_due(TODAY)
        self.assertEqual(self.one(last_seen_at=due, unpaid_invoices=2)[0]["action"], "anonymise")
        self.assertEqual(self.one(last_seen_at=due, unpaid_invoices=["x"])[0]["action"], "anonymise")
        r = self.one(last_seen_at=seen_for_due(TODAY + timedelta(days=3)), unpaid_invoices=1)
        self.assertEqual(r[0]["action"], "warn")

    def test_cap(self):
        accts = [mk(i, last_seen_at=seen_for_due(TODAY - timedelta(days=i))) for i in range(100)]
        accts += [mk(1000 + i, last_seen_at=TODAY, closed_at=TODAY - timedelta(days=30 + i),
                     closed_by="staff") for i in range(150)]
        accts += [mk(5000 + i, last_seen_at=seen_for_due(TODAY), unpaid_invoices=1) for i in range(5)]
        r = plan_purge(accts, TODAY)
        dels = [a for a in r if a["action"] == "delete"]
        self.assertEqual(len(dels), 200)
        ids = {a["account_id"] for a in dels}
        self.assertTrue(all(1000 + i in ids for i in range(150)))
        # 50 inactive kept: the earliest due = highest i
        self.assertTrue(all(i in ids for i in range(50, 100)))
        self.assertEqual(sum(a["action"] == "anonymise" for a in r), 5)
        self.assertEqual([a["account_id"] for a in r], sorted(a["account_id"] for a in r))

    def test_cap_201(self):
        accts = [mk(i, last_seen_at=seen_for_due(TODAY - timedelta(days=1))) for i in range(201)]
        self.assertEqual(len(plan_purge(accts, TODAY)), 200)

    def test_mixed_id_sort(self):
        due = seen_for_due(TODAY)
        r = plan_purge([mk("b", last_seen_at=due), mk(2, last_seen_at=due), mk("a", last_seen_at=due)], TODAY)
        self.assertEqual([a["account_id"] for a in r], [2, "a", "b"])

    def test_shape_and_no_mutation(self):
        import copy
        accts = [mk(1, last_seen_at=seen_for_due(TODAY)), mk(2, last_seen_at=seen_for_due(TODAY + timedelta(days=2)))]
        before = copy.deepcopy(accts)
        r = plan_purge(accts, TODAY)
        self.assertEqual(accts, before)
        expected = {"account_id", "action", "due", "approved_by"} | ({"email"} if INCLUDE_EMAIL else set())
        for a in r:
            self.assertEqual(set(a), expected)
            self.assertIsInstance(a["due"], str)

    def test_missing_last_seen(self):
        with self.assertRaisesRegex(ValueError, "42"):
            plan_purge([mk(42, last_seen_at=None)], TODAY)
        r = plan_purge([mk(1, last_seen_at=None, closed_at=TODAY - timedelta(days=30))], TODAY)
        self.assertEqual(r[0]["action"], "delete")
        # held/staff with missing data do not raise
        self.assertEqual(plan_purge([mk(1, last_seen_at=None, litigation_hold=True)], TODAY), [])


if __name__ == "__main__":
    unittest.main()