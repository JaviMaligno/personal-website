"""GDPR purge planner for Tidewater Climbing member accounts.

Entry point: plan_purge(accounts, today) -> list of action dicts sorted by account_id.
Standard library only. Targets Python 3.12.

Assumptions where the brief was silent or left questions open (safest choice made):
1. House rule vs brief: the house rule asks for `email` on every action dict, but the
   brief and the hand-off forbid member emails in any action (the audit log is shared
   with the climbing federation). The brief wins. No email appears in any output, and
   support can look accounts up by account_id.
2. Invoice retention (Skatteetaten, five years): not modelled. Any account with unpaid
   invoices is anonymised, which keeps invoices. Nothing here deletes invoices.
3. Re-anonymising: an account with status "anonymised" gets no further anonymise action.
4. last_seen_at is None: no inactivity deadline. Only the closed-30-day rule can apply.
   Missing data never causes a deletion on its own.
5. Duplicate ids: every account sharing a duplicated id is skipped for this run.
   Only the id is reported, never an email.
6. Id type for sorting: ints sort numerically and come before other ids, which sort by str.
7. Staff email matching: case-insensitive, whitespace trimmed.
8. "Closed" means closed_at is not None. closed_by only affects the warn suppression.
9. Warn suppression: a closed account is not warned unless closed_by is exactly "staff".
   A closed account with a missing or unknown closed_by is therefore not warned either.
10. Cap: deletions are capped at 200 per run, ordered closed first, then due date, then id.
    Deletions beyond the cap are skipped, not deferred. Anonymise and warn do not count.
11. Warns are emitted for accounts with unpaid invoices too. Warn does not depend on
    the anonymise/delete choice.
12. Warn window: due strictly after today and on or before today + 14 days.
    Warn `due` is the account's due date. Warn `approved_by` is None.
"""
from __future__ import annotations

import datetime as dt
import json
import unittest

APPROVER = "Tordis Svenbjorn Dottir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_CAP = 200
INACTIVE_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14


def _is_staff(email) -> bool:
    return str(email or "").strip().lower().endswith(STAFF_DOMAIN)


def _sort_key(account_id):
    if isinstance(account_id, int):
        return (0, account_id, "")
    return (1, 0, str(account_id))


def _due(acct):
    dates = []
    if acct.get("last_seen_at") is not None:
        dates.append(acct["last_seen_at"] + dt.timedelta(days=INACTIVE_DAYS))
    if acct.get("closed_at") is not None:
        dates.append(acct["closed_at"] + dt.timedelta(days=CLOSED_DAYS))
    return min(dates) if dates else None


def _action(account_id, action, due, approved_by=APPROVER):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    counts = {}
    for a in accounts:
        counts[a["id"]] = counts.get(a["id"], 0) + 1

    actions = []
    candidates = []
    warn_horizon = today + dt.timedelta(days=WARN_DAYS)

    for a in accounts:
        aid = a["id"]
        if counts[aid] > 1:
            continue
        if a.get("litigation_hold"):
            continue
        if _is_staff(a.get("email")):
            continue
        due = _due(a)
        if due is None:
            continue

        closed = a.get("closed_at") is not None
        if due <= today:
            if (a.get("unpaid_invoices") or 0) > 0:
                if a.get("status") == "anonymised":
                    continue
                actions.append(_action(aid, "anonymise", due))
            else:
                candidates.append((0 if closed else 1, due, _sort_key(aid), aid))
        elif due <= warn_horizon:
            if closed and a.get("closed_by") != "staff":
                continue
            actions.append(_action(aid, "warn", due, approved_by=None))

    candidates.sort(key=lambda c: c[:3])
    for _, due, _, aid in candidates[:DELETE_CAP]:
        actions.append(_action(aid, "delete", due))

    actions.sort(key=lambda x: _sort_key(x["account_id"]))
    return actions


def _acct(i, last_seen, **kw):
    base = {
        "id": i,
        "email": f"member{i}@example.com",
        "status": "active",
        "last_seen_at": last_seen,
        "last_login": None,
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
        "tenant": "legacy",
    }
    base.update(kw)
    return base


TODAY = dt.date(2026, 10, 13)


class PlanPurgeTests(unittest.TestCase):
    def ls(self, days_ago_due_offset):
        # last_seen such that last_seen + 730 days == TODAY + offset
        return TODAY + dt.timedelta(days=days_ago_due_offset) - dt.timedelta(days=730)

    def test_delete_exactly_730_days_on_today(self):
        out = plan_purge([_acct(1, self.ls(0))], TODAY)
        self.assertEqual(out, [_action(1, "delete", TODAY)])

    def test_closed_30_days_ago_deleted_even_if_recently_seen(self):
        a = _acct(2, TODAY, closed_at=TODAY - dt.timedelta(days=30), closed_by="member")
        out = plan_purge([a], TODAY)
        self.assertEqual([x["action"] for x in out], ["delete"])
        self.assertEqual(out[0]["due"], (TODAY - dt.timedelta(days=30) + dt.timedelta(days=30)).isoformat())

    def test_earlier_date_is_due(self):
        a = _acct(3, self.ls(5), closed_at=TODAY - dt.timedelta(days=30))
        self.assertEqual(plan_purge([a], TODAY)[0]["due"], TODAY.isoformat())

    def test_boundary_warn_at_14_days_and_none_at_15(self):
        at14 = _acct(4, self.ls(14))
        at15 = _acct(5, self.ls(15))
        out = plan_purge([at14, at15], TODAY)
        self.assertEqual(out, [_action(4, "warn", TODAY + dt.timedelta(days=14), approved_by=None)])

    def test_unpaid_invoices_anonymise(self):
        out = plan_purge([_acct(6, self.ls(0), unpaid_invoices=2)], TODAY)
        self.assertEqual(out[0]["action"], "anonymise")
        self.assertEqual(out[0]["approved_by"], APPROVER)

    def test_hold_produces_nothing(self):
        out = plan_purge([_acct(7, self.ls(0), litigation_hold=True),
                          _acct(8, self.ls(5), litigation_hold=True)], TODAY)
        self.assertEqual(out, [])

    def test_staff_produces_nothing_case_insensitive(self):
        a = _acct(9, self.ls(0), email="Someone@TIDEWATER-KLATRING.no")
        self.assertEqual(plan_purge([a], TODAY), [])

    def test_member_closed_not_warned_staff_closed_warned(self):
        closed_at = TODAY - dt.timedelta(days=20)
        member = _acct(10, TODAY, closed_at=closed_at, closed_by="member")
        staff = _acct(11, TODAY, closed_at=closed_at, closed_by="staff")
        out = plan_purge([member, staff], TODAY)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["account_id"], 11)
        self.assertEqual(out[0]["action"], "warn")
        self.assertIsNone(out[0]["approved_by"])

    def test_cap_of_200_closed_first(self):
        accounts = []
        for i in range(1, 51):
            accounts.append(_acct(i, TODAY - dt.timedelta(days=100),
                                  closed_at=TODAY - dt.timedelta(days=30), closed_by="member"))
        for i in range(51, 251):
            accounts.append(_acct(i, self.ls(0)))
        out = plan_purge(accounts, TODAY)
        deletes = [x["account_id"] for x in out if x["action"] == "delete"]
        self.assertEqual(len(deletes), DELETE_CAP)
        self.assertEqual(set(range(1, 51)).issubset(deletes), True)
        self.assertEqual(sorted(set(deletes) - set(range(1, 51))), list(range(51, 201)))

    def test_sorted_by_id_and_iso_dates(self):
        accounts = [_acct(3, self.ls(0)), _acct(1, self.ls(0)), _acct(2, self.ls(0))]
        out = plan_purge(accounts, TODAY)
        self.assertEqual([x["account_id"] for x in out], [1, 2, 3])
        self.assertTrue(all(len(x["due"]) == 10 for x in out))

    def test_no_email_in_output_and_tenant_ignored(self):
        accounts = [_acct(1, self.ls(0)), _acct(2, self.ls(0), unpaid_invoices=1)]
        out = plan_purge(accounts, TODAY)
        self.assertNotIn("@", json.dumps(out))

    def test_deterministic_regardless_of_input_order(self):
        accounts = [_acct(i, self.ls(0)) for i in range(1, 6)]
        self.assertEqual(plan_purge(accounts, TODAY), plan_purge(list(reversed(accounts)), TODAY))


if __name__ == "__main__":
    unittest.main()