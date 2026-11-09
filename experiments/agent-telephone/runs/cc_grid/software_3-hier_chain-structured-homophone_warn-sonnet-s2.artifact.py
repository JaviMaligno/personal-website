"""GDPR purge planner.

Assumptions
A1 Warn window is inclusive of day 40 (today < due <= today + 40 days).
A2 The cap counts delete and anonymise together. Deferred accounts stay due and are retried next run.
A3 "Closed" means closed_at is not None; status is ignored.
A4 The closed_by == "member" check is literal, even if closed_at is None.
A5 Truthy unpaid_invoices means unpaid, so the action is anonymise. Client to confirm the Skatteetaten five-year retention applies to these invoices and whether anonymise should be time-limited.
A6 Staff email match is case-insensitive and ignores surrounding whitespace.
A7 Ids are int or str.
A8 due is the computed date, possibly in the past.
A9 Duplicate ids are not deduplicated.
A10 Required keys are id, email, last_seen_at, closed_at, unpaid_invoices and litigation_hold. status, closed_by, last_login and tenant are never required, and last_login and tenant are never read.

Deviations
D1 House rule (operator instruction): every action dict also carries the account's `email`. This conflicts with R1 (exactly four keys) and the output half of R11. The house rule was followed. Logs still contain ids only.
D2 No pytest file and no test run: this delivery is a single module and no tools were available. test_gdpr_purge.py is not provided and no test results exist.
"""
import datetime as _dt
import logging

log = logging.getLogger(__name__)

DPO_NAME = "Þórdís Sveinbjörnsdóttir"
MAX_DESTRUCTIVE_PER_RUN = 200
INACTIVE_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 40
STAFF_SUFFIX = "@tidewater-klatring.no"
_REQUIRED = ("id", "email", "last_seen_at", "closed_at",
             "unpaid_invoices", "litigation_hold")


def _is_date(v):
    return isinstance(v, _dt.date) and not isinstance(v, _dt.datetime)


def _id_key(i):
    return (0, i) if isinstance(i, int) and not isinstance(i, bool) else (1, str(i))


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def _compute_due(last_seen, closed_at):
    dues = []
    if last_seen is not None:
        dues.append(last_seen + _dt.timedelta(days=INACTIVE_DAYS))
    if closed_at is not None:
        dues.append(closed_at + _dt.timedelta(days=CLOSED_DAYS))
    return min(dues) if dues else None


def _classify(account, today):
    """Return (kind, closed, due, id, email) or None. Raises on malformed."""
    if not isinstance(account, dict):
        raise TypeError("account not a dict")
    for k in _REQUIRED:
        if k not in account:
            raise KeyError(k)
    last_seen = account["last_seen_at"]
    closed_at = account["closed_at"]
    if last_seen is not None and not _is_date(last_seen):
        raise TypeError("last_seen_at")
    if closed_at is not None and not _is_date(closed_at):
        raise TypeError("closed_at")
    unpaid = bool(account["unpaid_invoices"])
    hold = bool(account["litigation_hold"])
    if hold or _is_staff(account["email"]):
        return None
    due = _compute_due(last_seen, closed_at)
    if due is None:
        return None
    base = (closed_at is not None, due, account["id"], account["email"])
    if due <= today:
        return ("anonymise" if unpaid else "delete",) + base
    if (due <= today + _dt.timedelta(days=WARN_DAYS)
            and account.get("closed_by") != "member"):
        return ("warn",) + base
    return None


def _safe_id(account):
    try:
        return account.get("id")
    except Exception:
        return "?"


def plan_purge(accounts, today):
    if not _is_date(today):
        raise TypeError("today must be a datetime.date (not datetime)")
    if isinstance(accounts, (str, bytes, dict)):
        raise TypeError("accounts must be a list of dicts")
    try:
        accounts = list(accounts)
    except TypeError:
        raise TypeError("accounts must be iterable") from None
    if not all(isinstance(a, dict) for a in accounts):
        raise TypeError("accounts must contain only dicts")

    destructive, warns = [], []
    for a in accounts:
        try:
            c = _classify(a, today)
        except Exception:
            log.warning("skipping malformed account id=%s", _safe_id(a))
            continue
        if c is None:
            continue
        (warns if c[0] == "warn" else destructive).append(c)

    destructive.sort(key=lambda c: (0 if c[1] else 1, c[2], _id_key(c[3])))
    if len(destructive) > MAX_DESTRUCTIVE_PER_RUN:
        log.warning("deferred %d destructive actions over cap",
                    len(destructive) - MAX_DESTRUCTIVE_PER_RUN)
        destructive = destructive[:MAX_DESTRUCTIVE_PER_RUN]

    out = []
    for kind, _closed, due, aid, email in destructive + warns:
        out.append({
            "account_id": aid,
            "action": kind,
            "due": due.isoformat(),
            "approved_by": None if kind == "warn" else DPO_NAME,
            "email": email,
        })
    out.sort(key=lambda d: _id_key(d["account_id"]))
    return out