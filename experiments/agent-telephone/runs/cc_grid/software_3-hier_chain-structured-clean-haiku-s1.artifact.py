import unicodedata
import unittest
from datetime import date, datetime, timedelta

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARNING_WINDOW_DAYS = 14
DELETION_CAP = 200
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"
APPROVER = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"

_REQUIRED_KEYS = ("id", "email", "last_seen_at", "closed_at", "closed_by",
                  "unpaid_invoices", "litigation_hold")


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _is_staff(email):
    return email.strip().lower().endswith(STAFF_EMAIL_SUFFIX)


def _label(index, account):
    acct_id = account.get("id") if isinstance(account, dict) else None
    if acct_id is None:
        return f"index {index}"
    return f"account {acct_id!r}"


def _validate(accounts, today):
    if not _is_date(today):
        raise TypeError("today must be a datetime.date and not a datetime")
    if not isinstance(accounts, list):
        raise ValueError("accounts must be a list")
    seen = set()
    for index, account in enumerate(accounts):
        if not isinstance(account, dict):
            raise ValueError(f"index {index}: account must be a dict")
        label = _label(index, account)
        for key in _REQUIRED_KEYS:
            if key not in account:
                raise ValueError(f"{label}: missing key {key!r}")
        acct_id = account["id"]
        if acct_id is None:
            raise ValueError(f"{label}: id must not be None")
        if not isinstance(acct_id, str):
            raise ValueError(f"{label}: id must be a str")
        if acct_id in seen:
            raise ValueError(f"{label}: duplicate id")
        seen.add(acct_id)
        if not isinstance(account["email"], str):
            raise ValueError(f"{label}: email must be a str")
        if not _is_date(account["last_seen_at"]):
            raise ValueError(f"{label}: last_seen_at must be a date")
        closed_at = account["closed_at"]
        closed_by = account["closed_by"]
        if closed_at is not None:
            if not _is_date(closed_at):
                raise ValueError(f"{label}: closed_at must be None or a date")
            if closed_by not in ("member", "staff"):
                raise ValueError(f"{label}: closed_by must be 'member' or 'staff'")
        elif closed_by is not None:
            raise ValueError(f"{label}: closed_by must be None when closed_at is None")
        if not isinstance(account["unpaid_invoices"], (bool, int)):
            raise ValueError(f"{label}: unpaid_invoices must be a bool or int")
        if not isinstance(account["litigation_hold"], bool):
            raise ValueError(f"{label}: litigation_hold must be a bool")


def _action(acct_id, action, due, approved_by):
    return {
        "account_id": acct_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    _validate(accounts, today)

    anonymise = []
    deletes = []
    warns = []
    window_end = today + timedelta(days=WARNING_WINDOW_DAYS)

    for acct in accounts:
        if acct["litigation_hold"] or _is_staff(acct["email"]):
            continue
        closed_at = acct["closed_at"]
        due = acct["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=CLOSED_GRACE_DAYS))
        acct_id = acct["id"]
        if due <= today:
            if bool(acct["unpaid_invoices"]):
                anonymise.append((acct_id, due))
            else:
                deletes.append((0 if closed_at is not None else 1, due, acct_id))
        elif due <= window_end:
            if acct["closed_by"] != "member":
                warns.append((acct_id, due))

    deletes.sort()
    actions = []
    for _, due, acct_id in deletes[:DELETION_CAP]:
        actions.append(_action(acct_id, "delete", due, APPROVER))
    for acct_id, due in anonymise:
        actions.append(_action(acct_id, "anonymise", due, APPROVER))
    for acct_id, due in warns:
        actions.append(_action(acct_id, "warn", due, None))

    actions.sort(key=lambda a: a["account_id"])
    return actions


T = date(2026, 10, 13)


def _acct(aid, **kw):
    base = {
        "id": aid,
        "email": f"member{aid}@example.com",
        "last_seen_at": T - timedelta(days=100),
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
    }
    base.update(kw)
    return base


class PlanPurgeTests(unittest.TestCase):

    def test_approver_is_nfc_and_exact(self):
        expected = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"
        self.assertEqual(APPROVER, unicodedata.normalize("NFC", expected))
        self.assertTrue(unicodedata.is_normalized("NFC", APPROVER))

    def test_due_today_delete(self):
        a = _acct("a", last_seen_at=T - timedelta(days=730))
        self.assertEqual(plan_purge([a], T), [
            {"account_id": "a", "action": "delete", "due": "2026-10-13", "approved_by": APPROVER}])

    def test_due_yesterday_delete(self):
        a = _acct("a", last_seen_at=T - timedelta(days=731))
        out = plan_purge([a], T)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], "2026-10-12")

    def test_warn_at_today_plus_14(self):
        a = _acct("a", last_seen_at=(T + timedelta(days=14)) - timedelta(days=730))
        self.assertEqual(plan_purge([a], T), [
            {"account_id": "a", "action": "warn", "due": "2026-10-27", "approved_by": None}])

    def test_no_action_at_today_plus_15(self):
        a = _acct("a", last_seen_at=(T + timedelta(days=15)) - timedelta(days=730))
        self.assertEqual(plan_purge([a], T), [])

    def test_member_closed_due_today_still_deleted(self):
        a = _acct("a", closed_at=T - timedelta(days=30), closed_by="member")
        out = plan_purge([a], T)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], "2026-10-13")

    def test_closed_grace_sets_due(self):
        a = _acct("a", closed_at=date(2026, 9, 13), closed_by="staff",
                  last_seen_at=date(2000, 1, 1))
        out = plan_purge([a], T)
        self.assertEqual(out[0]["action"], "delete")
        self.assertEqual(out[0]["due"], "2026-10-13")

    def test_member_closed_due_20_no_action(self):
        a = _acct("a", closed_at=date(2026, 9, 20), closed_by="member",
                  last_seen_at=date(2000, 1, 1))
        self.assertEqual(plan_purge([a], T), [])

    def test_staff_closed_due_20_warn(self):
        a = _acct("a", closed_at=date(2026, 9, 20), closed_by="staff",
                  last_seen_at=date(2000, 1, 1))
        out = plan_purge([a], T)
        self.assertEqual(out, [
            {"account_id": "a", "action": "warn", "due": "2026-10-20", "approved_by": None}])

    def test_unpaid_due_today_anonymise(self):
        a = _acct("a", unpaid_invoices=3, last_seen_at=T - timedelta(days=730))
        out = plan_purge([a], T)
        self.assertEqual(out[0]["action"], "anonymise")
        self.assertEqual(out[0]["approved_by"], APPROVER)

    def test_unpaid_in_window_warn(self):
        a = _acct("a", unpaid_invoices=1, last_seen_at=(T + timedelta(days=5)) - timedelta(days=730))
        out = plan_purge([a], T)
        self.assertEqual(out[0]["action"], "warn")

    def test_litigation_hold_no_action(self):
        a = _acct("a", litigation_hold=True, last_seen_at=T - timedelta(days=730))
        self.assertEqual(plan_purge([a], T), [])

    def test_staff_uppercase_whitespace_no_action(self):
        a = _acct("a", email="  Someone@Tidewater-Klatring.NO ", last_seen_at=T - timedelta(days=730))
        self.assertEqual(plan_purge([a], T), [])

    def test_staff_subdomain_not_matched(self):
        a = _acct("a", email="someone@tidewater-klatring.no.example.com",
                  last_seen_at=T - timedelta(days=730))
        self.assertEqual(plan_purge([a], T)[0]["action"], "delete")

    def test_last_login_tenant_status_ignored(self):
        base = [_acct("a", last_seen_at=T - timedelta(days=730)),
                _acct("b", last_seen_at=(T + timedelta(days=3)) - timedelta(days=730))]
        with_extra_1 = [dict(x, status="active", last_login=date(2001, 1, 1), tenant="x")
                        for x in base]
        with_extra_2 = [dict(x, status="closed", last_login=date(2026, 10, 1), tenant="y")
                        for x in base]
        self.assertEqual(plan_purge(with_extra_1, T), plan_purge(with_extra_2, T))
        self.assertEqual(plan_purge(with_extra_1, T), plan_purge(base, T))

    def test_output_shape_and_no_email(self):
        accts = [_acct("a", last_seen_at=T - timedelta(days=730)),
                 _acct("b", unpaid_invoices=2, last_seen_at=T - timedelta(days=730)),
                 _acct("c", last_seen_at=(T + timedelta(days=1)) - timedelta(days=730))]
        out = plan_purge(accts, T)
        emails = {a["email"] for a in accts}
        for item in out:
            self.assertEqual(set(item.keys()),
                             {"account_id", "action", "due", "approved_by"})
            for value in item.values():
                self.assertNotIn(value, emails)

    def test_output_sorted_by_account_id(self):
        accts = [_acct(x, last_seen_at=T - timedelta(days=730)) for x in ("c", "a", "b")]
        ids = [item["account_id"] for item in plan_purge(accts, T)]
        self.assertEqual(ids, sorted(ids))

    def test_cap_keeps_closed_first_then_oldest_non_closed(self):
        accts = [_acct(f"n{i:03d}", last_seen_at=T - timedelta(days=730)) for i in range(205)]
        accts += [_acct(f"c{i}", closed_at=T - timedelta(days=30), closed_by="staff",
                        last_seen_at=date(2000, 1, 1)) for i in range(3)]
        out = plan_purge(accts, T)
        deletes = [item["account_id"] for item in out if item["action"] == "delete"]
        self.assertEqual(len(deletes), DELETION_CAP)
        for i in range(3):
            self.assertIn(f"c{i}", deletes)
        kept_non_closed = sorted(d for d in deletes if d.startswith("n"))
        self.assertEqual(kept_non_closed, [f"n{i:03d}" for i in range(197)])

    def test_anonymise_not_capped(self):
        accts = [_acct(f"n{i:03d}", last_seen_at=T - timedelta(days=730)) for i in range(205)]
        accts += [_acct(f"u{i:03d}", unpaid_invoices=1, last_seen_at=T - timedelta(days=730))
                  for i in range(10)]
        out = plan_purge(accts, T)
        anon = [item for item in out if item["action"] == "anonymise"]
        self.assertEqual(len(anon), 10)

    def test_no_duplicate_account_ids_in_output(self):
        accts = [_acct("a", last_seen_at=T - timedelta(days=730)),
                 _acct("b", last_seen_at=(T + timedelta(days=2)) - timedelta(days=730))]
        ids = [item["account_id"] for item in plan_purge(accts, T)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_empty_list(self):
        self.assertEqual(plan_purge([], T), [])

    def test_today_datetime_raises_type_error(self):
        with self.assertRaises(TypeError):
            plan_purge([], datetime(2026, 10, 13))

    def test_not_a_list_raises(self):
        with self.assertRaises(ValueError):
            plan_purge(("a",), T)

    def test_non_dict_account_raises(self):
        with self.assertRaises(ValueError):
            plan_purge(["x"], T)

    def test_missing_key_raises(self):
        a = _acct("a")
        del a["unpaid_invoices"]
        with self.assertRaises(ValueError):
            plan_purge([a], T)

    def test_id_none_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct(None)], T)

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct("a"), _acct("a")], T)

    def test_email_must_be_str(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct("a", email=None)], T)

    def test_last_seen_datetime_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct("a", last_seen_at=datetime(2024, 1, 1))], T)

    def test_last_seen_none_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct("a", last_seen_at=None)], T)

    def test_closed_at_datetime_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct("a", closed_at=datetime(2026, 9, 1), closed_by="staff")], T)

    def test_closed_by_invalid_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct("a", closed_at=date(2026, 9, 1), closed_by="admin")], T)

    def test_closed_by_without_closed_at_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct("a", closed_by="member")], T)

    def test_unpaid_none_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct("a", unpaid_invoices=None)], T)

    def test_unpaid_string_raises(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct("a", unpaid_invoices="3")], T)

    def test_litigation_hold_must_be_bool(self):
        with self.assertRaises(ValueError):
            plan_purge([_acct("a", litigation_hold=None)], T)

    def test_validation_before_any_output(self):
        good = _acct("a", last_seen_at=T - timedelta(days=730))
        bad = _acct("b", litigation_hold="yes")
        with self.assertRaises(ValueError):
            plan_purge([good, bad], T)


if __name__ == "__main__":
    unittest.main()


# Assumptions and flagged items
# 1. The status column is not referenced by any requirement and is ignored.
# 2. Under R18 a single malformed record aborts the whole run (fail closed). Skipping the record instead is a PM decision.
# 3. Warnings go to unpaid-invoice accounts that will be anonymised; notice text may need to differ. PM decision.
# 4. Anonymise actions are uncapped per R11, so a large anonymise run could lock the database. Flagged as a risk; no cap added.
# 5. Accounts over the 200 cap stay due and are picked up on the next run.
# 6. Staff subdomains are not matched, per the literal spec (R19).
# 7. R18b requires ids to be str; integer ids are rejected. Confirm with the client if numeric ids exist.
# 8. Arithmetic discrepancy in R28: 205 non-closed plus 3 closed deletion candidates is 208. Keeping 200 drops 8, not 2. The implementation and test follow the rule (closed first, then oldest non-closed), so 8 non-closed accounts are dropped. The R28 wording should be corrected.
# 9. Staff matching uses strip and lower on the full email; an email with a trailing dot or extra whitespace inside the address is not normalised further.