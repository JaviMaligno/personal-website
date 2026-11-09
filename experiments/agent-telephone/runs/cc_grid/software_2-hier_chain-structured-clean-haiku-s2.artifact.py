"""Seat upgrade proration for Fernhollow Studios billing.

All amounts are integer EUR cents. Credits round up, charges round down.
Open items (not resolved here): Q1-Q5 are unconfirmed; A2 (whether "canceled"
or "past_due" should block proration) is unresolved; no cap is applied when
changed_at is more than 30 days before period_end; the 80-character limit is
counted in code points, not bytes; an empty plan name yields a double space;
whitespace-only vat_id is treated as absent (VAT applies).
"""

from datetime import datetime, timedelta

PERIOD_MICROS = 30 * 86400 * 10**6
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
LARGE_CREDIT_CENTS = 50000
CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"

_NAME_MAX = 32
_ONE_MICRO = timedelta(microseconds=1)
_REQUIRED_SUBSCRIPTION_KEYS = (
    "id",
    "status",
    "plan_name",
    "seat_price_cents",
    "billable_seats",
    "vat_id",
    "period_end",
)
_REQUIRED_PLAN_KEYS = ("name", "seat_price_cents")


def prorate_seats(subscription, new_plan, changed_at):
    _validate_inputs(subscription, new_plan, changed_at)

    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    elapsed = _elapsed_micros(changed_at, period_end)
    if elapsed <= 0:
        return []

    seats = subscription["billable_seats"]
    credit_cents = _ceil_div(old_price * seats * elapsed, PERIOD_MICROS)
    charge_cents = (new_price * seats * elapsed) // PERIOD_MICROS

    lines = []
    if credit_cents >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe("Credit", subscription["plan_name"], period_end),
            "approved_by": _approver_for_credit(credit_cents),
        })
    if charge_cents >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": _vat_cents(charge_cents, subscription["vat_id"]),
            "description": _describe("Charge", new_plan["name"], period_end),
            "approved_by": None,
        })
    return lines


def _validate_inputs(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict):
        raise TypeError("subscription must be a dict")
    if not isinstance(new_plan, dict):
        raise TypeError("new_plan must be a dict")
    for key in _REQUIRED_SUBSCRIPTION_KEYS:
        if key not in subscription:
            raise ValueError(f"subscription missing key: {key}")
    for key in _REQUIRED_PLAN_KEYS:
        if key not in new_plan:
            raise ValueError(f"new_plan missing key: {key}")

    _require_non_negative_int(subscription["billable_seats"], "billable_seats")
    _require_non_negative_int(subscription["seat_price_cents"], "seat_price_cents")
    _require_non_negative_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    _require_aware_datetime(changed_at, "changed_at")
    _require_aware_datetime(subscription["period_end"], "period_end")


def _require_non_negative_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _require_aware_datetime(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _elapsed_micros(changed_at, period_end):
    return (period_end - changed_at) // _ONE_MICRO


def _ceil_div(numerator, denominator):
    return -((-numerator) // denominator)


def _vat_present(vat_id):
    return vat_id is not None and str(vat_id).strip() != ""


def _vat_cents(charge_cents, vat_id):
    if _vat_present(vat_id):
        return 0
    return charge_cents * VAT_PERCENT // 100


def _approver_for_credit(credit_cents):
    if credit_cents > LARGE_CREDIT_CENTS:
        return LARGE_CREDIT_APPROVER
    return CREDIT_APPROVER


def _fit_name(name):
    if len(name) <= _NAME_MAX:
        return name
    return name[:_NAME_MAX - 3] + "..."


def _date_str(value):
    return f"{value.year:04d}-{value.month:02d}-{value.day:02d}"


def _describe(kind_word, name, period_end):
    text = (
        f"{kind_word} for unused {_fit_name(name)} seats, "
        f"period ends {_date_str(period_end)}"
    )
    assert len(text) <= 80, "description exceeds 80 characters"
    return text