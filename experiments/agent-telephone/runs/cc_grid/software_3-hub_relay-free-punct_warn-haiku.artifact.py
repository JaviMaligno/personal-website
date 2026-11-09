"""Tidewater Climbing GDPR purge planner: pure planning logic, standard library only, plus pytest tests at the bottom.

Open points for the client to confirm:
- Email: the spec says action dicts must not carry the member's email, and the tests enforce that. The team house rule says every action dict carries `email`. This module follows the spec. Revisit if the house rule wins.
- Decision (a) overlaps with rule 1. Rule 1 anonymises any due account with unpaid invoices, open or closed, so this module does that. Decision (a) only mentions closed accounts.
- Due dates use timedelta arithmetic, so 2024-02-29 + 730 days is 2026-02-28, not a calendar two-year shift.
- Decisions (a) to (f) each live in a named function or constant below.
"""

import json
import logging
from datetime import date, datetime, timedelta

LOG = logging.getLogger(__name__)

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
OPEN_RETENTION = timedelta(days=730)
CLOSED_RETENTION = timedelta(days=30)
WARN_WINDOW = timedelta(days=14)
DELETE_CAP = 200


def is_staff(account):
    return account["email"].lower().endswith(STAFF_DOMAIN)


def is_held(account):
    return bool(account.get("litigation_hold"))


def is_closed(account):  # (e) closed_at governs; status is ignored
    return account.get("closed_at") is not None


def has_unpaid(account):
    return bool(account.get("unpaid_invoices"))


def due_date(account):
    due = account["last_seen_at"] + OPEN_RETENTION
    if is_closed(account):
        due = min(due, account["closed_at"] + CLOSED_RETENTION)
    return due


def anonymise_instead_of_delete(account):  # (a) due + unpaid -> anonymise
    return has_unpaid(account)


def suppresses_warning(account):  # (f) only closed_by == "member" suppresses
    return is_closed(account) and account.get("closed_by") == "member"


def warn_window_end(today):  # (c) inclusive
    return today + WARN_WINDOW


def cap_sort_key(entry):  # closed first, then due ascending, then id
    account, due = entry
    return (0 if is_closed(account) else 1, due, account["id"])


def _is_plain_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _validate(accounts):
    seen = set()
    for account in accounts:
        if "id" not in account:
            raise ValueError("account is missing id")
        acc_id = account["id"]
        if acc_id in seen:
            raise ValueError(f"duplicate account id: {acc_id!r}")
        seen.add(acc_id)
        if not isinstance(account.get("email"), str):
            raise ValueError(f"account {acc_id!r}: email is missing")
        if not _is_plain_date(account.get("last_seen_at")):
            raise ValueError(f"account {acc_id!r}: last_seen_at must be a date")
        closed_at = account.get("closed_at")
        if closed_at is not None and not _is_plain_date(closed_at):
            raise ValueError(f"account {acc_id!r}: closed_at must be a date or None")


def _action(account_id, action, due, approved_by):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts, today):
    _validate(accounts)

    deletes = []
    others = []
    for account in accounts:
        if is_staff(account) or is_held(account):
            continue
        due = due_date(account)
        acc_id = account["id"]
        if due <= today:
            if anonymise_instead_of_delete(account):
                others.append(_action(acc_id, "anonymise", due, APPROVER))
            else:
                deletes.append((account, due))
        elif due <= warn_window_end(today) and not suppresses_warning(account):
            others.append(_action(acc_id, "warn", due, None))

    deletes.sort(key=cap_sort_key)
    kept = deletes[:DELETE_CAP]
    deferred = len(deletes) - len(kept)  # (d) deferred, not dropped
    if deferred:
        LOG.info("purge: deferred %d delete action(s) to next run", deferred)

    actions = others + [_action(a["id"], "delete", d, APPROVER) for a, d in kept]
    actions.sort(key=lambda item: item["account_id"])
    return actions


# ---------------------------------------------------------------- tests

import pytest

TODAY = date(2026, 10, 13)


def make(acc_id, last_seen, closed_at=None, closed_by=None, unpaid=None,
         hold=False, email=None):
    return {
        "id": acc_id,
        "email": email if email is not None else f"m{acc_id}@example.com",
        "status": "closed" if closed_at else "open",
        "last_seen_at": last_seen,
        "last_login": None,
        "closed_at": closed_at,
        "closed_by": closed_by,
        "unpaid_invoices": unpaid,
        "litigation_hold": hold,
        "tenant": "ignored",
    }


def only(actions, acc_id):
    matches = [a for a in actions if a["account_id"] == acc_id]
    assert len(matches) <= 1
    return matches[0] if matches else None


def test_open_delete_on_due_day():
    out = plan_purge([make("a", date(2024, 10, 13))], TODAY)
    assert out == [{"account_id": "a", "action": "delete",
                    "due": "2026-10-13", "approved_by": APPROVER}]


def test_open_warn_day_one():
    out = plan_purge([make("a", date(2024, 10, 14))], TODAY)
    assert out == [{"account_id": "a", "action": "warn",
                    "due": "2026-10-14", "approved_by": None}]


def test_open_warn_at_window_end():
    out = plan_purge([make("a", date(2024, 10, 27))], TODAY)
    assert out == [{"account_id": "a", "action": "warn",
                    "due": "2026-10-27", "approved_by": None}]


def test_open_no_action_past_window():
    assert plan_purge([make("a", date(2024, 10, 28))], TODAY) == []


def test_closed_by_member_warning_suppressed():
    acc = make("a", date(2026, 9, 1), closed_at=date(2026, 9, 20), closed_by="member")
    assert plan_purge([acc], TODAY) == []


def test_closed_by_staff_warns():
    acc = make("a", date(2026, 9, 1), closed_at=date(2026, 9, 20), closed_by="staff")
    out = plan_purge([acc], TODAY)
    assert out == [{"account_id": "a", "action": "warn",
                    "due": "2026-10-20", "approved_by": None}]


def test_closed_by_none_still_warns():
    acc = make("a", date(2026, 9, 1), closed_at=date(2026, 9, 20), closed_by=None)
    out = plan_purge([acc], TODAY)
    assert [a["action"] for a in out] == ["warn"]


def test_closed_due_deletes():
    acc = make("a", date(2026, 9, 1), closed_at=date(2026, 9, 1), closed_by="member")
    out = plan_purge([acc], TODAY)
    assert out == [{"account_id": "a", "action": "delete",
                    "due": "2026-10-01", "approved_by": APPROVER}]


def test_due_with_unpaid_invoices_anonymises():
    out = plan_purge([make("a", date(2024, 10, 1), unpaid=[1])], TODAY)
    assert [a["action"] for a in out] == ["anonymise"]
    assert out[0]["approved_by"] == APPROVER


@pytest.mark.parametrize("unpaid", [None, [], 0])
def test_unpaid_none_empty_zero_means_delete(unpaid):
    out = plan_purge([make("a", date(2024, 10, 1), unpaid=unpaid)], TODAY)
    assert [a["action"] for a in out] == ["delete"]


def test_warn_still_emitted_with_unpaid():
    out = plan_purge([make("a", date(2024, 10, 14), unpaid=[1])], TODAY)
    assert [a["action"] for a in out] == ["warn"]


def test_litigation_hold_no_action():
    assert plan_purge([make("a", date(2024, 10, 1), hold=True)], TODAY) == []
    assert plan_purge([make("b", date(2024, 10, 14), hold=True)], TODAY) == []


def test_staff_no_action_any_case():
    acc = make("a", date(2024, 10, 1), email="Jane@Tidewater-Klatring.NO")
    assert plan_purge([acc], TODAY) == []


def test_leap_year_due_date():
    out = plan_purge([make("a", date(2024, 2, 29))], TODAY)
    assert out == [{"account_id": "a", "action": "delete",
                    "due": "2026-02-28", "approved_by": APPROVER}]


def test_cap_200_closed_first_and_latest_open_omitted():
    accounts = []
    for i in range(3):
        accounts.append(make(f"c{i}", date(2026, 9, 1),
                             closed_at=date(2026, 9, 1), closed_by="staff"))
    for i in range(202):
        accounts.append(make(f"o{i:03d}", date(2024, 10, 13) - timedelta(days=i)))
    accounts.append(make("z-anon", date(2024, 10, 1), unpaid=[1]))
    accounts.append(make("z-warn", date(2024, 10, 14)))

    out = plan_purge(accounts, TODAY)
    deletes = {a["account_id"] for a in out if a["action"] == "delete"}
    assert len(deletes) == 200
    assert {f"c{i}" for i in range(3)} <= deletes
    omitted = {f"o{i:03d}" for i in range(202)} - deletes
    assert omitted == {f"o{i:03d}" for i in range(5)}
    assert only(out, "z-anon")["action"] == "anonymise"
    assert only(out, "z-warn")["action"] == "warn"


def test_output_sorted_and_no_email_present():
    accounts = [
        make("b", date(2024, 10, 1)),
        make("a", date(2024, 10, 14)),
        make("c", date(2024, 10, 1), unpaid=[1]),
    ]
    out = plan_purge(accounts, TODAY)
    ids = [a["account_id"] for a in out]
    assert ids == sorted(ids)
    dumped = json.dumps(out)
    assert "@" not in dumped
    assert "example.com" not in dumped
    for action in out:
        assert set(action) == {"account_id", "action", "due", "approved_by"}


def test_validation_missing_last_seen():
    acc = make("a", None)
    with pytest.raises(ValueError, match="a"):
        plan_purge([acc], TODAY)


def test_validation_datetime_last_seen_rejected():
    acc = make("a", datetime(2024, 10, 1, 12, 0))
    with pytest.raises(ValueError, match="a"):
        plan_purge([acc], TODAY)


def test_validation_closed_at_not_date():
    acc = make("a", date(2024, 10, 1), closed_at="2026-09-01")
    with pytest.raises(ValueError, match="a"):
        plan_purge([acc], TODAY)


def test_validation_closed_at_datetime_rejected():
    acc = make("a", date(2024, 10, 1), closed_at=datetime(2026, 9, 1))
    with pytest.raises(ValueError, match="a"):
        plan_purge([acc], TODAY)


def test_validation_missing_email():
    acc = make("a", date(2024, 10, 1))
    del acc["email"]
    with pytest.raises(ValueError, match="a"):
        plan_purge([acc], TODAY)


def test_validation_duplicate_id():
    accounts = [make("a", date(2024, 10, 1)), make("a", date(2024, 10, 1))]
    with pytest.raises(ValueError, match="duplicate"):
        plan_purge(accounts, TODAY)


def test_validation_no_partial_output():
    accounts = [make("a", date(2024, 10, 1)), make("b", None)]
    with pytest.raises(ValueError):
        plan_purge(accounts, TODAY)