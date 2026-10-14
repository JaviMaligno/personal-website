"""Seat proration for Fernhollow Studios (client: Ingrid).

Single entry point: prorate_seats(subscription, new_plan, changed_at).
Standard library only. All money arithmetic is exact (int and Fraction).

Notes (choices the spec did not cover):
- seats, billable_seats and seat_price_cents must be non-negative ints (TypeError
  for non-int or bool, ValueError for negative). seats is validated but never used.
- vat_id must be None or a str (TypeError otherwise).
- D2 (changed_at more than 30 days before period_end) is checked before the
  early-return rules, so it also applies to downgrades, trialing and equal price.
- Descriptions use period_end.date() in the datetime's own offset (no conversion).
- Plan-name shortening keeps the leading characters of the name followed by "...".
- Open client flag, carried through per D6: the 50-cent skip can leave the customer
  up to 49 cents better off on a credit, which may conflict with R11.
- The pytest file is not included in this response, and the tests have not been run.
"""

import math
from datetime import datetime, timedelta
from fractions import Fraction

__all__ = ["prorate_seats"]

_VAT_PERCENT = 21
_MIN_LINE_CENTS = 50
_LARGE_CREDIT_CENTS = 50000
_APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
_APPROVER_LARGE = "Ramón Etxeberria-Goñi"
_PERIOD_US = 30 * 24 * 3600 * 10**6
_MAX_DESC = 80
_ELLIPSIS = "..."
_ONE_US = timedelta(microseconds=1)


def _check_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _check_aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _has_vat_id(vat_id):
    if vat_id is None:
        return False
    if not isinstance(vat_id, str):
        raise TypeError("vat_id must be a string or None")
    return vat_id.strip() != ""


def _describe(prefix, plan, date_text):
    suffix = f" seats, period ends {date_text}"
    text = f"{prefix}{plan}{suffix}"
    if len(text) <= _MAX_DESC:
        return text
    room = max(_MAX_DESC - len(prefix) - len(suffix) - len(_ELLIPSIS), 0)
    return f"{prefix}{plan[:room]}{_ELLIPSIS}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    _check_aware(changed_at, "changed_at")
    period_end = subscription["period_end"]
    _check_aware(period_end, "period_end")

    old_price = _check_int(subscription["seat_price_cents"], "seat_price_cents")
    billable = _check_int(subscription["billable_seats"], "billable_seats")
    _check_int(subscription["seats"], "seats")
    new_price = _check_int(new_plan["seat_price_cents"], "new seat_price_cents")
    vat_id = subscription["vat_id"]
    _has_vat_id(vat_id)

    elapsed_us = (period_end - changed_at) // _ONE_US
    if elapsed_us > _PERIOD_US:
        raise ValueError("changed_at is more than 30 days before period_end")

    if subscription["status"] == "trialing":
        return []
    if new_price <= old_price:
        return []
    if elapsed_us <= 0:
        return []

    fraction = Fraction(elapsed_us, _PERIOD_US)
    credit_net = math.ceil(Fraction(old_price * billable) * fraction)
    charge_net = math.floor(Fraction(new_price * billable) * fraction)

    sub_id = subscription["id"]
    date_text = period_end.date().isoformat()
    lines = []

    if credit_net >= _MIN_LINE_CENTS:
        approver = (
            _APPROVER_LARGE if credit_net > _LARGE_CREDIT_CENTS else _APPROVER_DEFAULT
        )
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_net,
            "vat_cents": 0,
            "description": _describe("Unused ", subscription["plan_name"], date_text),
            "approved_by": approver,
        })

    if charge_net >= _MIN_LINE_CENTS:
        vat = 0 if _has_vat_id(vat_id) else (charge_net * _VAT_PERCENT) // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_net,
            "vat_cents": vat,
            "description": _describe("Prorated ", new_plan["name"], date_text),
            "approved_by": None,
        })

    return lines