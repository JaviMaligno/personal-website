from __future__ import annotations

from datetime import datetime, timedelta

PERIOD_US = 30 * 86400 * 10**6
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
APPROVER_OVER_500 = "Ramón Etxeberria-Goñi"
OVER_500_EUR_CENTS = 50000
NAME_LIMIT = 46
ELLIPSIS = "..."


def _check_money(value, field):
    if type(value) is not int:
        raise TypeError(f"{field} must be int, not {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{field} must be non-negative")


def _check_datetime(value, field):
    if not isinstance(value, datetime):
        raise TypeError(f"{field} must be a datetime")
    if value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


def _check_name(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")


def _description(verb, name, period_end):
    # Date is taken from period_end's own tzinfo (not converted to UTC).
    # ASSUMPTION: confirm with client
    date_text = period_end.date().isoformat()
    if len(name) > NAME_LIMIT:
        name = name[:NAME_LIMIT - len(ELLIPSIS)] + ELLIPSIS
    return f"{verb} unused {name} seats to {date_text}"


def prorate_seats(subscription, new_plan, changed_at):
    sub_id = subscription["id"]
    old_price = subscription["seat_price_cents"]
    billable = subscription["billable_seats"]
    vat_id = subscription.get("vat_id")
    period_end = subscription["period_end"]
    old_name = subscription["plan_name"]
    new_price = new_plan["seat_price_cents"]
    new_name = new_plan["name"]

    _check_money(old_price, "seat_price_cents")
    _check_money(billable, "billable_seats")
    _check_money(new_price, "new_plan seat_price_cents")
    _check_name(old_name, "plan_name")
    _check_name(new_name, "new_plan name")
    _check_datetime(changed_at, "changed_at")
    _check_datetime(period_end, "period_end")

    # ASSUMPTION: confirm with client. Unused time may not exceed one 30-day period.
    if changed_at < period_end - timedelta(days=30):
        raise ValueError("changed_at is more than 30 days before period_end")

    if subscription["status"] == "trialing":
        return []

    # ASSUMPTION: confirm with client. Equal price is treated as no change.
    # Downgrades (new < old) apply at renewal and produce no lines.
    if new_price <= old_price:
        return []

    if changed_at >= period_end:
        return []

    # Exact unused time in integer microseconds; fractional days are kept.
    # ASSUMPTION: confirm with client
    td = period_end - changed_at
    unused_us = td.days * 86400 * 10**6 + td.seconds * 10**6 + td.microseconds

    # Credit rounds up to the next cent; charge rounds down.
    credit_num = old_price * billable * unused_us
    credit_cents = -((-credit_num) // PERIOD_US)
    charge_num = new_price * billable * unused_us
    charge_cents = charge_num // PERIOD_US

    lines = []

    # ASSUMPTION: confirm with client. Skip threshold is applied to pre-VAT amount.
    if credit_cents >= MIN_LINE_CENTS:
        # ASSUMPTION: confirm with client. EUR threshold; strictly greater than 500 EUR.
        if credit_cents <= OVER_500_EUR_CENTS:
            approver = APPROVER_DEFAULT
        else:
            approver = APPROVER_OVER_500
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _description("Credit", old_name, period_end),
            "approved_by": approver,
        })

    if charge_cents >= MIN_LINE_CENTS:
        if vat_id:
            # Reverse charge.
            vat_cents = 0
        else:
            # ASSUMPTION: confirm with client. VAT is floored; VAT base is this charge only.
            vat_cents = charge_cents * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _description("Charge", new_name, period_end),
            "approved_by": None,
        })

    return lines