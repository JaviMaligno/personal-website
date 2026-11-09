"""Seat-change proration for Fernhollow Studios billing.

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list[dict]

Assumptions:
- Integer arithmetic only. A billing period is always 30 days.
- All datetimes (changed_at, period_end) must be timezone-aware, else ValueError.
- billable_seats is used; the `seats` and `legacy_discount` fields are ignored.
  Missing/None/negative/non-int billable_seats -> ValueError; 0 -> no lines.
- Prices must be non-bool ints (cents), else ValueError.
- status "trialing" -> no lines. Any other or unknown status is prorated.
- New price lower than old (downgrade) -> no lines (applies at renewal).
  Equal price -> no lines (nothing to prorate).
- days_left: changed_at is converted to period_end's timezone, then the whole
  calendar-day difference of the dates is taken, clamped to [0, 30]. 0 -> no lines.
- credit = ceil(old_price*seats*days/30); charge = floor(new_price*seats*days/30).
- Each line is skipped independently if its net amount is under 50 cents.
- Charge VAT = floor(amount*21/100), or 0 when vat_id is non-blank after strip
  (reverse charge). Credits carry vat_cents 0 (the brief overrides the generic
  house rule of VAT on every line).
- Credit comes first, then charge.
- Credit approver is "Nguyễn Thị Phương Thảo"; if the credit amount is strictly
  over 50000 cents, "Ramón Etxeberria-Goñi". Charges: approved_by None.
- Descriptions are at most 80 characters, "Credit: unused {old plan} seats until
  YYYY-MM-DD" and "Charge: unused {new plan} seats until YYYY-MM-DD", with the
  date in period_end's own timezone. Plan names (NFC-normalised) are truncated
  with "…" when needed; the date is never dropped.
"""
import unicodedata
from datetime import datetime

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
BIG_CREDIT_CENTS = 50000
MAX_DESC = 80
APPROVER = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
BIG_APPROVER = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")


def _int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _aware(value, name):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value


def _describe(prefix, plan, date_str):
    plan = unicodedata.normalize("NFC", str(plan))
    head, tail = f"{prefix} unused ", f" seats until {date_str}"
    room = MAX_DESC - len(head) - len(tail)
    if len(plan) > room:
        plan = plan[: max(room - 1, 1)] + "…"
    return head + plan + tail


def prorate_seats(subscription, new_plan, changed_at):
    period_end = _aware(subscription.get("period_end"), "period_end")
    _aware(changed_at, "changed_at")

    seats = subscription.get("billable_seats")
    if seats is None:
        raise ValueError("billable_seats is required")
    seats = _int(seats, "billable_seats")
    if seats < 0:
        raise ValueError("billable_seats must not be negative")
    old_price = _int(subscription.get("seat_price_cents"), "seat_price_cents")
    new_price = _int(new_plan.get("seat_price_cents"), "new seat_price_cents")

    if subscription.get("status") == "trialing" or seats == 0:
        return []
    if new_price <= old_price:
        return []

    local_change = changed_at.astimezone(period_end.tzinfo)
    days = (period_end.date() - local_change.date()).days
    days = max(0, min(PERIOD_DAYS, days))
    if days == 0:
        return []

    date_str = period_end.date().isoformat()
    sub_id = subscription.get("id")
    lines = []

    credit = -(-(old_price * seats * days) // PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit:", subscription.get("plan_name", ""), date_str),
            "approved_by": BIG_APPROVER if credit > BIG_CREDIT_CENTS else APPROVER,
        })

    charge = (new_price * seats * days) // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        vat_id = subscription.get("vat_id")
        has_vat_id = bool(vat_id.strip()) if isinstance(vat_id, str) else bool(vat_id)
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if has_vat_id else (charge * VAT_PERCENT) // 100,
            "description": _describe("Charge:", new_plan.get("name", ""), date_str),
            "approved_by": None,
        })

    return lines