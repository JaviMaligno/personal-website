"""Tidewater Climbing GDPR clean-up planner.

Pure function, standard library only. No I/O, no logging, no side effects.

Conflict noted: the house rule asks that every action dict carry the account's email.
R2 (exact keys) and R11 (email must not appear in any action dict) forbid that, so the
requirements were followed and no email is emitted.

Deliberate choice: last_login is checked for presence only, never for type or value (R3).
tenant is never read (R15).

Unit tests are not included in this module.
"""

from datetime import date, datetime, timedelta

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_CAP = 200
INACTIVITY = timedelta(days=730)
CLOSED_GRACE = timedelta(days=30)
WARN_WINDOW = timedelta(days=40)
REQUIRED_KEYS = (
    "id", "email", "status", "last_seen_at", "last_login",
    "closed_at", "closed_by", "unpaid_invoices", "litigation_hold",
)


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _ref(acc, index):
    # Reference accounts by id only, never by email.
    if isinstance(acc, dict) and "id" in acc:
        return f"account id {acc['id']!r}"
    return f"account at index {index}"


def _validate(accounts, today):
    if not _is_date(today):
        raise TypeError("today must be a datetime.date")
    if not isinstance(accounts, list):
        raise TypeError("accounts must be a list")
    id_kind = None
    for index, acc in enumerate(accounts):
        if not isinstance(acc, dict):
            raise TypeError(f"account at index {index} must be a dict")
        ref = _ref(acc, index)
        missing = [k for k in REQUIRED_KEYS if k not in acc]
        if missing:
            raise ValueError(f"{ref} is missing keys: {', '.join(missing)}")
        aid = acc["id"]
        if isinstance(aid, bool) or not isinstance(aid, (int, str)):
            raise TypeError(f"{ref}: id must be int or str")
        kind = int if isinstance(aid, int) else str
        if id_kind is None:
            id_kind = kind
        elif kind is not id_kind:
            raise TypeError(f"{ref}: id type differs from other accounts")
        if not isinstance(acc["email"], str):
            raise TypeError(f"{ref}: email must be str")
        if not _is_date(acc["last_seen_at"]):
            raise TypeError(f"{ref}: last_seen_at must be a date")
        if acc["closed_at"] is not None and not _is_date(acc["closed_at"]):
            raise TypeError(f"{ref}: closed_at must be a date or None")
        if acc["closed_by"] not in ("member", "staff", None):
            raise ValueError(f"{ref}: closed_by must be 'member', 'staff' or None")
        if acc["closed_at"] is not None and acc["closed_by"] is None:
            raise ValueError(f"{ref}: closed_by is required when closed_at is set")


def _effective_due(acc):
    due = acc["last_seen_at"] + INACTIVITY
    if acc["closed_at"] is not None:
        # OPEN: 30-day rule applies regardless of closed_by (includes staff-closed).
        due = min(due, acc["closed_at"] + CLOSED_GRACE)
    return due


def _action(acc, action, due):
    approved = None if action == "warn" else APPROVER
    return {
        "account_id": acc["id"],
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved,
    }


def plan_purge(accounts, today):
    _validate(accounts, today)

    due_now = []
    warns = []
    for acc in accounts:
        # R9: litigation hold produces no actions of any kind.
        if acc["litigation_hold"]:
            continue
        # R10: staff domain produces no actions.
        # OPEN: case-insensitive match (whitespace stripped too).
        if acc["email"].strip().lower().endswith(STAFF_DOMAIN):
            continue
        due = _effective_due(acc)
        if due <= today:
            due_now.append((acc, due))
        # OPEN: warn window is today < due <= today + 40 days.
        # R7: no warn for member-closed accounts.
        elif due <= today + WARN_WINDOW and acc["closed_by"] != "member":
            warns.append((acc, due))

    actions = []
    deletes = []
    for acc, due in due_now:
        # R8: unpaid invoices give anonymise instead of delete.
        # OPEN: truthiness; zero, empty list and None mean no unpaid invoices.
        if acc["unpaid_invoices"]:
            # OPEN: anonymise is not capped and not counted toward the 200.
            actions.append(_action(acc, "anonymise", due))
        else:
            deletes.append((acc, due))

    # R12: closed accounts first, then inactive; then due date, then id.
    deletes.sort(key=lambda p: (0 if p[0]["closed_at"] is not None else 1, p[1], p[0]["id"]))
    for acc, due in deletes[:DELETE_CAP]:
        actions.append(_action(acc, "delete", due))

    for acc, due in warns:
        actions.append(_action(acc, "warn", due))

    # R14: sort by account id ascending.
    actions.sort(key=lambda a: a["account_id"])
    return actions