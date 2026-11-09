"""Seat upgrade proration for Fernhollow Studios billing.

Not executed in this session. No tests were run and no test file was produced.
"""

import math
from datetime import datetime, timedelta
from fractions import Fraction

PERIOD_DAYS = 13
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
LARGE_CREDIT_THRESHOLD_CENTS = 50000
CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
DESCRIPTION_MAX = 80
_MICROSECONDS_PER_DAY = 86_400_000_000


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription["period_end"]
    _require_aware(changed_at)
    _require_aware(period_end)

    if subscription["status"] != "active":
        return []
    if changed_at >= period_end:
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    billable = subscription["billable_seats"]
    days = _days_remaining(changed_at, period_end)
    credit = _credit_cents(old_price, billable, days)
    charge = _charge_cents(new_price, billable, days)

    date_str = period_end.date().isoformat()
    reverse_charge = bool(subscription["vat_id"])
    lines = []

    if credit >= MIN_LINE_CENTS:
        lines.append(_line(
            subscription["id"],
            "credit",
            credit,
            0,
            _describe(subscription["plan_name"], "credit", date_str),
            _credit_approver(credit),
        ))

    if charge >= MIN_LINE_CENTS:
        vat = 0 if reverse_charge else _charge_vat(charge)
        lines.append(_line(
            subscription["id"],
            "charge",
            charge,
            vat,
            _describe(new_plan["name"], "charge", date_str),
            None,
        ))

    return lines


def _require_aware(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetimes must be timezone-aware")


def _days_remaining(changed_at, period_end):
    microseconds = (period_end - changed_at) // timedelta(microseconds=1)
    return Fraction(microseconds, _MICROSECONDS_PER_DAY)


def _credit_cents(old_price, billable_seats, days):
    return math.ceil(Fraction(old_price * billable_seats) * days / PERIOD_DAYS)


def _charge_cents(new_price, billable_seats, days):
    return math.floor(Fraction(new_price * billable_seats) * days / PERIOD_DAYS)


def _charge_vat(amount_cents):
    return amount_cents * VAT_PERCENT // 100


def _credit_approver(credit_cents):
    if credit_cents > LARGE_CREDIT_THRESHOLD_CENTS:
        return LARGE_CREDIT_APPROVER
    return CREDIT_APPROVER


def _describe(plan_name, kind, date_str):
    tail = f" seat {kind}, period ends {date_str}"
    budget = max(DESCRIPTION_MAX - len(tail), 0)
    return plan_name[:budget] + tail


def _line(subscription_id, kind, amount_cents, vat_cents, description, approved_by):
    return {
        "subscription_id": subscription_id,
        "kind": kind,
        "amount_cents": int(amount_cents),
        "vat_cents": int(vat_cents),
        "description": description,
        "approved_by": approved_by,
    }