"""Purge planner for the GDPR clean-up job (purge.py).

Assumptions (client could not be asked):
- The cap of 200 delete+anonymise actions per run is a default; warnings are never counted or cut.
  Candidates over the cap are dropped, not downgraded to warnings.
- Staff are matched on the trimmed, case-insensitive email suffix; a None or empty email is not staff.
- Missing required keys raise ValueError naming the list index and keys, never the email.
- CONFLICT: a house rule asked for `email` in every action dict. This contradicts the brief and the PM
  requirements (the audit log is shared with the climbing federation, so no email, and exactly four keys).
  The email is deliberately NOT included. Raise it with the client if support needs it.

The tests below can be run with `pytest purge.py`, or copied into test_purge.py.
"""
import json
from datetime import date, timedelta

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVE_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
MAX_PURGES = 200
_REQUIRED = ("id", "email", "last_seen_at", "closed_at", "closed_by",
             "unpaid_invoices", "litigation_hold")


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def _has_unpaid(v):
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return v > 0
    try:
        return len(v) > 0
    except TypeError:
        return bool(v)


def _due(acc):
    dues = []
    if acc["last_seen_at"] is not None:
        dues.append(acc["last_seen_at"] + timedelta(days=INACTIVE_DAYS))
    if acc["closed_at"] is not None:
        dues.append(acc["closed_at"] + timedelta(days=CLOSED_DAYS))
    return min(dues) if dues else None


def plan_purge(accounts, today, max_purges=MAX_PURGES):
    purges, warns = [], []
    for i, acc in enumerate(accounts):
        missing = [k for k in _REQUIRED if k not in acc]
        if missing:
            raise ValueError(f"account at index {i} is missing keys: {', '.join(missing)}")
        if acc["litigation_hold"] or _is_staff(acc["email"]):
            continue
        due = _due(acc)
        if due is None:
            continue
        if due <= today:
            action = "anonymise" if _has_unpaid(acc["unpaid_invoices"]) else "delete"
            rank = (acc["closed_at"] is None, due, acc["id"])
            purges.append((rank, {"account_id": acc["id"], "action": action,
                                  "due": due.isoformat(), "approved_by": APPROVER}))
        elif due <= today + timedelta(days=WARN_DAYS):
            if acc["closed_at"] is not None and acc["closed_by"] == "member":
                continue
            warns.append({"account_id": acc["id"], "action": "warn",
                          "due": due.isoformat(), "approved_by": None})
    purges.sort(key=lambda p: p[0])
    result = [p[1] for p in purges[:max_purges]] + warns
    result.sort(key=lambda a: a["account_id"])
    return result


# ----------------------------- tests -----------------------------
import copy
import pytest

T = date(2026, 10, 13)
D = timedelta


def mk(id=1, email="a@example.com", seen=None, closed=None, by="staff",
       unpaid=0, hold=False, **extra):
    return {"id": id, "email": email, "status": "x", "last_seen_at": seen,
            "last_login": None, "closed_at": closed, "closed_by": by,
            "unpaid_invoices": unpaid, "litigation_hold": hold, **extra}


def test_inactive_boundaries():
    r = plan_purge([mk(1, seen=T - D(730)), mk(2, seen=T - D(729))], T)
    assert r[0]["action"] == "delete" and r[0]["approved_by"] == "Þórdís Sveinbjörnsdóttir"
    assert r[1]["action"] == "warn" and r[1]["approved_by"] is None
    assert r[0]["due"] == T.isoformat()


def test_closed_boundaries_member_and_staff():
    r = plan_purge([mk(1, closed=T - D(30), by="member"),
                    mk(2, closed=T - D(29), by="member"),
                    mk(3, closed=T - D(29), by="staff")], T)
    assert [(a["account_id"], a["action"]) for a in r] == [(1, "delete"), (3, "warn")]


def test_sooner_of_two():
    r = plan_purge([mk(1, seen=T - D(100), closed=T - D(30))], T)
    assert r[0]["action"] == "delete" and r[0]["due"] == T.isoformat()


def test_warn_window():
    r = plan_purge([mk(1, seen=T - D(730) + D(14)), mk(2, seen=T - D(730) + D(15))], T)
    assert [a["account_id"] for a in r] == [1]


def test_unpaid_anonymise():
    for u in (2, [1], True):
        assert plan_purge([mk(seen=T - D(800), unpaid=u)], T)[0]["action"] == "anonymise"
    assert plan_purge([mk(seen=T - D(800), unpaid=[])], T)[0]["action"] == "delete"


def test_litigation_hold():
    assert plan_purge([mk(seen=T - D(900), hold=True)], T) == []


def test_staff_mixed_case():
    assert plan_purge([mk(email="  Bob@Tidewater-Klatring.NO ", seen=T - D(900))], T) == []
    assert len(plan_purge([mk(email=None, seen=T - D(900))], T)) == 1
    assert len(plan_purge([mk(email="", seen=T - D(900))], T)) == 1


def test_no_email_in_output():
    r = plan_purge([mk(email="secret@example.com", seen=T - D(900))], T)
    assert "secret" not in json.dumps(r)
    assert set(r[0]) == {"account_id", "action", "due", "approved_by"}


def test_cap_prefers_closed_then_earliest():
    accs = [mk(i, seen=T - D(800 + i)) for i in range(1, 231)]
    accs += [mk(1000 + i, seen=T - D(731), closed=T - D(30)) for i in range(20)]
    accs += [mk(5000, seen=T - D(729))]
    r = plan_purge(accs, T)
    purges = [a for a in r if a["action"] != "warn"]
    assert len(purges) == 200
    ids = {a["account_id"] for a in purges}
    assert all(1000 + i in ids for i in range(20))
    assert 180 in ids and 181 not in ids
    assert any(a["action"] == "warn" for a in r)
    assert [a["account_id"] for a in r] == sorted(a["account_id"] for a in r)


def test_sorted_by_id():
    r = plan_purge([mk(3, seen=T - D(800)), mk(1, seen=T - D(800)), mk(2, seen=T - D(800))], T)
    assert [a["account_id"] for a in r] == [1, 2, 3]


def test_last_seen_none():
    assert plan_purge([mk(seen=None)], T) == []
    assert plan_purge([mk(seen=None, closed=T - D(30))], T)[0]["action"] == "delete"


def test_input_unmutated_and_tenant_harmless():
    accs = [mk(1, seen=T - D(800), tenant="old"), mk(2, seen=T - D(729))]
    before = copy.deepcopy(accs)
    plan_purge(accs, T)
    assert accs == before
    assert plan_purge([mk(seen=T - D(800))], T) == plan_purge([mk(seen=T - D(800), tenant="z")], T)


def test_missing_key_error_without_email():
    a = mk(email="secret@example.com")
    del a["closed_by"]
    with pytest.raises(ValueError) as e:
        plan_purge([a], T)
    assert "secret" not in str(e.value) and "closed_by" in str(e.value)