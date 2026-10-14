# Module for seat proration. Not executed in this session: no tool access, so no tests were written or run.
# Assumptions per design A1-A13 (EUR cents; credit approval threshold strictly over 50000 cents;
# charge VAT = floor(cents * 21 / 100); credit ceiling and charge floor as written in R6;
# exact microsecond day count; more than 30 days remaining raises ValueError; equal price returns [];
# status other than active/trialing raises ValueError; R7 minimum applied to pre-VAT amount per line).

from datetime import timedelta

PERIOD_MICROS = 30 * 86400 * 10**6
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
APPROVAL_THRESHOLD_CENTS = 50000
PRIMARY_APPROVER = "Win Tee Fung Tao"
THRESHOLD_APPROVER = "Ramón Etxeberria-Goñi"
DESCRIPTION_MAX = 80

REQUIRED_SUB_KEYS = (
    "id", "status", "plan_name", "seat_price_cents", "seats",
    "billable_seats", "vat_id", "period_end",
)
REQUIRED_PLAN_KEYS = ("name", "seat_price_cents")


def _require_keys(mapping, keys, label):
    missing = [k for k in keys if k not in mapping]
    if missing:
        raise ValueError(f"{label} missing keys: {', '.join(missing)}")


def _check_int_cents(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be int")
    if value < 0:
        raise ValueError(f"{label} must be >= 0")
    return value


def _check_aware(value, label):
    if not hasattr(value, "tzinfo") or not hasattr(value, "utcoffset"):
        raise TypeError(f"{label} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value


def _check_name(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty str")
    return value


def _format_date(dt):
    return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"


def _describe(prefix, name, date_str):
    suffix = f" seats, period end {date_str}"
    budget = DESCRIPTION_MAX - len(prefix) - len(suffix)
    if len(name) > budget:
        name = name[:budget - 3] + "..."
    return f"{prefix}{name}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict):
        raise TypeError("subscription must be a dict")
    if not isinstance(new_plan, dict):
        raise TypeError("new_plan must be a dict")
    _require_keys(subscription, REQUIRED_SUB_KEYS, "subscription")
    _require_keys(new_plan, REQUIRED_PLAN_KEYS, "new_plan")

    sub_id = subscription["id"]
    status = subscription["status"]
    if not isinstance(status, str):
        raise TypeError("status must be str")
    old_name = _check_name(subscription["plan_name"], "plan_name")
    old_price = _check_int_cents(subscription["seat_price_cents"], "seat_price_cents")
    billable = _check_int_cents(subscription["billable_seats"], "billable_seats")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be None or str")
    period_end = _check_aware(subscription["period_end"], "period_end")

    new_name = _check_name(new_plan["name"], "new_plan name")
    new_price = _check_int_cents(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    changed_at = _check_aware(changed_at, "changed_at")

    if status == "trialing":
        return []
    if status != "active":
        raise ValueError(f"unsupported status: {status!r}")
    if new_price <= old_price:
        return []

    remaining_us = (period_end - changed_at) // timedelta(microseconds=1)
    if remaining_us <= 0:
        return []
    if remaining_us > PERIOD_MICROS:
        raise ValueError("more than 30 days remaining in billing period")

    credit_num = old_price * billable * remaining_us
    charge_num = new_price * billable * remaining_us
    credit = -((-credit_num) // PERIOD_MICROS)
    charge = charge_num // PERIOD_MICROS

    date_str = _format_date(period_end)
    lines = []

    if credit >= MIN_LINE_CENTS:
        approver = (
            PRIMARY_APPROVER
            if credit <= APPROVAL_THRESHOLD_CENTS
            else THRESHOLD_APPROVER
        )
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Unused ", old_name, date_str),
            "approved_by": approver,
        })

    if charge >= MIN_LINE_CENTS:
        if vat_id is None or vat_id.strip() == "":
            vat = charge * VAT_PERCENT // 100
        else:
            vat = 0
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe("New ", new_name, date_str),
            "approved_by": None,
        })

    return lines