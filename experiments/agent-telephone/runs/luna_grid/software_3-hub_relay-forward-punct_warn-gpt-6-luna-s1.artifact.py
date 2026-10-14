"""Acceptance criteria for plan_purge:

- Uses last_seen_at, not last_login; inactivity is due 730 days after last_seen_at.
- Uses the earlier of the inactivity deadline and the closed_at + 30-day deadline.
- Includes actions due today; warns only for deadlines after today and within the next 14 days.
- Does not warn accounts closed by the member.
- Excludes staff email addresses ending in @tidewater-klatring.no and all litigation-held accounts.
- Anonymises due accounts with unpaid invoices; deletes other due accounts.
- Caps deletions at 200, prioritising closed accounts; anonymisations do not count toward the cap.
- Includes the DPO approver for deletes and anonymisations; warnings have no approver.
- Returns only account_id, email, action, due, and approved_by; due is an ISO-format string.
- Sorts final actions by account ID.
"""

from datetime import date, timedelta
from typing import Any


DPO = "Þórdís Sveinbjörnsdóttir"
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    """Return due purge actions and upcoming warnings for the supplied accounts."""
    candidates = []
    warnings = []

    for account in accounts:
        email = account["email"]
        if email.lower().endswith(STAFF_EMAIL_SUFFIX) or account["litigation_hold"]:
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        closed_at = account["closed_at"]
        if closed_at is not None:
            closed_due = closed_at + timedelta(days=30)
            due = min(due, closed_due)

        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            candidates.append((account, due, action))
        elif (
            due <= today + timedelta(days=14)
            and not (
                closed_at is not None
                and account["closed_by"] == "member"
            )
        ):
            warnings.append((account, due))

    deletions = [item for item in candidates if item[2] == "delete"]
    deletions.sort(
        key=lambda item: (
            item[0]["closed_at"] is None,
            item[0]["id"],
        )
    )
    allowed_deletions = {id(item[0]) for item in deletions[:200]}

    actions = []
    for account, due, action in candidates:
        if action == "delete" and id(account) not in allowed_deletions:
            continue
        actions.append(
            {
                "account_id": account["id"],
                "email": account["email"],
                "action": action,
                "due": due.isoformat(),
                "approved_by": DPO,
            }
        )

    for account, due in warnings:
        actions.append(
            {
                "account_id": account["id"],
                "email": account["email"],
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            }
        )

    actions.sort(key=lambda action: action["account_id"])
    return actions