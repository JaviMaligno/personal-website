"""GDPR purge planner for Tidewater Climbing member accounts.

plan_purge(accounts, today) returns the purge actions for one run. It is pure:
it deletes, anonymises and notifies nothing itself. Output and log lines carry
account ids only, never email addresses.

Rules
- last_seen_at is the only inactivity signal. last_login is ignored.
- due = last_seen_at + 730 days. If closed_at is set, due = min(that, closed_at + 30 days).
- Classification, first match wins:
  1. Excluded, no action: litigation_hold is truthy, or email ends with
     "@tidewater-klatring.no" (case-insensitive).
  2. due <= today: "anonymise" if the account has unpaid invoices, else "delete"
     (subject to the cap).
  3. today < due <= today + 14 days: "warn", unless closed_at is set and
     closed_by == "member".
- Cap: at most 200 "delete" actions per run. "anonymise" is not capped.
  Overflow deletes are ranked closed-first (closed_at set), then by due ascending,
  then by account id. Overflow accounts get no action this run.
- approved_by is the DPO for delete and anonymise, None for warn.
- Output: list of dicts with exactly the keys account_id, action, due (ISO string),
  approved_by, sorted by account_id.

Open questions. Defaults below follow the PM's recommendations and need client confirmation.
- Idempotency: an account with status "anonymised" is treated as already processed
  and gets no further anonymise action. The status value is an assumption.
- Overflow beyond the cap is silently omitted. No overflow count is returned.
- Warn window is inclusive of day 14 (due <= today + 14 days).
- Accounts with unpaid invoices are warned like any other account.
- "Closed" for cap ordering means closed_at is set, whatever closed_by says.
- approved_by for warn is None.
- Staff domain match is case-insensitive.

Bad-data policy
- last_seen_at is None: account skipped with no action, logged by id.
- closed_by set but closed_at is None: treated as not closed, logged by id.
- closed_by not in {"member", "staff"}: not treated as member-closed, so warn applies. Logged by id.
- unpaid_invoices: None, False or 0 means no unpaid invoices. True or a positive int
  means unpaid. Any other type raises ValueError naming the id only.
- Duplicate ids: raise ValueError naming the id. The whole run fails.

Out of scope: deleting invoices after the five-year retention period.
"""

from __future__ import annotations

import logging
import unittest
from datetime import date, timedelta

__all__ = ["plan_purge"]

log = logging.getLogger(__name__)

DPO = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_CAP = 200
INACTIVITY = timedelta(days=730)
CLOSED_GRACE = timedelta(days=30)
WARN_WINDOW = timedelta(days=14)
ANONYMISED_STATUS = "anonymised"


def _is_staff(acc: dict) -> bool:
    email = acc.get("email")
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def _has_unpaid(acc: dict, account_id) -> bool:
    value = acc.get("unpaid_invoices")
    if value is None or value is False:
        return False
    if value is True:
        return True
    if isinstance(value, int):
        return value > 0
    raise ValueError(
        f"account {account_id!r}: unpaid_invoices has unsupported type {type(value).__name__}"
    )


def _action(account_id, action: str, due: date) -> dict:
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else DPO,
    }


def plan_purge(accounts, today: date) -> list[dict]:
    if not isinstance(today, date):
        raise TypeError("today must be a datetime.date")

    seen: set = set()
    actions: list[dict] = []
    deletes: list[tuple] = []  # (closed_rank, due, account_id)

    for acc in accounts:
        account_id = acc.get("id")
        if account_id in seen:
            raise ValueError(f"duplicate account id {account_id!r}")
        seen.add(account_id)

        if acc.get("litigation_hold") or _is_staff(acc):
            continue

        last_seen = acc.get("last_seen_at")
        if last_seen is None:
            log.warning("account %r: last_seen_at missing; skipped", account_id)
            continue

        closed_at = acc.get("closed_at")
        closed_by = acc.get("closed_by")
        if closed_at is None and closed_by is not None:
            log.warning("account %r: closed_by set without closed_at; treated as open", account_id)
        if closed_at is not None and closed_by not in ("member", "staff"):
            log.warning("account %r: unknown closed_by value; not treated as member-closed", account_id)

        due = last_seen + INACTIVITY
        if closed_at is not None:
            due = min(due, closed_at + CLOSED_GRACE)

        if due <= today:
            if _has_unpaid(acc, account_id):
                if acc.get("status") != ANONYMISED_STATUS:
                    actions.append(_action(account_id, "anonymise", due))
            else:
                closed_rank = 0 if closed_at is not None else 1
                deletes.append((closed_rank, due, account_id))
            continue

        if due <= today + WARN_WINDOW:
            member_closed = closed_at is not None and closed_by == "member"
            if not member_closed:
                actions.append(_action(account_id, "warn", due))

    deletes.sort(key=lambda t: (t[0], t[1], t[2]))
    if len(deletes) > DELETE_CAP:
        log.info("delete cap reached: %d candidates, %d deferred", len(deletes), len(deletes) - DELETE_CAP)
    for _, due, account_id in deletes[:DELETE_CAP]:
        actions.append(_action(account_id, "delete", due))

    actions.sort(key=lambda a: a["account_id"])
    return actions


TODAY = date(2026, 10, 13)
EMAIL = "member@example.com"


def _acc(id_, **kw) -> dict:
    base = {
        "id": id_,
        "email": f"m{id_}@example.com",
        "status": "active",
        "last_seen_at": None,
        "last_login": None,
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": None,
        "litigation_hold": False,
    }
    base.update(kw)
    return base


class PlanPurgeTests(unittest.TestCase):
    def test_inactive_due_today_is_delete(self):
        out = plan_purge([_acc(1, last_seen_at=date(2024, 10, 13))], TODAY)
        self.assertEqual(out, [{"account_id": 1, "action": "delete", "due": "2026-10-13", "approved_by": DPO}])

    def test_inactive_due_in_7_days_is_warn_without_approver(self):
        out = plan_purge([_acc(2, last_seen_at=date(2024, 10, 20))], TODAY)
        self.assertEqual(out, [{"account_id": 2, "action": "warn", "due": "2026-10-20", "approved_by": None}])

    def test_member_closed_due_today_is_delete(self):
        out = plan_purge(
            [_acc(3, last_seen_at=date(2026, 1, 1), closed_at=date(2026, 9, 13), closed_by="member")], TODAY
        )
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], "2026-10-13")

    def test_member_closed_due_in_7_days_has_no_warn(self):
        out = plan_purge(
            [_acc(4, last_seen_at=date(2026, 1, 1), closed_at=date(2026, 9, 20), closed_by="member")], TODAY
        )
        self.assertEqual(out, [])

    def test_staff_closed_due_in_7_days_is_warn(self):
        out = plan_purge(
            [_acc(5, last_seen_at=date(2026, 1, 1), closed_at=date(2026, 9, 20), closed_by="staff")], TODAY
        )
        self.assertEqual(out, [{"account_id": 5, "action": "warn", "due": "2026-10-20", "approved_by": None}])

    def test_unpaid_due_today_is_anonymise(self):
        out = plan_purge([_acc(6, last_seen_at=date(2024, 10, 13), unpaid_invoices=3)], TODAY)
        self.assertEqual(out[0]["action"], "anonymise")
        self.assertEqual(out[0]["approved_by"], DPO)

    def test_unpaid_true_and_zero_count(self):
        out = plan_purge(
            [
                _acc(7, last_seen_at=date(2024, 10, 13), unpaid_invoices=True),
                _acc(8, last_seen_at=date(2024, 10, 13), unpaid_invoices=0),
            ],
            TODAY,
        )
        self.assertEqual([(a["account_id"], a["action"]) for a in out], [(7, "anonymise"), (8, "delete")])

    def test_litigation_hold_due_today_no_action(self):
        out = plan_purge([_acc(9, last_seen_at=date(2024, 10, 13), litigation_hold=True)], TODAY)
        self.assertEqual(out, [])

    def test_litigation_hold_warn_window_no_action(self):
        out = plan_purge([_acc(10, last_seen_at=date(2024, 10, 20), litigation_hold=True)], TODAY)
        self.assertEqual(out, [])

    def test_staff_accounts_no_action_any_state(self):
        staff = [
            _acc(11, email="a@Tidewater-Klatring.no", last_seen_at=date(2024, 10, 13)),
            _acc(12, email="b@tidewater-klatring.no", last_seen_at=date(2024, 10, 20)),
            _acc(13, email="c@tidewater-klatring.no", last_seen_at=date(2024, 10, 13), unpaid_invoices=2),
        ]
        self.assertEqual(plan_purge(staff, TODAY), [])

    def test_warn_boundary_day_14_included_day_15_excluded(self):
        out = plan_purge(
            [
                _acc(14, last_seen_at=date(2024, 10, 27)),  # due 2026-10-27 = today + 14
                _acc(15, last_seen_at=date(2024, 10, 28)),  # due 2026-10-28 = today + 15
            ],
            TODAY,
        )
        self.assertEqual([a["account_id"] for a in out], [14])
        self.assertEqual(out[0]["action"], "warn")

    def test_idempotency_anonymised_status_not_reemitted(self):
        out = plan_purge(
            [_acc(16, last_seen_at=date(2024, 10, 13), unpaid_invoices=1, status=ANONYMISED_STATUS)], TODAY
        )
        self.assertEqual(out, [])

    def test_missing_last_seen_skipped(self):
        out = plan_purge([_acc(17, last_seen_at=None, last_login=date(2020, 1, 1))], TODAY)
        self.assertEqual(out, [])

    def test_closed_by_without_closed_at_treated_as_open(self):
        out = plan_purge([_acc(18, last_seen_at=date(2024, 10, 13), closed_by="member")], TODAY)
        self.assertEqual(out[0]["action"], "delete")

    def test_cap_200_with_all_60_closed_included(self):
        accounts = []
        for i in range(60):
            accounts.append(
                _acc(f"c{i:03d}", last_seen_at=date(2026, 1, 1), closed_at=date(2026, 9, 13), closed_by="member")
            )
        for i in range(190):
            accounts.append(_acc(f"i{i:03d}", last_seen_at=date(2024, 10, 13)))
        out = plan_purge(accounts, TODAY)
        deletes = [a["account_id"] for a in out if a["action"] == "delete"]
        self.assertEqual(len(deletes), 200)
        closed_ids = {f"c{i:03d}" for i in range(60)}
        self.assertTrue(closed_ids.issubset(set(deletes)))

    def test_anonymise_does_not_consume_cap(self):
        accounts = [_acc(f"i{i:03d}", last_seen_at=date(2024, 10, 13)) for i in range(200)]
        accounts.append(_acc("z", last_seen_at=date(2024, 10, 13), unpaid_invoices=1))
        out = plan_purge(accounts, TODAY)
        self.assertEqual(sum(a["action"] == "delete" for a in out), 200)
        self.assertEqual(sum(a["action"] == "anonymise" for a in out), 1)

    def test_output_sorted_and_iso_dates(self):
        out = plan_purge(
            [
                _acc("b", last_seen_at=date(2024, 10, 13)),
                _acc("a", last_seen_at=date(2024, 10, 20)),
            ],
            TODAY,
        )
        self.assertEqual([a["account_id"] for a in out], ["a", "b"])
        for a in out:
            self.assertIsInstance(a["due"], str)
            self.assertEqual(set(a), {"account_id", "action", "due", "approved_by"})

    def test_no_email_in_output(self):
        accounts = [
            _acc(1, email=EMAIL, last_seen_at=date(2024, 10, 13)),
            _acc(2, email=EMAIL, last_seen_at=date(2024, 10, 20)),
            _acc(3, email=EMAIL, last_seen_at=date(2024, 10, 13), unpaid_invoices=1),
        ]
        out = plan_purge(accounts, TODAY)
        self.assertTrue(out)
        self.assertNotIn("example.com", repr(out))
        self.assertNotIn("member", repr(out))

    def test_no_email_in_exception_messages(self):
        accounts = [
            _acc(1, email=EMAIL, last_seen_at=date(2024, 10, 13)),
            _acc(1, email=EMAIL, last_seen_at=date(2024, 10, 13)),
        ]
        with self.assertRaises(ValueError) as ctx:
            plan_purge(accounts, TODAY)
        self.assertNotIn("example.com", str(ctx.exception))
        self.assertNotIn("member", str(ctx.exception))

        bad = [_acc(2, email=EMAIL, unpaid_invoices=1.5, last_seen_at=date(2024, 10, 13))]
        with self.assertRaises(ValueError) as ctx:
            plan_purge(bad, TODAY)
        self.assertNotIn("example.com", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()