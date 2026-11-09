# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-ju0mg44n/gdpr_purge.py
"""GDPR clean-up planner for Tidewater Climbing.

Implements plan_purge(accounts, today) per the architect's design.
Standard library only. Python 3.12.

Open questions and defaults (PM to confirm):
1. Deletion candidates beyond DELETE_CAP get no action in this run.
2. An account both closed and with unpaid invoices uses the same due logic
   as other closed accounts, and the warn window applies to it too.
3. DELETE_CAP counts only "delete" actions. "anonymise" and "warn" are never capped.
4. Accounts with neither last_seen_at nor closed_at are skipped (no action).
5. Unrecognised closed_by values suppress warn (fail closed for notifications).
   closed_by == "member" also suppresses warn. Only None and "staff" warn.
6. Duplicate account ids raise ValueError. Only the id is reported, never the email.

Other decisions:
- Mixed id types (for example str and int) raise TypeError, because output is sorted by id.
- Accounts with a missing or unusable id are skipped and are not duplicate-checked.
- Accounts with a missing required key are skipped in step 1 and are not duplicate-checked either.
- The "tenant" and "last_login" keys are never read. Accounts are read only through
  the required keys, and the account mapping is never copied.
- Staff check: the email must be a str. It is stripped and lowercased before the suffix test.
- Overflowing date arithmetic is treated as "no computable due date" and the account is skipped.
- The email is read only for the staff check and is never placed in output or exceptions.
"""

import datetime
from datetime import date, timedelta

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200
DPO = "Tordis Svenbjorn Dottir"
STAFF_SUFFIX = "@tidewater-klatring.no"

REQUIRED_KEYS = (
    "id",
    "email",
    "status",
    "last_seen_at",
    "closed_at",
    "closed_by",
    "unpaid_invoices",
    "litigation_hold",
)


def _get(account, key):
    try:
        return True, account[key]
    except (KeyError, TypeError, IndexError):
        return False, None


def _usable_id(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, str):
        return value.strip() != ""
    return False


def _is_plain_date_or_none(value):
    if value is None:
        return True
    return isinstance(value, date) and not isinstance(value, datetime.datetime)


def _fetch(account):
    record = {}
    for key in REQUIRED_KEYS:
        ok, value = _get(account, key)
        if not ok:
            return None
        record[key] = value
    return record


def _due(last_seen_at, closed_at):
    candidates = []
    try:
        if last_seen_at is not None:
            candidates.append(last_seen_at + timedelta(days=INACTIVITY_DAYS))
        if closed_at is not None:
            candidates.append(closed_at + timedelta(days=CLOSED_GRACE_DAYS))
    except OverflowError:
        return None
    if not candidates:
        return None
    return min(candidates)


def _classify(record, today):
    """Return (action, due) or None. The email is read only for the staff check."""
    if not (_is_plain_date_or_none(record["last_seen_at"])
            and _is_plain_date_or_none(record["closed_at"])):
        return None

    email = record["email"]
    if isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX):
        return None

    if record["litigation_hold"]:
        return None

    due = _due(record["last_seen_at"], record["closed_at"])
    if due is None:
        return None

    if due <= today:
        action = "anonymise" if record["unpaid_invoices"] else "delete"
        return action, due

    if (due - today).days <= WARN_WINDOW_DAYS:
        closed_by = record["closed_by"]
        # Warn only when closed_by is None or "staff".
        # "member" never warns. Any other value is unrecognised and suppresses
        # the warn (fail closed for notifications, default decision 5).
        if closed_by is None or (isinstance(closed_by, str) and closed_by == "staff"):
            return "warn", due

    return None


def _row(account_id, action, due):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else DPO,
    }


def plan_purge(accounts, today):
    if not isinstance(accounts, (list, tuple)):
        raise TypeError("accounts must be a list or tuple")
    if not isinstance(today, date) or isinstance(today, datetime.datetime):
        raise TypeError("today must be a datetime.date")

    seen_ids = set()
    id_types = set()
    for account in accounts:
        ok, account_id = _get(account, "id")
        if not ok or not _usable_id(account_id):
            continue
        if account_id in seen_ids:
            raise ValueError("duplicate account id: %r" % (account_id,))
        seen_ids.add(account_id)
        id_types.add(type(account_id))
    if len(id_types) > 1:
        raise TypeError("account ids must all have the same type")

    actions = []
    queue = []
    for account in accounts:
        record = _fetch(account)
        if record is None or not _usable_id(record["id"]):
            continue
        result = _classify(record, today)
        if result is None:
            continue
        action, due = result
        if action == "delete":
            queue_key = (0 if record["closed_at"] is not None else 1, due, record["id"])
            queue.append((queue_key, record["id"], due))
        else:
            actions.append(_row(record["id"], action, due))

    # Deletion queue: closed accounts first, then by due ascending, then id.
    # Only the first DELETE_CAP queue members get a delete action this run
    # (default decision 1). Anonymise and warn actions are never capped.
    queue.sort(key=lambda item: item[0])
    for _, account_id, due in queue[:DELETE_CAP]:
        actions.append(_row(account_id, "delete", due))

    actions.sort(key=lambda row: row["account_id"])
    return actions


# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-ju0mg44n/tests/test_gdpr_purge.py
# Not executed in this session: no tool access was available to run plain python3.
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gdpr_purge import DPO, plan_purge  # noqa: E402

TODAY = datetime.date(2026, 10, 13)
ROW_KEYS = {"account_id", "action", "due", "approved_by"}


def days(n):
    return datetime.timedelta(days=n)


def acct(account_id="a1", email="member@example.org", last_seen_at=None,
         closed_at=None, closed_by=None, unpaid=False, hold=False, status="active"):
    return {
        "id": account_id,
        "email": email,
        "status": status,
        "last_seen_at": last_seen_at,
        "closed_at": closed_at,
        "closed_by": closed_by,
        "unpaid_invoices": unpaid,
        "litigation_hold": hold,
    }


class _TenantTrap(dict):
    def __getitem__(self, key):
        if key == "tenant":
            raise AssertionError("tenant must never be read")
        return dict.__getitem__(self, key)


class BoundaryTests(unittest.TestCase):
    def test_last_seen_due_today_is_delete(self):
        result = plan_purge([acct(last_seen_at=TODAY - days(730))], TODAY)
        self.assertEqual(result, [{"account_id": "a1", "action": "delete",
                                   "due": TODAY.isoformat(), "approved_by": DPO}])

    def test_last_seen_due_yesterday_is_delete(self):
        result = plan_purge([acct(last_seen_at=TODAY - days(731))], TODAY)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["action"], "delete")
        self.assertEqual(result[0]["due"], (TODAY - days(1)).isoformat())

    def test_last_seen_due_tomorrow_is_warn(self):
        result = plan_purge([acct(last_seen_at=TODAY - days(729))], TODAY)
        self.assertEqual(result, [{"account_id": "a1", "action": "warn",
                                   "due": (TODAY + days(1)).isoformat(), "approved_by": None}])

    def test_last_seen_due_plus14_is_warn(self):
        result = plan_purge([acct(last_seen_at=TODAY - days(716))], TODAY)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["action"], "warn")

    def test_last_seen_due_plus15_is_no_action(self):
        result = plan_purge([acct(last_seen_at=TODAY - days(715))], TODAY)
        self.assertEqual(result, [])

    def test_closed_due_today_is_delete(self):
        result = plan_purge([acct(closed_at=TODAY - days(30), closed_by="member")], TODAY)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["action"], "delete")
        self.assertEqual(result[0]["due"], TODAY.isoformat())

    def test_closed_due_tomorrow_is_warn(self):
        result = plan_purge([acct(closed_at=TODAY - days(29), closed_by="staff")], TODAY)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["action"], "warn")
        self.assertIsNone(result[0]["approved_by"])


class DueDateTests(unittest.TestCase):
    def test_closed_due_is_earlier(self):
        account = acct(last_seen_at=TODAY - days(100), closed_at=TODAY - days(40), closed_by="member")
        result = plan_purge([account], TODAY)
        self.assertEqual(result[0]["due"], (TODAY - days(10)).isoformat())
        self.assertEqual(result[0]["action"], "delete")

    def test_inactivity_due_is_earlier(self):
        account = acct(last_seen_at=TODAY - days(731), closed_at=TODAY - days(5), closed_by="member")
        result = plan_purge([account], TODAY)
        self.assertEqual(result[0]["due"], (TODAY - days(1)).isoformat())
        self.assertEqual(result[0]["action"], "delete")

    def test_none_last_seen_uses_closed(self):
        result = plan_purge([acct(last_seen_at=None, closed_at=TODAY - days(30), closed_by="member")], TODAY)
        self.assertEqual(result[0]["due"], TODAY.isoformat())
        self.assertEqual(result[0]["action"], "delete")

    def test_both_none_is_skipped(self):
        self.assertEqual(plan_purge([acct()], TODAY), [])


class ExclusionTests(unittest.TestCase):
    def test_staff_email_excluded_in_any_case(self):
        emails = ["person@tidewater-klatring.no",
                  "PERSON@TIDEWATER-KLATRING.NO",
                  "  Staff@Tidewater-Klatring.no  "]
        accounts = [acct("s%d" % i, email=e, last_seen_at=TODAY - days(800))
                    for i, e in enumerate(emails)]
        self.assertEqual(plan_purge(accounts, TODAY), [])

    def test_staff_email_in_warn_window_excluded(self):
        result = plan_purge([acct(email="X@TIDEWATER-KLATRING.NO", closed_at=TODAY - days(29),
                                  closed_by="staff")], TODAY)
        self.assertEqual(result, [])

    def test_litigation_hold_blocks_everything(self):
        self.assertEqual(plan_purge([acct(last_seen_at=TODAY - days(800), hold=True)], TODAY), [])
        self.assertEqual(plan_purge([acct(closed_at=TODAY - days(29), closed_by="staff", hold=True)], TODAY), [])
        self.assertEqual(plan_purge([acct(closed_at=TODAY - days(40), unpaid=True, hold=True)], TODAY), [])

    def test_member_closed_in_warn_window_no_warn(self):
        result = plan_purge([acct(closed_at=TODAY - days(29), closed_by="member")], TODAY)
        self.assertEqual(result, [])

    def test_member_closed_when_due_still_deletes(self):
        result = plan_purge([acct(closed_at=TODAY - days(30), closed_by="member")], TODAY)
        self.assertEqual(result[0]["action"], "delete")

    def test_unrecognised_closed_by_suppresses_warn_but_not_delete(self):
        for junk in ("other", 42, "", ["staff"], object()):
            with self.subTest(closed_by=junk):
                self.assertEqual(plan_purge([acct(closed_at=TODAY - days(29), closed_by=junk)], TODAY), [])
                overdue = plan_purge([acct(closed_at=TODAY - days(30), closed_by=junk)], TODAY)
                self.assertEqual(overdue[0]["action"], "delete")

    def test_missing_key_is_skipped(self):
        account = acct(last_seen_at=TODAY - days(800))
        del account["litigation_hold"]
        self.assertEqual(plan_purge([account], TODAY), [])

    def test_datetime_field_is_rejected(self):
        account = acct(last_seen_at=datetime.datetime(2024, 1, 1, 12, 0))
        self.assertEqual(plan_purge([account], TODAY), [])

    def test_unusable_id_is_skipped(self):
        self.assertEqual(plan_purge([acct(account_id=None, last_seen_at=TODAY - days(800))], TODAY), [])
        self.assertEqual(plan_purge([acct(account_id="   ", last_seen_at=TODAY - days(800))], TODAY), [])

    def test_last_login_is_ignored(self):
        account = acct(last_seen_at=TODAY - days(1))
        account["last_login"] = datetime.date(2000, 1, 1)
        self.assertEqual(plan_purge([account], TODAY), [])

    def test_tenant_is_never_read(self):
        account = _TenantTrap(acct(last_seen_at=TODAY - days(800)))
        account["tenant"] = "acme"
        result = plan_purge([account], TODAY)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["action"], "delete")


class UnpaidTests(unittest.TestCase):
    def test_unpaid_due_is_anonymise(self):
        result = plan_purge([acct(last_seen_at=TODAY - days(800), unpaid=True)], TODAY)
        self.assertEqual(result[0]["action"], "anonymise")
        self.assertEqual(result[0]["approved_by"], DPO)

    def test_closed_and_unpaid_in_warn_window_warns(self):
        result = plan_purge([acct(closed_at=TODAY - days(29), closed_by="staff", unpaid=True)], TODAY)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["action"], "warn")
        self.assertIsNone(result[0]["approved_by"])


class CapTests(unittest.TestCase):
    def _cap_accounts(self):
        accounts = []
        for i in range(120):
            accounts.append(acct("c%03d" % i, closed_at=TODAY - days(30 + i), closed_by="member"))
        for j in range(90):
            accounts.append(acct("o%03d" % j, last_seen_at=TODAY - days(730 + j)))
        return accounts

    def test_cap_ordering_and_overflow(self):
        result = plan_purge(self._cap_accounts(), TODAY)
        deletes = {r["account_id"] for r in result if r["action"] == "delete"}
        self.assertEqual(len(deletes), 200)
        closed_ids = {"c%03d" % i for i in range(120)}
        self.assertTrue(closed_ids <= deletes)
        open_deleted = deletes - closed_ids
        # Oldest last_seen first: j=89 is oldest, so j=0..9 are the overflow.
        self.assertEqual(open_deleted, {"o%03d" % j for j in range(10, 90)})
        for j in range(10):
            self.assertNotIn("o%03d" % j, [r["account_id"] for r in result])

    def test_anonymise_not_counted_toward_cap(self):
        accounts = self._cap_accounts()
        for k in range(5):
            accounts.append(acct("u%03d" % k, last_seen_at=TODAY - days(800), unpaid=True))
        result = plan_purge(accounts, TODAY)
        actions = [r["action"] for r in result]
        self.assertEqual(actions.count("delete"), 200)
        self.assertEqual(actions.count("anonymise"), 5)
        self.assertEqual({r["account_id"] for r in result if r["action"] == "anonymise"},
                         {"u%03d" % k for k in range(5)})


class PrivacyTests(unittest.TestCase):
    def test_email_never_appears_in_output(self):
        emails = ["alice-secret@example.org", "bob-secret@example.org", "x@tidewater-klatring.no"]
        accounts = [
            acct("a", email=emails[0], last_seen_at=TODAY - days(800)),
            acct("b", email=emails[1], last_seen_at=TODAY - days(800), unpaid=True),
            acct("c", email=emails[1], closed_at=TODAY - days(29), closed_by="staff"),
            acct("d", email=emails[2], last_seen_at=TODAY - days(800)),
            acct("e", email=None, last_seen_at=TODAY - days(800)),
        ]
        result = plan_purge(accounts, TODAY)
        for row in result:
            self.assertEqual(set(row.keys()), ROW_KEYS)
        text = str(result) + repr(result)
        for email in emails:
            self.assertNotIn(email, text)


class OrderingAndValidationTests(unittest.TestCase):
    def test_output_sorted_by_id(self):
        accounts = [acct("m", last_seen_at=TODAY - days(800)),
                    acct("a", last_seen_at=TODAY - days(800)),
                    acct("z", last_seen_at=TODAY - days(800))]
        result = plan_purge(accounts, TODAY)
        self.assertEqual([r["account_id"] for r in result], ["a", "m", "z"])

    def test_output_sorted_by_int_id(self):
        accounts = [acct(3, last_seen_at=TODAY - days(800)), acct(1, last_seen_at=TODAY - days(800))]
        result = plan_purge(accounts, TODAY)
        self.assertEqual([r["account_id"] for r in result], [1, 3])

    def test_accounts_must_be_list(self):
        with self.assertRaises(TypeError):
            plan_purge({"id": "x"}, TODAY)

    def test_today_must_be_date_not_datetime(self):
        with self.assertRaises(TypeError):
            plan_purge([], datetime.datetime(2026, 10, 13))

    def test_duplicate_ids_raise_without_email(self):
        accounts = [acct("dup", email="dup-secret@example.org", last_seen_at=TODAY - days(800)),
                    acct("dup", email="other-secret@example.org", last_seen_at=TODAY - days(800))]
        with self.assertRaises(ValueError) as ctx:
            plan_purge(accounts, TODAY)
        self.assertNotIn("secret@example.org", str(ctx.exception))

    def test_mixed_id_types_raise(self):
        accounts = [acct(1, last_seen_at=TODAY - days(800)), acct("b", last_seen_at=TODAY - days(800))]
        with self.assertRaises(TypeError):
            plan_purge(accounts, TODAY)

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(plan_purge([], TODAY), [])


if __name__ == "__main__":
    unittest.main()