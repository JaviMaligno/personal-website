# tidewater_purge.py
"""GDPR clean-up planning for Tidewater Climbing member accounts.

plan_purge(accounts, today) is pure: no clock reads, no I/O, inputs are not mutated.
Decisions applied: D1 warn window is due in (today, today+14]; D2 due account with unpaid
invoices gets only anonymise; D3 the 200 cap applies only to deletes; D4 status is ignored;
D5 members with unpaid invoices still get a warn inside the window.
Not executed: no file or interpreter tools were available when this was written, so tests were not run.
"""
from datetime import date, timedelta

DPO_APPROVER = "Tordis Svenbjorn Dottir"
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200
_VALID_CLOSED_BY = ("member", "staff", None)


def _is_staff(email):
    if not isinstance(email, str):
        return False
    return email.strip().lower().endswith(STAFF_EMAIL_SUFFIX)


def _validate(acc):
    acc_id = acc["id"]
    if acc["closed_by"] not in _VALID_CLOSED_BY:
        raise ValueError(
            f"account {acc_id!r}: closed_by must be 'member', 'staff' or None, "
            f"got {acc['closed_by']!r}"
        )
    last_seen = acc.get("last_seen_at")
    if last_seen is None:
        raise ValueError(f"account {acc_id!r}: last_seen_at is missing or None")
    if not isinstance(last_seen, date):
        raise TypeError(f"account {acc_id!r}: last_seen_at must be a datetime.date")
    closed_at = acc["closed_at"]
    if closed_at is not None and not isinstance(closed_at, date):
        raise TypeError(f"account {acc_id!r}: closed_at must be a datetime.date or None")


def _due(acc):
    inactive_due = acc["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
    if acc["closed_at"] is None:
        return inactive_due
    return min(acc["closed_at"] + timedelta(days=CLOSED_GRACE_DAYS), inactive_due)


def _action(account_id, action, due, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    if not isinstance(today, date):
        raise TypeError("today must be a datetime.date")
    for acc in accounts:
        _validate(acc)
    try:
        sorted(acc["id"] for acc in accounts)
    except TypeError as exc:
        raise ValueError("account ids must be mutually comparable") from exc

    warn_horizon = today + timedelta(days=WARN_WINDOW_DAYS)
    actions = []
    deletes = []  # (account, due) pairs subject to the cap

    for acc in accounts:
        if acc["litigation_hold"] or _is_staff(acc.get("email")):
            continue
        due = _due(acc)
        if due <= today:
            if acc["unpaid_invoices"] > 0:
                actions.append(_action(acc["id"], "anonymise", due, DPO_APPROVER))
            else:
                deletes.append((acc, due))
        elif due <= warn_horizon and acc["closed_by"] != "member":
            actions.append(_action(acc["id"], "warn", due, None))

    # Closed accounts first, then active; earlier due first; account_id as tie-break.
    deletes.sort(key=lambda pair: (pair[0]["closed_at"] is None, pair[1], pair[0]["id"]))
    for acc, due in deletes[:DELETE_CAP]:
        actions.append(_action(acc["id"], "delete", due, DPO_APPROVER))

    actions.sort(key=lambda a: a["account_id"])
    return actions


# test_tidewater_purge.py
import json
import unittest
from datetime import date, timedelta

from tidewater_purge import DPO_APPROVER, plan_purge

TODAY = date(2026, 10, 13)


def acct(id, last_seen, closed_at=None, closed_by=None, unpaid=0, hold=False,
         email="member@example.com", last_login=None):
    return {
        "id": id,
        "email": email,
        "status": "active",
        "last_seen_at": last_seen,
        "last_login": last_login,
        "closed_at": closed_at,
        "closed_by": closed_by,
        "unpaid_invoices": unpaid,
        "litigation_hold": hold,
    }


class PlanPurgeTests(unittest.TestCase):
    def test_active_exactly_730_days_deletes(self):
        acts = plan_purge([acct("a", TODAY - timedelta(days=730))], TODAY)
        self.assertEqual(len(acts), 1)
        self.assertEqual(acts[0]["action"], "delete")
        self.assertEqual(acts[0]["due"], TODAY.isoformat())
        self.assertEqual(acts[0]["approved_by"], DPO_APPROVER)

    def test_due_in_14_days_warns(self):
        due = TODAY + timedelta(days=14)
        acts = plan_purge([acct("a", due - timedelta(days=730))], TODAY)
        self.assertEqual([x["action"] for x in acts], ["warn"])
        self.assertIsNone(acts[0]["approved_by"])

    def test_due_in_15_days_nothing(self):
        due = TODAY + timedelta(days=15)
        self.assertEqual(plan_purge([acct("a", due - timedelta(days=730))], TODAY), [])

    def test_due_today_delete_only(self):
        acts = plan_purge([acct("a", TODAY - timedelta(days=730))], TODAY)
        self.assertEqual([x["action"] for x in acts], ["delete"])

    def test_member_closed_no_warn_then_delete_at_30_days(self):
        closed = TODAY - timedelta(days=30)
        for d in range(31):
            day = closed + timedelta(days=d)
            acts = plan_purge([acct("m", TODAY, closed_at=closed, closed_by="member")], day)
            self.assertNotIn("warn", [x["action"] for x in acts], f"warn on {day}")
        acts = plan_purge([acct("m", TODAY, closed_at=closed, closed_by="member")], TODAY)
        self.assertEqual([x["action"] for x in acts], ["delete"])

    def test_staff_closed_due_in_10_days_warns(self):
        closed = TODAY + timedelta(days=10) - timedelta(days=30)
        acts = plan_purge([acct("s", TODAY, closed_at=closed, closed_by="staff")], TODAY)
        self.assertEqual(len(acts), 1)
        self.assertEqual(acts[0]["action"], "warn")
        self.assertIsNone(acts[0]["approved_by"])
        self.assertEqual(acts[0]["due"], (TODAY + timedelta(days=10)).isoformat())

    def test_due_today_unpaid_anonymises_only(self):
        acts = plan_purge([acct("u", TODAY - timedelta(days=730), unpaid=2)], TODAY)
        self.assertEqual([x["action"] for x in acts], ["anonymise"])
        self.assertEqual(acts[0]["approved_by"], DPO_APPROVER)

    def test_litigation_hold_never_acts(self):
        for offset in range(-5, 40):
            day = TODAY + timedelta(days=offset)
            accounts = [
                acct("h1", TODAY - timedelta(days=730), hold=True),
                acct("h2", TODAY, closed_at=TODAY - timedelta(days=30),
                     closed_by="staff", unpaid=1, hold=True),
            ]
            self.assertEqual(plan_purge(accounts, day), [])

    def test_staff_email_any_case_no_action(self):
        for email in ["x@tidewater-klatring.no", "X@TIDEWATER-KLATRING.NO",
                      "  Pat@Tidewater-Klatring.no  "]:
            acts = plan_purge([acct("s", TODAY - timedelta(days=730), email=email)], TODAY)
            self.assertEqual(acts, [], email)

    def test_non_string_email_processed_normally(self):
        acts = plan_purge([acct("n", TODAY - timedelta(days=730), email=None)], TODAY)
        self.assertEqual([x["action"] for x in acts], ["delete"])

    def test_cap_250_candidates_with_30_closed(self):
        accounts = []
        for i in range(30):
            accounts.append(acct(f"c{i:03d}", TODAY, closed_at=TODAY - timedelta(days=60),
                                 closed_by="member"))
        for i in range(220):
            accounts.append(acct(f"a{i:03d}", TODAY - timedelta(days=730 + i)))
        accounts.reverse()
        acts = plan_purge(accounts, TODAY)
        deletes = [x["account_id"] for x in acts if x["action"] == "delete"]
        self.assertEqual(len(deletes), 200)
        closed_ids = {f"c{i:03d}" for i in range(30)}
        self.assertTrue(closed_ids <= set(deletes))
        self.assertEqual(set(deletes) - closed_ids,
                         {f"a{i:03d}" for i in range(50, 220)})

    def test_no_email_in_actions(self):
        secret = "secret.person@example.com"
        accounts = [acct("a", TODAY - timedelta(days=730), email=secret),
                    acct("b", TODAY, closed_at=TODAY - timedelta(days=30),
                         closed_by="staff", email=secret),
                    acct("c", TODAY - timedelta(days=720), email=secret)]
        acts = plan_purge(accounts, TODAY)
        self.assertNotIn("secret.person", json.dumps(acts))
        for x in acts:
            self.assertEqual(set(x), {"account_id", "action", "due", "approved_by"})

    def test_sorted_by_account_id_and_json_round_trip(self):
        accounts = [acct("m", TODAY - timedelta(days=730)),
                    acct("b", TODAY - timedelta(days=730), unpaid=1),
                    acct("z", TODAY - timedelta(days=716))]
        acts = plan_purge(accounts, TODAY)
        ids = [x["account_id"] for x in acts]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(json.loads(json.dumps(acts)), acts)

    def test_last_login_has_no_effect(self):
        base = [acct("a", TODAY - timedelta(days=730), last_login=None),
                acct("b", TODAY - timedelta(days=716), last_login=None)]
        other = [acct("a", TODAY - timedelta(days=730), last_login=TODAY),
                 acct("b", TODAY - timedelta(days=716), last_login=date(2000, 1, 1))]
        self.assertEqual(plan_purge(base, TODAY), plan_purge(other, TODAY))

    def test_bad_closed_by_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([acct("a", TODAY, closed_by="admin")], TODAY)

    def test_missing_last_seen_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([acct("a", None)], TODAY)

    def test_mixed_id_types_raise(self):
        with self.assertRaises(ValueError):
            plan_purge([acct(1, TODAY), acct("b", TODAY)], TODAY)


if __name__ == "__main__":
    unittest.main()