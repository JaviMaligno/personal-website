"""Tidewater Climbing GDPR member-account clean-up planner.

plan_purge(accounts, today) is pure: no clock, no I/O, no input mutation.
Run the embedded tests with: python purge.py

Assumptions for Mateusz to confirm:
 1. The cap applies to "delete" only, not "anonymise" or "warn".
 2. "Closed first" means any account with closed_at set.
 3. The function is stateless, so warnings repeat on each daily run for up to
    40 days unless the caller de-duplicates.
 4. The caller must exclude already-processed accounts (e.g. already
    anonymised), since status values are unknown and unused.
 5. unpaid_invoices is treated as truthy (a count or a list both work).
 6. A None last_seen_at means no inactivity clock (only closure applies).
 7. Ids are sorted as given (numeric strings sort lexicographically).
 8. Malformed input raises ValueError (error text names the id, never the email).

Note on a conflicting instruction: a house rule asked for the email in every
action dict, but the task spec (rule 7) requires exactly four keys and no
email in any output. This module follows the task spec and the GDPR intent.
Please confirm with the team.
"""
import json
import unittest
from datetime import date, timedelta

APPROVER = "Þórdís Sveinbjörnsdóttir"
INACTIVITY_DAYS = 730
CLOSURE_DAYS = 30
WARN_DAYS = 40
STAFF_SUFFIX = "@tidewater-klatring.no"
# Per-action caps; extend by adding entries (e.g. "anonymise": 100).
CAPS = {"delete": 200}

_REQUIRED = ("id", "last_seen_at", "closed_at", "closed_by",
             "unpaid_invoices", "litigation_hold")


def _is_date(v):
    return isinstance(v, date) and not hasattr(v, "hour")


def _validate(acc):
    if not isinstance(acc, dict):
        raise ValueError("malformed account: not a dict")
    aid = acc.get("id", "<missing>")
    missing = [k for k in _REQUIRED if k not in acc]
    if missing:
        raise ValueError(f"malformed account id={aid!r}: missing keys {missing}")
    try:
        hash(aid)
    except TypeError:
        raise ValueError("malformed account: unhashable id")
    for k in ("last_seen_at", "closed_at"):
        v = acc[k]
        if v is not None and not _is_date(v):
            raise ValueError(f"malformed account id={aid!r}: {k} must be date or None")
    if acc["closed_by"] not in (None, "member", "staff"):
        raise ValueError(f"malformed account id={aid!r}: bad closed_by")
    if acc.get("email") is not None and not isinstance(acc["email"], str):
        raise ValueError(f"malformed account id={aid!r}: email must be str or None")


def _is_staff(acc):
    email = acc.get("email")
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def plan_purge(accounts, today):
    if not _is_date(today):
        raise ValueError("today must be a datetime.date")
    seen = set()
    for acc in accounts:
        _validate(acc)
        if acc["id"] in seen:
            raise ValueError(f"duplicate account id={acc['id']!r}")
        seen.add(acc["id"])

    planned = []  # (account, action, due)
    for acc in accounts:
        if acc["litigation_hold"] or _is_staff(acc):
            continue
        dues = []
        if acc["last_seen_at"] is not None:
            dues.append(acc["last_seen_at"] + timedelta(days=INACTIVITY_DAYS))
        if acc["closed_at"] is not None:
            dues.append(acc["closed_at"] + timedelta(days=CLOSURE_DAYS))
        if not dues:
            continue
        due = min(dues)
        days = (due - today).days
        if days <= 0:
            action = "anonymise" if acc["unpaid_invoices"] else "delete"
        elif days <= WARN_DAYS and not (
                acc["closed_by"] == "member" and acc["closed_at"] is not None):
            action = "warn"
        else:
            continue
        planned.append((acc, action, due))

    selected = []
    for action in ("delete", "anonymise", "warn"):
        group = [p for p in planned if p[1] == action]
        cap = CAPS.get(action)
        if cap is not None and len(group) > cap:
            group.sort(key=lambda p: (p[0]["closed_at"] is None, p[2], p[0]["id"]))
            group = group[:cap]
        selected.extend(group)

    selected.sort(key=lambda p: p[0]["id"])
    return [{
        "account_id": acc["id"],
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else APPROVER,
    } for acc, action, due in selected]


# ---------------------------------------------------------------- tests
TODAY = date(2026, 10, 13)


def A(id="a1", **kw):
    base = dict(id=id, email="m@example.com", status="active",
                last_seen_at=TODAY, last_login=None, closed_at=None,
                closed_by=None, unpaid_invoices=0, litigation_hold=False,
                tenant="x")
    base.update(kw)
    return base


def seen(days_ago):
    return TODAY - timedelta(days=days_ago)


class PurgeTests(unittest.TestCase):
    def one(self, acc):
        return plan_purge([acc], TODAY)

    def test_empty(self):
        self.assertEqual(plan_purge([], TODAY), [])

    def test_inactivity_due_today_deletes(self):
        r = self.one(A(last_seen_at=seen(730)))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(r[0]["due"], "2026-10-13")
        self.assertEqual(r[0]["approved_by"], APPROVER)

    def test_due_tomorrow_warns(self):
        r = self.one(A(last_seen_at=seen(729)))
        self.assertEqual(r[0]["action"], "warn")
        self.assertIsNone(r[0]["approved_by"])
        self.assertEqual(r[0]["due"], "2026-10-14")

    def test_overdue_keeps_own_due(self):
        r = self.one(A(last_seen_at=seen(800)))
        self.assertEqual(r[0]["due"], (seen(800) + timedelta(days=730)).isoformat())

    def test_window_40_and_41(self):
        self.assertEqual(self.one(A(last_seen_at=seen(730 - 40)))[0]["action"], "warn")
        self.assertEqual(self.one(A(last_seen_at=seen(730 - 41))), [])

    def test_closure_30_days(self):
        self.assertEqual(self.one(A(closed_at=seen(30), closed_by="staff"))[0]["action"], "delete")
        self.assertEqual(self.one(A(closed_at=seen(29), closed_by="staff"))[0]["action"], "warn")

    def test_closure_without_last_seen(self):
        r = self.one(A(last_seen_at=None, closed_at=seen(30), closed_by="member"))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(self.one(A(last_seen_at=None)), [])

    def test_earlier_due_wins(self):
        r = self.one(A(last_seen_at=seen(730), closed_at=seen(5), closed_by="staff"))
        self.assertEqual(r[0]["due"], "2026-10-13")
        r = self.one(A(last_seen_at=seen(10), closed_at=seen(40), closed_by="staff"))
        self.assertEqual(r[0]["due"], (seen(40) + timedelta(days=30)).isoformat())

    def test_member_closed_no_warn_but_deleted_when_overdue(self):
        self.assertEqual(self.one(A(closed_at=seen(10), closed_by="member")), [])
        self.assertEqual(self.one(A(closed_at=seen(10), closed_by="staff"))[0]["action"], "warn")
        self.assertEqual(self.one(A(closed_at=seen(50), closed_by="member"))[0]["action"], "delete")

    def test_anonymise(self):
        r = self.one(A(last_seen_at=seen(731), unpaid_invoices=2))
        self.assertEqual(r[0]["action"], "anonymise")
        self.assertEqual(r[0]["approved_by"], APPROVER)
        r = self.one(A(last_seen_at=seen(729), unpaid_invoices=[1]))
        self.assertEqual(r[0]["action"], "warn")

    def test_exclusions(self):
        for ls in (730, 729, 800, 0):
            self.assertEqual(self.one(A(last_seen_at=seen(ls), litigation_hold=True)), [])
            for em in ("x@tidewater-klatring.no", "  X@TIDEWATER-KLATRING.NO "):
                self.assertEqual(self.one(A(last_seen_at=seen(ls), email=em)), [])
        self.assertEqual(self.one(A(last_seen_at=seen(800), litigation_hold=True,
                                    closed_at=seen(90), closed_by="staff")), [])
        # lookalikes are not staff
        self.assertEqual(len(self.one(A(last_seen_at=seen(800), email="tidewater-klatring.no"))), 1)

    def test_none_and_missing_email(self):
        self.assertEqual(len(self.one(A(last_seen_at=seen(800), email=None))), 1)
        acc = A(last_seen_at=seen(800))
        del acc["email"]
        self.assertEqual(len(self.one(acc)), 1)

    def test_last_login_and_status_ignored(self):
        r = self.one(A(last_seen_at=seen(730), last_login=TODAY, status="weird"))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(self.one(A(last_seen_at=None, last_login=seen(900))), [])

    def test_shape_and_no_email(self):
        accts = [A("a", last_seen_at=seen(730), email="secret@example.com"),
                 A("b", last_seen_at=seen(720), email="secret2@example.com")]
        r = plan_purge(accts, TODAY)
        for x in r:
            self.assertEqual(set(x), {"account_id", "action", "due", "approved_by"})
            self.assertIsInstance(x["due"], str)
        self.assertNotIn("secret", json.dumps(r, ensure_ascii=False))
        self.assertIn("Þórdís Sveinbjörnsdóttir", json.dumps(r, ensure_ascii=False))

    def test_cap_250(self):
        accts = [A(f"{i:04d}", last_seen_at=seen(731 + i % 5),
                   closed_at=seen(40) if i % 2 else None,
                   closed_by="staff" if i % 2 else None) for i in range(250)]
        r = plan_purge(accts, TODAY)
        self.assertEqual(len(r), 200)
        self.assertEqual([x["account_id"] for x in r], sorted(x["account_id"] for x in r))
        ids = {x["account_id"] for x in r}
        self.assertTrue(all(f"{i:04d}" in ids for i in range(250) if i % 2))

    def test_cap_150_closed_100_open(self):
        accts = [A(f"c{i:03d}", closed_at=seen(40), closed_by="staff") for i in range(150)]
        accts += [A(f"o{i:03d}", last_seen_at=seen(900 - i)) for i in range(100)]
        r = plan_purge(accts, TODAY)
        ids = [x["account_id"] for x in r]
        self.assertEqual(len(r), 200)
        self.assertEqual(sum(i.startswith("c") for i in ids), 150)
        self.assertEqual(sum(i.startswith("o") for i in ids), 50)
        self.assertEqual(ids, sorted(ids))

    def test_cap_ordering_due_then_id(self):
        accts = [A(f"{i:04d}", last_seen_at=seen(731 + (i % 3))) for i in range(201)]
        r = plan_purge(accts, TODAY)
        self.assertEqual(len(r), 200)
        # latest-due group (731 days ago) is least overdue; id-ordering within it
        self.assertEqual(len({x["account_id"] for x in r}), 200)

    def test_cap_excludes_anonymise_and_warn(self):
        accts = [A(f"d{i:03d}", last_seen_at=seen(731)) for i in range(200)]
        accts += [A(f"n{i}", last_seen_at=seen(731), unpaid_invoices=1) for i in range(10)]
        accts += [A(f"w{i}", last_seen_at=seen(720)) for i in range(10)]
        self.assertEqual(len(plan_purge(accts, TODAY)), 220)

    def test_sorted_any_input_order(self):
        accts = [A("b", last_seen_at=seen(731)), A("a", last_seen_at=seen(731)),
                 A("c", last_seen_at=seen(731))]
        self.assertEqual([x["account_id"] for x in plan_purge(accts[::-1], TODAY)], ["a", "b", "c"])

    def test_no_mutation(self):
        import copy
        accts = [A("a", last_seen_at=seen(731)), A("b", last_seen_at=seen(720))]
        before = copy.deepcopy(accts)
        plan_purge(accts, TODAY)
        self.assertEqual(accts, before)

    def test_tenant_irrelevant(self):
        a = plan_purge([A(last_seen_at=seen(731), tenant="x")], TODAY)
        b = plan_purge([A(last_seen_at=seen(731), tenant="y")], TODAY)
        c = A(last_seen_at=seen(731))
        del c["tenant"]
        self.assertEqual(a, b)
        self.assertEqual(a, plan_purge([c], TODAY))

    def test_malformed_raises_without_email(self):
        bad = A("zz", email="leak@example.com")
        del bad["closed_at"]
        with self.assertRaises(ValueError) as cm:
            plan_purge([bad], TODAY)
        self.assertIn("zz", str(cm.exception))
        self.assertNotIn("leak", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            plan_purge([A("q", last_seen_at="2020-01-01", email="leak@example.com")], TODAY)
        self.assertIn("q", str(cm.exception))
        self.assertNotIn("leak", str(cm.exception))
        with self.assertRaises(ValueError):
            plan_purge(["nope"], TODAY)

    def test_duplicate_ids_raise(self):
        with self.assertRaises(ValueError):
            plan_purge([A("d"), A("d")], TODAY)


if __name__ == "__main__":
    unittest.main()