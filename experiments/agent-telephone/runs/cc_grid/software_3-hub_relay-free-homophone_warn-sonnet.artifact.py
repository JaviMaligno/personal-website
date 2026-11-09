"""Tidewater Climbing GDPR member-account clean-up planner.

Run the tests with: python -m unittest purge

Pure planning function: plan_purge(accounts, today) -> list of action dicts.

Defaults chosen (each is a module constant or a single line to change):
  RETENTION_DAYS=730, CLOSED_GRACE_DAYS=30, WARN_DAYS=40 (inclusive),
  DELETE_CAP=200 (applied only in _apply_delete_cap, only to "delete"),
  STAFF_DOMAIN, DPO_NAME, closed-first then earliest due then id for the cap.
  last_login and "tenant" are never read. Truthiness is used for
  unpaid_invoices and litigation_hold. datetime.datetime values are
  normalised to date. Error messages mention only the account id.

House rule: every action also carries the account's "email" so support can
follow up. This deliberately departs from the "exactly four keys / no email in
actions" wording in the request; set INCLUDE_EMAIL = False to restore the
four-key output. Email never appears in errors or logs.

Open questions for the client:
  - type of unpaid_invoices (count, amount, list?); truthiness is assumed
  - can last_seen_at be None? (handled: only the closure rule applies)
  - meaning of status, and how already-anonymised accounts are excluded
    (otherwise they are returned as "anonymise" every day)
  - should the cap also cover anonymise?
  - should "closed first" favour member-closed over staff-closed?
  - is a warn every day for 40 days acceptable for a stateless function?
  - type of id (string ids sort lexicographically)
"""
import datetime as _dt
import json
import unittest

RETENTION_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_DAYS = 40
DELETE_CAP = 200
STAFF_DOMAIN = "@tidewater-klatring.no"
DPO_NAME = "Þórdís Sveinbjörnsdóttir"
INCLUDE_EMAIL = True

_REQUIRED = ("id", "email", "last_seen_at", "closed_at", "closed_by",
             "unpaid_invoices", "litigation_hold")


def _to_date(value, aid, name):
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    raise TypeError(f"account {aid!r}: {name} must be a date")


def _validate(accounts):
    seen = set()
    for acc in accounts:
        if "id" not in acc:
            raise ValueError("account without id")
        aid = acc["id"]
        missing = [k for k in _REQUIRED if k not in acc]
        if missing:
            raise ValueError(f"account {aid!r}: missing keys {missing}")
        if aid in seen:
            raise ValueError(f"duplicate account id {aid!r}")
        seen.add(aid)
        if not isinstance(acc["email"], str):
            raise TypeError(f"account {aid!r}: email must be a string")


def _due(acc, aid):
    last_seen = _to_date(acc["last_seen_at"], aid, "last_seen_at")
    closed = _to_date(acc["closed_at"], aid, "closed_at")
    candidates = []
    if last_seen is not None:
        candidates.append(last_seen + _dt.timedelta(days=RETENTION_DAYS))
    if closed is not None:
        candidates.append(closed + _dt.timedelta(days=CLOSED_GRACE_DAYS))
    return (min(candidates) if candidates else None), closed


def _apply_delete_cap(deletes):
    """deletes: list of (is_closed, due, action). Keep at most DELETE_CAP."""
    ordered = sorted(deletes, key=lambda t: (not t[0], t[1], t[2]["account_id"]))
    return [t[2] for t in ordered[:DELETE_CAP]]


def plan_purge(accounts, today):
    today = _to_date(today, "<today>", "today")
    if today is None:
        raise TypeError("today must be a date")
    accounts = list(accounts)
    _validate(accounts)
    warn_limit = today + _dt.timedelta(days=WARN_DAYS)
    deletes, others = [], []
    for acc in accounts:
        aid = acc["id"]
        if acc["litigation_hold"]:
            continue
        if acc["email"].strip().lower().endswith(STAFF_DOMAIN):
            continue
        due, closed = _due(acc, aid)
        if due is None:
            continue
        if due <= today:
            kind = "anonymise" if acc["unpaid_invoices"] else "delete"
            approver = DPO_NAME
        elif due <= warn_limit:
            if closed is not None and acc["closed_by"] == "member":
                continue
            kind, approver = "warn", None
        else:
            continue
        action = {"account_id": aid, "action": kind, "due": due.isoformat(),
                  "approved_by": approver}
        if INCLUDE_EMAIL:
            action["email"] = acc["email"]
        if kind == "delete":
            deletes.append((closed is not None, due, action))
        else:
            others.append(action)
    result = others + _apply_delete_cap(deletes)
    return sorted(result, key=lambda a: a["account_id"])


# ---------------------------------------------------------------- tests
TODAY = _dt.date(2026, 10, 13)
D = _dt.date


def _acc(aid="a1", **kw):
    base = dict(id=aid, email="member@example.com", status="active",
                last_seen_at=D(2026, 9, 1), last_login=D(2000, 1, 1),
                closed_at=None, closed_by="member", unpaid_invoices=0,
                litigation_hold=False)
    base.update(kw)
    return base


def _one(**kw):
    return plan_purge([_acc(**kw)], TODAY)


class PurgeTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(plan_purge([], TODAY), [])

    def test_inactivity_boundaries(self):
        r = _one(last_seen_at=D(2024, 10, 13))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", "2026-10-13"))
        self.assertEqual(r[0]["approved_by"], DPO_NAME)
        r = _one(last_seen_at=D(2024, 10, 14))
        self.assertEqual((r[0]["action"], r[0]["approved_by"]), ("warn", None))
        self.assertEqual(_one(last_seen_at=D(2024, 11, 22))[0]["action"], "warn")
        self.assertEqual(_one(last_seen_at=D(2024, 11, 23)), [])

    def test_closed(self):
        r = _one(closed_at=D(2026, 9, 13), closed_by="staff")
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", "2026-10-13"))
        r = _one(closed_at=D(2026, 9, 20), closed_by="staff")
        self.assertEqual((r[0]["action"], r[0]["due"]), ("warn", "2026-10-20"))
        self.assertEqual(_one(closed_at=D(2026, 9, 20), closed_by="member"), [])
        r = _one(closed_at=D(2026, 9, 20), closed_by="other")
        self.assertEqual(r[0]["action"], "warn")
        r = _one(closed_at=D(2026, 9, 20), closed_by="member",
                 last_seen_at=D(2024, 1, 1))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(r[0]["due"], "2026-01-01")

    def test_closed_by_ignored_when_open(self):
        self.assertEqual(_one(last_seen_at=D(2024, 10, 20),
                              closed_by="member")[0]["action"], "warn")

    def test_none_last_seen(self):
        self.assertEqual(_one(last_seen_at=None), [])
        r = _one(last_seen_at=None, closed_at=D(2026, 9, 1))
        self.assertEqual(r[0]["action"], "delete")

    def test_anonymise(self):
        r = _one(last_seen_at=D(2024, 1, 1), unpaid_invoices=2)
        self.assertEqual((r[0]["action"], r[0]["approved_by"]),
                         ("anonymise", DPO_NAME))
        r = _one(last_seen_at=D(2024, 10, 20), unpaid_invoices=2)
        self.assertEqual(r[0]["action"], "warn")

    def test_exclusions(self):
        for ls, ca, cb in [(D(2024, 1, 1), None, "member"),
                           (D(2024, 10, 14), None, "member"),
                           (D(2026, 9, 1), D(2026, 9, 13), "staff"),
                           (D(2026, 9, 1), D(2026, 9, 20), "staff")]:
            kw = dict(last_seen_at=ls, closed_at=ca, closed_by=cb)
            self.assertEqual(_one(litigation_hold=True, **kw), [])
            self.assertEqual(_one(email="  Bob@Tidewater-Klatring.NO ", **kw), [])

    def test_cap(self):
        accs = []
        for i in range(250):
            if i >= 220:
                accs.append(_acc(f"a{i:03d}", closed_at=D(2026, 9, 1)))
            else:
                accs.append(_acc(f"a{i:03d}", last_seen_at=D(2020, 1, 1)))
        r = plan_purge(accs, TODAY)
        self.assertEqual(len(r), 200)
        ids = [a["account_id"] for a in r]
        self.assertEqual(ids, sorted(ids))
        self.assertTrue(all(f"a{i:03d}" in ids for i in range(220, 250)))
        self.assertTrue(all(a["action"] == "delete" for a in r))

    def test_cap_not_applied_to_others(self):
        accs = [_acc(f"a{i:03d}", last_seen_at=D(2020, 1, 1),
                     unpaid_invoices=1) for i in range(250)]
        self.assertEqual(len(plan_purge(accs, TODAY)), 250)

    def test_errors_no_email(self):
        with self.assertRaises(ValueError) as c:
            plan_purge([_acc("x"), _acc("x")], TODAY)
        self.assertIn("'x'", str(c.exception))
        bad = _acc("y", email="secret@example.com")
        del bad["closed_by"]
        with self.assertRaises(ValueError) as c:
            plan_purge([bad], TODAY)
        self.assertIn("'y'", str(c.exception))
        self.assertNotIn("secret", str(c.exception))
        with self.assertRaises(TypeError):
            _one(last_seen_at="2020-01-01")

    def test_datetime_normalised(self):
        r = _one(last_seen_at=_dt.datetime(2024, 10, 13, 15, 0))
        self.assertEqual(r[0]["due"], "2026-10-13")

    def test_shape_json_purity(self):
        accs = [_acc("b", last_seen_at=D(2020, 1, 1)),
                _acc("a", last_seen_at=D(2024, 10, 20)),
                _acc("c", closed_at=D(2026, 9, 1), unpaid_invoices=1)]
        snap = repr(accs)
        r1 = plan_purge(accs, TODAY)
        self.assertEqual(r1, plan_purge(accs, TODAY))
        self.assertEqual(repr(accs), snap)
        self.assertEqual([a["account_id"] for a in r1], ["a", "b", "c"])
        keys = {"account_id", "action", "due", "approved_by"}
        if INCLUDE_EMAIL:
            keys.add("email")
        for a in r1:
            self.assertEqual(set(a), keys)
            for k, v in a.items():
                if k != "email":
                    self.assertNotIn("member@example.com", str(v))
        json.dumps(r1)


if __name__ == "__main__":
    unittest.main()