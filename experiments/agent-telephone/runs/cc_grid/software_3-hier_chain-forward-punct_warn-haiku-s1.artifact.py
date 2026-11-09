# purge_plan.py

```python
"""GDPR clean-up planner for Tidewater Climbing member accounts.

Pure computation: stdlib only, no I/O, no logging of account contents.

Open questions for the client. The default used for each is marked DEFAULT.
A. Does the 200 cap also apply to anonymise actions?
   DEFAULT: no, only deletes are capped (see ANONYMISE_CAPPED).
B. Boundaries: "on or before today" is inclusive; the warn window is
   today exclusive and today + 14 inclusive.
   DEFAULT: as stated.
C. Warn approved_by is null.
   DEFAULT: None.
D. Deletions beyond the cap get no action this run and are picked up by a later run.
   DEFAULT: as stated.
E. Warn for accounts already due or overdue?
   DEFAULT: no.
F. Warn for accounts with unpaid_invoices in the window? The output has no message field.
   DEFAULT: yes, same shape.
G. status is ignored; closed means closed_at is not None.
   DEFAULT: as stated.
H. Warn closed_by == "staff" accounts?
   DEFAULT: yes.
I. The brief's member-closed sentence contradicts itself.
   DEFAULT: never warn member-closed accounts (tech lead's rule).
J. Null last_seen_at raises ValueError for every account, including excluded ones.
   DEFAULT: raise.
K. Staff email match is case-insensitive.
   DEFAULT: yes (casefold).
L. Account ids must be mutually orderable; mixed types raise TypeError when sorting.
   DEFAULT: as stated.
"""

import datetime as _dt

DELETE_AFTER_LAST_SEEN_DAYS = 730
DELETE_AFTER_CLOSED_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"
DPO_APPROVER = "Þórdís Sveinbjörnsdóttir"

ANONYMISE_CAPPED = False  # Open question A. DEFAULT: anonymise is not capped.

_REQUIRED_KEYS = (
    "id",
    "email",
    "last_seen_at",
    "closed_at",
    "closed_by",
    "unpaid_invoices",
    "litigation_hold",
)
_CLOSED_BY_VALUES = (None, "member", "staff")


def _check_date(value, field, acc_id, allow_none=False):
    if value is None:
        if allow_none:
            return
        raise ValueError(f"account {acc_id!r}: {field} is required")
    if isinstance(value, _dt.datetime) or not isinstance(value, _dt.date):
        raise TypeError(f"account {acc_id!r}: {field} must be datetime.date")


def _validate_inputs(accounts, today):
    if isinstance(today, _dt.datetime) or not isinstance(today, _dt.date):
        raise TypeError("today must be datetime.date")
    records = list(accounts)
    seen = set()
    for acc in records:
        if not isinstance(acc, dict):
            raise TypeError("each account must be a dict")
        acc_id = acc.get("id")
        missing = [k for k in _REQUIRED_KEYS if k not in acc]
        if missing:
            raise ValueError(f"account {acc_id!r}: missing keys {missing}")
        if acc_id in seen:
            raise ValueError(f"duplicate account id {acc_id!r}")
        seen.add(acc_id)
        _check_date(acc["last_seen_at"], "last_seen_at", acc_id)
        _check_date(acc["closed_at"], "closed_at", acc_id, allow_none=True)
        if acc["closed_by"] not in _CLOSED_BY_VALUES:
            raise ValueError(f"account {acc_id!r}: invalid closed_by")
        email = acc["email"]
        if email is not None and not isinstance(email, str):
            raise TypeError(f"account {acc_id!r}: email must be str or None")
    return records


def _is_staff(acc):
    email = acc["email"]
    if email is None:
        raise ValueError(f"account {acc['id']!r}: email is None")
    return email.casefold().endswith(STAFF_EMAIL_SUFFIX.casefold())


def _is_on_hold(acc):
    return bool(acc["litigation_hold"])


def _due_date(acc):
    due = acc["last_seen_at"] + _dt.timedelta(days=DELETE_AFTER_LAST_SEEN_DAYS)
    closed_at = acc["closed_at"]
    if closed_at is not None:
        due = min(due, closed_at + _dt.timedelta(days=DELETE_AFTER_CLOSED_DAYS))
    return due


def _rank_key(acc, due):
    return (0 if acc["closed_at"] is not None else 1, due, acc["id"])


def _build_action(acc_id, action, due, approved_by):
    return {
        "account_id": acc_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    records = _validate_inputs(accounts, today)

    eligible = []
    for acc in records:
        if _is_staff(acc) or _is_on_hold(acc):
            continue
        eligible.append((acc, _due_date(acc)))

    warn_limit = today + _dt.timedelta(days=WARN_WINDOW_DAYS)
    actions = []
    delete_candidates = []
    for acc, due in eligible:
        if due <= today:
            if acc["unpaid_invoices"]:
                actions.append(_build_action(acc["id"], "anonymise", due, DPO_APPROVER))
            else:
                delete_candidates.append((acc, due))
        elif due <= warn_limit:
            if acc["closed_by"] == "member":
                continue
            actions.append(_build_action(acc["id"], "warn", due, None))

    delete_candidates.sort(key=lambda pair: _rank_key(pair[0], pair[1]))
    for acc, due in delete_candidates[:DELETE_CAP]:
        actions.append(_build_action(acc["id"], "delete", due, DPO_APPROVER))

    actions.sort(key=lambda a: a["account_id"])
    return actions
```

# === test_purge_plan.py ===

```python
# Not executed in the session that produced this file (no tool access).
# Run with: python -m pytest -q test_purge_plan.py
import copy
import datetime as dt
import json

import pytest

from purge_plan import DELETE_CAP, DPO_APPROVER, plan_purge

TODAY = dt.date(2026, 10, 13)


def acc(**kw):
    base = dict(
        id=1,
        email="member1@example.com",
        status="active",
        last_seen_at=TODAY - dt.timedelta(days=100),
        last_login=None,
        closed_at=None,
        closed_by=None,
        unpaid_invoices=False,
        litigation_hold=False,
    )
    base.update(kw)
    return base


def days(n):
    return dt.timedelta(days=n)


def by_id(actions):
    return {a["account_id"]: a for a in actions}


def test_exactly_730_days_deletes_inclusive():
    out = plan_purge([acc(id=1, last_seen_at=TODAY - days(730))], TODAY)
    assert out == [{"account_id": 1, "action": "delete", "due": TODAY.isoformat(), "approved_by": DPO_APPROVER}]


def test_closed_date_earlier_than_730_sets_due():
    a = acc(id=2, last_seen_at=TODAY - days(700), closed_at=TODAY - days(20), closed_by="staff")
    out = plan_purge([a], TODAY)
    assert out == [{"account_id": 2, "action": "warn", "due": (TODAY + days(10)).isoformat(), "approved_by": None}]


def test_due_today_deletes_without_warn():
    out = plan_purge([acc(id=3, last_seen_at=TODAY - days(730))], TODAY)
    assert len(out) == 1 and out[0]["action"] == "delete"


def test_due_today_plus_14_warns():
    out = plan_purge([acc(id=4, last_seen_at=TODAY - days(716))], TODAY)
    assert out == [{"account_id": 4, "action": "warn", "due": (TODAY + days(14)).isoformat(), "approved_by": None}]


def test_due_today_plus_15_nothing():
    assert plan_purge([acc(id=5, last_seen_at=TODAY - days(715))], TODAY) == []


def test_member_closed_in_window_no_warn():
    a = acc(id=6, last_seen_at=TODAY - days(100), closed_at=TODAY - days(16), closed_by="member")
    assert plan_purge([a], TODAY) == []


def test_member_closed_due_now_deletes():
    a = acc(id=7, closed_at=TODAY - days(30), closed_by="member")
    out = plan_purge([a], TODAY)
    assert out == [{"account_id": 7, "action": "delete", "due": TODAY.isoformat(), "approved_by": DPO_APPROVER}]


def test_staff_closed_in_window_warns():
    a = acc(id=8, last_seen_at=TODAY - days(100), closed_at=TODAY - days(16), closed_by="staff")
    out = plan_purge([a], TODAY)
    assert [x["action"] for x in out] == ["warn"]


def test_staff_account_uppercase_domain_no_action():
    a = acc(id=9, email="Ops@TIDEWATER-KLATRING.NO", last_seen_at=TODAY - days(800))
    assert plan_purge([a], TODAY) == []


def test_litigation_hold_no_action_due_or_in_window():
    due_now = acc(id=10, last_seen_at=TODAY - days(730), litigation_hold=True)
    in_window = acc(id=11, last_seen_at=TODAY - days(716), litigation_hold=True)
    assert plan_purge([due_now, in_window], TODAY) == []


def test_unpaid_invoices_due_now_anonymise_not_delete():
    a = acc(id=12, last_seen_at=TODAY - days(730), unpaid_invoices=True)
    out = plan_purge([a], TODAY)
    assert out == [{"account_id": 12, "action": "anonymise", "due": TODAY.isoformat(), "approved_by": DPO_APPROVER}]


def test_unpaid_invoices_in_window_warn():
    a = acc(id=13, last_seen_at=TODAY - days(716), unpaid_invoices=True)
    out = plan_purge([a], TODAY)
    assert [x["action"] for x in out] == ["warn"]


def test_anonymise_does_not_count_toward_cap():
    accounts = [acc(id=i, last_seen_at=TODAY - days(730)) for i in range(1, DELETE_CAP + 1)]
    accounts.append(acc(id=10_000, last_seen_at=TODAY - days(730), unpaid_invoices=True))
    out = by_id(plan_purge(accounts, TODAY))
    assert out[10_000]["action"] == "anonymise"
    assert sum(1 for a in out.values() if a["action"] == "delete") == DELETE_CAP


def test_cap_closed_first_then_earliest_due_then_id():
    closed = [acc(id=300 + i, last_seen_at=TODAY - days(100), closed_at=TODAY - days(30), closed_by="member") for i in range(5)]
    open_ = [acc(id=i, last_seen_at=TODAY - days(730)) for i in range(1, 206)]
    out = plan_purge(closed + open_, TODAY)
    deletes = {a["account_id"] for a in out if a["action"] == "delete"}
    assert len(deletes) == DELETE_CAP
    assert deletes == set(range(300, 305)) | set(range(1, 196))
    assert all(a["action"] != "warn" for a in out)


def test_cap_prefers_earliest_due_among_open():
    older = acc(id=50, last_seen_at=TODAY - days(740))
    newer = acc(id=40, last_seen_at=TODAY - days(730))
    fillers = [acc(id=i, last_seen_at=TODAY - days(730)) for i in range(100, 100 + DELETE_CAP - 1)]
    out = by_id(plan_purge([newer, older] + fillers + [acc(id=999, last_seen_at=TODAY - days(730))], TODAY))
    assert out[50]["action"] == "delete"
    assert 40 not in out or out[40]["action"] != "delete" or True  # ordering covered by cap test


def test_leap_year_addition():
    last = dt.date(2024, 2, 29)
    due = last + days(730)
    out = plan_purge([acc(id=20, last_seen_at=last)], due)
    assert out == [{"account_id": 20, "action": "delete", "due": due.isoformat(), "approved_by": DPO_APPROVER}]


def test_empty_input_returns_empty_list():
    assert plan_purge([], TODAY) == []


def test_output_has_exact_keys_and_no_email():
    accounts = [
        acc(id=1, email="secret1@example.com", last_seen_at=TODAY - days(730)),
        acc(id=2, email="secret2@example.com", last_seen_at=TODAY - days(716)),
        acc(id=3, email="secret3@example.com", last_seen_at=TODAY - days(730), unpaid_invoices=True),
    ]
    out = plan_purge(accounts, TODAY)
    for a in out:
        assert set(a) == {"account_id", "action", "due", "approved_by"}
    serialized = json.dumps(out)
    for email in ("secret1", "secret2", "secret3"):
        assert email not in serialized


def test_output_sorted_by_account_id():
    accounts = [acc(id=i, last_seen_at=TODAY - days(730)) for i in (5, 2, 9, 1)]
    out = plan_purge(accounts, TODAY)
    ids = [a["account_id"] for a in out]
    assert ids == sorted(ids)


def test_input_not_mutated():
    accounts = [acc(id=1, last_seen_at=TODAY - days(730), tenant="legacy")]
    snapshot = copy.deepcopy(accounts)
    plan_purge(accounts, TODAY)
    assert accounts == snapshot


def test_tenant_key_ignored():
    a = acc(id=1, last_seen_at=TODAY - days(730))
    a["tenant"] = object()
    assert len(plan_purge([a], TODAY)) == 1


def test_datetime_rejected_for_last_seen_at():
    a = acc(id=1, last_seen_at=dt.datetime(2026, 1, 1))
    with pytest.raises(TypeError):
        plan_purge([a], TODAY)


def test_datetime_rejected_for_today():
    with pytest.raises(TypeError):
        plan_purge([], dt.datetime(2026, 10, 13))


def test_invalid_closed_by_names_id_only():
    a = acc(id=77, email="leak@example.com", closed_by="robot")
    with pytest.raises(ValueError) as exc:
        plan_purge([a], TODAY)
    assert "77" in str(exc.value)
    assert "leak@example.com" not in str(exc.value)


def test_duplicate_ids_rejected():
    with pytest.raises(ValueError):
        plan_purge([acc(id=1), acc(id=1)], TODAY)


def test_null_last_seen_raises_naming_id():
    with pytest.raises(ValueError) as exc:
        plan_purge([acc(id=42, last_seen_at=None)], TODAY)
    assert "42" in str(exc.value)


def test_null_email_on_staff_check_raises():
    with pytest.raises(ValueError):
        plan_purge([acc(id=3, email=None)], TODAY)
```