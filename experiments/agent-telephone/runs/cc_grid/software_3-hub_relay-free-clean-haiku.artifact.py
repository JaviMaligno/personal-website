# Tidewater Climbing GDPR purge planner.
# This file was written without running it. The tests below have NOT been executed.
# Run them with: python -m unittest <path-to-this-file>
# Conflict to review: the brief requires exactly four keys per action and forbids the
# email in any output, because the audit log is shared with the federation. The team
# house rule asks every action dict to carry the email. This implementation follows the
# brief. Add an "email" key to the output only if the client confirms the audit log is
# not shared externally.

import copy
import datetime
import unittest

# ---- Choices the client has not confirmed (change here) ----
STAFF_DOMAIN = "@tidewater-klatring.no"
DPO_NAME = "Þórdís Sveinbjörnsdóttir"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14                    # day 14 is included
DELETE_CAP = 200
CAPPED_ACTIONS = frozenset({"delete"})   # add "anonymise" to cap it as well


def _in_scope(acc):
    # Default: every account is processed regardless of status.
    # Return False here to exclude e.g. already-anonymised accounts.
    return True


def _is_date(value):
    return isinstance(value, datetime.date) and not isinstance(value, datetime.datetime)


def _is_count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _id_key(value):
    # Orders ints before strs without comparing across types.
    return (isinstance(value, str), value)


def _validate(accounts, today):
    seen = set()
    for position, acc in enumerate(accounts):
        if not isinstance(acc, dict):
            raise TypeError(f"account at position {position} is not a dict")
        acc_id = acc.get("id")
        if isinstance(acc_id, bool) or not isinstance(acc_id, (int, str)):
            raise ValueError(f"account at position {position} has an invalid id")
        if acc_id in seen:
            raise ValueError(f"duplicate account id {acc_id!r}")
        seen.add(acc_id)
        if not isinstance(acc.get("email"), str):
            raise ValueError(f"account {acc_id!r} has an invalid email")
        if not _is_date(acc.get("last_seen_at")):
            raise ValueError(f"account {acc_id!r} has a missing or invalid last_seen_at")
        closed_at = acc.get("closed_at")
        if closed_at is not None:
            if not _is_date(closed_at):
                raise ValueError(f"account {acc_id!r} has an invalid closed_at")
            if closed_at > today:
                raise ValueError(f"account {acc_id!r} has a closed_at in the future")
            if acc.get("closed_by") not in ("member", "staff"):
                raise ValueError(f"account {acc_id!r} has an invalid closed_by")
        if not _is_count(acc.get("unpaid_invoices")):
            raise ValueError(f"account {acc_id!r} has an invalid unpaid_invoices")
        if not isinstance(acc.get("litigation_hold"), bool):
            raise ValueError(f"account {acc_id!r} has an invalid litigation_hold")


def _due(acc):
    deadlines = [acc["last_seen_at"] + datetime.timedelta(days=INACTIVITY_DAYS)]
    if acc.get("closed_at") is not None:
        deadlines.append(acc["closed_at"] + datetime.timedelta(days=CLOSED_GRACE_DAYS))
    return min(deadlines)


def _decide(acc, today):
    if acc["email"].strip().lower().endswith(STAFF_DOMAIN):
        return None
    if acc["litigation_hold"]:
        return None
    due = _due(acc)
    if due <= today:
        kind = "anonymise" if acc["unpaid_invoices"] > 0 else "delete"
        return kind, due
    if due <= today + datetime.timedelta(days=WARN_WINDOW_DAYS):
        member_closed = acc.get("closed_at") is not None and acc.get("closed_by") == "member"
        if member_closed:
            return None
        return "warn", due
    return None


def plan_purge(accounts, today):
    """Return purge actions for the given accounts. Pure: no side effects."""
    if not _is_date(today):
        raise TypeError("today must be a datetime.date (not datetime or another type)")
    accounts = list(accounts)
    _validate(accounts, today)

    decided = []
    for acc in accounts:
        if not _in_scope(acc):
            continue
        result = _decide(acc, today)
        if result is not None:
            kind, due = result
            decided.append((acc, kind, due))

    def cap_order(item):
        acc, _, due = item
        closed_rank = 0 if acc.get("closed_at") is not None else 1
        return (closed_rank, due, _id_key(acc["id"]))

    capped = sorted((d for d in decided if d[1] in CAPPED_ACTIONS), key=cap_order)
    kept_ids = {d[0]["id"] for d in capped[:DELETE_CAP]}
    chosen = [d for d in decided if d[1] not in CAPPED_ACTIONS or d[0]["id"] in kept_ids]
    chosen.sort(key=lambda d: _id_key(d[0]["id"]))

    return [
        {
            "account_id": acc["id"],
            "action": kind,
            "due": due.isoformat(),
            "approved_by": None if kind == "warn" else DPO_NAME,
        }
        for acc, kind, due in chosen
    ]


# ---------------------------------------------------------------- tests

TODAY = datetime.date(2026, 10, 13)
DAY = datetime.timedelta(days=1)


def _acc(**overrides):
    base = {
        "id": 1,
        "email": "member@example.com",
        "status": "active",
        "last_seen_at": TODAY - 10 * DAY,
        "last_login": None,
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
        "tenant": "legacy",
    }
    base.update(overrides)
    return base


class PlanPurgeTests(unittest.TestCase):

    def test_exactly_730_days_inactive_gives_delete_with_due_date(self):
        out = plan_purge([_acc(last_seen_at=TODAY - 730 * DAY)], TODAY)
        self.assertEqual(out, [{"account_id": 1, "action": "delete",
                                "due": TODAY.isoformat(),
                                "approved_by": DPO_NAME}])

    def test_member_closed_30_days_ago_is_deleted_despite_later_inactivity_deadline(self):
        acc = _acc(last_seen_at=TODAY - 1 * DAY, closed_at=TODAY - 30 * DAY, closed_by="member")
        out = plan_purge([acc], TODAY)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], TODAY.isoformat())

    def test_staff_closed_31_days_ago_with_recent_activity_is_deleted(self):
        acc = _acc(last_seen_at=TODAY - 1 * DAY, closed_at=TODAY - 31 * DAY, closed_by="staff")
        out = plan_purge([acc], TODAY)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], (TODAY - 1 * DAY).isoformat())

    def test_due_account_with_unpaid_invoice_gives_anonymise(self):
        acc = _acc(last_seen_at=TODAY - 730 * DAY, unpaid_invoices=1)
        out = plan_purge([acc], TODAY)
        self.assertEqual(out[0]["action"], "anonymise")
        self.assertEqual(out[0]["due"], TODAY.isoformat())

    def test_due_account_on_litigation_hold_gives_nothing(self):
        acc = _acc(last_seen_at=TODAY - 800 * DAY, litigation_hold=True)
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_staff_email_gives_nothing_including_uppercase(self):
        acc = _acc(email="  Someone@Tidewater-Klatring.NO ", last_seen_at=TODAY - 800 * DAY)
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_due_in_exactly_14_days_warns_and_15_days_gives_nothing(self):
        warn = _acc(id=1, last_seen_at=TODAY - (730 - 14) * DAY)
        quiet = _acc(id=2, last_seen_at=TODAY - (730 - 15) * DAY)
        out = plan_purge([warn, quiet], TODAY)
        self.assertEqual(out, [{"account_id": 1, "action": "warn",
                                "due": (TODAY + 14 * DAY).isoformat(),
                                "approved_by": None}])

    def test_member_closed_in_window_gives_no_warn(self):
        acc = _acc(last_seen_at=TODAY - 5 * DAY, closed_at=TODAY - 16 * DAY, closed_by="member")
        self.assertEqual(plan_purge([acc], TODAY), [])

    def test_cap_keeps_closed_first_then_earliest_then_id_and_output_sorted(self):
        inactive = [_acc(id=i, email=f"m{i}@example.com", last_seen_at=TODAY - 740 * DAY)
                    for i in range(1, 201)]
        closed = [_acc(id=i, email=f"m{i}@example.com", last_seen_at=TODAY - 5 * DAY,
                       closed_at=TODAY - 31 * DAY, closed_by="member")
                  for i in range(201, 206)]
        out = plan_purge(inactive + closed, TODAY)
        self.assertEqual(len(out), 200)
        kept = {a["account_id"] for a in out}
        self.assertEqual(kept, set(range(201, 206)) | set(range(1, 196)))
        ids = [a["account_id"] for a in out]
        self.assertEqual(ids, sorted(ids))

    def test_delete_and_anonymise_carry_dpo_and_warn_carries_none(self):
        accounts = [
            _acc(id=1, last_seen_at=TODAY - 730 * DAY),
            _acc(id=2, last_seen_at=TODAY - 730 * DAY, unpaid_invoices=2),
            _acc(id=3, last_seen_at=TODAY - (730 - 14) * DAY),
        ]
        out = {a["account_id"]: a for a in plan_purge(accounts, TODAY)}
        self.assertEqual(out[1]["approved_by"], "Þórdís Sveinbjörnsdóttir")
        self.assertEqual(out[2]["approved_by"], "Þórdís Sveinbjörnsdóttir")
        self.assertIsNone(out[3]["approved_by"])
        self.assertEqual(out[1]["approved_by"].encode("utf-8"),
                         "Þórdís Sveinbjörnsdóttir".encode("utf-8"))

    def test_no_email_in_output_or_error_messages(self):
        secret = "secret.person@example.com"
        good = _acc(id=1, email=secret, last_seen_at=TODAY - 730 * DAY)
        self.assertNotIn(secret, repr(plan_purge([good], TODAY)))
        bad = _acc(id=9, email=secret, last_seen_at=None)
        with self.assertRaises(ValueError) as cm:
            plan_purge([bad], TODAY)
        self.assertIn("9", str(cm.exception))
        self.assertNotIn(secret, str(cm.exception))

    def test_input_is_not_mutated(self):
        accounts = [_acc(id=1, last_seen_at=TODAY - 730 * DAY, unpaid_invoices=1),
                    _acc(id=2, last_seen_at=TODAY - 716 * DAY)]
        before = copy.deepcopy(accounts)
        plan_purge(accounts, TODAY)
        self.assertEqual(accounts, before)

    def test_missing_last_seen_raises_naming_account_without_partial_plan(self):
        good = _acc(id=1, last_seen_at=TODAY - 730 * DAY)
        bad = _acc(id=7)
        del bad["last_seen_at"]
        with self.assertRaises(ValueError) as cm:
            plan_purge([good, bad], TODAY)
        self.assertIn("account 7", str(cm.exception))

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(plan_purge([], TODAY), [])

    def test_datetime_today_is_rejected(self):
        with self.assertRaises(TypeError):
            plan_purge([], datetime.datetime(2026, 10, 13))

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError) as cm:
            plan_purge([_acc(id=3), _acc(id=3)], TODAY)
        self.assertIn("3", str(cm.exception))


if __name__ == "__main__":
    unittest.main()