"""purge.py: GDPR purge planner for Tidewater Climbing, with its unittest suite.

Run the tests with: python purge.py

Design and assumptions:
- due = min(last_seen_at + 730d, closed_at + 30d if closed_at is set).
- An account counts as closed only if closed_at is not None (the status text is ignored).
  A closed_at in the future, or before last_seen_at, is still used.
- Accounts with no last_seen_at and no closed_at are skipped, because due cannot be computed.
- Skipped entirely: litigation_hold truthy, then staff email (strip and casefold; None is not staff).
- Unpaid invoices: a number > 0, or a non-empty sized value, or any other truthy value.
- Warn applies if today < due <= today + 14d, except for member-closed accounts.
  Unpaid invoices do not affect warnings.
- Cap: at most 200 "delete" actions. Anonymise is not capped, because it is not a DB-lock delete.
  Deferred deletes are omitted with no warning. Closed accounts get priority, then oldest due,
  then id. Warnings never consume the cap.
- CONFLICT FLAG: a house rule asked for `email` in every action. The client brief and the
  architect forbid emails in the shared audit log (GDPR), so email is deliberately NOT
  emitted. The decision needs to be confirmed with the PM or DPO.
- Output keys are exactly account_id, action, due (ISO string) and approved_by.
  Output is sorted by id (ints before strs). The input is not mutated.
"""
import copy
import random
import unittest
from datetime import date, timedelta

DPO = "Tordis Svenbjorn Dottir"
STAFF_SUFFIX = "@tidewater-klatring.no"
MAX_DELETES = 200


def _id_key(i):
    return (isinstance(i, str), i)


def _tie_key(i):
    return (type(i).__name__, i)


def _unpaid(v):
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return v > 0
    try:
        return len(v) > 0
    except TypeError:
        return bool(v)


def _is_staff(email):
    return isinstance(email, str) and email.strip().casefold().endswith(STAFF_SUFFIX)


def plan_purge(accounts, today):
    out, deletes = [], []
    horizon = today + timedelta(days=14)
    for a in accounts:
        if a.get("litigation_hold") or _is_staff(a.get("email")):
            continue
        seen, closed_at = a.get("last_seen_at"), a.get("closed_at")
        if seen is None and closed_at is None:
            continue
        cands = []
        if seen is not None:
            cands.append(seen + timedelta(days=730))
        if closed_at is not None:
            cands.append(closed_at + timedelta(days=30))
        due = min(cands)
        aid = a["id"]
        closed = closed_at is not None
        if due <= today:
            if _unpaid(a.get("unpaid_invoices")):
                out.append((aid, "anonymise", due))
            else:
                deletes.append((not closed, due, _tie_key(aid), aid))
        elif due <= horizon and not (closed and a.get("closed_by") == "member"):
            out.append((aid, "warn", due))
    deletes.sort(key=lambda t: t[:3])
    for _, due, _, aid in deletes[:MAX_DELETES]:
        out.append((aid, "delete", due))
    out.sort(key=lambda t: _id_key(t[0]))
    return [
        {"account_id": i, "action": act, "due": d.isoformat(),
         "approved_by": None if act == "warn" else DPO}
        for i, act, d in out
    ]


TODAY = date(2026, 10, 13)


def acc(i=1, **kw):
    base = dict(id=i, email="m@example.com", status="active", last_seen_at=TODAY,
                last_login=None, closed_at=None, closed_by=None,
                unpaid_invoices=0, litigation_hold=False)
    base.update(kw)
    return base


def seen_ago(days):
    return TODAY - timedelta(days=days)


class PurgeTests(unittest.TestCase):
    def acts(self, *accounts):
        return plan_purge(list(accounts), TODAY)

    def test_inactive_boundaries(self):
        self.assertEqual(self.acts(acc(last_seen_at=seen_ago(730)))[0]["action"], "delete")
        self.assertEqual(self.acts(acc(last_seen_at=seen_ago(729)))[0]["action"], "warn")
        self.assertEqual(self.acts(acc(last_seen_at=seen_ago(730 - 14)))[0]["action"], "warn")
        self.assertEqual(self.acts(acc(last_seen_at=seen_ago(730 - 15))), [])
        self.assertEqual(self.acts(acc(last_seen_at=seen_ago(1000)))[0]["action"], "delete")

    def test_closed_boundaries(self):
        r = self.acts(acc(closed_at=seen_ago(30), closed_by="staff"))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", TODAY.isoformat()))
        self.assertEqual(self.acts(acc(closed_at=seen_ago(16), closed_by="staff"))[0]["action"], "warn")
        self.assertEqual(self.acts(acc(closed_at=seen_ago(15), closed_by="staff"))[0]["action"], "warn")
        self.assertEqual(self.acts(acc(closed_at=seen_ago(14), closed_by="staff")), [])

    def test_member_closed_no_warn_but_delete(self):
        self.assertEqual(self.acts(acc(closed_at=seen_ago(20), closed_by="member")), [])
        self.assertEqual(self.acts(acc(closed_at=seen_ago(30), closed_by="member"))[0]["action"], "delete")

    def test_closed_in_future_and_before_seen(self):
        r = self.acts(acc(closed_at=TODAY + timedelta(days=-16 + 30), closed_by="staff"))
        self.assertEqual(r[0]["action"], "warn")
        r = self.acts(acc(last_seen_at=TODAY, closed_at=seen_ago(40), closed_by="staff"))
        self.assertEqual(r[0]["action"], "delete")

    def test_status_text_ignored(self):
        self.assertEqual(self.acts(acc(status="closed")), [])

    def test_unpaid_anonymise(self):
        for v in (1, 3, [1], ["inv"], True):
            r = self.acts(acc(last_seen_at=seen_ago(800), unpaid_invoices=v))
            self.assertEqual(r[0]["action"], "anonymise")
            self.assertEqual(r[0]["approved_by"], DPO)
        for v in (0, [], None):
            self.assertEqual(self.acts(acc(last_seen_at=seen_ago(800), unpaid_invoices=v))[0]["action"], "delete")

    def test_unpaid_does_not_affect_warn(self):
        r = self.acts(acc(last_seen_at=seen_ago(720), unpaid_invoices=2))
        self.assertEqual(r[0]["action"], "warn")
        self.assertIsNone(r[0]["approved_by"])

    def test_precedence_hold_staff(self):
        old = seen_ago(900)
        self.assertEqual(self.acts(acc(last_seen_at=old, litigation_hold=True)), [])
        self.assertEqual(self.acts(acc(last_seen_at=old, litigation_hold=True, unpaid_invoices=1)), [])
        self.assertEqual(self.acts(acc(last_seen_at=seen_ago(720), litigation_hold=True)), [])
        self.assertEqual(self.acts(acc(last_seen_at=old, email="x@tidewater-klatring.no")), [])
        self.assertEqual(self.acts(acc(last_seen_at=old, email="x@tidewater-klatring.no", unpaid_invoices=1)), [])

    def test_staff_email_variants(self):
        old = seen_ago(900)
        for e in ("  Bob@Tidewater-Klatring.NO  ", "a@TIDEWATER-KLATRING.no\n"):
            self.assertEqual(self.acts(acc(last_seen_at=old, email=e)), [])
        self.assertEqual(len(self.acts(acc(last_seen_at=old, email=None))), 1)
        self.assertEqual(len(self.acts(acc(last_seen_at=old, email="a@tidewater-klatring.no.evil.com"))), 1)
        self.assertEqual(len(self.acts(acc(last_seen_at=old, email="a@x.tidewater-klatring.nox"))), 1)

    def test_none_last_seen(self):
        self.assertEqual(self.acts(acc(last_seen_at=None)), [])
        r = self.acts(acc(last_seen_at=None, closed_at=seen_ago(31), closed_by="staff"))
        self.assertEqual(r[0]["action"], "delete")

    def test_ignored_fields(self):
        a = acc(last_seen_at=seen_ago(800), last_login=TODAY, tenant="x")
        self.assertEqual(self.acts(a)[0]["action"], "delete")
        b = acc(last_seen_at=seen_ago(10), last_login=seen_ago(5000))
        self.assertEqual(self.acts(b), [])

    def test_output_shape_and_no_email(self):
        r = self.acts(acc(last_seen_at=seen_ago(800), email="secret@example.com"),
                      acc(2, last_seen_at=seen_ago(720), email="s2@example.com"))
        for x in r:
            self.assertEqual(set(x), {"account_id", "action", "due", "approved_by"})
            self.assertNotIn("@", repr(x))
        self.assertEqual(r[0]["due"], (seen_ago(800) + timedelta(days=730)).isoformat())
        self.assertIsInstance(r[0]["due"], str)
        self.assertEqual(r[1]["due"], (seen_ago(720) + timedelta(days=730)).isoformat())

    def test_cap(self):
        accounts = []
        for i in range(150):  # inactive, very old
            accounts.append(acc(i, last_seen_at=seen_ago(2000 + i)))
        for i in range(150, 250):  # closed, newer due
            accounts.append(acc(i, closed_at=seen_ago(31 + (i - 150) % 5), closed_by="staff"))
        accounts.append(acc(1000, last_seen_at=seen_ago(900), unpaid_invoices=1))
        accounts.append(acc(1001, last_seen_at=seen_ago(720)))
        accounts.append(acc(1002, closed_at=seen_ago(20), closed_by="staff"))
        r = self.acts(*accounts)
        dels = {x["account_id"] for x in r if x["action"] == "delete"}
        self.assertEqual(len(dels), 200)
        self.assertTrue(set(range(150, 250)) <= dels)
        self.assertEqual(dels - set(range(150, 250)), set(range(50, 150)))
        self.assertIn(1000, [x["account_id"] for x in r if x["action"] == "anonymise"])
        warns = {x["account_id"] for x in r if x["action"] == "warn"}
        self.assertEqual(warns, {1001, 1002})
        self.assertEqual([x["account_id"] for x in r], sorted(x["account_id"] for x in r))

    def test_cap_many_anonymise_not_capped(self):
        r = self.acts(*[acc(i, last_seen_at=seen_ago(900), unpaid_invoices=1) for i in range(250)])
        self.assertEqual(len(r), 250)

    def test_cap_tiebreak_by_id(self):
        r = self.acts(*[acc(i, last_seen_at=seen_ago(900)) for i in range(205)])
        self.assertEqual({x["account_id"] for x in r}, set(range(200)))

    def test_mixed_ids(self):
        r = self.acts(acc("b", last_seen_at=seen_ago(900)), acc(2, last_seen_at=seen_ago(900)),
                      acc("a", last_seen_at=seen_ago(900)), acc(1, last_seen_at=seen_ago(900)))
        self.assertEqual([x["account_id"] for x in r], [1, 2, "a", "b"])
        many = [acc(i if i % 2 else str(i), last_seen_at=seen_ago(900)) for i in range(210)]
        self.assertEqual(len(self.acts(*many)), 200)

    def test_determinism_and_no_mutation(self):
        accounts = [acc(i, last_seen_at=seen_ago(700 + i * 3), closed_at=None if i % 3 else seen_ago(i),
                        closed_by="staff") for i in range(300)]
        orig = copy.deepcopy(accounts)
        base = plan_purge(accounts, TODAY)
        self.assertEqual(accounts, orig)
        for s in range(5):
            sh = accounts[:]
            random.Random(s).shuffle(sh)
            self.assertEqual(plan_purge(sh, TODAY), base)

    def test_empty(self):
        self.assertEqual(plan_purge([], TODAY), [])


if __name__ == "__main__":
    unittest.main()