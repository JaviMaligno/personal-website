# tidewater_purge.py
"""Tidewater Climbing GDPR clean-up planner. Pure function, standard library only."""

from datetime import date, datetime, timedelta

APPROVER = "Þórdís Sveinbjörnsdóttir"
EXCLUDED_SUFFIX = "@tidewater-klatring.no"
INACTIVITY = timedelta(days=730)
CLOSURE = timedelta(days=30)
WARN_WINDOW = timedelta(days=40)
DELETE_CAP = 200
REQUIRED_KEYS = ("id", "email", "last_seen_at", "closed_at", "unpaid_invoices", "litigation_hold")
NON_NULL_KEYS = ("id", "email", "last_seen_at", "unpaid_invoices", "litigation_hold")


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _validate(accounts):
    if not isinstance(accounts, list):
        raise ValueError("accounts must be a list")
    seen_ids = set()
    id_types = set()
    for idx, rec in enumerate(accounts):
        if not isinstance(rec, dict):
            raise ValueError(f"record {idx} is not a mapping")
        for key in REQUIRED_KEYS:
            if key not in rec:
                raise ValueError(f"record {idx} is missing '{key}'")
        for key in NON_NULL_KEYS:
            if rec[key] is None:
                raise ValueError(f"record {idx} has null '{key}'")
        rid = rec["id"]
        if not isinstance(rid, (str, int)) or isinstance(rid, bool):
            raise ValueError(f"record {idx} has invalid 'id' type")
        if rid in seen_ids:
            raise ValueError(f"record {idx} has a duplicate 'id'")
        seen_ids.add(rid)
        id_types.add(type(rid))
        if len(id_types) > 1:
            raise ValueError("ids must all be strings or all be integers")
        if not isinstance(rec["email"], str):
            raise ValueError(f"record {idx} has invalid 'email' type")
        if not _is_date(rec["last_seen_at"]):
            raise ValueError(f"record {idx} has invalid 'last_seen_at'")
        if rec["closed_at"] is not None and not _is_date(rec["closed_at"]):
            raise ValueError(f"record {idx} has invalid 'closed_at'")
        unpaid = rec["unpaid_invoices"]
        if not isinstance(unpaid, int) or isinstance(unpaid, bool) or unpaid < 0:
            raise ValueError(f"record {idx} has invalid 'unpaid_invoices'")
        if not isinstance(rec["litigation_hold"], bool):
            raise ValueError(f"record {idx} has invalid 'litigation_hold'")
        if rec["closed_at"] is not None and rec.get("closed_by") not in ("member", "staff"):
            raise ValueError(f"record {idx} has invalid 'closed_by'")


def _due(rec):
    try:
        inactivity = rec["last_seen_at"] + INACTIVITY
        if rec["closed_at"] is None:
            return inactivity
        return min(inactivity, rec["closed_at"] + CLOSURE)
    except OverflowError:
        raise ValueError("deadline out of range") from None


def plan_purge(accounts, today):
    if not _is_date(today):
        raise ValueError("today must be a date")
    _validate(accounts)

    actions = []
    deletes = []
    for rec in accounts:
        email = rec["email"].strip().lower()
        if rec["litigation_hold"] or email.endswith(EXCLUDED_SUFFIX):
            continue
        due = _due(rec)
        if today >= due:
            if rec["unpaid_invoices"] == 0:
                deletes.append((rec, due))
            else:
                actions.append({
                    "account_id": rec["id"],
                    "action": "anonymise",
                    "due": due.isoformat(),
                    "approved_by": APPROVER,
                })
        elif due <= today + WARN_WINDOW and rec.get("closed_by") != "member":
            actions.append({
                "account_id": rec["id"],
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    deletes.sort(key=lambda item: (item[0]["closed_at"] is None, item[1], item[0]["id"]))
    for rec, due in deletes[:DELETE_CAP]:
        actions.append({
            "account_id": rec["id"],
            "action": "delete",
            "due": due.isoformat(),
            "approved_by": APPROVER,
        })

    actions.sort(key=lambda a: a["account_id"])
    return actions


# ---------------------------------------------------------------------------
# test_tidewater_purge.py
# Not executed in this session: no tool access was available to run these.
# ---------------------------------------------------------------------------
import random
import unittest
from datetime import timedelta

from tidewater_purge import APPROVER, plan_purge

TODAY = date(2026, 10, 13)
EMAIL = "member@example.com"


def acct(**overrides):
    rec = {
        "id": "a1",
        "email": EMAIL,
        "status": "active",
        "last_seen_at": date(2025, 6, 1),
        "last_login": date(2020, 1, 1),
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
    }
    rec.update(overrides)
    return rec


class PurgeTests(unittest.TestCase):
    def test_1_open_inactive_delete(self):
        out = plan_purge([acct(last_seen_at=date(2024, 10, 13))], TODAY)
        self.assertEqual(out, [{"account_id": "a1", "action": "delete",
                                "due": "2026-10-13", "approved_by": APPROVER}])

    def test_2_open_inactive_with_invoices_anonymise(self):
        out = plan_purge([acct(last_seen_at=date(2024, 10, 13), unpaid_invoices=2)], TODAY)
        self.assertEqual(out, [{"account_id": "a1", "action": "anonymise",
                                "due": "2026-10-13", "approved_by": APPROVER}])

    def test_3_open_warn(self):
        out = plan_purge([acct(last_seen_at=date(2024, 11, 1))], TODAY)
        self.assertEqual(out, [{"account_id": "a1", "action": "warn",
                                "due": "2026-11-01", "approved_by": None}])

    def test_4_closed_by_staff_warn_and_member_none(self):
        staff = acct(last_seen_at=date(2025, 1, 1), closed_at=date(2026, 9, 20), closed_by="staff")
        out = plan_purge([staff], TODAY)
        self.assertEqual(out, [{"account_id": "a1", "action": "warn",
                                "due": "2026-10-20", "approved_by": None}])
        member = acct(last_seen_at=date(2025, 1, 1), closed_at=date(2026, 9, 20), closed_by="member")
        self.assertEqual(plan_purge([member], TODAY), [])

    def test_5_closed_by_member_delete_not_warn(self):
        rec = acct(last_seen_at=date(2024, 10, 13), closed_at=date(2026, 9, 10), closed_by="member")
        out = plan_purge([rec], TODAY)
        self.assertEqual(out, [{"account_id": "a1", "action": "delete",
                                "due": "2026-10-10", "approved_by": APPROVER}])

    def test_6_exclusions(self):
        hold = acct(last_seen_at=date(2024, 10, 13), litigation_hold=True)
        staff_domain = acct(id="a2", email="  X@Tidewater-Klatring.NO ",
                            last_seen_at=date(2024, 10, 13))
        lookalike = acct(id="a3", email="x@evil-tidewater-klatring.no",
                         last_seen_at=date(2024, 10, 13))
        out = plan_purge([hold, staff_domain], TODAY)
        self.assertEqual(out, [])
        out = plan_purge([lookalike], TODAY)
        self.assertEqual([a["action"] for a in out], ["delete"])

    def test_7_delete_cap_and_ranking(self):
        recs = []
        for i in range(120):
            recs.append(acct(id=f"c{i:03d}", email=f"c{i}@example.com",
                             last_seen_at=date(2026, 1, 1), closed_at=date(2026, 8, 1),
                             closed_by="staff"))
        for i in range(130):
            recs.append(acct(id=f"o{i:03d}", email=f"o{i}@example.com",
                             last_seen_at=date(2024, 10, 13) - timedelta(days=i)))
        recs.append(acct(id="x1", email="x1@example.com",
                         last_seen_at=date(2024, 10, 13), unpaid_invoices=1))
        random.Random(0).shuffle(recs)

        out = plan_purge(recs, TODAY)
        deletes = [a for a in out if a["action"] == "delete"]
        anonymise = [a for a in out if a["action"] == "anonymise"]
        self.assertEqual(len(deletes), 200)
        ids = {a["account_id"] for a in deletes}
        self.assertTrue({f"c{i:03d}" for i in range(120)} <= ids)
        self.assertEqual({i for i in ids if i.startswith("o")},
                         {f"o{i:03d}" for i in range(50, 130)})
        self.assertEqual([a["account_id"] for a in anonymise], ["x1"])

    def test_8_output_sorted_by_account_id(self):
        recs = [acct(id=i, email=f"{i}@example.com", last_seen_at=date(2024, 10, 13))
                for i in ["m", "b", "z", "a"]]
        out = plan_purge(recs, TODAY)
        self.assertEqual([a["account_id"] for a in out], ["a", "b", "m", "z"])

    def test_9_no_email_in_output(self):
        out = plan_purge([acct(last_seen_at=date(2024, 10, 13)),
                          acct(id="a2", email="w@example.com", last_seen_at=date(2024, 11, 1))],
                         TODAY)
        self.assertTrue(out)
        for action in out:
            self.assertNotIn("email", action)
            self.assertNotIn(EMAIL, repr(action))
            self.assertNotIn("w@example.com", repr(action))

    def test_10_tenant_key_ignored(self):
        rec = acct(last_seen_at=date(2024, 10, 13), tenant="acme")
        out = plan_purge([rec], TODAY)
        self.assertEqual([a["action"] for a in out], ["delete"])

    def test_11_malformed_fails_closed(self):
        good = acct(id="good", email="ok@example.com", last_seen_at=date(2024, 10, 13))
        bad_cases = [
            acct(id="bad1", last_seen_at="2024-10-13"),
            acct(id="bad2", closed_at=date(2026, 9, 1), closed_by=None),
            acct(id="bad3", litigation_hold="no"),
            acct(id="bad4", last_seen_at=date(2024, 10, 13), closed_at=None),
            acct(id="bad5", last_seen_at=date(2024, 10, 13), closed_at=date(2026, 9, 1),
                 closed_by="staff") | {"id": "good"},
        ]
        for bad in bad_cases:
            with self.subTest(bad=bad.get("id")):
                with self.assertRaises(ValueError) as cm:
                    plan_purge([good, bad], TODAY)
                self.assertNotIn(EMAIL, str(cm.exception))

        missing_email = acct(id="bad6", last_seen_at=date(2024, 10, 13))
        del missing_email["email"]
        with self.assertRaises(ValueError):
            plan_purge([good, missing_email], TODAY)


if __name__ == "__main__":
    unittest.main()