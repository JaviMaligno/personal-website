# file: purge.py
"""GDPR purge planning for member accounts.

Pure function: no I/O, no logging, no network. Standard library only.
"""

from datetime import date, datetime, timedelta

MAX_DELETIONS_PER_RUN = 200
DPO_APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _invalid(account_id, field):
    # Never include the email here: only the account id and the field name.
    return ValueError(f"account {account_id!r}: invalid or missing field {field!r}")


def _validate(acct):
    if not isinstance(acct, dict):
        raise ValueError("each account must be a dict")
    account_id = acct.get("id")
    if account_id is None:
        raise ValueError("account is missing field 'id'")
    try:
        hash(account_id)
    except TypeError:
        raise ValueError("account has an unhashable 'id'") from None
    if not _is_date(acct.get("last_seen_at")):
        raise _invalid(account_id, "last_seen_at")
    closed_at = acct.get("closed_at")
    if closed_at is not None and not _is_date(closed_at):
        raise _invalid(account_id, "closed_at")
    unpaid = acct.get("unpaid_invoices")
    if not isinstance(unpaid, int) or isinstance(unpaid, bool) or unpaid < 0:
        raise _invalid(account_id, "unpaid_invoices")
    return account_id


def _due(acct, account_id):
    # closed_by == "member" with closed_at None is treated as not closed for
    # due computation (closed-ness is decided by closed_at only). The warn
    # suppression for member requests is applied separately in plan_purge.
    try:
        candidates = [acct["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)]
        if acct.get("closed_at") is not None:
            candidates.append(acct["closed_at"] + timedelta(days=CLOSED_GRACE_DAYS))
    except OverflowError:
        raise _invalid(account_id, "last_seen_at or closed_at") from None
    return min(candidates)


def _row(account_id, action, due):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else DPO_APPROVER,
    }


def plan_purge(accounts, today):
    if not _is_date(today):
        raise ValueError("today must be a datetime.date")

    # Validate everything before producing any output: fail the whole call.
    seen_ids = set()
    prepared = []
    for acct in accounts:
        account_id = _validate(acct)
        if account_id in seen_ids:
            raise ValueError(f"duplicate account id {account_id!r}")
        seen_ids.add(account_id)
        prepared.append((acct, account_id))

    warn_until = today + timedelta(days=WARN_WINDOW_DAYS)
    results = []
    deletes = []  # (priority group, due, account_id) ; row built after capping

    for acct, account_id in prepared:
        email = acct.get("email")
        if isinstance(email, str) and email.strip().lower().endswith(STAFF_EMAIL_SUFFIX):
            continue
        if acct.get("litigation_hold") is True:
            continue

        due = _due(acct, account_id)
        if due <= today:
            if acct["unpaid_invoices"] > 0:
                results.append(_row(account_id, "anonymise", due))
            else:
                group = 0 if acct.get("closed_at") is not None else 1
                deletes.append((group, due, account_id))
        elif due <= warn_until:
            if acct.get("closed_by") == "member":
                continue
            results.append(_row(account_id, "warn", due))

    # Deletion cap: closed accounts first, then by due date, then by id.
    # Deferred deletes are not emitted and get no warn (they are already due).
    deletes.sort(key=lambda t: (t[0], t[1], t[2]))
    for _group, due, account_id in deletes[:MAX_DELETIONS_PER_RUN]:
        results.append(_row(account_id, "delete", due))

    results.sort(key=lambda r: r["account_id"])
    return results

# file: test_purge.py
# Note: the spec's test list says "due today+1 (no action)", but rule 4 makes
# due in (today, today+14] a warn. The rule was followed, and that case is
# tested as a warn.

import copy
from datetime import date, timedelta

import pytest

from purge import DPO_APPROVER, MAX_DELETIONS_PER_RUN, plan_purge

TODAY = date(2026, 10, 13)
DAY = timedelta(days=1)


def ago(days):
    return TODAY - timedelta(days=days)


def seen_for_due(due):
    return due - timedelta(days=730)


def make(aid, last_seen_at=TODAY, closed_at=None, closed_by=None,
         unpaid=0, hold=False, email=None):
    return {
        "id": aid,
        "email": email if email is not None else f"member{aid}@example.org",
        "status": "active",
        "last_seen_at": last_seen_at,
        "last_login": None,
        "closed_at": closed_at,
        "closed_by": closed_by,
        "unpaid_invoices": unpaid,
        "litigation_hold": hold,
        "tenant": "legacy",
    }


def run(*accounts):
    return plan_purge(list(accounts), TODAY)


def by_id(out):
    return {r["account_id"]: r for r in out}


def test_empty_input():
    assert plan_purge([], TODAY) == []


def test_inactive_due_exactly_today_deletes():
    out = run(make(1, last_seen_at=seen_for_due(TODAY)))
    assert out == [{"account_id": 1, "action": "delete",
                    "due": TODAY.isoformat(), "approved_by": DPO_APPROVER}]


def test_due_yesterday_deletes():
    out = run(make(2, last_seen_at=seen_for_due(TODAY - DAY)))
    assert len(out) == 1
    assert out[0]["action"] == "delete"
    assert out[0]["due"] == (TODAY - DAY).isoformat()


def test_due_tomorrow_warns():
    out = run(make(3, last_seen_at=seen_for_due(TODAY + DAY)))
    assert len(out) == 1
    assert out[0]["action"] == "warn"


def test_warn_at_today_plus_14_inclusive():
    out = run(make(4, last_seen_at=seen_for_due(TODAY + 14 * DAY)))
    assert len(out) == 1 and out[0]["action"] == "warn"


def test_no_warn_at_today_plus_15():
    assert run(make(5, last_seen_at=seen_for_due(TODAY + 15 * DAY))) == []


def test_warn_suppressed_for_closed_by_member():
    acct = make(6, last_seen_at=TODAY, closed_at=ago(20), closed_by="member")
    assert run(acct) == []


def test_member_close_without_closed_at_suppresses_warn():
    acct = make(7, last_seen_at=seen_for_due(TODAY + 5 * DAY), closed_by="member")
    assert run(acct) == []


def test_warn_emitted_for_closed_by_staff():
    acct = make(8, last_seen_at=TODAY, closed_at=ago(20), closed_by="staff")
    out = run(acct)
    assert len(out) == 1
    assert out[0]["action"] == "warn"
    assert out[0]["approved_by"] is None


def test_closed_date_used_when_earlier():
    # inactive due = TODAY+10, closed due = TODAY+5
    acct = make(9, last_seen_at=ago(720), closed_at=ago(25), closed_by="staff")
    out = run(acct)
    assert out[0]["due"] == (TODAY + 5 * DAY).isoformat()


def test_earlier_of_inactive_and_closed_used_when_inactive_is_earlier():
    # inactive due = TODAY+10, closed due = TODAY+20
    acct = make(10, last_seen_at=ago(720), closed_at=ago(10), closed_by="staff")
    out = run(acct)
    assert out[0]["due"] == (TODAY + 10 * DAY).isoformat()


def test_unpaid_due_account_anonymised_with_dpo():
    out = run(make(11, last_seen_at=seen_for_due(TODAY), unpaid=2))
    assert out == [{"account_id": 11, "action": "anonymise",
                    "due": TODAY.isoformat(), "approved_by": DPO_APPROVER}]


def test_unpaid_warn_window_account_gets_warn():
    out = run(make(12, last_seen_at=seen_for_due(TODAY + 3 * DAY), unpaid=1))
    assert len(out) == 1
    assert out[0]["action"] == "warn"
    assert out[0]["approved_by"] is None


@pytest.mark.parametrize("email", [
    "ops@tidewater-klatring.no",
    "Admin@TIDEWATER-KLATRING.NO",
    "  Staff@Tidewater-Klatring.no  ",
])
def test_staff_accounts_produce_no_output(email):
    assert run(make(13, last_seen_at=seen_for_due(TODAY), email=email)) == []
    assert run(make(14, last_seen_at=seen_for_due(TODAY + 2 * DAY), email=email)) == []


def test_litigation_hold_due_and_warn_produce_no_output():
    assert run(make(15, last_seen_at=seen_for_due(TODAY), hold=True)) == []
    assert run(make(16, last_seen_at=seen_for_due(TODAY + 5 * DAY), hold=True)) == []


def test_no_email_anywhere_in_output():
    secret = "secret.member@example.org"
    accounts = [
        make(20, last_seen_at=seen_for_due(TODAY), email=secret),
        make(21, last_seen_at=seen_for_due(TODAY), unpaid=1, email=secret),
        make(22, last_seen_at=seen_for_due(TODAY + 3 * DAY), email=secret),
    ]
    out = run(*accounts)
    assert len(out) == 3
    text = repr(out)
    assert "secret.member" not in text
    assert "example.org" not in text


def test_approved_by_per_action():
    out = by_id(run(
        make(30, last_seen_at=seen_for_due(TODAY)),
        make(31, last_seen_at=seen_for_due(TODAY), unpaid=1),
        make(32, last_seen_at=seen_for_due(TODAY + 2 * DAY)),
    ))
    assert out[30]["action"] == "delete" and out[30]["approved_by"] == DPO_APPROVER
    assert out[31]["action"] == "anonymise" and out[31]["approved_by"] == DPO_APPROVER
    assert out[32]["action"] == "warn" and out[32]["approved_by"] is None


def test_output_sorted_by_account_id():
    out = run(
        make(50, last_seen_at=seen_for_due(TODAY)),
        make(10, last_seen_at=seen_for_due(TODAY)),
        make(30, last_seen_at=seen_for_due(TODAY + 2 * DAY)),
    )
    assert [r["account_id"] for r in out] == [10, 30, 50]


def test_deletion_cap_closed_first_then_due_then_id():
    closed = [make(f"c{i:03d}", last_seen_at=ago(800),
                   closed_at=ago(40), closed_by="member") for i in range(60)]
    inactive = [make(f"i{i:03d}", last_seen_at=ago(800)) for i in range(240)]
    out = by_id(run(*(closed + inactive)))

    deleted = {aid for aid, r in out.items() if r["action"] == "delete"}
    assert len(deleted) == MAX_DELETIONS_PER_RUN == 200
    assert all(f"c{i:03d}" in deleted for i in range(60))
    assert all(f"i{i:03d}" in deleted for i in range(140))
    assert all(f"i{i:03d}" not in out for i in range(140, 240))


def test_cap_does_not_reduce_anonymise_or_warn():
    closed = [make(f"c{i:03d}", last_seen_at=ago(800),
                   closed_at=ago(40), closed_by="member") for i in range(60)]
    inactive = [make(f"i{i:03d}", last_seen_at=ago(800)) for i in range(190)]
    anon = [make(f"z{i}", last_seen_at=ago(800), unpaid=2) for i in range(1, 4)]
    warn = [make(f"w{i}", last_seen_at=seen_for_due(TODAY + DAY)) for i in range(1, 3)]
    out = run(*(closed + inactive + anon + warn))

    actions = [r["action"] for r in out]
    assert actions.count("delete") == 200
    assert actions.count("anonymise") == 3
    assert actions.count("warn") == 2


def test_due_values_are_iso_strings():
    out = run(
        make(40, last_seen_at=seen_for_due(TODAY)),
        make(41, last_seen_at=seen_for_due(TODAY + 4 * DAY)),
    )
    for r in out:
        assert isinstance(r["due"], str)
        assert date.fromisoformat(r["due"]) == date.fromisoformat(r["due"])
        assert set(r.keys()) == {"account_id", "action", "due", "approved_by"}


def test_input_not_mutated():
    accounts = [make(60, last_seen_at=seen_for_due(TODAY), closed_at=ago(5),
                     closed_by="staff", unpaid=1)]
    snapshot = copy.deepcopy(accounts)
    plan_purge(accounts, TODAY)
    assert accounts == snapshot


@pytest.mark.parametrize("field,value", [
    ("last_seen_at", None),
    ("last_seen_at", "2026-01-01"),
    ("last_seen_at", "2026-01-01T00:00:00"),
    ("last_seen_at", None),
    ("closed_at", "2026-01-01"),
    ("unpaid_invoices", -1),
    ("unpaid_invoices", "2"),
    ("unpaid_invoices", True),
    ("unpaid_invoices", None),
])
def test_invalid_fields_raise_without_email(field, value):
    secret = "secret.member@example.org"
    acct = make("acct-9", last_seen_at=seen_for_due(TODAY), email=secret)
    acct[field] = value
    with pytest.raises(ValueError) as exc:
        plan_purge([acct], TODAY)
    msg = str(exc.value)
    assert "acct-9" in msg
    assert field in msg
    assert "secret" not in msg
    assert "example.org" not in msg


def test_duplicate_ids_raise_without_email():
    secret = "secret.member@example.org"
    accounts = [
        make("dup-1", last_seen_at=TODAY, email=secret),
        make("dup-1", last_seen_at=TODAY, email=secret),
    ]
    with pytest.raises(ValueError) as exc:
        plan_purge(accounts, TODAY)
    msg = str(exc.value)
    assert "dup-1" in msg
    assert "secret" not in msg


def test_invalid_account_fails_whole_call_even_if_others_valid():
    good = make(70, last_seen_at=seen_for_due(TODAY))
    bad = make(71, last_seen_at=None)
    with pytest.raises(ValueError):
        plan_purge([good, bad], TODAY)