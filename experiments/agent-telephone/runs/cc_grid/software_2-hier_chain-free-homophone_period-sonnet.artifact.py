"""Seat-upgrade proration for Fernhollow Studios (EUR, integer cents only).

Open questions for the client, with the defaults implemented here:
 1. PERIOD_DAYS = 13 is suspicious (typo, test value, or 30?); 13 is used as stated, capped.
 2. Skip threshold applies before VAT (amount_cents).
 3. "Over 500 EUR" means strictly more than 50000 cents.
 4. A change after period_end, or time of day on the change date: date only, clamped at 0, no lines.
 5. Change date is taken in period_end's own timezone.
 6. Credit description uses the old plan name, charge the new one.
 7. Downgrade check is per seat price; an equal price is a no-op.
 8. Credit rounds up and charge rounds down (both cost the company); confirm intent.
 9. Currency is EUR only.
10. The same billable_seats applies to the old and new plan.
11. canceled and past_due return [].
12. Bad input raises InvalidSubscriptionError.
13. Truncation style is "..." with the full date kept.
14. The 500 EUR approval check uses the pre-VAT credit (credits carry no VAT).
15. Credit amount_cents is a positive magnitude; the sign is carried by kind.

Deviation from the house rule "VAT applies to every invoice line, credits
included": the task brief explicitly sets credit vat_cents = 0, so it is followed.
"""
from __future__ import annotations

import unicodedata
from datetime import datetime
from typing import Any

__all__ = ["prorate_seats", "InvalidSubscriptionError"]

# ---- Tunable defaults -------------------------------------------------------
PERIOD_DAYS = 13                 # suspicious; awaiting client confirmation
SKIP_BELOW_CENTS = 50            # lines with pre-VAT amount < this are dropped
VAT_PERCENT = 21
APPROVAL_LIMIT_CENTS = 50000     # strictly more than this needs the senior approver
DEFAULT_APPROVER = unicodedata.normalize("NFC", "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o")
SENIOR_APPROVER = unicodedata.normalize("NFC", "Ram\u00f3n Etxeberria-Go\u00f1i")
MAX_DESCRIPTION_LEN = 80
ELLIPSIS = "..."
CREDIT_TEMPLATE = "Credit: unused {plan} seats until {date}"
CHARGE_TEMPLATE = "Charge: {plan} seats until {date}"
_PASS_THROUGH_STATUSES = frozenset({"trialing", "canceled", "past_due"})

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


class InvalidSubscriptionError(ValueError):
    """Raised when the subscription, plan or timestamps are invalid."""


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_aware(v: Any) -> bool:
    return isinstance(v, datetime) and v.tzinfo is not None and v.utcoffset() is not None


def _validate(subscription: Any, new_plan: Any, changed_at: Any) -> None:
    """Validate all inputs; raise InvalidSubscriptionError on any problem."""
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise InvalidSubscriptionError("subscription and new_plan must be dicts")
    for k in _SUB_KEYS:
        if k not in subscription:
            raise InvalidSubscriptionError(f"missing subscription key: {k}")
    for k in _PLAN_KEYS:
        if k not in new_plan:
            raise InvalidSubscriptionError(f"missing new_plan key: {k}")
    for v in (subscription["seat_price_cents"], subscription["seats"],
              subscription["billable_seats"], new_plan["seat_price_cents"]):
        if not _is_int(v):
            raise InvalidSubscriptionError("money and seat values must be int")
        if v < 0:
            raise InvalidSubscriptionError("prices and seats must be non-negative")
    if subscription["billable_seats"] > subscription["seats"]:
        raise InvalidSubscriptionError("billable_seats exceeds seats")
    if not _is_aware(changed_at) or not _is_aware(subscription["period_end"]):
        raise InvalidSubscriptionError("datetimes must be timezone-aware")
    for name in (subscription["plan_name"], new_plan["name"]):
        if not isinstance(name, str) or not name.strip():
            raise InvalidSubscriptionError("plan names must be non-empty strings")
    if not isinstance(subscription["status"], str):
        raise InvalidSubscriptionError("status must be a string")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise InvalidSubscriptionError("vat_id must be a string or None")


def _days_left(changed_at: datetime, period_end: datetime) -> int:
    """Whole days from the change date to period end, clamped to [0, PERIOD_DAYS]."""
    change_date = changed_at.astimezone(period_end.tzinfo).date()
    days = (period_end.date() - change_date).days
    return max(0, min(PERIOD_DAYS, days))


def _prorated_cents(price: int, seats: int, days: int, rounding: str) -> int:
    """Single-rounding proration on the whole product; rounding is 'up' or 'down'."""
    num = price * seats * days
    if rounding == "up":
        return -(-num // PERIOD_DAYS)
    return num // PERIOD_DAYS


def _vat_for_charge(amount_cents: int, vat_id: str | None) -> int:
    """21% floor VAT, or 0 under reverse charge (non-blank vat_id)."""
    if isinstance(vat_id, str) and vat_id.strip():
        return 0
    return amount_cents * VAT_PERCENT // 100


def _approver_for_credit(amount_cents: int) -> str:
    """Senior approver only for credits strictly above the limit."""
    return SENIOR_APPROVER if amount_cents > APPROVAL_LIMIT_CENTS else DEFAULT_APPROVER


def _describe(template: str, plan: str, date: str) -> str:
    """Render a description of at most 80 code points, shortening only the plan name."""
    plan = unicodedata.normalize("NFC", plan)
    text = template.format(plan=plan, date=date)
    if len(text) <= MAX_DESCRIPTION_LEN:
        return text
    overhead = len(template.format(plan="", date=date))
    budget = MAX_DESCRIPTION_LEN - overhead
    keep = budget - len(ELLIPSIS)
    short = (plan[:keep].rstrip() + ELLIPSIS) if keep > 0 else ELLIPSIS
    return template.format(plan=short, date=date)


def prorate_seats(subscription: dict, new_plan: dict, changed_at: datetime) -> list[dict]:
    """Return credit (old plan) then charge (new plan) lines for a mid-period upgrade."""
    _validate(subscription, new_plan, changed_at)

    status = subscription["status"]
    if status in _PASS_THROUGH_STATUSES:
        return []
    if status != "active":
        raise InvalidSubscriptionError(f"unknown status: {status!r}")

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:
        return []

    seats = subscription["billable_seats"]
    if seats == 0:
        return []

    period_end = subscription["period_end"]
    days = _days_left(changed_at, period_end)
    if days == 0:
        return []

    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines: list[dict] = []

    credit = _prorated_cents(old_price, seats, days, "up")
    if credit >= SKIP_BELOW_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe(CREDIT_TEMPLATE, subscription["plan_name"], date_str),
            "approved_by": _approver_for_credit(credit),
        })

    charge = _prorated_cents(new_price, seats, days, "down")
    if charge >= SKIP_BELOW_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": _vat_for_charge(charge, subscription["vat_id"]),
            "description": _describe(CHARGE_TEMPLATE, new_plan["name"], date_str),
            "approved_by": None,
        })

    return lines