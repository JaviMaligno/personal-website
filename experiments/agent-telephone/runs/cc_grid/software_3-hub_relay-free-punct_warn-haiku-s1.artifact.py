"""GDPR purge planner for Tidewater Climbing member accounts.

plan_purge(accounts, today) returns a list of action dicts sorted by account_id.
plan_purge_with_deferred(accounts, today) also returns the number of purge
candidates deferred by the cap, so the caller can log it.

The planner is stateless. Warnings are not deduplicated, so an account in the
warning window is warned on every run until it is acted on. The caller must
dedupe if required.

Decisions use last_seen_at only. last_login is ignored. The status field is
ignored for decisions until the client supplies its values.

Open items for client confirmation, implemented as described:
- anonymise actions count toward the 200-candidate cap.
- Tie-break inside each group (closed first, then inactive) is due ascending,
  then account_id ascending.
- Warnings repeat on every run while an account is in the window.

Conflict to confirm before deploy: the house rule requires every action dict to
carry the account's email, but the spec lists exactly account_id, action, due
and approved_by with no member email. This module follows the house rule and
adds an "email" key to each action dict. Remove that key if the spec wins.
"""

import datetime as dt
import logging

__all__ = ["plan_purge", "plan_purge_with_deferred"]

log = logging.getLogger(__name__)

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
CAP = 200
INACTIVITY_DAYS = 730
CLOSURE_DAYS = 30
WARN_DAYS = 14


def _check_date(name, value):
    if isinstance(value, dt.datetime) or not isinstance(value, dt.date):
        raise TypeError(f"{name} must be a datetime.date, not {type(value).__name__}")


def _validate(accounts, today):
    _check_date("today", today)
    seen = set()
    for acc in accounts:
        if acc.get("id") in seen:
            raise ValueError(f"duplicate account id: {acc.get('id')!r}")
        seen.add(acc.get("id"))
        if acc.get("unpaid_invoices") is None:
            raise ValueError(f"unpaid_invoices is None for account {acc.get('id')!r}")
        if acc.get("litigation_hold") is None:
            raise ValueError(f"litigation_hold is None for account {acc.get('id')!r}")
        for key in ("last_seen_at", "closed_at"):
            if acc.get(key) is not None:
                _check_date(key, acc[key])


def _due(acc):
    options = []
    if acc.get("last_seen_at") is not None:
        options.append(acc["last_seen_at"] + dt.timedelta(days=INACTIVITY_DAYS))
    if acc.get("closed_at") is not None:
        options.append(acc["closed_at"] + dt.timedelta(days=CLOSURE_DAYS))
    return min(options) if options else None


def _action(acc, action, due, approved_by):
    return {
        "account_id": acc["id"],
        "email": acc["email"],
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge_with_deferred(accounts, today):
    """Return (actions, deferred_count). deferred_count contains no personal data."""
    accounts = list(accounts)
    _validate(accounts, today)

    candidates = []
    warnings = []
    skipped_no_date = 0
    warn_limit = today + dt.timedelta(days=WARN_DAYS)

    for acc in accounts:
        email = acc.get("email")
        if isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX):
            continue
        if acc["litigation_hold"]:
            continue
        due = _due(acc)
        if due is None:
            skipped_no_date += 1
            continue
        if due <= today:
            closed = acc.get("closed_at") is not None
            group = 0 if closed else 1
            candidates.append((group, due, acc["id"], acc))
        elif due <= warn_limit:
            if acc.get("closed_by") != "member":
                warnings.append(_action(acc, "warn", due, None))

    if skipped_no_date:
        log.warning("skipped %d account(s) with no last_seen_at and not closed", skipped_no_date)

    candidates.sort(key=lambda c: (c[0], c[1], c[2]))
    deferred = max(0, len(candidates) - CAP)
    if deferred:
        log.info("deferred %d purge candidate(s) by cap of %d", deferred, CAP)

    purge_actions = []
    for _, due, _, acc in candidates[:CAP]:
        if acc["unpaid_invoices"] > 0:
            purge_actions.append(_action(acc, "anonymise", due, APPROVER))
        else:
            purge_actions.append(_action(acc, "delete", due, APPROVER))

    actions = sorted(purge_actions + warnings, key=lambda a: a["account_id"])
    return actions, deferred


def plan_purge(accounts, today):
    """Return the list of actions for this run, sorted by account_id.

    Warnings are not deduplicated. See the module docstring.
    """
    return plan_purge_with_deferred(accounts, today)[0]


# ---------------------------------------------------------------- tests

if __name__ == "__main__":
    import unittest

    TODAY = dt.date(2026, 10, 13)

    def make(aid, last_seen=None, closed_at=None, closed_by="staff",
             unpaid=0, hold=False, email="member@example.com"):
        return {
            "id": aid,
            "email": email,
            "status": "active",
            "last_seen_at": last_seen,
            "last_login": None,
            "closed_at": closed_at,
            "closed_by": closed_by,
            "unpaid_invoices": unpaid,
            "litigation_hold": hold,
        }

    def days(n):
        return dt.timedelta(days=n)

    class PlanPurgeTests(unittest.TestCase):

        def test_empty(self):
            self.assertEqual(plan_purge([], TODAY), [])

        def test_due_today_is_delete(self):
            out = plan_purge([make("a", last_seen=TODAY - days(730))], TODAY)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0]["action"], "delete")
            self.assertEqual(out[0]["due"], TODAY.isoformat())
            self.assertEqual(out[0]["approved_by"], APPROVER)

        def test_due_in_past_is_candidate(self):
            out = plan_purge([make("a", last_seen=TODAY - days(900))], TODAY)
            self.assertEqual(out[0]["action"], "delete")

        def test_unpaid_is_anonymise(self):
            out = plan_purge([make("a", last_seen=TODAY - days(730), unpaid=1)], TODAY)
            self.assertEqual(out[0]["action"], "anonymise")
            self.assertEqual(out[0]["approved_by"], APPROVER)

        def test_warn_window_boundaries(self):
            for offset, expected in [(1, 1), (14, 1), (15, 0)]:
                due = TODAY + days(offset)
                accs = [make("a", last_seen=due - days(730))]
                out = plan_purge(accs, TODAY)
                self.assertEqual(len(out), expected, f"offset {offset}")
                if expected:
                    self.assertEqual(out[0]["action"], "warn")
                    self.assertIsNone(out[0]["approved_by"])

        def test_warn_at_716_days(self):
            out = plan_purge([make("a", last_seen=TODAY - days(716))], TODAY)
            self.assertEqual(out[0]["action"], "warn")
            self.assertEqual(out[0]["due"], (TODAY + days(14)).isoformat())

        def test_member_closed_not_warned(self):
            accs = [make("a", last_seen=TODAY, closed_at=TODAY + days(5) - days(30),
                         closed_by="member")]
            self.assertEqual(plan_purge(accs, TODAY), [])

        def test_staff_closed_warn_then_anonymise(self):
            accs = [make("a", last_seen=TODAY, closed_at=TODAY + days(5) - days(30),
                         closed_by="staff", unpaid=2)]
            now = plan_purge(accs, TODAY)
            self.assertEqual([a["action"] for a in now], ["warn"])
            on_due = plan_purge(accs, TODAY + days(5))
            self.assertEqual([a["action"] for a in on_due], ["anonymise"])
            self.assertEqual(on_due[0]["approved_by"], APPROVER)

        def test_staff_email_any_case_excluded(self):
            accs = [make("a", last_seen=TODAY - days(900),
                         email="  Someone@TIDEWATER-klatring.no ")]
            self.assertEqual(plan_purge(accs, TODAY), [])

        def test_hold_excluded_even_when_due(self):
            accs = [make("a", last_seen=TODAY - days(900), hold=True)]
            self.assertEqual(plan_purge(accs, TODAY), [])

        def test_hold_excluded_from_warn(self):
            accs = [make("a", last_seen=TODAY - days(716), hold=True)]
            self.assertEqual(plan_purge(accs, TODAY), [])

        def test_missing_last_seen_and_not_closed_no_action(self):
            self.assertEqual(plan_purge([make("a", last_seen=None)], TODAY), [])

        def test_closed_without_last_seen_uses_closure_date(self):
            accs = [make("a", last_seen=None, closed_at=TODAY - days(30))]
            out = plan_purge(accs, TODAY)
            self.assertEqual(out[0]["action"], "delete")

        def test_cap_250_closed_first(self):
            accs = []
            for i in range(50):
                accs.append(make(f"c{i:03d}", last_seen=TODAY,
                                 closed_at=TODAY - days(30)))
            for i in range(200):
                accs.append(make(f"i{i:03d}", last_seen=TODAY - days(730)))
            actions, deferred = plan_purge_with_deferred(accs, TODAY)
            self.assertEqual(len(actions), 200)
            self.assertEqual(deferred, 50)
            closed_ids = [a["account_id"] for a in actions if a["account_id"].startswith("c")]
            self.assertEqual(len(closed_ids), 50)

        def test_output_sorted_by_account_id(self):
            accs = [make("z", last_seen=TODAY - days(900)),
                    make("a", last_seen=TODAY - days(900)),
                    make("m", last_seen=TODAY - days(716))]
            ids = [a["account_id"] for a in plan_purge(accs, TODAY)]
            self.assertEqual(ids, ["a", "m", "z"])

        def test_output_keys(self):
            out = plan_purge([make("a", last_seen=TODAY - days(900),
                                   email="x@example.com")], TODAY)
            self.assertEqual(set(out[0]),
                             {"account_id", "email", "action", "due", "approved_by"})
            self.assertEqual(out[0]["email"], "x@example.com")

        def test_datetime_today_raises(self):
            with self.assertRaises(TypeError):
                plan_purge([], dt.datetime(2026, 10, 13))

        def test_none_unpaid_raises(self):
            with self.assertRaises(ValueError):
                plan_purge([make("a", last_seen=TODAY, unpaid=None)], TODAY)

        def test_none_hold_raises(self):
            acc = make("a", last_seen=TODAY)
            acc["litigation_hold"] = None
            with self.assertRaises(ValueError):
                plan_purge([acc], TODAY)

        def test_duplicate_id_raises(self):
            with self.assertRaises(ValueError):
                plan_purge([make("a", last_seen=TODAY), make("a", last_seen=TODAY)], TODAY)

    unittest.main()