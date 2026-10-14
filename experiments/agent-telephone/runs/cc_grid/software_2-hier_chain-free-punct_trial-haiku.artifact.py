# -*- coding: utf-8 -*-
# Fernhollow Studios seat upgrade proration.
#
# Notes for the reviewer (not run or verified here):
# - House rule says VAT applies to every invoice line, credits included. Rule 7 of the spec
#   says credit vat_cents is always 0. The spec is more specific, so it is followed here.
# - The spec does not say whether whitespace-only names count as "non-empty". They are
#   accepted here, as the literal rule reads. Tighten this if required.
# - Tests were not written or executed in this run, so no test results are reported.

import datetime
import math
from fractions import Fraction

VAT_RATE_PERCENT = 21
MIN_LINE_CENTS = 50
LARGE_CREDIT_THRESHOLD_CENTS = 50000
MAX_DESCRIPTION_LENGTH = 80
PERIOD_MICROSECONDS = 30 * 86400 * 10**6

CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"

VALID_STATUSES = frozenset({
    "active",
    "trialing",
    "past_due",
    "canceled",
    "unpaid",
    "incomplete",
    "incomplete_expired",
})

CREDIT_TEMPLATE = "Credit unused {plan} seats, period ends {date}"
CHARGE_TEMPLATE = "Charge {plan} seats, period ends {date}"


def _require_key(mapping, key, label):
    if key not in mapping:
        raise ValueError(f"{label} is missing required key {key!r}")


def _check_name(value, label):
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")


def _check_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an int, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{label} must be zero or greater")


def _check_datetime(value, label):
    if not isinstance(value, datetime.datetime):
        raise ValueError(f"{label} must be a datetime.datetime")
    if value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _validate(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict):
        raise ValueError("subscription must be a dict")
    if not isinstance(new_plan, dict):
        raise ValueError("new_plan must be a dict")

    for key in ("id", "status", "plan_name", "seat_price_cents",
                "seats", "billable_seats", "vat_id", "period_end"):
        _require_key(subscription, key, "subscription")
    for key in ("name", "seat_price_cents"):
        _require_key(new_plan, key, "new_plan")

    _check_name(subscription["id"], "subscription id")
    _check_name(subscription["plan_name"], "subscription plan_name")
    _check_int(subscription["seat_price_cents"], "subscription seat_price_cents")
    _check_int(subscription["seats"], "subscription seats")
    _check_int(subscription["billable_seats"], "subscription billable_seats")

    if subscription["status"] not in VALID_STATUSES:
        raise ValueError(f"unknown subscription status {subscription['status']!r}")

    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise ValueError("subscription vat_id must be None or a string")

    _check_name(new_plan["name"], "new_plan name")
    _check_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")

    _check_datetime(subscription["period_end"], "period_end")
    _check_datetime(changed_at, "changed_at")


def _has_vat_id(vat_id):
    return isinstance(vat_id, str) and vat_id.strip() != ""


def _describe(template, plan, period_end):
    date_str = period_end.date().isoformat()
    full = template.format(plan=plan, date=date_str)
    if len(full) <= MAX_DESCRIPTION_LENGTH:
        return full
    budget = MAX_DESCRIPTION_LENGTH - len(template.format(plan="", date=date_str))
    if len(plan) <= budget:
        return full
    if budget < 4:
        raise ValueError("description budget too small to shorten plan name")
    short = plan[:budget - 3].rstrip() + "..."
    return template.format(plan=short, date=date_str)


def prorate_seats(subscription, new_plan, changed_at):
    _validate(subscription, new_plan, changed_at)

    if subscription["status"] != "active":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:
        return []

    period_end = subscription["period_end"]
    delta = period_end - changed_at
    unused_us = (delta.days * 86400 + delta.seconds) * 10**6 + delta.microseconds
    if unused_us <= 0:
        return []
    if unused_us > PERIOD_MICROSECONDS:
        raise ValueError("changed_at is more than 30 days before period_end; data is inconsistent")

    fraction = Fraction(unused_us, PERIOD_MICROSECONDS)
    billable = subscription["billable_seats"]

    credit_exact = Fraction(old_price * billable) * fraction
    charge_exact = Fraction(new_price * billable) * fraction

    credit_cents = math.ceil(credit_exact)
    charge_cents = math.floor(charge_exact)

    sub_id = subscription["id"]
    lines = []

    if credit_cents >= MIN_LINE_CENTS:
        if credit_cents > LARGE_CREDIT_THRESHOLD_CENTS:
            approver = LARGE_CREDIT_APPROVER
        else:
            approver = CREDIT_APPROVER
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe(CREDIT_TEMPLATE, subscription["plan_name"], period_end),
            "approved_by": approver,
        })

    if charge_cents >= MIN_LINE_CENTS:
        if _has_vat_id(subscription["vat_id"]):
            vat_cents = 0
        else:
            vat_cents = (charge_cents * VAT_RATE_PERCENT) // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _describe(CHARGE_TEMPLATE, new_plan["name"], period_end),
            "approved_by": None,
        })

    return lines