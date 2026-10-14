"""GDPR purge planner for Tidewater Climbing member accounts.

Entry point: plan_purge(accounts, today) -> list of action dicts.

Choices made where the client has not answered the PM's open questions:
- Effective due date is the earlier of last_seen_at + 730 days and, when closed_at is set, closed_at + 30 days. Closure applies to member and staff closures alike. Closing an account does not reset the inactivity clock.
- Due means effective due <= today (delete or anonymise today).
- Warn means today < effective due <= today + 14 days, inclusive at +14.
- Accounts with closed_by == "member" never receive a warn, whatever the reason they are due soon.
- Any truthy unpaid_invoices value means anonymise instead of delete. Zero, empty or False means delete.
- Anonymise is not a deletion and does not count toward the cap. The 200 cap applies to delete actions only.
- Deletion cap ordering: member-closed, then staff-closed, then inactive-only (not closed). Within each group, earliest effective due date first, then account id. Deletions beyond the cap get no action and are omitted from the output.
- litigation_hold true: no action of any kind. Staff accounts (email ends with @tidewater-klatring.no, case-insensitive): no action of any kind.
- Output dicts have exactly the keys account_id, action, due (ISO 8601 string), approved_by. approved_by is the DPO's name for delete and anonymise, and None for warn.
- Output is sorted by account_id ascending, after the cap is applied.
- Required fields are id, email, last_seen_at, closed_at, closed_by, unpaid_invoices and litigation_hold. The status, last_login and tenant fields are ignored. last_login is not used for any rule; last_seen_at is the inactivity clock.
- Malformed input (missing required field, non-date or datetime.datetime date field, closed_by outside the allowed values, non-string email, non-bool litigation_hold) raises ValueError naming the account id only. Email and other field values never appear in errors.
- The function is pure: no I/O, no logging.

Tests at the bottom use plain asserts and the standard library only. They run under pytest or directly with python -I.
"""

from datetime import date, datetime, timedelta

INACTIVITY_DAYS = 730
CLOSURE_DAYS = 30
WARN_DAYS = 14
MAX_DELETIONS = 200
DPO = "Þórdís Sveinbjörnsdóttir"
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"
REQUIRED_FIELDS = (
    "id", "email", "last_seen_at", "closed_at",
    "closed_by", "unpaid_invoices", "litigation_hold",
)


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _bad(acc):
    account_id = acc.get("id") if isinstance(acc, dict) else None
    raise ValueError(f"malformed account record: id={account_id!r}")


def _validate(acc):
    if not isinstance(acc, dict) or any(f not in acc for f in REQUIRED_FIELDS):
        _bad(acc)
    if acc["id"] is None or not isinstance(acc["email"], str):
        _bad(acc)
    if not _is_date(acc["last_seen_at"]):
        _bad(acc)
    closed_at = acc["closed_at"]
    if closed_at is not None and not _is_date(closed_at):
        _bad(acc)
    if not isinstance(acc["litigation_hold"], bool):
        _bad(acc)
    allowed = ("member", "staff") if closed_at is not None else (None, "member", "staff")
    if acc["closed_by"] not in allowed:
        _bad(acc)


def _is_staff(email):
    return email.lower().endswith(STAFF_EMAIL_SUFFIX)


def _effective_due(acc):
    due = acc["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
    if acc["closed_at"] is not None:
        due = min(due, acc["closed_at"] + timedelta(days=CLOSURE_DAYS))
    return due


def _delete_rank(acc):
    if acc["closed_at"] is None:
        return 2
    return 0 if acc["closed_by"] == "member" else 1


def plan_purge(accounts, today):
    if not _is_date(today):
        raise ValueError("today must be a datetime.date")
    rows = list(accounts)
    for acc in rows:
        _validate(acc)

    horizon = today + timedelta(days=WARN_DAYS)
    deletes, anonymises, warns = [], [], []
    for acc in rows:
        if acc["litigation_hold"] or _is_staff(acc["email"]):
            continue
        due = _effective_due(acc)
        if due <= today:
            if acc["unpaid_invoices"]:
                anonymises.append((acc["id"], due))
            else:
                deletes.append(((_delete_rank(acc), due, acc["id"]), acc["id"], due))
        elif due <= horizon and acc["closed_by"] != "member":
            warns.append((acc["id"], due))

    deletes.sort(key=lambda t: t[0])
    actions = [
        {"account_id": i, "action": "delete", "due": d.isoformat(), "approved_by": DPO}
        for _, i, d in deletes[:MAX_DELETIONS]
    ]
    actions += [
        {"account_id": i, "action": "anonymise", "due": d.isoformat(), "approved_by": DPO}
        for i, d in anonymises
    ]
    actions += [
        {"account_id": i, "action": "warn", "due": d.isoformat(), "approved_by": None}
        for i, d in warns
    ]
    actions.sort(key=lambda a: a["account_id"])
    return actions


# ---- tests (pytest-compatible, stdlib only) ----

TODAY = date(2026, 10, 13)


def _days(n):
    return timedelta(days=n)


def _acc(i, last_seen, closed_at=None, closed_by=None, unpaid=0, hold=False,
         email=None, last_login=None):
    return {
        "id": i,
        "email": email or f"member{i}@example.com",
        "status": "active",
        "last_seen_at": last_seen,
        "last_login": last_login,
        "closed_at": closed_at,
        "closed_by": closed_by,
        "unpaid_invoices": unpaid,
        "litigation_hold": hold,
    }


def _malformed_message(row):
    try:
        plan_purge([row], TODAY)
    except ValueError as exc:
        return str(exc)
    raise AssertionError("expected ValueError")


def test_inactive_due_today_is_deleted():
    out = plan_purge([_acc(1, TODAY - _days(730))], TODAY)
    assert out == [{"account_id": 1, "action": "delete",
                    "due": TODAY.isoformat(), "approved_by": DPO}]


def test_warn_window_inclusive_at_14_days():
    rows = [_acc(1, TODAY + _days(14) - _days(730)),
            _acc(2, TODAY + _days(15) - _days(730))]
    out = plan_purge(rows, TODAY)
    assert out == [{"account_id": 1, "action": "warn",
                    "due": (TODAY + _days(14)).isoformat(), "approved_by": None}]


def test_closure_sooner_than_inactivity_deletes():
    row = _acc(1, TODAY - _days(1), closed_at=TODAY - _days(30), closed_by="staff")
    out = plan_purge([row], TODAY)
    assert len(out) == 1 and out[0]["action"] == "delete"
    assert out[0]["due"] == TODAY.isoformat()


def test_closure_does_not_reset_inactivity_clock():
    row = _acc(1, TODAY - _days(730), closed_at=TODAY, closed_by="member")
    out = plan_purge([row], TODAY)
    assert [a["action"] for a in out] == ["delete"]


def test_member_closed_never_warned():
    row = _acc(1, TODAY, closed_at=TODAY - _days(17), closed_by="member")
    assert plan_purge([row], TODAY) == []


def test_staff_closed_is_warned():
    row = _acc(1, TODAY, closed_at=TODAY - _days(17), closed_by="staff")
    out = plan_purge([row], TODAY)
    assert out == [{"account_id": 1, "action": "warn",
                    "due": (TODAY + _days(13)).isoformat(), "approved_by": None}]


def test_unpaid_invoices_anonymise_instead_of_delete():
    rows = [_acc(1, TODAY - _days(730), unpaid=3),
            _acc(2, TODAY - _days(730), unpaid=0)]
    out = plan_purge(rows, TODAY)
    assert {a["account_id"]: a["action"] for a in out} == {1: "anonymise", 2: "delete"}
    assert all(a["approved_by"] == DPO for a in out)


def test_hold_and_staff_excluded_from_all_actions():
    old = TODAY - _days(800)
    rows = [
        _acc(1, old, hold=True),
        _acc(2, old, email="Ops@Tidewater-Klatring.NO"),
        _acc(3, old, closed_at=TODAY - _days(40), closed_by="member", hold=True),
        _acc(4, TODAY + _days(13) - _days(730), hold=True),
    ]
    assert plan_purge(rows, TODAY) == []


def test_cap_ordering_and_anonymise_not_counted():
    rows = []
    for k in range(10):
        rows.append(_acc(1 + k, TODAY, closed_at=TODAY - _days(30), closed_by="member"))
    for k in range(60):
        rows.append(_acc(100 + k, TODAY, closed_at=TODAY - _days(30), closed_by="staff"))
    for i in range(150):
        rows.append(_acc(1000 + i, TODAY - _days(730 + i)))
    for k in range(5):
        rows.append(_acc(5000 + k, TODAY - _days(730), unpaid=1))

    out = plan_purge(rows, TODAY)
    deletes = [a for a in out if a["action"] == "delete"]
    anon = [a for a in out if a["action"] == "anonymise"]
    assert len(deletes) == 200
    assert len(anon) == 5
    ids = {a["account_id"] for a in deletes}
    assert set(range(1, 11)) <= ids
    assert set(range(100, 160)) <= ids
    # Inactive group: earliest effective due kept first, so ids 1020..1149 survive.
    assert {i for i in ids if 1000 <= i < 2000} == set(range(1020, 1150))
    assert [a["account_id"] for a in out] == sorted(a["account_id"] for a in out)


def test_output_sorted_by_id_with_exact_keys():
    rows = [_acc(3, TODAY - _days(730)), _acc(1, TODAY - _days(730), unpaid=2),
            _acc(2, TODAY + _days(5) - _days(730))]
    out = plan_purge(rows, TODAY)
    assert [a["account_id"] for a in out] == [1, 2, 3]
    for a in out:
        assert set(a) == {"account_id", "action", "due", "approved_by"}


def test_tenant_and_last_login_are_ignored():
    row = _acc(1, TODAY - _days(730), last_login=date(2100, 1, 1))
    row["tenant"] = "legacy"
    out = plan_purge([row], TODAY)
    assert [a["action"] for a in out] == ["delete"]


def test_malformed_error_names_id_only():
    bad = _acc(42, TODAY, closed_by="other", email="secret.person@example.com")
    msg = _malformed_message(bad)
    assert "42" in msg
    assert "secret" not in msg and "example.com" not in msg


def test_datetime_instead_of_date_rejected():
    msg = _malformed_message(_acc(7, __import__("datetime").datetime(2026, 1, 1)))
    assert "7" in msg


def test_missing_field_rejected():
    row = _acc(8, TODAY)
    del row["closed_at"]
    assert "8" in _malformed_message(row)


def test_no_email_in_output():
    rows = [_acc(1, TODAY - _days(730), email="private.member@example.com"),
            _acc(2, TODAY + _days(5) - _days(730), email="other.member@example.com")]
    out = plan_purge(rows, TODAY)
    text = repr(out)
    assert "@" not in text
    assert "private.member" not in text and "other.member" not in text


if __name__ == "__main__":
    for _name, _fn in list(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()