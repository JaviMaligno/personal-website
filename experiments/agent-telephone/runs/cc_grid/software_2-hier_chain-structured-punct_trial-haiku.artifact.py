import unicodedata
from datetime import datetime, timedelta

PERIOD_US = 2592000000000
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
APPROVAL_THRESHOLD_CENTS = 50000
APPROVER_DEFAULT = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
APPROVER_OVER_THRESHOLD = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")
DESC_MAX = 80
PLAN_NAME_MAX = 38
DATE_FORMAT = "%Y-%m-%d"

_REQUIRED_SUB_KEYS = (
    "id", "status", "plan_name", "seat_price_cents",
    "seats", "billable_seats", "vat_id", "period_end",
)
_REQUIRED_PLAN_KEYS = ("name", "seat_price_cents")

# Open questions for Ingrid (not blocking):
# R19: EUR assumed for the 500 threshold (50000 cents), strictly greater than.
# R20: VAT on charges rounds down, floor(amount * 21 / 100).
# R21: Fractional days are computed exactly from elapsed microseconds.
# R23: R10 minimum is tested on the net amount before VAT.
# Equal price is not a downgrade; both lines are produced.
# Canceled status is prorated like any other non-trialing status.


def _check_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must not be negative")


def _check_aware(name, value):
    if not isinstance(value, datetime):
        raise ValueError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _check_plan_name(name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("plan name must be a non-empty str")
    return name.strip()


def _ceil_div(a, b):
    return -((-a) // b)


def _shorten(plan):
    if len(plan) > PLAN_NAME_MAX:
        return plan[:35] + "..."
    return plan


def _describe(kind, plan, period_end):
    prefix = "Credit for unused " if kind == "credit" else "Charge for unused "
    date = period_end.strftime(DATE_FORMAT)
    text = f"{prefix}{_shorten(plan)}, period ends {date}"
    assert len(text) <= DESC_MAX
    return text


def prorate_seats(subscription, new_plan, changed_at):
    for key in _REQUIRED_SUB_KEYS:
        if key not in subscription:
            raise ValueError(f"subscription missing key: {key}")
    for key in _REQUIRED_PLAN_KEYS:
        if key not in new_plan:
            raise ValueError(f"new_plan missing key: {key}")

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    seats_billed = subscription["billable_seats"]
    _check_int("subscription seat_price_cents", old_price)
    _check_int("new_plan seat_price_cents", new_price)
    _check_int("seats", subscription["seats"])
    _check_int("billable_seats", seats_billed)

    _check_aware("changed_at", changed_at)
    period_end = subscription["period_end"]
    _check_aware("period_end", period_end)

    old_name = _check_plan_name(subscription["plan_name"])
    new_name = _check_plan_name(new_plan["name"])

    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise ValueError("vat_id must be None or str")

    if subscription["status"] == "trialing":
        return []

    if new_price < old_price:
        return []

    remaining_us = (period_end - changed_at) // timedelta(microseconds=1)
    if remaining_us <= 0:
        return []
    if remaining_us > PERIOD_US:
        raise ValueError("input is outside the 30-day billing period")

    credit_cents = _ceil_div(old_price * seats_billed * remaining_us, PERIOD_US)
    charge_cents = (new_price * seats_billed * remaining_us) // PERIOD_US

    lines = []

    if credit_cents >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe("credit", old_name, period_end),
            "approved_by": (
                APPROVER_OVER_THRESHOLD
                if credit_cents > APPROVAL_THRESHOLD_CENTS
                else APPROVER_DEFAULT
            ),
        })

    if charge_cents >= MIN_LINE_CENTS:
        has_vat_id = vat_id is not None and vat_id.strip() != ""
        vat_cents = 0 if has_vat_id else (charge_cents * VAT_PERCENT) // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _describe("charge", new_name, period_end),
            "approved_by": None,
        })

    return lines