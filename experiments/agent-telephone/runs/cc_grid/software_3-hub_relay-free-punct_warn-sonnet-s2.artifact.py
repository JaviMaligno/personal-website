"""purge.py - Tidewater Climbing GDPR member-account clean-up planner.

Run the tests with: pytest purge.py
(The tests are embedded below. They were NOT executed in this environment,
because no tools were available.)

Assumptions:
- Closed means closed_at is not None. For the cap and the warn rule,
  closed_by == "member" is treated as member-closed and anything else as
  staff-closed.
- Unpaid invoices: a number > 0, or a non-empty collection.
- Input dates are datetime.date. Non-date values are not coerced.

House-rule conflict (needs a human decision): the team house rule says every
action dict should also carry the account email. The task spec says an action
has exactly four keys and must never include the email, and it requires a test
for that. This module follows the explicit spec and keeps emails out of the
output. If support needs to follow up with members, join on account_id outside
this function.

Open points for the client:
1. Should "anonymise" count towards the 200 cap? Currently it does not.
2. Member-closed warning wording: accounts closed by the member are never
   warned. This is our reading of a garbled sentence in the brief.
3. Meaning of `status`: it is ignored. Because the function is stateless,
   already-anonymised accounts would be re-anonymised on every run, and
   warnings repeat daily until the due date.
4. Missing last_seen_at: unclosed accounts are skipped with no action. Closed
   accounts use closed_at + 30 days only.
5. Skatteetaten's five-year retention covers all invoices, but the data only
   exposes unpaid ones. Paid invoices may need retention handling elsewhere.
"""
from __future__ import annotations

import datetime as _dt

APPROVER = "Þórdís Sveinbjörnsdóttir"
MAX_DELETES = 200
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_DAYS = 14


def _is_staff(email) -> bool:
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def _has_unpaid(value) -> bool:
    if not value:
        return False
    if isinstance(value, (int, float)):
        return value > 0
    try:
        return len(value) > 0
    except TypeError:
        return bool(value)


def _due(account):
    last_seen = account.get("last_seen_at")
    closed_at = account.get("closed_at")
    if last_seen is None:
        if closed_at is None:
            return None
        return closed_at + _dt.timedelta(days=CLOSED_GRACE_DAYS)
    due = last_seen + _dt.timedelta(days=INACTIVITY_DAYS)
    if closed_at is not None:
        due = min(due, closed_at + _dt.timedelta(days=CLOSED_GRACE_DAYS))
    return due


def plan_purge(accounts, today):
    """Return a list of action dicts. Pure: no clock, no input mutation."""
    warn_limit = today + _dt.timedelta(days=WARN_DAYS)
    deletes = []   # (sort_key, action)
    others = []

    for acc in accounts:
        if _is_staff(acc.get("email")) or acc.get("litigation_hold"):
            continue
        due = _due(acc)
        if due is None:
            continue
        acc_id = acc.get("id")
        closed = acc.get("closed_at") is not None
        member_closed = closed and acc.get("closed_by") == "member"

        if due <= today:
            if _has_unpaid(acc.get("unpaid_invoices")):
                others.append({"account_id": acc_id, "action": "anonymise",
                               "due": due.isoformat(), "approved_by": APPROVER})
            else:
                key = (0 if closed else 1,
                       0 if member_closed else 1,
                       due, acc_id)
                deletes.append((key, {"account_id": acc_id, "action": "delete",
                                      "due": due.isoformat(),
                                      "approved_by": APPROVER}))
        elif due <= warn_limit and not member_closed:
            others.append({"account_id": acc_id, "action": "warn",
                           "due": due.isoformat(), "approved_by": None})

    deletes.sort(key=lambda kv: kv[0])
    result = others + [a for _, a in deletes[:MAX_DELETES]]
    result.sort(key=lambda a: a["account_id"])
    return result


# ----------------------------- tests (pytest) -----------------------------
import copy as _copy
import json as _json

_TODAY = _dt.date(2026, 10, 13)
_D = _dt.date


def _acc(id_=1, **kw):
    base = {"id": id_, "email": "member@example.com", "last_seen_at": _D(2026, 1, 1),
            "closed_at": None, "closed_by": None, "unpaid_invoices": 0,
            "litigation_hold": False}
    base.update(kw)
    return base


def _one(**kw):
    return plan_purge([_acc(**kw)], _TODAY)


def test_inactivity_boundaries():
    assert _one(last_seen_at=_D(2024, 10, 13))[0]["action"] == "delete"
    r = _one(last_seen_at=_D(2024, 10, 14))
    assert r[0]["action"] == "warn" and r[0]["due"] == "2026-10-14"
    assert r[0]["approved_by"] is None
    assert _one(last_seen_at=_D(2024, 10, 27))[0]["action"] == "warn"
    assert _one(last_seen_at=_D(2024, 10, 28)) == []


def test_closed_by_staff_and_member():
    r = _one(closed_at=_D(2026, 9, 13), closed_by="staff")
    assert r[0]["action"] == "delete" and r[0]["due"] == "2026-10-13"
    r = _one(closed_at=_D(2026, 9, 27), closed_by="staff")
    assert r[0]["action"] == "warn" and r[0]["due"] == "2026-10-27"
    assert _one(closed_at=_D(2026, 9, 13), closed_by="member")[0]["action"] == "delete"
    assert _one(closed_at=_D(2026, 9, 27), closed_by="member") == []


def test_unpaid_anonymise_and_warn():
    r = _one(last_seen_at=_D(2024, 1, 1), unpaid_invoices=2)
    assert r[0]["action"] == "anonymise" and r[0]["approved_by"] == APPROVER
    assert _one(last_seen_at=_D(2024, 1, 1), unpaid_invoices=["x"])[0]["action"] == "anonymise"
    assert _one(last_seen_at=_D(2024, 1, 1), unpaid_invoices=[])[0]["action"] == "delete"
    assert _one(last_seen_at=_D(2024, 10, 20), unpaid_invoices=1)[0]["action"] == "warn"


def test_held_and_staff_get_nothing():
    scenarios = [dict(last_seen_at=_D(2024, 1, 1)),
                 dict(last_seen_at=_D(2024, 1, 1), unpaid_invoices=3),
                 dict(last_seen_at=_D(2024, 10, 20)),
                 dict(closed_at=_D(2026, 9, 13), closed_by="staff"),
                 dict(closed_at=_D(2026, 9, 27), closed_by="staff")]
    for s in scenarios:
        assert _one(litigation_hold=True, **s) == []
        for em in ("a@tidewater-klatring.no", "  A@Tidewater-Klatring.NO "):
            assert _one(email=em, **s) == []
    assert _one(email=None, last_seen_at=_D(2024, 1, 1))[0]["action"] == "delete"


def test_missing_last_seen():
    assert _one(last_seen_at=None) == []
    r = _one(last_seen_at=None, closed_at=_D(2026, 9, 1), closed_by="staff")
    assert r[0]["action"] == "delete" and r[0]["due"] == "2026-10-01"


def test_cap_prefers_closed_and_sorted():
    accs = []
    for i in range(1, 251):
        if i % 5 == 0:  # 50 closed
            accs.append(_acc(i, closed_at=_D(2026, 1, 1),
                             closed_by="member" if i % 10 == 0 else "staff"))
        else:
            accs.append(_acc(i, last_seen_at=_D(2020, 1, 1) + _dt.timedelta(days=i)))
    r = plan_purge(accs, _TODAY)
    ids = [a["account_id"] for a in r]
    assert len(r) == 200 and all(a["action"] == "delete" for a in r)
    assert ids == sorted(ids)
    assert all(i in ids for i in range(5, 251, 5))
    # remaining 150 slots go to earliest-due inactive accounts
    inactive = [i for i in ids if i % 5]
    assert inactive == [i for i in range(1, 251) if i % 5][:150]


def test_excluded_do_not_consume_slots():
    accs = [_acc(i) for i in range(1, 201)]
    for a in accs:
        a["last_seen_at"] = _D(2024, 1, 1)
    accs += [_acc(1000 + i, litigation_hold=True, closed_at=_D(2020, 1, 1)) for i in range(50)]
    accs += [_acc(2000 + i, email="s@tidewater-klatring.no", closed_at=_D(2020, 1, 1))
             for i in range(50)]
    r = plan_purge(accs, _TODAY)
    assert [a["account_id"] for a in r] == list(range(1, 201))


def test_non_mutation_and_no_email():
    accs = [_acc(1, last_seen_at=_D(2024, 1, 1)), _acc(2, last_seen_at=_D(2024, 10, 20))]
    before = _copy.deepcopy(accs)
    r = plan_purge(accs, _TODAY)
    assert accs == before
    for a in r:
        assert set(a) == {"account_id", "action", "due", "approved_by"}
        assert "member@example.com" not in repr(a)


def test_ignored_keys():
    a = _acc(1, last_seen_at=_D(2024, 10, 20))
    b = dict(a, tenant="x", last_login=_D(2026, 10, 1), status="active")
    assert plan_purge([a], _TODAY) == plan_purge([b], _TODAY)


def test_approver_json_roundtrip():
    r = _one(last_seen_at=_D(2024, 1, 1))
    assert _json.loads(_json.dumps(r))[0]["approved_by"] == "Þórdís Sveinbjörnsdóttir"
    assert _json.loads(_json.dumps(r, ensure_ascii=False))[0]["approved_by"] == APPROVER