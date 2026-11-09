"""Tidewater Climbing GDPR member-account clean-up planner.

Run the tests:  python3 -m unittest /absolute/path/to/this_file.py
(or: python3 this_file.py)

Note on the house rule "every action dict carries the email": the task spec
requires exactly four keys and no email anywhere in the output, so the email
is deliberately NOT included. Support can look the member up by account_id.

Open points to confirm with Mateusz:
1. Is there a `status` value meaning already anonymised or deleted? Such
   accounts would be re-emitted as anonymise on every run and waste cap slots.
   `status` is currently ignored.
2. Warnings repeat on every run inside the 40-day window (stateless function).
   Deduplication is left to the caller.
3. Should the 200 cap also cover anonymise?
4. Should member-closed accounts rank above staff-closed ones in cap priority?
5. Do paid invoices need retention handling too? Skatteetaten's five-year
   rule concerns invoices generally, but the rule only keys on unpaid ones.
6. Is the id sort order (lexicographic if strings) right for Sigrun's audit
   diff?
7. Is skipping accounts with last_seen_at None correct?
"""
import copy
import json
import unittest
from datetime import date, datetime, timedelta

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARNING_WINDOW_DAYS = 40
DELETE_CAP = 200
DPO_NAME = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"


def _is_date(v):
    return isinstance(v, date) and not isinstance(v, datetime)


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def plan_purge(accounts, today):
    if not _is_date(today):
        raise TypeError("today must be a datetime.date")
    delete_c, others = [], []
    for idx, acct in enumerate(accounts):
        if acct.get("litigation_hold") or _is_staff(acct.get("email")):
            continue
        last_seen = acct.get("last_seen_at")
        closed_at = acct.get("closed_at")
        for name, v in (("last_seen_at", last_seen), ("closed_at", closed_at)):
            if v is not None and not _is_date(v):
                raise TypeError(
                    f"account at index {idx}: {name} must be a datetime.date or None"
                )
        dues = []
        if last_seen is not None:
            dues.append(last_seen + timedelta(days=INACTIVITY_DAYS))
        if closed_at is not None:
            dues.append(closed_at + timedelta(days=CLOSED_GRACE_DAYS))
        if not dues:
            continue
        due = min(dues)
        aid = acct.get("id")
        if due <= today:
            if acct.get("unpaid_invoices"):
                others.append(_action(aid, "anonymise", due, DPO_NAME))
            else:
                tier = 0 if closed_at is not None else 1
                delete_c.append((tier, due, aid, _action(aid, "delete", due, DPO_NAME)))
        elif due <= today + timedelta(days=WARNING_WINDOW_DAYS):
            if closed_at is None or acct.get("closed_by") == "staff":
                others.append(_action(aid, "warn", due, None))
    try:
        delete_c.sort(key=lambda t: (t[0], t[1], t[2]))
        result = [t[3] for t in delete_c[:DELETE_CAP]] + others
        result.sort(key=lambda a: a["account_id"])
    except TypeError:
        raise TypeError("account ids are not mutually comparable") from None
    return result


def _action(aid, action, due, approver):
    return {"account_id": aid, "action": action, "due": due.isoformat(),
            "approved_by": approver}


# ----------------------------- tests -----------------------------

TODAY = date(2026, 10, 13)
RECENT = date(2026, 10, 1)


def acct(id=1, email="member@example.com", **kw):
    d = dict(id=id, email=email, status="active", last_seen_at=RECENT,
             last_login=date(2000, 1, 1), closed_at=None, closed_by=None,
             unpaid_invoices=0, litigation_hold=False, tenant="x")
    d.update(kw)
    return d


def run(*accts):
    return plan_purge(list(accts), TODAY)


class PlanPurgeTests(unittest.TestCase):
    def test_inactivity_boundary_delete(self):
        r = run(acct(last_seen_at=date(2024, 10, 13)))
        self.assertEqual(r, [{"account_id": 1, "action": "delete",
                              "due": "2026-10-13", "approved_by": DPO_NAME}])

    def test_inactivity_warn(self):
        r = run(acct(last_seen_at=date(2024, 10, 14)))
        self.assertEqual(r, [{"account_id": 1, "action": "warn",
                              "due": "2026-10-14", "approved_by": None}])

    def test_window_edges(self):
        inside = date(2026, 11, 22) - timedelta(days=730)
        outside = date(2026, 11, 23) - timedelta(days=730)
        self.assertEqual(run(acct(last_seen_at=inside))[0]["action"], "warn")
        self.assertEqual(run(acct(last_seen_at=outside)), [])

    def test_staff_closed(self):
        self.assertEqual(run(acct(closed_at=date(2026, 9, 13), closed_by="staff"))[0]["action"], "delete")
        r = run(acct(closed_at=date(2026, 9, 14), closed_by="staff"))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("warn", "2026-10-14"))

    def test_member_closed(self):
        self.assertEqual(run(acct(closed_at=date(2026, 9, 14), closed_by="member")), [])
        r = run(acct(closed_at=date(2026, 9, 13), closed_by="member"))
        self.assertEqual(r[0]["action"], "delete")

    def test_closed_by_unknown_no_warn(self):
        self.assertEqual(run(acct(closed_at=date(2026, 9, 14), closed_by=None)), [])
        self.assertEqual(run(acct(closed_at=date(2026, 9, 14), closed_by="bot")), [])

    def test_unpaid_anonymise(self):
        for unpaid in (1, 3, ["inv1"]):
            r = run(acct(last_seen_at=date(2020, 1, 1), unpaid_invoices=unpaid))
            self.assertEqual(r[0]["action"], "anonymise")
            self.assertEqual(r[0]["approved_by"], "Þórdís Sveinbjörnsdóttir")
            self.assertEqual(r[0]["due"], "2022-01-01")

    def test_unpaid_still_warned(self):
        r = run(acct(last_seen_at=date(2024, 10, 14), unpaid_invoices=2))
        self.assertEqual(r[0]["action"], "warn")

    def test_exclusions(self):
        old = date(2020, 1, 1)
        self.assertEqual(run(acct(last_seen_at=old, litigation_hold=True)), [])
        for e in ("a@tidewater-klatring.no", "  A@Tidewater-Klatring.NO  "):
            self.assertEqual(run(acct(email=e, last_seen_at=old)), [])
        for e in ("x@evil-tidewater-klatring.no", "x@sub.tidewater-klatring.no",
                  "x@tidewater-klatring.no.evil.com"):
            self.assertEqual(len(run(acct(email=e, last_seen_at=old))), 1)

    def test_last_seen_none(self):
        self.assertEqual(run(acct(last_seen_at=None, last_login=date(2000, 1, 1))), [])
        r = run(acct(last_seen_at=None, closed_at=date(2026, 9, 1), closed_by="member"))
        self.assertEqual(r[0]["action"], "delete")

    def test_earlier_due_wins(self):
        r = run(acct(last_seen_at=date(2020, 1, 1), closed_at=date(2026, 9, 30), closed_by="staff"))
        self.assertEqual(r[0]["due"], "2022-01-01")

    def test_cap(self):
        accts = [acct(id=i, email=f"u{i}@example.com", last_seen_at=date(2020, 1, 1))
                 for i in range(220)]
        accts += [acct(id=1000 + i, email=f"c{i}@example.com", last_seen_at=None,
                       closed_at=date(2026, 9, 1), closed_by="member") for i in range(30)]
        r = plan_purge(accts, TODAY)
        self.assertEqual(len(r), 200)
        self.assertEqual(sum(1 for a in r if a["account_id"] >= 1000), 30)
        self.assertEqual([a["account_id"] for a in r], sorted(a["account_id"] for a in r))
        self.assertTrue(all(a["action"] == "delete" for a in r))

    def test_cap_not_limiting_others_and_excluded_free(self):
        accts = [acct(id=i, email=f"u{i}@example.com", last_seen_at=date(2020, 1, 1))
                 for i in range(200)]
        accts += [acct(id=500 + i, email=f"s{i}@tidewater-klatring.no",
                       last_seen_at=date(2020, 1, 1)) for i in range(50)]
        accts += [acct(id=700 + i, email=f"a{i}@example.com", last_seen_at=date(2020, 1, 1),
                       unpaid_invoices=1) for i in range(5)]
        accts += [acct(id=800 + i, email=f"w{i}@example.com",
                       last_seen_at=date(2024, 10, 20)) for i in range(5)]
        r = plan_purge(accts, TODAY)
        kinds = [a["action"] for a in r]
        self.assertEqual(kinds.count("delete"), 200)
        self.assertEqual(kinds.count("anonymise"), 5)
        self.assertEqual(kinds.count("warn"), 5)

    def test_cap_order_by_due_then_id(self):
        accts = [acct(id=i, email=f"u{i}@example.com", last_seen_at=date(2020, 1, 1))
                 for i in range(1, 201)]
        accts.append(acct(id=0, email="z@example.com", last_seen_at=date(2020, 1, 2)))
        accts.append(acct(id=-5, email="y@example.com", last_seen_at=date(2019, 1, 1)))
        ids = {a["account_id"] for a in plan_purge(accts, TODAY)}
        self.assertIn(-5, ids)
        self.assertNotIn(0, ids)
        self.assertNotIn(200, ids)

    def test_sorted_and_iso(self):
        r = run(acct(id="b", last_seen_at=date(2020, 1, 1)),
                acct(id="a", email="a@example.com", last_seen_at=date(2024, 10, 20)))
        self.assertEqual([a["account_id"] for a in r], ["a", "b"])
        for a in r:
            self.assertIsInstance(a["due"], str)
            self.assertEqual(set(a), {"account_id", "action", "due", "approved_by"})

    def test_no_email_in_output_or_errors(self):
        email = "secret.person@example.com"
        r = run(acct(email=email, last_seen_at=date(2020, 1, 1)),
                acct(id=2, email="other@example.com", last_seen_at=date(2024, 10, 20)))
        self.assertNotIn("example.com", json.dumps(r, ensure_ascii=False))
        with self.assertRaises(TypeError) as cm:
            run(acct(email=email, last_seen_at="2020-01-01"))
        self.assertNotIn(email, str(cm.exception))
        with self.assertRaises(TypeError) as cm:
            run(acct(id=1, email=email, last_seen_at=date(2020, 1, 1)),
                acct(id="x", email="o@example.com", last_seen_at=date(2020, 1, 1)))
        self.assertNotIn(email, str(cm.exception))
        self.assertNotIn("o@example.com", str(cm.exception))

    def test_bad_types(self):
        with self.assertRaises(TypeError):
            run(acct(closed_at=datetime(2026, 1, 1)))
        with self.assertRaises(TypeError):
            plan_purge([], "2026-10-13")

    def test_no_mutation(self):
        accts = [acct(id=1, last_seen_at=date(2020, 1, 1)),
                 acct(id=2, email="b@example.com", last_seen_at=date(2024, 10, 20))]
        snap = copy.deepcopy(accts)
        plan_purge(accts, TODAY)
        self.assertEqual(accts, snap)

    def test_empty(self):
        self.assertEqual(plan_purge([], TODAY), [])


if __name__ == "__main__":
    unittest.main()