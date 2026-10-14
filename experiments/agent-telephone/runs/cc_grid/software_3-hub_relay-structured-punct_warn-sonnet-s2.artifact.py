"""Tidewater Climbing GDPR member-account purge planner.

Tests are embedded below and run with: pytest purge.py
(I could not execute them in this session, so no test results are reported.)

HOUSE RULE VS SPEC: the house rule says every action dict also carries the
account's `email`. This conflicts with R1/R9 (exactly four keys, never email).
I followed the house rule, so each action has five keys (the four from R1 plus
`email`). Please confirm with the client. If R1/R9 should win, delete the
"email" entry in _act and adjust test_output_shape_and_email.
Error messages never contain email.

Open points for the client:
- Cap applies to delete only; anonymise is uncapped (switch: COUNT_ANONYMISE_TOWARD_CAP).
- Warnings repeat on every run inside the 14-day window.
- litigation_hold of None (or anything not explicitly False) blocks all actions.
- Accounts with last_seen_at None and not closed are never purged.
- Sorting uses native id ordering (string ids sort lexicographically).
- Already-processed accounts must be filtered out by the caller.
- Paid-invoice retention (5 years) is not protected by R6, only unpaid invoices.
"""
import datetime as _dt
import json
import unicodedata
from datetime import date, timedelta

MAX_DELETIONS = 200
# Set True to make anonymise actions count toward MAX_DELETIONS (one-line switch).
COUNT_ANONYMISE_TOWARD_CAP = False
APPROVER = unicodedata.normalize("NFC", "Þórdís Sveinbjörnsdóttir")
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_DAYS = 14
_REQUIRED = ("id", "email", "status", "last_seen_at", "last_login", "closed_at",
             "closed_by", "unpaid_invoices", "litigation_hold")


def _is_date(v):
    return isinstance(v, date) and not isinstance(v, _dt.datetime)


def _validate(accounts):
    seen = set()
    for a in accounts:
        if "id" not in a:
            raise ValueError("account without 'id' field")
        aid = a["id"]
        for k in _REQUIRED:
            if k not in a:
                raise ValueError(f"account {aid!r}: missing required key {k!r}")
        for k in ("last_seen_at", "closed_at"):
            if a[k] is not None and not _is_date(a[k]):
                raise TypeError(f"account {aid!r}: {k} must be datetime.date or None")
        if aid in seen:
            raise ValueError(f"duplicate account id {aid!r}")
        seen.add(aid)


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def _due(a):
    ls, ca = a["last_seen_at"], a["closed_at"]
    due = ls + timedelta(days=INACTIVITY_DAYS) if ls is not None else None
    if ca is not None:
        c = ca + timedelta(days=CLOSED_GRACE_DAYS)
        due = c if due is None else min(due, c)
    return due


def _act(a, action, due, approver):
    return {"account_id": a["id"], "action": action, "due": due.isoformat(),
            "approved_by": approver, "email": a["email"]}


def plan_purge(accounts, today):
    if isinstance(today, _dt.datetime) or not isinstance(today, date):
        raise TypeError("today must be a datetime.date (not datetime)")
    accounts = list(accounts)
    _validate(accounts)
    pool, others = [], []  # pool: (sortkey, action) subject to cap
    uncapped = []
    for a in accounts:
        if a["litigation_hold"] is not False or _is_staff(a["email"]):
            continue
        due = _due(a)
        if due is None:
            continue
        if due <= today:
            verb = "anonymise" if a["unpaid_invoices"] else "delete"
            act = _act(a, verb, due, APPROVER)
            closed = a["closed_at"] is not None
            if verb == "delete" or COUNT_ANONYMISE_TOWARD_CAP:
                pool.append(((0 if closed else 1, due, a["id"]), act))
            else:
                uncapped.append(act)
        elif due <= today + timedelta(days=WARN_DAYS) and a["closed_by"] != "member":
            others.append(_act(a, "warn", due, None))
    pool.sort(key=lambda p: p[0])
    kept = [act for _, act in pool[:MAX_DELETIONS]]
    result = kept + uncapped + others
    result.sort(key=lambda r: r["account_id"])
    return result


# ----------------------------- tests -----------------------------
TODAY = date(2026, 10, 13)


def mk(i, **kw):
    a = {"id": i, "email": f"m{i}@example.com", "status": "active",
         "last_seen_at": date(2026, 1, 1), "last_login": None, "closed_at": None,
         "closed_by": None, "unpaid_invoices": 0, "litigation_hold": False}
    a.update(kw)
    return a


def inactive_due(i, offset, **kw):
    return mk(i, last_seen_at=TODAY + timedelta(days=offset - INACTIVITY_DAYS), **kw)


def closed(i, days_ago, **kw):
    return mk(i, closed_at=TODAY - timedelta(days=days_ago), **kw)


def acts(res):
    return {r["account_id"]: r["action"] for r in res}


def test_empty_and_today_type():
    import pytest
    assert plan_purge([], TODAY) == []
    with pytest.raises(TypeError):
        plan_purge([], _dt.datetime(2026, 10, 13))


def test_approver_nfc():
    assert APPROVER == unicodedata.normalize("NFC", APPROVER)
    assert APPROVER == "\u00deórd\u00eds Sveinbj\u00f6rnsd\u00f3ttir".replace("\u00eds", "\u00eds")


def test_boundaries():
    res = plan_purge([inactive_due(i, o) for i, o in enumerate([-5, 0, 1, 14, 15])], TODAY)
    assert acts(res) == {0: "delete", 1: "delete", 2: "warn", 3: "warn"}
    r = {x["account_id"]: x for x in res}
    assert r[0]["due"] == (TODAY - timedelta(days=5)).isoformat()
    assert r[0]["approved_by"] == APPROVER and r[2]["approved_by"] is None


def test_closed_due_and_min():
    res = plan_purge([closed(1, 30), closed(2, 29), mk(3, last_seen_at=None),
                      closed(4, 40, last_seen_at=None)], TODAY)
    assert acts(res) == {1: "delete", 2: "warn", 4: "delete"}


def test_warn_rules():
    accts = [closed(1, 20, closed_by="member"), closed(2, 20, closed_by="staff"),
             closed(3, 20, closed_by=None), inactive_due(4, 5, unpaid_invoices=2)]
    assert acts(plan_purge(accts, TODAY)) == {2: "warn", 3: "warn", 4: "warn"}


def test_unpaid_anonymise():
    res = plan_purge([inactive_due(1, 0, unpaid_invoices=1)], TODAY)
    assert acts(res) == {1: "anonymise"} and res[0]["approved_by"] == APPROVER


def test_hold_and_staff():
    accts = [inactive_due(1, 0, litigation_hold=True), inactive_due(2, 0, litigation_hold=None),
             inactive_due(3, 5, litigation_hold="no"), inactive_due(4, 0, litigation_hold=0),
             inactive_due(5, 0, email="  Bob@Tidewater-Klatring.NO "),
             inactive_due(6, 0, email=None), inactive_due(7, 0, email="")]
    assert acts(plan_purge(accts, TODAY)) == {6: "delete", 7: "delete"}


def test_cap_sizes():
    for n, exp in ((199, 199), (200, 200), (201, 200)):
        res = plan_purge([inactive_due(i, -1) for i in range(n)], TODAY)
        assert len(res) == exp


def test_cap_priority_closed_first():
    accts = [closed(i, 31 + i) for i in range(60)]
    accts += [inactive_due(1000 + i, -(100 + i)) for i in range(190)]
    res = plan_purge(accts, TODAY)
    ids = {r["account_id"] for r in res}
    assert len(res) == 200 and set(range(60)) <= ids
    assert ids - set(range(60)) == {1000 + i for i in range(140)}


def test_cap_300_closed_earliest_first_and_tiebreak():
    res = plan_purge([closed(i, 31 + i) for i in range(300)], TODAY)
    assert {r["account_id"] for r in res} == set(range(100, 300))
    res = plan_purge([closed(i, 40) for i in range(250)], TODAY)
    assert {r["account_id"] for r in res} == set(range(200))


def test_cap_excludes_held_staff_anonymise_warn():
    accts = [inactive_due(i, -1, litigation_hold=True) for i in range(50)]
    accts += [inactive_due(100 + i, -1) for i in range(200)]
    accts += [inactive_due(400 + i, -1, unpaid_invoices=1) for i in range(30)]
    accts += [inactive_due(600 + i, 3) for i in range(20)]
    c = {}
    for r in plan_purge(accts, TODAY):
        c[r["action"]] = c.get(r["action"], 0) + 1
    assert c == {"delete": 200, "anonymise": 30, "warn": 20}


def test_output_shape_and_email():
    res = plan_purge([inactive_due(1, 0), inactive_due(2, 3)], TODAY)
    assert all(set(r) == {"account_id", "action", "due", "approved_by", "email"} for r in res)
    json.dumps(res)


def test_errors_do_not_leak_email():
    import pytest
    bad = mk(7, email="secret@x.com")
    del bad["status"]
    with pytest.raises(ValueError) as e:
        plan_purge([bad], TODAY)
    assert "7" in str(e.value) and "secret" not in str(e.value)
    with pytest.raises(TypeError) as e:
        plan_purge([mk(8, email="secret@x.com", last_seen_at=_dt.datetime(2020, 1, 1))], TODAY)
    assert "secret" not in str(e.value)
    with pytest.raises(TypeError):
        plan_purge([mk(9, closed_at="2020-01-01")], TODAY)
    with pytest.raises(ValueError) as e:
        plan_purge([mk(1, email="secret@x.com"), mk(1)], TODAY)
    assert "secret" not in str(e.value)


def test_order_independence_nonmutation_last_login():
    import copy
    import random
    accts = [inactive_due(i, o, tenant="t", extra=1, last_login=TODAY)
             for i, o in enumerate([-3, 0, 5, 20, -1, 14])]
    snap = copy.deepcopy(accts)
    base = plan_purge(accts, TODAY)
    assert accts == snap
    sh = accts[:]
    random.Random(1).shuffle(sh)
    assert plan_purge(sh, TODAY) == base
    assert [r["account_id"] for r in base] == sorted(r["account_id"] for r in base)
    assert plan_purge([mk(1, last_seen_at=None, last_login=TODAY - timedelta(days=9999))], TODAY) == []
    assert plan_purge([inactive_due(1, 0, last_login=TODAY)], TODAY)[0]["action"] == "delete"


def test_one_action_per_account():
    res = plan_purge([closed(1, 31, unpaid_invoices=1), inactive_due(2, 0)], TODAY)
    assert len({r["account_id"] for r in res}) == len(res)