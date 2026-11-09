from datetime import date, timedelta
from typing import Any


APPROVER = "DPO Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_CAP = 200
WARNING_WINDOW = 14
INACTIVITY_PERIOD = 730
CLOSURE_PERIOD = 30


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    """Plan due account actions and warnings."""
    due_deletes: list[tuple[bool, date, str, dict[str, Any]]] = []
    actions: list[dict[str, Any]] = []
    warning_cutoff = today + timedelta(days=WARNING_WINDOW)

    for account in accounts:
        email = account.get("email", "")
        if account.get("litigation_hold") or email.lower().endswith(STAFF_DOMAIN):
            continue

        last_seen = account.get("last_seen_at")
        if last_seen is None:
            continue

        inactivity_due = last_seen + timedelta(days=INACTIVITY_PERIOD)
        due = inactivity_due
        from_closure = False
        closed_at = account.get("closed_at")
        if account.get("status", "").lower() == "closed" and closed_at is not None:
            closure_due = closed_at + timedelta(days=CLOSURE_PERIOD)
            if closure_due < due:
                due = closure_due
                from_closure = True

        account_id = account.get("id")
        if due <= today:
            action = "anonymise" if account.get("unpaid_invoices") else "delete"
            item = {
                "account_id": account_id,
                "action": action,
                "due": due.isoformat(),
                "approved_by": APPROVER,
                "email": email,
            }
            if action == "delete":
                due_deletes.append((from_closure, due, str(account_id), item))
            else:
                actions.append(item)
        elif due <= warning_cutoff:
            closed_by = account.get("closed_by")
            holder_closed = isinstance(closed_by, str) and closed_by.strip().lower() in {
                "account holder", "account_holder", "member", "user", "customer",
            }
            if not holder_closed:
                actions.append({
                    "account_id": account_id,
                    "action": "warn",
                    "due": due.isoformat(),
                    "approved_by": None,
                    "email": email,
                })

    due_deletes.sort(key=lambda row: (not row[0], row[1], row[2]))
    actions.extend(item for _, _, _, item in due_deletes[:DELETE_CAP])
    actions.sort(key=lambda item: (str(item["account_id"]), item["action"]))
    return actions