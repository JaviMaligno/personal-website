"""GDPR clean-up planner for Tidewater Climbing member accounts.

plan_purge(accounts, today) returns the actions for one run as a list of dicts
with keys account_id, action, due and approved_by. It is pure: it does not
mutate its inputs, perform I/O, or log account data.

Caller contract: the function is stateless and does not track history. Accounts
that were due in an earlier run and not deleted are emitted again. The caller
must record executed deletes and filter or dedupe the output before acting on
it, so that a delete is not run twice.

Spec notes (implemented as written):
- The "delete every due account" brief conflicts with DELETE_CAP. The cap wins;
  omitted deletes remain due and appear in later runs.
- Warn applies to unpaid-invoice accounts before they are due. Anonymise applies
  only once due.
- Staff-closed accounts (closed_by == "staff") are still warned. Only
  closed_by == "member" suppresses a warn.
- closed_by is not cross-checked against closed_at.
- last_login and tenant are ignored.
"""

import datetime
from datetime import date, timedelta

INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200
STAFF_DOMAIN = "@tidewater-klatring.no"
APPROVER = "Þórdís Sveinbjörnsdóttir"

_REQUIRED = ("id", "email", "last_seen_at", "closed_at", "closed_by",
             "unpaid_invoices", "litigation_hold")


def _is_plain_date(value):
    return isinstance(value, date) and not isinstance(value, datetime.datetime)


def _validate(accounts, today):
    if not isinstance(accounts, (list, tuple)):
        raise ValueError("accounts must be a list")
    if not _is_plain_date(today):
        raise ValueError("today must be a date, not a datetime")

    seen = set()
    for idx, acc in enumerate(accounts):
        if not isinstance(acc, dict):
            raise ValueError(f"account at index {idx} is not a dict")
        for key in _REQUIRED:
            if key not in acc:
                raise ValueError(f"missing field '{key}' for account at index {idx}")

        aid = acc["id"]
        if not isinstance(aid, str) or not aid:
            raise ValueError(f"invalid id for account at index {idx}")
        if aid in seen:
            raise ValueError(f"duplicate id '{aid}'")
        seen.add(aid)

        if not isinstance(acc["email"], str):
            raise ValueError(f"invalid email for account '{aid}'")
        if not _is_plain_date(acc["last_seen_at"]):
            raise ValueError(f"invalid last_seen_at for account '{aid}'")
        if acc["closed_at"] is not None and not _is_plain_date(acc["closed_at"]):
            raise ValueError(f"invalid closed_at for account '{aid}'")
        if acc["closed_by"] is not None and acc["closed_by"] not in ("member", "staff"):
            raise ValueError(f"invalid closed_by for account '{aid}'")
        up = acc["unpaid_invoices"]
        if not isinstance(up, int) or isinstance(up, bool) or up < 0:
            raise ValueError(f"invalid unpaid_invoices for account '{aid}'")
        if not isinstance(acc["litigation_hold"], bool):
            raise ValueError(f"invalid litigation_hold for account '{aid}'")


def _due(acc):
    due = acc["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
    if acc["closed_at"] is not None:
        closed_due = acc["closed_at"] + timedelta(days=CLOSED_DAYS)
        due = min(due, closed_due)
    return due


def _row(aid, action, due, approved_by):
    return {
        "account_id": aid,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
    }


def plan_purge(accounts: list[dict], today: datetime.date) -> list[dict]:
    _validate(accounts, today)

    out = []
    delete_candidates = []

    for acc in accounts:
        if acc["litigation_hold"]:
            continue
        if acc["email"].strip().casefold().endswith(STAFF_DOMAIN):
            continue

        aid = acc["id"]
        try:
            due = _due(acc)
        except OverflowError:
            raise ValueError(f"due date overflow for account '{aid}'") from None

        days_until = (due - today).days
        if days_until <= 0:
            if acc["unpaid_invoices"] > 0:
                out.append(_row(aid, "anonymise", due, APPROVER))
            else:
                delete_candidates.append((0 if acc["closed_at"] is not None else 1,
                                          due, aid))
        elif days_until <= WARN_WINDOW_DAYS and acc["closed_by"] != "member":
            out.append(_row(aid, "warn", due, None))

    delete_candidates.sort()
    for _, due, aid in delete_candidates[:DELETE_CAP]:
        out.append(_row(aid, "delete", due, APPROVER))

    out.sort(key=lambda r: r["account_id"])
    return out


def _self_check():
    t = date(2026, 10, 13)
    assert t - date(2024, 10, 13) == timedelta(days=730)

    def acc(aid, last_seen, **kw):
        base = {"id": aid, "email": f"{aid.lower()}@example.org",
                "last_seen_at": last_seen, "closed_at": None, "closed_by": None,
                "unpaid_invoices": 0, "litigation_hold": False}
        base.update(kw)
        return base

    # A1 due today -> delete
    assert plan_purge([acc("A1", date(2024, 10, 13))], t) == [
        {"account_id": "A1", "action": "delete", "due": "2026-10-13", "approved_by": APPROVER}]
    # A2 / A3 warn window boundary
    assert [r["action"] for r in plan_purge([acc("A2", date(2024, 10, 27))], t)] == ["warn"]
    assert plan_purge([acc("A3", date(2024, 10, 28))], t) == []
    # A6 / A7 member vs staff closure
    closed = dict(closed_at=date(2026, 9, 20))
    assert plan_purge([acc("A6", date(2026, 1, 1), closed_by="member", **closed)], t) == []
    assert plan_purge([acc("A7", date(2026, 1, 1), closed_by="staff", **closed)], t)[0]["due"] == "2026-10-20"
    # A10 hold, A12 staff
    assert plan_purge([acc("A10", date(2024, 10, 13), litigation_hold=True)], t) == []
    staff = acc("A12", date(2024, 10, 13))
    staff["email"] = "Ops@Tidewater-Klatring.NO"
    assert plan_purge([staff], t) == []
    # A13 unpaid due -> anonymise
    assert plan_purge([acc("A13", date(2024, 10, 13), unpaid_invoices=2)], t)[0]["action"] == "anonymise"
    # A18 sort order
    ids = [r["account_id"] for r in plan_purge(
        [acc("C", date(2024, 1, 1)), acc("A", date(2024, 1, 1)), acc("B", date(2024, 1, 1))], t)]
    assert ids == ["A", "B", "C"]
    # V1 duplicate id, V4 datetime today
    for bad_call in (
        lambda: plan_purge([acc("X1", date(2024, 1, 1)), acc("X1", date(2024, 1, 1))], t),
        lambda: plan_purge([], datetime.datetime(2026, 10, 13)),
    ):
        try:
            bad_call()
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")
    # V6 no email in error message
    try:
        plan_purge([acc("V6", date(2024, 1, 1), unpaid_invoices=None,
                        email="secret@example.org")], t)
    except ValueError as exc:
        assert "secret@example.org" not in str(exc)
    else:
        raise AssertionError("expected ValueError")


if __name__ == "__main__":
    _self_check()
    print("self-check passed")