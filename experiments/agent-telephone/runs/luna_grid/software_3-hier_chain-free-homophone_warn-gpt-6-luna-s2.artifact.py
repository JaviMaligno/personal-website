"""Plan account purges and warnings.

Dates may be datetime.date instances, datetime instances (treated as dates), or
strict ISO YYYY-MM-DD strings. Invalid dates are ignored. If last_seen_at is
missing or invalid, a valid closure date supplies the due date; otherwise the
account is skipped. A valid closure date can also move the inactivity due date
earlier. Member closure means closed_by_member is exactly True.

Accounts without an account_id, accounts on litigation hold, and staff whose
email ends in @tidewater-klatring.no (case-insensitive) are skipped. Due
accounts with unpaid invoices are anonymised; other due accounts are deleted.
Warnings apply to non-member-closed accounts due within the next 40 days.
Only deletions count toward the cap of 200; closed accounts rank first,
followed by due date and account ID. Actions are sorted by account ID, then
action type. Returned actions never contain email addresses.
"""

from datetime import date, datetime, timedelta
import re

__all__ = ["plan_purge"]

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_APPROVER = "DPO Þórdís Sveinbjörnsdóttir"


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and _ISO_DATE.fullmatch(value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return None


def _id_key(account_id):
    return (type(account_id).__name__, repr(account_id))


def plan_purge(accounts, today):
    today = _as_date(today)
    if today is None:
        raise ValueError("today must be a valid date")

    actions = []
    deletions = []

    for account in accounts:
        if "account_id" not in account or account["account_id"] is None:
            continue
        if account.get("litigation_hold"):
            continue

        email = account.get("email")
        if isinstance(email, str) and email.casefold().endswith(
            "@tidewater-klatring.no"
        ):
            continue

        closed_at = _as_date(account.get("closed_at"))
        last_seen_at = _as_date(account.get("last_seen_at"))
        if last_seen_at is None:
            if closed_at is None:
                continue
            due = closed_at + timedelta(days=30)
        else:
            due = last_seen_at + timedelta(days=730)
            if closed_at is not None:
                due = min(due, closed_at + timedelta(days=30))

        account_id = account["account_id"]
        member_closed = account.get("closed_by_member") is True

        if due <= today:
            action = {
                "account_id": account_id,
                "action": "anonymise" if account.get("has_unpaid_invoices") else "delete",
                "due": due.isoformat(),
                "approved_by": _APPROVER,
            }
            if action["action"] == "delete":
                deletions.append((closed_at is None, due, _id_key(account_id), action))
            else:
                actions.append(action)
        elif not member_closed and due <= today + timedelta(days=40):
            actions.append({
                "account_id": account_id,
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    deletions.sort(key=lambda item: item[:3])
    actions.extend(item[3] for item in deletions[:200])
    actions.sort(key=lambda item: (_id_key(item["account_id"]), item["action"]))
    return actions