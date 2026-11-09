from datetime import datetime, timedelta

PERIOD_DAYS = 13
PERIOD_US = PERIOD_DAYS * 86400 * 10**6
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
DESC_MAX = 80
LARGE_CREDIT_CENTS = 50000
ALLOWED_STATUSES = frozenset({"active"})

APPROVER_STANDARD = "Nguyễn Thị Phương Thảo"
APPROVER_LARGE = "Ramón Etxeberria-Goñi"

_NAME_BUDGET = 48
_NAME_KEEP = 45
_ELLIPSIS = "..."
_CREDIT_PREFIX = "Credit: "
_CHARGE_PREFIX = "Charge: "


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _check_int(value, label):
    if not _is_int(value):
        raise TypeError(f"{label} must be int, not bool or float")
    if value < 0:
        raise TypeError(f"{label} must not be negative")


def _check_aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _describe(prefix, name, period_end):
    if len(name) > _NAME_BUDGET:
        name = name[:_NAME_KEEP] + _ELLIPSIS
    desc = f"{prefix}{name} (period end {period_end.date().isoformat()})"
    assert len(desc) <= DESC_MAX, "description exceeds 80 characters"
    return desc


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict):
        raise TypeError("subscription must be a dict")
    if not isinstance(new_plan, dict):
        raise TypeError("new_plan must be a dict")

    sub_id = subscription["id"]
    status = subscription["status"]
    plan_name = subscription["plan_name"]
    old_price = subscription["seat_price_cents"]
    billable = subscription["billable_seats"]
    subscription["seats"]
    vat_id = subscription["vat_id"]
    period_end = subscription["period_end"]

    new_name = new_plan["name"]
    new_price = new_plan["seat_price_cents"]

    if not isinstance(sub_id, str):
        raise TypeError("id must be str")
    if not isinstance(status, str):
        raise TypeError("status must be str")
    if not isinstance(plan_name, str):
        raise TypeError("plan_name must be str")
    if not isinstance(new_name, str):
        raise TypeError("new_plan name must be str")
    _check_int(old_price, "seat_price_cents")
    _check_int(subscription["seats"], "seats")
    _check_int(billable, "billable_seats")
    _check_int(new_price, "new_plan seat_price_cents")
    _check_aware(period_end, "period_end")
    _check_aware(changed_at, "changed_at")

    if status not in ALLOWED_STATUSES:
        return []
    if new_price <= old_price:
        return []
    if changed_at >= period_end:
        return []

    unused_us = (period_end - changed_at) // timedelta(microseconds=1)
    if unused_us > PERIOD_US:
        raise ValueError("unused time exceeds billing period")

    old_base = old_price * billable * unused_us
    credit_cents = -((-old_base) // PERIOD_US)
    new_base = new_price * billable * unused_us
    charge_cents = new_base // PERIOD_US

    lines = []

    if credit_cents >= MIN_LINE_CENTS:
        approver = APPROVER_LARGE if credit_cents > LARGE_CREDIT_CENTS else APPROVER_STANDARD
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe(_CREDIT_PREFIX, plan_name, period_end),
            "approved_by": approver,
        })

    if charge_cents >= MIN_LINE_CENTS:
        reverse_charge = bool(vat_id)
        vat_cents = 0 if reverse_charge else charge_cents * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _describe(_CHARGE_PREFIX, new_name, period_end),
            "approved_by": None,
        })

    return lines