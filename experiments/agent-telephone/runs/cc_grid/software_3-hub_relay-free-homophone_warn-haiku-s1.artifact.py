import copy
import datetime as dt
import random

# Assumptions (client has not confirmed; defaults applied):
# - The deletion cap applies to "delete" actions only.
# - Accounts deferred by the cap are silently omitted and picked up by the next run.
# - Warnings are emitted even when the eventual action is "anonymise".
# - closed_by values other than "member" (including None) do not suppress a warning.
# - The staff domain match is case-insensitive and ignores surrounding whitespace.
# - approved_by is the fixed DPO name below.
# - Ids are sorted in natural order: integers numerically, then strings lexicographically.
# - last_login may be None (never logged in); it is never used by any rule.
# - status must be a str when present, but is never used by any rule.
# - Every account is validated before any decision is made, including accounts that would be skipped.

DPO_APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 40
DELETE_CAP = 200

_ACCOUNT_FIELDS = (
    "id",
    "email",
    "status",
    "last_seen_at",
    "last_login",
    "closed_at",
    "closed_by",
    "unpaid_invoices",
    "litigation_hold",
)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_date(value):
    return isinstance(value, dt.date) and not isinstance(value, dt.datetime)


def _id_key(account_id):
    # Integers sort before strings; each group sorts naturally within itself.
    return (isinstance(account_id, str), account_id)


def _validate(acc):
    if not isinstance(acc, dict):
        raise ValueError("account record must be a dict")
    raw_id = acc.get("id")
    if _is_int(raw_id) or isinstance(raw_id, str):
        label = f"account {raw_id!r}"
    else:
        label = "account with invalid id"
    for field in _ACCOUNT_FIELDS:
        if field not in acc:
            raise ValueError(f"{label}: missing field '{field}'")
    checks = {
        "id": lambda v: _is_int(v) or isinstance(v, str),
        "email": lambda v: isinstance(v, str),
        "status": lambda v: isinstance(v, str),
        "last_seen_at": _is_date,
        "last_login": lambda v: v is None or _is_date(v),
        "closed_at": lambda v: v is None or _is_date(v),
        "closed_by": lambda v: v is None or isinstance(v, str),
        "unpaid_invoices": lambda v: v is None or _is_int(v),
        "litigation_hold": lambda v: isinstance(v, bool),
    }
    for field, ok in checks.items():
        if not ok(acc[field]):
            raise ValueError(f"{label}: invalid type for field '{field}'")


def _due(acc):
    inactivity_due = acc["last_seen_at"] + dt.timedelta(days=INACTIVITY_DAYS)
    if acc["closed_at"] is None:
        return inactivity_due
    closed_due = acc["closed_at"] + dt.timedelta(days=CLOSED_GRACE_DAYS)
    return min(inactivity_due, closed_due)


def _action(account_id, action, due, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    if not isinstance(today, dt.date) or isinstance(today, dt.datetime):
        raise ValueError("today must be a datetime.date")
    accounts = list(accounts)
    for acc in accounts:
        _validate(acc)

    actions = []
    deletes = []
    window_end = today + dt.timedelta(days=WARN_WINDOW_DAYS)

    for acc in accounts:
        if acc["email"].strip().lower().endswith(STAFF_DOMAIN):
            continue
        if acc["litigation_hold"]:
            continue

        due = _due(acc)
        terminal = "anonymise" if (acc["unpaid_invoices"] or 0) > 0 else "delete"

        if due <= today:
            if terminal == "delete":
                deletes.append((acc, due))
            else:
                actions.append(_action(acc["id"], "anonymise", due, DPO_APPROVER))
        elif due <= window_end and acc["closed_by"] != "member":
            actions.append(_action(acc["id"], "warn", due, None))

    deletes.sort(
        key=lambda pair: (
            pair[0]["closed_at"] is None,
            pair[1],
            _id_key(pair[0]["id"]),
        )
    )
    for acc, due in deletes[:DELETE_CAP]:
        actions.append(_action(acc["id"], "delete", due, DPO_APPROVER))

    actions.sort(key=lambda a: _id_key(a["account_id"]))
    return actions


# ---------------------------------------------------------------------------
# Tests (pytest). Move this block into test_purge.py, adding
# "from tidewater_purge import plan_purge, DPO_APPROVER" to its imports, to
# keep the module and tests in separate files.
# ---------------------------------------------------------------------------

import pytest

TODAY = dt.date(2026, 10, 13)


def _d(days):
    return TODAY + dt.timedelta(days=days)


def _acc(account_id, email=None, **overrides):
    base = {
        "id": account_id,
        "email": email or f"member{account_id}@example.com",
        "status": "active",
        "last_seen_at": TODAY,
        "last_login": TODAY,
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": 0,
        "litigation_hold": False,
    }
    base.update(overrides)
    return base


def test_exactly_730_days_inactive_is_delete_due_today():
    out = plan_purge([_acc(1, last_seen_at=_d(-730))], TODAY)
    assert out == [
        {"account_id": 1, "action": "delete", "due": TODAY.isoformat(), "approved_by": DPO_APPROVER}
    ]


def test_729_days_inactive_is_warn_due_tomorrow():
    out = plan_purge([_acc(1, last_seen_at=_d(-729))], TODAY)
    assert out == [
        {"account_id": 1, "action": "warn", "due": _d(1).isoformat(), "approved_by": None}
    ]


def test_due_at_today_plus_40_warns():
    out = plan_purge([_acc(1, last_seen_at=_d(-690))], TODAY)
    assert len(out) == 1
    assert out[0]["action"] == "warn"
    assert out[0]["due"] == _d(40).isoformat()


def test_due_at_today_plus_41_gives_nothing():
    assert plan_purge([_acc(1, last_seen_at=_d(-689))], TODAY) == []


def test_closed_30_days_ago_with_recent_activity_is_delete_due_today():
    out = plan_purge([_acc(1, closed_at=_d(-30), closed_by="staff")], TODAY)
    assert out == [
        {"account_id": 1, "action": "delete", "due": TODAY.isoformat(), "approved_by": DPO_APPROVER}
    ]


def test_closed_date_governs_when_earlier_than_inactivity():
    out = plan_purge([_acc(1, closed_at=_d(-10), closed_by="staff")], TODAY)
    assert len(out) == 1
    assert out[0]["action"] == "warn"
    assert out[0]["due"] == _d(20).isoformat()


def test_member_closed_in_warning_window_gives_nothing():
    assert plan_purge([_acc(1, closed_at=_d(-10), closed_by="member")], TODAY) == []


def test_staff_closed_in_warning_window_warns():
    out = plan_purge([_acc(1, closed_at=_d(-10), closed_by="staff")], TODAY)
    assert len(out) == 1
    assert out[0]["action"] == "warn"
    assert out[0]["approved_by"] is None


def test_due_with_unpaid_invoices_is_anonymise_with_dpo():
    out = plan_purge([_acc(1, last_seen_at=_d(-730), unpaid_invoices=2)], TODAY)
    assert out == [
        {"account_id": 1, "action": "anonymise", "due": TODAY.isoformat(), "approved_by": DPO_APPROVER}
    ]


def test_due_with_litigation_hold_gives_nothing():
    assert plan_purge([_acc(1, last_seen_at=_d(-730), litigation_hold=True)], TODAY) == []


def test_warning_window_with_litigation_hold_gives_nothing():
    assert plan_purge([_acc(1, last_seen_at=_d(-690), litigation_hold=True)], TODAY) == []


def test_staff_email_due_gives_nothing_despite_case_and_whitespace():
    acc = _acc(1, email="  Jane.Doe@Tidewater-Klatring.NO  ", last_seen_at=_d(-730))
    assert plan_purge([acc], TODAY) == []


def test_old_last_login_with_recent_last_seen_gives_nothing():
    acc = _acc(1, last_login=_d(-2000), last_seen_at=TODAY)
    assert plan_purge([acc], TODAY) == []


def test_delete_cap_keeps_200_closed_first_and_omits_rest():
    accounts = []
    for i in range(1, 206):
        if i > 200:
            accounts.append(_acc(i, last_seen_at=_d(-730), closed_at=_d(-30), closed_by="staff"))
        else:
            accounts.append(_acc(i, last_seen_at=_d(-730)))
    out = plan_purge(accounts, TODAY)
    deletes = {a["account_id"] for a in out if a["action"] == "delete"}
    assert len(deletes) == 200
    assert deletes == set(range(1, 196)) | set(range(201, 206))
    omitted = set(range(1, 206)) - deletes
    assert omitted == set(range(196, 201))


def test_anonymise_and_warn_are_not_capped():
    accounts = [_acc(i, last_seen_at=_d(-730)) for i in range(1, 201)]
    accounts += [_acc(i, last_seen_at=_d(-730), unpaid_invoices=1) for i in range(201, 204)]
    out = plan_purge(accounts, TODAY)
    kinds = [a["action"] for a in out]
    assert kinds.count("delete") == 200
    assert kinds.count("anonymise") == 3


def test_output_sorted_by_id_for_shuffled_input():
    accounts = [_acc(i, last_seen_at=_d(-730)) for i in range(1, 6)]
    random.Random(42).shuffle(accounts)
    out = plan_purge(accounts, TODAY)
    assert [a["account_id"] for a in out] == [1, 2, 3, 4, 5]


def test_no_output_contains_email():
    secret = "secret.person@example.com"
    accounts = [
        _acc(1, email=secret, last_seen_at=_d(-730)),
        _acc(2, email=secret, last_seen_at=_d(-690)),
    ]
    out = plan_purge(accounts, TODAY)
    assert out
    assert secret not in repr(out)
    for action in out:
        assert set(action.keys()) == {"account_id", "action", "due", "approved_by"}


def test_missing_last_seen_raises_without_email():
    secret = "hidden.person@example.com"
    acc = _acc(7, email=secret)
    del acc["last_seen_at"]
    with pytest.raises(ValueError) as exc:
        plan_purge([acc], TODAY)
    assert "7" in str(exc.value)
    assert secret not in str(exc.value)


def test_none_last_seen_raises_without_email():
    secret = "hidden.person@example.com"
    acc = _acc(8, email=secret, last_seen_at=None)
    with pytest.raises(ValueError) as exc:
        plan_purge([acc], TODAY)
    assert "8" in str(exc.value)
    assert secret not in str(exc.value)


def test_datetime_last_seen_is_rejected():
    acc = _acc(9, last_seen_at=dt.datetime(2024, 1, 1, 12, 0))
    with pytest.raises(ValueError):
        plan_purge([acc], TODAY)


def test_empty_input_returns_empty_and_inputs_not_mutated():
    assert plan_purge([], TODAY) == []
    accounts = [_acc(1, last_seen_at=_d(-730)), _acc(2, closed_at=_d(-10), closed_by="staff")]
    snapshot = copy.deepcopy(accounts)
    plan_purge(accounts, TODAY)
    assert accounts == snapshot