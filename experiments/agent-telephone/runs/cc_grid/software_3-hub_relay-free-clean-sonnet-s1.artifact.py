"""Tidewater Climbing GDPR member-account purge planner.

NOTE: the house rule asks for an email on every action, but the task spec
requires exactly four keys and no email anywhere in output, logs or
exceptions. This module follows the spec; adding email is a one-line change
in _action() if the conflict is resolved the other way.
"""
from datetime import date, timedelta

DPO_APPROVER = "Þórdís Sveinbjörnsdóttir"
MAX_DELETES_PER_RUN = 200  # cap applies to "delete" actions only
STAFF_DOMAIN = "@tidewater-klatring.no"
PURGED_STATUSES = frozenset({"deleted", "anonymised", "anonymized"})
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14


def _due(a):
    cands = []
    closed = a.get("closed_at")
    seen = a.get("last_seen_at")
    if closed is not None:
        cands.append(closed + timedelta(days=CLOSED_GRACE_DAYS))
    if seen is not None:
        cands.append(seen + timedelta(days=INACTIVITY_DAYS))
    return min(cands) if cands else None


def _is_staff(a):
    email = a.get("email")
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def _skip(a):
    if a.get("litigation_hold") or _is_staff(a):
        return True
    status = a.get("status")
    return isinstance(status, str) and status.strip().lower() in PURGED_STATUSES


def _action(account_id, action, due, approver):
    return {"account_id": account_id, "action": action,
            "due": due.isoformat(), "approved_by": approver}


def plan_purge(accounts, today):
    deletes, others = [], []
    horizon = today + timedelta(days=WARN_WINDOW_DAYS)
    for a in accounts:
        if _skip(a):
            continue
        due = _due(a)
        if due is None:
            continue
        aid = a.get("id")
        if due <= today:
            if a.get("unpaid_invoices"):
                others.append(_action(aid, "anonymise", due, DPO_APPROVER))
            else:
                rank = 0 if a.get("closed_at") is not None else 1
                deletes.append(((rank, due, aid),
                                _action(aid, "delete", due, DPO_APPROVER)))
        elif due <= horizon and a.get("closed_by") != "member":
            others.append(_action(aid, "warn", due, None))
    deletes.sort(key=lambda t: t[0])
    kept = [act for _, act in deletes[:MAX_DELETES_PER_RUN]]
    return sorted(others + kept, key=lambda x: x["account_id"])


# ---------------------------------------------------------------- tests
import copy
import json
import random

import pytest

TODAY = date(2026, 10, 13)
D = timedelta


def acc(i=1, **kw):
    base = dict(id=i, email=f"m{i}@example.com", status="active",
                last_seen_at=None, last_login=date(2026, 10, 12),
                closed_at=None, closed_by=None, unpaid_invoices=0,
                litigation_hold=False, tenant="legacy", extra="x")
    base.update(kw)
    return base


def one(a):
    return plan_purge([a], TODAY)


@pytest.mark.parametrize("age,expected", [(730, "delete"), (729, None), (731, "delete")])
def test_inactive_boundaries(age, expected):
    r = one(acc(last_seen_at=TODAY - D(days=age), last_login=TODAY))
    if expected is None:
        assert [x["action"] for x in r] == ["warn"]
    else:
        assert r[0]["action"] == expected


@pytest.mark.parametrize("days,warn", [(0, False), (1, True), (14, True), (15, False)])
def test_warn_window_inactive(days, warn):
    r = one(acc(last_seen_at=TODAY - D(days=730) + D(days=days)))
    assert bool(r) == warn
    if warn:
        assert r[0]["action"] == "warn"
        assert r[0]["due"] == (TODAY + D(days=days)).isoformat()
        assert r[0]["approved_by"] is None


def test_due_today_is_delete_not_warn():
    r = one(acc(last_seen_at=TODAY - D(days=730)))
    assert r[0]["action"] == "delete" and r[0]["due"] == TODAY.isoformat()


@pytest.mark.parametrize("off,action", [(-30, "delete"), (-29, "warn"),
                                         (-16, "warn"), (-15, None)])
def test_closed_boundaries(off, action):
    # closed_at = today + off; due = closed_at + 30
    r = one(acc(closed_at=TODAY + D(days=off), closed_by="staff",
                last_seen_at=TODAY))
    assert (r[0]["action"] if r else None) == action


def test_earlier_of_rule():
    # last_seen rule earlier than closed+30
    r = one(acc(closed_at=TODAY - D(days=1), closed_by="staff",
                last_seen_at=TODAY - D(days=800)))
    assert r[0]["due"] == (TODAY - D(days=70)).isoformat()
    # closed rule earlier
    r = one(acc(closed_at=TODAY - D(days=40), last_seen_at=TODAY))
    assert r[0]["due"] == (TODAY - D(days=10)).isoformat()


def test_member_closed_no_warn_staff_closed_warn():
    kw = dict(closed_at=TODAY - D(days=20), last_seen_at=TODAY)
    assert one(acc(closed_by="member", **kw)) == []
    assert one(acc(closed_by="staff", **kw))[0]["action"] == "warn"
    assert one(acc(closed_by=None, **kw))[0]["action"] == "warn"
    assert one(acc(closed_by="other", **kw))[0]["action"] == "warn"


def test_member_closed_still_deleted():
    r = one(acc(closed_at=TODAY - D(days=30), closed_by="member"))
    assert r[0]["action"] == "delete"


def test_unpaid_invoices():
    r = one(acc(last_seen_at=TODAY - D(days=800), unpaid_invoices=3))
    assert r[0]["action"] == "anonymise" and r[0]["approved_by"] == DPO_APPROVER
    r = one(acc(last_seen_at=TODAY - D(days=725), unpaid_invoices=3))
    assert r[0]["action"] == "warn" and r[0]["approved_by"] is None


def test_litigation_hold():
    old = TODAY - D(days=900)
    assert one(acc(last_seen_at=old, litigation_hold=True)) == []
    assert one(acc(last_seen_at=old, litigation_hold=True, unpaid_invoices=1)) == []
    assert one(acc(last_seen_at=TODAY - D(days=725), litigation_hold=1)) == []


@pytest.mark.parametrize("email", ["a@tidewater-klatring.no",
                                   "  A@Tidewater-Klatring.NO \n"])
def test_staff_skipped(email):
    assert one(acc(email=email, last_seen_at=TODAY - D(days=900))) == []


@pytest.mark.parametrize("email", ["x@evil-tidewater-klatring.no",
                                   "x@tidewater-klatring.no.evil.com", None])
def test_non_staff(email):
    assert len(one(acc(email=email, last_seen_at=TODAY - D(days=900)))) == 1


def test_purged_statuses_skipped():
    for s in ["deleted", "ANONYMISED", "Anonymized"]:
        assert one(acc(status=s, last_seen_at=TODAY - D(days=900))) == []


def test_no_email_and_four_keys():
    accts = [acc(1, last_seen_at=TODAY - D(days=900)),
             acc(2, last_seen_at=TODAY - D(days=900), unpaid_invoices=1),
             acc(3, last_seen_at=TODAY - D(days=725))]
    r = plan_purge(accts, TODAY)
    assert len(r) == 3
    blob = json.dumps(r, ensure_ascii=False)
    for a in accts:
        assert a["email"] not in blob and "example.com" not in blob
    for x in r:
        assert set(x) == {"account_id", "action", "due", "approved_by"}
        assert isinstance(x["due"], str)
        date.fromisoformat(x["due"])


def test_approver_exact():
    import unicodedata
    assert DPO_APPROVER == "\u00deór\u00f0\u00eds Sveinbj\u00f6rnsd\u00f3ttir"
    assert unicodedata.is_normalized("NFC", DPO_APPROVER)
    assert one(acc(last_seen_at=TODAY - D(days=900)))[0]["approved_by"] == DPO_APPROVER


def test_none_last_seen():
    assert one(acc(last_seen_at=None, last_login=TODAY - D(days=2000))) == []
    r = one(acc(last_seen_at=None, closed_at=TODAY - D(days=30), closed_by="staff"))
    assert r[0]["action"] == "delete"


def test_cap_and_ordering():
    accts = []
    for i in range(250):
        if i % 5 == 0:  # closed, due today
            accts.append(acc(i, closed_at=TODAY - D(days=30), closed_by="staff",
                             last_seen_at=TODAY))
        elif i == 249:  # inactive, earliest due, highest id
            accts.append(acc(i, last_seen_at=TODAY - D(days=800)))
        else:  # inactive, all due today (ties broken by id)
            accts.append(acc(i, last_seen_at=TODAY - D(days=730)))
    # uncapped extras
    accts.append(acc(1000, last_seen_at=TODAY - D(days=900), unpaid_invoices=1))
    accts.append(acc(1001, last_seen_at=TODAY - D(days=725)))
    accts.append(acc(1002, last_seen_at=TODAY - D(days=900), litigation_hold=True))
    r = plan_purge(accts, TODAY)
    dels = [x["account_id"] for x in r if x["action"] == "delete"]
    assert len(dels) == 200
    closed = [i for i in range(250) if i % 5 == 0]
    inactive = sorted(i for i in range(250) if i % 5 and i != 249)
    expected = set(closed) | set(inactive[:149]) | {249}
    assert set(dels) == expected
    deferred = set(range(250)) - expected
    assert len(deferred) == 50 and deferred == set(inactive[149:])
    ids = [x["account_id"] for x in r]
    assert not deferred & set(ids)
    assert ids == sorted(ids)
    assert {1000: "anonymise", 1001: "warn"} == {
        x["account_id"]: x["action"] for x in r if x["account_id"] >= 1000}
    assert any(i % 5 == 0 for i in ids[:10]) and any(i % 5 for i in ids[:10])


def test_deterministic_and_not_mutated():
    accts = [acc(i, last_seen_at=TODAY - D(days=700 + i)) for i in range(60)]
    before = copy.deepcopy(accts)
    base = plan_purge(accts, TODAY)
    assert accts == before
    for seed in range(5):
        sh = accts[:]
        random.Random(seed).shuffle(sh)
        assert plan_purge(sh, TODAY) == base