"""GDPR member-account purge planner for Tidewater Climbing.

Note: the spec (R1/R9) asks for exactly four keys and no email, but the house
rule says every action dict also carries the account's `email`. The house rule
is followed here, so each action has a fifth key, `email`. Drop it from
_action if R9 should win.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

MAX_DELETIONS = 200
DPO_APPROVER = "Tordis Svenbjorn Dottir"
STAFF_SUFFIX = "@tidewater-klatring.no"
_REQUIRED = ("id", "email", "status", "last_seen_at", "last_login", "closed_at",
             "closed_by", "unpaid_invoices", "litigation_hold")


def _is_staff(email: Any) -> bool:
    """R8: staff email check, safe for None/non-str."""
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def _due_date(acc: dict[str, Any]) -> date | None:
    """R2/R3: earlier of inactivity due and closed due; last_login is never read."""
    cands = []
    if acc["last_seen_at"] is not None:
        cands.append(acc["last_seen_at"] + timedelta(days=730))
    if acc["closed_at"] is not None:
        cands.append(acc["closed_at"] + timedelta(days=30))
    return min(cands) if cands else None


def _action(acc: dict[str, Any], action: str, due: date) -> dict[str, Any]:
    return {
        "account_id": acc["id"],
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else DPO_APPROVER,
        "email": acc["email"],
    }


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    """Return purge actions sorted by account_id; pure, inputs are not mutated."""
    seen = set()
    for acc in accounts:
        missing = [k for k in _REQUIRED if k not in acc]
        if missing:
            raise ValueError(f"account {acc.get('id')!r} missing keys: {missing}")
        if acc["id"] in seen:
            raise ValueError(f"duplicate account id: {acc['id']!r}")
        seen.add(acc["id"])

    out: list[dict[str, Any]] = []
    deletes: list[tuple[Any, dict[str, Any], date]] = []
    horizon = today + timedelta(days=14)
    for acc in accounts:
        if _is_staff(acc["email"]) or acc["litigation_hold"]:
            continue
        due = _due_date(acc)
        if due is None:
            continue
        if due <= today:
            if acc["unpaid_invoices"]:
                out.append(_action(acc, "anonymise", due))
            else:
                key = (acc["closed_at"] is None, due, acc["id"])
                deletes.append((key, acc, due))
        elif due <= horizon:
            if acc["closed_at"] is not None and acc["closed_by"] == "member":
                continue
            out.append(_action(acc, "warn", due))

    deletes.sort(key=lambda t: t[0])
    out.extend(_action(a, "delete", d) for _, a, d in deletes[:MAX_DELETIONS])
    out.sort(key=lambda a: a["account_id"])
    return out