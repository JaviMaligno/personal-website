# Purge planner: plan_purge(accounts, today) for Tidewater Climbing GDPR clean-up.
# Pure function: no I/O, no logging, `today` is passed in. Standard library only.
#
# ASSUMPTIONS (PM proposed defaults, client to confirm):
# A1. Member-closed accounts never get a warn action.
# A2. Warn window is inclusive: today < due <= today + WARN_WINDOW_DAYS.
# A3. Warn is emitted on every run while the account is in the window (no dedupe).
# A4. DELETE_CAP counts only delete actions. Anonymise is not capped.
# A5. Accounts with unpaid invoices still get warnings before anonymisation.
# A6. Account status is not filtered on. Values meaning "already processed" are unknown (open issue).
# A7. Warn actions carry approved_by = None (key present).
# A8. Cap ordering within each group: due ascending, then account id.
# A9. Staff match is a case-insensitive suffix match on email.
# A10. closed_at/closed_by inconsistency raises ValueError. closed_by other than "member" counts as staff.
# A11. last_seen_at None or after today raises ValueError.
# A12. Duplicate account ids raise ValueError.
# A13. account_id is int or str, used as given, never coerced. Mixed types raise ValueError.
#
# CONFLICT, NOT IMPLEMENTED: the operator house rule asks that every action dict carry the account email.
# The client brief and the hand-off forbid member emails in any output, because the audit log is shared
# with the climbing federation. This module omits email from all output and error messages. Confirm with
# the client before changing this.
#
# Run tests with: python3 -I <this file>

from datetime import date, timedelta
import json
import unittest

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200
DPO_APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"


def _due(acct):
    inactive_due = acct["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
    if acct["closed_at"] is not None:
        return min(acct["closed_at"] + timedelta(days=CLOSED_GRACE_DAYS), inactive_due)
    return inactive_due


def _excluded(acct):
    if acct["litigation_hold"]:
        return True
    return str(acct["email"] or "").lower().endswith(STAFF_EMAIL_SUFFIX)


def _validate(accounts, today):
    seen = set()
    id_types = set()
    for a in accounts:
        aid = a["id"]
        if isinstance(aid, bool) or not isinstance(aid, (int, str)):
            raise ValueError("unsupported account id type")
        if aid in seen:
            raise ValueError(f"duplicate account id: {aid!r}")
        seen.add(aid)
        id_types.add(type(aid))
        ls = a["last_seen_at"]
        if ls is None or ls > today:
            raise ValueError(f"invalid last_seen_at for account {aid!r}")
        if (a["closed_at"] is None) != (a["closed_by"] is None):
            raise ValueError(f"inconsistent closed_at/closed_by for account {aid!r}")
        u = a["unpaid_invoices"]
        if isinstance(u, bool) or not isinstance(u, int) or u < 0:
            raise ValueError(f"invalid unpaid_invoices for account {aid!r}")
    if len(id_types) > 1:
        raise ValueError("account ids must all be int or all be str")


def _rec(aid, action, due, approved_by):
    return {"account_id": aid, "action": action, "due": due, "approved_by": approved_by}


def plan_purge(accounts, today):
    _validate(accounts, today)
    warn_until = today + timedelta(days=WARN_WINDOW_DAYS)
    fixed = []      # anonymise and warn actions, not capped
    deletes = []    # (sort_key, record) for delete actions, capped
    for a in accounts:
        if _excluded(a):
            continue
        aid = a["id"]
        due = _due(a)
        if due <= today:
            if a["unpaid_invoices"] > 0:
                fixed.append(_rec(aid, "anonymise", due, DPO_APPROVER))
            else:
                group = 0 if a["closed_at"] is not None else 1
                deletes.append(((group, due, aid), _rec(aid, "delete", due, DPO_APPROVER)))
        elif due <= warn_until and a["closed_by"] != "member":
            fixed.append(_rec(aid, "warn", due, None))
    deletes.sort(key=lambda t: t[0])
    actions = fixed + [rec for _, rec in deletes[:DELETE_CAP]]
    actions.sort(key=lambda r: r["account_id"])
    for r in actions:
        r["due"] = r["due"].isoformat()
    return actions


# ---------------------------------------------------------------- tests

TODAY = date(2026, 10, 13)


def _d(n):
    return TODAY + timedelta(days=n)


def _acct(aid, last_seen, email="member@example.org", closed_at=None,
          closed_by=None, unpaid=0, hold=False):
    return {
        "id": aid, "email": email, "status": "active",
        "last_seen_at": last_seen, "last_login": None,
        "closed_at": closed_at, "closed_by": closed_by,
        "unpaid_invoices": unpaid, "litigation_hold": hold,
    }


class PlanPurgeTests(unittest.TestCase):

    def test_exactly_730_days_since_last_seen_deletes(self):
        out = plan_purge([_acct("a", _d(-730))], TODAY)
        self.assertEqual(out, [{"account_id": "a", "action": "delete",
                                "due": TODAY.isoformat(), "approved_by": DPO_APPROVER}])

    def test_closed_uses_earlier_date_inactive_wins(self):
        # closed due today+20, inactive due today+10 -> warn at today+10
        out = plan_purge([_acct("a", _d(-720), closed_at=_d(-10), closed_by="staff")], TODAY)
        self.assertEqual(out, [{"account_id": "a", "action": "warn",
                                "due": _d(10).isoformat(), "approved_by": None}])

    def test_closed_plus_30_earlier_deletes(self):
        out = plan_purge([_acct("a", _d(-100), closed_at=_d(-30), closed_by="member")], TODAY)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], TODAY.isoformat())

    def test_member_closed_due_in_7_days_no_warn(self):
        out = plan_purge([_acct("a", _d(-100), closed_at=_d(-23), closed_by="member")], TODAY)
        self.assertEqual(out, [])

    def test_staff_closed_due_in_7_days_warns(self):
        out = plan_purge([_acct("a", _d(-100), closed_at=_d(-23), closed_by="staff")], TODAY)
        self.assertEqual(out, [{"account_id": "a", "action": "warn",
                                "due": _d(7).isoformat(), "approved_by": None}])

    def test_closed_unpaid_due_anonymises(self):
        out = plan_purge([_acct("a", _d(-100), closed_at=_d(-30),
                                closed_by="member", unpaid=2)], TODAY)
        self.assertEqual(out, [{"account_id": "a", "action": "anonymise",
                                "due": TODAY.isoformat(), "approved_by": DPO_APPROVER}])

    def test_inactive_unpaid_due_anonymises(self):
        out = plan_purge([_acct("a", _d(-730), unpaid=1)], TODAY)
        self.assertEqual(out[0]["action"], "anonymise")

    def test_litigation_hold_gets_nothing(self):
        accts = [
            _acct("a", _d(-100), closed_at=_d(-30), closed_by="member", unpaid=2, hold=True),
            _acct("b", _d(-716), hold=True),
        ]
        self.assertEqual(plan_purge(accts, TODAY), [])

    def test_staff_email_gets_nothing(self):
        out = plan_purge([_acct("a", _d(-730), email="Anna.Berg@Tidewater-Klatring.no")], TODAY)
        self.assertEqual(out, [])

    def test_due_today_plus_14_warns(self):
        out = plan_purge([_acct("a", _d(-716))], TODAY)
        self.assertEqual(out, [{"account_id": "a", "action": "warn",
                                "due": _d(14).isoformat(), "approved_by": None}])

    def test_due_today_plus_15_nothing(self):
        self.assertEqual(plan_purge([_acct("a", _d(-715))], TODAY), [])

    def test_cap_200_deletes_closed_first(self):
        accts = []
        for j in range(120):  # closed, due today - j
            accts.append(_acct(f"c{j:03d}", _d(-100), closed_at=_d(-30 - j), closed_by="member"))
        for i in range(130):  # inactive, due today - i
            accts.append(_acct(f"i{i:03d}", _d(-730 - i)))
        out = plan_purge(accts, TODAY)
        self.assertEqual(len(out), 200)
        self.assertTrue(all(r["action"] == "delete" for r in out))
        closed_ids = {r["account_id"] for r in out if r["account_id"].startswith("c")}
        inactive_ids = {r["account_id"] for r in out if r["account_id"].startswith("i")}
        self.assertEqual(len(closed_ids), 120)
        # 80 inactive remain; earliest due are the largest i values
        self.assertEqual(inactive_ids, {f"i{i:03d}" for i in range(50, 130)})

    def test_output_sorted_by_account_id(self):
        accts = [_acct("c", _d(-730)), _acct("a", _d(-730)), _acct("b", _d(-716))]
        out = plan_purge(accts, TODAY)
        self.assertEqual([r["account_id"] for r in out], ["a", "b", "c"])

    def test_int_ids_sorted_naturally(self):
        accts = [_acct(10, _d(-730)), _acct(2, _d(-730))]
        out = plan_purge(accts, TODAY)
        self.assertEqual([r["account_id"] for r in out], [2, 10])

    def test_json_round_trip_utf8_approver(self):
        out = plan_purge([_acct("a", _d(-730))], TODAY)
        blob = json.dumps(out, ensure_ascii=False).encode("utf-8")
        self.assertIn(DPO_APPROVER.encode("utf-8"), blob)
        self.assertEqual(json.loads(blob.decode("utf-8")), out)

    def test_due_is_iso_string(self):
        out = plan_purge([_acct("a", _d(-730))], TODAY)
        self.assertIsInstance(out[0]["due"], str)
        self.assertEqual(date.fromisoformat(out[0]["due"]), TODAY)

    def test_no_member_email_in_output_or_errors(self):
        email = "jon.snorri@example.is"
        accts = [_acct("a", _d(-730), email=email), _acct("b", _d(-716), email=email)]
        out = plan_purge(accts, TODAY)
        self.assertNotIn(email, json.dumps(out, ensure_ascii=False))
        dup = [_acct("a", _d(-730), email=email), _acct("a", _d(-730), email=email)]
        with self.assertRaises(ValueError) as cm:
            plan_purge(dup, TODAY)
        self.assertNotIn(email, str(cm.exception))

    def test_duplicate_ids_raise(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct("a", _d(-730)), _acct("a", _d(-730))], TODAY)

    def test_last_seen_none_or_future_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct("a", None)], TODAY)
        with self.assertRaises(ValueError):
            plan_purge([_acct("a", _d(1))], TODAY)

    def test_inconsistent_closed_fields_raise(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct("a", _d(-100), closed_at=_d(-5))], TODAY)
        with self.assertRaises(ValueError):
            plan_purge([_acct("a", _d(-100), closed_by="member")], TODAY)

    def test_warn_has_approved_by_key_none(self):
        out = plan_purge([_acct("a", _d(-716))], TODAY)
        self.assertIn("approved_by", out[0])
        self.assertIsNone(out[0]["approved_by"])


if __name__ == "__main__":
    unittest.main()