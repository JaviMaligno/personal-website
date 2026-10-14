# Tests were not executed in the authoring environment. Run `python3 -I tidewater_purge.py` to check.
"""Tidewater Climbing GDPR clean-up planner. Stdlib only. Entry point: plan_purge(accounts, today)."""
import json
import random
import unittest
from datetime import date, timedelta

DPO_NAME = "Þórdís Sveinbjörnsdóttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
DELETE_CAP = 200
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 40
VALID_CLOSED_BY = ("member", "staff")


def _is_staff(email):
    return isinstance(email, str) and email.lower().endswith(STAFF_SUFFIX)


def _validate(acct):
    if not isinstance(acct.get("last_seen_at"), date):
        raise ValueError(f"account {acct.get('id')!r}: last_seen_at must be a date")
    closed_at = acct.get("closed_at")
    if closed_at is not None and not isinstance(closed_at, date):
        raise ValueError(f"account {acct.get('id')!r}: closed_at must be a date or None")
    closed_by = acct.get("closed_by")
    if closed_by not in VALID_CLOSED_BY and not (closed_by is None and closed_at is None):
        raise ValueError(f"account {acct.get('id')!r}: unknown closed_by")


def _due(acct, today):
    due = acct["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
    closed_at = acct.get("closed_at")
    # A closed_at in the future is treated as not yet closed for the due calculation.
    if closed_at is not None and closed_at <= today:
        due = min(due, closed_at + timedelta(days=CLOSED_GRACE_DAYS))
    return due


def _action(acct, action, due):
    return {
        "account_id": acct["id"],
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else DPO_NAME,
    }


def plan_purge(accounts, today):
    if not isinstance(today, date):
        raise TypeError("today must be a datetime.date")
    accounts = list(accounts)
    if not accounts:
        return []

    ids = [a["id"] for a in accounts]
    if len({type(i) for i in ids}) > 1:
        raise TypeError("account ids must all share one type")
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate account ids in input")
    for a in accounts:
        _validate(a)

    actions = []
    deletes = []
    warn_limit = today + timedelta(days=WARN_WINDOW_DAYS)

    for a in accounts:
        if _is_staff(a.get("email")) or a.get("litigation_hold"):
            continue
        due = _due(a, today)
        if due <= today:
            if (a.get("unpaid_invoices") or 0) > 0:
                actions.append(_action(a, "anonymise", due))
            else:
                deletes.append((a, due))
        elif due <= warn_limit and a.get("closed_by") != "member":
            actions.append(_action(a, "warn", due))

    # Closed accounts first (any closed_at counts), then ascending due, then ascending id.
    deletes.sort(key=lambda p: (p[0].get("closed_at") is None, p[1], p[0]["id"]))
    for a, due in deletes[:DELETE_CAP]:
        actions.append(_action(a, "delete", due))

    actions.sort(key=lambda d: d["account_id"])
    return actions


def _acct(id_, email="member@example.org", last_seen=date(2026, 10, 1), closed_at=None,
          closed_by=None, unpaid=0, hold=False, last_login=date(2020, 1, 1)):
    return {
        "id": id_, "email": email, "status": "active", "last_seen_at": last_seen,
        "last_login": last_login, "closed_at": closed_at, "closed_by": closed_by,
        "unpaid_invoices": unpaid, "litigation_hold": hold,
    }


T = date(2026, 10, 13)


class PlanPurgeTests(unittest.TestCase):

    def test_delete_due_today(self):
        out = plan_purge([_acct(1, last_seen=date(2024, 10, 13))], T)
        self.assertEqual(out, [{"account_id": 1, "action": "delete",
                                "due": "2026-10-13", "approved_by": DPO_NAME}])

    def test_delete_past_due(self):
        out = plan_purge([_acct(1, last_seen=date(2024, 10, 12))], T)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], "2026-10-12")

    def test_warn_in_window(self):
        out = plan_purge([_acct(1, last_seen=date(2024, 10, 14))], T)
        self.assertEqual(out, [{"account_id": 1, "action": "warn",
                                "due": "2026-10-14", "approved_by": None}])

    def test_window_boundaries(self):
        self.assertEqual(plan_purge([_acct(1, last_seen=date(2024, 12, 22))], T), [])
        self.assertEqual(plan_purge([_acct(1, last_seen=date(2024, 11, 22))], T)[0]["action"], "warn")
        self.assertEqual(plan_purge([_acct(1, last_seen=date(2024, 11, 23))], T), [])

    def test_member_closed_grace_deletes_without_warn(self):
        a = _acct(1, last_seen=date(2026, 10, 1), closed_at=date(2026, 9, 13), closed_by="member")
        out = plan_purge([a], T)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], "2026-10-13")

    def test_member_closed_in_window_no_action(self):
        a = _acct(1, last_seen=date(2026, 10, 1), closed_at=date(2026, 9, 20), closed_by="member")
        self.assertEqual(plan_purge([a], T), [])

    def test_staff_closed_is_warned(self):
        a = _acct(1, last_seen=date(2026, 10, 1), closed_at=date(2026, 9, 20), closed_by="staff")
        out = plan_purge([a], T)
        self.assertEqual(out[0]["action"], "warn")
        self.assertEqual(out[0]["due"], "2026-10-20")

    def test_closed_sooner_than_inactivity(self):
        a = _acct(1, last_seen=date(2024, 10, 1), closed_at=date(2026, 10, 1), closed_by="staff")
        out = plan_purge([a], T)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], "2026-10-01")

    def test_future_closed_at_ignored_for_due(self):
        a = _acct(1, last_seen=date(2024, 10, 13), closed_at=date(2026, 11, 1), closed_by="staff")
        out = plan_purge([a], T)
        self.assertEqual(out[0]["due"], "2026-10-13")

    def test_anonymise_when_unpaid(self):
        a = _acct(1, last_seen=date(2024, 10, 13), unpaid=2)
        out = plan_purge([a], T)
        self.assertEqual(out, [{"account_id": 1, "action": "anonymise",
                                "due": "2026-10-13", "approved_by": DPO_NAME}])

    def test_anonymise_member_closed_with_unpaid(self):
        a = _acct(1, last_seen=date(2026, 10, 1), closed_at=date(2026, 9, 13),
                  closed_by="member", unpaid=1)
        self.assertEqual(plan_purge([a], T)[0]["action"], "anonymise")

    def test_warn_not_blocked_by_unpaid(self):
        a = _acct(1, last_seen=date(2024, 10, 14), unpaid=2)
        self.assertEqual(plan_purge([a], T)[0]["action"], "warn")

    def test_hold_blocks_delete_and_warn(self):
        self.assertEqual(plan_purge([_acct(1, last_seen=date(2024, 10, 13), hold=True)], T), [])
        self.assertEqual(plan_purge([_acct(1, last_seen=date(2024, 10, 14), hold=True)], T), [])

    def test_staff_excluded(self):
        self.assertEqual(plan_purge([_acct(1, email="x@tidewater-klatring.no",
                                           last_seen=date(2024, 10, 13))], T), [])
        self.assertEqual(plan_purge([_acct(1, email="x@tidewater-klatring.no",
                                           last_seen=date(2024, 10, 14))], T), [])

    def test_staff_suffix_is_case_insensitive(self):
        self.assertEqual(plan_purge([_acct(1, email="X@Tidewater-Klatring.NO",
                                           last_seen=date(2024, 10, 13))], T), [])

    def test_lookalike_domain_not_staff(self):
        out = plan_purge([_acct(1, email="x@tidewater-klatring.no.example.com",
                                last_seen=date(2024, 10, 13))], T)
        self.assertEqual(out[0]["action"], "delete")

    def test_last_login_never_read(self):
        self.assertEqual(plan_purge([_acct(1, last_login=date(1990, 1, 1))], T), [])
        out = plan_purge([_acct(1, last_seen=date(2024, 10, 12),
                                last_login=date(2026, 10, 12))], T)
        self.assertEqual(out[0]["action"], "delete")

    def test_cap_closed_first_then_oldest_open(self):
        accounts = []
        for i in range(60):
            accounts.append(_acct(f"c{i:03d}", last_seen=date(2026, 10, 1),
                                  closed_at=date(2026, 9, 13), closed_by="member"))
        for i in range(200):
            accounts.append(_acct(f"o{i:03d}", last_seen=date(2024, 10, 13) - timedelta(days=i)))
        out = plan_purge(accounts, T)
        deletes = {d["account_id"] for d in out if d["action"] == "delete"}
        self.assertEqual(len(deletes), DELETE_CAP)
        expected = {f"c{i:03d}" for i in range(60)} | {f"o{i:03d}" for i in range(60, 200)}
        self.assertEqual(deletes, expected)

    def test_exactly_200_all_deleted(self):
        accounts = [_acct(f"a{i:03d}", last_seen=date(2024, 10, 13)) for i in range(200)]
        out = plan_purge(accounts, T)
        self.assertEqual(sum(d["action"] == "delete" for d in out), 200)

    def test_anonymise_not_capped(self):
        accounts = [_acct(f"a{i:03d}", last_seen=date(2024, 10, 13)) for i in range(200)]
        accounts += [_acct(f"u{i:03d}", last_seen=date(2024, 10, 13), unpaid=1) for i in range(5)]
        out = plan_purge(accounts, T)
        self.assertEqual(sum(d["action"] == "delete" for d in out), 200)
        self.assertEqual(sum(d["action"] == "anonymise" for d in out), 5)

    def test_output_shape_and_name(self):
        accounts = [_acct(1, last_seen=date(2024, 10, 13)), _acct(2, last_seen=date(2024, 10, 14))]
        out = plan_purge(accounts, T)
        for d in out:
            self.assertEqual(set(d.keys()), {"account_id", "action", "due", "approved_by"})
            self.assertEqual(len(d["due"]), 10)
        self.assertEqual(out[0]["approved_by"], "Þórdís Sveinbjörnsdóttir")
        self.assertIsNone(out[1]["approved_by"])

    def test_no_email_in_output(self):
        emails = ["alpha@example.org", "beta@example.org", "gamma@tidewater-klatring.no"]
        accounts = [
            _acct(1, email=emails[0], last_seen=date(2024, 10, 13)),
            _acct(2, email=emails[1], last_seen=date(2024, 10, 14)),
            _acct(3, email=emails[2], last_seen=date(2024, 10, 13)),
        ]
        blob = json.dumps(plan_purge(accounts, T), ensure_ascii=False)
        for e in emails:
            self.assertNotIn(e, blob)

    def test_sorted_by_id_regardless_of_input_order(self):
        accounts = [_acct(i, last_seen=date(2024, 10, 13)) for i in range(20)]
        random.Random(7).shuffle(accounts)
        ids = [d["account_id"] for d in plan_purge(accounts, T)]
        self.assertEqual(ids, sorted(ids))

    def test_empty_input(self):
        self.assertEqual(plan_purge([], T), [])

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct(1), _acct(1)], T)

    def test_mixed_id_types_rejected(self):
        with self.assertRaises(TypeError):
            plan_purge([_acct(1), _acct("2")], T)

    def test_missing_last_seen_rejected(self):
        a = _acct(1)
        a["last_seen_at"] = None
        with self.assertRaises(ValueError):
            plan_purge([a], T)

    def test_unknown_closed_by_rejected(self):
        a = _acct(1, closed_at=date(2026, 9, 1), closed_by="admin")
        with self.assertRaises(ValueError):
            plan_purge([a], T)


if __name__ == "__main__":
    unittest.main()