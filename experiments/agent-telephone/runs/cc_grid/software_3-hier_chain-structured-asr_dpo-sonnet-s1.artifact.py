"""Tidewater Climbing GDPR member-account purge planner (stdlib only).

Decisions and assumptions:
- R4: closed_at is authoritative for open/closed. `status` is not used.
- R3: inactivity uses last_seen_at only, never last_login.
- last_seen_at None: due = closed_at + 30 if closed, else the account is
  skipped (never falling back to last_login). Skipped ids are logged
  (ids only, no emails) and available via `skipped_ids()`.
- R6: warn window is today < due <= today + 14.
- R7: closed_by == "member" gets no warn (only when closed_at is set).
- R8 (assumption): accounts with unpaid invoices get "anonymise", never warn.
- R12 (assumption): MAX_DESTRUCTIVE covers delete and anonymise combined.
  Priority is closed accounts first, then earliest due, then id. Dropped
  accounts are not emitted and reappear next run. Warns are not capped (R14).
- R13: warn has approved_by None.
- R15: output sorted by id after cap selection. If ids are not mutually
  comparable, falls back to str(id).
- Duplicate ids are all kept. Inputs are never mutated.
- HOUSE RULE vs R11: the house rule says every action dict also carries the
  account's `email`, while client requirement R11 says actions contain exactly
  four keys and no email. These conflict. The house rule is followed here via
  INCLUDE_EMAIL = True. Set it to False to satisfy R11 strictly. This needs a
  decision from the client or the user, as it is a GDPR-sensitive choice.
- R18-R20: MISSING. They were never received and are not implemented or guessed.
- No tests were run or written in this reply: no execution tools were available.
"""
import logging
from datetime import date, timedelta

MAX_DESTRUCTIVE = 200
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_DAYS = 14
APPROVER = "Tordis Svenbjorn Dottir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INCLUDE_EMAIL = True  # house rule; conflicts with R11, see module docstring

_log = logging.getLogger(__name__)
_skipped: list = []


def skipped_ids() -> list:
    """Ids skipped in the most recent plan_purge call (no due date derivable)."""
    return list(_skipped)


def _is_staff(email) -> bool:
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def _unpaid(value) -> bool:
    if isinstance(value, (int, float)):
        return value > 0
    return bool(value)


def _due(acc):
    candidates = []
    seen = acc.get("last_seen_at")
    closed = acc.get("closed_at")
    if seen is not None:
        candidates.append(seen + timedelta(days=INACTIVITY_DAYS))
    if closed is not None:
        candidates.append(closed + timedelta(days=CLOSED_GRACE_DAYS))
    return min(candidates) if candidates else None


def _action(acc, kind, due):
    a = {
        "account_id": acc["id"],
        "action": kind,
        "due": due.isoformat(),
        "approved_by": None if kind == "warn" else APPROVER,
    }
    if INCLUDE_EMAIL:
        a["email"] = acc.get("email")
    return a


def plan_purge(accounts, today: date) -> list:
    _skipped.clear()
    horizon = today + timedelta(days=WARN_DAYS)
    destructive = []  # (sort_key, action)
    warns = []

    for acc in accounts:
        if acc.get("litigation_hold") or _is_staff(acc.get("email")):
            continue
        due = _due(acc)
        if due is None:
            _skipped.append(acc.get("id"))
            continue
        closed = acc.get("closed_at") is not None
        unpaid = _unpaid(acc.get("unpaid_invoices"))
        if due <= today:
            kind = "anonymise" if unpaid else "delete"
            key = (not closed, due, str(acc["id"]))
            destructive.append((key, _action(acc, kind, due)))
        elif due <= horizon:
            if unpaid or (closed and acc.get("closed_by") == "member"):
                continue
            warns.append(_action(acc, "warn", due))

    if _skipped:
        _log.warning("purge: skipped %d account(s) without due date: %s",
                     len(_skipped), _skipped)

    destructive.sort(key=lambda t: t[0])
    chosen = [a for _, a in destructive[:MAX_DESTRUCTIVE]]
    result = chosen + warns
    try:
        result.sort(key=lambda a: a["account_id"])
    except TypeError:
        result.sort(key=lambda a: str(a["account_id"]))
    return result