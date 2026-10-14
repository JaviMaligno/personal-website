"""GDPR clean-up planner for Tidewater Climbing member accounts.

Open items (client has not answered, defaults applied):
- C2: Skatteetaten requires keeping all invoices for five years, but only accounts
  with unpaid invoices are protected. Paid invoices in deleted accounts may be lost.
  Behaviour not changed. Needs approval.
- C3: approved_by is set automatically to DPO_NAME. A script cannot grant DPO
  approval. The client must confirm the approval process.
- C4: Warn notices for accounts that will be anonymised say they will be deleted.
  Wording issue, not handled in this module.
- C5: One warn per account per daily run while in the window. Members will receive
  repeated daily warnings until the account is processed.
- C6: last_seen_at missing, non-date values, or inconsistent closed fields raise
  ValueError naming only the account id. The whole run halts rather than guessing.
- C7: status and last_login are ignored. tenant is ignored (R18).

Interpretation notes:
- A4 is applied literally. A due account pushed out of the delete cap receives a
  warn with its past due date, unless closed_by == "member" (R9).
- Conflict: the house rule asks that every action carry the account email. R13
  forbids any member email in any output field. R13 is followed, so actions carry
  no email. Client and operator to confirm.
- DPO_NAME is read from the TIDEWATER_DPO_NAME environment variable. The placeholder
  is used if the variable is unset. Replace it with the confirmed DPO name (C3).
"""

import logging
import os
import unittest
from datetime import date, datetime, timedelta

log = logging.getLogger(__name__)

DPO_NAME = os.environ.get("TIDEWATER_DPO_NAME", "PENDING-DPO-CONFIRMATION")
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200


def _is_plain_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _date_field(acc, field, required):
    value = acc.get(field)
    if value is None:
        if required:
            raise ValueError(f"account {acc.get('id')!r}: {field} is missing")
        return None
    if not _is_plain_date(value):
        raise ValueError(f"account {acc.get('id')!r}: {field} must be a date")
    return value


def _due_date(acc):
    """Return (due date, is_closed). A1: earlier of the R5 and R6 dates."""
    last_seen = _date_field(acc, "last_seen_at", required=True)
    closed_at = _date_field(acc, "closed_at", required=False)
    closed_by = acc.get("closed_by")
    inactive_due = last_seen + timedelta(days=INACTIVITY_DAYS)
    if closed_at is None:
        if closed_by is not None:
            raise ValueError(f"account {acc.get('id')!r}: closed_by set without closed_at")
        return inactive_due, False
    if closed_by not in ("member", "staff"):
        raise ValueError(f"account {acc.get('id')!r}: closed_at set with invalid closed_by")
    return min(inactive_due, closed_at + timedelta(days=CLOSED_GRACE_DAYS)), True


def _is_staff(acc):
    email = acc.get("email")
    if not isinstance(email, str):
        raise ValueError(f"account {acc.get('id')!r}: email must be a string")
    return email.lower().endswith(STAFF_DOMAIN)


def _action(acc_id, action, due):
    approved_by = None if action == "warn" else DPO_NAME
    return {
        "account_id": acc_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    if not _is_plain_date(today):
        raise ValueError("today must be a datetime.date")
    window_end = today + timedelta(days=WARN_WINDOW_DAYS)

    deletes = []    # (group, due, account_id, member_closed)
    anonymise = []
    warns = []

    for acc in accounts:
        if acc.get("litigation_hold") or _is_staff(acc):
            continue
        due, closed = _due_date(acc)
        acc_id = acc["id"]
        member_closed = acc.get("closed_by") == "member"
        if due <= today:
            if acc.get("unpaid_invoices"):
                anonymise.append(_action(acc_id, "anonymise", due))
            else:
                # R14: closed accounts (group 0) before inactive ones (group 1).
                deletes.append((0 if closed else 1, due, acc_id, member_closed))
        elif due <= window_end and not member_closed:
            warns.append(_action(acc_id, "warn", due))

    deletes.sort(key=lambda d: (d[0], d[1], d[2]))
    selected = deletes[:DELETE_CAP]
    overflow = deletes[DELETE_CAP:]
    if overflow:
        log.info("delete cap reached: %d candidates deferred", len(overflow))

    actions = [_action(acc_id, "delete", due) for _, due, acc_id, _ in selected]
    actions.extend(anonymise)
    actions.extend(warns)
    # A4: accounts pushed out by the cap receive a warn; R9 still applies.
    actions.extend(
        _action(acc_id, "warn", due)
        for _, due, acc_id, member_closed in overflow
        if not member_closed
    )
    actions.sort(key=lambda a: a["account_id"])
    return actions


TODAY = date(2026, 10, 13)


def _acc(acc_id, last_seen, closed_at=None, closed_by=None, unpaid=0, hold=False,
         email=None, last_login=None):
    return {
        "id": acc_id,
        "email": email if email is not None else f"member{acc_id}@example.invalid",
        "status": "active",
        "last_seen_at": last_seen,
        "last_login": last_login,
        "closed_at": closed_at,
        "closed_by": closed_by,
        "unpaid_invoices": unpaid,
        "litigation_hold": hold,
        "tenant": "legacy",
    }


def _last_seen_for_due(due):
    return due - timedelta(days=INACTIVITY_DAYS)


def _ids(actions, kind):
    return [a["account_id"] for a in actions if a["action"] == kind]


class PlanPurgeTests(unittest.TestCase):

    def test_inactive_account_deleted_on_due_date(self):
        acts = plan_purge([_acc(1, _last_seen_for_due(TODAY))], TODAY)
        self.assertEqual(_ids(acts, "delete"), [1])
        self.assertEqual(acts[0]["due"], "2026-10-13")

    def test_not_due_and_outside_window_produces_nothing(self):
        acts = plan_purge([_acc(1, _last_seen_for_due(TODAY + timedelta(days=15)))], TODAY)
        self.assertEqual(acts, [])

    def test_window_boundary_inclusive_at_14_days(self):
        acts = plan_purge([_acc(1, _last_seen_for_due(TODAY + timedelta(days=14)))], TODAY)
        self.assertEqual(_ids(acts, "warn"), [1])
        self.assertEqual(acts[0]["due"], "2026-10-27")

    def test_closed_account_uses_earlier_30_day_date(self):
        acc = _acc(2, TODAY - timedelta(days=10), closed_at=TODAY - timedelta(days=30),
                   closed_by="staff")
        acts = plan_purge([acc], TODAY)
        self.assertEqual(_ids(acts, "delete"), [2])
        self.assertEqual(acts[0]["due"], "2026-10-13")

    def test_closed_account_warned_in_window(self):
        acc = _acc(3, TODAY - timedelta(days=10), closed_at=TODAY - timedelta(days=20),
                   closed_by="staff")
        acts = plan_purge([acc], TODAY)
        self.assertEqual(_ids(acts, "warn"), [3])

    def test_member_closed_account_never_warned(self):
        acc = _acc(4, TODAY - timedelta(days=10), closed_at=TODAY - timedelta(days=20),
                   closed_by="member")
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_last_login_is_ignored(self):
        acc = _acc(5, TODAY - timedelta(days=1), last_login=TODAY - timedelta(days=5000))
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_unpaid_invoices_get_anonymise_not_delete(self):
        acc = _acc(6, _last_seen_for_due(TODAY) - timedelta(days=30), unpaid=2)
        acts = plan_purge([acc], TODAY)
        self.assertEqual(_ids(acts, "anonymise"), [6])
        self.assertEqual(_ids(acts, "delete"), [])
        self.assertEqual(acts[0]["approved_by"], DPO_NAME)

    def test_litigation_hold_produces_no_actions(self):
        due_now = _acc(7, _last_seen_for_due(TODAY), hold=True)
        in_window = _acc(8, _last_seen_for_due(TODAY + timedelta(days=5)), hold=True)
        self.assertEqual(plan_purge([due_now, in_window], TODAY), [])

    def test_staff_domain_matched_case_insensitively(self):
        acc = _acc(9, _last_seen_for_due(TODAY), email="Ann.Lee@Tidewater-Klatring.NO")
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_cap_closed_first_and_anonymise_not_counted(self):
        old = TODAY - timedelta(days=800)
        accs = [_acc(i, old) for i in range(1, 202)]              # 201 inactive due
        accs.append(_acc(300, old, closed_at=TODAY - timedelta(days=5),
                         closed_by="staff"))                       # closed due
        accs += [_acc(400 + k, old, unpaid=1) for k in range(3)]   # anonymise
        acts = plan_purge(accs, TODAY)

        deleted = set(_ids(acts, "delete"))
        self.assertEqual(len(deleted), DELETE_CAP)
        self.assertEqual(deleted, {300} | set(range(1, 200)))
        self.assertEqual(set(_ids(acts, "warn")), {200, 201})
        self.assertEqual(sorted(_ids(acts, "anonymise")), [400, 401, 402])

    def test_output_sorted_shape_and_no_email(self):
        accs = [
            _acc(20, _last_seen_for_due(TODAY)),
            _acc(10, _last_seen_for_due(TODAY + timedelta(days=3))),
            _acc(30, _last_seen_for_due(TODAY - timedelta(days=2)), unpaid=1),
        ]
        acts = plan_purge(accs, TODAY)
        self.assertEqual([a["account_id"] for a in acts], [10, 20, 30])
        for a in acts:
            self.assertEqual(set(a.keys()), {"account_id", "action", "due", "approved_by"})
            for value in a.values():
                self.assertNotIn("@", str(value))
        by_id = {a["account_id"]: a for a in acts}
        self.assertIsNone(by_id[10]["approved_by"])
        self.assertEqual(by_id[20]["approved_by"], DPO_NAME)
        self.assertEqual(by_id[10]["due"], "2026-10-16")

    def test_missing_last_seen_raises(self):
        acc = _acc(40, None)
        with self.assertRaises(ValueError):
            plan_purge([acc], TODAY)

    def test_closed_at_without_closed_by_raises(self):
        acc = _acc(41, TODAY, closed_at=TODAY, closed_by=None)
        with self.assertRaises(ValueError):
            plan_purge([acc], TODAY)

    def test_closed_by_without_closed_at_raises(self):
        acc = _acc(42, TODAY, closed_at=None, closed_by="member")
        with self.assertRaises(ValueError):
            plan_purge([acc], TODAY)

    def test_non_date_today_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([], datetime(2026, 10, 13))


if __name__ == "__main__":
    unittest.main()