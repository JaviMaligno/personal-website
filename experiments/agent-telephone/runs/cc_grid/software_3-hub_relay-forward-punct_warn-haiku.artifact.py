# intended path: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-sgmvua9_/tidewater_purge/purge_plan.py
"""GDPR purge planner for Tidewater Climbing member accounts.

Entry point: plan_purge(accounts, today). Pure function, no I/O.

Open questions for the client:
1. Member-closed warnings. The brief says "If the member closed the account
   themselves, don't. Warn them, they asked to leave." Default implemented:
   NO warning for member-closed accounts. Controlled by WARN_MEMBER_CLOSED
   below. Set it to True to warn them instead.
2. Anonymise timing. The rule order "anonymise if unpaid_invoices > 0", read
   literally, would anonymise live accounts that are not yet due. The brief
   says "instead of deleting it", so anonymise here applies only once the
   account is due (due <= today). Confirm.
3. "Closed" means closed_at is not None. closed_by must be "member" or
   "staff" when closed_at is set. It is only used for the member-closed
   warn rule.
4. An account with unpaid invoices that is due within the warn window gets
   a warn action, because anonymise only fires once the account is due.
"""

from datetime import date, datetime, timedelta

DPO_APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200
WARN_MEMBER_CLOSED = False  # open question 1, see module docstring

_REQUIRED_KEYS = (
    "id", "email", "last_seen_at", "closed_at", "closed_by",
    "unpaid_invoices", "litigation_hold",
)


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _label(index, rec):
    # Never include the record itself, since it carries the email.
    acc_id = rec.get("id") if isinstance(rec, dict) else None
    return repr(acc_id) if acc_id is not None else f"at index {index}"


def _check(index, rec):
    def bad():
        raise ValueError(f"malformed account record: {_label(index, rec)}")

    if not isinstance(rec, dict) or any(k not in rec for k in _REQUIRED_KEYS):
        bad()
    if not isinstance(rec["id"], str) or not isinstance(rec["email"], str):
        bad()
    if not _is_date(rec["last_seen_at"]):
        bad()
    closed_at = rec["closed_at"]
    if closed_at is not None:
        if not _is_date(closed_at) or rec["closed_by"] not in ("member", "staff"):
            bad()
    units = rec["unpaid_invoices"]
    if not isinstance(units, int) or isinstance(units, bool) or units < 0:
        bad()
    if not isinstance(rec["litigation_hold"], bool):
        bad()


def _action(account_id, action, due):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else DPO_APPROVER,
    }


def plan_purge(accounts, today):
    if not _is_date(today):
        raise TypeError("today must be a datetime.date")

    records = list(accounts)
    seen_ids = set()
    for index, rec in enumerate(records):
        _check(index, rec)
        if rec["id"] in seen_ids:
            raise ValueError(f"duplicate account id: {rec['id']!r}")
        seen_ids.add(rec["id"])

    warn_horizon = today + timedelta(days=WARN_WINDOW_DAYS)
    anonymise, warn, deletable = [], [], []

    for rec in records:
        if rec["litigation_hold"]:
            continue
        if rec["email"].lower().endswith(STAFF_EMAIL_SUFFIX):
            continue

        closed = rec["closed_at"] is not None
        due = rec["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
        if closed:
            due = min(due, rec["closed_at"] + timedelta(days=CLOSED_GRACE_DAYS))

        if due <= today:
            if rec["unpaid_invoices"] > 0:
                anonymise.append(_action(rec["id"], "anonymise", due))
            else:
                # Closed accounts sort first under the cap.
                deletable.append((0 if closed else 1, due, rec["id"]))
        elif due <= warn_horizon:
            member_closed = closed and rec["closed_by"] == "member"
            if WARN_MEMBER_CLOSED or not member_closed:
                warn.append(_action(rec["id"], "warn", due))

    deletable.sort()
    deletes = [
        _action(acc_id, "delete", due)
        for _, due, acc_id in deletable[:DELETE_CAP]
    ]

    result = anonymise + deletes + warn
    result.sort(key=lambda a: a["account_id"])
    return result


# intended path: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-sgmvua9_/tidewater_purge/test_purge_plan.py
# Not executed in this session. Run with: pytest test_purge_plan.py

import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from purge_plan import DPO_APPROVER, plan_purge  # noqa: E402

TODAY = date(2026, 10, 13)
DAY = timedelta(days=1)


def make(aid, last_seen_at=None, email="member@example.org", closed_at=None,
         closed_by=None, unpaid=0, hold=False):
    return {
        "id": aid,
        "email": email,
        "status": "active",
        "last_seen_at": last_seen_at if last_seen_at is not None else TODAY,
        "last_login": None,
        "closed_at": closed_at,
        "closed_by": closed_by,
        "unpaid_invoices": unpaid,
        "litigation_hold": hold,
    }


def test_730_day_boundary_deletes_on_due_date():
    out = plan_purge([make("a", last_seen_at=TODAY - 730 * DAY)], TODAY)
    assert out == [{"account_id": "a", "action": "delete",
                    "due": "2026-10-13", "approved_by": DPO_APPROVER}]


def test_one_day_before_730_boundary_warns():
    out = plan_purge([make("a", last_seen_at=TODAY - 729 * DAY)], TODAY)
    assert out == [{"account_id": "a", "action": "warn",
                    "due": "2026-10-14", "approved_by": None}]


def test_closed_account_due_30_days_after_closed_at_when_sooner():
    rec = make("c", last_seen_at=TODAY - 100 * DAY,
               closed_at=TODAY - 30 * DAY, closed_by="staff")
    out = plan_purge([rec], TODAY)
    assert out == [{"account_id": "c", "action": "delete",
                    "due": "2026-10-13", "approved_by": DPO_APPROVER}]


def test_closed_30_day_warn_for_staff_closed():
    rec = make("c", last_seen_at=TODAY, closed_at=TODAY - 29 * DAY,
               closed_by="staff")
    out = plan_purge([rec], TODAY)
    assert out == [{"account_id": "c", "action": "warn",
                    "due": "2026-10-14", "approved_by": None}]


def test_member_closed_not_warned_by_default():
    rec = make("c", last_seen_at=TODAY, closed_at=TODAY - 29 * DAY,
               closed_by="member")
    assert plan_purge([rec], TODAY) == []


def test_warn_window_includes_plus_14_and_excludes_plus_15():
    inc = make("inc", last_seen_at=TODAY + 14 * DAY - 730 * DAY)
    exc = make("exc", last_seen_at=TODAY + 15 * DAY - 730 * DAY)
    out = plan_purge([inc, exc], TODAY)
    assert out == [{"account_id": "inc", "action": "warn",
                    "due": "2026-10-27", "approved_by": None}]


def test_staff_accounts_are_skipped():
    seen = TODAY - 800 * DAY
    accounts = [
        make("s1", last_seen_at=seen, email="jon@tidewater-klatring.no"),
        make("s2", last_seen_at=seen, email="ANA@Tidewater-Klatring.NO"),
    ]
    assert plan_purge(accounts, TODAY) == []


def test_litigation_hold_skipped_for_delete_anonymise_and_warn():
    accounts = [
        make("h1", last_seen_at=TODAY - 800 * DAY, hold=True),
        make("h2", last_seen_at=TODAY - 800 * DAY, unpaid=3, hold=True),
        make("h3", last_seen_at=TODAY - 729 * DAY, hold=True),
    ]
    assert plan_purge(accounts, TODAY) == []


def test_unpaid_invoices_give_anonymise_not_delete():
    out = plan_purge([make("u", last_seen_at=TODAY - 730 * DAY, unpaid=2)], TODAY)
    assert out == [{"account_id": "u", "action": "anonymise",
                    "due": "2026-10-13", "approved_by": DPO_APPROVER}]


def test_cap_of_200_deletes_closed_first_even_when_inactive_more_overdue():
    closed = [
        make(f"c{i:03d}", last_seen_at=TODAY - 900 * DAY,
             closed_at=TODAY - 31 * DAY, closed_by="member")
        for i in range(5)
    ]
    # Inactive accounts are far more overdue but must still rank after closed.
    inactive = [make(f"i{i:03d}", last_seen_at=TODAY - 2000 * DAY)
                for i in range(200)]
    unpaid = [make("u000", last_seen_at=TODAY - 2000 * DAY, unpaid=1)]

    out = plan_purge(closed + inactive + unpaid, TODAY)
    deletes = [a for a in out if a["action"] == "delete"]
    anonymises = [a for a in out if a["action"] == "anonymise"]

    assert len(deletes) == 200
    assert len(anonymises) == 1  # anonymise is not subject to the cap
    delete_ids = {a["account_id"] for a in deletes}
    assert {f"c{i:03d}" for i in range(5)} <= delete_ids
    assert "i194" in delete_ids
    assert "i195" not in delete_ids  # deferred, no output


def test_output_sorted_by_account_id():
    accounts = [
        make("b", last_seen_at=TODAY - 730 * DAY),
        make("a", last_seen_at=TODAY - 729 * DAY),
        make("c", last_seen_at=TODAY - 730 * DAY, unpaid=1),
    ]
    ids = [a["account_id"] for a in plan_purge(accounts, TODAY)]
    assert ids == ["a", "b", "c"]


def test_email_never_appears_in_output():
    email = "secret.member@example.org"
    accounts = [
        make("m1", last_seen_at=TODAY - 730 * DAY, email=email),
        make("m2", last_seen_at=TODAY - 729 * DAY, email=email),
        make("m3", last_seen_at=TODAY - 730 * DAY, email=email, unpaid=1),
    ]
    out = plan_purge(accounts, TODAY)
    assert len(out) == 3
    assert email not in repr(out)
    for action in out:
        assert set(action) == {"account_id", "action", "due", "approved_by"}


def test_due_dates_are_iso_strings():
    out = plan_purge([make("a", last_seen_at=TODAY - 730 * DAY)], TODAY)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", out[0]["due"])
    assert date.fromisoformat(out[0]["due"]) == TODAY


def test_malformed_record_error_names_id_not_email():
    rec = make("bad1", email="leak@example.org")
    rec["last_seen_at"] = datetime(2026, 1, 1)
    with pytest.raises(ValueError) as exc:
        plan_purge([rec], TODAY)
    msg = str(exc.value)
    assert "bad1" in msg
    assert "leak@example.org" not in msg


def test_missing_key_is_malformed():
    rec = make("bad2")
    del rec["unpaid_invoices"]
    with pytest.raises(ValueError, match="bad2"):
        plan_purge([rec], TODAY)