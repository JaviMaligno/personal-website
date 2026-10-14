"""GDPR clean-up planner for Tidewater Climbing member accounts.

ESCALATE items for tech lead confirmation (defaults implemented):
(a) CAP_APPLIES_TO = "delete": the 200 cap counts deletes only. Anonymise and
    warn actions are not capped. The stated reason is database locking, so the
    client may want anonymise writes capped too.
(b) closed_by values other than "member" and "staff" are treated as staff-closed,
    so a warn is issued.
(c) closed_by == "member" suppresses the warn. The brief also says "Warn them",
    which contradicts this. Default is no warn for member-closed accounts.
(d) Accounts with last_seen_at None and closed_at None are skipped and counted,
    as the brief says. Accounts with closed_at set and last_seen_at None use
    closed_at + 30 days.
(e) unpaid_invoices None is treated as 0.

Tests were not executed in this session (no tool access). Test file is below.
"""
from __future__ import annotations

import datetime as _dt
import logging
from collections.abc import Mapping

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
MAX_DELETIONS_PER_RUN = 200
CAP_APPLIES_TO = "delete"
DPO_APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"

_log = logging.getLogger(__name__)


def _is_staff(account):
    email = account.get("email")
    return isinstance(email, str) and email.lower().endswith(STAFF_EMAIL_SUFFIX)


def _is_closed(account):
    return account.get("closed_at") is not None


def _due_date(account):
    candidates = []
    last_seen = account.get("last_seen_at")
    closed = account.get("closed_at")
    if last_seen is not None:
        candidates.append(last_seen + _dt.timedelta(days=INACTIVITY_DAYS))
    if closed is not None:
        candidates.append(closed + _dt.timedelta(days=CLOSED_GRACE_DAYS))
    return min(candidates) if candidates else None


def _check_date(account, key):
    value = account.get(key)
    if value is not None and (
        not isinstance(value, _dt.date) or isinstance(value, _dt.datetime)
    ):
        raise TypeError(
            f"{key} must be a datetime.date or None (account {account.get('id')!r})"
        )


def _unpaid(account):
    value = account.get("unpaid_invoices")
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"unpaid_invoices is not a count for account {account.get('id')!r}"
        ) from None


def _action(account_id, action, due, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def _plan(accounts, today):
    if not isinstance(today, _dt.date) or isinstance(today, _dt.datetime):
        raise TypeError("today must be a datetime.date")
    try:
        rows = list(accounts)
    except TypeError:
        raise TypeError("accounts must be an iterable of mappings") from None

    warn_limit = today + _dt.timedelta(days=WARN_WINDOW_DAYS)
    seen_ids = set()
    actions = []
    deletes = []  # (closed_rank, due, account_id); closed sorts first
    skipped = 0

    for account in rows:
        if not isinstance(account, Mapping):
            raise TypeError("each account must be a mapping")
        account_id = account.get("id")
        if account_id in seen_ids:
            raise ValueError(f"duplicate account id: {account_id!r}")
        seen_ids.add(account_id)

        _check_date(account, "last_seen_at")
        _check_date(account, "closed_at")

        if _is_staff(account):
            continue
        if account.get("litigation_hold"):
            continue

        unpaid = _unpaid(account)
        due = _due_date(account)
        if due is None:
            skipped += 1
            continue

        if due <= today:
            if unpaid > 0:
                actions.append(_action(account_id, "anonymise", due, DPO_APPROVER))
            else:
                rank = 0 if _is_closed(account) else 1
                deletes.append((rank, due, account_id))
        elif due <= warn_limit:
            if account.get("closed_by") == "member":
                continue
            actions.append(_action(account_id, "warn", due, None))

    deletes.sort()
    kept = deletes[:MAX_DELETIONS_PER_RUN]
    omitted = len(deletes) - len(kept)
    for _rank, due, account_id in kept:
        actions.append(_action(account_id, "delete", due, DPO_APPROVER))

    actions.sort(key=lambda a: a["account_id"])
    _log.info(
        "purge plan: %d skipped (no usable date), %d omitted by delete cap",
        skipped,
        omitted,
    )
    return actions, skipped


def plan_purge(accounts, today):
    actions, _skipped = _plan(accounts, today)
    return actions


def count_skipped(accounts, today):
    _actions, skipped = _plan(accounts, today)
    return skipped


# ===== test_purge.py (place next to purge.py and run pytest from that directory) =====
import datetime as dt
import logging

import pytest

from purge import count_skipped, plan_purge

T = dt.date(2026, 10, 13)
DPO = "Þórdís Sveinbjörnsdóttir"


def acc(i, last_seen=None, closed=None, closed_by="staff", unpaid=0, hold=False,
        email=None, **extra):
    a = {
        "id": i,
        "email": email if email is not None else f"member{i}@example.com",
        "status": "active",
        "last_seen_at": last_seen,
        "last_login": None,
        "closed_at": closed,
        "closed_by": closed_by,
        "unpaid_invoices": unpaid,
        "litigation_hold": hold,
        "tenant": "tw",
    }
    a.update(extra)
    return a


def seen_for_due(offset):
    """last_seen_at such that the inactivity due date is T + offset days."""
    return T + dt.timedelta(days=offset - 730)


def test_empty_input():
    assert plan_purge([], T) == []


def test_cap_exactly_200():
    accounts = [acc(i, last_seen=seen_for_due(0)) for i in range(1, 201)]
    out = plan_purge(accounts, T)
    assert len(out) == 200
    assert all(a["action"] == "delete" for a in out)


def test_cap_201_omits_latest_ordered():
    accounts = [acc(i, last_seen=seen_for_due(0)) for i in range(1, 202)]
    out = plan_purge(accounts, T)
    ids = [a["account_id"] for a in out]
    assert ids == list(range(1, 201))
    assert 201 not in ids


def test_closed_first_across_cap():
    inactive = [acc(i, last_seen=seen_for_due(i - 150)) for i in range(1, 151)]
    closed = [
        acc(1000 + k, closed=T - dt.timedelta(days=30 + k), closed_by="member")
        for k in range(100)
    ]
    out = plan_purge(inactive + closed, T)
    deletes = {a["account_id"] for a in out if a["action"] == "delete"}
    assert len(out) == 200
    assert {1000 + k for k in range(100)} <= deletes
    assert deletes & set(range(1, 151)) == set(range(1, 101))


def test_tiebreak_closed_same_due_by_id():
    accounts = [
        acc(9, closed=T - dt.timedelta(days=30), closed_by="member"),
        acc(2, closed=T - dt.timedelta(days=30), closed_by="member"),
    ]
    out = plan_purge(accounts, T)
    assert [a["account_id"] for a in out] == [2, 9]


def test_closed_earlier_than_inactivity_wins():
    a = acc(1, last_seen=T - dt.timedelta(days=700), closed=T - dt.timedelta(days=20))
    out = plan_purge([a], T)
    assert out == [{
        "account_id": 1,
        "action": "warn",
        "due": (T + dt.timedelta(days=10)).isoformat(),
        "approved_by": None,
    }]


def test_overdue_keeps_original_due():
    a = acc(1, last_seen=T - dt.timedelta(days=800))
    out = plan_purge([a], T)
    assert out == [{
        "account_id": 1,
        "action": "delete",
        "due": (T - dt.timedelta(days=70)).isoformat(),
        "approved_by": DPO,
    }]


@pytest.mark.parametrize("offset,expected", [
    (14, "warn"), (15, None), (1, "warn"), (0, "delete"), (-1, "delete"),
])
def test_warn_and_due_boundaries(offset, expected):
    out = plan_purge([acc(1, last_seen=seen_for_due(offset))], T)
    if expected is None:
        assert out == []
    else:
        assert [a["action"] for a in out] == [expected]


def test_member_closed_no_warn_in_window():
    a = acc(1, closed=T - dt.timedelta(days=20), closed_by="member")
    assert plan_purge([a], T) == []


def test_staff_closed_warns_in_window():
    a = acc(1, closed=T - dt.timedelta(days=20), closed_by="staff")
    out = plan_purge([a], T)
    assert [x["action"] for x in out] == ["warn"]


def test_member_closed_due_now_still_deleted():
    a = acc(1, closed=T - dt.timedelta(days=30), closed_by="member")
    out = plan_purge([a], T)
    assert [x["action"] for x in out] == ["delete"]


def test_unpaid_due_is_anonymised_and_approved():
    out = plan_purge([acc(1, last_seen=seen_for_due(0), unpaid=2)], T)
    assert out[0]["action"] == "anonymise"
    assert out[0]["approved_by"] == DPO


def test_unpaid_in_window_warns_without_approver():
    out = plan_purge([acc(1, last_seen=seen_for_due(5), unpaid=2)], T)
    assert out[0]["action"] == "warn"
    assert out[0]["approved_by"] is None


def test_anonymise_not_counted_toward_cap():
    accounts = (
        [acc(i, last_seen=seen_for_due(0)) for i in range(1, 201)]
        + [acc(i, last_seen=seen_for_due(0), unpaid=1) for i in range(201, 401)]
    )
    out = plan_purge(accounts, T)
    actions = [a["action"] for a in out]
    assert actions.count("delete") == 200
    assert actions.count("anonymise") == 200


def test_held_accounts_consume_no_cap_slots():
    accounts = (
        [acc(i, last_seen=seen_for_due(0), hold=True) for i in range(1, 201)]
        + [acc(i, last_seen=seen_for_due(0)) for i in range(201, 401)]
    )
    out = plan_purge(accounts, T)
    assert {a["account_id"] for a in out} == set(range(201, 401))


def test_held_in_window_gets_no_action():
    out = plan_purge([acc(1, last_seen=seen_for_due(5), hold=True)], T)
    assert out == []


@pytest.mark.parametrize("email", [
    "m@Tidewater-Klatring.NO",
    "x@tidewater-klatring.no",
])
def test_staff_excluded(email):
    accounts = [acc(1, last_seen=seen_for_due(0), email=email)]
    assert plan_purge(accounts, T) == []
    assert count_skipped(accounts, T) == 0


@pytest.mark.parametrize("email", [
    "x@tidewater-klatring.no.example.com",
    "x@tidewater-klatring.nope",
])
def test_lookalike_domains_are_not_staff(email):
    out = plan_purge([acc(1, last_seen=seen_for_due(0), email=email)], T)
    assert [a["action"] for a in out] == ["delete"]


def test_missing_last_seen_uses_closed_at():
    a = acc(1, last_seen=None, closed=T - dt.timedelta(days=30), closed_by="member")
    out = plan_purge([a], T)
    assert out == [{
        "account_id": 1,
        "action": "delete",
        "due": T.isoformat(),
        "approved_by": DPO,
    }]


def test_missing_both_dates_is_skipped_and_counted():
    accounts = [acc(1), acc(2, last_seen=seen_for_due(0))]
    out = plan_purge(accounts, T)
    assert [a["account_id"] for a in out] == [2]
    assert count_skipped(accounts, T) == 1


def test_output_shape_sorted_and_typed():
    accounts = [
        acc(3, last_seen=seen_for_due(0)),
        acc(1, last_seen=seen_for_due(0)),
        acc(2, last_seen=seen_for_due(5)),
    ]
    out = plan_purge(accounts, T)
    assert [a["account_id"] for a in out] == [1, 2, 3]
    assert set(out[0]) == {"account_id", "action", "due", "approved_by"}
    assert isinstance(out[0]["due"], str)
    assert out[0]["approved_by"] == DPO
    assert out[1]["action"] == "warn"
    assert out[1]["approved_by"] is None


def test_tenant_and_last_login_make_no_difference():
    base = [acc(1, last_seen=seen_for_due(0)), acc(2, last_seen=seen_for_due(5))]
    with_extra = [dict(a, tenant="other", last_login=T) for a in base]
    without = [{k: v for k, v in a.items() if k not in ("tenant", "last_login")} for a in base]
    assert plan_purge(base, T) == plan_purge(with_extra, T) == plan_purge(without, T)


def test_no_email_leak(caplog):
    caplog.set_level(logging.DEBUG)
    emails = ["alice@example.com", "bob@example.com", "carol@example.com", "dan@example.com"]
    accounts = [
        acc(1, last_seen=seen_for_due(0), email=emails[0]),
        acc(2, last_seen=seen_for_due(5), email=emails[1]),
        acc(3, last_seen=seen_for_due(0), hold=True, email=emails[2]),
        acc(4, last_seen=seen_for_due(0), unpaid=1, email=emails[3]),
    ]
    out = plan_purge(accounts, T)
    count_skipped(accounts, T)
    text = repr(out) + caplog.text
    for e in emails:
        assert e not in text


def test_exception_messages_contain_no_email():
    accounts = [
        acc(1, last_seen=seen_for_due(0), email="eve@example.com"),
        acc(1, last_seen=seen_for_due(0), email="eve2@example.com"),
    ]
    with pytest.raises(ValueError) as exc:
        plan_purge(accounts, T)
    assert "eve" not in str(exc.value)


def test_today_must_be_date_not_datetime():
    with pytest.raises(TypeError):
        plan_purge([], dt.datetime(2026, 10, 13))