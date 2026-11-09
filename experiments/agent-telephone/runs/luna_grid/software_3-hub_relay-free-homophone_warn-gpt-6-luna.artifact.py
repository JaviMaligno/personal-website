"""Acceptance criteria
- Skip accounts on litigation hold and staff whose email ends with
  ``@tidewater-klatring.no`` (case-insensitively).
- Calculate due as 730 days after ``last_seen_at``, or the earlier of that
  date and 30 days after ``closed_at``. Accept ``datetime.date`` values or
  ISO date strings; ignore accounts without ``last_seen_at``.
- Due on or before today is eligible for deletion; due 1–40 days after today
  is eligible for warning unless the member closed their own account.
- Every result has exactly ``account_id``, ``action``, ``due``, and
  ``approved_by``; ``due`` is an ISO date string. Results are sorted by
  account ID and contain no email or legacy ``tenant`` field.
- Emit at most 200 deletes per run, choosing closed accounts first. Accounts
  with unpaid invoices are anonymised instead and do not count toward the cap.
- Deletes and anonymisations use the required approver; warnings use None.
"""

from datetime import date, timedelta


_APPROVER = "Þórdís Sveinbjörnsdóttir"
_STAFF_DOMAIN = "@tidewater-klatring.no"


def _as_date(value):
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return None


def plan_purge(accounts, today):
    """Plan account warnings, deletions, and anonymisations."""
    if not isinstance(today, date):
        raise TypeError("today must be a datetime.date")

    candidates = []
    for account in accounts:
        email = account.get("email") or ""
        if account.get("on_litigation_hold"):
            continue
        if account.get("is_staff") and email.lower().endswith(_STAFF_DOMAIN):
            continue

        last_seen = _as_date(account.get("last_seen_at"))
        if last_seen is None:
            continue

        due = last_seen + timedelta(days=730)
        closed_at = _as_date(account.get("closed_at"))
        if closed_at is not None:
            due = min(due, closed_at + timedelta(days=30))

        account_id = account.get("account_id")
        if due <= today:
            unpaid = bool(account.get("unpaid_invoices"))
            candidates.append((account_id, due, account, "anonymise" if unpaid else "delete"))
        elif (
            due <= today + timedelta(days=40)
            and not account.get("closed_by_member")
        ):
            candidates.append((account_id, due, account, "warn"))

    deletions = sorted(
        (item for item in candidates if item[3] == "delete"),
        key=lambda item: (item[2].get("closed_at") is None, str(item[0])),
    )
    selected_deletions = {id(item) for item in deletions[:200]}

    actions = []
    for item in candidates:
        account_id, due, _account, action = item
        if action == "delete" and id(item) not in selected_deletions:
            continue
        actions.append({
            "account_id": account_id,
            "action": action,
            "due": due.isoformat(),
            "approved_by": None if action == "warn" else _APPROVER,
        })

    return sorted(actions, key=lambda action: str(action["account_id"]))