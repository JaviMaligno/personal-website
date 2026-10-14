"""Tidewater Climbing GDPR clean-up planner.

plan_purge(accounts, today) returns today's actions only. It performs no I/O.

Open points (documented behaviour, not handled here):
(a) Anonymised accounts keep their old last_seen_at, so a daily run re-emits
    "anonymise" for them until the input data changes. The input has no
    "already anonymised" marker.
(b) The warn notice is emitted on every daily run during the 14-day window.
(c) No rule exists for when anonymised records are finally deleted.

Approval: the function takes no approval input. DPO_APPROVER is attached to
delete and anonymise actions as a constant. This function does NOT verify
that an actual approval was given.
"""

import unittest
from datetime import date, timedelta

DPO_APPROVER = "Þórdís Sveinbjörnsdóttir"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200
STAFF_DOMAIN = "@tidewater-klatring.no"
OUTPUT_KEYS = ("account_id", "action", "due", "approved_by")


def _due_date(account):
    due = account["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
    closed_at = account.get("closed_at")
    if closed_at is not None:
        due = min(due, closed_at + timedelta(days=CLOSED_GRACE_DAYS))
    return due


def plan_purge(accounts, today, skipped=None):
    """Return today's actions sorted by account_id.

    If `skipped` is a list, ids of accounts skipped under R17 are appended to it.
    Output items contain only the keys in OUTPUT_KEYS (no member emails).
    """
    planned = []
    for acc in accounts:
        email = str(acc.get("email") or "").lower()
        if email.endswith(STAFF_DOMAIN):  # R8
            continue
        if acc.get("litigation_hold"):  # R7
            continue

        acc_id = acc.get("id")
        closed_at = acc.get("closed_at")
        closed_by = acc.get("closed_by")
        if acc.get("last_seen_at") is None or (
            closed_at is not None and closed_by not in ("member", "staff")
        ):  # R17
            if skipped is not None:
                skipped.append(acc_id)
            continue

        due = _due_date(acc)  # R2, R3
        if due <= today:  # R4, R6
            action = "anonymise" if acc.get("unpaid_invoices") else "delete"
        elif due <= today + timedelta(days=WARN_WINDOW_DAYS) and closed_by != "member":  # R5
            action = "warn"
        else:
            continue

        planned.append({
            "account_id": acc_id,
            "action": action,
            "due": due,
            "closed": closed_at is not None,
        })

    deletes = sorted(
        (p for p in planned if p["action"] == "delete"),
        key=lambda p: (0 if p["closed"] else 1, p["due"], p["account_id"]),
    )[:DELETE_CAP]  # R10
    others = [p for p in planned if p["action"] != "delete"]

    result = []
    for p in sorted(deletes + others, key=lambda p: p["account_id"]):  # R12
        result.append({
            "account_id": p["account_id"],
            "action": p["action"],
            "due": p["due"].isoformat(),  # R14
            "approved_by": None if p["action"] == "warn" else DPO_APPROVER,  # R11
        })
    return result


class PlanPurgeTests(unittest.TestCase):
    TODAY = date(2026, 10, 13)

    def acc(self, **kw):
        base = {
            "id": 1,
            "email": "member@example.com",
            "status": "active",
            "last_seen_at": self.TODAY - timedelta(days=10),
            "last_login": None,
            "closed_at": None,
            "closed_by": None,
            "unpaid_invoices": False,
            "litigation_hold": False,
        }
        base.update(kw)
        return base

    def test_r2_inactivity_due_date(self):
        last_seen = self.TODAY - timedelta(days=INACTIVITY_DAYS)
        out = plan_purge([self.acc(last_seen_at=last_seen)], self.TODAY)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], (last_seen + timedelta(days=730)).isoformat())

    def test_r3_closed_date_earlier_wins_regardless_of_closed_by(self):
        closed_at = self.TODAY - timedelta(days=30)
        for by in ("member", "staff"):
            out = plan_purge(
                [self.acc(closed_at=closed_at, closed_by=by)], self.TODAY
            )
            self.assertEqual(out[0]["action"], "delete")
            self.assertEqual(out[0]["due"], self.TODAY.isoformat())

    def test_r4_due_on_today_is_deleted_and_future_is_not(self):
        due_today = self.acc(last_seen_at=self.TODAY - timedelta(days=730))
        future = self.acc(id=2, last_seen_at=self.TODAY - timedelta(days=700))
        out = plan_purge([due_today, future], self.TODAY)
        self.assertEqual([o["account_id"] for o in out], [1])

    def test_r5_warn_window_and_day_14_boundary(self):
        def last_seen_due_in(n):
            return self.TODAY + timedelta(days=n) - timedelta(days=730)

        d1 = self.acc(id=1, last_seen_at=last_seen_due_in(1))
        d14 = self.acc(id=2, last_seen_at=last_seen_due_in(14))
        d15 = self.acc(id=3, last_seen_at=last_seen_due_in(15))
        out = plan_purge([d1, d14, d15], self.TODAY)
        self.assertEqual([(o["account_id"], o["action"]) for o in out],
                         [(1, "warn"), (2, "warn")])
        self.assertIsNone(out[0]["approved_by"])

    def test_r5_member_closed_is_not_warned_but_staff_closed_is(self):
        closed_at = self.TODAY - timedelta(days=20)  # closed due in 10 days
        member = self.acc(id=1, closed_at=closed_at, closed_by="member")
        staff = self.acc(id=2, closed_at=closed_at, closed_by="staff")
        out = plan_purge([member, staff], self.TODAY)
        self.assertEqual([o["account_id"] for o in out], [2])
        self.assertEqual(out[0]["action"], "warn")

    def test_r6_unpaid_invoices_become_anonymise(self):
        acc = self.acc(last_seen_at=self.TODAY - timedelta(days=800),
                       unpaid_invoices=True)
        out = plan_purge([acc], self.TODAY)
        self.assertEqual(out[0]["action"], "anonymise")
        self.assertEqual(out[0]["approved_by"], DPO_APPROVER)

    def test_r7_litigation_hold_gets_no_action(self):
        acc = self.acc(last_seen_at=self.TODAY - timedelta(days=800),
                       litigation_hold=True)
        self.assertEqual(plan_purge([acc], self.TODAY), [])

    def test_r8_staff_email_gets_no_action_case_insensitive(self):
        acc = self.acc(email="Someone@TIDEWATER-Klatring.NO",
                       last_seen_at=self.TODAY - timedelta(days=800))
        self.assertEqual(plan_purge([acc], self.TODAY), [])

    def test_r9_no_email_in_output(self):
        acc = self.acc(email="secret.member@example.com",
                       last_seen_at=self.TODAY - timedelta(days=800))
        out = plan_purge([acc], self.TODAY)
        self.assertNotIn("secret.member@example.com", repr(out))

    def test_r10_cap_200_with_closed_first(self):
        open_accts = [
            self.acc(id=i, last_seen_at=self.TODAY - timedelta(days=730))
            for i in range(1, 206)
        ]
        closed_accts = [
            self.acc(id=1000 + i, last_seen_at=self.TODAY - timedelta(days=5),
                     closed_at=self.TODAY - timedelta(days=30), closed_by="member")
            for i in range(3)
        ]
        out = plan_purge(open_accts + closed_accts, self.TODAY)
        deletes = [o["account_id"] for o in out if o["action"] == "delete"]
        self.assertEqual(len(deletes), DELETE_CAP)
        self.assertEqual(set(deletes[:3]), {1000, 1001, 1002})
        self.assertEqual(deletes[3:], list(range(1, 198)))

    def test_r12_sorted_by_account_id(self):
        accts = [self.acc(id=i, last_seen_at=self.TODAY - timedelta(days=730))
                 for i in (5, 2, 9)]
        out = plan_purge(accts, self.TODAY)
        self.assertEqual([o["account_id"] for o in out], [2, 5, 9])

    def test_r14_past_due_keeps_original_due_date(self):
        last_seen = self.TODAY - timedelta(days=800)
        out = plan_purge([self.acc(last_seen_at=last_seen)], self.TODAY)
        self.assertEqual(out[0]["due"], (last_seen + timedelta(days=730)).isoformat())

    def test_r15_output_keys_exact(self):
        accts = [
            self.acc(id=1, last_seen_at=self.TODAY - timedelta(days=730)),
            self.acc(id=2, last_seen_at=self.TODAY - timedelta(days=725)),
        ]
        for item in plan_purge(accts, self.TODAY):
            self.assertEqual(set(item.keys()), set(OUTPUT_KEYS))

    def test_r17_skips_missing_last_seen_and_missing_closed_by(self):
        skipped = []
        accts = [
            self.acc(id=1, last_seen_at=None),
            self.acc(id=2, closed_at=self.TODAY, closed_by=None),
            self.acc(id=3, last_seen_at=self.TODAY - timedelta(days=800)),
        ]
        out = plan_purge(accts, self.TODAY, skipped=skipped)
        self.assertEqual(skipped, [1, 2])
        self.assertEqual([o["account_id"] for o in out], [3])


if __name__ == "__main__":
    unittest.main()