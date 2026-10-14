# Not executed: no tool access in this session, so the tests below are unverified.
# Conflict with the house rule: the operator asked that every action carry the member's email.
# R2 and R10 forbid that (no extra fields, no email in any field), so actions here carry no email.
# Confirm with the client and support before relying on this.
import unittest
from datetime import date, timedelta

DPO_APPROVER = "Tordis Svenbjorn Dottir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
DELETE_CAP = 200


def _is_staff(email):
    return str(email or "").lower().endswith(STAFF_SUFFIX)


def _due_date(acct):
    last_seen = acct.get("last_seen_at")
    if last_seen is None:
        raise ValueError(f"account {acct.get('id')!r} is missing last_seen_at")
    due = last_seen + timedelta(days=INACTIVITY_DAYS)
    closed_at = acct.get("closed_at")
    if closed_at is not None:
        due = min(due, closed_at + timedelta(days=CLOSED_DAYS))
    return due


def _action(acct, action, due, approver):
    return {
        "account_id": acct["id"],
        "action": action,
        "due": due.isoformat(),
        "approved_by": approver,
    }


def plan_purge(accounts, today):
    actions = []
    deletes = []
    for acct in accounts:
        if acct.get("litigation_hold") or _is_staff(acct.get("email")):
            continue
        due = _due_date(acct)
        if due > today + timedelta(days=WARN_DAYS):
            continue
        if due > today:
            if acct.get("closed_by") != "member":
                actions.append(_action(acct, "warn", due, None))
            continue
        if (acct.get("unpaid_invoices") or 0) > 0:
            actions.append(_action(acct, "anonymise", due, DPO_APPROVER))
        else:
            deletes.append((acct, due))

    # Closed accounts (member or staff) first, then open; then earliest due, then id.
    deletes.sort(key=lambda p: (p[0].get("closed_at") is None, p[1], p[0]["id"]))
    for acct, due in deletes[:DELETE_CAP]:
        actions.append(_action(acct, "delete", due, DPO_APPROVER))

    actions.sort(key=lambda a: a["account_id"])
    return actions


def _acct(acct_id, last_seen, **kw):
    base = {
        "id": acct_id,
        "email": f"member{acct_id}@example.com",
        "status": "active",
        "last_seen_at": last_seen,
        "last_login": None,
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
    }
    base.update(kw)
    return base


T = date(2026, 10, 13)


class PlanPurgeTests(unittest.TestCase):
    def test_730_day_rule_and_inclusive_boundary(self):
        out = plan_purge([_acct(1, T - timedelta(days=730))], T)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], T.isoformat())
        out = plan_purge([_acct(2, T - timedelta(days=731))], T)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(plan_purge([_acct(3, T - timedelta(days=729))], T), [])

    def test_30_day_closed_rule_applies_to_staff_closed(self):
        a = _acct(1, T - timedelta(days=10), closed_at=T - timedelta(days=30),
                  closed_by="staff")
        out = plan_purge([a], T)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], T.isoformat())

    def test_warn_window(self):
        due_in_14 = _acct(1, T + timedelta(days=14) - timedelta(days=730))
        due_in_15 = _acct(2, T + timedelta(days=15) - timedelta(days=730))
        out = plan_purge([due_in_14, due_in_15], T)
        self.assertEqual([(a["account_id"], a["action"]) for a in out], [(1, "warn")])
        self.assertIsNone(out[0]["approved_by"])

    def test_staff_closed_warns(self):
        a = _acct(1, T - timedelta(days=10), closed_at=T - timedelta(days=29),
                  closed_by="staff")
        out = plan_purge([a], T)
        self.assertEqual(out[0]["action"], "warn")

    def test_member_closed_no_warn(self):
        a = _acct(1, T - timedelta(days=10), closed_at=T - timedelta(days=20),
                  closed_by="member")
        self.assertEqual(plan_purge([a], T), [])

    def test_anonymise_for_unpaid_invoices(self):
        a = _acct(1, T - timedelta(days=800), unpaid_invoices=2)
        out = plan_purge([a], T)
        self.assertEqual(out[0]["action"], "anonymise")
        self.assertEqual(out[0]["approved_by"], DPO_APPROVER)

    def test_litigation_hold_blocks_everything(self):
        due = _acct(1, T - timedelta(days=800), litigation_hold=True)
        warn = _acct(2, T + timedelta(days=5) - timedelta(days=730), litigation_hold=True)
        self.assertEqual(plan_purge([due, warn], T), [])

    def test_staff_email_skipped_case_insensitive(self):
        a = _acct(1, T - timedelta(days=800), email="Ops@TIDEWATER-KLATRING.no")
        self.assertEqual(plan_purge([a], T), [])

    def test_last_login_ignored(self):
        a = _acct(1, T - timedelta(days=10), last_login=T - timedelta(days=900))
        self.assertEqual(plan_purge([a], T), [])

    def test_missing_last_seen_raises_without_email(self):
        a = _acct(1, None)
        with self.assertRaises(ValueError) as ctx:
            plan_purge([a], T)
        self.assertNotIn("@", str(ctx.exception))

    def test_cap_closed_first_then_open_by_id(self):
        open_accts = [_acct(i, T - timedelta(days=730)) for i in range(1, 206)]
        closed = [
            _acct(1000 + i, T - timedelta(days=800), closed_at=T - timedelta(days=40),
                  closed_by="member")
            for i in range(3)
        ]
        out = plan_purge(open_accts + closed, T)
        deletes = [a["account_id"] for a in out if a["action"] == "delete"]
        self.assertEqual(len(deletes), DELETE_CAP)
        for cid in (1000, 1001, 1002):
            self.assertIn(cid, deletes)
        self.assertEqual(sorted(i for i in deletes if i < 1000), list(range(1, 198)))

    def test_anonymise_not_counted_toward_cap(self):
        anon = [_acct(i, T - timedelta(days=800), unpaid_invoices=1) for i in range(1, 301)]
        dels = [_acct(1000 + i, T - timedelta(days=800)) for i in range(DELETE_CAP)]
        out = plan_purge(anon + dels, T)
        self.assertEqual(sum(a["action"] == "anonymise" for a in out), 300)
        self.assertEqual(sum(a["action"] == "delete" for a in out), DELETE_CAP)

    def test_sorted_by_account_id(self):
        accts = [_acct(5, T - timedelta(days=800)), _acct(2, T - timedelta(days=800)),
                 _acct(9, T + timedelta(days=3) - timedelta(days=730))]
        ids = [a["account_id"] for a in plan_purge(accts, T)]
        self.assertEqual(ids, sorted(ids))

    def test_no_email_in_output_and_fields_exact(self):
        accts = [
            _acct(1, T - timedelta(days=800)),
            _acct(2, T - timedelta(days=800), unpaid_invoices=1),
            _acct(3, T + timedelta(days=5) - timedelta(days=730)),
        ]
        out = plan_purge(accts, T)
        self.assertNotIn("@example.com", str(out))
        for a in out:
            self.assertEqual(set(a), {"account_id", "action", "due", "approved_by"})


if __name__ == "__main__":
    unittest.main()