"""Tidewater Climbing GDPR member-account purge planner.

Pure planner: plan_purge(accounts, today) -> list of action dicts.
Run the embedded tests with: python purge.py

Deviation from the house rule: the house rule says each action should carry the
account's email, but the task spec requires exactly four keys and no email
anywhere in the output. The spec is followed, so support must join on account_id.

Assumptions:
- datetime.datetime is rejected for `today` and treated as a wrong-typed date
  in account fields.
- A non-dict record, or one with a missing/None/unhashable id, raises ValueError.
- unpaid_invoices of any type other than bool/int/list/tuple is unknown (None).
- A litigation_hold that is not exactly False (None, 0, "") is treated as held.
- A wrong-typed closed_at is treated as missing, so it does not suppress warns.

Open points for the client:
- Should the cap also cover anonymise? (Implemented for delete only.)
- Should staff-closed accounts rank below member-closed in the cap?
- Warnings repeat daily because the planner is stateless.
- Already-anonymised accounts keep being emitted because status is not used.
- Accounts never seen and not closed are never purged.
- Does invoice retention apply to paid invoices too?
"""
import datetime as _dt
import json
import logging
import unittest
from datetime import date, timedelta

MAX_DELETES_PER_RUN = 200
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"
APPROVER_NAME = "Tordis Svenbjorn Dottir"

log = logging.getLogger(__name__)


def _is_eligible(account):
    """Single place for eligibility; a status filter could be added here."""
    return True


def _date_or_none(value, acc_id, field):
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, _dt.datetime):
        return value
    log.warning("account %s: invalid %s, treated as missing", acc_id, field)
    return None


def _is_staff(email):
    if not isinstance(email, str):
        return False
    return email.strip().lower().endswith(STAFF_EMAIL_SUFFIX)


def _has_unpaid(value):
    """True/False, or None when unknown."""
    if isinstance(value, (bool, int)):
        return bool(value)
    if isinstance(value, (list, tuple)):
        return len(value) > 0
    return None


def _validate(accounts, today):
    if not isinstance(today, date) or isinstance(today, _dt.datetime):
        raise TypeError("today must be a datetime.date (not datetime)")
    seen = set()
    for idx, acc in enumerate(accounts):
        if not isinstance(acc, dict):
            raise ValueError(f"record at index {idx} is not a mapping")
        acc_id = acc.get("id")
        if acc_id is None:
            raise ValueError(f"record at index {idx} has no id")
        try:
            dup = acc_id in seen
        except TypeError:
            raise ValueError(f"record at index {idx} has an unhashable id")
        if dup:
            raise ValueError(f"duplicate account id {acc_id}")
        seen.add(acc_id)


def _evaluate(acc, today):
    """Return (action_dict, sort_key) or None. sort_key only used for deletes."""
    acc_id = acc["id"]
    if not _is_eligible(acc):
        return None
    if acc.get("litigation_hold") is not False:
        return None
    if _is_staff(acc.get("email")):
        return None

    last_seen = _date_or_none(acc.get("last_seen_at"), acc_id, "last_seen_at")
    closed_at = _date_or_none(acc.get("closed_at"), acc_id, "closed_at")

    candidates = []
    try:
        if last_seen is not None:
            candidates.append(last_seen + timedelta(days=INACTIVITY_DAYS))
        if closed_at is not None:
            candidates.append(closed_at + timedelta(days=CLOSED_GRACE_DAYS))
    except OverflowError:
        log.warning("account %s: date out of range", acc_id)
        return None
    if not candidates:
        return None
    due = min(candidates)

    if due <= today:
        unpaid = _has_unpaid(acc.get("unpaid_invoices"))
        if unpaid is None:
            return None
        kind = "anonymise" if unpaid else "delete"
        approver = APPROVER_NAME
    elif due <= today + timedelta(days=WARN_WINDOW_DAYS):
        if closed_at is not None and acc.get("closed_by") == "member":
            return None
        kind = "warn"
        approver = None
    else:
        return None

    action = {
        "account_id": acc_id,
        "action": kind,
        "due": due.isoformat(),
        "approved_by": approver,
    }
    key = (0 if closed_at is not None else 1, due, acc_id)
    return action, key


def plan_purge(accounts, today):
    accounts = list(accounts)
    _validate(accounts, today)

    others = []
    deletes = []
    for acc in accounts:
        try:
            res = _evaluate(acc, today)
        except Exception as exc:  # one bad record must not abort the run
            log.warning("account %s: skipped (%s)", acc.get("id"), type(exc).__name__)
            continue
        if res is None:
            continue
        action, key = res
        if action["action"] == "delete":
            deletes.append((key, action))
        else:
            others.append(action)

    deletes.sort(key=lambda t: t[0])
    kept = [a for _, a in deletes[:MAX_DELETES_PER_RUN]]
    result = others + kept
    result.sort(key=lambda a: a["account_id"])
    return result


# ----------------------------- tests -----------------------------

TODAY = date(2026, 10, 13)


def _acc(id, **kw):
    base = {"id": id, "email": f"{id}@example.com", "status": "active",
            "last_seen_at": None, "last_login": None, "closed_at": None,
            "closed_by": None, "unpaid_invoices": 0, "litigation_hold": False}
    base.update(kw)
    return base


class PurgeTests(unittest.TestCase):
    def one(self, **kw):
        return plan_purge([_acc("a", **kw)], TODAY)

    def test_inactivity_boundaries(self):
        r = self.one(last_seen_at=date(2024, 10, 13))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", "2026-10-13"))
        self.assertEqual(r[0]["approved_by"], APPROVER_NAME)
        r = self.one(last_seen_at=date(2024, 10, 12))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", "2026-10-12"))
        r = self.one(last_seen_at=date(2024, 10, 27))
        self.assertEqual((r[0]["action"], r[0]["due"], r[0]["approved_by"]),
                         ("warn", "2026-10-27", None))
        self.assertEqual(self.one(last_seen_at=date(2024, 10, 28)), [])

    def test_last_login_ignored(self):
        self.assertEqual(self.one(last_login=date(2000, 1, 1),
                                  last_seen_at=date(2026, 10, 1)), [])
        r = self.one(last_login=date(2026, 10, 1), last_seen_at=date(2024, 1, 1))
        self.assertEqual(r[0]["action"], "delete")

    def test_closed(self):
        r = self.one(closed_at=date(2026, 9, 13), closed_by="member")
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(self.one(closed_at=date(2026, 9, 20), closed_by="member"), [])
        r = self.one(closed_at=date(2026, 9, 20), closed_by="staff")
        self.assertEqual((r[0]["action"], r[0]["due"]), ("warn", "2026-10-20"))

    def test_earlier_due_wins(self):
        r = self.one(last_seen_at=date(2024, 10, 1), closed_at=date(2026, 10, 10))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", "2026-10-01"))

    def test_unpaid(self):
        r = self.one(last_seen_at=date(2024, 1, 1), unpaid_invoices=2)
        self.assertEqual(r[0]["action"], "anonymise")
        r = self.one(last_seen_at=date(2024, 1, 1), unpaid_invoices=["x"])
        self.assertEqual(r[0]["action"], "anonymise")
        r = self.one(last_seen_at=date(2024, 1, 1), unpaid_invoices=[])
        self.assertEqual(r[0]["action"], "delete")
        r = self.one(last_seen_at=date(2024, 10, 20), unpaid_invoices=1)
        self.assertEqual(r[0]["action"], "warn")
        self.assertEqual(self.one(last_seen_at=date(2024, 1, 1), unpaid_invoices=None), [])
        r = self.one(last_seen_at=date(2024, 10, 20), unpaid_invoices=None)
        self.assertEqual(r[0]["action"], "warn")

    def test_hold_and_staff(self):
        old = date(2024, 1, 1)
        self.assertEqual(self.one(last_seen_at=old, litigation_hold=True), [])
        self.assertEqual(self.one(last_seen_at=old, litigation_hold=None), [])
        self.assertEqual(plan_purge([{"id": "a", "email": "x@y.no", "last_seen_at": old,
                                      "unpaid_invoices": 0}], TODAY), [])
        self.assertEqual(self.one(last_seen_at=old, email=" Bob@Tidewater-Klatring.NO "), [])
        self.assertEqual(len(self.one(last_seen_at=old, email="b@evil-tidewater-klatring.no.com")), 1)
        self.assertEqual(len(self.one(last_seen_at=old, email="btidewater-klatring.no")), 1)
        self.assertEqual(len(self.one(last_seen_at=old, email=None)), 1)
        self.assertEqual(len(self.one(last_seen_at=old, email="")), 1)

    def test_cap(self):
        accs = []
        for k in range(60):
            accs.append(_acc(f"c{k:03d}", closed_at=TODAY - timedelta(days=31 + k)))
        for k in range(190):
            accs.append(_acc(f"i{k:03d}",
                             last_seen_at=TODAY - timedelta(days=INACTIVITY_DAYS + 1 + k)))
        accs.append(_acc("w1", last_seen_at=date(2024, 10, 20)))
        accs.append(_acc("an1", last_seen_at=date(2020, 1, 1), unpaid_invoices=3))
        res = plan_purge(accs, TODAY)
        dels = {a["account_id"] for a in res if a["action"] == "delete"}
        self.assertEqual(len(dels), 200)
        self.assertTrue(all(f"c{k:03d}" in dels for k in range(60)))
        self.assertTrue(all(f"i{k:03d}" in dels for k in range(50, 190)))
        self.assertFalse(any(f"i{k:03d}" in dels for k in range(50)))
        acts = {a["account_id"]: a["action"] for a in res}
        self.assertEqual(acts["w1"], "warn")
        self.assertEqual(acts["an1"], "anonymise")
        ids = [a["account_id"] for a in res]
        self.assertEqual(ids, sorted(ids))

    def test_output_shape_and_purity(self):
        import copy
        accs = [_acc("a", last_seen_at=date(2024, 1, 1), email="secret@x.com"),
                _acc("b", last_seen_at=date(2024, 10, 20), email="secret2@x.com")]
        before = copy.deepcopy(accs)
        res = plan_purge(accs, TODAY)
        self.assertEqual(accs, before)
        self.assertEqual(len(res), 2)
        for a in res:
            self.assertEqual(set(a), {"account_id", "action", "due", "approved_by"})
        self.assertNotIn("secret", json.dumps(res))

    def test_misc(self):
        self.assertEqual(plan_purge([], TODAY), [])
        r = self.one(last_seen_at=date(2024, 1, 1), tenant="zzz", junk=object())
        self.assertEqual(r[0]["action"], "delete")
        self.assertNotIn("tenant", r[0])

    def test_malformed(self):
        self.assertEqual(self.one(last_seen_at="2024-01-01"), [])
        self.assertEqual(self.one(last_seen_at=_dt.datetime(2024, 1, 1)), [])
        r = self.one(last_seen_at=date(2024, 1, 1), closed_at="bad")
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(self.one(), [])
        # bad record does not abort others
        res = plan_purge([_acc("a", last_seen_at=5), _acc("b", last_seen_at=date(2024, 1, 1))], TODAY)
        self.assertEqual([a["account_id"] for a in res], ["b"])

    def test_validation(self):
        with self.assertRaises(ValueError):
            plan_purge([{"email": "e@x.com"}], TODAY)
        with self.assertRaises(ValueError):
            plan_purge([_acc(None, email="e@x.com")], TODAY)
        with self.assertRaises(ValueError) as cm:
            plan_purge([_acc("a", email="e@x.com"), _acc("a", email="e@x.com")], TODAY)
        self.assertNotIn("e@x.com", str(cm.exception))
        for bad in ("2026-10-13", None, _dt.datetime(2026, 10, 13)):
            with self.assertRaises(TypeError):
                plan_purge([], bad)


if __name__ == "__main__":
    unittest.main()