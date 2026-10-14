"""GDPR clean-up planner for Tidewater Climbing.

plan_purge(accounts, today) returns the planned actions. It is pure: no I/O,
no writes, and the inputs are not mutated.

Tests are embedded below. Run with: python -m unittest <path-to-this-file>
These tests have not been executed yet.

Open points (not blocking):
- Delete candidates beyond the 200 cap are dropped silently, with no count.
- status is ignored by all rules (X7, D5).
- Accounts with both last_seen_at and closed_at None produce no action (X1, D7).
- last_login is required as a key but its value is never read (R4).
- closed_by is only checked when closed_at is set (X4).
- R9 is applied literally: closed_by == "member" blocks warn even when closed_at is None.
- The cap tie-break (closed first, then earliest due, then account_id) is a PM choice.
- D1–D8 remain provisional until Mateusz confirms them.
"""
import copy
import datetime as dt
import unittest

DPO_NAME = "Þórdís Sveinbjörnsdóttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 40
DELETE_CAP = 200
REQUIRED_KEYS = (
    "id", "email", "status", "last_seen_at", "last_login",
    "closed_at", "closed_by", "unpaid_invoices", "litigation_hold",
)


def _is_date(value):
    return isinstance(value, dt.date) and not isinstance(value, dt.datetime)


def _is_id(value):
    return isinstance(value, (str, int)) and not isinstance(value, bool)


def _label(index, acc):
    if isinstance(acc, dict) and _is_id(acc.get("id")):
        return f"account {acc['id']}"
    return f"entry at index {index}"


def _validate(accounts, today):
    if not _is_date(today):
        raise ValueError("today must be a datetime.date")
    if not isinstance(accounts, list):
        raise ValueError("accounts must be a list")
    seen_ids = set()
    id_kinds = set()
    for index, acc in enumerate(accounts):
        label = _label(index, acc)
        if not isinstance(acc, dict):
            raise ValueError(f"{label} is not a dict")
        missing = [k for k in REQUIRED_KEYS if k not in acc]
        if missing:
            raise ValueError(f"{label} is missing keys: {', '.join(missing)}")
        if not _is_id(acc["id"]):
            raise ValueError(f"{label} has an invalid id")
        if acc["id"] in seen_ids:
            raise ValueError(f"duplicate account id {acc['id']}")
        seen_ids.add(acc["id"])
        id_kinds.add(type(acc["id"]))
        if len(id_kinds) > 1:
            raise ValueError("account ids must all be str or all int")
        if not isinstance(acc["email"], str):
            raise ValueError(f"{label} has an invalid email")
        for key in ("last_seen_at", "closed_at"):
            if acc[key] is not None and not _is_date(acc[key]):
                raise ValueError(f"{label} has an invalid {key}")
        if acc["closed_at"] is not None and acc["closed_by"] not in ("member", "staff"):
            raise ValueError(f"{label} has an invalid closed_by")
        unpaid = acc["unpaid_invoices"]
        if not isinstance(unpaid, int) or isinstance(unpaid, bool) or unpaid < 0:
            raise ValueError(f"{label} has an invalid unpaid_invoices")
        if not isinstance(acc["litigation_hold"], bool):
            raise ValueError(f"{label} has an invalid litigation_hold")


def _is_staff(email):
    return email.lower().endswith(STAFF_SUFFIX)


def _action(account_id, action, due, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    _validate(accounts, today)
    warn_limit = today + dt.timedelta(days=WARN_WINDOW_DAYS)
    actions = []
    deletes = []
    for acc in accounts:
        if acc["litigation_hold"] or _is_staff(acc["email"]):
            continue
        candidates = []
        if acc["last_seen_at"] is not None:
            candidates.append(acc["last_seen_at"] + dt.timedelta(days=INACTIVITY_DAYS))
        if acc["closed_at"] is not None:
            candidates.append(acc["closed_at"] + dt.timedelta(days=CLOSED_GRACE_DAYS))
        if not candidates:
            continue
        due = min(candidates)
        account_id = acc["id"]
        if due <= today:
            if acc["unpaid_invoices"] > 0:
                actions.append(_action(account_id, "anonymise", due, DPO_NAME))
            else:
                closed_group = 0 if acc["closed_at"] is not None else 1
                deletes.append((closed_group, due, account_id))
        elif due <= warn_limit and acc["closed_by"] != "member":
            actions.append(_action(account_id, "warn", due, None))
    deletes.sort()
    for _, due, account_id in deletes[:DELETE_CAP]:
        actions.append(_action(account_id, "delete", due, DPO_NAME))
    actions.sort(key=lambda a: a["account_id"])
    return actions


TODAY = dt.date(2026, 10, 13)


def make(account_id, **overrides):
    acc = {
        "id": account_id,
        "email": f"member{account_id}@example.com",
        "status": "active",
        "last_seen_at": TODAY - dt.timedelta(days=10),
        "last_login": None,
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
        "tenant": "legacy-ignored",
    }
    acc.update(overrides)
    return acc


def seen_for(offset):
    """last_seen_at such that the inactivity due date is today + offset."""
    return TODAY + dt.timedelta(days=offset - INACTIVITY_DAYS)


def closed_for(offset):
    """closed_at such that the closure due date is today + offset."""
    return TODAY + dt.timedelta(days=offset - CLOSED_GRACE_DAYS)


class PlanPurgeTests(unittest.TestCase):
    def test_due_exactly_today_deletes(self):
        out = plan_purge([make("a", last_seen_at=seen_for(0))], TODAY)
        self.assertEqual(out, [{
            "account_id": "a",
            "action": "delete",
            "due": TODAY.isoformat(),
            "approved_by": DPO_NAME,
        }])

    def test_warn_at_today_plus_40_and_not_at_41(self):
        out = plan_purge([make("a", last_seen_at=seen_for(40))], TODAY)
        self.assertEqual(out[0]["action"], "warn")
        self.assertEqual(out[0]["due"], (TODAY + dt.timedelta(days=40)).isoformat())
        self.assertIsNone(out[0]["approved_by"])
        self.assertEqual(plan_purge([make("a", last_seen_at=seen_for(41))], TODAY), [])

    def test_day_729_warns_and_day_730_deletes(self):
        out = plan_purge([make("a", last_seen_at=TODAY - dt.timedelta(days=729))], TODAY)
        self.assertEqual(out[0]["action"], "warn")
        out = plan_purge([make("a", last_seen_at=TODAY - dt.timedelta(days=730))], TODAY)
        self.assertEqual(out[0]["action"], "delete")

    def test_closed_day_29_warns_and_day_30_deletes(self):
        out = plan_purge([make("a", closed_at=closed_for(1), closed_by="staff")], TODAY)
        self.assertEqual(out[0]["action"], "warn")
        out = plan_purge([make("a", closed_at=closed_for(0), closed_by="staff")], TODAY)
        self.assertEqual(out[0]["action"], "delete")

    def test_closed_member_excluded_from_warn(self):
        out = plan_purge([make("a", closed_at=closed_for(1), closed_by="member")], TODAY)
        self.assertEqual(out, [])

    def test_closed_member_still_deleted_when_due(self):
        out = plan_purge([make("a", closed_at=closed_for(0), closed_by="member")], TODAY)
        self.assertEqual(out[0]["action"], "delete")

    def test_cap_of_200_closed_first(self):
        accounts = []
        for j in range(30):
            accounts.append(make(
                f"c{j:03d}",
                last_seen_at=TODAY,
                closed_at=TODAY - dt.timedelta(days=31 + j),
                closed_by="member",
            ))
        for i in range(220):
            accounts.append(make(f"o{i:03d}", last_seen_at=TODAY - dt.timedelta(days=730 + i)))
        out = plan_purge(accounts, TODAY)
        deletes = {a["account_id"] for a in out if a["action"] == "delete"}
        expected = {f"c{j:03d}" for j in range(30)} | {f"o{i:03d}" for i in range(50, 220)}
        self.assertEqual(len(deletes), DELETE_CAP)
        self.assertEqual(deletes, expected)

    def test_anonymise_not_capped(self):
        accounts = [make(f"u{i:03d}", last_seen_at=TODAY - dt.timedelta(days=800),
                         unpaid_invoices=1) for i in range(210)]
        out = plan_purge(accounts, TODAY)
        self.assertEqual(len(out), 210)
        self.assertTrue(all(a["action"] == "anonymise" for a in out))

    def test_litigation_hold_and_staff_excluded(self):
        accounts = [
            make("h", last_seen_at=TODAY - dt.timedelta(days=2000), litigation_hold=True),
            make("s1", last_seen_at=TODAY - dt.timedelta(days=2000),
                 email="Anna.K@Tidewater-Klatring.NO"),
            make("s2", last_seen_at=TODAY - dt.timedelta(days=2000),
                 email="x@tidewater-klatring.no"),
        ]
        self.assertEqual(plan_purge(accounts, TODAY), [])

    def test_unpaid_due_is_anonymised(self):
        out = plan_purge([make("a", last_seen_at=TODAY - dt.timedelta(days=800),
                               unpaid_invoices=2)], TODAY)
        self.assertEqual(out[0]["action"], "anonymise")
        self.assertEqual(out[0]["approved_by"], DPO_NAME)

    def test_unpaid_due_within_window_still_warns(self):
        out = plan_purge([make("a", last_seen_at=seen_for(10), unpaid_invoices=3)], TODAY)
        self.assertEqual(out[0]["action"], "warn")

    def test_output_sorted_by_account_id(self):
        accounts = [make(x, last_seen_at=TODAY - dt.timedelta(days=800)) for x in ("c", "a", "b")]
        out = plan_purge(accounts, TODAY)
        self.assertEqual([a["account_id"] for a in out], ["a", "b", "c"])

    def test_dpo_name_exact(self):
        out = plan_purge([make("a", last_seen_at=TODAY - dt.timedelta(days=800))], TODAY)
        self.assertEqual(out[0]["approved_by"], "Þórdís Sveinbjörnsdóttir")

    def test_warn_has_null_approved_by_key(self):
        out = plan_purge([make("a", last_seen_at=seen_for(5))], TODAY)
        self.assertIn("approved_by", out[0])
        self.assertIsNone(out[0]["approved_by"])

    def test_no_dates_produces_nothing(self):
        self.assertEqual(plan_purge([make("a", last_seen_at=None)], TODAY), [])

    def test_closed_only_uses_closure_date(self):
        out = plan_purge([make("a", last_seen_at=None, closed_at=closed_for(0),
                               closed_by="member")], TODAY)
        self.assertEqual(out[0]["action"], "delete")

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            plan_purge([make("a"), make("a")], TODAY)

    def test_mixed_id_types_rejected(self):
        with self.assertRaises(ValueError):
            plan_purge([make("a"), make(1)], TODAY)

    def test_error_message_hides_email(self):
        bad = make("a", unpaid_invoices=-1)
        with self.assertRaises(ValueError) as ctx:
            plan_purge([bad], TODAY)
        message = str(ctx.exception)
        self.assertNotIn(bad["email"], message)
        self.assertIn("account a", message)

    def test_inputs_not_mutated(self):
        accounts = [make("a", last_seen_at=TODAY - dt.timedelta(days=800))]
        before = copy.deepcopy(accounts)
        plan_purge(accounts, TODAY)
        self.assertEqual(accounts, before)

    def test_output_keys_exact(self):
        out = plan_purge([make("a", last_seen_at=TODAY - dt.timedelta(days=800))], TODAY)
        self.assertEqual(set(out[0]), {"account_id", "action", "due", "approved_by"})


if __name__ == "__main__":
    unittest.main()