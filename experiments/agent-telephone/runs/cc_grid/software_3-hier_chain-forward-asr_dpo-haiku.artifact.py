# Status: this reply contains the module and the test file as text. No files were written and no tests were run, because this turn has no file or shell tools.
# Deviations and notes:
# - apply_cap(candidates) returns the kept action dicts. deferred_ids(candidates) returns the deferred ids in cap order.
# - The mixed-type check looks only at ids that are str or non-bool int. Records with other id types are skipped in validation.
# - Duplicate detection counts the ids of all records that carry a valid id type, including records that fail other validation. A valid record that shares an id with an invalid one is skipped too, which is the fail-safe choice.
# - plan_purge raises TypeError if today is not a plain datetime.date. This is an addition to the design.
# - Assumptions A to L are implemented as written. Assumptions D, G and H still need a DPO or Mateusz decision.

"""GDPR clean-up planner for Tidewater Climbing. Standard library only."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date, datetime, timedelta

INACTIVE_DELETE_DAYS = 730
CLOSED_DELETE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETION_CAP = 200
DPO_APPROVER = "Tordis Svenbjorn Dottir"
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"
WARN_UNPAID_ACCOUNTS = True  # assumption G
CLOSED_MEANS_CLOSED_AT_NOT_NONE = True  # assumption B

log = logging.getLogger(__name__)

_CLOSED_BY_VALUES = ("member", "staff", None)


def _is_date(value) -> bool:
    return isinstance(value, date) and not isinstance(value, datetime)


def _is_valid_id(value) -> bool:
    return isinstance(value, (str, int)) and not isinstance(value, bool)


def is_staff(email: str) -> bool:
    return email.strip().lower().endswith(STAFF_EMAIL_SUFFIX)


def is_closed(rec: dict) -> bool:
    if CLOSED_MEANS_CLOSED_AT_NOT_NONE:
        return rec["closed_at"] is not None
    return rec["closed_by"] == "member"


def due_date(rec: dict) -> date:
    due = rec["last_seen_at"] + timedelta(days=INACTIVE_DELETE_DAYS)
    if rec["closed_at"] is not None:
        due = min(due, rec["closed_at"] + timedelta(days=CLOSED_DELETE_DAYS))
    return due


def _action(account_id, action: str, due: date) -> dict:
    approved = None if action == "warn" else DPO_APPROVER
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved,
    }


def decide(rec: dict, today: date) -> dict | None:
    if rec["litigation_hold"] or is_staff(rec["email"]):
        return None
    due = due_date(rec)
    unpaid = rec["unpaid_invoices"]
    if due <= today:
        action = "anonymise" if unpaid else "delete"
    elif due <= today + timedelta(days=WARN_WINDOW_DAYS):
        if rec["closed_by"] == "member":
            return None
        if unpaid and not WARN_UNPAID_ACCOUNTS:
            return None
        action = "warn"
    else:
        return None
    return _action(rec["id"], action, due)


def _cap_order(candidate):
    rec, _ = candidate
    return (0 if is_closed(rec) else 1, due_date(rec), rec["id"])


def deferred_ids(candidates: list) -> list:
    ordered = sorted(candidates, key=_cap_order)
    return [rec["id"] for rec, _ in ordered[DELETION_CAP:]]


def apply_cap(candidates: list) -> list:
    ordered = sorted(candidates, key=_cap_order)
    kept = [action for _, action in ordered[:DELETION_CAP]]
    deferred = deferred_ids(candidates)
    if deferred:
        log.warning(
            "deletion cap %d reached; deferred %d account(s): %s",
            DELETION_CAP, len(deferred), deferred,
        )
    return kept


def _problem(rec) -> str | None:
    if not isinstance(rec, dict):
        return "record is not a dict"
    if not _is_valid_id(rec.get("id")):
        return "id must be a non-bool str or int"
    email = rec.get("email")
    if not isinstance(email, str) or not email.strip():
        return "email missing or empty"
    if not _is_date(rec.get("last_seen_at")):
        return "last_seen_at must be a date"
    closed_at = rec.get("closed_at")
    if closed_at is not None and not _is_date(closed_at):
        return "closed_at must be a date or None"
    closed_by = rec.get("closed_by")
    if closed_by not in _CLOSED_BY_VALUES:
        return "unknown closed_by"
    if (closed_by is None) != (closed_at is None):
        return "closed_by and closed_at are inconsistent"
    if not isinstance(rec.get("litigation_hold"), bool):
        return "litigation_hold must be a bool"
    if not isinstance(rec.get("unpaid_invoices"), bool):
        return "unpaid_invoices must be a bool"
    return None


def plan_purge(accounts: list, today: date) -> list[dict]:
    if not _is_date(today):
        raise TypeError("today must be a datetime.date")
    records = list(accounts)

    ids = [r.get("id") for r in records if isinstance(r, dict) and _is_valid_id(r.get("id"))]
    if len({type(i) for i in ids}) > 1:
        raise ValueError("account ids must all be str or all be int")
    id_counts = Counter(ids)

    valid = []
    for idx, rec in enumerate(records):
        reason = _problem(rec)
        if reason is None and id_counts[rec["id"]] > 1:
            reason = "duplicate id"
        if reason is not None:
            account_id = rec.get("id") if isinstance(rec, dict) else None
            log.warning("skipping record at index %d (account_id=%r): %s", idx, account_id, reason)
            continue
        valid.append(rec)

    actions = []
    delete_candidates = []
    for rec in valid:
        act = decide(rec, today)
        if act is None:
            continue
        if act["action"] == "delete":
            delete_candidates.append((rec, act))
        else:
            actions.append(act)

    actions.extend(apply_cap(delete_candidates))

    assert len({a["account_id"] for a in actions}) == len(actions), "more than one action per account"
    actions.sort(key=lambda a: a["account_id"])
    return actions

# ===== test_purge_plan.py (second file, save separately) =====

import json
import os
import sys
import unittest
from datetime import date, datetime, timedelta
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import purge_plan as pp  # noqa: E402

TODAY = date(2026, 10, 13)
DPO = "Tordis Svenbjorn Dottir"


def make(**kw):
    base = {
        "id": 1,
        "email": "user@example.com",
        "status": "active",
        "last_seen_at": TODAY - timedelta(days=100),
        "last_login": date(2000, 1, 1),
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": False,
        "litigation_hold": False,
    }
    base.update(kw)
    return base


def seen(days_ago):
    return TODAY - timedelta(days=days_ago)


def plan(*recs):
    return pp.plan_purge(list(recs), TODAY)


class HardExclusionTests(unittest.TestCase):
    def test_staff_exact_suffix(self):
        out = plan(make(email="a@tidewater-klatring.no", last_seen_at=seen(800), unpaid_invoices=True))
        self.assertEqual(out, [])

    def test_staff_uppercase(self):
        self.assertEqual(plan(make(email="A@TIDEWATER-KLATRING.NO", last_seen_at=seen(800))), [])

    def test_staff_trailing_spaces(self):
        self.assertEqual(plan(make(email="a@tidewater-klatring.no   ", last_seen_at=seen(800))), [])

    def test_litigation_hold_blocks_everything(self):
        cases = (
            {"last_seen_at": seen(800)},
            {"last_seen_at": seen(800), "unpaid_invoices": True},
            {"last_seen_at": seen(729)},
        )
        for kw in cases:
            with self.subTest(kw=kw):
                self.assertEqual(plan(make(litigation_hold=True, **kw)), [])


class InactivityTests(unittest.TestCase):
    def test_due_today_deletes(self):
        out = plan(make(last_seen_at=seen(730)))
        self.assertEqual(out, [{"account_id": 1, "action": "delete", "due": "2026-10-13", "approved_by": DPO}])

    def test_due_yesterday_deletes(self):
        out = plan(make(last_seen_at=seen(731)))
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], "2026-10-12")

    def test_due_tomorrow_warns(self):
        out = plan(make(last_seen_at=seen(729)))
        self.assertEqual(out, [{"account_id": 1, "action": "warn", "due": "2026-10-14", "approved_by": None}])

    def test_due_in_15_days_nothing(self):
        self.assertEqual(plan(make(last_seen_at=seen(715))), [])

    def test_last_login_ignored(self):
        self.assertEqual(plan(make(last_seen_at=seen(10), last_login=date(2000, 1, 1))), [])


class ClosedRuleTests(unittest.TestCase):
    def test_closed_plus_30_earlier_wins(self):
        out = plan(make(closed_by="member", closed_at=seen(40), last_seen_at=seen(10)))
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], seen(10).isoformat())

    def test_closed_plus_30_later_loses(self):
        out = plan(make(closed_by="staff", closed_at=TODAY, last_seen_at=seen(729)))
        self.assertEqual(out[0]["action"], "warn")
        self.assertEqual(out[0]["due"], (TODAY + timedelta(days=1)).isoformat())


class WarnWindowTests(unittest.TestCase):
    def test_today_plus_14_warns(self):
        self.assertEqual(plan(make(last_seen_at=seen(716)))[0]["action"], "warn")

    def test_today_plus_15_none(self):
        self.assertEqual(plan(make(last_seen_at=seen(715))), [])

    def test_due_today_is_delete_not_warn(self):
        self.assertEqual(plan(make(last_seen_at=seen(730)))[0]["action"], "delete")


class ClosedWarnTests(unittest.TestCase):
    def test_closed_member_not_warned(self):
        self.assertEqual(plan(make(closed_by="member", closed_at=seen(5), last_seen_at=seen(729))), [])

    def test_closed_staff_warned(self):
        out = plan(make(closed_by="staff", closed_at=seen(5), last_seen_at=seen(729)))
        self.assertEqual(out[0]["action"], "warn")

    def test_closed_member_due_deletes(self):
        out = plan(make(closed_by="member", closed_at=seen(31), last_seen_at=seen(100)))
        self.assertEqual(out[0]["action"], "delete")


class AnonymiseTests(unittest.TestCase):
    def test_unpaid_due_anonymises(self):
        out = plan(make(unpaid_invoices=True, last_seen_at=seen(800)))
        self.assertEqual(out[0]["action"], "anonymise")
        self.assertEqual(out[0]["approved_by"], DPO)

    def test_unpaid_in_warn_window_warns(self):
        out = plan(make(unpaid_invoices=True, last_seen_at=seen(729)))
        self.assertEqual(out[0]["action"], "warn")
        self.assertIsNone(out[0]["approved_by"])


class CapTests(unittest.TestCase):
    def build(self):
        recs = [make(id=i, closed_by="member", closed_at=seen(31), last_seen_at=seen(100))
                for i in range(1, 101)]
        recs += [make(id=i, last_seen_at=seen(900 - (i - 101))) for i in range(101, 206)]
        return recs

    def test_200_deletes_closed_first(self):
        out = plan(*self.build())
        deletes = [a["account_id"] for a in out if a["action"] == "delete"]
        self.assertEqual(len(deletes), 200)
        self.assertTrue(set(range(1, 101)) <= set(deletes))
        self.assertEqual(set(deletes) - set(range(1, 101)), set(range(101, 201)))

    def test_deferred_ids_reported_and_absent(self):
        recs = self.build()
        cands = [(r, pp.decide(r, TODAY)) for r in recs]
        deferred = pp.deferred_ids(cands)
        self.assertEqual(deferred, [201, 202, 203, 204, 205])
        ids = {a["account_id"] for a in plan(*recs)}
        self.assertFalse(ids & set(deferred))

    def test_ordering_within_cap_with_small_cap(self):
        recs = [
            make(id=9, closed_by="member", closed_at=seen(31), last_seen_at=seen(100)),
            make(id=3, last_seen_at=seen(900)),
            make(id=1, last_seen_at=seen(800)),
            make(id=2, last_seen_at=seen(800)),
        ]
        with mock.patch.object(pp, "DELETION_CAP", 2):
            with self.assertLogs(pp.log, level="WARNING"):
                out = plan(*recs)
        self.assertEqual([a["account_id"] for a in out], [3, 9])

    def test_anonymise_and_warn_not_counted(self):
        recs = [make(id=i, last_seen_at=seen(800)) for i in range(1, 201)]
        recs += [make(id=i, last_seen_at=seen(800), unpaid_invoices=True) for i in range(301, 304)]
        recs += [make(id=i, last_seen_at=seen(729)) for i in (401, 402)]
        out = plan(*recs)
        counts = {}
        for a in out:
            counts[a["action"]] = counts.get(a["action"], 0) + 1
        self.assertEqual(counts, {"delete": 200, "anonymise": 3, "warn": 2})


class OutputTests(unittest.TestCase):
    def test_sorted_by_int_id(self):
        out = plan(make(id=10, last_seen_at=seen(800)),
                   make(id=9, last_seen_at=seen(800)),
                   make(id=2, last_seen_at=seen(800)))
        self.assertEqual([a["account_id"] for a in out], [2, 9, 10])

    def test_approvals(self):
        out = plan(make(id=1, last_seen_at=seen(800)),
                   make(id=2, last_seen_at=seen(800), unpaid_invoices=True),
                   make(id=3, last_seen_at=seen(729)))
        by_id = {a["account_id"]: a for a in out}
        self.assertEqual(by_id[1]["approved_by"], DPO)
        self.assertEqual(by_id[2]["approved_by"], DPO)
        self.assertIsNone(by_id[3]["approved_by"])

    def test_due_is_iso_string(self):
        out = plan(make(last_seen_at=seen(730)))
        self.assertIsInstance(out[0]["due"], str)
        self.assertEqual(out[0]["due"], "2026-10-13")
        date.fromisoformat(out[0]["due"])

    def test_no_email_in_output_or_logs(self):
        good = make(id=1, email="secret.person@example.com", last_seen_at=seen(800))
        bad = make(id=2, email="other.secret@example.com", last_seen_at=None)
        with self.assertLogs(pp.log, level="WARNING") as cm:
            out = plan(good, bad)
        dump = repr(out) + json.dumps(out)
        self.assertNotIn("secret", dump)
        self.assertNotIn("secret", "\n".join(cm.output))
        for a in out:
            self.assertEqual(set(a), {"account_id", "action", "due", "approved_by"})

    def test_at_most_one_action_per_account(self):
        out = plan(make(id=1, last_seen_at=seen(730)), make(id=2, last_seen_at=seen(729)))
        ids = [a["account_id"] for a in out]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(out[0]["action"], "delete")

    def test_empty_input(self):
        self.assertEqual(pp.plan_purge([], TODAY), [])


class DefensiveTests(unittest.TestCase):
    def test_missing_last_seen_skipped_and_logged(self):
        with self.assertLogs(pp.log, level="WARNING"):
            out = plan(make(last_seen_at=None))
        self.assertEqual(out, [])

    def test_duplicate_ids_skip_all(self):
        with self.assertLogs(pp.log, level="WARNING"):
            out = plan(make(id=5, last_seen_at=seen(800)),
                       make(id=5, last_seen_at=seen(800)),
                       make(id=6, last_seen_at=seen(800)))
        self.assertEqual([a["account_id"] for a in out], [6])

    def test_unknown_closed_by_skipped(self):
        with self.assertLogs(pp.log, level="WARNING"):
            out = plan(make(closed_by="robot", closed_at=seen(40), last_seen_at=seen(800)))
        self.assertEqual(out, [])

    def test_closed_by_closed_at_inconsistency_skipped(self):
        with self.assertLogs(pp.log, level="WARNING"):
            out = plan(make(id=1, closed_by="member", closed_at=None, last_seen_at=seen(800)),
                       make(id=2, closed_by=None, closed_at=seen(40), last_seen_at=seen(800)))
        self.assertEqual(out, [])

    def test_datetime_rejected(self):
        with self.assertLogs(pp.log, level="WARNING"):
            out = plan(make(id=1, last_seen_at=datetime(2020, 1, 1)),
                       make(id=2, closed_by="staff", closed_at=datetime(2026, 1, 1), last_seen_at=seen(800)))
        self.assertEqual(out, [])

    def test_mixed_id_types_raise(self):
        with self.assertRaises(ValueError):
            plan(make(id=1), make(id="2"))

    def test_non_bool_unpaid_not_coerced(self):
        with self.assertLogs(pp.log, level="WARNING"):
            self.assertEqual(plan(make(unpaid_invoices=1, last_seen_at=seen(800))), [])

    def test_bool_id_rejected(self):
        with self.assertLogs(pp.log, level="WARNING"):
            self.assertEqual(plan(make(id=True, last_seen_at=seen(800))), [])


if __name__ == "__main__":
    unittest.main()