"""Tidewater Climbing GDPR purge planner.

plan_purge(accounts, today) returns a list of action dicts sorted by account_id.

Decisions:
- (a) The cap MAX_DELETIONS_PER_RUN applies to "delete" actions only. "anonymise"
  actions are neither counted nor capped.
- Capped-out accounts are omitted this run (no warn) and stay due for a later run.
- last_login and status are never read. last_seen_at None means no inactivity date.
- Malformed dates raise TypeError/ValueError rather than being guessed.
- HOUSE RULE DEVIATION: the operator house rule requires every action to also
  carry the account's "email" so support can follow up. This conflicts with
  R1/R9 (exactly four keys, no personal data). The house rule is followed, so
  each action has five keys. Please confirm with the client, since it is a GDPR
  concern.
"""
from datetime import timedelta

MAX_DELETIONS_PER_RUN = 200
DPO_NAME = "Þórdís Sveinbjörnsdóttir"
INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
STAFF_SUFFIX = "@tidewater-klatring.no"


def _has_unpaid(value):
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value > 0
    return len(value) > 0


def _is_staff(email):
    return isinstance(email, str) and email.strip().casefold().endswith(STAFF_SUFFIX)


def _due_date(acct):
    candidates = []
    seen = acct.get("last_seen_at")
    if seen is not None:
        candidates.append(seen + timedelta(days=INACTIVITY_DAYS))
    closed = acct.get("closed_at")
    if closed is not None:
        candidates.append(closed + timedelta(days=CLOSED_DAYS))
    return min(candidates) if candidates else None


def _action(acct, action, due, approver):
    return {
        "account_id": acct["id"],
        "action": action,
        "due": due.isoformat(),
        "approved_by": approver,
        "email": acct.get("email"),
    }


def plan_purge(accounts, today):
    deletes = []  # (sort_key, action dict)
    others = []
    warn_limit = today + timedelta(days=WARN_DAYS)

    for acct in accounts:
        if acct.get("litigation_hold"):
            continue
        if _is_staff(acct.get("email")):
            continue
        due = _due_date(acct)
        if due is None:
            continue
        if due <= today:
            if _has_unpaid(acct.get("unpaid_invoices")):
                others.append(_action(acct, "anonymise", due, DPO_NAME))
            else:
                key = (acct.get("closed_at") is None, due, acct["id"])
                deletes.append((key, _action(acct, "delete", due, DPO_NAME)))
        elif due <= warn_limit and acct.get("closed_by") != "member":
            others.append(_action(acct, "warn", due, None))

    deletes.sort(key=lambda item: item[0])
    result = others + [a for _, a in deletes[:MAX_DELETIONS_PER_RUN]]
    result.sort(key=lambda a: a["account_id"])
    return result