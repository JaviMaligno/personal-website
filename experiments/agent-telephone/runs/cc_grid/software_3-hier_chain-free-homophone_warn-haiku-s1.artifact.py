from __future__ import annotations

"""Tidewater Climbing GDPR purge planner.

Public entry point: plan_purge(accounts, today).

Architect's interpretation (open questions for the client):
- Staff accounts are matched case-insensitively after stripping whitespace,
  against the suffix "@tidewater-klatring.no".
- unpaid_invoices is treated as unpaid when truthy. A count greater than zero
  is unpaid. This is the conservative reading because anonymise keeps invoices,
  as Skatteetaten requires. Zero, None, False and empty values are not unpaid.
- Validation: last_seen_at and last_login are required dates. closed_at is a
  date or None. Any datetime.datetime value is rejected, because only plain
  dates are accepted. A non-string email raises ValueError because the staff
  check cannot be made safely. Duplicate account ids raise ValueError. Error
  messages name the account id and never include the email.
- The tenant key is ignored entirely.
- Warn applies only to accounts that are not yet due, due within the next 40
  days, not closed by a member, not staff, and not on hold.
- Delete cap: at most 200 delete actions per run. Candidates are ordered by
  (closed first, due ascending, id ascending). Delete candidates beyond the cap
  get no action at all. They are not converted to anonymise and no warn is
  emitted for them. Staff and hold exclusions are applied before the cap.
- Warned accounts that are later deleted may need a separate notice. This is
  an open question for the client.
"""

from datetime import date, datetime, timedelta
from typing import NamedTuple

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 40
DELETE_CAP = 200
STAFF_DOMAIN = "@tidewater-klatring.no"
APPROVER = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"

_REQUIRED_DATES = ("last_seen_at", "last_login")
_REQUIRED_KEYS = ("id", "email", "status", "last_seen_at", "last_login",
                  "closed_at", "closed_by", "unpaid_invoices", "litigation_hold")


class _Plan(NamedTuple):
    account_id: object
    kind: str
    due: date
    closed: bool


def _check_date(value, label, required):
    if value is None:
        if required:
            raise ValueError(f"{label} is required")
        return
    if isinstance(value, datetime) or not isinstance(value, date):
        raise ValueError(f"{label} must be a datetime.date")


def _validate(accounts):
    seen = set()
    for acc in accounts:
        if not isinstance(acc, dict):
            raise ValueError("each account must be a dict")
        if "id" not in acc:
            raise ValueError("account is missing key 'id'")
        aid = acc["id"]
        if aid in seen:
            raise ValueError(f"duplicate account id {aid!r}")
        seen.add(aid)
        for key in _REQUIRED_KEYS:
            if key not in acc:
                raise ValueError(f"account {aid!r} is missing key {key!r}")
        if not isinstance(acc["email"], str):
            raise ValueError(f"account {aid!r}: email must be a string")
        for field in _REQUIRED_DATES:
            try:
                _check_date(acc[field], field, required=True)
            except ValueError as exc:
                raise ValueError(f"account {aid!r}: {exc}") from None
        try:
            _check_date(acc["closed_at"], "closed_at", required=False)
        except ValueError as exc:
            raise ValueError(f"account {aid!r}: {exc}") from None


def _due(acc):
    inactive_due = acc["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
    closed_at = acc["closed_at"]
    if closed_at is None:
        return inactive_due
    return min(inactive_due, closed_at + timedelta(days=CLOSED_GRACE_DAYS))


def plan_purge(accounts, today):
    if isinstance(today, datetime) or not isinstance(today, date):
        raise ValueError("today must be a datetime.date")
    _validate(accounts)

    warn_limit = today + timedelta(days=WARN_WINDOW_DAYS)
    plans = []
    for acc in accounts:
        email = acc["email"].strip().lower()
        if email.endswith(STAFF_DOMAIN):
            continue
        if bool(acc["litigation_hold"]):
            continue
        due = _due(acc)
        closed = acc["closed_at"] is not None
        if due <= today:
            # Unpaid invoices (truthy count) force anonymise, which keeps
            # invoices as Skatteetaten requires. Otherwise delete.
            kind = "anonymise" if bool(acc["unpaid_invoices"]) else "delete"
            plans.append(_Plan(acc["id"], kind, due, closed))
        elif due <= warn_limit and acc["closed_by"] != "member":
            plans.append(_Plan(acc["id"], "warn", due, closed))

    deletes = [p for p in plans if p.kind == "delete"]
    deletes.sort(key=lambda p: (0 if p.closed else 1, p.due, p.account_id))
    kept_deletes = {p.account_id for p in deletes[:DELETE_CAP]}

    output = []
    for p in plans:
        if p.kind == "delete" and p.account_id not in kept_deletes:
            continue
        output.append({
            "account_id": p.account_id,
            "action": p.kind,
            "due": p.due.isoformat(),
            "approved_by": None if p.kind == "warn" else APPROVER,
        })
    output.sort(key=lambda a: a["account_id"])
    return output