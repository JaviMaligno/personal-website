"""Prorated seat credit and charge calculation for Fernhollow Studios.

Status: NOT RUN. This environment has no file-write or shell tools, so
prorate_seats.py was not written to disk, test_prorate_seats.py was not
written, and python3 -I was not run. No test results exist.

Open points for the PM and client:
- Currency is assumed EUR; the input carries no currency field.
- Exact-time proration is implemented per the PM's decision. The client may
  have intended whole-day proration; please confirm.
- Statuses other than "trialing" (e.g. canceled, past_due) are processed normally.
- The >30-day period check runs before the trialing and downgrade shortcuts,
  so trialing or downgrade inputs with an invalid period still raise. Confirm.
- "seats" is type-validated but otherwise unused, which may conflict with the
  spec's "ignore for billing" wording.
- Description wording is the PM's proposal, not the client's text.
- Spec leaves error types open in places; choices made: non-str plan name ->
  ValueError (per spec), non-str id or vat_id -> TypeError.
"""
import math
from datetime import datetime, timedelta
from fractions import Fraction

_PERIOD_US = 30 * 86400 * 10**6
_MAX_UNUSED = timedelta(days=30)
_MAX_DESC = 80
_MIN_CENTS = 50
_THRESHOLD_CENTS = 50000
_APPROVER_LOW = "Win Tee Fung Tao"
_APPROVER_HIGH = "Ram\u00f3n Etxeberria-Go\u00f1i"
_VAT_PERCENT = 21


def _check_dt(value):
    if not isinstance(value, datetime):
        raise TypeError("expected datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")


def _check_cents(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("expected int cents")
    if value < 0:
        raise ValueError("cents must be non-negative")


def _check_name(value):
    if not isinstance(value, str) or len(value) == 0:
        raise ValueError("plan name must be a non-empty str")


def _vat_present(vat_id):
    return vat_id is not None and vat_id.strip() != ""


def _describe(prefix, name, date_str):
    head = prefix
    tail = " seats to " + date_str
    desc = head + name + tail
    if len(desc) > _MAX_DESC:
        k = _MAX_DESC - len(head) - len(tail)
        name = name[:k - 3] + "..."
        desc = head + name + tail
    return desc


def prorate_seats(subscription, new_plan, changed_at):
    sub_id = subscription["id"]
    status = subscription["status"]
    old_name = subscription["plan_name"]
    old_price = subscription["seat_price_cents"]
    billable = subscription["billable_seats"]
    seats = subscription["seats"]
    vat_id = subscription["vat_id"]
    period_end = subscription["period_end"]
    new_name = new_plan["name"]
    new_price = new_plan["seat_price_cents"]

    # 1. Validation
    _check_dt(changed_at)
    _check_dt(period_end)
    _check_cents(old_price)
    _check_cents(new_price)
    _check_cents(billable)
    _check_cents(seats)
    if not isinstance(sub_id, str):
        raise TypeError("subscription id must be str")
    _check_name(old_name)
    _check_name(new_name)
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be str or None")

    # 2. Period validity
    unused = period_end - changed_at
    if unused > _MAX_UNUSED:
        raise ValueError("unused period exceeds 30 days")

    # 3-5. Shortcuts
    if status == "trialing":
        return []
    if new_price <= old_price:
        return []
    if unused <= timedelta(0):
        return []

    # 6. Calculation
    unused_us = unused // timedelta(microseconds=1)
    f = Fraction(unused_us, _PERIOD_US)
    credit_amt = math.ceil(Fraction(old_price * billable) * f)
    charge_amt = math.floor(Fraction(new_price * billable) * f)

    date_str = period_end.date().isoformat()
    lines = []

    if credit_amt >= _MIN_CENTS:
        approver = _APPROVER_LOW if credit_amt <= _THRESHOLD_CENTS else _APPROVER_HIGH
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_amt,
            "vat_cents": 0,
            "description": _describe("Unused ", old_name, date_str),
            "approved_by": approver,
        })

    if charge_amt >= _MIN_CENTS:
        if _vat_present(vat_id):
            vat = 0
        else:
            vat = charge_amt * _VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_amt,
            "vat_cents": vat,
            "description": _describe("New ", new_name, date_str),
            "approved_by": None,
        })

    return lines