"""prorate_seats: seat-upgrade proration lines for Fernhollow Studios.

Open issues (to confirm with the client before release):
a. CURRENCY BLOCKER: amounts carry no currency field. CREDIT_APPROVAL_THRESHOLD_CENTS assumes EUR. Confirm with Ingrid before release.
b. The threshold compares the NET credit amount_cents, strictly greater than 50000.
c. Description overflow raises ValueError as a last-resort check. The date is never dropped.
d. Equal price returns [] (no-op). Unconfirmed.
e. changed_at >= period_end returns []. More than 30 days remaining raises ValueError.
f. Only status "trialing" is excluded. canceled, past_due and other statuses are still billed. Needs client confirmation.
g. Rounding is per line.
h. vat_id is "present" when it is a str whose strip() is non-empty.
i. Credit amount_cents is positive with kind "credit".
j. Validation as specified. The subscription id type is not specified in the design; it is accepted as a non-empty str.
k. If scope must shrink, cut VAT detail before credit math. Credit math stays exact.
Days are fractional (exact), not whole days. Needs confirmation.
Description date is period_end.date() in its own timezone. Needs confirmation.
Charge VAT floors via (charge_cents * 21) // 100. Needs finance confirmation.
Client confirmation list: currency (blocker), whole vs fractional days, status set, equal-price behaviour, exact description wording, period_end timezone for the date, VAT floor on charges, strict > 50000 threshold.
"""

from __future__ import annotations

import math
from datetime import datetime
from fractions import Fraction

PERIOD_US = 30 * 86400 * 10**6
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
DESCRIPTION_MAX = 80
CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
BIG_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
# Assumes EUR (no currency field exists on amounts). Confirm with Ingrid before release.
CREDIT_APPROVAL_THRESHOLD_CENTS = 50000


def _require_keys(mapping, keys, label):
    if not isinstance(mapping, dict):
        raise TypeError(f"{label} must be a dict")
    for key in keys:
        if key not in mapping:
            raise ValueError(f"{label} missing key: {key}")


def _text(value, label):
    if not isinstance(value, str):
        raise TypeError(f"{label} must be str")
    if not value.strip():
        raise ValueError(f"{label} must be non-empty")
    return value


def _cents(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be int cents")
    if value < 0:
        raise ValueError(f"{label} must be >= 0")
    return value


def _aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value


def _validate(subscription, new_plan, changed_at):
    _require_keys(
        subscription,
        ("id", "status", "plan_name", "seat_price_cents",
         "billable_seats", "vat_id", "period_end"),
        "subscription",
    )
    _require_keys(new_plan, ("name", "seat_price_cents"), "new_plan")

    sub_id = _text(subscription["id"], "subscription id")
    status = subscription["status"]
    if not isinstance(status, str):
        raise TypeError("subscription status must be str")
    old_name = _text(subscription["plan_name"], "plan_name")
    old_price = _cents(subscription["seat_price_cents"], "seat_price_cents")
    billable = _cents(subscription["billable_seats"], "billable_seats")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be str or None")
    period_end = _aware(subscription["period_end"], "period_end")

    new_name = _text(new_plan["name"], "new_plan name")
    new_price = _cents(new_plan["seat_price_cents"], "new_plan seat_price_cents")

    _aware(changed_at, "changed_at")

    return (sub_id, status, old_name, old_price, billable,
            vat_id, period_end, new_name, new_price)


def _fraction(changed_at, period_end):
    """Return the unused fraction of the 30-day period, or None if none remains."""
    remaining = period_end - changed_at
    remaining_us = (remaining.days * 86400 + remaining.seconds) * 10**6 + remaining.microseconds
    if remaining_us <= 0:
        return None
    if remaining_us > PERIOD_US:
        raise ValueError("more than 30 days remaining; input inconsistent with a 30-day period")
    return Fraction(remaining_us, PERIOD_US)


def _vat_present(vat_id):
    return isinstance(vat_id, str) and vat_id.strip() != ""


def _description(label, plan_name, date_str):
    head = f"{label}: unused "
    tail = f" until {date_str}"
    full = head + plan_name + tail
    if len(full) <= DESCRIPTION_MAX:
        return full
    # Keep the full date; shorten the name, reserving room for "...".
    budget = DESCRIPTION_MAX - len(head) - len(tail) - 3
    if budget < 1:
        raise ValueError("description cannot fit the plan name and date within 80 characters")
    return head + plan_name[:budget] + "..." + tail


def prorate_seats(subscription, new_plan, changed_at):
    (sub_id, status, old_name, old_price, billable,
     vat_id, period_end, new_name, new_price) = _validate(subscription, new_plan, changed_at)

    if status == "trialing":
        return []
    if new_price <= old_price:
        return []

    fraction = _fraction(changed_at, period_end)
    if fraction is None:
        return []

    date_str = period_end.date().isoformat()
    lines = []

    # Credit: old price, rounded up, no VAT.
    credit_cents = math.ceil(Fraction(old_price * billable) * fraction)
    if credit_cents >= MIN_LINE_CENTS:
        approver = (BIG_CREDIT_APPROVER
                    if credit_cents > CREDIT_APPROVAL_THRESHOLD_CENTS
                    else CREDIT_APPROVER)
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _description("Credit", old_name, date_str),
            "approved_by": approver,
        })

    # Charge: new price, rounded down; VAT floored unless reverse charge applies.
    charge_cents = math.floor(Fraction(new_price * billable) * fraction)
    if charge_cents >= MIN_LINE_CENTS:
        vat_cents = 0 if _vat_present(vat_id) else (charge_cents * VAT_PERCENT) // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _description("Charge", new_name, date_str),
            "approved_by": None,
        })

    return lines