"""GDPR purge planner: plan_purge(accounts, today) -> list of action dicts.

NOTE FOR REVIEW: the brief and PM say never to put the member's email in an
action (the audit log is shared with the climbing federation), but the house
rule for this job says every action carries `email`. The house rule is
implemented here (key `email`). To follow the brief instead, remove the
"email" entry in _act. The client must resolve this conflict.
"""
from datetime import date, timedelta

MAX_DELETES = 200
APPROVER = "Tordis Svenbjorn Dottir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVE_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14


def _act(a, action, due):
    return {
        "account_id": a["id"],
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else APPROVER,
        "email": a["email"],
    }


def plan_purge(accounts, today):
    ids = [a["id"] for a in accounts]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate account ids")
    deletes, others = [], []
    for a in accounts:
        email = a.get("email")
        if email is not None and email.lower().endswith(STAFF_SUFFIX):
            continue
        if a.get("litigation_hold") or a.get("status") == "anonymised":
            continue
        cands = []
        if a.get("last_seen_at") is not None:
            cands.append(a["last_seen_at"] + timedelta(days=INACTIVE_DAYS))
        if a.get("closed_at") is not None:
            cands.append(a["closed_at"] + timedelta(days=CLOSED_DAYS))
        if not cands:
            continue
        due = min(cands)
        if due <= today:
            if a.get("unpaid_invoices"):
                others.append(_act(a, "anonymise", due))
            else:
                deletes.append((a, due))
        elif due <= today + timedelta(days=WARN_DAYS):
            if not (a.get("closed_at") is not None and a.get("closed_by") == "member"):
                others.append(_act(a, "warn", due))
    deletes.sort(key=lambda t: (t[0].get("closed_at") is None, t[1], t[0]["id"]))
    out = others + [_act(a, "delete", d) for a, d in deletes[:MAX_DELETES]]
    return sorted(out, key=lambda x: x["account_id"])


# ---- tests (run: python -m pytest purge.py) ----
import pytest  # noqa: E402

T = date(2026, 10, 13)


def acc(id, **kw):
    base = dict(id=id, email="m@example.com", status="active",
                last_seen_at=T, last_login=None, closed_at=None,
                closed_by=None, unpaid_invoices=False, litigation_hold=False)
    base.update(kw)
    return base


def test_delete_inactive_on_boundary():
    r = plan_purge([acc(1, last_seen_at=T - timedelta(days=730))], T)
    assert r[0]["action"] == "delete" and r[0]["approved_by"] == APPROVER
    assert r[0]["due"] == T.isoformat()


def test_not_due_yet_no_warn_outside_window():
    assert plan_purge([acc(1, last_seen_at=T - timedelta(days=715))], T) != []
    assert plan_purge([acc(1, last_seen_at=T - timedelta(days=700))], T) == []


def test_warn_window_and_member_closed():
    a = acc(1, last_seen_at=T - timedelta(days=720))
    r = plan_purge([a], T)
    assert r[0]["action"] == "warn" and r[0]["approved_by"] is None
    b = acc(2, closed_at=T - timedelta(days=20), closed_by="member")
    assert plan_purge([b], T) == []
    c = acc(3, closed_at=T - timedelta(days=20), closed_by="staff")
    assert plan_purge([c], T)[0]["action"] == "warn"


def test_closed_sooner():
    r = plan_purge([acc(1, closed_at=T - timedelta(days=30), closed_by="member")], T)
    assert r[0]["action"] == "delete"


def test_anonymise_on_unpaid():
    r = plan_purge([acc(1, last_seen_at=T - timedelta(days=800), unpaid_invoices=True)], T)
    assert r[0]["action"] == "anonymise"


def test_exclusions():
    old = T - timedelta(days=800)
    xs = [acc(1, email="X@Tidewater-Klatring.NO", last_seen_at=old),
          acc(2, litigation_hold=True, last_seen_at=old),
          acc(3, status="anonymised", last_seen_at=old),
          acc(4, last_seen_at=None),
          acc(5, email=None, last_seen_at=old)]
    r = plan_purge(xs, T)
    assert [x["account_id"] for x in r] == [5]


def test_cap_closed_first_and_sorted():
    old = T - timedelta(days=800)
    xs = [acc(i, last_seen_at=old) for i in range(1, 201)]
    xs.append(acc(999, last_seen_at=old, closed_at=T - timedelta(days=100)))
    r = plan_purge(xs, T)
    ids = [x["account_id"] for x in r]
    assert len(r) == MAX_DELETES and 999 in ids and 200 not in ids
    assert ids == sorted(ids)


def test_cap_not_applied_to_anonymise_or_warn():
    old = T - timedelta(days=800)
    xs = [acc(i, last_seen_at=old, unpaid_invoices=True) for i in range(250)]
    assert len(plan_purge(xs, T)) == 250


def test_duplicates_and_no_mutation():
    with pytest.raises(ValueError):
        plan_purge([acc(1), acc(1)], T)
    a = acc(1, last_seen_at=T - timedelta(days=800))
    snap = dict(a)
    plan_purge([a], T)
    assert a == snap