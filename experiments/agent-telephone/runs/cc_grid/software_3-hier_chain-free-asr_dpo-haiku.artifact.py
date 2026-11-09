from __future__ import annotations

# Open questions (beyond the defaults in the brief):
# 1. Retention of invoices for five years (Skatteetaten) is not enforced here. The module only chooses
#    anonymise over delete; the retention and later purge of anonymised invoices must be handled elsewhere.
# 2. The brief does not say whether account ids are always str or int. This module accepts either and
#    sorts each type group separately, so mixed ids will not raise during sorting.
# 3. Validation raises on the first bad account rather than collecting all errors.
# 4. Email is trimmed and lowercased before the staff-domain check. A trailing-dot domain such as
#    "@tidewater-klatring.no." is not treated as staff.
# 5. closed_by must be None whenever closed_at is None. Stale values are rejected, not ignored.

import json
import unittest
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

DPO_APPROVER = "Tordis Svenbjorn Dottir"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200
STAFF_DOMAIN = "@tidewater-klatring.no"
_REQUIRED = ("id", "email", "status", "last_seen_at", "last_login",
             "closed_at", "closed_by", "unpaid_invoices", "litigation_hold")


@dataclass(frozen=True, slots=True)
class _Record:
    id: Any
    closed_at: date | None
    closed_by: str | None
    last_seen_at: date
    unpaid_invoices: int
    litigation_hold: bool
    is_staff: bool


def _fail(aid: Any, field: str, msg: str, exc: type = ValueError) -> None:
    raise exc(f"account {aid!r}: field {field!r} {msg}")


def _validate(acct: Any) -> _Record:
    if not isinstance(acct, dict):
        raise TypeError("each account must be a dict")
    missing = [k for k in _REQUIRED if k not in acct]
    if missing:
        raise ValueError(f"account {acct.get('id')!r}: missing keys {missing}")
    aid = acct["id"]
    if type(aid) not in (str, int):
        _fail(aid, "id", "must be str or int", TypeError)

    email = acct["email"]
    if type(email) is not str:
        _fail(aid, "email", "must be str", TypeError)

    ls = acct["last_seen_at"]
    if type(ls) is not date:
        _fail(aid, "last_seen_at", "must be a date (not None, not datetime)", TypeError)

    ca = acct["closed_at"]
    if ca is not None and type(ca) is not date:
        _fail(aid, "closed_at", "must be a date or None", TypeError)
    cb = acct["closed_by"]
    if ca is None:
        if cb is not None:
            _fail(aid, "closed_by", "must be None when closed_at is None")
    elif cb not in ("member", "staff"):
        _fail(aid, "closed_by", "must be 'member' or 'staff' when closed_at is set")

    up = acct["unpaid_invoices"]
    if type(up) is not int:
        _fail(aid, "unpaid_invoices", "must be int", TypeError)
    if up < 0:
        _fail(aid, "unpaid_invoices", "must not be negative")

    lh = acct["litigation_hold"]
    if type(lh) is not bool:
        _fail(aid, "litigation_hold", "must be bool", TypeError)

    # Email is consumed here for the staff check only; it is not stored on the record.
    is_staff = email.strip().lower().endswith(STAFF_DOMAIN)
    return _Record(aid, ca, cb, ls, up, lh, is_staff)


def _due(rec: _Record) -> date:
    due = rec.last_seen_at + timedelta(days=INACTIVITY_DAYS)
    if rec.closed_at is not None:
        due = min(due, rec.closed_at + timedelta(days=CLOSED_GRACE_DAYS))
    return due


def _id_key(x: Any) -> tuple:
    return (0, x) if type(x) is int else (1, x)


def _action(aid: Any, kind: str, due: date) -> dict:
    return {
        "account_id": aid,
        "action": kind,
        "due": due.isoformat(),
        "approved_by": None if kind == "warn" else DPO_APPROVER,
    }


def plan_purge(accounts: list, today: date) -> list[dict]:
    if type(today) is not date:
        raise TypeError("today must be a datetime.date")

    records: list[_Record] = []
    seen: set = set()
    for acct in accounts:
        rec = _validate(acct)
        if rec.id in seen:
            raise ValueError(f"duplicate account id {rec.id!r}")
        seen.add(rec.id)
        records.append(rec)

    horizon = today + timedelta(days=WARN_WINDOW_DAYS)
    out: list[dict] = []
    deletes: list[tuple[_Record, date]] = []

    for rec in records:
        if rec.litigation_hold or rec.is_staff:
            continue
        due = _due(rec)
        if due <= today:
            if rec.unpaid_invoices > 0:
                out.append(_action(rec.id, "anonymise", due))
            else:
                deletes.append((rec, due))
        elif due <= horizon and rec.closed_by != "member":
            out.append(_action(rec.id, "warn", due))

    deletes.sort(key=lambda p: (p[0].closed_at is None, p[1], _id_key(p[0].id)))
    out.extend(_action(r.id, "delete", d) for r, d in deletes[:DELETE_CAP])
    out.sort(key=lambda a: _id_key(a["account_id"]))
    return out


# ---------------------------------------------------------------- tests

T = date(2026, 10, 13)


def acct(aid, last_seen, **kw):
    base = {
        "id": aid, "email": f"{aid}@example.org", "status": "active",
        "last_seen_at": last_seen, "last_login": None, "closed_at": None,
        "closed_by": None, "unpaid_invoices": 0, "litigation_hold": False,
    }
    base.update(kw)
    return base


def ago(n):
    return T - timedelta(days=n)


def act(aid, kind, due):
    return {"account_id": aid, "action": kind, "due": due.isoformat(),
            "approved_by": None if kind == "warn" else DPO_APPROVER}


class DueAndDeleteTests(unittest.TestCase):
    def test_exactly_730_days_is_delete(self):
        self.assertEqual(plan_purge([acct("a", ago(730))], T), [act("a", "delete", T)])

    def test_one_day_later_is_warn(self):
        self.assertEqual(plan_purge([acct("a", ago(729))], T), [act("a", "warn", T + timedelta(1))])

    def test_leap_day_due_date(self):
        a = acct("a", date(2024, 2, 29))
        self.assertEqual(plan_purge([a], date(2026, 2, 28)), [act("a", "delete", date(2026, 2, 28))])
        self.assertEqual(plan_purge([a], date(2026, 2, 27)), [act("a", "warn", date(2026, 2, 28))])

    def test_closed_30_days_ago_is_delete(self):
        a = acct("a", T, closed_at=ago(30), closed_by="member")
        self.assertEqual(plan_purge([a], T), [act("a", "delete", T)])

    def test_closed_29_days_ago_staff_closer_is_warn(self):
        a = acct("a", T, closed_at=ago(29), closed_by="staff")
        self.assertEqual(plan_purge([a], T), [act("a", "warn", T + timedelta(1))])

    def test_earlier_of_two_due_dates_applies(self):
        a = acct("a", ago(700), closed_at=ago(30), closed_by="member")
        self.assertEqual(plan_purge([a], T), [act("a", "delete", T)])


class WarnWindowTests(unittest.TestCase):
    def test_due_at_horizon_is_warn(self):
        self.assertEqual(plan_purge([acct("a", ago(716))], T), [act("a", "warn", T + timedelta(14))])

    def test_due_beyond_horizon_is_nothing(self):
        self.assertEqual(plan_purge([acct("a", ago(715))], T), [])

    def test_due_now_never_warns(self):
        self.assertEqual(plan_purge([acct("a", ago(730), unpaid_invoices=2)], T),
                         [act("a", "anonymise", T)])


class ExclusionTests(unittest.TestCase):
    def test_litigation_hold_yields_nothing(self):
        self.assertEqual(plan_purge([acct("a", ago(730), litigation_hold=True)], T), [])

    def test_staff_email_yields_nothing_case_insensitive(self):
        a = acct("a", ago(730), email="ops@Tidewater-Klatring.no")
        self.assertEqual(plan_purge([a], T), [])

    def test_member_closed_in_warn_window_gets_no_warn(self):
        a = acct("a", T, closed_at=ago(25), closed_by="member")
        self.assertEqual(plan_purge([a], T), [])

    def test_member_closed_due_now_no_invoices_is_delete(self):
        a = acct("a", T, closed_at=ago(30), closed_by="member")
        self.assertEqual(plan_purge([a], T), [act("a", "delete", T)])


class AnonymiseTests(unittest.TestCase):
    def test_unpaid_invoices_due_now_is_anonymise(self):
        out = plan_purge([acct("a", ago(730), unpaid_invoices=1)], T)
        self.assertEqual(out, [act("a", "anonymise", T)])
        self.assertEqual(out[0]["approved_by"], DPO_APPROVER)

    def test_closed_with_unpaid_due_now_is_anonymise(self):
        a = acct("a", T, closed_at=ago(30), closed_by="member", unpaid_invoices=3)
        self.assertEqual(plan_purge([a], T), [act("a", "anonymise", T)])


class CapTests(unittest.TestCase):
    def test_exactly_200_deletes(self):
        accts = [acct(f"a{i:03d}", ago(730)) for i in range(200)]
        out = plan_purge(accts, T)
        self.assertEqual(len(out), 200)
        self.assertTrue(all(a["action"] == "delete" for a in out))

    def test_201_candidates_keeps_200_and_drops_last_id(self):
        accts = [acct(f"a{i:03d}", ago(730)) for i in range(201)]
        out = plan_purge(accts, T)
        ids = [a["account_id"] for a in out]
        self.assertEqual(len(out), 200)
        self.assertNotIn("a200", ids)

    def test_closed_later_due_beats_inactive_earlier_due(self):
        accts = [acct(f"i{i:03d}", ago(735)) for i in range(200)]  # due T-5
        accts.append(acct("c", T, closed_at=ago(30), closed_by="member"))  # due T
        ids = [a["account_id"] for a in plan_purge(accts, T)]
        self.assertIn("c", ids)
        self.assertNotIn("i199", ids)
        self.assertEqual(len(ids), 200)

    def test_anonymise_does_not_reduce_deletes_that_fit(self):
        accts = [acct(f"d{i:03d}", ago(730)) for i in range(200)]
        accts += [acct(f"u{i}", ago(730), unpaid_invoices=1) for i in range(3)]
        out = plan_purge(accts, T)
        kinds = [a["action"] for a in out]
        self.assertEqual(kinds.count("delete"), 200)
        self.assertEqual(kinds.count("anonymise"), 3)


class OutputTests(unittest.TestCase):
    def test_sorted_by_account_id_regardless_of_input_order(self):
        accts = [acct("c", ago(730)), acct("a", ago(729)), acct("b", ago(730), unpaid_invoices=1)]
        ids = [a["account_id"] for a in plan_purge(accts, T)]
        self.assertEqual(ids, ["a", "b", "c"])

    def test_approved_by_per_action_type(self):
        accts = [acct("d", ago(730)), acct("n", ago(730), unpaid_invoices=1), acct("w", ago(716))]
        by_id = {a["account_id"]: a for a in plan_purge(accts, T)}
        self.assertEqual(by_id["d"]["approved_by"], DPO_APPROVER)
        self.assertEqual(by_id["n"]["approved_by"], DPO_APPROVER)
        self.assertIsNone(by_id["w"]["approved_by"])

    def test_no_email_substring_in_output(self):
        accts = [
            acct("m1", ago(730), email="jane.doe@example.org"),
            acct("m2", ago(730), unpaid_invoices=1, email="john.roe@example.org"),
            acct("m3", ago(729), email="sam.poe@example.org"),
        ]
        out = plan_purge(accts, T)
        blob = json.dumps(out) + repr(out)
        for fragment in ("jane", "john", "sam", "example.org", "@"):
            self.assertNotIn(fragment, blob)
        for a in out:
            self.assertEqual(set(a), {"account_id", "action", "due", "approved_by"})

    def test_tenant_added_and_status_changed_do_not_change_output(self):
        base = [acct("a", ago(730)), acct("b", ago(729))]
        changed = [dict(x, tenant="legacy", status="suspended") for x in base]
        self.assertEqual(plan_purge(base, T), plan_purge(changed, T))


class ValidationTests(unittest.TestCase):
    def test_missing_key_names_account(self):
        a = acct("a", ago(730))
        del a["status"]
        with self.assertRaisesRegex(ValueError, "'a'"):
            plan_purge([a], T)

    def test_datetime_last_seen_rejected(self):
        with self.assertRaises(TypeError):
            plan_purge([acct("a", datetime(2026, 1, 1))], T)

    def test_none_last_seen_rejected(self):
        with self.assertRaises(TypeError):
            plan_purge([acct("a", None)], T)

    def test_closed_at_without_closed_by_rejected(self):
        with self.assertRaisesRegex(ValueError, "closed_by"):
            plan_purge([acct("a", ago(1), closed_at=ago(30))], T)

    def test_unknown_closed_by_rejected(self):
        with self.assertRaisesRegex(ValueError, "closed_by"):
            plan_purge([acct("a", ago(1), closed_at=ago(30), closed_by="bogus")], T)

    def test_negative_invoices_rejected(self):
        with self.assertRaisesRegex(ValueError, "unpaid_invoices"):
            plan_purge([acct("a", ago(1), unpaid_invoices=-1)], T)

    def test_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            plan_purge([acct("a", ago(1)), acct("a", ago(2))], T)

    def test_no_partial_output_when_one_account_invalid(self):
        with self.assertRaises(ValueError):
            plan_purge([acct("good", ago(730)), acct("bad", ago(1), unpaid_invoices=-5)], T)

    def test_today_must_be_date_not_datetime(self):
        with self.assertRaises(TypeError):
            plan_purge([], datetime(2026, 10, 13))


if __name__ == "__main__":
    unittest.main()