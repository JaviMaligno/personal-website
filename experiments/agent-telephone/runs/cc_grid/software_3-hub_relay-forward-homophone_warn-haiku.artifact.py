"""GDPR purge planner for Tidewater Climbing member accounts.

Single entry point: plan_purge(accounts, today). Pure function: no I/O, no logging, no mutation of input.
The unittest cases at the bottom of this module were written but NOT executed. Run: python3 -I this_file.py

OPEN DECISIONS (defaults implemented, client to confirm):
1. Deferred over-cap deletes are not reported to the caller. They are silently left out of the output.
2. "Closed first" means any closure (closed_at is set), not member-only closure.
3. Only unpaid invoices trigger anonymise. Paid invoices, and the five-year Skatteetaten retention, are not considered; accounts with paid invoices are deleted.
4. Anonymise does not count toward the 200-delete cap.
5. Warn boundary is inclusive at today + 40 days.
6. The module is stateless, so the same account produces the same warn or action on every daily run until it changes state. Warnings repeat daily.
7. Warnings are emitted for unpaid-invoice accounts that are due in the future. The brief's note that they are "not reached" is wrong for future-due accounts; the warn rule is implemented as stated. No warning wording is produced.
8. "Closed" is defined as closed_at is not None. The status field is not used to define closure.
9. Invalid input raises ValueError (it is not skipped). Error messages name only the account id, never the email.
10. CONFLICT: the team house rule asks that every action dict carry the account's email. The client brief and tech lead forbid any member email in output, because the audit log is shared with the climbing federation. This module follows the brief and omits email from every key. Needs explicit sign-off.

Ignored by design: tenant, last_login.
"""

import copy
import datetime as _dt
import unittest
from collections.abc import Mapping

DPO_APPROVER = "Þórdís Sveinbjörnsdóttir"
DELETE_CAP = 200
WARN_DAYS = 40
INACTIVE_DAYS = 730
CLOSED_DAYS = 30
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"
_REQUIRED_FIELDS = (
    "id",
    "email",
    "status",
    "last_seen_at",
    "closed_at",
    "closed_by",
    "unpaid_invoices",
    "litigation_hold",
)


def _is_date(value):
    return isinstance(value, _dt.date) and not isinstance(value, _dt.datetime)


def _validate(account, index):
    if not isinstance(account, Mapping):
        raise ValueError(f"account at index {index} is not a mapping")
    acc_id = account.get("id")
    if not isinstance(acc_id, str) or not acc_id:
        raise ValueError(f"account at index {index}: field 'id' missing or invalid")
    label = repr(acc_id)

    def bad(field):
        return ValueError(f"account {label}: field '{field}' missing or invalid")

    for field in _REQUIRED_FIELDS:
        if field not in account:
            raise bad(field)
    if not isinstance(account["email"], str):
        raise bad("email")
    if not isinstance(account["status"], str):
        raise bad("status")

    last_seen = account["last_seen_at"]
    closed_at = account["closed_at"]
    closed_by = account["closed_by"]
    unpaid = account["unpaid_invoices"]
    hold = account["litigation_hold"]

    if not _is_date(last_seen):
        raise bad("last_seen_at")
    if closed_at is not None and not _is_date(closed_at):
        raise bad("closed_at")
    if closed_at is None:
        if closed_by is not None:
            raise bad("closed_by")
    elif closed_by not in ("member", "staff"):
        raise bad("closed_by")
    if not isinstance(unpaid, (bool, int)):
        raise bad("unpaid_invoices")
    if not isinstance(hold, bool):
        raise bad("litigation_hold")

    try:
        due = last_seen + _dt.timedelta(days=INACTIVE_DAYS)
        if closed_at is not None:
            due = min(due, closed_at + _dt.timedelta(days=CLOSED_DAYS))
    except OverflowError:
        raise bad("last_seen_at") from None

    return {
        "id": acc_id,
        "staff": account["email"].strip().lower().endswith(STAFF_EMAIL_SUFFIX),
        "hold": hold,
        "unpaid": bool(unpaid),
        "closed_at": closed_at,
        "closed_by": closed_by,
        "due": due,
    }


def _action(row, action, due, approved_by):
    return {
        "account_id": row["id"],
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    if not _is_date(today):
        raise ValueError("today must be a datetime.date")

    rows = []
    seen = set()
    for index, account in enumerate(accounts):
        row = _validate(account, index)
        if row["id"] in seen:
            raise ValueError(f"duplicate account id {row['id']!r}")
        seen.add(row["id"])
        rows.append(row)

    horizon = today + _dt.timedelta(days=WARN_DAYS)
    actions = []
    deletions = []

    for row in rows:
        if row["hold"] or row["staff"]:
            continue
        due = row["due"]
        if due <= today:
            if row["unpaid"]:
                actions.append(_action(row, "anonymise", due, DPO_APPROVER))
            else:
                deletions.append(row)
        elif due <= horizon and row["closed_by"] != "member":
            actions.append(_action(row, "warn", due, None))

    # Closed accounts first, then earliest due, then account id as tiebreak.
    deletions.sort(key=lambda r: (r["closed_at"] is None, r["due"], r["id"]))
    for row in deletions[:DELETE_CAP]:
        actions.append(_action(row, "delete", row["due"], DPO_APPROVER))

    actions.sort(key=lambda a: a["account_id"])
    return actions


# ---------------------------------------------------------------------------
# Tests (not executed when this file was written)
# ---------------------------------------------------------------------------

TODAY = _dt.date(2026, 10, 13)
EMAIL = "member.one@example.com"


def _acct(acc_id="a1", **overrides):
    base = {
        "id": acc_id,
        "email": EMAIL,
        "status": "active",
        "last_seen_at": _dt.date(2026, 1, 1),
        "last_login": _dt.date(2019, 1, 1),
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
    }
    base.update(overrides)
    return base


class PlanPurgeTests(unittest.TestCase):
    def plan(self, *accounts):
        return plan_purge(list(accounts), TODAY)

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(plan_purge([], TODAY), [])

    def test_active_inactive_due_today_gets_delete(self):
        out = self.plan(_acct(last_seen_at=_dt.date(2024, 10, 13)))
        self.assertEqual(out, [{
            "account_id": "a1",
            "action": "delete",
            "due": "2026-10-13",
            "approved_by": DPO_APPROVER,
        }])

    def test_due_tomorrow_gets_warn_with_none_approver(self):
        out = self.plan(_acct(last_seen_at=_dt.date(2024, 10, 14)))
        self.assertEqual(out, [{
            "account_id": "a1",
            "action": "warn",
            "due": "2026-10-14",
            "approved_by": None,
        }])

    def test_warn_boundary_inclusive_at_40_days(self):
        last_seen = _dt.date(2026, 11, 22) - _dt.timedelta(days=730)
        out = self.plan(_acct(last_seen_at=last_seen))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "warn")
        self.assertEqual(out[0]["due"], "2026-11-22")

    def test_no_action_one_day_past_40_day_window(self):
        last_seen = _dt.date(2026, 11, 23) - _dt.timedelta(days=730)
        self.assertEqual(self.plan(_acct(last_seen_at=last_seen)), [])

    def test_member_closed_gets_no_warning(self):
        out = self.plan(_acct(closed_at=_dt.date(2026, 9, 20), closed_by="member"))
        self.assertEqual(out, [])

    def test_staff_closed_gets_warning_with_closed_due(self):
        out = self.plan(_acct(closed_at=_dt.date(2026, 9, 20), closed_by="staff"))
        self.assertEqual(out, [{
            "account_id": "a1",
            "action": "warn",
            "due": "2026-10-20",
            "approved_by": None,
        }])

    def test_unpaid_invoices_past_due_gets_anonymise(self):
        out = self.plan(_acct(last_seen_at=_dt.date(2024, 1, 1), unpaid_invoices=2))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "anonymise")
        self.assertEqual(out[0]["approved_by"], DPO_APPROVER)

    def test_litigation_hold_no_action_including_warn(self):
        self.assertEqual(
            self.plan(_acct(last_seen_at=_dt.date(2024, 10, 13), litigation_hold=True)),
            [],
        )
        self.assertEqual(
            self.plan(_acct(closed_at=_dt.date(2026, 9, 20), closed_by="staff",
                            litigation_hold=True)),
            [],
        )

    def test_staff_email_no_action(self):
        out = self.plan(_acct(email="  Ops@Tidewater-Klatring.NO ",
                              last_seen_at=_dt.date(2024, 10, 13)))
        self.assertEqual(out, [])

    def test_delete_cap_200_closed_first_and_sorted(self):
        accts = []
        closed_ids = []
        for i in range(60):
            cid = f"c{i:03d}"
            closed_ids.append(cid)
            accts.append(_acct(cid, last_seen_at=_dt.date(2026, 6, 1),
                               closed_at=_dt.date(2026, 9, 13), closed_by="staff"))
        for i in range(190):
            accts.append(_acct(f"a{i:03d}", last_seen_at=_dt.date(2024, 9, 1)))
        out = plan_purge(accts, TODAY)
        deletes = [a for a in out if a["action"] == "delete"]
        self.assertEqual(len(deletes), 200)
        self.assertEqual(len(out), 200)
        delete_ids = {a["account_id"] for a in deletes}
        self.assertTrue(set(closed_ids) <= delete_ids)
        ids = [a["account_id"] for a in out]
        self.assertEqual(ids, sorted(ids))

    def test_output_never_contains_email(self):
        accts = [
            _acct("a1", email="secret.member@example.com",
                  last_seen_at=_dt.date(2024, 10, 13)),
            _acct("a2", email="other.member@example.com",
                  last_seen_at=_dt.date(2024, 10, 14)),
        ]
        out = self.plan(*accts)
        self.assertTrue(out)
        self.assertNotIn("@", repr(out))
        self.assertNotIn("secret", repr(out))

    def test_due_values_are_iso_dates(self):
        out = self.plan(
            _acct("a1", last_seen_at=_dt.date(2024, 10, 13)),
            _acct("a2", last_seen_at=_dt.date(2024, 10, 14)),
        )
        self.assertEqual(len(out), 2)
        for action in out:
            self.assertRegex(action["due"], r"^\d{4}-\d{2}-\d{2}$")

    def test_input_not_mutated(self):
        accts = [_acct("a1", last_seen_at=_dt.date(2024, 10, 13)),
                 _acct("a2", closed_at=_dt.date(2026, 9, 20), closed_by="staff")]
        snapshot = copy.deepcopy(accts)
        plan_purge(accts, TODAY)
        self.assertEqual(accts, snapshot)

    def test_missing_field_error_names_only_id(self):
        acct = _acct("a9", email="leak.me@example.com")
        del acct["closed_at"]
        with self.assertRaises(ValueError) as cm:
            plan_purge([acct], TODAY)
        message = str(cm.exception)
        self.assertIn("a9", message)
        self.assertNotIn("leak", message)

    def test_invalid_field_error_has_no_email(self):
        acct = _acct("a7", email="leak.me@example.com", unpaid_invoices="yes")
        with self.assertRaises(ValueError) as cm:
            plan_purge([acct], TODAY)
        self.assertIn("a7", str(cm.exception))
        self.assertNotIn("leak", str(cm.exception))

    def test_today_must_be_date_not_datetime(self):
        with self.assertRaises(ValueError):
            plan_purge([], _dt.datetime(2026, 10, 13))

    def test_duplicate_account_id_rejected(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct("x"), _acct("x")], TODAY)


if __name__ == "__main__":
    unittest.main()