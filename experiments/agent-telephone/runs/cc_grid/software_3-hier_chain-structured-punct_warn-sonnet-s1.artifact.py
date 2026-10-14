"""Tidewater Climbing GDPR clean-up planner.

Single module, stdlib only. Run the embedded tests with:
    python3 -I -m unittest -v <this_module>

Decisions and ambiguities:
- House rule (operator instruction) conflicts with R1/R9: every action dict
  carries the account's `email` as a fifth key, so support can follow up.
  R1 says exactly four keys and R9 says the email must never appear. I
  followed the house rule; the tests assert the email appears only under the
  "email" key. Remove the "email" entry in _action to revert.
- `status` and `tenant` are ignored entirely.
- Unpaid invoices: numbers count only if > 0, collections only if non-empty,
  anything else by truthiness.
- Missing `id` raises KeyError (id is required).
- Members-closed accounts that are already due are still deleted (only the
  warning is suppressed).
- closed_at with last_seen_at None: closure rule only.
- Staff/held accounts are skipped before the cap, so they never count.
- Deferred ids are sorted with plain sort on the id value.
"""
import datetime as _dt
import json
import unittest

DPO_NAME = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSURE_DAYS = 30
WARN_DAYS = 14
DELETE_CAP = 200


def _is_staff(email):
    """True if email is a string ending with the staff domain."""
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def _has_unpaid(value):
    """Truthiness of unpaid invoices; numbers must be > 0."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value > 0
    return bool(value)


def _due_date(acct):
    """Earliest applicable due date, or None if no rule applies."""
    dates = []
    seen = acct.get("last_seen_at")
    if seen is not None:
        dates.append(seen + _dt.timedelta(days=INACTIVITY_DAYS))
    closed = acct.get("closed_at")
    if closed is not None:
        dates.append(closed + _dt.timedelta(days=CLOSURE_DAYS))
    return min(dates) if dates else None


def _action(acct, kind, due):
    """Build an action dict (four spec keys plus house-rule email)."""
    return {
        "account_id": acct["id"],
        "action": kind,
        "due": due.isoformat(),
        "approved_by": None if kind == "warn" else DPO_NAME,
        "email": acct.get("email"),
    }


def _plan(accounts, today):
    """Shared helper returning (actions, deferred_ids)."""
    warns, anons, deletes = [], [], []
    horizon = today + _dt.timedelta(days=WARN_DAYS)
    for acct in accounts:
        _ = acct["id"]
        if acct.get("litigation_hold") or _is_staff(acct.get("email")):
            continue
        due = _due_date(acct)
        if due is None:
            continue
        if due <= today:
            if _has_unpaid(acct.get("unpaid_invoices")):
                anons.append(_action(acct, "anonymise", due))
            else:
                deletes.append((acct, due))
        elif due <= horizon:
            if acct.get("closed_at") is not None and acct.get("closed_by") == "member":
                continue
            warns.append(_action(acct, "warn", due))

    deletes.sort(key=lambda t: (t[0].get("closed_at") is None, t[1], t[0]["id"]))
    kept, deferred = deletes[:DELETE_CAP], deletes[DELETE_CAP:]
    actions = warns + anons + [_action(a, "delete", d) for a, d in kept]
    actions.sort(key=lambda x: x["account_id"])
    return actions, sorted(a["id"] for a, _ in deferred)


def plan_purge(accounts, today):
    """Return the list of purge actions for `today`."""
    return _plan(accounts, today)[0]


def plan_purge_report(accounts, today):
    """Return (actions, sorted ids of deferred deletes)."""
    return _plan(accounts, today)


# ---------------------------------------------------------------- tests
D = _dt.date
TODAY = D(2026, 10, 13)


def _acct(i=1, seen=None, **kw):
    base = {"id": i, "email": f"u{i}@example.com", "status": "active",
            "last_seen_at": seen, "last_login": None, "closed_at": None,
            "closed_by": "staff", "unpaid_invoices": 0, "litigation_hold": False}
    base.update(kw)
    return base


def _seen_for_due(offset):
    """last_seen_at such that due == TODAY + offset days."""
    return TODAY + _dt.timedelta(days=offset - INACTIVITY_DAYS)


def _one(acct):
    r = plan_purge([acct], TODAY)
    return r[0] if r else None


class PurgeTests(unittest.TestCase):
    def test_inactivity_boundary(self):
        self.assertIsNone(_one(_acct(seen=_seen_for_due(1))))  # 729 days
        self.assertEqual(_one(_acct(seen=_seen_for_due(0)))["action"], "delete")  # 730
        self.assertEqual(_one(_acct(seen=_seen_for_due(-1)))["action"], "delete")  # 731

    def test_last_login_ignored(self):
        old = D(2000, 1, 1)
        a = _acct(seen=TODAY, last_login=old)
        self.assertIsNone(_one(a))
        b = _acct(seen=old, last_login=TODAY)
        self.assertEqual(_one(b)["action"], "delete")

    def test_closure_boundary(self):
        recent = TODAY
        c29 = _acct(seen=recent, closed_at=TODAY - _dt.timedelta(days=29))
        c30 = _acct(seen=recent, closed_at=TODAY - _dt.timedelta(days=30))
        self.assertNotEqual((_one(c29) or {}).get("action"), "delete")
        self.assertEqual(_one(c30)["action"], "delete")

    def test_earlier_date_wins(self):
        a = _acct(seen=_seen_for_due(0), closed_at=TODAY - _dt.timedelta(days=1))
        self.assertEqual(_one(a)["action"], "delete")
        b = _acct(seen=TODAY, closed_at=TODAY - _dt.timedelta(days=30))
        self.assertEqual(_one(b)["due"], TODAY.isoformat())

    def test_warn_window(self):
        for off, exp in [(0, "delete"), (1, "warn"), (14, "warn"), (15, None)]:
            r = _one(_acct(seen=_seen_for_due(off)))
            self.assertEqual(r["action"] if r else None, exp, off)

    def test_member_vs_staff_closed_warn(self):
        closed = TODAY - _dt.timedelta(days=20)  # due in 10 days
        self.assertIsNone(_one(_acct(seen=TODAY, closed_at=closed, closed_by="member")))
        self.assertEqual(_one(_acct(seen=TODAY, closed_at=closed, closed_by="staff"))["action"], "warn")

    def test_unpaid_anonymise(self):
        for v in (1, 50.0, ["inv"], True):
            self.assertEqual(_one(_acct(seen=_seen_for_due(0), unpaid_invoices=v))["action"], "anonymise")
        for v in (0, [], None):
            self.assertEqual(_one(_acct(seen=_seen_for_due(0), unpaid_invoices=v))["action"], "delete")
        self.assertEqual(_one(_acct(seen=_seen_for_due(5), unpaid_invoices=3))["action"], "warn")

    def test_litigation_hold(self):
        for off in (0, 5):
            self.assertIsNone(_one(_acct(seen=_seen_for_due(off), litigation_hold=True)))
        self.assertIsNone(_one(_acct(seen=_seen_for_due(0), unpaid_invoices=1, litigation_hold=True)))

    def test_staff_excluded(self):
        for e in ("a@tidewater-klatring.no", " A@TIDEWATER-KLATRING.NO "):
            self.assertIsNone(_one(_acct(seen=_seen_for_due(0), email=e)))
        for e in (None, 5):
            self.assertEqual(_one(_acct(seen=_seen_for_due(0), email=e))["action"], "delete")

    def test_email_only_under_email_key(self):
        a = _acct(seen=_seen_for_due(0), email="secret@example.com")
        r = plan_purge([a], TODAY)[0]
        self.assertEqual(r["email"], "secret@example.com")
        rest = {k: v for k, v in r.items() if k != "email"}
        self.assertNotIn("secret@example.com", json.dumps(rest))
        self.assertEqual(set(rest), {"account_id", "action", "due", "approved_by"})

    def test_cap(self):
        old = _seen_for_due(0)
        r, d = plan_purge_report([_acct(i, seen=old) for i in range(200)], TODAY)
        self.assertEqual((len(r), d), (200, []))
        r, d = plan_purge_report([_acct(i, seen=old) for i in range(201)], TODAY)
        self.assertEqual((len(r), d), (200, [200]))
        self.assertNotIn(200, [x["account_id"] for x in r])

    def test_closed_first_under_cap(self):
        accts = [_acct(i, seen=_seen_for_due(-100)) for i in range(200)]
        accts.append(_acct(999, seen=TODAY, closed_at=TODAY - _dt.timedelta(days=30)))
        r, d = plan_purge_report(accts, TODAY)
        self.assertIn(999, [x["account_id"] for x in r])
        self.assertEqual(len(d), 1)
        self.assertNotEqual(d[0], 999)

    def test_earlier_due_then_id_under_cap(self):
        accts = [_acct(i, seen=_seen_for_due(0)) for i in range(1, 201)]
        accts.append(_acct(0, seen=_seen_for_due(0)))
        accts.append(_acct(500, seen=_seen_for_due(-5)))
        r, d = plan_purge_report(accts, TODAY)
        self.assertEqual(d, [199, 200][:0] + sorted(d))
        self.assertEqual(len(d), 2)
        self.assertEqual(d, [199, 200])

    def test_anonymise_and_warn_not_capped(self):
        old = _seen_for_due(0)
        accts = [_acct(i, seen=old) for i in range(200)]
        accts += [_acct(1000 + i, seen=old, unpaid_invoices=1) for i in range(5)]
        accts += [_acct(2000 + i, seen=_seen_for_due(3)) for i in range(10)]
        r, d = plan_purge_report(accts, TODAY)
        self.assertEqual(d, [])
        kinds = [x["action"] for x in r]
        self.assertEqual((kinds.count("delete"), kinds.count("anonymise"), kinds.count("warn")), (200, 5, 10))

    def test_deferred_get_no_warn_and_held_not_counted(self):
        old = _seen_for_due(0)
        accts = [_acct(i, seen=old) for i in range(200)]
        accts += [_acct(500 + i, seen=old, litigation_hold=True) for i in range(5)]
        accts += [_acct(600 + i, seen=old, email="s@tidewater-klatring.no") for i in range(5)]
        r, d = plan_purge_report(accts, TODAY)
        self.assertEqual((len(r), d), (200, []))

    def test_sorted_output(self):
        accts = [_acct(i, seen=_seen_for_due(0)) for i in range(201)]
        accts.append(_acct(-1, seen=TODAY, closed_at=TODAY - _dt.timedelta(days=40)))
        accts.append(_acct(300, seen=_seen_for_due(4)))
        import random
        random.Random(1).shuffle(accts)
        ids = [x["account_id"] for x in plan_purge(accts, TODAY)]
        self.assertEqual(ids, sorted(ids))

    def test_iso_json_and_approver(self):
        accts = [_acct(1, seen=_seen_for_due(0)), _acct(2, seen=_seen_for_due(0), unpaid_invoices=1),
                 _acct(3, seen=_seen_for_due(2))]
        r = plan_purge(accts, TODAY)
        json.dumps(r)
        by = {x["account_id"]: x for x in r}
        self.assertEqual(by[1]["due"], TODAY.isoformat())
        self.assertEqual(by[3]["due"], (TODAY + _dt.timedelta(days=2)).isoformat())
        self.assertEqual(by[1]["approved_by"], "Þórdís Sveinbjörnsdóttir")
        self.assertEqual(by[2]["approved_by"], DPO_NAME)
        self.assertIsNone(by[3]["approved_by"])

    def test_none_last_seen(self):
        self.assertIsNone(_one(_acct(seen=None, last_login=D(2000, 1, 1))))
        r = _one(_acct(seen=None, closed_at=TODAY - _dt.timedelta(days=30)))
        self.assertEqual(r["action"], "delete")

    def test_no_mutation_and_tenant_ignored(self):
        import copy
        accts = [_acct(1, seen=_seen_for_due(0), tenant="x"), _acct(2, seen=_seen_for_due(3))]
        before = copy.deepcopy(accts)
        a = plan_purge(accts, TODAY)
        self.assertEqual(accts, before)
        for x in accts:
            x.pop("tenant", None)
        self.assertEqual(plan_purge(accts, TODAY), a)

    def test_missing_optional_keys(self):
        r = plan_purge([{"id": 1, "last_seen_at": _seen_for_due(0)}], TODAY)
        self.assertEqual(r[0]["action"], "delete")


if __name__ == "__main__":
    unittest.main()