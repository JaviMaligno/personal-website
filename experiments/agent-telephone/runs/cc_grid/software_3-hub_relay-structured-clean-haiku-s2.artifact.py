"""GDPR clean-up planner for Tidewater Climbing.

Single public entry point: plan_purge(accounts, today).

Assumptions (not yet confirmed by the client):
- A staff-closed account (closed_by == "staff") is warned under R8 as written.
- The status field is ignored. It must be present but is not used.
- closed_by is ignored when closed_at is None.
- Daily warnings repeat (one per run while in the window). No dedupe.
- Anonymise due is the effective due date that triggered it.
- Already-processed accounts are removed by the caller.

Interpretations:
- The R13 cap of 200 counts only accounts that would receive a delete action
  (those without unpaid_invoices). Anonymise actions are not capped.
- Duplicate account ids raise ValueError.
"""

import datetime as _dt

_INACTIVE_DAYS = 730
_CLOSED_DAYS = 30
_WARN_DAYS = 14
_DELETE_CAP = 200
_APPROVER = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"
_STAFF_DOMAIN = "@tidewater-klatring.no"
_REQUIRED = (
    "id", "email", "status", "last_seen_at", "last_login",
    "closed_at", "closed_by", "unpaid_invoices", "litigation_hold",
)


def _is_date(v):
    return isinstance(v, _dt.date) and not isinstance(v, _dt.datetime)


def _id_key(aid):
    return (isinstance(aid, str), aid)


def _validate(acc, idx):
    if not isinstance(acc, dict):
        raise ValueError(f"account at index {idx}: not a dict")
    for f in _REQUIRED:
        if f not in acc:
            raise ValueError(f"account at index {idx}: field '{f}' is missing or malformed")
    aid = acc["id"]
    if not isinstance(aid, (str, int)) or isinstance(aid, bool):
        raise ValueError(f"account at index {idx}: field 'id' is missing or malformed")

    def bad(field):
        raise ValueError(f"account {aid}: field '{field}' is missing or malformed")

    if not isinstance(acc["email"], str):
        bad("email")
    for f in ("last_seen_at", "last_login", "closed_at"):
        if acc[f] is not None and not _is_date(acc[f]):
            bad(f)
    for f in ("unpaid_invoices", "litigation_hold"):
        if not isinstance(acc[f], bool):
            bad(f)
    if acc["closed_at"] is not None and acc["closed_by"] not in ("member", "staff"):
        bad("closed_by")


def _effective_due(acc):
    dues = []
    try:
        if acc["last_seen_at"] is not None:
            dues.append(acc["last_seen_at"] + _dt.timedelta(days=_INACTIVE_DAYS))
        if acc["closed_at"] is not None:
            dues.append(acc["closed_at"] + _dt.timedelta(days=_CLOSED_DAYS))
    except OverflowError:
        raise ValueError(f"account {acc['id']}: date arithmetic out of range")
    return min(dues) if dues else None


def _action(aid, action, due, approver):
    return {
        "account_id": aid,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approver,
    }


def plan_purge(accounts, today):
    if not isinstance(accounts, list):
        raise TypeError("accounts must be a list")
    if not _is_date(today):
        raise TypeError("today must be a datetime.date")
    try:
        warn_limit = today + _dt.timedelta(days=_WARN_DAYS)
    except OverflowError:
        raise ValueError("today is out of range")

    seen = set()
    actions = []
    deletes = []
    for idx, acc in enumerate(accounts):
        _validate(acc, idx)
        aid = acc["id"]
        if aid in seen:
            raise ValueError(f"duplicate account id {aid}")
        seen.add(aid)
        if acc["litigation_hold"]:
            continue
        if acc["email"].lower().endswith(_STAFF_DOMAIN):
            continue
        due = _effective_due(acc)
        if due is None:
            continue
        if due <= today:
            if acc["unpaid_invoices"]:
                actions.append(_action(aid, "anonymise", due, _APPROVER))
            else:
                group = 0 if acc["closed_at"] is not None else 1
                deletes.append((group, due, _id_key(aid), aid))
        elif due <= warn_limit:
            member_closed = acc["closed_at"] is not None and acc["closed_by"] == "member"
            if not member_closed:
                actions.append(_action(aid, "warn", due, None))

    deletes.sort(key=lambda r: (r[0], r[1], r[2]))
    for _group, due, _key, aid in deletes[:_DELETE_CAP]:
        actions.append(_action(aid, "delete", due, _APPROVER))

    actions.sort(key=lambda a: _id_key(a["account_id"]))
    return actions


if __name__ == "__main__":
    import copy
    import unittest

    TODAY = _dt.date(2026, 10, 13)
    APPROVER = "Þórdís Sveinbjörnsdóttir"

    def acc(i, **kw):
        a = {
            "id": i,
            "email": f"m{i}@example.com",
            "status": "active",
            "last_seen_at": TODAY,
            "last_login": None,
            "closed_at": None,
            "closed_by": "member",
            "unpaid_invoices": False,
            "litigation_hold": False,
        }
        a.update(kw)
        return a

    class PurgeTests(unittest.TestCase):
        def test_inactive_delete_with_approver(self):
            a = acc(1, last_seen_at=TODAY - _dt.timedelta(days=730))
            self.assertEqual(plan_purge([a], TODAY), [
                {"account_id": 1, "action": "delete",
                 "due": TODAY.isoformat(), "approved_by": APPROVER},
            ])

        def test_closed_30_days_delete(self):
            a = acc(2, closed_at=TODAY - _dt.timedelta(days=30), closed_by="staff")
            out = plan_purge([a], TODAY)
            self.assertEqual(out[0]["action"], "delete")

        def test_warn_window_and_member_exclusion(self):
            staff = acc(3, closed_at=TODAY - _dt.timedelta(days=20), closed_by="staff")
            member = acc(4, closed_at=TODAY - _dt.timedelta(days=20), closed_by="member")
            out = plan_purge([staff, member], TODAY)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0]["account_id"], 3)
            self.assertEqual(out[0]["action"], "warn")
            self.assertIsNone(out[0]["approved_by"])

        def test_member_closed_unpaid_no_warn_then_anonymise(self):
            before = acc(5, closed_at=TODAY - _dt.timedelta(days=29),
                         closed_by="member", unpaid_invoices=True)
            self.assertEqual(plan_purge([before], TODAY), [])
            on_due = acc(5, closed_at=TODAY - _dt.timedelta(days=30),
                         closed_by="member", unpaid_invoices=True)
            out = plan_purge([on_due], TODAY)
            self.assertEqual(out[0]["action"], "anonymise")
            self.assertEqual(out[0]["approved_by"], APPROVER)

        def test_hold_and_staff_domain_excluded(self):
            old = TODAY - _dt.timedelta(days=800)
            held = acc(6, last_seen_at=old, litigation_hold=True)
            staff = acc(7, last_seen_at=old, email="X@TIDEWATER-KLATRING.NO")
            self.assertEqual(plan_purge([held, staff], TODAY), [])

        def test_cap_closed_first_and_deferred_dropped(self):
            accounts = []
            for n in range(100):
                accounts.append(acc(f"c{n:03d}",
                                    closed_at=TODAY - _dt.timedelta(days=30),
                                    closed_by="staff"))
            for n in range(150):
                accounts.append(acc(f"i{n:03d}",
                                    last_seen_at=TODAY - _dt.timedelta(days=730)))
            out = plan_purge(accounts, TODAY)
            deletes = {a["account_id"] for a in out if a["action"] == "delete"}
            self.assertEqual(len(deletes), 200)
            self.assertTrue(all(f"c{n:03d}" in deletes for n in range(100)))
            self.assertTrue(all(f"i{n:03d}" in deletes for n in range(100)))
            self.assertFalse(any(f"i{n:03d}" in deletes for n in range(100, 150)))

        def test_last_login_ignored(self):
            a = acc(8, last_seen_at=TODAY, last_login=_dt.date(2000, 1, 1))
            self.assertEqual(plan_purge([a], TODAY), [])

        def test_missing_field_names_field(self):
            a = acc(9)
            del a["email"]
            with self.assertRaisesRegex(ValueError, "'email'"):
                plan_purge([a], TODAY)

        def test_malformed_field_names_id_and_field(self):
            a = acc(10, last_seen_at="2026-01-01")
            with self.assertRaisesRegex(ValueError, "account 10.*'last_seen_at'"):
                plan_purge([a], TODAY)

        def test_no_mutation_and_deterministic(self):
            accounts = [acc(12, last_seen_at=TODAY - _dt.timedelta(days=730)),
                        acc(11, last_seen_at=TODAY - _dt.timedelta(days=725))]
            snapshot = copy.deepcopy(accounts)
            first = plan_purge(accounts, TODAY)
            self.assertEqual(accounts, snapshot)
            self.assertEqual(first, plan_purge(accounts, TODAY))
            self.assertEqual([a["account_id"] for a in first], [11, 12])

        def test_output_has_only_r3_keys(self):
            a = acc(13, last_seen_at=TODAY - _dt.timedelta(days=730))
            out = plan_purge([a], TODAY)
            self.assertEqual(set(out[0]), {"account_id", "action", "due", "approved_by"})

    unittest.main()
}