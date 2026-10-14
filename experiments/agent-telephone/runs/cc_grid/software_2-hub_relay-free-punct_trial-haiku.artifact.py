"""Seat-upgrade proration for Fernhollow Studios (standard library only).

Entry point: prorate_seats(subscription, new_plan, changed_at)

CONFIRM items and the defaults implemented:
1. Currency is EUR. No currency field is emitted.
2. Status other than 'active' or 'trialing' raises BillingError.
3. New seat price equal to old seat price returns [] (treated as no change).
4. VAT on charges without a vat_id is 21% of the rounded net amount, rounded down to the cent.
5. Description date is the local YYYY-MM-DD of period_end, with no timezone conversion.
6. Missing keys, non-int or bool or negative numbers, and timezone-naive datetimes raise BillingError.
7. If a description exceeds 80 characters, the plan name is cut and ends with an ellipsis. The date is never cut. BillingError is raised if the name cannot fit.

Not included and not run in this session: the unit test module and its run results. The tests have not been written or executed.
"""

import math
from datetime import datetime, timezone
from fractions import Fraction

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
HIGH_CREDIT_THRESHOLD_CENTS = 50000
VAT_PERCENT = 21
MAX_DESCRIPTION = 80
MICROS_PER_DAY = 86_400_000_000

APPROVER_HIGH = "Ramón Etxeberria-Goñi"
APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"

ALLOWED_STATUS = ("active", "trialing")
SUBSCRIPTION_KEYS = (
    "id", "status", "plan_name", "seat_price_cents",
    "seats", "billable_seats", "vat_id", "period_end",
)
PLAN_KEYS = ("name", "seat_price_cents")


class BillingError(ValueError):
    pass


def _require_keys(obj, keys, label):
    if not isinstance(obj, dict):
        raise BillingError(f"{label} must be a dict")
    for key in keys:
        if key not in obj:
            raise BillingError(f"{label} is missing required key {key!r}")


def _non_negative_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BillingError(f"{label} must be a non-negative int")
    return value


def _aware_datetime(value, label):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise BillingError(f"{label} must be a timezone-aware datetime")
    return value


def _date_text(dt):
    return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"


def _describe(prefix, plan, period_end):
    date = _date_text(period_end)
    tail = f" seats until {date}"
    full = f"{prefix}{plan}{tail}"
    if len(full) <= MAX_DESCRIPTION:
        return full
    room = MAX_DESCRIPTION - len(prefix) - len(tail)
    if room < 2:
        raise BillingError("plan name cannot be shortened to fit the description limit")
    return f"{prefix}{plan[:room - 1]}\u2026{tail}"


def _has_vat_id(vat_id):
    return vat_id is not None and vat_id.strip() != ""


def prorate_seats(subscription, new_plan, changed_at):
    _require_keys(subscription, SUBSCRIPTION_KEYS, "subscription")
    _require_keys(new_plan, PLAN_KEYS, "new_plan")

    status = subscription["status"]
    if status not in ALLOWED_STATUS:
        raise BillingError(f"unsupported subscription status {status!r}")

    old_price = _non_negative_int(subscription["seat_price_cents"], "subscription.seat_price_cents")
    new_price = _non_negative_int(new_plan["seat_price_cents"], "new_plan.seat_price_cents")
    seats = _non_negative_int(subscription["billable_seats"], "subscription.billable_seats")

    period_end = _aware_datetime(subscription["period_end"], "subscription.period_end")
    changed_at = _aware_datetime(changed_at, "changed_at")

    old_plan_name = subscription["plan_name"]
    new_plan_name = new_plan["name"]
    if not isinstance(old_plan_name, str) or not isinstance(new_plan_name, str):
        raise BillingError("plan names must be strings")

    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise BillingError("subscription.vat_id must be a string or None")

    if status == "trialing":
        return []
    if new_price <= old_price:
        return []
    if changed_at >= period_end:
        return []

    # Exact elapsed time, using UTC so DST-zone offsets cannot skew the difference.
    delta = period_end.astimezone(timezone.utc) - changed_at.astimezone(timezone.utc)
    micros = (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds
    elapsed_days = Fraction(micros, MICROS_PER_DAY)
    remaining_days = min(max(elapsed_days, Fraction(0)), Fraction(PERIOD_DAYS))
    fraction = remaining_days / PERIOD_DAYS

    credit_cents = math.ceil(Fraction(old_price * seats) * fraction)
    charge_cents = math.floor(Fraction(new_price * seats) * fraction)

    lines = []

    if credit_cents >= MIN_LINE_CENTS:
        approver = APPROVER_HIGH if credit_cents > HIGH_CREDIT_THRESHOLD_CENTS else APPROVER_DEFAULT
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe("Credit for unused ", old_plan_name, period_end),
            "approved_by": approver,
        })

    if charge_cents >= MIN_LINE_CENTS:
        if _has_vat_id(vat_id):
            vat_cents = 0
        else:
            vat_cents = charge_cents * VAT_PERCENT // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _describe("Prorated ", new_plan_name, period_end),
            "approved_by": None,
        })

    return lines