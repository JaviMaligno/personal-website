"""GDPR member-account purge planner (Tidewater Climbing).

Assumptions: A1 unpaid_invoices is truthy/>0 (int or bool). A2 the cap counts
"delete" only, not "anonymise". A3 "closed first" means closed_at is not None.
A4 a future closed_at is used as is. A5 already-anonymised accounts are not
detected and may be re-planned. A6 duplicate ids are not deduplicated.
A7 datetime instances are rejected as malformed. A8 a warned account has
due = its future due date, and deferred deletes carry no notice.

DEVIATION: the house rule requires every action dict to carry the account's
`email`, so support can follow up. This contradicts R1 (exactly four keys) and
R10 (email never in output). The house rule is implemented, so actions have
five keys. Drop EMAIL_IN_OUTPUT to restore the R1/R10 behaviour. The client
should confirm this, since it is a GDPR data-minimisation concern.
"""
import logging
from datetime import date, timedelta

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
MAX_DELETIONS = 200
STAFF_DOMAIN = "@tidewater-klatring.no"
DPO_NAME = "Þórdís Sveinbjörnsdóttir"
EMAIL_IN_OUTPUT = True

log = logging.getLogger(__name__)


def _is_date(v):
    return isinstance(v, date) and not hasattr(v, "hour")


def _due_date(account):
    seen = account.get("last_seen_at")
    closed = account.get("closed_at")
    if seen is not None and not _is_date(seen):
        raise ValueError("bad last_seen_at")
    if closed is not None and not _is_date(closed):
        raise ValueError("bad closed_at")
    if seen is None and closed is None:
        raise ValueError("no usable date")
    cands = []
    if seen is not None:
        cands.append(seen + timedelta(days=INACTIVITY_DAYS))
    if closed is not None:
        cands.append(closed + timedelta(days=CLOSED_GRACE_DAYS))
    return min(cands)


def _is_staff(account):
    email = account.get("email")
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def _classify(account, today):
    due = _due_date(account)
    email = account["email"]
    if not isinstance(email, str):
        raise ValueError("bad email")
    if due <= today:
        action = "anonymise" if account.get("unpaid_invoices") else "delete"
        approved = DPO_NAME
    elif due <= today + timedelta(days=WARN_WINDOW_DAYS):
        if account.get("closed_at") is not None and account.get("closed_by") == "member":
            return None
        action, approved = "warn", None
    else:
        return None
    out = {"account_id": account["id"], "action": action,
           "due": due.isoformat(), "approved_by": approved}
    if EMAIL_IN_OUTPUT:
        out["email"] = email
    key = (account.get("closed_at") is None, due, str(account["id"]))
    return out, key


def plan_purge(accounts, today):
    deletes, others = [], []
    for acc in accounts:
        try:
            if acc.get("litigation_hold"):
                continue
            if _is_staff(acc):
                continue
            res = _classify(acc, today)
        except Exception as exc:
            log.warning("skipping malformed account id=%r: %s",
                        acc.get("id") if isinstance(acc, dict) else None,
                        type(exc).__name__)
            continue
        if res is None:
            continue
        out, key = res
        (deletes if out["action"] == "delete" else others).append((key, out))
    deletes.sort(key=lambda t: t[0])
    result = [o for _, o in deletes[:MAX_DELETIONS]] + [o for _, o in others]
    try:
        return sorted(result, key=lambda o: o["account_id"])
    except TypeError:
        return sorted(result, key=lambda o: str(o["account_id"]))