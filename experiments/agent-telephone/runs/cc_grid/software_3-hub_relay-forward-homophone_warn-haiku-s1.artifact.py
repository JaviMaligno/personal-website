# ---- file: purge_plan.py ----
# OPEN QUESTIONS FOR THE CLIENT (defaults implemented, shown in brackets):
# a. Warns repeat daily across the window, or once? [Daily.]
# b. Accounts being anonymised also get a warn? [Yes.]
# c. Day 40 inclusive? [Yes.]
# d. Does "closed" include staff-closed accounts? [Yes.]
# e. unpaid_invoices a count or boolean? [Non-zero means true.]
# f. Are anonymised accounts removed from input on later runs? [Must answer; otherwise they reappear daily.]
# g. Does status matter? [Ignored.]
# h. Staff domain match case-insensitive? [Yes.]
# i. Anonymise counts toward the 200 cap? [No.]
# j. Are deferred over-cap deletions reported anywhere? [No.]
# k. Is approved_by a fixed constant? [Yes.]

from datetime import date, datetime, timedelta

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_CAP = 200
INACTIVE_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_DAYS = 40
REQUIRED_FIELDS = (
    "id", "email", "last_seen_at", "closed_at",
    "closed_by", "unpaid_invoices", "litigation_hold",
)


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _id_key(acc_id):
    return (isinstance(acc_id, str), acc_id)


def _is_staff(email):
    return email.strip().lower().endswith(STAFF_DOMAIN)


def _member_closed(acc):
    return acc["closed_at"] is not None and acc["closed_by"] == "member"


def _validate(acc, index):
    if not isinstance(acc, dict):
        raise ValueError(f"account at index {index} is not a mapping")
    acc_id = acc.get("id")
    for field in REQUIRED_FIELDS:
        if field not in acc:
            raise ValueError(f"account {acc_id!r}: missing field {field!r}")
    if not isinstance(acc_id, (str, int)) or isinstance(acc_id, bool):
        raise ValueError(f"account {acc_id!r}: id must be str or int")
    if not isinstance(acc["email"], str):
        raise ValueError(f"account {acc_id!r}: email must be a string")
    if not _is_date(acc["last_seen_at"]):
        raise ValueError(f"account {acc_id!r}: last_seen_at must be a date")
    closed_at = acc["closed_at"]
    if closed_at is not None:
        if not _is_date(closed_at):
            raise ValueError(f"account {acc_id!r}: closed_at must be a date or None")
        if acc["closed_by"] not in ("member", "staff"):
            raise ValueError(f"account {acc_id!r}: closed_by must be 'member' or 'staff'")
    if not isinstance(acc["unpaid_invoices"], int):
        raise ValueError(f"account {acc_id!r}: unpaid_invoices must be an int")
    if not isinstance(acc["litigation_hold"], bool):
        raise ValueError(f"account {acc_id!r}: litigation_hold must be a bool")


def _effective_due(acc):
    due = acc["last_seen_at"] + timedelta(days=INACTIVE_DAYS)
    if acc["closed_at"] is not None:
        due = min(due, acc["closed_at"] + timedelta(days=CLOSED_GRACE_DAYS))
    return due


def _action(acc_id, action, due):
    return {
        "account_id": acc_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else APPROVER,
    }


def plan_purge(accounts, today):
    if not _is_date(today):
        raise ValueError("today must be a datetime.date")

    seen = set()
    for index, acc in enumerate(accounts):
        _validate(acc, index)
        if acc["id"] in seen:
            raise ValueError(f"duplicate account id {acc['id']!r}")
        seen.add(acc["id"])

    warn_until = today + timedelta(days=WARN_DAYS)
    results = []
    deletions = []

    for acc in accounts:
        if acc["litigation_hold"] or _is_staff(acc["email"]):
            continue
        try:
            due = _effective_due(acc)
        except OverflowError:
            raise ValueError(f"account {acc['id']!r}: date out of range") from None

        if due <= today:
            if acc["unpaid_invoices"]:
                results.append(_action(acc["id"], "anonymise", due))
            else:
                deletions.append((acc, due))
        elif due <= warn_until and not _member_closed(acc):
            results.append(_action(acc["id"], "warn", due))

    deletions.sort(key=lambda p: (p[0]["closed_at"] is None, p[1], _id_key(p[0]["id"])))
    for acc, due in deletions[:DELETE_CAP]:
        results.append(_action(acc["id"], "delete", due))

    results.sort(key=lambda r: _id_key(r["account_id"]))
    return results


# ---- file: test_purge_plan.py ----
import unittest
from datetime import date, timedelta

from purge_plan import APPROVER, plan_purge

TODAY = date(2026, 10, 13)


def acc(acc_id, last_seen, closed_at=None, closed_by=None, unpaid=0, hold=False, email=None):
    return {
        "id": acc_id,
        "email": email if email is not None else f"{acc_id}@example.com",
        "status": "active",
        "last_seen_at": last_seen,
        "last_login": None,
        "closed_at": closed_at,
        "closed_by": closed_by,
        "unpaid_invoices": unpaid,
        "litigation_hold": hold,
        "tenant": "legacy",
    }


def seen_for_due(due):
    return due - timedelta(days=730)


class PlanPurgeTests(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(plan_purge([], TODAY), [])

    def test_due_today_deleted_with_iso_date_and_approver(self):
        out = plan_purge([acc("a1", seen_for_due(TODAY))], TODAY)
        self.assertEqual(out, [{
            "account_id": "a1",
            "action": "delete",
            "due": "2026-10-13",
            "approved_by": "Þórdís Sveinbjörnsdóttir",
        }])

    def test_day_40_warned_day_41_not(self):
        out = plan_purge([
            acc("a1", seen_for_due(TODAY + timedelta(days=40))),
            acc("a2", seen_for_due(TODAY + timedelta(days=41))),
        ], TODAY)
        self.assertEqual([(r["account_id"], r["action"]) for r in out], [("a1", "warn")])

    def test_warn_has_no_approver(self):
        out = plan_purge([acc("a1", seen_for_due(TODAY + timedelta(days=5)))], TODAY)
        self.assertEqual(out[0]["action"], "warn")
        self.assertIsNone(out[0]["approved_by"])

    def test_closed_by_member_not_warned(self):
        a = acc("a1", TODAY - timedelta(days=900), closed_at=TODAY - timedelta(days=25), closed_by="member")
        self.assertEqual(plan_purge([a], TODAY), [])

    def test_closed_by_staff_warned(self):
        a = acc("a1", TODAY - timedelta(days=900), closed_at=TODAY - timedelta(days=25), closed_by="staff")
        out = plan_purge([a], TODAY)
        self.assertEqual(out[0]["action"], "warn")
        self.assertEqual(out[0]["due"], "2026-10-18")

    def test_closed_grace_earlier_than_inactivity(self):
        a = acc("a1", TODAY - timedelta(days=900), closed_at=TODAY - timedelta(days=30), closed_by="staff")
        out = plan_purge([a], TODAY)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], "2026-10-13")

    def test_closed_at_before_last_seen_uses_min(self):
        a = acc("a1", TODAY - timedelta(days=720), closed_at=TODAY - timedelta(days=800), closed_by="staff")
        out = plan_purge([a], TODAY)
        expected_due = (TODAY - timedelta(days=770)).isoformat()
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], expected_due)

    def test_member_closed_and_due_today_still_deleted(self):
        a = acc("a1", TODAY - timedelta(days=900), closed_at=TODAY - timedelta(days=30), closed_by="member")
        self.assertEqual(plan_purge([a], TODAY)[0]["action"], "delete")

    def test_staff_domain_excluded_case_insensitive(self):
        a = acc("a1", seen_for_due(TODAY), email="Someone@TIDEWATER-KLATRING.no")
        self.assertEqual(plan_purge([a], TODAY), [])

    def test_litigation_hold_excluded(self):
        due_today = acc("a1", seen_for_due(TODAY), unpaid=3, hold=True)
        in_window = acc("a2", seen_for_due(TODAY + timedelta(days=3)), hold=True)
        self.assertEqual(plan_purge([due_today, in_window], TODAY), [])

    def test_unpaid_due_today_anonymised(self):
        out = plan_purge([acc("a1", seen_for_due(TODAY), unpaid=2)], TODAY)
        self.assertEqual(out[0]["action"], "anonymise")
        self.assertEqual(out[0]["approved_by"], APPROVER)

    def test_unpaid_in_window_also_warned(self):
        out = plan_purge([acc("a1", seen_for_due(TODAY + timedelta(days=3)), unpaid=1)], TODAY)
        self.assertEqual(out[0]["action"], "warn")

    def test_cap_closed_first_then_oldest_and_anonymise_uncounted(self):
        accounts = []
        for i in range(300):
            accounts.append(acc(f"o{i:03d}", TODAY - timedelta(days=730 + i + 10)))
        for i in range(5):
            accounts.append(acc(f"c{i:03d}", TODAY - timedelta(days=700),
                                closed_at=TODAY - timedelta(days=30), closed_by="staff"))
        for i in range(10):
            accounts.append(acc(f"u{i:03d}", TODAY - timedelta(days=730), unpaid=1))

        out = plan_purge(accounts, TODAY)
        deletes = {r["account_id"] for r in out if r["action"] == "delete"}
        anon = {r["account_id"] for r in out if r["action"] == "anonymise"}

        closed = {f"c{i:03d}" for i in range(5)}
        expected_open = {f"o{i:03d}" for i in range(105, 300)}
        self.assertEqual(len(deletes), 200)
        self.assertEqual(len(anon), 10)
        self.assertTrue(closed <= deletes)
        self.assertEqual(deletes - closed, expected_open)

    def test_sorted_by_account_id(self):
        accounts = [acc(i, seen_for_due(TODAY)) for i in ["b", "a", "c"]]
        ids = [r["account_id"] for r in plan_purge(accounts, TODAY)]
        self.assertEqual(ids, sorted(ids))

    def test_due_is_iso_string(self):
        out = plan_purge([acc("a1", seen_for_due(TODAY + timedelta(days=2)))], TODAY)
        self.assertIsInstance(out[0]["due"], str)
        self.assertEqual(date.fromisoformat(out[0]["due"]), TODAY + timedelta(days=2))

    def test_no_email_in_output(self):
        accounts = [
            acc("a1", seen_for_due(TODAY), email="secret.person@example.com"),
            acc("a2", seen_for_due(TODAY + timedelta(days=1)), email="secret.person@example.com"),
        ]
        text = repr(plan_purge(accounts, TODAY))
        self.assertNotIn("secret", text)
        self.assertNotIn("@", text)

    def test_duplicate_id_raises(self):
        accounts = [acc("a1", seen_for_due(TODAY)), acc("a1", seen_for_due(TODAY))]
        with self.assertRaises(ValueError):
            plan_purge(accounts, TODAY)

    def test_bad_date_error_names_only_id(self):
        bad = acc("a1", TODAY, email="leak@example.com")
        bad["last_seen_at"] = "2026-01-01"
        with self.assertRaises(ValueError) as ctx:
            plan_purge([bad], TODAY)
        msg = str(ctx.exception)
        self.assertIn("a1", msg)
        self.assertNotIn("leak", msg)
        self.assertNotIn("@", msg)


if __name__ == "__main__":
    unittest.main()