"""Account purge planning.

Input assumptions and edge-case choices:
- Each account is a mapping with ``id``, ``email``, ``last_seen_at``,
  ``last_login``, ``closed_at``, ``closed_by``, ``unpaid_invoices``,
  ``litigation_hold``, and ``status``. ``last_seen_at`` and any non-None
  ``closed_at`` are ``datetime.date`` values; ``closed_at`` may be None.
  ``last_login`` is accepted but not used.
- ``unpaid_invoices`` is treated by truthiness: a non-empty collection or
  true value means invoices are unpaid. Such accounts are anonymised; their
  invoices are retained while personal data is removed.
- ``closed_at`` being set identifies a closed account for delete-cap
  priority, even if ``status`` conflicts. If it is absent, ``status`` equal
  to ``"closed"`` (case-insensitive) identifies a closed account; all others
  are treated as inactive. ``status`` is used only for this priority.
- Warnings are for dates strictly after ``today`` and on or before
  ``today + 14 days``. Accounts already due receive their due action only.
- The excluded email domain is matched case-insensitively. Account IDs are
  assumed mutually sortable.

Returned action dictionaries contain exactly ``account_id``, ``action``,
``due``, and ``approved_by``. The output does not include email addresses.
"""

from datetime import date as _date, timedelta as _timedelta

__all__ = ["plan_purge"]

_APPROVER = "Þórdís Sveinbjörnsdóttir"
_EXCLUDED_DOMAIN = "@tidewater-klatring.no"
_DELETE_LIMIT = 200
_WARNING_WINDOW = _timedelta(days=14)


def plan_purge(accounts, today):
    """Return purge, anonymisation, and warning actions for eligible accounts."""
    candidates = []
    actions = []

    for account in accounts:
        email = account["email"]
        if email.lower().endswith(_EXCLUDED_DOMAIN) or account["litigation_hold"]:
            continue

        due = account["last_seen_at"] + _timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            due = min(due, closed_at + _timedelta(days=30))

        if due <= today:
            closed = closed_at is not None or str(account["status"]).lower() == "closed"
            if account["unpaid_invoices"]:
                actions.append({
                    "account_id": account["id"],
                    "action": "anonymise",
                    "due": due.isoformat(),
                    "approved_by": _APPROVER,
                })
            else:
                candidates.append((not closed, account["id"], {
                    "account_id": account["id"],
                    "action": "delete",
                    "due": due.isoformat(),
                    "approved_by": _APPROVER,
                }))
        elif due <= today + _WARNING_WINDOW and account["closed_by"] != "member":
            actions.append({
                "account_id": account["id"],
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    candidates.sort(key=lambda candidate: (candidate[0], candidate[1]))
    actions.extend(candidate[2] for candidate in candidates[:_DELETE_LIMIT])
    return sorted(actions, key=lambda action: action["account_id"])