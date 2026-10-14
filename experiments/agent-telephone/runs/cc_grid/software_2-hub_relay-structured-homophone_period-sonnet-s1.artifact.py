"""Seat proration for Fernhollow Studios billing (single public function: prorate_seats).

Open client questions (implemented with the defaults below):
  - PERIOD_DAYS = 13 may be a typo.
  - VAT 21% versus Portugal's 23%; reverse charge is normally only for cross-border B2B.
  - Equal price is treated as not a downgrade and is prorated normally.
  - Credit amount sign: amount_cents is a non-negative magnitude.
  - The 50-cent minimum skip applies to each line independently.
  - Description date uses the calendar date of period_end in its own timezone.
  - VAT rounding direction: integer floor.
  - Other statuses (canceled, past_due, paused) prorate normally.

Delivery note: no tools were available when this was written, so the pytest
tests were NOT written and NOT run. Nothing here is verified by execution.
VAT was not cut.
"""
import unicodedata
from datetime import datetime, timedelta

PERIOD_DAYS = 13
VAT_RATE_PERCENT = 21
MIN_LINE_AMOUNT_CENTS = 50
APPROVAL_THRESHOLD_CENTS = 50000
DEFAULT_APPROVER = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
SENIOR_APPROVER = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")
MAX_DESCRIPTION_LENGTH = 80
TRIALING_STATUS = "trialing"
ELLIPSIS = "…"

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")
_CREDIT_TEMPLATE = "Credit: unused {plan} seats until {date}"
_CHARGE_TEMPLATE = "Charge: {plan} seats until {date}"


def _check_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an int")
    if value < 0:
        raise ValueError(f"{label} must not be negative")


def _check_aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _description(template, plan, date_str):
    full = template.format(plan=plan, date=date_str)
    if len(full) <= MAX_DESCRIPTION_LENGTH:
        return full
    plan = unicodedata.normalize("NFC", plan)
    full = template.format(plan=plan, date=date_str)
    if len(full) <= MAX_DESCRIPTION_LENGTH:
        return full
    budget = MAX_DESCRIPTION_LENGTH - len(template.format(plan="", date=date_str))
    cut = plan[:max(budget - len(ELLIPSIS), 0)]
    while cut and len(cut) < len(plan) and unicodedata.combining(plan[len(cut)]):
        cut = cut[:-1]
    return template.format(plan=cut + ELLIPSIS, date=date_str)


def prorate_seats(subscription, new_plan, changed_at):
    for key in _SUB_KEYS:
        if key not in subscription:
            raise ValueError(f"subscription missing key: {key}")
    for key in _PLAN_KEYS:
        if key not in new_plan:
            raise ValueError(f"new_plan missing key: {key}")
    _check_int(subscription["seat_price_cents"], "seat_price_cents")
    _check_int(subscription["seats"], "seats")
    _check_int(subscription["billable_seats"], "billable_seats")
    _check_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    _check_aware(changed_at, "changed_at")
    _check_aware(subscription["period_end"], "period_end")

    if subscription["status"] == TRIALING_STATUS:
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    delta = period_end - changed_at
    days_left = max(0, min(PERIOD_DAYS, delta // timedelta(days=1)))
    if days_left == 0:
        return []

    seats = subscription["billable_seats"]
    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    numerator = old_price * seats * days_left
    credit = -(-numerator // PERIOD_DAYS)
    if credit >= MIN_LINE_AMOUNT_CENTS:
        approver = (SENIOR_APPROVER if credit > APPROVAL_THRESHOLD_CENTS
                    else DEFAULT_APPROVER)
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(
                _CREDIT_TEMPLATE, subscription["plan_name"], date_str),
            "approved_by": approver,
        })

    charge = new_price * seats * days_left // PERIOD_DAYS
    if charge >= MIN_LINE_AMOUNT_CENTS:
        vat_id = subscription["vat_id"]
        reverse = isinstance(vat_id, str) and vat_id.strip() != ""
        vat = 0 if reverse else charge * VAT_RATE_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description(
                _CHARGE_TEMPLATE, new_plan["name"], date_str),
            "approved_by": None,
        })
    return lines