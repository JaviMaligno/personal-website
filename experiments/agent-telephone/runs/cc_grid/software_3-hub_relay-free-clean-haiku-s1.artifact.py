# -*- coding: utf-8 -*-
"""Tidewater Climbing GDPR purge planner.

Pure planning function: no I/O, no network, no deletion, no anonymisation,
no email. Returns action dicts only. Member emails never appear in output
or in exception text.

Status: the tests at the bottom were written against the spec but have not
been executed in the authoring environment. No test results are claimed.

Assumptions:
- Ids are str or int; all ids in one run must share the same type.
- Staff domain check is case-insensitive after trimming whitespace.
- unpaid_invoices must be an int (bool rejected); otherwise ValueError.
- litigation_hold must be a bool when present; missing means False.
- last_seen_at and closed_at must be datetime.date, not datetime.datetime.
- closed_by is only validated when closed_at is set.

Open items for the client:
- Whether the delete cap should also cover anonymise (currently uncapped).
- How already-processed accounts are excluded; status is ignored here, so
  anonymised accounts would be re-anonymised each run unless the caller filters.
- Whether warnings should be deduplicated across runs (not done here).
"""

import datetime as _dt
import unittest

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200


def _is_date(value):
    return isinstance(value, _dt.date) and not isinstance(value, _dt.datetime)


def _fail(account_id, message):
    raise ValueError(f"account {account_id!r}: {message}")


def _validate(accounts, today):
    if not _is_date(today):
        raise TypeError("today must be a datetime.date (not datetime.datetime)")
    if not isinstance(accounts, (list, tuple)):
        raise TypeError("accounts must be a list")

    records = []
    seen = set()
    id_type = None
    for acc in accounts:
        if not isinstance(acc, dict):
            raise ValueError("each account must be a dict")

        aid = acc.get("id")
        if isinstance(aid, bool) or not isinstance(aid, (str, int)):
            raise ValueError(f"account id must be str or int, got {type(aid).__name__}")
        if id_type is None:
            id_type = type(aid)
        elif type(aid) is not id_type:
            _fail(aid, "id type differs from the other accounts")
        if aid in seen:
            _fail(aid, "duplicate id")
        seen.add(aid)

        email = acc.get("email")
        if not isinstance(email, str):
            _fail(aid, "email must be a string")

        last_seen = acc.get("last_seen_at")
        if not _is_date(last_seen):
            _fail(aid, "last_seen_at must be a datetime.date")

        closed_at = acc.get("closed_at")
        closed_by = acc.get("closed_by")
        if closed_at is not None:
            if not _is_date(closed_at):
                _fail(aid, "closed_at must be a datetime.date or None")
            if closed_by not in ("member", "staff"):
                _fail(aid, "closed_by must be 'member' or 'staff' when closed_at is set")

        unpaid = acc.get("unpaid_invoices")
        if isinstance(unpaid, bool) or not isinstance(unpaid, int):
            _fail(aid, "unpaid_invoices must be an integer")

        hold = acc.get("litigation_hold", False)
        if not isinstance(hold, bool):
            _fail(aid, "litigation_hold must be a boolean")

        records.append({
            "id": aid,
            "staff": email.strip().lower().endswith(STAFF_DOMAIN),
            "last_seen": last_seen,
            "closed_at": closed_at,
            "closed_by": closed_by,
            "unpaid": unpaid,
            "hold": hold,
        })
    return records


def plan_purge(accounts, today):
    records = _validate(accounts, today)
    warn_limit = today + _dt.timedelta(days=WARN_WINDOW_DAYS)

    planned = []
    for r in records:
        if r["staff"] or r["hold"]:
            continue

        due = r["last_seen"] + _dt.timedelta(days=INACTIVITY_DAYS)
        closed = r["closed_at"] is not None
        if closed:
            closed_due = r["closed_at"] + _dt.timedelta(days=CLOSED_GRACE_DAYS)
            due = min(due, closed_due)

        target = "anonymise" if r["unpaid"] > 0 else "delete"
        if due <= today:
            action = target
        elif due <= warn_limit:
            if closed and r["closed_by"] == "member":
                continue
            action = "warn"
        else:
            continue

        planned.append({"id": r["id"], "action": action, "due": due, "closed": closed})

    deletes = [p for p in planned if p["action"] == "delete"]
    others = [p for p in planned if p["action"] != "delete"]
    deletes.sort(key=lambda p: (0 if p["closed"] else 1, p["due"], p["id"]))
    chosen = others + deletes[:DELETE_CAP]
    chosen.sort(key=lambda p: p["id"])

    return [
        {
            "account_id": p["id"],
            "action": p["action"],
            "due": p["due"].isoformat(),
            "approved_by": None if p["action"] == "warn" else APPROVER,
        }
        for p in chosen
    ]


class PlanPurgeTests(unittest.TestCase):
    TODAY = _dt.date(2026, 10, 13)

    def acc(self, **kw):
        base = {
            "id": "a1",
            "email": "member@example.org",
            "status": "active",
            "last_seen_at": self.TODAY,
            "last_login": None,
            "closed_at": None,
            "closed_by": None,
            "unpaid_invoices": 0,
            "litigation_hold": False,
        }
        base.update(kw)
        return base

    def days(self, n):
        return self.TODAY + _dt.timedelta(days=n)

    def test_exact_730_days_deleted_today(self):
        out = plan_purge([self.acc(last_seen_at=self.days(-730))], self.TODAY)
        self.assertEqual(out, [{"account_id": "a1", "action": "delete",
                                "due": self.TODAY.isoformat(), "approved_by": APPROVER}])

    def test_one_day_less_warns(self):
        out = plan_purge([self.acc(last_seen_at=self.days(-729))], self.TODAY)
        self.assertEqual(out[0]["action"], "warn")
        self.assertEqual(out[0]["due"], self.days(1).isoformat())

    def test_outside_window_nothing(self):
        self.assertEqual(plan_purge([self.acc(last_seen_at=self.days(-715))], self.TODAY), [])

    def test_window_edge_inclusive(self):
        out = plan_purge([self.acc(last_seen_at=self.days(-716))], self.TODAY)
        self.assertEqual(out[0]["action"], "warn")
        self.assertEqual(out[0]["due"], self.days(14).isoformat())

    def test_closed_30_days_ago_deleted_despite_recent_activity(self):
        out = plan_purge([self.acc(closed_at=self.days(-30), closed_by="member")], self.TODAY)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], self.TODAY.isoformat())

    def test_earlier_inactivity_date_is_due(self):
        acc = self.acc(last_seen_at=self.days(-740), closed_at=self.days(-5), closed_by="staff")
        out = plan_purge([acc], self.TODAY)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], self.days(-10).isoformat())

    def test_unpaid_invoices_anonymise_with_same_due_and_approver(self):
        out = plan_purge([self.acc(last_seen_at=self.days(-730), unpaid_invoices=2)], self.TODAY)
        self.assertEqual(out, [{"account_id": "a1", "action": "anonymise",
                                "due": self.TODAY.isoformat(), "approved_by": APPROVER}])

    def test_litigation_hold_blocks_everything(self):
        overdue = self.acc(last_seen_at=self.days(-900), unpaid_invoices=2, litigation_hold=True)
        warning = self.acc(id="a2", last_seen_at=self.days(-729), litigation_hold=True)
        self.assertEqual(plan_purge([overdue, warning], self.TODAY), [])

    def test_staff_excluded_in_any_category(self):
        overdue = self.acc(email="  Ops@Tidewater-Klatring.NO ", last_seen_at=self.days(-900))
        warning = self.acc(id="a2", email="x@tidewater-klatring.no", last_seen_at=self.days(-729))
        self.assertEqual(plan_purge([overdue, warning], self.TODAY), [])

    def test_member_closed_in_window_not_warned_staff_closed_is(self):
        member = self.acc(closed_at=self.days(-25), closed_by="member")
        staff = self.acc(id="a2", closed_at=self.days(-25), closed_by="staff")
        self.assertEqual(plan_purge([member], self.TODAY), [])
        out = plan_purge([staff], self.TODAY)
        self.assertEqual(out, [{"account_id": "a2", "action": "warn",
                                "due": self.days(5).isoformat(), "approved_by": None}])

    def test_delete_cap_and_uncapped_anonymise(self):
        accounts = []
        for i in range(250):
            closed = i < 50
            accounts.append(self.acc(
                id=f"d{i:03d}",
                email=f"m{i}@example.org",
                last_seen_at=self.days(-800),
                closed_at=self.days(-40) if closed else None,
                closed_by="staff" if closed else None,
            ))
        for i in range(10):
            accounts.append(self.acc(id=f"z{i:03d}", email=f"z{i}@example.org",
                                     last_seen_at=self.days(-800), unpaid_invoices=1))
        out = plan_purge(accounts, self.TODAY)
        deletes = {r["account_id"] for r in out if r["action"] == "delete"}
        anon = [r for r in out if r["action"] == "anonymise"]
        self.assertEqual(deletes, {f"d{i:03d}" for i in range(200)})
        self.assertEqual(len(anon), 10)

    def test_no_email_in_output(self):
        out = plan_purge([self.acc(email="secret.member@example.org", last_seen_at=self.days(-730))],
                         self.TODAY)
        for row in out:
            for value in row.values():
                if isinstance(value, str):
                    self.assertNotIn("@", value)
                    self.assertNotIn("secret", value)

    def test_output_sorted_by_id(self):
        accounts = [self.acc(id=i, last_seen_at=self.days(-730)) for i in ["c", "a", "b"]]
        out = plan_purge(accounts, self.TODAY)
        self.assertEqual([r["account_id"] for r in out], ["a", "b", "c"])

    def test_duplicate_ids_raise(self):
        with self.assertRaises(ValueError):
            plan_purge([self.acc(id="x"), self.acc(id="x")], self.TODAY)

    def test_missing_last_seen_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([self.acc(last_seen_at=None)], self.TODAY)

    def test_invalid_closed_by_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([self.acc(closed_at=self.days(-1), closed_by="admin")], self.TODAY)

    def test_validation_is_all_or_nothing(self):
        with self.assertRaises(ValueError):
            plan_purge([self.acc(last_seen_at=self.days(-730)),
                        self.acc(id="a2", last_seen_at=None)], self.TODAY)

    def test_datetime_today_rejected(self):
        with self.assertRaises(TypeError):
            plan_purge([], _dt.datetime(2026, 10, 13))

    def test_empty_input(self):
        self.assertEqual(plan_purge([], self.TODAY), [])

    def test_last_login_has_no_effect(self):
        base = self.acc(last_seen_at=self.days(-729))
        other = dict(base, last_login=_dt.date(2000, 1, 1))
        self.assertEqual(plan_purge([base], self.TODAY), plan_purge([other], self.TODAY))


if __name__ == "__main__":
    unittest.main()