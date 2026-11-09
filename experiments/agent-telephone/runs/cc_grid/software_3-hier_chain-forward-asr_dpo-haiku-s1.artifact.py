"""GDPR clean-up planner for Tidewater Climbing. Standard library only.

Tests are at the bottom of this module. They were written but not executed in this session.
Run them with: python3 -I <absolute path to this file>

OPEN QUESTIONS AND CHOICES (each marked "OPEN: confirm with client" in code):
1. Staff email match is case-insensitive. Chosen as the safer direction for a hard exclusion.
2. The closed_at + 30 rule applies to staff-closed accounts too. Chosen as the design states.
3. The 14-day warn window is inclusive (due == today + 14 warns, today + 15 does not).
4. unpaid_invoices may be an int (unpaid if > 0) or a list (unpaid if non-empty). Any other type, including bool, raises ValueError naming the id. Negative ints count as paid.
5. Anonymise is decided at the same due point as delete. The later state of anonymised accounts is undefined and no extra logic was added for it.
6. An account with unpaid invoices inside the warn window gets only a warn action. This is a conflict with the one-action-per-account assumption and is flagged for confirmation.
7. last_seen_at that is None or not a date raises ValueError. A datetime is rejected as not a date. Raising, not skipping, is chosen.
8. closed_at in the future raises ValueError naming the id.
9. closed_by None while closed_at is set raises ValueError. Chosen over treating it as not member-closed.
10. closed_by values other than "member" are treated as not member-closed.
11. Litigation-hold and staff skips are evaluated before field validation, so a skipped account with bad fields does not raise.
12. The 200 cap counts only delete actions. Anonymise and warn are never capped.
13. Over-cap delete candidates are dropped silently with no warn. Confirm whether they should be warned instead.
14. Cap ordering: closed accounts first, sorted by (closed_at, id). Open accounts follow, sorted by (due, id).
15. account_id is assumed to be int or str with a single consistent type, so the final sort is natural. Duplicate ids are not handled.
"""

from datetime import date, datetime, timedelta

APPROVER = "Tordis Svenbjorn Dottir"
STAFF_DOMAIN = "@tidewater-klatring.no"  # OPEN: confirm with client (matched case-insensitively)
INACTIVITY = timedelta(days=730)
CLOSED_GRACE = timedelta(days=30)
WARN_WINDOW = timedelta(days=14)  # OPEN: confirm with client (inclusive boundary)
DELETE_CAP = 200


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _is_staff(email):
    return isinstance(email, str) and email.lower().endswith(STAFF_DOMAIN)


def _has_unpaid(account):
    # OPEN: confirm with client (accepted types and count semantics)
    inv = account.get("unpaid_invoices")
    if isinstance(inv, bool) or not isinstance(inv, (int, list)):
        raise ValueError(f"account {account.get('id')!r}: unpaid_invoices must be an int or a list")
    if isinstance(inv, int):
        return inv > 0
    return len(inv) > 0


def _evaluate(account, today):
    """Return (action, due, closed_at) for an account, or None for no action."""
    aid = account.get("id")
    if account.get("litigation_hold"):
        return None
    if _is_staff(account.get("email")):
        return None

    last_seen = account.get("last_seen_at")
    if not _is_date(last_seen):
        raise ValueError(f"account {aid!r}: last_seen_at must be a date")

    closed_at = account.get("closed_at")
    closed_by = account.get("closed_by")
    if closed_at is not None:
        if not _is_date(closed_at):
            raise ValueError(f"account {aid!r}: closed_at must be a date or None")
        if closed_at > today:
            raise ValueError(f"account {aid!r}: closed_at is in the future")
        if closed_by is None:
            # OPEN: confirm with client (raise chosen over treating as not member-closed)
            raise ValueError(f"account {aid!r}: closed_by is None while closed_at is set")

    due = last_seen + INACTIVITY
    if closed_at is not None:
        due = min(due, closed_at + CLOSED_GRACE)

    unpaid = _has_unpaid(account)

    if due <= today:
        # OPEN: anonymise decided at the same due point as delete; later state undefined.
        return ("anonymise" if unpaid else "delete"), due, closed_at
    if due <= today + WARN_WINDOW:
        # OPEN: a member-closed account is never warned. Unpaid invoices in the window
        # still produce a warn only (one action per account assumed).
        if closed_by == "member":
            return None
        return "warn", due, closed_at
    return None


def plan_purge(accounts, today):
    if not _is_date(today):
        raise ValueError("today must be a date")

    rows = []  # (account_id, action, due, closed_at)
    for account in accounts:
        result = _evaluate(account, today)
        if result is not None:
            action, due, closed_at = result
            rows.append((account["id"], action, due, closed_at))

    deletes = [r for r in rows if r[1] == "delete"]
    if len(deletes) > DELETE_CAP:
        # OPEN: confirm with client (ordering within closed/open groups and tie-breaks)
        def cap_key(row):
            aid, _, due, closed_at = row
            if closed_at is not None:
                return (0, closed_at, aid)
            return (1, due, aid)

        kept_ids = {r[0] for r in sorted(deletes, key=cap_key)[:DELETE_CAP]}
        # OPEN: over-cap accounts are dropped silently. Confirm whether they should warn.
        rows = [r for r in rows if r[1] != "delete" or r[0] in kept_ids]

    out = []
    for aid, action, due, _ in rows:
        out.append({
            "account_id": aid,
            "action": action,
            "due": due.isoformat(),
            "approved_by": None if action == "warn" else APPROVER,
        })
    # OPEN: confirm id type (assumed int or str, consistent) for natural sort.
    out.sort(key=lambda d: d["account_id"])
    return out


if __name__ == "__main__":
    import unittest

    T = date(2026, 10, 13)

    def acct(aid, last_seen, closed_at=None, closed_by=None, unpaid=0, hold=False, email=None):
        return {
            "id": aid,
            "email": email or f"member{aid}@example.com",
            "status": "active",
            "last_seen_at": last_seen,
            "last_login": None,
            "closed_at": closed_at,
            "closed_by": closed_by,
            "unpaid_invoices": unpaid,
            "litigation_hold": hold,
        }

    class PurgeTests(unittest.TestCase):
        def test_cap_closed_first_then_earliest_open(self):
            accts = []
            for i in range(60):
                # closed by member 40 days ago, so due = T-10 (delete)
                accts.append(acct(i, T - timedelta(days=10), closed_at=T - timedelta(days=40), closed_by="member"))
            for i in range(150):
                # open, due = T-10-i (delete)
                accts.append(acct(1000 + i, T - timedelta(days=740 + i)))
            out = plan_purge(accts, T)
            deletes = {d["account_id"] for d in out if d["action"] == "delete"}
            expected = set(range(60)) | {1000 + i for i in range(10, 150)}
            self.assertEqual(len(deletes), DELETE_CAP)
            self.assertEqual(deletes, expected)

        def test_litigation_hold_no_action(self):
            self.assertEqual(plan_purge([acct(1, T - timedelta(days=800), hold=True)], T), [])

        def test_staff_excluded_case_insensitive(self):
            a = acct(2, T - timedelta(days=800), email="Ops@Tidewater-Klatring.no")
            self.assertEqual(plan_purge([a], T), [])

        def test_warn_window_inclusive_at_14_days(self):
            inside = acct(3, T + timedelta(days=14) - INACTIVITY)
            outside = acct(4, T + timedelta(days=15) - INACTIVITY)
            out = plan_purge([inside, outside], T)
            self.assertEqual([d["account_id"] for d in out], [3])
            self.assertEqual(out[0]["action"], "warn")
            self.assertIsNone(out[0]["approved_by"])
            self.assertEqual(out[0]["due"], (T + timedelta(days=14)).isoformat())

        def test_member_close_suppresses_warn(self):
            member = acct(5, T - timedelta(days=5), closed_at=T - timedelta(days=20), closed_by="member")
            staff = acct(6, T - timedelta(days=5), closed_at=T - timedelta(days=20), closed_by="staff")
            out = plan_purge([member, staff], T)
            self.assertEqual([(d["account_id"], d["action"]) for d in out], [(6, "warn")])

        def test_due_equal_today_is_delete(self):
            out = plan_purge([acct(7, T - INACTIVITY)], T)
            self.assertEqual(out[0]["action"], "delete")
            self.assertEqual(out[0]["due"], T.isoformat())
            self.assertEqual(out[0]["approved_by"], APPROVER)

        def test_unpaid_invoices_switch_to_anonymise(self):
            out = plan_purge([acct(8, T - INACTIVITY, unpaid=1)], T)
            self.assertEqual(out[0]["action"], "anonymise")
            self.assertEqual(out[0]["approved_by"], APPROVER)

        def test_no_email_in_output(self):
            out = plan_purge([acct(9, T - INACTIVITY), acct(10, T + timedelta(days=3) - INACTIVITY)], T)
            for d in out:
                self.assertEqual(set(d.keys()), {"account_id", "action", "due", "approved_by"})
            self.assertNotIn("@", repr(out))

        def test_invalid_last_seen_raises(self):
            bad = acct(11, None)
            with self.assertRaises(ValueError) as ctx:
                plan_purge([bad], T)
            self.assertIn("11", str(ctx.exception))

    unittest.main()
}