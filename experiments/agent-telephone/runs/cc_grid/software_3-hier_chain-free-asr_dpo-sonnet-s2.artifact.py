# ===== FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-e6_9kdfa/tidewater_purge.py =====
"""Tidewater Klatring GDPR clean-up planner for member accounts.

Design: small pure helpers (_is_staff, _as_date, _closed_date, _due_date) and
one entry point, plan_purge(accounts, today), which returns action dicts with
exactly the keys account_id, action, due (ISO string) and approved_by.
Nothing is mutated, logged or printed.

Odd-data rules
- closed_at is the sole source of truth for "closed"; status and last_login
  are never used.
- closed_at later than today is a data error: treated as not closed (no
  closure due date, no closed priority). Inactivity still applies.
- last_seen_at None/missing: no inactivity due date (no fallback to
  last_login). A validly closed account still has its closure due date. If no
  due date can be computed, there is no action.
- OverflowError when adding days: that candidate due date is ignored.
- Non-date values (and datetimes) in date fields are treated as missing.
- Duplicate ids are NOT de-duplicated; each dict is evaluated on its own.
- The obsolete "tenant" key is never read.

Assumptions to confirm with the client
- MAX_DELETIONS_PER_RUN (200) caps "delete" actions only. Anonymise actions
  are uncapped, although they also write to the database. Deletes over the
  cap get no warn and are picked up next run (closed first, oldest due, id).
- closed_at is the source of truth for "closed"; the odd-data handling above.
- House rule says every action dict should carry the account email. This
  conflicts with the task spec (exactly four keys, email never in output,
  and GDPR data minimisation), so the email is deliberately omitted. Support
  can look the member up by account_id. Please confirm.
- Not verified: the test suite below was written without the ability to run
  pytest in this environment, so no actual pytest result is available.
"""
from datetime import date, datetime, timedelta

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
MAX_DELETIONS_PER_RUN = 200
STAFF_EMAIL_DOMAIN = "@tidewater-klatring.no"
DPO_APPROVER = "Tordis Svenbjorn Dottir"


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_EMAIL_DOMAIN)


def _as_date(value):
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return None


def _closed_date(account, today):
    closed = _as_date(account.get("closed_at"))
    return closed if closed is not None and closed <= today else None


def _due_date(account, today):
    """Return (due, is_closed) or None if no due date can be computed."""
    candidates = []
    seen = _as_date(account.get("last_seen_at"))
    if seen is not None:
        try:
            candidates.append(seen + timedelta(days=INACTIVITY_DAYS))
        except OverflowError:
            pass
    closed = _closed_date(account, today)
    if closed is not None:
        try:
            candidates.append(closed + timedelta(days=CLOSED_GRACE_DAYS))
        except OverflowError:
            pass
    if not candidates:
        return None
    return min(candidates), closed is not None


def _action(account_id, action, due):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else DPO_APPROVER,
    }


def plan_purge(accounts, today):
    if not isinstance(today, date) or isinstance(today, datetime):
        raise TypeError("today must be a datetime.date (not a datetime)")
    try:
        horizon = today + timedelta(days=WARN_WINDOW_DAYS)
    except OverflowError:
        horizon = date.max

    deletes, anonymises, warns = [], [], []
    for account in accounts:
        if _is_staff(account.get("email")) or account.get("litigation_hold"):
            continue
        result = _due_date(account, today)
        if result is None:
            continue
        due, is_closed = result
        account_id = account.get("id")
        if due <= today:
            if account.get("unpaid_invoices"):
                anonymises.append(_action(account_id, "anonymise", due))
            else:
                deletes.append(((0 if is_closed else 1, due, account_id),
                                _action(account_id, "delete", due)))
        elif due <= horizon and account.get("closed_by") != "member":
            warns.append(_action(account_id, "warn", due))

    deletes.sort(key=lambda pair: pair[0])
    kept = [act for _, act in deletes[:MAX_DELETIONS_PER_RUN]]
    return sorted(kept + anonymises + warns, key=lambda a: a["account_id"])


# ===== FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-e6_9kdfa/test_tidewater_purge.py =====
import copy
import json
import random
from datetime import date, datetime, timedelta

import pytest

from tidewater_purge import (DPO_APPROVER, MAX_DELETIONS_PER_RUN, plan_purge)

TODAY = date(2026, 10, 13)


def d(n):
    return TODAY + timedelta(days=n)


def make(id="a1", **kw):
    acc = {"id": id, "email": "member@example.com", "status": "active",
           "last_seen_at": d(-1), "last_login": d(-1), "closed_at": None,
           "closed_by": None, "unpaid_invoices": 0, "litigation_hold": False}
    acc.update(kw)
    return acc


def run(*accs):
    return plan_purge(list(accs), TODAY)


def one(**kw):
    res = run(make(**kw))
    return res[0] if res else None


def test_730_boundary():
    r = one(last_seen_at=d(-730))
    assert r["action"] == "delete" and r["due"] == TODAY.isoformat()
    r = one(last_seen_at=d(-729))
    assert r["action"] == "warn" and r["due"] == d(1).isoformat()


def test_731_plus():
    r = one(last_seen_at=d(-800))
    assert r["action"] == "delete" and r["due"] == d(-70).isoformat()


def test_closed_boundary():
    assert one(closed_at=d(-30), closed_by="staff")["action"] == "delete"
    assert one(closed_at=d(-29), closed_by="staff")["action"] == "warn"
    assert one(closed_at=d(-30), last_seen_at=d(-1))["action"] == "delete"


def test_earlier_of():
    r = one(last_seen_at=d(-725), closed_at=d(-1), closed_by="staff")
    assert r["due"] == d(5).isoformat()  # inactivity earlier
    r = one(last_seen_at=d(-720), closed_at=d(-27), closed_by="staff")
    assert r["due"] == d(3).isoformat()  # closure earlier


def test_warn_window_edges():
    assert one(last_seen_at=d(-729))["action"] == "warn"
    assert one(last_seen_at=d(-730 + 14))["action"] == "warn"
    assert one(last_seen_at=d(-730 + 15)) is None
    assert one(last_seen_at=d(-730))["action"] == "delete"


def test_member_closed_no_warn_but_delete():
    assert one(closed_at=d(-29), closed_by="member") is None
    assert one(closed_at=d(-30), closed_by="member")["action"] == "delete"
    assert one(closed_at=d(-29), closed_by="staff")["action"] == "warn"
    assert one(closed_at=d(-29), closed_by=None)["action"] == "warn"


def test_last_login_ignored():
    assert one(last_login=d(-2000), last_seen_at=d(-1)) is None
    assert one(last_login=d(-1), last_seen_at=d(-2000))["action"] == "delete"


def test_unpaid_anonymise_and_warn():
    assert one(unpaid_invoices=3, last_seen_at=d(-800))["action"] == "anonymise"
    assert one(unpaid_invoices=True, last_seen_at=d(-800))["action"] == "anonymise"
    assert one(unpaid_invoices=None, last_seen_at=d(-800))["action"] == "delete"
    assert one(unpaid_invoices=2, last_seen_at=d(-729))["action"] == "warn"


def test_litigation_hold():
    assert one(litigation_hold=True, last_seen_at=d(-800)) is None
    assert one(litigation_hold=True, last_seen_at=d(-729)) is None


@pytest.mark.parametrize("email", ["x@TIDEWATER-KLATRING.NO", "x@tidewater-klatring.no  ",
                                   "  x@Tidewater-Klatring.no"])
def test_staff_excluded(email):
    assert one(email=email, last_seen_at=d(-800)) is None


@pytest.mark.parametrize("email", ["x@tidewater-klatring.no.evil.com",
                                   "x@notidewater-klatring.no", None, 42])
def test_not_staff(email):
    assert one(email=email, last_seen_at=d(-800))["action"] == "delete"


def test_approver():
    assert one(last_seen_at=d(-800))["approved_by"] == DPO_APPROVER
    assert one(last_seen_at=d(-800), unpaid_invoices=1)["approved_by"] == DPO_APPROVER
    assert one(last_seen_at=d(-729))["approved_by"] is None


def test_output_shape_and_no_email():
    email = "secret.person@example.com"
    res = run(make("a", email=email, last_seen_at=d(-800)),
              make("b", email=email, last_seen_at=d(-729)))
    for r in res:
        assert set(r) == {"account_id", "action", "due", "approved_by"}
        assert isinstance(r["due"], str)
    assert email not in json.dumps(res)


def _bulk(n, prefix="i", **kw):
    return [make(f"{prefix}{i:03d}", last_seen_at=d(-731 - i), **kw) for i in range(n)]


def test_cap_200_and_201():
    assert len(run(*_bulk(200))) == 200
    res = run(*_bulk(201))
    assert len(res) == 200 and all(r["action"] == "delete" for r in res)
    assert "i000" not in {r["account_id"] for r in res}  # newest due dropped


def test_cap_order_closed_then_oldest_then_id():
    closed = [make(f"c{i:03d}", closed_at=d(-30)) for i in range(150)]
    inactive = _bulk(100)
    res = run(*inactive, *closed)
    ids = {r["account_id"] for r in res}
    assert len(res) == 200
    assert all(f"c{i:03d}" in ids for i in range(150))
    assert ids - {f"c{i:03d}" for i in range(150)} == {f"i{i:03d}" for i in range(50, 100)}
    assert [r["account_id"] for r in res] == sorted(ids)


def test_cap_id_tiebreak_and_no_warn_for_dropped():
    accs = [make(f"t{i:03d}", last_seen_at=d(-740)) for i in range(201)]
    res = run(*accs)
    assert len(res) == 200
    assert "t200" not in {r["account_id"] for r in res}
    assert all(r["action"] == "delete" for r in res)


def test_anonymise_uncapped_and_no_slot_use():
    assert len(run(*_bulk(201, unpaid_invoices=1))) == 201
    res = run(*_bulk(200, prefix="d"), *_bulk(50, prefix="u", unpaid_invoices=1))
    assert sum(r["action"] == "delete" for r in res) == 200
    assert sum(r["action"] == "anonymise" for r in res) == 50
    assert [r["account_id"] for r in res] == sorted(r["account_id"] for r in res)


def test_closed_priority_by_closed_at_set():
    old = [make(f"o{i:03d}", last_seen_at=d(-1000)) for i in range(200)]
    both = make("z-closed", last_seen_at=d(-731), closed_at=d(-5), closed_by="staff")
    res = run(*old, both)
    ids = {r["account_id"] for r in res}
    assert len(res) == 200 and "z-closed" in ids and "o199" not in ids


def test_sorted_when_shuffled():
    accs = [make(f"id{i:03d}", last_seen_at=d(-800)) for i in range(30)]
    random.Random(1).shuffle(accs)
    ids = [r["account_id"] for r in run(*accs)]
    assert ids == sorted(ids)


def test_tenant_key_irrelevant():
    base = [make("a", last_seen_at=d(-800)), make("b", last_seen_at=d(-729))]
    expected = run(*base)
    for val in ("x", None, 5, {"k": 1}):
        accs = [dict(a, tenant=val) for a in base]
        assert run(*accs) == expected


def test_no_mutation_and_empty():
    accs = [make("a", last_seen_at=d(-800), tenant="t"), make("b")]
    snap = copy.deepcopy(accs)
    plan_purge(accs, TODAY)
    assert accs == snap
    assert plan_purge([], TODAY) == []


def test_today_type_errors():
    with pytest.raises(TypeError):
        plan_purge([], datetime(2026, 10, 13))
    with pytest.raises(TypeError):
        plan_purge([], "2026-10-13")


def test_odd_data():
    assert one(closed_at=d(5), closed_by="staff") is None  # future closed_at
    r = one(closed_at=d(5), last_seen_at=d(-800))
    assert r["action"] == "delete" and r["due"] == d(-70).isoformat()
    assert one(last_seen_at=None) is None
    assert one(last_seen_at=None, closed_at=d(-30))["action"] == "delete"
    assert one(status="closed") is None
    assert one(status="active", closed_at=d(-30))["action"] == "delete"
    assert plan_purge([{"id": "x"}], TODAY) == []
    assert one(last_seen_at=datetime(2020, 1, 1)) is None
    assert one(last_seen_at="2020-01-01") is None
    assert one(last_seen_at=date.max, closed_at=d(-30))["action"] == "delete"
    assert plan_purge([{"id": "x", "last_seen_at": d(-800)}], TODAY)[0]["action"] == "delete"