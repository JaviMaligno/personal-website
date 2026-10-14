"""proration.py - seat proration for plan changes (stdlib only).

NOTE to the caller: I had no tools in this run, so I could not write
test_proration.py or run any tests. This module is untested. The requested
test file and test results are NOT delivered (deviation from the brief).

Open question (R12): any status other than "active" returns [].
Seats are not used in calculations (R5); a "seats" key is optional.
"""
from datetime import datetime

_PERIOD_US = 30 * 86400 * 10**6
_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")
_MAX_DESC = 80
_APPROVER = "Win Tee Fung Tao"
_APPROVER_HIGH = "Ramón Etxeberria-Goñi"


def _check_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an int, got {value!r}")
    if value < 0:
        raise ValueError(f"{label} must not be negative, got {value!r}")


def _check_aware(value, label):
    if not isinstance(value, datetime):
        raise ValueError(f"{label} must be a datetime, got {value!r}")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _validate(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict):
        raise ValueError("subscription must be a dict")
    if not isinstance(new_plan, dict):
        raise ValueError("new_plan must be a dict")
    for k in _SUB_KEYS:
        if k not in subscription:
            raise ValueError(f"subscription is missing key: {k}")
    for k in _PLAN_KEYS:
        if k not in new_plan:
            raise ValueError(f"new_plan is missing key: {k}")
    _check_int(subscription["seat_price_cents"], "subscription seat_price_cents")
    _check_int(subscription["billable_seats"], "subscription billable_seats")
    if "seats" in subscription:
        _check_int(subscription["seats"], "subscription seats")
    _check_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise ValueError("vat_id must be None or a string")
    _check_aware(subscription["period_end"], "period_end")
    _check_aware(changed_at, "changed_at")


def _time_left_us(period_end, changed_at):
    delta = period_end - changed_at
    us = (delta.days * 86400 + delta.seconds) * 10**6 + delta.microseconds
    return max(0, min(_PERIOD_US, us))


def _description(verb, plan, period_end):
    suffix = f" until {period_end.strftime('%Y-%m-%d')}"
    prefix = f"{verb} unused "
    if len(prefix) + len(plan) + len(suffix) > _MAX_DESC:
        budget = _MAX_DESC - len(prefix) - len(suffix) - 3
        plan = plan[:max(budget, 0)] + "..."
    return prefix + plan + suffix


def _approver(amount_cents):
    return _APPROVER_HIGH if amount_cents > 50000 else _APPROVER


def _charge_vat(net_cents, vat_id):
    if isinstance(vat_id, str) and vat_id.strip():
        return 0
    return net_cents * 21 // 100


def prorate_seats(subscription: dict, new_plan: dict, changed_at: datetime) -> list[dict]:
    _validate(subscription, new_plan, changed_at)

    if subscription["status"] != "active":
        return []
    qty = subscription["billable_seats"]
    if qty == 0:
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    left = _time_left_us(period_end, changed_at)
    sub_id = subscription["id"]
    lines = []

    # Credit first; independent of any VAT logic (R15).
    num = old_price * qty * left
    credit = -(-num // _PERIOD_US)
    if credit >= 50:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit", subscription["plan_name"], period_end),
            "approved_by": _approver(credit),
        })

    num = new_price * qty * left
    charge = num // _PERIOD_US
    if charge >= 50:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": _charge_vat(charge, subscription["vat_id"]),
            "description": _description("Charge", new_plan["name"], period_end),
            "approved_by": None,
        })
    return lines