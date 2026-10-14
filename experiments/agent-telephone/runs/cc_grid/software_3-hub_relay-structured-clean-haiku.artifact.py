"""Plan GDPR purge actions for Tidewater Climbing accounts.

Single entry point: plan_purge(accounts, today). Standard library only.
Calendar-day arithmetic, no timezone handling.

Notes:
- Duplicate account ids are not rejected. Each row is planned independently,
  so duplicates can appear in the output.
- closed_by of None (no recorded closure) does not suppress warns.
  "member" and any value other than "staff" or None suppress warns.
- Test file not included in this reply and not executed.
"""

from datetime import date, timedelta

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200


def _is_staff(email):
    return isinstance(email, str) and email.strip().casefold().endswith(STAFF_DOMAIN)


def _warn_suppressed(closed_by):
    return closed_by not in (None, "staff")


def _action(account_id, action, due):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": APPROVER if action in ("delete", "anonymise") else None,
    }


def plan_purge(accounts, today):
    horizon = today + timedelta(days=WARN_WINDOW_DAYS)
    deletes = []
    others = []

    for acc in accounts:
        last_seen = acc.get("last_seen_at")
        if last_seen is None or acc.get("litigation_hold") or _is_staff(acc.get("email")):
            continue

        effective = last_seen + timedelta(days=INACTIVITY_DAYS)
        closed_at = acc.get("closed_at")
        closed = closed_at is not None
        if closed:
            effective = min(effective, closed_at + timedelta(days=CLOSED_GRACE_DAYS))

        account_id = acc["id"]

        if effective <= today:
            action = "anonymise" if acc.get("unpaid_invoices") else "delete"
            item = _action(account_id, action, effective)
            if action == "delete":
                deletes.append((0 if closed else 1, effective, account_id, item))
            else:
                others.append(item)
        elif effective <= horizon:
            if not _warn_suppressed(acc.get("closed_by")):
                others.append(_action(account_id, "warn", effective))

    deletes.sort(key=lambda t: (t[0], t[1], t[2]))
    result = [t[3] for t in deletes[:DELETE_CAP]] + others
    result.sort(key=lambda a: a["account_id"])
    return result