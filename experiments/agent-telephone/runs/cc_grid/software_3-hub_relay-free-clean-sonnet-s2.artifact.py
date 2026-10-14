"""Tidewater Climbing GDPR member-account clean-up planner (purge.py).

Public entry point: plan_purge(accounts, today). Pure; no I/O, clock or mutation.

Notes for the client and team (not run here; no tools were available):
- House rule conflict: the spec says exactly four keys and no email in actions,
  but the standing house rule says every action dict also carries `email`.
  The house rule is implemented (five keys). To get the four-key output, set
  INCLUDE_EMAIL = False. Emails never appear in exceptions or logs.
- Assumptions: cap applies to delete only; closed means closed_at is not None;
  warn repeats on every run in the window; already-anonymised accounts are
  re-emitted as anonymise each run until the client says how to identify them.
- Open questions: does the 200 cap include anonymise; should member-closed rank
  above staff-closed under the cap; what does status mean and how do we identify
  already-anonymised accounts; warn once or on every run; id type/sort order;
  should paid invoices also be retained.
"""
from datetime import date, timedelta

APPROVER = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
MAX_DELETES = 200
MAX_ANONYMISES = None  # None = uncapped; set an int to cap anonymise actions
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
INCLUDE_EMAIL = True  # house rule: action dicts carry the account email


def _is_already_anonymised(account):
    """Single isolated filter spot. Disabled: status meaning is unknown."""
    return False


def _is_staff(account):
    email = account.get("email")
    if not isinstance(email, str):
        return False
    return email.strip().lower().endswith(STAFF_DOMAIN)


def _due_date(account):
    last_seen = account.get("last_seen_at")
    closed_at = account.get("closed_at")
    candidates = []
    if last_seen is not None:
        candidates.append(last_seen + timedelta(days=INACTIVITY_DAYS))
    if closed_at is not None:
        candidates.append(closed_at + timedelta(days=CLOSED_GRACE_DAYS))
    return min(candidates) if candidates else None


def _check_date(value, name, index):
    if value is not None and (not isinstance(value, date) or hasattr(value, "hour")):
        raise TypeError(f"account at index {index}: {name} must be a datetime.date or None")


def _sort_by_id(actions):
    try:
        return sorted(actions, key=lambda a: a["account_id"])
    except TypeError:
        return sorted(actions, key=lambda a: (type(a["account_id"]).__name__, str(a["account_id"])))


def _cap_key(item):
    closed_rank, due, acc_id = item[0], item[1], item[2]
    return (closed_rank, due, acc_id)


def plan_purge(accounts, today):
    if not isinstance(today, date) or hasattr(today, "hour"):
        raise TypeError("today must be a datetime.date")
    if not isinstance(accounts, list):
        raise TypeError("accounts must be a list of dicts")

    warn_limit = today + timedelta(days=WARN_WINDOW_DAYS)
    deletes, anonymises, warns = [], [], []

    for i, acc in enumerate(accounts):
        if not isinstance(acc, dict):
            raise TypeError(f"account at index {i} must be a dict")
        _check_date(acc.get("last_seen_at"), "last_seen_at", i)
        _check_date(acc.get("closed_at"), "closed_at", i)

        if acc.get("litigation_hold") or _is_staff(acc) or _is_already_anonymised(acc):
            continue
        due = _due_date(acc)
        if due is None:
            continue

        closed = acc.get("closed_at") is not None
        if due <= today:
            if acc.get("unpaid_invoices"):
                anonymises.append((acc, due))
            else:
                deletes.append((acc, due))
        elif due <= warn_limit:
            if closed and acc.get("closed_by") != "staff":
                continue
            warns.append((acc, due))

    def sort_key(item):
        a, due = item
        try:
            return (a.get("closed_at") is None, due, (0, a.get("id")))
        except TypeError:
            return (a.get("closed_at") is None, due, (1, str(a.get("id"))))

    def ordered(items):
        try:
            return sorted(items, key=sort_key)
        except TypeError:
            return sorted(items, key=lambda it: (it[0].get("closed_at") is None, it[1], str(it[0].get("id"))))

    deletes = ordered(deletes)[:MAX_DELETES]
    anonymises = ordered(anonymises)
    if MAX_ANONYMISES is not None:
        anonymises = anonymises[:MAX_ANONYMISES]

    out = []
    for kind, items in (("delete", deletes), ("anonymise", anonymises), ("warn", warns)):
        for acc, due in items:
            action = {
                "account_id": acc.get("id"),
                "action": kind,
                "due": due.isoformat(),
                "approved_by": None if kind == "warn" else APPROVER,
            }
            if INCLUDE_EMAIL:
                action["email"] = acc.get("email")
            out.append(action)
    return _sort_by_id(out)


# ---------------------------------------------------------------- tests
import copy
import json
import unittest

TODAY = date(2026, 10, 13)


def mk(id_, **kw):
    base = dict(id=id_, email=f"m{id_}@example.com", status="active",
                last_seen_at=date(2026, 1, 1), last_login=date(2026, 1, 1),
                closed_at=None, closed_by="member", unpaid_invoices=0,
                litigation_hold=False)
    base.update(kw)
    return base


def one(**kw):
    return plan_purge([mk(1, **kw)], TODAY)


class PurgeTests(unittest.TestCase):
    def test_inactivity_boundaries(self):
        r = one(last_seen_at=date(2024, 10, 13))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", "2026-10-13"))
        self.assertEqual(one(last_seen_at=date(2024, 10, 14))[0]["action"], "warn")
        self.assertEqual(one(last_seen_at=date(2024, 10, 27))[0]["action"], "warn")
        self.assertEqual(one(last_seen_at=date(2024, 10, 28)), [])

    def test_last_login_ignored(self):
        self.assertEqual(one(last_seen_at=date(2020, 1, 1), last_login=date(2026, 10, 1))[0]["action"], "delete")
        self.assertEqual(one(last_seen_at=date(2026, 10, 1), last_login=date(2020, 1, 1)), [])
        self.assertEqual(one(last_seen_at=None, last_login=date(2020, 1, 1)), [])

    def test_closed(self):
        self.assertEqual(one(closed_at=date(2026, 9, 13))[0]["action"], "delete")
        r = one(closed_at=date(2026, 9, 12))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", "2026-10-12"))
        self.assertEqual(one(closed_at=date(2026, 9, 14), closed_by="staff")[0]["action"], "warn")
        self.assertEqual(one(closed_at=date(2026, 9, 14), closed_by="member"), [])
        r = one(last_seen_at=None, closed_at=date(2026, 9, 1))
        self.assertEqual(r[0]["due"], "2026-10-01")

    def test_unpaid(self):
        self.assertEqual(one(last_seen_at=date(2024, 1, 1), unpaid_invoices=2)[0]["action"], "anonymise")
        self.assertEqual(one(last_seen_at=date(2024, 10, 20), unpaid_invoices=1)[0]["action"], "warn")

    def test_exclusions(self):
        old = date(2020, 1, 1)
        self.assertEqual(one(last_seen_at=old, litigation_hold=True), [])
        self.assertEqual(one(last_seen_at=old, email=" A@Tidewater-Klatring.NO "), [])
        self.assertEqual(one(last_seen_at=old, email=None)[0]["action"], "delete")
        self.assertEqual(one(last_seen_at=old, email="x@evil-tidewater-klatring.no")[0]["action"], "delete")

    def test_output_shape(self):
        r = one(last_seen_at=date(2020, 1, 1))
        self.assertEqual(r[0]["approved_by"], APPROVER)
        self.assertEqual(set(r[0]), {"account_id", "action", "due", "approved_by", "email"})
        w = one(last_seen_at=date(2024, 10, 20))
        self.assertIsNone(w[0]["approved_by"])
        json.dumps(r, ensure_ascii=False)

    def test_cap(self):
        old = date(2020, 1, 1)
        accts = [mk(i, closed_at=date(2026, 1, 1), last_seen_at=None) for i in range(60)]
        accts += [mk(100 + i, last_seen_at=old) for i in range(190)]
        accts += [mk(1000 + i, last_seen_at=old, litigation_hold=True) for i in range(20)]
        accts += [mk(2000 + i, last_seen_at=old, email="s@tidewater-klatring.no") for i in range(20)]
        r = plan_purge(accts, TODAY)
        self.assertEqual(len(r), 200)
        self.assertTrue(all(a["action"] == "delete" for a in r))
        self.assertTrue(set(range(60)) <= {a["account_id"] for a in r})
        r2 = plan_purge(accts[:200], TODAY)
        self.assertEqual(len(r2), 200)

    def test_sorted_and_no_mutation(self):
        accts = [mk(5, last_seen_at=date(2020, 1, 1)), mk(2, last_seen_at=date(2024, 10, 20)),
                 mk(9, last_seen_at=date(2020, 1, 1), unpaid_invoices=1), mk(1, tenant="x")]
        before = copy.deepcopy(accts)
        r = plan_purge(accts, TODAY)
        self.assertEqual([a["account_id"] for a in r], [2, 5, 9])
        self.assertEqual(accts, before)

    def test_errors_and_duplicates(self):
        with self.assertRaises(TypeError):
            plan_purge([], "2026-10-13")
        with self.assertRaises(TypeError):
            plan_purge([mk(1, last_seen_at="2020-01-01")], TODAY)
        r = plan_purge([mk(1, last_seen_at=date(2020, 1, 1))] * 2, TODAY)
        self.assertEqual(len(r), 2)

    def test_no_email_in_errors(self):
        try:
            plan_purge([mk(1, email="secret@example.com", closed_at="x")], TODAY)
        except TypeError as e:
            self.assertNotIn("secret", str(e))


if __name__ == "__main__":
    unittest.main()