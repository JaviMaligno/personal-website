"""Seat-change proration for subscriptions.

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list[dict].

NOTE: no execution tools were available when this was written, so the module
has not been run and test_prorate.py has NOT been written or executed.

Assumptions needing client confirmation:
- Currency is EUR, amounts are integer cents; the 50000 approver limit is EUR 500.
- Threshold (drop if < 50 cents) applies after rounding, to each line separately;
  exactly 50 is kept.
- Equal price is not a downgrade: both lines are computed (they net out) and
  each is emitted if >= 50 cents.
- Days left = floor of whole days between changed_at and period_end (partial
  days dropped, computed on absolute instants so different UTC offsets are
  handled correctly), clamped to 0..30. Period is always 30 days.
- Credit = ceil(billable_seats*old*days/30); charge = floor(...new...).
- VAT 21% on the charge is rounded DOWN (floor), mirroring the "no rounding in
  our favour" principle; credits never carry VAT.
- vat_id counts only if it is a string with non-whitespace content.
- legacy_discount and `seats` are ignored; billing uses billable_seats.
- Description date is period_end.date() in period_end's own timezone.
- Description length is counted in Unicode code points (max 80).
- Early-return order: validate, trialing, zero billable seats, downgrade,
  changed_at >= period_end.
"""
import unicodedata
from datetime import datetime, timedelta

_NFC = lambda s: unicodedata.normalize("NFC", s)
APPROVER_DEFAULT = _NFC("Nguyễn Thị Phương Thảo")
APPROVER_LARGE = _NFC("Ramón Etxeberria-Goñi")
LARGE_CREDIT_CENTS = 50000
MIN_LINE_CENTS = 50
MAX_DESC = 80
PERIOD_DAYS = 30
VAT_PERCENT = 21
ELLIPSIS = "…"

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents",
             "billable_seats", "vat_id", "period_end")


def _check_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an int, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{label} must be >= 0, got {value}")


def _check_aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware (naive datetime rejected)")


def _check_name(value, label):
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a str")
    if not value.strip():
        raise ValueError(f"{label} must not be empty")


def _validate(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict):
        raise TypeError("subscription must be a dict")
    if not isinstance(new_plan, dict):
        raise TypeError("new_plan must be a dict")
    for k in _SUB_KEYS:
        if k not in subscription:
            raise ValueError(f"subscription is missing key '{k}'")
    for k in ("name", "seat_price_cents"):
        if k not in new_plan:
            raise ValueError(f"new_plan is missing key '{k}'")
    if not isinstance(subscription["status"], str):
        raise TypeError("subscription.status must be a str")
    _check_name(subscription["plan_name"], "subscription.plan_name")
    _check_name(new_plan["name"], "new_plan.name")
    _check_int(subscription["seat_price_cents"], "subscription.seat_price_cents")
    _check_int(subscription["billable_seats"], "subscription.billable_seats")
    _check_int(new_plan["seat_price_cents"], "new_plan.seat_price_cents")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("subscription.vat_id must be a str or None")
    _check_aware(subscription["period_end"], "subscription.period_end")
    _check_aware(changed_at, "changed_at")


def _days_left(changed_at, period_end):
    days = (period_end - changed_at) // timedelta(days=1)
    return max(0, min(PERIOD_DAYS, days))


def _describe(prefix, name, date_str):
    suffix = f" until {date_str}"
    room = MAX_DESC - len(prefix) - len(suffix)
    if len(name) > room:
        name = name[:max(room - 1, 0)] + ELLIPSIS
    return f"{prefix}{name}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    _validate(subscription, new_plan, changed_at)
    if subscription["status"] == "trialing":
        return []
    seats = subscription["billable_seats"]
    if seats == 0:
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []
    period_end = subscription["period_end"]
    if changed_at >= period_end:
        return []

    days = _days_left(changed_at, period_end)
    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]

    credit = -(-(seats * old_price * days) // PERIOD_DAYS)
    charge = (seats * new_price * days) // PERIOD_DAYS
    vat_id = subscription["vat_id"]
    reverse_charge = bool(vat_id and vat_id.strip())
    vat = 0 if reverse_charge else (charge * VAT_PERCENT) // 100

    lines = []
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": int(credit),
            "vat_cents": 0,
            "description": _describe("Credit unused ", subscription["plan_name"], date_str),
            "approved_by": APPROVER_LARGE if credit > LARGE_CREDIT_CENTS else APPROVER_DEFAULT,
        })
    if charge >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": int(charge),
            "vat_cents": int(vat),
            "description": _describe("Charge ", new_plan["name"], date_str),
            "approved_by": None,
        })
    return lines