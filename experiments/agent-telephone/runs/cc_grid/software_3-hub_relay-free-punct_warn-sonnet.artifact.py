"""Tidewater Climbing GDPR member-account clean-up planner (pure, no I/O).

Output action dicts carry exactly four keys (account_id, action, due,
approved_by). The email is deliberately excluded, per the explicit
requirement that no email or other key may appear in the output.
"""
from datetime import date, timedelta

CAP = 200
INACTIVITY_DAYS = 730
CLOSURE_DAYS = 30
WARN_DAYS = 14
STAFF_DOMAIN = "@tidewater-klatring.no"
APPROVER = "Þórdís Sveinbjörnsdóttir"


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def plan_purge(accounts, today):
    today_warn = today + timedelta(days=WARN_DAYS)
    deletes = []  # (sort key, action)
    others = []

    for acc in accounts:
        if _is_staff(acc.get("email")) or acc.get("litigation_hold"):
            continue

        seen = acc.get("last_seen_at")
        closed = acc.get("closed_at")
        candidates = []
        if seen is not None:
            candidates.append(seen + timedelta(days=INACTIVITY_DAYS))
        if closed is not None:
            candidates.append(closed + timedelta(days=CLOSURE_DAYS))
        if not candidates:
            continue
        due = min(candidates)
        acc_id = acc.get("id")

        def make(action, approver):
            return {
                "account_id": acc_id,
                "action": action,
                "due": due.isoformat(),
                "approved_by": approver,
            }

        if due <= today:
            if acc.get("unpaid_invoices"):
                others.append(make("anonymise", APPROVER))
            else:
                deletes.append(((closed is None, due, acc_id), make("delete", APPROVER)))
        elif due <= today_warn:
            if closed is not None and acc.get("closed_by") == "member":
                continue
            others.append(make("warn", None))

    deletes.sort(key=lambda t: t[0])
    result = others + [a for _, a in deletes[:CAP]]
    result.sort(key=lambda a: a["account_id"])
    return result


# ===== test_purge.py =====
import copy
from datetime import date, timedelta

import pytest

from purge import APPROVER, CAP, plan_purge

TODAY = date(2026, 10, 13)


def d(n):
    return timedelta(days=n)


def acct(id=1, **kw):
    base = {
        "id": id, "email": f"m{id}@example.com", "status": "active",
        "last_seen_at": TODAY - d(10), "last_login": None, "closed_at": None,
        "closed_by": None, "unpaid_invoices": 0, "litigation_hold": False,
    }
    base.update(kw)
    return base


def run(*accts):
    return plan_purge(list(accts), TODAY)


def test_empty():
    assert plan_purge([], TODAY) == []


def test_730_delete_due_today():
    r = run(acct(last_seen_at=TODAY - d(730)))
    assert r == [{"account_id": 1, "action": "delete", "due": TODAY.isoformat(), "approved_by": APPROVER}]


def test_729_warn_due_tomorrow():
    r = run(acct(last_seen_at=TODAY - d(729)))
    assert r == [{"account_id": 1, "action": "warn", "due": (TODAY + d(1)).isoformat(), "approved_by": None}]


def test_716_warn_715_nothing():
    assert run(acct(last_seen_at=TODAY - d(716)))[0]["action"] == "warn"
    assert run(acct(last_seen_at=TODAY - d(715))) == []


def test_closed_30_days_delete():
    r = run(acct(closed_at=TODAY - d(30), closed_by="staff"))
    assert r[0]["action"] == "delete"
    assert r[0]["due"] == TODAY.isoformat()


def test_staff_closed_warn_due_closure():
    c = TODAY - d(10)
    r = run(acct(closed_at=c, closed_by="staff"))
    assert r[0]["action"] == "warn"
    assert r[0]["due"] == (c + d(30)).isoformat()


def test_member_closed_no_warn_but_deleted():
    assert run(acct(closed_at=TODAY - d(10), closed_by="member")) == []
    assert run(acct(closed_at=TODAY - d(30), closed_by="member"))[0]["action"] == "delete"


def test_missing_closed_by_is_not_member():
    assert run(acct(closed_at=TODAY - d(10), closed_by=None))[0]["action"] == "warn"


@pytest.mark.parametrize("unpaid", [2, ["inv1"]])
def test_unpaid_anonymise_and_warn(unpaid):
    r = run(acct(last_seen_at=TODAY - d(730), unpaid_invoices=unpaid))
    assert r[0]["action"] == "anonymise" and r[0]["approved_by"] == APPROVER
    r = run(acct(last_seen_at=TODAY - d(729), unpaid_invoices=unpaid))
    assert r[0]["action"] == "warn" and r[0]["approved_by"] is None


def test_litigation_hold():
    assert run(acct(last_seen_at=TODAY - d(900), litigation_hold=True)) == []


@pytest.mark.parametrize("email,excluded", [
    ("a@tidewater-klatring.no", True),
    ("  A@TIDEWATER-KLATRING.NO  ", True),
    ("x@tidewater-klatring.no.example.com", False),
    ("x@notidewater-klatring.no", False),
    (None, False),
])
def test_staff_emails(email, excluded):
    r = run(acct(email=email, last_seen_at=TODAY - d(800)))
    assert (r == []) == excluded


def test_last_login_and_status_irrelevant():
    a = run(acct(last_seen_at=TODAY - d(800), last_login=TODAY, status="active"))
    b = run(acct(last_seen_at=TODAY - d(800), last_login=None, status="closed"))
    assert a == b and a[0]["action"] == "delete"


def test_tenant_ignored():
    r = run(acct(last_seen_at=TODAY - d(800), tenant="old"))
    assert r[0]["action"] == "delete"


def test_output_keys_no_email():
    r = run(acct(email="secret@example.com", last_seen_at=TODAY - d(800)),
            acct(id=2, last_seen_at=TODAY - d(725)))
    for item in r:
        assert set(item) == {"account_id", "action", "due", "approved_by"}
        assert "secret@example.com" not in str(item)


def test_due_is_iso_string_even_if_past():
    r = run(acct(last_seen_at=TODAY - d(800)))
    assert r[0]["due"] == (TODAY - d(70)).isoformat()
    assert isinstance(r[0]["due"], str)


def test_missing_last_seen():
    assert run(acct(last_seen_at=None)) == []
    r = run(acct(last_seen_at=None, closed_at=TODAY - d(31)))
    assert r[0]["action"] == "delete"


def test_cap_250():
    accts = []
    for k in range(100):  # closed, ids high
        accts.append(acct(1000 + k, last_seen_at=TODAY - d(5), closed_at=TODAY - d(30 + k), closed_by="staff"))
    for i in range(150):  # inactive, due = TODAY - i
        accts.append(acct(i, last_seen_at=TODAY - d(730 + i)))
    r = plan_purge(accts, TODAY)
    assert len(r) == CAP and all(x["action"] == "delete" for x in r)
    ids = [x["account_id"] for x in r]
    assert ids == sorted(ids)
    assert set(range(1000, 1100)) <= set(ids)
    assert {i for i in ids if i < 1000} == set(range(50, 150))


def test_cap_ignores_other_actions():
    accts = [acct(i, last_seen_at=TODAY - d(730)) for i in range(1, 201)]
    accts += [acct(500 + i, last_seen_at=TODAY - d(730), unpaid_invoices=1) for i in range(5)]
    accts += [acct(600, email="s@tidewater-klatring.no", last_seen_at=TODAY - d(900))]
    accts += [acct(601, litigation_hold=True, last_seen_at=TODAY - d(900))]
    accts += [acct(602, last_seen_at=TODAY - d(725))]
    r = plan_purge(accts, TODAY)
    kinds = [x["action"] for x in r]
    assert kinds.count("delete") == 200
    assert kinds.count("anonymise") == 5
    assert kinds.count("warn") == 1
    assert 600 not in [x["account_id"] for x in r]


def test_cap_tie_broken_by_id():
    accts = [acct(i, last_seen_at=TODAY - d(730)) for i in range(201)]
    ids = [x["account_id"] for x in plan_purge(accts, TODAY)]
    assert 200 not in ids and len(ids) == 200


def test_input_unchanged():
    accts = [acct(2, last_seen_at=TODAY - d(800)), acct(1, last_seen_at=TODAY - d(725))]
    before = copy.deepcopy(accts)
    plan_purge(accts, TODAY)
    assert accts == before