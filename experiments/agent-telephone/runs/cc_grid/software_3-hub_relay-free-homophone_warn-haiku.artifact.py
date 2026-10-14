"""Tidewater Climbing GDPR clean-up planner.

plan_purge(accounts, today) returns planned actions only. It does not delete,
anonymise, email, or read the clock. Run the embedded tests with:
    python3 -I <this file>

Rules implemented:
- Inactivity uses last_seen_at only. last_login is never read.
- inactive_due = last_seen_at + 730 days; closed_due = closed_at + 30 days;
  due is the earliest present value (timedelta arithmetic).
- litigation_hold True: no action.
- Staff email (trimmed, case-insensitive, ends with @tidewater-klatring.no): no action.
- due <= today: anonymise if unpaid_invoices > 0, else delete.
- today < due <= today + 40 days: warn, unless closed_by == "member".
- At most 200 deletes per run. Delete priority: member-closed, then other
  closed, then inactive-only; ties by due then id. Anonymise is uncapped
  (ANONYMISE_CAPPED = False).

Validation (account skipped, only its id is logged): missing or non-string
email; unpaid_invoices None, non-int, bool or negative; litigation_hold
missing, None or non-bool; closed_at after today; closed_by "member" with
no closed_at; no last_seen_at and no closed_at.

Raises: accounts not a list; today not a date (datetime rejected); any
record not a dict; missing id; duplicate ids; last_seen_at or closed_at
not a date (datetime rejected). Exception messages never include emails or
field values.

Judgement calls:
- Non-bool litigation_hold and non-int or negative unpaid_invoices are
  treated as malformed and skipped rather than coerced.
- A closed account with closed_by other than "member" or "staff" is ranked
  in the "other closed" cap tier and is warned as non-member.
- Because a future closed_at is skipped, closed_due is at most today + 30,
  so the 35-day warn case is exercised with an inactive-only account.

Open questions for the client (not blocking):
1. Warning frequency. One warning per account per run; no de-duplication
   across runs is implemented.
2. Whether anonymise should count toward the 200 cap. Set
   ANONYMISE_CAPPED = True to include it.
3. Meaning of `status`. Ignored by all rules.
4. Warning wording for accounts that will be anonymised instead of deleted.

Status: the tests below were written but not executed in the environment
that produced this file.
"""

import json
import logging
import unicodedata
import unittest
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

INACTIVE_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 40
DELETE_CAP = 200

# Anonymise is deliberately uncapped. Open question for the client: should
# anonymise count toward DELETE_CAP? Set to True to include it in the cap.
ANONYMISE_CAPPED = False

APPROVER = unicodedata.normalize("NFC", "Þórdís Sveinbjörnsdóttir")
STAFF_SUFFIX = "@tidewater-klatring.no"


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _check_date(value, field, acc_id):
    if value is None or _is_date(value):
        return value
    raise TypeError(
        f"account {acc_id!r}: {field} must be a datetime.date or None, "
        f"got {type(value).__name__}"
    )


def _is_staff(email):
    return email.strip().lower().endswith(STAFF_SUFFIX)


def _skip(acc_id, reason):
    logger.info("skipped account %s: %s", acc_id, reason)
    return None


def _decide(acc, today):
    """Return (action, due, tier) or None for an account."""
    acc_id = acc["id"]
    email = acc.get("email")
    closed_by = acc.get("closed_by")
    unpaid = acc.get("unpaid_invoices")
    hold = acc.get("litigation_hold")
    last_seen = _check_date(acc.get("last_seen_at"), "last_seen_at", acc_id)
    closed_at = _check_date(acc.get("closed_at"), "closed_at", acc_id)

    if not isinstance(email, str) or not email.strip():
        return _skip(acc_id, "email missing")
    if not isinstance(unpaid, int) or isinstance(unpaid, bool) or unpaid < 0:
        return _skip(acc_id, "unpaid_invoices invalid")
    if not isinstance(hold, bool):
        return _skip(acc_id, "litigation_hold missing or invalid")
    if closed_at is not None and closed_at > today:
        return _skip(acc_id, "closed_at in the future")
    if closed_by == "member" and closed_at is None:
        return _skip(acc_id, "member closure without closed_at")
    if last_seen is None and closed_at is None:
        return _skip(acc_id, "no last_seen_at or closed_at")

    if hold:
        return None
    if _is_staff(email):
        return None

    dues = []
    if last_seen is not None:
        dues.append(last_seen + timedelta(days=INACTIVE_DAYS))
    if closed_at is not None:
        dues.append(closed_at + timedelta(days=CLOSED_GRACE_DAYS))
    due = min(dues)

    member = closed_by == "member"
    tier = 0 if member else (1 if closed_at is not None else 2)

    if due <= today:
        return ("anonymise" if unpaid > 0 else "delete"), due, tier
    if due <= today + timedelta(days=WARN_WINDOW_DAYS) and not member:
        return "warn", due, tier
    return None


def plan_purge(accounts, today):
    if not isinstance(accounts, list):
        raise TypeError("accounts must be a list")
    if not _is_date(today):
        raise TypeError("today must be a datetime.date, not datetime")
    if not accounts:
        return []

    seen = set()
    for acc in accounts:
        if not isinstance(acc, dict):
            raise TypeError("each account must be a dict")
        acc_id = acc.get("id")
        if acc_id is None:
            raise ValueError("account record is missing id")
        if acc_id in seen:
            raise ValueError(f"duplicate account id {acc_id!r}")
        seen.add(acc_id)

    decisions = []
    for acc in accounts:
        res = _decide(acc, today)
        if res is not None:
            action, due, tier = res
            decisions.append({
                "account_id": acc["id"],
                "action": action,
                "due": due,
                "tier": tier,
            })

    capped = [
        d for d in decisions
        if d["action"] == "delete" or (ANONYMISE_CAPPED and d["action"] == "anonymise")
    ]
    capped.sort(key=lambda d: (d["tier"], d["due"], d["account_id"]))
    deferred = capped[DELETE_CAP:]
    for d in deferred:
        d["action"] = None
    if deferred:
        logger.info("deferred %d actions over the delete cap", len(deferred))

    out = []
    for d in decisions:
        if d["action"] is None:
            continue
        out.append({
            "account_id": d["account_id"],
            "action": d["action"],
            "due": d["due"].isoformat(),
            "approved_by": None if d["action"] == "warn" else APPROVER,
        })
    out.sort(key=lambda r: r["account_id"])
    logger.info("planned %d actions for %d accounts", len(out), len(accounts))
    return out


# ---------------------------------------------------------------- tests

TODAY = date(2026, 10, 13)


def _acc(i, last_seen=None, closed_at=None, closed_by=None, unpaid=0,
         hold=False, email=None):
    return {
        "id": i,
        "email": email if email is not None else f"member{i}@example.com",
        "status": "active",
        "last_seen_at": last_seen,
        "last_login": None,
        "closed_at": closed_at,
        "closed_by": closed_by,
        "unpaid_invoices": unpaid,
        "litigation_hold": hold,
        "tenant": "tidewater",
    }


def _ls(due):
    """last_seen_at that yields inactive due date `due`."""
    return due - timedelta(days=INACTIVE_DAYS)


class PlanPurgeTests(unittest.TestCase):

    def test_empty_input(self):
        self.assertEqual(plan_purge([], TODAY), [])

    def test_730_days_after_last_seen_gives_delete(self):
        acc = _acc(1, last_seen=date(2024, 10, 13))
        self.assertEqual(plan_purge([acc], TODAY), [
            {"account_id": 1, "action": "delete", "due": "2026-10-13",
             "approved_by": APPROVER},
        ])

    def test_same_account_with_invoices_gives_anonymise(self):
        acc = _acc(1, last_seen=date(2024, 10, 13), unpaid=1)
        res = plan_purge([acc], TODAY)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["action"], "anonymise")
        self.assertEqual(res[0]["due"], "2026-10-13")

    def test_member_closed_30_days_gives_delete_at_closed_plus_30(self):
        acc = _acc(1, closed_at=date(2026, 9, 1), closed_by="member")
        res = plan_purge([acc], TODAY)
        self.assertEqual(res[0]["action"], "delete")
        self.assertEqual(res[0]["due"], "2026-10-01")

    def test_inactive_due_35_days_out_warns(self):
        acc = _acc(1, last_seen=_ls(TODAY + timedelta(days=35)))
        res = plan_purge([acc], TODAY)
        self.assertEqual(res[0]["action"], "warn")
        self.assertIsNone(res[0]["approved_by"])

    def test_staff_closed_warns_but_member_closed_does_not(self):
        staff = _acc(1, closed_at=TODAY, closed_by="staff")
        member = _acc(2, closed_at=TODAY, closed_by="member")
        res = plan_purge([staff, member], TODAY)
        self.assertEqual(res, [
            {"account_id": 1, "action": "warn", "due": "2026-11-12",
             "approved_by": None},
        ])

    def test_unknown_closed_by_still_warns(self):
        acc = _acc(1, closed_at=TODAY, closed_by="other")
        res = plan_purge([acc], TODAY)
        self.assertEqual(res[0]["action"], "warn")

    def test_due_exactly_today_plus_40_warns(self):
        acc = _acc(1, last_seen=_ls(TODAY + timedelta(days=40)))
        self.assertEqual(plan_purge([acc], TODAY)[0]["action"], "warn")

    def test_due_today_plus_41_gives_nothing(self):
        acc = _acc(1, last_seen=_ls(TODAY + timedelta(days=41)))
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_due_today_is_delete_or_anonymise_never_warn(self):
        d = _acc(1, last_seen=_ls(TODAY))
        a = _acc(2, last_seen=_ls(TODAY), unpaid=3)
        res = plan_purge([d, a], TODAY)
        self.assertEqual([r["action"] for r in res], ["delete", "anonymise"])

    def test_litigation_hold_gives_nothing(self):
        overdue = _acc(1, last_seen=_ls(TODAY - timedelta(days=100)), hold=True)
        window = _acc(2, last_seen=_ls(TODAY + timedelta(days=10)), hold=True)
        self.assertEqual(plan_purge([overdue, window], TODAY), [])

    def test_staff_email_mixed_case_gives_nothing(self):
        acc = _acc(1, last_seen=_ls(TODAY - timedelta(days=5)),
                   email="  Jane.Doe@TIDEWATER-Klatring.NO ")
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_lookalike_domains_are_not_staff(self):
        a = _acc(1, last_seen=_ls(TODAY), email="x@mail.tidewater-klatring.no")
        b = _acc(2, last_seen=_ls(TODAY),
                 email="x@tidewater-klatring.no.example.com")
        res = plan_purge([a, b], TODAY)
        self.assertEqual([r["action"] for r in res], ["delete", "delete"])

    def test_recent_last_seen_with_old_last_login_no_delete(self):
        acc = _acc(1, last_seen=TODAY - timedelta(days=10))
        acc["last_login"] = date(2000, 1, 1)
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_cap_prioritises_member_closed_and_keeps_anonymise_and_warn(self):
        accounts = []
        for i in range(250):
            accounts.append(_acc(i + 1,
                                 closed_at=TODAY - timedelta(days=60 + i // 3),
                                 closed_by="member"))
        for j in range(10):
            accounts.append(_acc(301 + j,
                                 last_seen=TODAY - timedelta(days=800 + j)))
        for k in range(4):
            accounts.append(_acc(501 + k,
                                 last_seen=TODAY - timedelta(days=900 + k),
                                 unpaid=2))
        for k in range(3):
            accounts.append(_acc(401 + k,
                                 last_seen=_ls(TODAY + timedelta(days=20))))

        result = plan_purge(accounts, TODAY)

        def ids(action):
            return sorted(r["account_id"] for r in result if r["action"] == action)

        deletes = ids("delete")
        self.assertEqual(len(deletes), 200)

        due_by_id = {i: TODAY - timedelta(days=30 + i // 3) for i in range(1, 251)}
        expected_order = sorted(range(1, 251), key=lambda i: (due_by_id[i], i))
        self.assertEqual(set(deletes), set(expected_order[:200]))
        deferred = set(expected_order[200:])
        self.assertTrue(deferred.isdisjoint(deletes))
        self.assertEqual(len(deferred), 50)

        self.assertEqual(ids("warn"), [401, 402, 403])
        self.assertEqual(ids("anonymise"), [501, 502, 503, 504])
        self.assertTrue(set(range(301, 311)).isdisjoint(deletes))

    def test_output_sorted_with_exact_keys_and_approved_by(self):
        accounts = [
            _acc(9, last_seen=_ls(TODAY - timedelta(days=5))),
            _acc(2, last_seen=_ls(TODAY + timedelta(days=10))),
            _acc(5, last_seen=_ls(TODAY - timedelta(days=1)), unpaid=1),
            _acc(7, closed_at=TODAY, closed_by="staff"),
            _acc(1, closed_at=TODAY - timedelta(days=40), closed_by="member"),
        ]
        res = plan_purge(accounts, TODAY)
        self.assertEqual(res, [
            {"account_id": 1, "action": "delete", "due": "2026-10-03",
             "approved_by": APPROVER},
            {"account_id": 2, "action": "warn", "due": "2026-10-23",
             "approved_by": None},
            {"account_id": 5, "action": "anonymise", "due": "2026-10-12",
             "approved_by": APPROVER},
            {"account_id": 7, "action": "warn", "due": "2026-11-12",
             "approved_by": None},
            {"account_id": 9, "action": "delete", "due": "2026-10-08",
             "approved_by": APPROVER},
        ])
        for r in res:
            self.assertEqual(set(r.keys()),
                             {"account_id", "action", "due", "approved_by"})

    def test_approver_is_nfc_normalised(self):
        self.assertTrue(unicodedata.is_normalized("NFC", APPROVER))
        self.assertEqual(APPROVER, "Þórdís Sveinbjörnsdóttir")

    def test_json_output_never_contains_email(self):
        secret = "Secret.Person@Example.org"
        accounts = [
            _acc(1, last_seen=_ls(TODAY), email=secret),
            _acc(2, last_seen=_ls(TODAY + timedelta(days=20)), email=secret),
            _acc(3, last_seen=_ls(TODAY), email=None),
            _acc(4, closed_at=TODAY + timedelta(days=1), closed_by="staff",
                 email=secret),
            _acc(5, closed_by="member", email=secret),
            _acc(6, last_seen=_ls(TODAY), email=secret, unpaid=None),
        ]
        text = json.dumps(plan_purge(accounts, TODAY))
        self.assertNotIn("Person", text)
        self.assertNotIn("example", text.lower())
        self.assertNotIn("@", text)

    def test_exception_message_does_not_leak_email(self):
        secret = "Secret.Person@Example.org"
        bad = _acc(7, last_seen=datetime(2024, 1, 1), email=secret)
        with self.assertRaises(TypeError) as cm:
            plan_purge([bad], TODAY)
        self.assertNotIn("Person", str(cm.exception))
        self.assertNotIn("@", str(cm.exception))

    def test_closed_at_future_skipped_rest_unaffected(self):
        accounts = [
            _acc(1, closed_at=TODAY + timedelta(days=1), closed_by="staff"),
            _acc(2, last_seen=_ls(TODAY)),
        ]
        res = plan_purge(accounts, TODAY)
        self.assertEqual([r["account_id"] for r in res], [2])

    def test_unpaid_none_is_skipped(self):
        accounts = [
            _acc(1, last_seen=_ls(TODAY), unpaid=None),
            _acc(2, last_seen=_ls(TODAY)),
        ]
        res = plan_purge(accounts, TODAY)
        self.assertEqual([r["account_id"] for r in res], [2])

    def test_missing_email_is_skipped(self):
        acc = _acc(1, last_seen=_ls(TODAY), email="   ")
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_litigation_hold_none_is_skipped(self):
        acc = _acc(1, last_seen=_ls(TODAY))
        acc["litigation_hold"] = None
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_member_closed_without_closed_at_skipped(self):
        acc = _acc(1, last_seen=_ls(TODAY), closed_by="member")
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_both_dates_none_skipped(self):
        acc = _acc(1)
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_duplicate_ids_raise(self):
        with self.assertRaises(ValueError):
            plan_purge([_acc(1), _acc(1)], TODAY)

    def test_datetime_today_raises(self):
        with self.assertRaises(TypeError):
            plan_purge([], datetime(2026, 10, 13))

    def test_non_date_today_raises(self):
        with self.assertRaises(TypeError):
            plan_purge([], "2026-10-13")

    def test_datetime_field_raises(self):
        with self.assertRaises(TypeError):
            plan_purge([_acc(1, last_seen=datetime(2024, 1, 1))], TODAY)

    def test_string_last_seen_raises(self):
        with self.assertRaises(TypeError):
            plan_purge([_acc(1, last_seen="2024-01-01")], TODAY)

    def test_non_list_accounts_raises(self):
        with self.assertRaises(TypeError):
            plan_purge(tuple(), TODAY)

    def test_leap_year_due_uses_timedelta(self):
        acc = _acc(1, last_seen=date(2024, 2, 29))
        res = plan_purge([acc], date(2026, 2, 28))
        self.assertEqual(res[0]["due"], "2026-02-28")
        self.assertEqual(res[0]["action"], "delete")
        res = plan_purge([acc], date(2026, 2, 27))
        self.assertEqual(res[0]["action"], "warn")
        self.assertEqual(res[0]["due"], "2026-02-28")


if __name__ == "__main__":
    unittest.main()