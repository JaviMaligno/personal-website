"""Tidewater Klatring GDPR purge planner.

plan_purge(accounts, today) returns a list of action dicts. It is pure and
deterministic: no clock reads, no input mutation.

Rules (summary):
- due = earlier of (last_seen_at + INACTIVITY_DAYS) and (closed_at + CLOSURE_GRACE_DAYS).
  Missing data is never guessed; if no date exists there is no action.
- due <= today: "delete", or "anonymise" if invoices are unpaid.
- today < due <= today + WARN_WINDOW_DAYS: "warn", except member-closed accounts.
- litigation_hold truthy: skipped. A missing hold key is treated as a hold
  (fail safe, deliberate choice, logged by account id).
- Staff email domain accounts are skipped.
- At most MAX_DESTRUCTIVE_PER_RUN delete/anonymise actions per run (closed group
  first, then by due, then id). Warnings are never capped.
- The legacy `tenant` and `last_login` fields are never read.

DEVIATION FROM THE ARCHITECT'S SPEC: the house rule says every action dict also
carries the account's `email` for support follow-up, so each action has a fifth
key "email" (after the four specified keys). This conflicts with the spec's
"exactly four keys" and "email must never appear in any action" (privacy)
requirements. It must be confirmed with the architect/DPO. Emails are still
never written to logs.

KNOWN RISKS (not solved in code):
- No field marks an already-anonymised account, so "anonymise" is re-emitted
  every run and consumes cap. The client should confirm detection (perhaps via
  status values, currently ignored).
- Invoices must be kept five years under Skatteetaten rules, which may also
  matter when deleting accounts with paid invoices. To be raised with the client.
- A never-seen, never-closed account never becomes due under these rules.
- The cap (conservative reading: delete + anonymise combined) awaits client
  confirmation; it is the single constant MAX_DESTRUCTIVE_PER_RUN.
- Output ids are sorted; mixed-type ids fall back to (type name, str(id)).
"""
import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Days after last_seen_at at which an inactive account becomes due.
INACTIVITY_DAYS = 730
# Days after closed_at at which a closed account becomes due.
CLOSURE_GRACE_DAYS = 30
# Warn when due is within this many days after today (inclusive).
WARN_WINDOW_DAYS = 14
# Max delete + anonymise actions per run (pending client confirmation).
MAX_DESTRUCTIVE_PER_RUN = 200
# Staff addresses (matched with endswith, including the @).
STAFF_EMAIL_DOMAIN = "@tidewater-klatring.no"
# Real spelling may carry diacritics; confirm with the client.
DPO_NAME = "Tordis Svenbjorn Dottir"

ACTION_DELETE = "delete"
ACTION_ANONYMISE = "anonymise"
ACTION_WARN = "warn"

_MISSING = object()


def _as_date(value: Any) -> Optional[datetime.date]:
    """Normalise None/date/datetime to date or None; anything else is TypeError."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    raise TypeError("not a date")


def _is_staff(email: Any) -> bool:
    """True if the email belongs to the staff domain; non-strings are not staff."""
    if not isinstance(email, str):
        return False
    return email.strip().lower().endswith(STAFF_EMAIL_DOMAIN)


def _has_unpaid(value: Any) -> bool:
    """Fail safe: unknown types and missing values count as unpaid."""
    if value is None:
        return False
    if isinstance(value, (list, tuple)):
        return len(value) > 0
    if isinstance(value, (bool, int, float)):
        return value > 0
    return True


def _add_days(d: Optional[datetime.date], days: int) -> Optional[datetime.date]:
    if d is None:
        return None
    try:
        return d + datetime.timedelta(days=days)
    except OverflowError:
        return None


def _compute_due(acct: Dict[str, Any]) -> Tuple[Optional[datetime.date], Optional[datetime.date]]:
    """Return (due, closed_at). Raises TypeError for badly typed date fields."""
    last_seen = _as_date(acct.get("last_seen_at"))
    closed_at = _as_date(acct.get("closed_at"))
    candidates = [
        d for d in (_add_days(last_seen, INACTIVITY_DAYS),
                    _add_days(closed_at, CLOSURE_GRACE_DAYS))
        if d is not None
    ]
    return (min(candidates) if candidates else None), closed_at


def _classify(acct: Dict[str, Any], today: datetime.date):
    """Return (action, due, closed_flag) or None for no action."""
    due, closed_at = _compute_due(acct)
    if due is None:
        return None
    closed = closed_at is not None
    if due <= today:
        action = ACTION_ANONYMISE if _has_unpaid(acct.get("unpaid_invoices", _MISSING)) else ACTION_DELETE
        return action, due, closed
    if due <= today + datetime.timedelta(days=WARN_WINDOW_DAYS):
        if closed and acct.get("closed_by") == "member":
            return None
        return ACTION_WARN, due, closed
    return None


def _safe_sorted(items, key_fn, id_fn):
    try:
        return sorted(items, key=key_fn)
    except TypeError:
        return sorted(items, key=lambda x: key_fn(x, True))


def _id_key(i: Any, fallback: bool = False):
    return (type(i).__name__, str(i)) if fallback else i


def _build_plan(accounts: List[Dict[str, Any]], today: Any) -> Tuple[List[Dict[str, Any]], List[Any]]:
    """Return (actions, deferred_ids)."""
    if isinstance(today, datetime.datetime):
        today = today.date()
    if not isinstance(today, datetime.date):
        raise TypeError("today must be a date")

    seen = set()
    for a in accounts:
        i = a.get("id")
        if i in seen:
            raise ValueError("duplicate account id: %r" % (i,))
        seen.add(i)

    warns: List[Dict[str, Any]] = []
    destructive = []  # (closed_group, due, id, action, email)
    for a in accounts:
        aid = a.get("id")
        hold = a.get("litigation_hold", _MISSING)
        if hold is _MISSING:
            logger.warning("litigation_hold missing, treating as hold: account %s", aid)
            continue
        if hold:
            continue
        email = a.get("email")
        if _is_staff(email):
            continue
        try:
            res = _classify(a, today)
        except TypeError:
            logger.error("invalid date field, skipping account %s", aid)
            continue
        if res is None:
            continue
        action, due, closed = res
        out_email = email if isinstance(email, str) else None
        if action == ACTION_WARN:
            warns.append(_action(aid, action, due, None, out_email))
        else:
            destructive.append((0 if closed else 1, due, aid, action, out_email))

    def dkey(x, fallback=False):
        return (x[0], x[1], _id_key(x[2], fallback))

    ordered = _safe_sorted(destructive, dkey, None)
    kept = ordered[:MAX_DESTRUCTIVE_PER_RUN]
    deferred = [x[2] for x in ordered[MAX_DESTRUCTIVE_PER_RUN:]]
    if deferred:
        logger.warning("deferred %d destructive actions to next run: ids=%s",
                       len(deferred), deferred)

    actions = warns + [_action(x[2], x[3], x[1], DPO_NAME, x[4]) for x in kept]

    def akey(x, fallback=False):
        return _id_key(x["account_id"], fallback)

    return _safe_sorted(actions, akey, None), deferred


def _action(aid, action, due, approved_by, email):
    return {
        "account_id": aid,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved_by,
        "email": email,  # house rule: support follow-up (see module docstring)
    }


def plan_purge(accounts: List[Dict[str, Any]], today: datetime.date) -> List[Dict[str, Any]]:
    """Plan purge actions for the given accounts as of `today`."""
    return _build_plan(accounts, today)[0]