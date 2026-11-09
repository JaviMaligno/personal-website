"""GDPR inactivity purge planner for member accounts (Tidewater Climbing).

Pure planning only: no deletion, anonymisation or database side effects.

Open questions for the client (not blocking):
- Staff domain match is by email suffix only; confirm whether a company-name check is also wanted.
- Account status values are not used for filtering; confirm none should be.
- Accounts beyond the 200-delete cap get no action this run; confirm they are picked up on the next run.
"""

from datetime import date, datetime, timedelta
import unittest

APPROVER = "Tordis Svenbjorn Dottir"
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVE_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_DAYS = 14
DELETE_CAP = 200

_REQUIRED = (
    "id", "email", "status", "last_seen_at", "last_login",
    "closed_at", "closed_by", "unpaid_invoices", "litigation_hold",
)


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _validate(account):
    if not isinstance(account, dict):
        raise ValueError("account must be a dict")
    missing = [k for k in _REQUIRED if k not in account]
    if missing:
        raise ValueError(f"account {account.get('id')!r} missing keys: {missing}")
    acct_id = account["id"]
    if not isinstance(acct_id, (int, str)) or isinstance(acct_id, bool):
        raise ValueError("id must be int or str")
    if not isinstance(account["email"], str):
        raise ValueError(f"account {acct_id!r}: email must be str")
    if not _is_date(account["last_seen_at"]):
        raise ValueError(f"account {acct_id!r}: last_seen_at must be a date")
    if account["closed_at"] is not None:
        if not _is_date(account["closed_at"]):
            raise ValueError(f"account {acct_id!r}: closed_at must be a date or None")
        if account["closed_by"] not in ("member", "staff"):
            raise ValueError(f"account {acct_id!r}: closed_by must be 'member' or 'staff'")
    elif account["closed_by"] is not None:
        raise ValueError(f"account {acct_id!r}: closed_by set without closed_at")
    if not isinstance(account["litigation_hold"], bool):
        raise ValueError(f"account {acct_id!r}: litigation_hold must be bool")
    if not isinstance(account["unpaid_invoices"], int):
        raise ValueError(f"account {acct_id!r}: unpaid_invoices must be int")


def _is_staff(email):
    return email.strip().lower().endswith(STAFF_DOMAIN)


def _due(account):
    due = account["last_seen_at"] + timedelta(days=INACTIVE_DAYS)
    if account["closed_at"] is not None:
        due = min(due, account["closed_at"] + timedelta(days=CLOSED_GRACE_DAYS))
    return due


def _action(account_id, action, due, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    if not _is_date(today):
        raise ValueError("today must be a date")

    horizon = today + timedelta(days=WARN_DAYS)
    actions = []
    deletes = []

    for account in accounts:
        _validate(account)
        if account["litigation_hold"] or _is_staff(account["email"]):
            continue

        due = _due(account)
        if due <= today:
            if account["unpaid_invoices"]:
                actions.append(_action(account["id"], "anonymise", due, APPROVER))
            else:
                # Closed accounts first, then earliest due date, then id.
                key = (account["closed_at"] is None, due, account["id"])
                deletes.append((key, account, due))
        elif due <= horizon and account["closed_by"] != "member":
            actions.append(_action(account["id"], "warn", due, None))

    deletes.sort(key=lambda item: item[0])
    for _, account, due in deletes[:DELETE_CAP]:
        actions.append(_action(account["id"], "delete", due, APPROVER))

    actions.sort(key=lambda a: a["account_id"])
    return actions


# ---------------------------------------------------------------- tests

TODAY = date(2026, 10, 13)


def _acct(acct_id, last_seen_at, **overrides):
    base = {
        "id": acct_id,
        "email": f"member{acct_id}@example.com",
        "status": "active",
        "last_seen_at": last_seen_at,
        "last_login": last_seen_at,
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
    }
    base.update(overrides)
    return base


class PlanPurgeTests(unittest.TestCase):

    def test_730_day_rule(self):
        accounts = [
            _acct(1, TODAY - timedelta(days=730)),  # due today -> delete
            _acct(2, TODAY - timedelta(days=729)),  # due tomorrow -> warn
            _acct(3, TODAY - timedelta(days=700)),  # due in 30 days -> nothing
        ]
        out = plan_purge(accounts, TODAY)
        self.assertEqual(out, [
            {"account_id": 1, "action": "delete", "due": "2026-10-13", "approved_by": APPROVER},
            {"account_id": 2, "action": "warn", "due": "2026-10-14", "approved_by": None},
        ])

    def test_closed_earlier_rule(self):
        accounts = [_acct(
            1, TODAY - timedelta(days=10),
            closed_at=TODAY - timedelta(days=40), closed_by="staff",
        )]
        out = plan_purge(accounts, TODAY)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], (TODAY - timedelta(days=10)).isoformat())

    def test_warn_window_boundaries(self):
        accounts = [
            _acct(1, TODAY + timedelta(days=14) - timedelta(days=730)),  # due +14 -> warn
            _acct(2, TODAY + timedelta(days=15) - timedelta(days=730)),  # due +15 -> nothing
            _acct(3, TODAY - timedelta(days=730)),                       # due today -> delete
        ]
        out = plan_purge(accounts, TODAY)
        by_id = {a["account_id"]: a["action"] for a in out}
        self.assertEqual(by_id, {1: "warn", 3: "delete"})

    def test_member_closed_not_warned(self):
        accounts = [_acct(
            1, TODAY - timedelta(days=720),
            closed_at=TODAY - timedelta(days=5), closed_by="member",
        )]
        self.assertEqual(plan_purge(accounts, TODAY), [])

    def test_staff_accounts_excluded(self):
        accounts = [_acct(
            1, TODAY - timedelta(days=730),
            email="  Admin@Tidewater-Klatring.NO ",
        )]
        self.assertEqual(plan_purge(accounts, TODAY), [])

    def test_litigation_hold_untouched(self):
        accounts = [
            _acct(1, TODAY - timedelta(days=730), litigation_hold=True),
            _acct(2, TODAY - timedelta(days=729), litigation_hold=True),
            _acct(3, TODAY - timedelta(days=730), unpaid_invoices=1, litigation_hold=True),
        ]
        self.assertEqual(plan_purge(accounts, TODAY), [])

    def test_invoices_lead_to_anonymise(self):
        accounts = [
            _acct(1, TODAY - timedelta(days=730), unpaid_invoices=2),
            _acct(2, TODAY - timedelta(days=725), unpaid_invoices=1),  # warn-window, anonymise-bound
        ]
        out = plan_purge(accounts, TODAY)
        self.assertEqual(out, [
            {"account_id": 1, "action": "anonymise", "due": "2026-10-13", "approved_by": APPROVER},
            {"account_id": 2, "action": "warn", "due": "2026-10-18", "approved_by": None},
        ])

    def test_cap_ordering(self):
        normal = [_acct(i, TODAY - timedelta(days=730)) for i in range(1, 206)]
        closed = [
            _acct(1000 + k, TODAY - timedelta(days=730),
                  closed_at=TODAY - timedelta(days=5), closed_by="staff")
            for k in range(5)
        ]
        out = plan_purge(normal + closed, TODAY)
        deletes = {a["account_id"] for a in out if a["action"] == "delete"}
        expected = {1000 + k for k in range(5)} | set(range(1, 196))
        self.assertEqual(len(deletes), DELETE_CAP)
        self.assertEqual(deletes, expected)

    def test_cap_does_not_count_anonymise(self):
        accounts = [_acct(i, TODAY - timedelta(days=730)) for i in range(1, 201)]
        accounts.append(_acct(500, TODAY - timedelta(days=730), unpaid_invoices=1))
        out = plan_purge(accounts, TODAY)
        self.assertEqual(sum(a["action"] == "delete" for a in out), 200)
        self.assertIn(
            {"account_id": 500, "action": "anonymise", "due": "2026-10-13", "approved_by": APPROVER},
            out,
        )

    def test_no_email_in_output(self):
        accounts = [
            _acct(1, TODAY - timedelta(days=730)),
            _acct(2, TODAY - timedelta(days=729)),
        ]
        out = plan_purge(accounts, TODAY)
        self.assertTrue(out)
        for action in out:
            self.assertEqual(set(action), {"account_id", "action", "due", "approved_by"})
            self.assertNotIn("@", str(action))

    def test_sorted_by_account_id(self):
        accounts = [
            _acct(30, TODAY - timedelta(days=730)),
            _acct(10, TODAY - timedelta(days=730)),
            _acct(20, TODAY - timedelta(days=729)),
        ]
        ids = [a["account_id"] for a in plan_purge(accounts, TODAY)]
        self.assertEqual(ids, [10, 20, 30])

    def test_iso_dates(self):
        accounts = [_acct(1, TODAY - timedelta(days=730))]
        due = plan_purge(accounts, TODAY)[0]["due"]
        self.assertIsInstance(due, str)
        self.assertEqual(date.fromisoformat(due), TODAY)

    def test_missing_last_seen_raises(self):
        account = _acct(1, TODAY)
        del account["last_seen_at"]
        with self.assertRaises(ValueError):
            plan_purge([account], TODAY)

    def test_datetime_last_seen_raises(self):
        account = _acct(1, datetime(2024, 1, 1))
        with self.assertRaises(ValueError):
            plan_purge([account], TODAY)


if __name__ == "__main__":
    unittest.main()