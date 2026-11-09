"""Tidewater Climbing GDPR clean-up planner.

Entry point: plan_purge(accounts, today) -> list[dict]

Verification status: not executed. No tools were available in this run, so
the module and its tests were not run.

Open questions (client decision required; defaults implemented as noted):

Q1 Overflow beyond the 200-delete cap: NOT answered by the spec. Implemented
   silent deferral via statelessness: overflow deletes are simply not
   returned and remain due for the next run. The client must decide whether
   overflow should be reported.

Q2 Warn for accounts with unpaid invoices: NOT answered by the spec. Default
   implemented: warn applies per R5 (WARN_INCLUDES_UNPAID = True). Set the
   constant to False to exclude these accounts from warn.

Q3 Missing last_seen_at: raises ValueError naming the account id only, never
   the email. Missing closed_at key is treated as None (open account, only
   the R2 date applies). The client must confirm both behaviours.

Q4 status field: NOT answered by the spec. It is read by no rule and does not
   affect any decision. The client must confirm this.

Q5 Warn window boundary: answered by R5. today + 40 days is included.

Other ambiguities and resolutions:
- closed_by values other than "member" or "staff" are treated as not member
  for R5, so warn still applies.
- Staff check lowercases the email and tests the suffix only, so lookalike
  domains such as x@tidewater-klatring.no.example.com are not staff.
- Delete cap ordering: closed accounts (closed_at is not None) first, then
  due date ascending, then account id ascending.
- Anonymise and warn actions are never counted against or dropped by the cap.
- No logging is performed, and no email appears in any output key or value.
"""

from datetime import date, timedelta
from typing import Any

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
DELETE_CAP = 200
INACTIVITY = timedelta(days=730)
CLOSED_GRACE = timedelta(days=30)
WARN_WINDOW = timedelta(days=40)
WARN_INCLUDES_UNPAID = True  # Q2 default; set False to exclude unpaid accounts from warn


def _due_date(acc: dict[str, Any]) -> date:
    last_seen = acc.get("last_seen_at")
    if last_seen is None:
        raise ValueError(f"account {acc.get('id')!r}: last_seen_at is missing")
    due = last_seen + INACTIVITY
    closed_at = acc.get("closed_at")
    if closed_at is not None:
        due = min(due, closed_at + CLOSED_GRACE)
    return due


def _excluded(acc: dict[str, Any]) -> bool:
    if acc.get("litigation_hold"):
        return True
    email = str(acc.get("email") or "").lower()
    return email.endswith(STAFF_SUFFIX)


def _action(acc_id: Any, action: str, due: date, approver: str | None) -> dict[str, Any]:
    return {
        "account_id": acc_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approver,
    }


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    deletes: list[tuple[int, date, Any]] = []
    others: list[dict[str, Any]] = []

    for acc in accounts:
        if _excluded(acc):
            continue
        due = _due_date(acc)
        acc_id = acc["id"]
        unpaid = bool(acc.get("unpaid_invoices"))

        if due <= today:
            if unpaid:
                others.append(_action(acc_id, "anonymise", due, APPROVER))
            else:
                closed_flag = 0 if acc.get("closed_at") is not None else 1
                deletes.append((closed_flag, due, acc_id))
        elif due <= today + WARN_WINDOW:
            if acc.get("closed_by") == "member":
                continue
            if unpaid and not WARN_INCLUDES_UNPAID:
                continue
            others.append(_action(acc_id, "warn", due, None))

    deletes.sort(key=lambda t: (t[0], t[1], t[2]))
    for _, due, acc_id in deletes[:DELETE_CAP]:
        others.append(_action(acc_id, "delete", due, APPROVER))

    others.sort(key=lambda a: a["account_id"])
    return others