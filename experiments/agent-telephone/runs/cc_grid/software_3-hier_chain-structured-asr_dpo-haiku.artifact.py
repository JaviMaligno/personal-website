"""Tidewater Climbing GDPR purge planner.

Public API:
  plan_purge(accounts, today) -> list of action dicts (sorted by account_id)
  find_anomalies(accounts, today) -> list of {"account_id", "reason"} dicts

Error policy:
  TypeError for a wrong container/type of `today` or `accounts`.
  ValueError for any malformed account data (fail closed, no output).
  Error messages never include emails or other personal data.

Open questions (behaviour implemented as specified, not decided here):
  Q1 (P5): what `status` is for, and whether any rule should use it. Currently unused.
  Q2 (P7/D15): closed_by == "member" with closed_at None. Currently processed normally,
      warn suppressed, and reported by find_anomalies.
  Q3 (P1, P2, P3, P4, P6, P8): PM decisions to be confirmed with the client by the tech lead.
  Q4 (D9): fail closed on any malformed row. Confirm versus skipping bad rows.
  Q5 (D10, D11): accounts must be a list. Confirm whether other iterables should be accepted.
  Q6: anonymise actions are not counted toward the cap (P3). Confirm this holds for any future cap.
"""

import copy
import datetime
import unittest
from datetime import date, timedelta

DELETE_CAP = 200
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
APPROVER = "Tordis Svenbjorn Dottir"
STAFF_SUFFIX = "@tidewater-klatring.no"

_REQUIRED_KEYS = (
    "id", "email", "status", "last_seen_at", "last_login",
    "closed_at", "closed_by", "unpaid_invoices", "litigation_hold",
)


def _validate_today(today):
    if isinstance(today, datetime.datetime) or not isinstance(today, date):
        raise TypeError("today must be a datetime.date")


def _is_date_only(value):
    return isinstance(value, date) and not isinstance(value, datetime.datetime)


def _validate_accounts(accounts):
    if not isinstance(accounts, list):
        raise TypeError("accounts must be a list")
    seen = set()
    id_types = set()
    for index, account in enumerate(accounts):
        if not isinstance(account, dict):
            raise ValueError(f"account at index {index} is not a dict")
        for key in _REQUIRED_KEYS:
            if key not in account:
                raise ValueError(f"account at index {index} is missing key {key!r}")
        account_id = account["id"]
        if isinstance(account_id, bool) or not isinstance(account_id, (int, str)):
            raise ValueError(f"account at index {index} has an invalid id type")
        if account_id in seen:
            raise ValueError(f"duplicate account id {account_id!r}")
        seen.add(account_id)
        id_types.add(type(account_id))
        if not isinstance(account["email"], str):
            raise ValueError(f"account at index {index} field 'email' must be a string")
        if not _is_date_only(account["last_seen_at"]):
            raise ValueError(f"account at index {index} field 'last_seen_at' must be a date")
        closed_at = account["closed_at"]
        if closed_at is not None and not _is_date_only(closed_at):
            raise ValueError(f"account at index {index} field 'closed_at' must be None or a date")
        if closed_at is not None and account["closed_by"] not in ("member", "staff"):
            raise ValueError(
                f"account at index {index} field 'closed_by' must be 'member' or 'staff' "
                "when closed_at is set"
            )
    if len(id_types) > 1:
        raise ValueError("account ids must all be int or all be str")


def _due_date(account):
    base = account["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
    closed_at = account["closed_at"]
    if closed_at is not None:
        return min(base, closed_at + timedelta(days=CLOSED_GRACE_DAYS))
    return base


def _is_staff(email):
    return email.lower().endswith(STAFF_SUFFIX)


def _decide(account, today):
    if account["litigation_hold"]:
        return None
    if _is_staff(account["email"]):
        return None
    due = _due_date(account)
    if due <= today:
        return ("anonymise" if account["unpaid_invoices"] else "delete"), due
    if due <= today + timedelta(days=WARN_WINDOW_DAYS):
        if account["closed_by"] == "member":
            return None
        return "warn", due
    return None


def _select_under_cap(candidates, cap=DELETE_CAP):
    """candidates: list of (account_id, due, is_closed) tuples."""
    ordered = sorted(candidates, key=lambda c: (0 if c[2] else 1, c[1], c[0]))
    return ordered[:cap]


def _build_action(account_id, action, due_date, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due_date.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    _validate_today(today)
    _validate_accounts(accounts)
    deletes = []
    actions = []
    for account in accounts:
        decision = _decide(account, today)
        if decision is None:
            continue
        kind, due = decision
        if kind == "delete":
            deletes.append((account["id"], due, account["closed_at"] is not None))
        elif kind == "anonymise":
            actions.append(_build_action(account["id"], "anonymise", due, APPROVER))
        else:
            actions.append(_build_action(account["id"], "warn", due, None))
    for account_id, due, _ in _select_under_cap(deletes):
        actions.append(_build_action(account_id, "delete", due, APPROVER))
    actions.sort(key=lambda a: a["account_id"])
    return actions


def find_anomalies(accounts, today):
    _validate_today(today)
    _validate_accounts(accounts)
    return [
        {"account_id": a["id"], "reason": "closed_by is 'member' but closed_at is not set"}
        for a in accounts
        if a["closed_by"] == "member" and a["closed_at"] is None
    ]


TODAY = date(2026, 10, 13)


def _acct(account_id=1, **overrides):
    account = {
        "id": account_id,
        "email": f"m{account_id}@example.com",
        "status": "active",
        "last_seen_at": TODAY - timedelta(days=100),
        "last_login": TODAY - timedelta(days=100),
        "closed_at": None,
        "closed_by": "staff",
        "unpaid_invoices": False,
        "litigation_hold": False,
    }
    account.update(overrides)
    return account


def _seen_for(due):
    return due - timedelta(days=INACTIVITY_DAYS)


class PlanPurgeTests(unittest.TestCase):

    def test_empty_input(self):
        self.assertEqual(plan_purge([], TODAY), [])

    def test_last_seen_drives_inactivity_not_last_login(self):
        old_login = _acct(1, last_login=date(2000, 1, 1), last_seen_at=TODAY - timedelta(days=10))
        self.assertEqual(plan_purge([old_login], TODAY), [])
        stale = _acct(2, last_login=TODAY, last_seen_at=_seen_for(TODAY))
        self.assertEqual([a["action"] for a in plan_purge([stale], TODAY)], ["delete"])

    def test_due_boundaries(self):
        cases = [
            (TODAY, "delete"),
            (TODAY - timedelta(days=1), "delete"),
            (TODAY + timedelta(days=1), "warn"),
            (TODAY + timedelta(days=14), "warn"),
            (TODAY + timedelta(days=15), None),
        ]
        for due, expected in cases:
            with self.subTest(due=due):
                acts = plan_purge([_acct(1, last_seen_at=_seen_for(due))], TODAY)
                self.assertEqual(acts[0]["action"] if acts else None, expected)

    def test_closed_grace_wins_when_earlier(self):
        acct = _acct(1, last_seen_at=TODAY, closed_at=TODAY - timedelta(days=30), closed_by="member")
        acts = plan_purge([acct], TODAY)
        self.assertEqual(acts[0]["action"], "delete")
        self.assertEqual(acts[0]["due"], TODAY.isoformat())

    def test_base_rule_wins_when_closed_grace_later(self):
        acct = _acct(1, last_seen_at=_seen_for(TODAY + timedelta(days=5)), closed_at=TODAY)
        acts = plan_purge([acct], TODAY)
        self.assertEqual(acts[0]["action"], "warn")
        self.assertEqual(acts[0]["due"], (TODAY + timedelta(days=5)).isoformat())

    def test_closed_grace_due_string_when_earlier(self):
        acct = _acct(1, last_seen_at=_seen_for(TODAY + timedelta(days=100)),
                     closed_at=TODAY - timedelta(days=20), closed_by="staff")
        acts = plan_purge([acct], TODAY)
        self.assertEqual(acts[0]["due"], (TODAY + timedelta(days=10)).isoformat())

    def test_member_closed_suppresses_warn_but_not_delete(self):
        warn_window = _acct(1, last_seen_at=_seen_for(TODAY + timedelta(days=100)),
                            closed_at=TODAY - timedelta(days=20), closed_by="member")
        self.assertEqual(plan_purge([warn_window], TODAY), [])
        due_now = _acct(2, closed_at=TODAY - timedelta(days=30), closed_by="member",
                        last_seen_at=TODAY)
        self.assertEqual([a["action"] for a in plan_purge([due_now], TODAY)], ["delete"])

    def test_open_warn(self):
        acts = plan_purge([_acct(1, last_seen_at=_seen_for(TODAY + timedelta(days=5)))], TODAY)
        self.assertEqual(acts[0]["action"], "warn")
        self.assertIsNone(acts[0]["approved_by"])

    def test_unpaid_invoices_anonymise_or_warn(self):
        anon = plan_purge([_acct(1, last_seen_at=_seen_for(TODAY), unpaid_invoices=True)], TODAY)
        self.assertEqual(anon[0]["action"], "anonymise")
        self.assertEqual(anon[0]["approved_by"], APPROVER)
        warn = plan_purge([_acct(2, last_seen_at=_seen_for(TODAY + timedelta(days=5)),
                                 unpaid_invoices=True)], TODAY)
        self.assertEqual(warn[0]["action"], "warn")

    def test_litigation_hold_blocks_everything(self):
        cases = [
            dict(last_seen_at=_seen_for(TODAY)),
            dict(last_seen_at=_seen_for(TODAY), unpaid_invoices=True),
            dict(last_seen_at=_seen_for(TODAY + timedelta(days=5))),
        ]
        for kw in cases:
            with self.subTest(kw=kw):
                self.assertEqual(plan_purge([_acct(1, litigation_hold=True, **kw)], TODAY), [])

    def test_staff_exclusion_case_insensitive(self):
        for email in ["x@tidewater-klatring.no", "X@Tidewater-Klatring.NO"]:
            with self.subTest(email=email):
                acct = _acct(1, email=email, last_seen_at=_seen_for(TODAY))
                self.assertEqual(plan_purge([acct], TODAY), [])

    def test_staff_suffix_must_be_exact_at_end(self):
        # Decision: the suffix must match exactly at the end of the address.
        # Lookalike domains and subdomains are not staff and are processed normally.
        for email in ["x@tidewater-klatring.no.evil.example", "x@sub.tidewater-klatring.no"]:
            with self.subTest(email=email):
                acct = _acct(1, email=email, last_seen_at=_seen_for(TODAY))
                self.assertEqual([a["action"] for a in plan_purge([acct], TODAY)], ["delete"])

    def test_action_shape_and_no_email_in_output(self):
        accts = [
            _acct(1, email="secret.one@example.com", last_seen_at=_seen_for(TODAY)),
            _acct(2, email="secret.two@example.com", last_seen_at=_seen_for(TODAY), unpaid_invoices=True),
            _acct(3, email="secret.three@example.com", last_seen_at=_seen_for(TODAY + timedelta(days=3))),
        ]
        acts = plan_purge(accts, TODAY)
        self.assertEqual(len(acts), 3)
        for a in acts:
            self.assertEqual(set(a.keys()), {"account_id", "action", "due", "approved_by"})
            self.assertNotIn("@", str(a))
            self.assertNotIn("secret.", str(a))

    def test_cap_counts_deletes_only(self):
        def deletes(n):
            return [_acct(i, last_seen_at=_seen_for(TODAY - timedelta(days=1))) for i in range(1, n + 1)]
        self.assertEqual(len(plan_purge(deletes(200), TODAY)), 200)
        self.assertEqual(len(plan_purge(deletes(201), TODAY)), 200)
        anon = [_acct(i, last_seen_at=_seen_for(TODAY), unpaid_invoices=True) for i in range(1000, 1050)]
        acts = plan_purge(deletes(200) + anon, TODAY)
        self.assertEqual(len(acts), 250)
        self.assertEqual(sum(a["action"] == "delete" for a in acts), 200)
        self.assertEqual(sum(a["action"] == "anonymise" for a in acts), 50)

    def test_cap_keeps_closed_over_earlier_open_and_drops_largest_id(self):
        open_accts = [_acct(i, last_seen_at=_seen_for(TODAY - timedelta(days=100))) for i in range(1, 201)]
        closed = _acct(500, last_seen_at=_seen_for(TODAY - timedelta(days=1)),
                       closed_at=TODAY - timedelta(days=31), closed_by="member")
        acts = plan_purge(open_accts + [closed], TODAY)
        ids = {a["account_id"] for a in acts}
        self.assertEqual(len([a for a in acts if a["action"] == "delete"]), 200)
        self.assertIn(500, ids)
        self.assertNotIn(200, ids)
        self.assertEqual(len(acts), 200)

    def test_select_under_cap_order_and_tie_break(self):
        cands = [(5, TODAY - timedelta(10), False), (3, TODAY - timedelta(10), False),
                 (9, TODAY - timedelta(20), False), (7, TODAY - timedelta(30), True)]
        selected = _select_under_cap(cands, cap=3)
        self.assertEqual([c[0] for c in selected], [7, 9, 3])

    def test_output_sorted_after_cap_with_shuffled_input(self):
        accts = [_acct(i, last_seen_at=_seen_for(TODAY - timedelta(days=1))) for i in range(1, 202)]
        acts = plan_purge(list(reversed(accts)), TODAY)
        ids = [a["account_id"] for a in acts]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), 200)

    def test_due_is_iso_string(self):
        acts = plan_purge([_acct(1, last_seen_at=_seen_for(TODAY + timedelta(days=3)))], TODAY)
        self.assertIsInstance(acts[0]["due"], str)
        self.assertEqual(acts[0]["due"], (TODAY + timedelta(days=3)).isoformat())
        self.assertEqual(date.fromisoformat(acts[0]["due"]), TODAY + timedelta(days=3))

    def test_tenant_key_ignored(self):
        base = _acct(1, last_seen_at=_seen_for(TODAY))
        self.assertEqual(plan_purge([base], TODAY),
                         plan_purge([dict(base, tenant="acme")], TODAY))
        self.assertEqual(plan_purge([base], TODAY),
                         plan_purge([dict(base, tenant=None)], TODAY))

    def test_input_not_mutated(self):
        accts = [_acct(2, last_seen_at=_seen_for(TODAY)), _acct(1, last_seen_at=_seen_for(TODAY + timedelta(days=2)))]
        snapshot = copy.deepcopy(accts)
        plan_purge(accts, TODAY)
        self.assertEqual(accts, snapshot)

    def test_status_ignored(self):
        base = plan_purge([_acct(1, status="active", last_seen_at=_seen_for(TODAY))], TODAY)
        for status in ["closed", None, "anything"]:
            with self.subTest(status=status):
                self.assertEqual(
                    plan_purge([_acct(1, status=status, last_seen_at=_seen_for(TODAY))], TODAY), base)

    def test_leap_year_cases(self):
        acts = plan_purge([_acct(1, last_seen_at=date(2024, 2, 29))], TODAY)
        self.assertEqual(acts[0]["due"], "2026-02-28")
        self.assertEqual(_due_date(_acct(2, last_seen_at=date(2023, 3, 1))),
                         date(2023, 3, 1) + timedelta(days=730))
        closed = _acct(3, last_seen_at=date(2028, 1, 1), closed_at=date(2028, 1, 20), closed_by="staff")
        self.assertEqual(_due_date(closed), date(2028, 2, 19))

    def test_today_datetime_rejected(self):
        with self.assertRaises(TypeError):
            plan_purge([], datetime.datetime(2026, 10, 13))

    def test_accounts_must_be_list(self):
        with self.assertRaises(TypeError):
            plan_purge((_acct(1),), TODAY)

    def test_missing_key_raises(self):
        a = _acct(1)
        del a["closed_by"]
        with self.assertRaises(ValueError) as cm:
            plan_purge([a], TODAY)
        self.assertNotIn("@", str(cm.exception))

    def test_last_seen_string_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct(1, last_seen_at="2024-01-01")], TODAY)

    def test_last_seen_datetime_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct(1, last_seen_at=datetime.datetime(2024, 1, 1))], TODAY)

    def test_closed_at_datetime_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct(1, closed_at=datetime.datetime(2026, 1, 1), closed_by="staff")], TODAY)

    def test_invalid_closed_by_with_closed_at_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct(1, closed_at=TODAY, closed_by="robot")], TODAY)

    def test_duplicate_id_raises_without_email(self):
        accts = [_acct(1, email="dup.person@example.com"), _acct(1)]
        with self.assertRaises(ValueError) as cm:
            plan_purge(accts, TODAY)
        self.assertNotIn("dup.person", str(cm.exception))
        self.assertNotIn("@", str(cm.exception))

    def test_mixed_id_types_raise(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct(1), _acct("2")], TODAY)

    def test_bool_id_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct(True)], TODAY)

    def test_non_dict_element_raises(self):
        with self.assertRaises(ValueError):
            plan_purge(["not a dict"], TODAY)

    def test_closed_by_member_without_closed_at_is_anomaly_not_error(self):
        acct = _acct(1, closed_by="member", last_seen_at=_seen_for(TODAY + timedelta(days=5)))
        self.assertEqual(plan_purge([acct], TODAY), [])
        anomalies = find_anomalies([acct], TODAY)
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(set(anomalies[0].keys()), {"account_id", "reason"})
        self.assertEqual(anomalies[0]["account_id"], 1)
        self.assertNotIn("@", anomalies[0]["reason"])

    def test_approved_by_and_warn_none(self):
        acts = plan_purge([
            _acct(1, last_seen_at=_seen_for(TODAY)),
            _acct(2, last_seen_at=_seen_for(TODAY), unpaid_invoices=True),
            _acct(3, last_seen_at=_seen_for(TODAY + timedelta(days=2))),
        ], TODAY)
        by_action = {a["action"]: a["approved_by"] for a in acts}
        self.assertEqual(by_action["delete"], APPROVER)
        self.assertEqual(by_action["anonymise"], APPROVER)
        self.assertIsNone(by_action["warn"])

    def test_precedence_litigation_beats_staff_beats_delete(self):
        self.assertEqual(plan_purge([_acct(1, litigation_hold=True, email="a@tidewater-klatring.no",
                                           last_seen_at=_seen_for(TODAY))], TODAY), [])
        self.assertEqual(plan_purge([_acct(2, email="a@tidewater-klatring.no",
                                           last_seen_at=_seen_for(TODAY))], TODAY), [])
        acts = plan_purge([_acct(3, last_seen_at=_seen_for(TODAY))], TODAY)
        self.assertEqual(len(acts), 1)


if __name__ == "__main__":
    unittest.main()