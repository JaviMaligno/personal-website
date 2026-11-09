"""purge_planner: plan data-retention purge actions for member accounts.

Deviation from the client brief: the house rule says every action dict also
carries the account's `email`, so each action has five keys (account_id,
action, due, approved_by, email). This conflicts with R1 (exactly four keys)
and R11 (never put the email in any action), so the client should confirm.

Other points to confirm:
- The cap of 200 covers delete and anonymise combined.
- Within the cap, closed accounts come first, then earliest due, then id.
- The cap is applied before the final sort by id.
- Accounts cut by the cap get no action and are retried next run (stateless).
- Overdue accounts get delete or anonymise only, never a warn.
- `status` is ignored, so already-anonymised accounts will be re-emitted.
- A missing last_seen_at on an unclosed account gives no action.
- The meaning of unpaid_invoices is unknown (int or list is handled).
- Anonymise versus the 5-year Skatteetaten invoice retention rule needs confirming.
- Member-closed accounts are never warned.
- closed_by without closed_at is treated as not closed.
- Warns go to accounts that will later be anonymised.
- Warns go to staff-closed accounts.
- Duplicate ids are not deduplicated.
"""
import datetime as _dt

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
MAX_DESTRUCTIVE_PER_RUN = 200
STAFF_DOMAIN = "@tidewater-klatring.no"
DPO_NAME = "Þórdís Sveinbjörnsdóttir"


def _is_staff(acct):
    email = acct.get("email")
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def _due_date(acct):
    dues = []
    seen = acct.get("last_seen_at")
    if seen is not None:
        dues.append(seen + _dt.timedelta(days=INACTIVITY_DAYS))
    closed = acct.get("closed_at")
    if closed is not None:
        dues.append(closed + _dt.timedelta(days=CLOSED_GRACE_DAYS))
    return min(dues) if dues else None


def _id_key(account_id):
    return (isinstance(account_id, str), account_id)


def _classify(acct, today):
    """Return (action, due) or None when no action applies."""
    if acct.get("litigation_hold"):
        return None
    if _is_staff(acct):
        return None
    due = _due_date(acct)
    if due is None:
        return None
    delta = (due - today).days
    if delta <= 0:
        return ("anonymise" if acct.get("unpaid_invoices") else "delete"), due
    if delta <= WARN_WINDOW_DAYS:
        if acct.get("closed_by") == "member" and acct.get("closed_at") is not None:
            return None
        return "warn", due
    return None


def _format(acct, action, due):
    return {
        "account_id": acct["id"],
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else DPO_NAME,
        "email": acct.get("email"),  # house rule: support follow-up
    }


def plan_purge(accounts, today):
    if not isinstance(today, _dt.date):
        raise TypeError("today must be a datetime.date")
    destructive = []
    warns = []
    for acct in accounts:
        if acct.get("id") is None:
            raise ValueError("account is missing an id")
        res = _classify(acct, today)
        if res is None:
            continue
        action, due = res
        entry = _format(acct, action, due)
        if action == "warn":
            warns.append(entry)
        else:
            rank = (acct.get("closed_at") is None, due, _id_key(acct["id"]))
            destructive.append((rank, entry))
    destructive.sort(key=lambda t: t[0])
    selected = [e for _, e in destructive[:MAX_DESTRUCTIVE_PER_RUN]]
    result = selected + warns
    result.sort(key=lambda e: _id_key(e["account_id"]))
    return result