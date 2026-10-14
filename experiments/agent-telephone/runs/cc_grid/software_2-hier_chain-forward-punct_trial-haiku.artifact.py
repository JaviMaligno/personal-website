# Seat proration module (single file). Layout collapsed to one module because no tools are available: the package split and tests/test_prorate_seats.py were not created and pytest was not run. The VAT floor on charges rounds in the customer's favour, so confirm it with finance.
from datetime import datetime, timedelta, timezone
import unicodedata

__all__ = ["prorate_seats"]

PERIOD_DAYS = 30
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
LARGE_CREDIT_CENTS = 50000
MAX_DESCRIPTION = 80
ELLIPSIS = "\u2026"
APPROVER_DEFAULT = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
APPROVER_LARGE = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")


def _ceil_div(n, d):
    return -(-n // d)


def _check_int(value, name, minimum=0):
    if type(value) is not int:
        raise TypeError(f"{name} must be an int")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _check_str(value, name):
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a str")
    return value


def _check_aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _describe(label, plan_name, date_str):
    suffix = f" (to {date_str})"
    prefix = f"{label}: "
    budget = MAX_DESCRIPTION - len(prefix) - len(suffix)
    if not plan_name.strip() or budget <= 0:
        text = f"{label}{suffix}"
    elif len(plan_name) <= budget:
        text = f"{prefix}{plan_name}{suffix}"
    else:
        text = f"{prefix}{plan_name[:budget - 1]}{ELLIPSIS}{suffix}"
    if len(text) > MAX_DESCRIPTION:
        raise ValueError("description exceeds 80 characters")
    return text


def prorate_seats(subscription, new_plan, changed_at):
    sub_id = _check_str(subscription["id"], "id")
    status = _check_str(subscription["status"], "status")
    plan_name = _check_str(subscription["plan_name"], "plan_name")
    old_price = _check_int(subscription["seat_price_cents"], "seat_price_cents")
    _ = subscription["seats"]  # required by contract, ignored for billing
    billable = _check_int(subscription["billable_seats"], "billable_seats")
    vat_id = subscription["vat_id"]
    if vat_id is not None:
        _check_str(vat_id, "vat_id")
    period_end = _check_aware(subscription["period_end"], "period_end")

    new_name = _check_str(new_plan["name"], "new_plan.name")
    new_price = _check_int(new_plan["seat_price_cents"], "new_plan.seat_price_cents")
    changed_at = _check_aware(changed_at, "changed_at")

    if status == "trialing":
        return []

    period_start = period_end - timedelta(days=PERIOD_DAYS)
    if changed_at < period_start:
        raise ValueError("changed_at is before the billing period start")

    days_left = (period_end - changed_at) // timedelta(days=1)
    if days_left <= 0:
        return []

    if new_price <= old_price:
        return []

    credit_cents = _ceil_div(old_price * billable * days_left, PERIOD_DAYS)
    charge_cents = (new_price * billable * days_left) // PERIOD_DAYS

    date_str = period_end.astimezone(timezone.utc).date().isoformat()
    lines = []

    if credit_cents >= MIN_LINE_CENTS:
        approver = APPROVER_LARGE if credit_cents > LARGE_CREDIT_CENTS else APPROVER_DEFAULT
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe("Credit", plan_name, date_str),
            "approved_by": approver,
        })

    if charge_cents >= MIN_LINE_CENTS:
        has_vat_id = vat_id is not None and vat_id.strip() != ""
        vat_cents = 0 if has_vat_id else (charge_cents * VAT_PERCENT) // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _describe("Charge", new_name, date_str),
            "approved_by": None,
        })

    return lines