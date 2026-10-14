# Not executed: this environment has no tools, so the tests below have not been run. Run with: python3 -I -m unittest <path-to-this-file>
import unicodedata
import unittest
from datetime import date, datetime, timedelta

DPO_APPROVER = unicodedata.normalize("NFC", "Þórdís Sveinbjörnsdóttir")
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY_PERIOD = timedelta(days=730)
CLOSED_GRACE_PERIOD = timedelta(days=30)
WARN_WINDOW = timedelta(days=40)
DELETE_CAP = 200


def _require_date(name, value):
    if isinstance(value, datetime) or not isinstance(value, date):
        raise TypeError(f"{name} must be datetime.date, got {type(value).__name__}")
    return value


def _optional_date(name, value):
    if value is None:
        return None
    return _require_date(name, value)


def is_staff_email(email):
    return str(email or "").strip().lower().endswith(STAFF_DOMAIN)


def is_excluded(account):
    return is_staff_email(account.get("email")) or bool(account.get("litigation_hold"))


def compute_due(last_seen_at, closed_at):
    due = last_seen_at + INACTIVITY_PERIOD
    if closed_at is not None:
        due = min(due, closed_at + CLOSED_GRACE_PERIOD)
    return due


def classify(due, today, closed_by):
    """Return 'due', 'warn' or None."""
    if due <= today:
        return "due"
    if due <= today + WARN_WINDOW and closed_by != "member":
        return "warn"
    return None


def _action(account_id, action, due, approver=DPO_APPROVER):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approver,
    }


def plan_purge(accounts, today):
    _require_date("today", today)
    actions = []
    deletable = []  # (closed_group, due, account_id)

    for account in accounts:
        if is_excluded(account):
            continue

        account_id = account["id"]
        last_seen = _require_date("last_seen_at", account["last_seen_at"])
        closed_at = _optional_date("closed_at", account.get("closed_at"))
        due = compute_due(last_seen, closed_at)
        status = classify(due, today, account.get("closed_by"))
        has_unpaid = (account.get("unpaid_invoices") or 0) > 0

        if status == "due":
            if has_unpaid:
                actions.append(_action(account_id, "anonymise", due))
            else:
                closed_group = 0 if closed_at is not None else 1
                deletable.append((closed_group, due, account_id))
        elif status == "warn":
            actions.append(_action(account_id, "warn", due, approver=None))

    deletable.sort(key=lambda t: (t[0], t[1], t[2]))
    for _group, due, account_id in deletable[:DELETE_CAP]:
        actions.append(_action(account_id, "delete", due))

    actions.sort(key=lambda a: a["account_id"])
    return actions


# ---------------------------------------------------------------- tests

TODAY = date(2026, 10, 13)


def make_account(account_id, last_seen_at=TODAY, closed_at=None, closed_by="member",
                 unpaid_invoices=0, litigation_hold=False, email=None):
    return {
        "id": account_id,
        "email": email or f"member{account_id}@example.org",
        "status": "active",
        "last_seen_at": last_seen_at,
        "last_login": None,
        "closed_at": closed_at,
        "closed_by": closed_by,
        "unpaid_invoices": unpaid_invoices,
        "litigation_hold": litigation_hold,
    }


def ids_with(actions, action):
    return {a["account_id"] for a in actions if a["action"] == action}


class PlanPurgeTests(unittest.TestCase):

    def test_due_exactly_730_days_after_last_seen_gives_delete(self):
        last_seen = TODAY - timedelta(days=730)
        out = plan_purge([make_account(1, last_seen_at=last_seen)], TODAY)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], TODAY.isoformat())

    def test_one_day_before_due_gives_no_delete(self):
        last_seen = TODAY - timedelta(days=730)
        out = plan_purge([make_account(1, last_seen_at=last_seen)], TODAY - timedelta(days=1))
        self.assertNotIn(1, ids_with(out, "delete"))

    def test_closed_plus_30_earlier_sets_due(self):
        out = plan_purge(
            [make_account(1, last_seen_at=TODAY - timedelta(days=5),
                          closed_at=TODAY - timedelta(days=30), closed_by="member")],
            TODAY,
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], TODAY.isoformat())

    def test_equal_closed_and_inactive_due_gives_single_action(self):
        acc = make_account(1, last_seen_at=TODAY - timedelta(days=700),
                           closed_at=TODAY, closed_by="staff")
        out = plan_purge([acc], TODAY)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "warn")
        self.assertEqual(out[0]["due"], (TODAY + timedelta(days=30)).isoformat())

    def test_closed_later_than_last_seen_rule_uses_last_seen(self):
        last_seen = TODAY - timedelta(days=720)  # inactivity due = TODAY + 10
        acc = make_account(1, last_seen_at=last_seen, closed_at=TODAY, closed_by="staff")
        out = plan_purge([acc], TODAY)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "warn")
        self.assertEqual(out[0]["due"], (TODAY + timedelta(days=10)).isoformat())

    def test_warn_at_day_40_inclusive(self):
        acc = make_account(1, last_seen_at=TODAY + timedelta(days=40) - INACTIVITY_PERIOD)
        out = plan_purge([acc], TODAY)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "warn")
        self.assertIsNone(out[0]["approved_by"])

    def test_no_warn_at_day_41(self):
        acc = make_account(1, last_seen_at=TODAY + timedelta(days=41) - INACTIVITY_PERIOD)
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_no_warn_for_member_closed(self):
        acc = make_account(1, last_seen_at=TODAY - timedelta(days=700),
                           closed_at=TODAY, closed_by="member")
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_warn_for_staff_closed(self):
        acc = make_account(1, last_seen_at=TODAY - timedelta(days=700),
                           closed_at=TODAY, closed_by="staff")
        out = plan_purge([acc], TODAY)
        self.assertEqual([a["action"] for a in out], ["warn"])

    def test_unpaid_due_now_gives_anonymise_and_no_cap_slot(self):
        deletable = [make_account(i, last_seen_at=TODAY - INACTIVITY_PERIOD) for i in range(1, 201)]
        anon = make_account(1000, last_seen_at=TODAY - INACTIVITY_PERIOD, unpaid_invoices=2)
        out = plan_purge(deletable + [anon], TODAY)
        self.assertEqual(ids_with(out, "anonymise"), {1000})
        self.assertEqual(ids_with(out, "delete"), set(range(1, 201)))

    def test_staff_email_produces_no_actions(self):
        acc = make_account(1, last_seen_at=TODAY - INACTIVITY_PERIOD,
                           email="  Someone@TIDEWATER-KLATRING.NO ")
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_litigation_hold_produces_no_actions_even_when_due(self):
        acc = make_account(2, last_seen_at=TODAY - INACTIVITY_PERIOD, litigation_hold=True)
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_cap_gives_exactly_200_deletes(self):
        accounts = [make_account(i, last_seen_at=TODAY - timedelta(days=730 + (i - 1)))
                    for i in range(1, 251)]
        out = plan_purge(accounts, TODAY)
        self.assertEqual(len(ids_with(out, "delete")), DELETE_CAP)
        # earliest due first: ids 250 down to 51 have the earliest due dates
        self.assertEqual(ids_with(out, "delete"), set(range(51, 251)))

    def test_closed_accounts_chosen_before_inactive(self):
        inactive = [make_account(i, last_seen_at=TODAY - timedelta(days=730 + (i - 1)))
                    for i in range(1, 151)]
        closed = [make_account(i, last_seen_at=TODAY - timedelta(days=1),
                               closed_at=TODAY - timedelta(days=40), closed_by="member")
                  for i in range(1001, 1101)]
        out = plan_purge(inactive + closed, TODAY)
        deletes = ids_with(out, "delete")
        self.assertEqual(len(deletes), DELETE_CAP)
        self.assertTrue(set(range(1001, 1101)).issubset(deletes))
        self.assertEqual(deletes - set(range(1001, 1101)), set(range(51, 151)))

    def test_tie_on_due_broken_by_lower_id(self):
        accounts = [make_account(i, last_seen_at=TODAY - INACTIVITY_PERIOD) for i in range(1, 202)]
        out = plan_purge(accounts, TODAY)
        self.assertEqual(ids_with(out, "delete"), set(range(1, 201)))

    def test_no_email_in_serialised_output(self):
        accounts = [
            make_account(1, last_seen_at=TODAY - INACTIVITY_PERIOD, email="jan.kowalski@example.org"),
            make_account(2, last_seen_at=TODAY - INACTIVITY_PERIOD, unpaid_invoices=1,
                         email="jan.kowalski2@example.org"),
            make_account(3, last_seen_at=TODAY + timedelta(days=10) - INACTIVITY_PERIOD,
                         email="jan.kowalski3@example.org"),
        ]
        dump = json.dumps(plan_purge(accounts, TODAY))
        self.assertNotIn("jan.kowalski", dump)
        self.assertNotIn("example.org", dump)
        self.assertNotIn("@", dump)

    def test_dpo_approver_on_delete_and_anonymise_warn_has_none(self):
        accounts = [
            make_account(1, last_seen_at=TODAY - INACTIVITY_PERIOD),
            make_account(2, last_seen_at=TODAY - INACTIVITY_PERIOD, unpaid_invoices=1),
            make_account(3, last_seen_at=TODAY + timedelta(days=5) - INACTIVITY_PERIOD),
        ]
        by_action = {a["action"]: a for a in plan_purge(accounts, TODAY)}
        self.assertEqual(by_action["delete"]["approved_by"], DPO_APPROVER)
        self.assertEqual(by_action["anonymise"]["approved_by"], DPO_APPROVER)
        self.assertIsNone(by_action["warn"]["approved_by"])

    def test_dpo_literal_is_nfc_and_has_expected_code_points(self):
        self.assertEqual(DPO_APPROVER, unicodedata.normalize("NFC", "Þórdís Sveinbjörnsdóttir"))
        self.assertTrue(unicodedata.is_normalized("NFC", DPO_APPROVER))
        self.assertIn("\u00de", DPO_APPROVER)   # Þ
        self.assertIn("\u00f3", DPO_APPROVER)   # ó
        self.assertIn("\u00ed", DPO_APPROVER)   # í
        self.assertIn("bj\u00f6rns", DPO_APPROVER)  # ö

    def test_output_sorted_iso_dates_and_exact_keys(self):
        accounts = [
            make_account(9, last_seen_at=TODAY - INACTIVITY_PERIOD),
            make_account(2, last_seen_at=TODAY - INACTIVITY_PERIOD, unpaid_invoices=1),
            make_account(5, last_seen_at=TODAY + timedelta(days=3) - INACTIVITY_PERIOD),
        ]
        out = plan_purge(accounts, TODAY)
        ids = [a["account_id"] for a in out]
        self.assertEqual(ids, sorted(ids))
        for a in out:
            self.assertEqual(set(a.keys()), {"account_id", "action", "due", "approved_by"})
            self.assertRegex(a["due"], r"^\d{4}-\d{2}-\d{2}$")
            date.fromisoformat(a["due"])

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(plan_purge([], TODAY), [])

    def test_datetime_field_raises_type_error(self):
        acc = make_account(1)
        acc["last_seen_at"] = datetime(2026, 1, 1, 12, 0)
        with self.assertRaises(TypeError):
            plan_purge([acc], TODAY)

    def test_none_last_seen_raises_type_error(self):
        acc = make_account(1)
        acc["last_seen_at"] = None
        with self.assertRaises(TypeError):
            plan_purge([acc], TODAY)


if __name__ == "__main__":
    unittest.main()