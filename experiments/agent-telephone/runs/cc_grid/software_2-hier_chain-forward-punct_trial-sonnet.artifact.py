"""Seat-upgrade proration for Fernhollow Studios.

Public entry point: prorate_seats(subscription, new_plan, changed_at).

Settled decisions
1. Seats: billable_seats is used for both old and new plan. `seats` and
   `legacy_discount` are ignored entirely and not validated.
2. Days left: delta = period_end - changed_at (aware datetimes, absolute-time
   arithmetic). Whole days = delta // timedelta(days=1) (floor, partial days
   dropped, so 29.9 days = 29), clamped to 0..30. The period is always 30
   days. days_left == 0 (including changed_at >= period_end) gives [].
3. Integer math only. Credit = ceil(old_price * seats * days_left / 30) via
   -(-n // 30). Charge = floor(new_price * seats * days_left / 30) via n // 30.
   The credit covers the old plan, the charge the new plan, for the days left.
4. Returns [] when status == "trialing" (read as "no proration at all"), when
   the new price < old price (downgrade, applies at renewal), or when the new
   price == old price (nothing to prorate). Other statuses proceed normally.
   Inputs are validated first, then the early returns apply.
5. Skip rule, per line and independent, on the rounded amount: a line with
   amount_cents < 50 is dropped. A skipped credit does not suppress the
   charge and vice versa.
6. Credit approval: rounded credit amount_cents > 50000 (strictly over EUR 500,
   evaluated before the skip rule) gives approved_by "Ramón Etxeberria-Goñi",
   otherwise "Nguyễn Thị Phương Thảo". Charges have approved_by None.
7. VAT: charge vat_cents = amount_cents * 21 // 100 (floor, never overcharging
   the customer), but 0 if vat_id is a non-empty string (reverse charge).
   Credits always have vat_cents 0 (this overrides the generic house rule
   that VAT applies to credits, as instructed). The 50-cent skip tests the
   charge amount before VAT. Credit correctness has priority over VAT.
8. Descriptions: "Credit unused {plan} until YYYY-MM-DD" (plan = old plan_name)
   and "Charge prorated {plan} until YYYY-MM-DD" (plan = new plan name). The
   date is period_end.date() in period_end's own tzinfo (no conversion). Max
   80 characters (code points). If too long, only the plan name is truncated
   and a single "…" is appended so the total is exactly 80; the full date is
   always kept. No truncation at exactly 80.
9. Output order: credit then charge. Each dict has exactly the keys
   subscription_id, kind, amount_cents, vat_cents, description, approved_by.
   All amounts are plain int.

Validation: TypeError for wrong types, ValueError for bad values. Prices and
billable_seats must be int (not bool, not float) and >= 0. Plan names are
non-empty str, status is str, vat_id is None or str. period_end and changed_at
must be timezone-aware datetimes (tzinfo and utcoffset() not None).
"""
from collections.abc import Mapping
from datetime import datetime, timedelta

__all__ = ["prorate_seats"]

_PERIOD_DAYS = 30
_MAX_DESC = 80
_MIN_LINE_CENTS = 50
_BIG_CREDIT_CENTS = 50000
_VAT_PERCENT = 21
_APPROVER_STANDARD = "Nguyễn Thị Phương Thảo"
_APPROVER_LARGE = "Ramón Etxeberria-Goñi"

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def _need_keys(obj, keys, label):
    if not isinstance(obj, Mapping):
        raise TypeError(f"{label} must be a mapping, got {type(obj).__name__}")
    missing = [k for k in keys if k not in obj]
    if missing:
        raise ValueError(f"{label} is missing required keys: {', '.join(missing)}")


def _nonneg_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an int, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{label} must be >= 0, got {value}")
    return value


def _name(value, label):
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a str, got {type(value).__name__}")
    if not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime, got {type(value).__name__}")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value


def _describe(prefix, plan, date_str):
    suffix = f" until {date_str}"
    full = f"{prefix} {plan}{suffix}"
    if len(full) <= _MAX_DESC:
        return full
    room = _MAX_DESC - len(prefix) - 1 - len(suffix) - 1  # -1 for the ellipsis
    return f"{prefix} {plan[:max(room, 0)]}…{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    _need_keys(subscription, _SUB_KEYS, "subscription")
    _need_keys(new_plan, _PLAN_KEYS, "new_plan")
    sub_id = subscription["id"]
    status = subscription["status"]
    if not isinstance(status, str):
        raise TypeError(f"status must be a str, got {type(status).__name__}")
    old_name = _name(subscription["plan_name"], "plan_name")
    old_price = _nonneg_int(subscription["seat_price_cents"], "seat_price_cents")
    seats = _nonneg_int(subscription["billable_seats"], "billable_seats")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError(f"vat_id must be None or str, got {type(vat_id).__name__}")
    period_end = _aware(subscription["period_end"], "period_end")
    new_name = _name(new_plan["name"], "new_plan name")
    new_price = _nonneg_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    changed_at = _aware(changed_at, "changed_at")

    if status == "trialing" or new_price <= old_price:
        return []

    days_left = (period_end - changed_at) // timedelta(days=1)
    days_left = max(0, min(_PERIOD_DAYS, days_left))
    if days_left == 0:
        return []

    date_str = period_end.date().isoformat()
    lines = []

    credit = -(-(old_price * seats * days_left) // _PERIOD_DAYS)
    if credit >= _MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit unused", old_name, date_str),
            "approved_by": (_APPROVER_LARGE if credit > _BIG_CREDIT_CENTS
                            else _APPROVER_STANDARD),
        })

    charge = (new_price * seats * days_left) // _PERIOD_DAYS
    if charge >= _MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if vat_id else charge * _VAT_PERCENT // 100,
            "description": _describe("Charge prorated", new_name, date_str),
            "approved_by": None,
        })

    return lines