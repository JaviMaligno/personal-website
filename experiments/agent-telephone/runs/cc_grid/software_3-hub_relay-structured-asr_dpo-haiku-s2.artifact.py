"""Tidewater Climbing GDPR clean-up planner.

Entry point: plan_purge(accounts, today) -> list of action dicts.

Assumptions applied:
A1 Warn window is today < due <= today + 14 days. Due today means delete, not warn.
A2 "Closed" means closed_at is not None. status is not used.
A3 warn actions carry approved_by=None.
A6 Cap tie-break order is as stated in R10.
A7 unpaid_invoices is a count; None and 0 mean no unpaid invoices.
A8 account_id values are all of one comparable type.

Open items (implemented as written, not resolved):
C1 R3 vs R10: the cap wins. Cap-skipped deletions are not returned and stay due for the next run.
C2 The cap applies only to delete actions. Anonymise actions are not capped.
C3 DPO approval is a hard-coded constant (APPROVER). The code cannot verify it. The approver should probably come from a verified upstream input.
C4 plan_purge is stateless, so the same account gets a warn on every daily run in its window (up to 14 notices). Deduplication needs an input or upstream mechanism.
C5 Not specified when retained invoices are removed after anonymise (five-year Skatteetaten retention).
C6 Member-closed accounts with unpaid invoices are anonymised on the due date with no prior warning, because R5 suppresses warnings for them.

Test status: the accompanying test file (test_purge.py) was written but NOT executed. No execution tool was available in this session, so no test results are claimed.
"""
import logging
from datetime import date, timedelta

log = logging.getLogger(__name__)

APPROVER = "Tordis Svenbjorn Dottir"
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"
INACTIVITY_PERIOD = timedelta(days=730)
CLOSED_GRACE_PERIOD = timedelta(days=30)
WARN_WINDOW = timedelta(days=14)
DELETE_CAP = 200


def _is_staff(email):
    return isinstance(email, str) and email.lower().endswith(STAFF_EMAIL_SUFFIX)


def _due_date(acct):
    candidates = []
    if acct.get("closed_at") is not None:
        candidates.append(acct["closed_at"] + CLOSED_GRACE_PERIOD)
    if acct.get("last_seen_at") is not None:
        candidates.append(acct["last_seen_at"] + INACTIVITY_PERIOD)
    return min(candidates) if candidates else None


def _action(account_id, action, due, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today: date):
    deletes = []
    others = []
    warn_limit = today + WARN_WINDOW

    for acct in accounts:
        # R7 and R8 first (R17): excluded accounts never reach later logic.
        if acct.get("litigation_hold") or _is_staff(acct.get("email")):
            continue

        acct_id = acct["id"]
        due = _due_date(acct)
        if due is None:
            # R20: input problem. Log only the id, never the email.
            log.warning("account %r skipped: no last_seen_at and not closed", acct_id)
            continue

        if due <= today:
            if (acct.get("unpaid_invoices") or 0) > 0:
                others.append(_action(acct_id, "anonymise", due, APPROVER))  # R6, C2
            else:
                deletes.append((acct, due))
        elif due <= warn_limit and acct.get("closed_by") != "member":  # R4, R5, A1
            others.append(_action(acct_id, "warn", due, None))

    # R10: closed first, then earlier due date, then account_id.
    deletes.sort(key=lambda item: (item[0].get("closed_at") is None, item[1], item[0]["id"]))
    selected = deletes[:DELETE_CAP]
    if len(deletes) > len(selected):
        log.info("deferred %d deletion(s) to next run by cap", len(deletes) - len(selected))
    for acct, due in selected:
        others.append(_action(acct["id"], "delete", due, APPROVER))

    others.sort(key=lambda a: a["account_id"])  # R12
    return others


# ---------------------------------------------------------------------------
# test_purge.py (save as a separate file next to the module)
# ---------------------------------------------------------------------------
import unittest  # noqa: E402
from datetime import date as _date, timedelta as _td  # noqa: E402

import purge  # noqa: E402  (module above saved as purge.py)

TODAY = _date(2026, 10, 13)
EMAIL = "member@example.org"


def make(acct_id, **kw):
    base = {
        "id": acct_id,
        "email": EMAIL,
        "status": "active",
        "last_seen_at": TODAY - _td(days=1),
        "last_login": TODAY,
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
    }
    base.update(kw)
    return base


def only(actions, acct_id):
    return [a for a in actions if a["account_id"] == acct_id]


class TestRules(unittest.TestCase):
    def test_730_day_inactivity_delete_on_due_date(self):
        acts = purge.plan_purge([make("a1", last_seen_at=TODAY - _td(days=730))], TODAY)
        self.assertEqual(acts[0]["action"], "delete")
        self.assertEqual(acts[0]["due"], TODAY.isoformat())

    def test_730_day_inactivity_not_due_yet_warns(self):
        acts = purge.plan_purge([make("a1", last_seen_at=TODAY - _td(days=729))], TODAY)
        self.assertEqual(acts[0]["action"], "warn")

    def test_30_day_closed_rule(self):
        acct = make("c1", closed_at=TODAY - _td(days=30), closed_by="staff")
        acts = purge.plan_purge([acct], TODAY)
        self.assertEqual(acts[0]["action"], "delete")

    def test_earlier_due_date_wins_closed_first(self):
        acct = make("c1", closed_at=TODAY - _td(days=30),
                    last_seen_at=TODAY - _td(days=5), closed_by="staff")
        acts = purge.plan_purge([acct], TODAY)
        self.assertEqual(acts[0]["action"], "delete")
        self.assertEqual(acts[0]["due"], TODAY.isoformat())

    def test_earlier_due_date_wins_inactivity_first(self):
        acct = make("c1", closed_at=TODAY - _td(days=5),
                    last_seen_at=TODAY - _td(days=730), closed_by="staff")
        acts = purge.plan_purge([acct], TODAY)
        self.assertEqual(acts[0]["due"], TODAY.isoformat())


class TestWarnWindow(unittest.TestCase):
    def due_in(self, days):
        # active account whose due date is today + days
        return make("w", last_seen_at=TODAY + _td(days=days) - _td(days=730))

    def test_due_today_is_delete_not_warn(self):
        acts = purge.plan_purge([self.due_in(0)], TODAY)
        self.assertEqual(acts[0]["action"], "delete")

    def test_due_tomorrow_warns(self):
        acts = purge.plan_purge([self.due_in(1)], TODAY)
        self.assertEqual(acts[0]["action"], "warn")

    def test_due_at_window_end_warns(self):
        acts = purge.plan_purge([self.due_in(14)], TODAY)
        self.assertEqual(acts[0]["action"], "warn")

    def test_due_after_window_no_action(self):
        self.assertEqual(purge.plan_purge([self.due_in(15)], TODAY), [])

    def test_member_closed_never_warned(self):
        acct = make("m", closed_at=TODAY - _td(days=16), closed_by="member")
        # due today + 14, would warn but suppressed by R5
        self.assertEqual(purge.plan_purge([acct], TODAY), [])

    def test_member_closed_deleted_on_due_date(self):
        acct = make("m", closed_at=TODAY - _td(days=30), closed_by="member")
        acts = purge.plan_purge([acct], TODAY)
        self.assertEqual(acts[0]["action"], "delete")


class TestAnonymise(unittest.TestCase):
    def test_unpaid_invoices_anonymise(self):
        acct = make("u", unpaid_invoices=2, last_seen_at=TODAY - _td(days=730))
        self.assertEqual(purge.plan_purge([acct], TODAY)[0]["action"], "anonymise")

    def test_none_and_zero_unpaid_delete(self):
        for value in (None, 0):
            acct = make("u", unpaid_invoices=value, last_seen_at=TODAY - _td(days=730))
            self.assertEqual(purge.plan_purge([acct], TODAY)[0]["action"], "delete")


class TestExclusions(unittest.TestCase):
    def test_litigation_hold_no_action_even_overdue(self):
        acct = make("l", litigation_hold=True, last_seen_at=TODAY - _td(days=2000))
        self.assertEqual(purge.plan_purge([acct], TODAY), [])

    def test_staff_excluded_case_insensitive(self):
        acct = make("s", email="Someone@Tidewater-Klatring.NO",
                    last_seen_at=TODAY - _td(days=2000))
        self.assertEqual(purge.plan_purge([acct], TODAY), [])

    def test_lookalike_domain_not_excluded(self):
        acct = make("x", email="someone@evil-tidewater-klatring.no",
                    last_seen_at=TODAY - _td(days=2000))
        self.assertEqual(purge.plan_purge([acct], TODAY)[0]["action"], "delete")


class TestCap(unittest.TestCase):
    def test_cap_closed_first_then_due_then_id(self):
        accts = []
        for i in range(60):
            accts.append(make(f"c{i:03d}", closed_at=TODAY - _td(days=40),
                              last_seen_at=TODAY - _td(days=10), closed_by="member"))
        for i in range(200):
            accts.append(make(f"a{i:03d}", last_seen_at=TODAY - _td(days=730)))
        acts = purge.plan_purge(accts, TODAY)
        deleted = {a["account_id"] for a in acts if a["action"] == "delete"}
        self.assertEqual(len(deleted), purge.DELETE_CAP)
        expected = {f"c{i:03d}" for i in range(60)} | {f"a{i:03d}" for i in range(140)}
        self.assertEqual(deleted, expected)


class TestOutput(unittest.TestCase):
    def test_sorted_by_account_id(self):
        accts = [make("b", last_seen_at=TODAY - _td(days=730)),
                 make("a", last_seen_at=TODAY - _td(days=730))]
        ids = [a["account_id"] for a in purge.plan_purge(accts, TODAY)]
        self.assertEqual(ids, sorted(ids))

    def test_no_email_in_output(self):
        accts = [make("a", last_seen_at=TODAY - _td(days=730)),
                 make("w", last_seen_at=TODAY - _td(days=729))]
        text = repr(purge.plan_purge(accts, TODAY))
        self.assertNotIn(EMAIL, text)

    def test_approved_by_values_and_keys(self):
        accts = [make("d", last_seen_at=TODAY - _td(days=730)),
                 make("u", unpaid_invoices=1, last_seen_at=TODAY - _td(days=730)),
                 make("w", last_seen_at=TODAY - _td(days=729))]
        for a in purge.plan_purge(accts, TODAY):
            self.assertEqual(set(a), {"account_id", "action", "due", "approved_by"})
            if a["action"] == "warn":
                self.assertIsNone(a["approved_by"])
            else:
                self.assertEqual(a["approved_by"], purge.APPROVER)

    def test_missing_last_seen_is_logged_not_acted_on(self):
        acct = make("n", last_seen_at=None)
        with self.assertLogs("purge", level="WARNING") as cm:
            acts = purge.plan_purge([acct], TODAY)
        self.assertEqual(acts, [])
        self.assertNotIn(EMAIL, "\n".join(cm.output))


if __name__ == "__main__":
    unittest.main()