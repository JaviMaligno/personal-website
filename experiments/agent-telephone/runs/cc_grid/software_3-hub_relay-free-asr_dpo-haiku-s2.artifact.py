"""Plan GDPR purge actions for Tidewater Climbing member accounts.

Standard library only. Entry point: plan_purge(accounts, today).
Run the embedded unit tests with: python3 -I purge_plan.py

Decisions where the spec was open:
- Ids may be str or int. Output ordering and cap tie-breaks use the key
  (str(id), type name), so mixed ids never raise and the order is total.
- A closed account past its deletion date with unpaid invoices follows rule 4
  like any other account: it gets "anonymise", not "delete", so it is not
  counted against the delete cap.
- unpaid_invoices of None is treated as 0.
- A missing or non-string email is treated as not staff.
- An account with last_seen_at None is excluded even if closed_at is set.
- The staff domain is the text after the last "@", compared in lowercase, with
  no whitespace trimming.

Open questions for the client (unanswered):
- Should a closed account past its deletion date with unpaid invoices be
  anonymised (implemented) or deleted?
- Should unpaid_invoices of None mean 0 (implemented) or exclude the account?
- Should an account with last_seen_at None but closed_at set be excluded
  (implemented) or aged by closed_at alone?
- Should the 200 cap count anonymise actions? Implemented: no.
- Should whitespace around the email domain be trimmed before the staff check?
- Is the approver name fixed for every run, or should the caller supply it?
- Duplicate account ids are not deduplicated.
"""

import copy
import unittest
from datetime import date, timedelta

APPROVER = "Tordis Svenbjorn Dottir"
STAFF_DOMAIN = "tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200


def _is_staff(email):
    if not isinstance(email, str) or "@" not in email:
        return False
    domain = email.rsplit("@", 1)[1]
    return domain.lower() == STAFF_DOMAIN


def _due_date(acct):
    candidates = [acct["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)]
    if acct.get("closed_at") is not None:
        candidates.append(acct["closed_at"] + timedelta(days=CLOSED_GRACE_DAYS))
    return min(candidates)


def _id_key(account_id):
    return (str(account_id), type(account_id).__name__)


def _classify(acct, today):
    """Return (action, due) for an account, or None if no action applies."""
    if _is_staff(acct.get("email")):
        return None
    if acct.get("litigation_hold"):
        return None
    if acct.get("last_seen_at") is None:
        return None
    due = _due_date(acct)
    if due <= today:
        if (acct.get("unpaid_invoices") or 0) > 0:
            return "anonymise", due
        return "delete", due
    if due <= today + timedelta(days=WARN_WINDOW_DAYS):
        if acct.get("closed_by") == "member":
            return None
        return "warn", due
    return None


def _make_action(account_id, action, due):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else APPROVER,
    }


def plan_purge(accounts, today):
    others = []
    deletes = []
    for acct in accounts:
        result = _classify(acct, today)
        if result is None:
            continue
        action, due = result
        if action == "delete":
            deletes.append((acct, due))
        else:
            others.append(_make_action(acct["id"], action, due))

    # Closed accounts (closed_at set) first, then inactive; earlier due first;
    # then id as tie-break.
    deletes.sort(key=lambda item: (
        item[0].get("closed_at") is None,
        item[1],
        _id_key(item[0]["id"]),
    ))
    kept = [_make_action(acct["id"], "delete", due) for acct, due in deletes[:DELETE_CAP]]

    result = others + kept
    result.sort(key=lambda a: _id_key(a["account_id"]))
    return result


# ---------------------------------------------------------------- tests

TODAY = date(2026, 10, 13)


def _acct(**over):
    base = {
        "id": 1,
        "email": "member@example.org",
        "status": "active",
        "last_seen_at": TODAY - timedelta(days=100),
        "last_login": None,
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
        "tenant": "t1",
    }
    base.update(over)
    return base


class PurgeBoundaryTests(unittest.TestCase):

    def test_inactivity_boundary_delete_on_exact_today(self):
        out = plan_purge([_acct(last_seen_at=TODAY - timedelta(days=730))], TODAY)
        self.assertEqual(out, [{"account_id": 1, "action": "delete",
                                "due": TODAY.isoformat(),
                                "approved_by": APPROVER}])

    def test_inactivity_warn_at_today_plus_1(self):
        out = plan_purge([_acct(last_seen_at=TODAY - timedelta(days=729))], TODAY)
        self.assertEqual([a["action"] for a in out], ["warn"])

    def test_warn_at_today_plus_14(self):
        out = plan_purge([_acct(last_seen_at=TODAY - timedelta(days=716))], TODAY)
        self.assertEqual([a["action"] for a in out], ["warn"])
        self.assertEqual(out[0]["due"], "2026-10-27")

    def test_no_action_at_today_plus_15(self):
        out = plan_purge([_acct(last_seen_at=TODAY - timedelta(days=715))], TODAY)
        self.assertEqual(out, [])

    def test_closed_grace_delete_on_exact_today(self):
        out = plan_purge([_acct(last_seen_at=TODAY - timedelta(days=1),
                                closed_at=TODAY - timedelta(days=30),
                                closed_by="staff")], TODAY)
        self.assertEqual([a["action"] for a in out], ["delete"])
        self.assertEqual(out[0]["due"], TODAY.isoformat())

    def test_closed_grace_warn_at_today_plus_14_for_staff_closed(self):
        out = plan_purge([_acct(last_seen_at=TODAY - timedelta(days=1),
                                closed_at=TODAY - timedelta(days=16),
                                closed_by="staff")], TODAY)
        self.assertEqual([a["action"] for a in out], ["warn"])
        self.assertEqual(out[0]["due"], "2026-10-27")

    def test_closed_grace_no_action_at_today_plus_15(self):
        out = plan_purge([_acct(last_seen_at=TODAY - timedelta(days=1),
                                closed_at=TODAY - timedelta(days=15),
                                closed_by="staff")], TODAY)
        self.assertEqual(out, [])

    def test_earlier_of_two_candidates_is_used(self):
        # last_seen gives today+630; closed gives today-1: closed wins.
        out = plan_purge([_acct(last_seen_at=TODAY - timedelta(days=100),
                                closed_at=TODAY - timedelta(days=31),
                                closed_by="staff")], TODAY)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], (TODAY - timedelta(days=1)).isoformat())


class PurgeRuleTests(unittest.TestCase):

    def test_closed_by_member_gets_no_warn(self):
        out = plan_purge([_acct(last_seen_at=TODAY - timedelta(days=1),
                                closed_at=TODAY - timedelta(days=16),
                                closed_by="member")], TODAY)
        self.assertEqual(out, [])

    def test_closed_by_member_still_deleted_when_due(self):
        out = plan_purge([_acct(last_seen_at=TODAY - timedelta(days=1),
                                closed_at=TODAY - timedelta(days=30),
                                closed_by="member")], TODAY)
        self.assertEqual([a["action"] for a in out], ["delete"])

    def test_closed_by_member_still_anonymised_when_due(self):
        out = plan_purge([_acct(last_seen_at=TODAY - timedelta(days=1),
                                closed_at=TODAY - timedelta(days=30),
                                closed_by="member",
                                unpaid_invoices=3)], TODAY)
        self.assertEqual([a["action"] for a in out], ["anonymise"])

    def test_anonymise_when_unpaid_invoices(self):
        out = plan_purge([_acct(last_seen_at=TODAY - timedelta(days=800),
                                unpaid_invoices=2)], TODAY)
        self.assertEqual([a["action"] for a in out], ["anonymise"])
        self.assertEqual(out[0]["approved_by"], APPROVER)

    def test_litigation_hold_excludes_all_action_types(self):
        accts = [
            _acct(id=1, last_seen_at=TODAY - timedelta(days=800), litigation_hold=True),
            _acct(id=2, last_seen_at=TODAY - timedelta(days=800),
                  unpaid_invoices=1, litigation_hold=True),
            _acct(id=3, last_seen_at=TODAY - timedelta(days=729), litigation_hold=True),
        ]
        self.assertEqual(plan_purge(accts, TODAY), [])

    def test_staff_domain_excluded_any_case(self):
        accts = [
            _acct(id=1, email="ops@tidewater-klatring.no",
                  last_seen_at=TODAY - timedelta(days=800)),
            _acct(id=2, email="ops@TIDEWATER-KLATRING.no",
                  last_seen_at=TODAY - timedelta(days=800)),
            _acct(id=3, email="ops@Tidewater-Klatring.NO",
                  last_seen_at=TODAY - timedelta(days=800), unpaid_invoices=1),
        ]
        self.assertEqual(plan_purge(accts, TODAY), [])

    def test_staff_match_is_exact_domain(self):
        accts = [
            _acct(id=1, email="ops@tidewater-klatring.com",
                  last_seen_at=TODAY - timedelta(days=800)),
            _acct(id=2, email="ops@x.tidewater-klatring.no",
                  last_seen_at=TODAY - timedelta(days=800)),
        ]
        out = plan_purge(accts, TODAY)
        self.assertEqual([a["account_id"] for a in out], [1, 2])

    def test_missing_last_seen_excluded_without_error(self):
        accts = [
            _acct(id=1, last_seen_at=None, closed_at=TODAY - timedelta(days=40)),
            _acct(id=2, last_seen_at=None, unpaid_invoices=4),
        ]
        self.assertEqual(plan_purge(accts, TODAY), [])


class PurgeCapAndOrderTests(unittest.TestCase):

    def test_cap_keeps_closed_accounts_first(self):
        accts = []
        for i in range(150):
            accts.append(_acct(id=f"c{i:03d}",
                               last_seen_at=TODAY - timedelta(days=800),
                               closed_at=TODAY - timedelta(days=31),
                               closed_by="staff"))
        for i in range(150):
            # Larger i means earlier due date, so these are the earliest inactive.
            accts.append(_acct(id=f"i{i:03d}",
                               last_seen_at=TODAY - timedelta(days=900 + i)))
        out = plan_purge(accts, TODAY)
        deletes = {a["account_id"] for a in out if a["action"] == "delete"}
        self.assertEqual(len(deletes), 200)
        closed_ids = {f"c{i:03d}" for i in range(150)}
        self.assertTrue(closed_ids <= deletes)
        kept_inactive = deletes - closed_ids
        self.assertEqual(kept_inactive, {f"i{i:03d}" for i in range(100, 150)})

    def test_cap_does_not_apply_to_anonymise_or_warn(self):
        accts = [_acct(id=i, last_seen_at=TODAY - timedelta(days=800),
                       unpaid_invoices=1) for i in range(210)]
        accts += [_acct(id=f"w{i}", last_seen_at=TODAY - timedelta(days=729))
                  for i in range(5)]
        out = plan_purge(accts, TODAY)
        self.assertEqual(sum(a["action"] == "anonymise" for a in out), 210)
        self.assertEqual(sum(a["action"] == "warn" for a in out), 5)

    def test_output_sorted_by_id_with_mixed_types(self):
        accts = [
            _acct(id=3, last_seen_at=TODAY - timedelta(days=800)),
            _acct(id="b", last_seen_at=TODAY - timedelta(days=800)),
            _acct(id=1, last_seen_at=TODAY - timedelta(days=800)),
            _acct(id="a", last_seen_at=TODAY - timedelta(days=800)),
        ]
        out = plan_purge(accts, TODAY)
        self.assertEqual([a["account_id"] for a in out], [1, 3, "a", "b"])

    def test_approved_by_values(self):
        accts = [
            _acct(id=1, last_seen_at=TODAY - timedelta(days=800)),
            _acct(id=2, last_seen_at=TODAY - timedelta(days=800), unpaid_invoices=1),
            _acct(id=3, last_seen_at=TODAY - timedelta(days=729)),
        ]
        out = plan_purge(accts, TODAY)
        by_action = {a["action"]: a["approved_by"] for a in out}
        self.assertEqual(by_action["delete"], APPROVER)
        self.assertEqual(by_action["anonymise"], APPROVER)
        self.assertIsNone(by_action["warn"])

    def test_due_is_iso_string_and_keys_exact(self):
        out = plan_purge([_acct(last_seen_at=TODAY - timedelta(days=800))], TODAY)
        self.assertEqual(out[0]["due"], "2026-08-04")
        self.assertIsInstance(out[0]["due"], str)
        self.assertEqual(set(out[0].keys()),
                         {"account_id", "action", "due", "approved_by"})


class PurgeSafetyTests(unittest.TestCase):

    def test_no_email_in_output(self):
        accts = [_acct(id=i, email=f"secret{i}@example.org",
                       last_seen_at=TODAY - timedelta(days=800)) for i in range(3)]
        text = repr(plan_purge(accts, TODAY))
        for i in range(3):
            self.assertNotIn(f"secret{i}@example.org", text)
        self.assertNotIn("@", text)

    def test_inputs_not_mutated(self):
        accts = [
            _acct(id=1, last_seen_at=TODAY - timedelta(days=800)),
            _acct(id=2, last_seen_at=TODAY - timedelta(days=800),
                  closed_at=TODAY - timedelta(days=31), closed_by="member"),
            _acct(id=3, last_seen_at=TODAY - timedelta(days=729), unpaid_invoices=1),
        ]
        snapshot = copy.deepcopy(accts)
        plan_purge(accts, TODAY)
        self.assertEqual(accts, snapshot)


if __name__ == "__main__":
    unittest.main()