"""Tidewater Climbing GDPR clean-up planner.

Assumptions beyond the stated requirements:
- Accounts with last_seen_at None are skipped entirely (R25), including any closed_at-based R7 date. Open question.
- status is not filtered (R26). Open question: the valid status values were not provided.
- Email matching is case-insensitive; a None email is treated as "" and is not staff.
- A warn is emitted for an account with unpaid invoices too, because R9 applies to every account due within 14 days.
- Accounts closed by a member get no warn (R10) but are still deleted or anonymised when due.
- Email is omitted from every action (R14, R29). This conflicts with the house rule to carry email in every action dict. The explicit client privacy requirements were followed. Confirm before release.
- Tests were written but not executed in this session.
"""

import unittest
from datetime import date, timedelta

DPO_APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVITY = timedelta(days=730)
CLOSED_GRACE = timedelta(days=30)
WARN_WINDOW = timedelta(days=14)
DELETE_CAP = 200


def _due_date(acc):
    due = acc["last_seen_at"] + INACTIVITY
    if acc.get("closed_at") is not None:
        due = min(due, acc["closed_at"] + CLOSED_GRACE)
    return due


def _in_scope(acc):
    if acc.get("litigation_hold"):
        return False
    if (acc.get("email") or "").lower().endswith(STAFF_SUFFIX):
        return False
    return acc.get("last_seen_at") is not None


def _action(acc, kind, due, approved_by):
    return {
        "account_id": acc["id"],
        "action": kind,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    actions = []
    deletable = []
    for acc in accounts:
        if not _in_scope(acc):
            continue
        due = _due_date(acc)
        if due <= today:
            if (acc.get("unpaid_invoices") or 0) > 0:
                actions.append(_action(acc, "anonymise", due, DPO_APPROVER))
            else:
                deletable.append((acc, due))
        elif due <= today + WARN_WINDOW and acc.get("closed_by") != "member":
            actions.append(_action(acc, "warn", due, None))

    # Closed accounts first, then earliest due date, then account_id.
    deletable.sort(key=lambda p: (p[0].get("closed_at") is None, p[1], p[0]["id"]))
    for acc, due in deletable[:DELETE_CAP]:
        actions.append(_action(acc, "delete", due, DPO_APPROVER))

    actions.sort(key=lambda a: a["account_id"])
    return actions


TODAY = date(2026, 10, 13)


def _acct(i="A1", offset=0, email="member@example.com", **kw):
    """Open account whose R6 due date is TODAY + offset days, unless overridden via kw."""
    acc = {
        "id": i,
        "email": email,
        "status": "active",
        "last_seen_at": TODAY + timedelta(days=offset) - INACTIVITY,
        "last_login": None,
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
    }
    acc.update(kw)
    return acc


class PlanPurgeTests(unittest.TestCase):

    def test_r6_delete_on_730th_day(self):
        acts = plan_purge([_acct("A", offset=0)], TODAY)
        self.assertEqual(acts, [{
            "account_id": "A", "action": "delete",
            "due": TODAY.isoformat(), "approved_by": DPO_APPROVER,
        }])

    def test_r6_not_deleted_before_730_days(self):
        acts = plan_purge([_acct("A", offset=1)], TODAY)
        self.assertNotIn("delete", [a["action"] for a in acts])

    def test_r7_closed_30_days_is_sooner(self):
        acc = _acct("C", offset=200, closed_at=TODAY - timedelta(days=30), closed_by="staff")
        acts = plan_purge([acc], TODAY)
        self.assertEqual(len(acts), 1)
        self.assertEqual(acts[0]["action"], "delete")
        self.assertEqual(acts[0]["due"], TODAY.isoformat())

    def test_r7_uses_earlier_r6_date_when_closed_later(self):
        acc = _acct("D", offset=0, closed_at=TODAY - timedelta(days=5), closed_by="member")
        acts = plan_purge([acc], TODAY)
        self.assertEqual(acts[0]["due"], TODAY.isoformat())

    def test_r8_overdue_and_due_today_are_deleted(self):
        acts = plan_purge([_acct("E", offset=-100), _acct("F", offset=0)], TODAY)
        self.assertEqual({a["account_id"]: a["action"] for a in acts},
                         {"E": "delete", "F": "delete"})

    def test_r9_warn_within_14_days(self):
        acts = plan_purge([_acct("G", offset=5)], TODAY)
        self.assertEqual(acts, [{
            "account_id": "G", "action": "warn",
            "due": (TODAY + timedelta(days=5)).isoformat(), "approved_by": None,
        }])

    def test_r10_no_warn_for_member_closed_but_warn_for_staff_closed(self):
        member = _acct("H", offset=100, closed_at=TODAY - timedelta(days=20), closed_by="member")
        staff = _acct("I", offset=100, closed_at=TODAY - timedelta(days=20), closed_by="staff")
        acts = plan_purge([member, staff], TODAY)
        self.assertEqual([(a["account_id"], a["action"]) for a in acts], [("I", "warn")])

    def test_r11_unpaid_invoices_anonymise(self):
        acts = plan_purge([_acct("J", offset=-1, unpaid_invoices=2)], TODAY)
        self.assertEqual(acts[0]["action"], "anonymise")
        self.assertEqual(acts[0]["approved_by"], DPO_APPROVER)

    def test_r11_none_unpaid_invoices_treated_as_zero(self):
        acts = plan_purge([_acct("K", offset=0, unpaid_invoices=None)], TODAY)
        self.assertEqual(acts[0]["action"], "delete")

    def test_r12_litigation_hold_untouched(self):
        accts = [_acct("L", offset=-1, litigation_hold=True),
                 _acct("M", offset=5, litigation_hold=True)]
        self.assertEqual(plan_purge(accts, TODAY), [])

    def test_r13_staff_excluded_case_insensitive(self):
        accts = [_acct("N", offset=-1, email="ops@TIDEWATER-klatring.NO"),
                 _acct("O", offset=5, email="x@tidewater-klatring.no")]
        self.assertEqual(plan_purge(accts, TODAY), [])

    def test_r14_member_email_never_in_output(self):
        accts = [_acct("P", offset=-1, email="secret.member@example.com"),
                 _acct("Q", offset=5, email="other.member@example.com")]
        self.assertNotIn("@", repr(plan_purge(accts, TODAY)))

    def test_r15_cap_closed_first_then_earliest_due(self):
        closed = [_acct(f"c{i:03d}", offset=300, closed_at=TODAY - timedelta(days=40),
                        closed_by="staff") for i in range(60)]
        open_ = [_acct(f"o{i:03d}", offset=-i) for i in range(150)]
        anon = [_acct("z-anon", offset=-500, unpaid_invoices=1)]
        acts = plan_purge(closed + open_ + anon, TODAY)
        deletes = {a["account_id"] for a in acts if a["action"] == "delete"}
        self.assertEqual(len(deletes), DELETE_CAP)
        self.assertTrue(all(f"c{i:03d}" in deletes for i in range(60)))
        self.assertTrue(all(f"o{i:03d}" not in deletes for i in range(10)))
        self.assertTrue(all(f"o{i:03d}" in deletes for i in range(10, 150)))
        self.assertIn(("z-anon", "anonymise"),
                      [(a["account_id"], a["action"]) for a in acts])

    def test_r17_sorted_by_account_id(self):
        accts = [_acct("B", offset=-1), _acct("C", offset=-1), _acct("A", offset=-1)]
        self.assertEqual([a["account_id"] for a in plan_purge(accts, TODAY)], ["A", "B", "C"])

    def test_r22_window_boundaries(self):
        accts = [_acct("due-today", offset=0),
                 _acct("due-plus1", offset=1),
                 _acct("due-plus14", offset=14),
                 _acct("due-plus15", offset=15)]
        acts = plan_purge(accts, TODAY)
        self.assertEqual({a["account_id"]: a["action"] for a in acts},
                         {"due-today": "delete", "due-plus1": "warn", "due-plus14": "warn"})

    def test_r25_null_last_seen_skipped(self):
        self.assertEqual(plan_purge([_acct("R", offset=-1, last_seen_at=None)], TODAY), [])


if __name__ == "__main__":
    unittest.main()