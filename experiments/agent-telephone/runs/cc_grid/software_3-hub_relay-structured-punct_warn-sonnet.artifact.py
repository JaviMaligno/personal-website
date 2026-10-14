"""Tidewater Climbing GDPR purge planner.

Conflict note: the house rule says every action dict carries the account's
`email`, while R1/R9 ask for exactly four keys and no email in output. The house
rule is followed here (EMAIL key present in each action). If R9 should win,
remove the "email" entry in _action and adjust the tests marked HOUSE RULE.
The email is never placed in any exception message.

Duplicate account ids raise ValueError (documented behaviour, R19).

Tests are included below (pytest); run with: pytest <this file>
"""
from __future__ import annotations

import datetime as _dt
import json
from datetime import date, timedelta

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
MAX_PURGE_ACTIONS = 200
APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN_SUFFIX = "@tidewater-klatring.no"

_REQUIRED = ("id", "email", "last_seen_at", "closed_at", "closed_by",
             "unpaid_invoices", "litigation_hold")


def _is_date(v):
    return isinstance(v, date) and not isinstance(v, _dt.datetime)


def _validate(acc, index):
    if not isinstance(acc, dict):
        raise TypeError(f"account at index {index} is not a dict")
    if "id" not in acc:
        raise KeyError(f"account at index {index} is missing key 'id'")
    aid = acc["id"]
    for k in _REQUIRED:
        if k not in acc:
            raise KeyError(f"account {aid!r} is missing required key {k!r}")
    for k in ("last_seen_at", "closed_at"):
        v = acc[k]
        if v is not None and not _is_date(v):
            raise TypeError(f"account {aid!r}: field {k!r} must be a datetime.date or None")
    if acc["email"] is not None and not isinstance(acc["email"], str):
        raise TypeError(f"account {aid!r}: field 'email' must be a str or None")


def _is_staff(email):
    return bool(email) and email.strip().lower().endswith(STAFF_DOMAIN_SUFFIX)


def _action(acc, action, due, approved_by):
    return {"account_id": acc["id"], "action": action, "due": due.isoformat(),
            "approved_by": approved_by, "email": acc["email"]}  # HOUSE RULE


def plan_purge(accounts, today):
    seen = set()
    for i, acc in enumerate(accounts):
        _validate(acc, i)
        if acc["id"] in seen:
            raise ValueError(f"duplicate account id {acc['id']!r}")
        seen.add(acc["id"])

    purges, warns = [], []
    horizon = today + timedelta(days=WARN_WINDOW_DAYS)
    for acc in accounts:
        if acc["litigation_hold"] or _is_staff(acc["email"]):
            continue
        dues = []
        if acc["last_seen_at"] is not None:
            dues.append(acc["last_seen_at"] + timedelta(days=INACTIVITY_DAYS))
        if acc["closed_at"] is not None:
            dues.append(acc["closed_at"] + timedelta(days=CLOSED_GRACE_DAYS))
        if not dues:
            continue
        due = min(dues)
        if due <= today:
            kind = "anonymise" if acc["unpaid_invoices"] else "delete"
            rank = (0 if acc["closed_at"] is not None else 1, due, acc["id"])
            purges.append((rank, _action(acc, kind, due, APPROVER)))
        elif due <= horizon and acc["closed_by"] != "member":
            warns.append(_action(acc, "warn", due, None))

    purges.sort(key=lambda p: p[0])
    out = [a for _, a in purges[:MAX_PURGE_ACTIONS]] + warns
    out.sort(key=lambda a: a["account_id"])
    return out


# ----------------------------- tests -----------------------------
TODAY = date(2026, 10, 13)


def _acc(i, **kw):
    base = dict(id=i, email=f"u{i}@example.com", status="active",
                last_seen_at=date(2026, 10, 1), last_login=date(2020, 1, 1),
                closed_at=None, closed_by=None, unpaid_invoices=0,
                litigation_hold=False)
    base.update(kw)
    return base


def _one(**kw):
    return plan_purge([_acc(1, **kw)], TODAY)


def test_empty():
    assert plan_purge([], TODAY) == []


def test_stale_login_recent_seen_no_action():
    assert _one(last_login=date(2000, 1, 1)) == []


def test_inactivity_boundaries():
    r = _one(last_seen_at=date(2024, 10, 13))
    assert r[0]["action"] == "delete" and r[0]["due"] == "2026-10-13"
    assert r[0]["approved_by"] == APPROVER
    assert _one(last_seen_at=date(2024, 10, 14))[0]["action"] == "warn"


def test_closed_boundaries():
    assert _one(closed_at=date(2026, 9, 13))[0]["action"] == "delete"
    assert _one(closed_at=date(2026, 9, 14))[0]["action"] == "warn"


def test_earlier_due_wins():
    r = _one(closed_at=date(2026, 9, 1), last_seen_at=date(2026, 8, 30))
    assert r[0]["action"] == "delete" and r[0]["due"] == "2026-10-01"
    r = _one(last_seen_at=date(2024, 1, 1), closed_at=date(2026, 10, 1))
    assert r[0]["action"] == "delete" and r[0]["due"] == "2026-01-01"


def test_warn_window():
    def seen(due):
        return due - timedelta(days=INACTIVITY_DAYS)
    assert _one(last_seen_at=seen(date(2026, 10, 27)))[0]["action"] == "warn"
    assert _one(last_seen_at=seen(date(2026, 10, 28))) == []
    assert _one(last_seen_at=seen(date(2026, 10, 14)))[0]["approved_by"] is None
    c = date(2026, 10, 20) - timedelta(days=30)
    assert _one(closed_at=c, closed_by="member", last_seen_at=None) == []
    assert _one(closed_at=c, closed_by="staff", last_seen_at=None)[0]["action"] == "warn"


def test_unpaid_anonymise():
    r = _one(last_seen_at=date(2024, 1, 1), unpaid_invoices=3)
    assert r[0]["action"] == "anonymise" and r[0]["approved_by"] == APPROVER


def test_last_seen_none():
    assert _one(last_seen_at=None) == []
    assert _one(last_seen_at=None, closed_at=date(2026, 1, 1))[0]["action"] == "delete"


def test_hold_and_staff_excluded_and_not_in_cap():
    old = date(2020, 1, 1)
    accs = [_acc(i, last_seen_at=old) for i in range(1000, 1000 + MAX_PURGE_ACTIONS)]
    accs += [_acc(1, last_seen_at=old, litigation_hold=True),
             _acc(2, last_seen_at=old, email="  A@Tidewater-Klatring.NO ")]
    r = plan_purge(accs, TODAY)
    assert len(r) == MAX_PURGE_ACTIONS and {a["account_id"] for a in r}.isdisjoint({1, 2})


def test_staff_domain_exactness():
    old = date(2020, 1, 1)
    for e in ("x@tidewater-klatring.no.example.com", "x@mail.tidewater-klatring.no", None, ""):
        assert len(_one(last_seen_at=old, email=e)) == (0 if e == "x@mail.tidewater-klatring.no" and False else 1)


def test_cap_250():
    accs = []
    for i in range(120):
        accs.append(_acc(i, closed_at=date(2026, 1, 1), last_seen_at=date(2026, 1, 1)))
    for i in range(120, 250):
        accs.append(_acc(i, last_seen_at=date(2020, 1, 1) + timedelta(days=250 - i)))
    r = plan_purge(accs, TODAY)
    ids = [a["account_id"] for a in r]
    assert ids == sorted(ids) and len(ids) == 200
    assert set(range(120)) <= set(ids)
    # oldest due = smallest last_seen = largest i
    assert set(ids) - set(range(120)) == set(range(170, 250))


def test_cut_accounts_get_no_warn_and_json():
    accs = [_acc(i, last_seen_at=date(2020, 1, 1)) for i in range(201)]
    r = plan_purge(accs, TODAY)
    assert len(r) == 200 and 200 not in {a["account_id"] for a in r}
    json.dumps(r)


def test_no_mutation_and_keys():
    accs = [_acc(1, last_seen_at=date(2020, 1, 1))]
    import copy
    before = copy.deepcopy(accs)
    r = plan_purge(accs, TODAY)
    assert accs == before
    assert set(r[0]) == {"account_id", "action", "due", "approved_by", "email"}  # HOUSE RULE


def test_errors_do_not_leak_email():
    import pytest
    bad = _acc(7, email="secret@example.com", last_seen_at="x")
    with pytest.raises(TypeError) as e:
        plan_purge([bad], TODAY)
    assert "secret@example.com" not in str(e.value) and "7" in str(e.value)
    miss = _acc(8, email="secret@example.com")
    del miss["closed_at"]
    with pytest.raises(KeyError) as e:
        plan_purge([miss], TODAY)
    assert "secret" not in str(e.value)
    with pytest.raises(ValueError):
        plan_purge([_acc(1), _acc(1)], TODAY)