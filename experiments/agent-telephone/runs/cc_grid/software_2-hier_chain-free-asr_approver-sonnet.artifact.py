"""Seat-upgrade proration for Fernhollow Studios billing.

Currency is assumed to be EUR, with all amounts in cents (Python ints).
Integer arithmetic only; no floats are used anywhere.

Day counting: remaining = period_end - changed_at (aware datetimes, so the
true instant difference is used regardless of timezone). It is measured
against timedelta(days=1) using integer timedelta arithmetic.
  credit_days = ceil(remaining / 1 day)   (customer gets partial-day benefit)
  charge_days = floor(remaining / 1 day)  (partial day is not charged)
Both are clamped to 0..30 (a period counts as 30 days). If period_end is at
or before changed_at, both are 0 and no lines result.

Rules: credit = ceil(old * seats * credit_days / 30);
charge = floor(new * seats * charge_days / 30). Lines under 50 cents are
omitted. Credit VAT is 0. Charge VAT is floor(amount * 21 / 100), or 0 when
the subscription has a non-blank vat_id (reverse charge). Only billable_seats
is used ("seats" is never read); legacy_discount is ignored. Output order is
credit, then charge.
"""
from datetime import datetime, timedelta

VAT_RATE_PERCENT = 21
NO_PRORATION_STATUSES = frozenset({"trialing"})
MIN_LINE_CENTS = 50
PERIOD_DAYS = 30
MAX_DESCRIPTION_LEN = 80
APPROVAL_THRESHOLD_CENTS = 50000
APPROVER_DEFAULT = "Win Tee Fung Tao"
APPROVER_SENIOR = "Ram\u00f3n Etxeberria-Go\u00f1i"

_ONE_DAY = timedelta(days=1)
_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def _check_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an int, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{label} must not be negative")


def _check_aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label}: naive datetimes are not accepted")


def _validate_inputs(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict):
        raise TypeError("subscription must be a dict")
    if not isinstance(new_plan, dict):
        raise TypeError("new_plan must be a dict")
    for key in _SUB_KEYS:
        if key not in subscription:
            raise ValueError(f"subscription is missing required key: {key}")
    for key in _PLAN_KEYS:
        if key not in new_plan:
            raise ValueError(f"new_plan is missing required key: {key}")
    _check_int(subscription["seat_price_cents"], "subscription seat_price_cents")
    _check_int(subscription["billable_seats"], "subscription billable_seats")
    _check_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    for value, label in ((subscription["plan_name"], "plan_name"),
                         (new_plan["name"], "new_plan name"),
                         (subscription["status"], "status")):
        if not isinstance(value, str):
            raise TypeError(f"{label} must be a str")
    _check_aware(changed_at, "changed_at")
    _check_aware(subscription["period_end"], "period_end")


def _remaining_days(period_end, changed_at):
    """Return (credit_days, charge_days), each clamped to 0..30."""
    remaining = period_end - changed_at
    if remaining <= timedelta(0):
        return 0, 0
    floor_days = remaining // _ONE_DAY
    ceil_days = -((-remaining) // _ONE_DAY)
    return (max(0, min(PERIOD_DAYS, ceil_days)),
            max(0, min(PERIOD_DAYS, floor_days)))


def _credit_cents(old_price, seats, days):
    return -(-(old_price * seats * days) // PERIOD_DAYS)


def _charge_cents(new_price, seats, days):
    return (new_price * seats * days) // PERIOD_DAYS


def _charge_vat_cents(amount, vat_id):
    if isinstance(vat_id, str) and vat_id.strip():
        return 0
    return (amount * VAT_RATE_PERCENT) // 100


def _credit_approver(amount):
    return APPROVER_SENIOR if amount > APPROVAL_THRESHOLD_CENTS else APPROVER_DEFAULT


def _describe(kind_text, name, date_str):
    """Build '{kind_text} {name} to {date_str}', max MAX_DESCRIPTION_LEN chars.

    Only the name is ever shortened; fixed text and date are kept intact.
    """
    fixed = len(kind_text) + len(" ") + len(" to ") + len(date_str)
    budget = MAX_DESCRIPTION_LEN - fixed
    if budget <= 0 or not name:
        return f"{kind_text} to {date_str}"
    if len(name) > budget:
        if budget >= 4:
            name = name[:budget - 3].rstrip() + "..."
        else:
            name = name[:budget]
    return f"{kind_text} {name} to {date_str}"


def _make_line(subscription_id, kind, amount, vat, description, approved_by):
    return {
        "subscription_id": subscription_id,
        "kind": kind,
        "amount_cents": amount,
        "vat_cents": vat,
        "description": description,
        "approved_by": approved_by,
    }


def prorate_seats(subscription, new_plan, changed_at):
    _validate_inputs(subscription, new_plan, changed_at)
    if subscription["status"] in NO_PRORATION_STATUSES:
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:
        return []
    seats = subscription["billable_seats"]
    if seats == 0:
        return []

    period_end = subscription["period_end"]
    credit_days, charge_days = _remaining_days(period_end, changed_at)
    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    credit = _credit_cents(old_price, seats, credit_days)
    if credit >= MIN_LINE_CENTS:
        lines.append(_make_line(
            sub_id, "credit", credit, 0,
            _describe("Credit unused", subscription["plan_name"], date_str),
            _credit_approver(credit)))

    charge = _charge_cents(new_price, seats, charge_days)
    if charge >= MIN_LINE_CENTS:
        lines.append(_make_line(
            sub_id, "charge", charge,
            _charge_vat_cents(charge, subscription["vat_id"]),
            _describe("Charge", new_plan["name"], date_str),
            None))

    return lines