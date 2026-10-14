# seat_proration.py
# Notes: no tools were available in this run, so this module was not executed or tested.
# Judgment calls: a non-str, non-None vat_id raises TypeError. The trialing early return
# precedes all validation. Timezone checks run before the downgrade early return.
# The 500 EUR threshold assumes EUR cents and is pending client confirmation.

import math
from datetime import datetime
from fractions import Fraction

PERIOD_DAYS = 13
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
# Assumes amounts are EUR cents (pending client confirmation of currency).
LARGE_CREDIT_CENTS = 50000
FINANCE_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
DESCRIPTION_MAX = 80
ACTIVE_STATUSES = frozenset({"active"})
TRIALING_STATUS = "trialing"

_MICROS_PER_DAY = 86400 * 10**6
_CREDIT_TEMPLATE = "Credit {plan} remaining until {end}"
_CHARGE_TEMPLATE = "Charge {plan} remaining until {end}"


def _require_aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _require_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an int")
    if value < 0:
        raise ValueError(f"{label} must not be negative")


def _has_vat_id(vat_id):
    if vat_id is None:
        return False
    if not isinstance(vat_id, str):
        raise TypeError("vat_id must be str or None")
    return bool(vat_id.strip())


def _remaining_days(changed_at, period_end):
    delta = period_end - changed_at
    micros = (delta.days * 86400 + delta.seconds) * 10**6 + delta.microseconds
    return Fraction(micros, _MICROS_PER_DAY)


def _check_remaining(remaining):
    if remaining < 0 or remaining > PERIOD_DAYS:
        raise ValueError("remaining period must be between 0 and 13 days")


def _credit_cents(old_price, billable, remaining):
    exact = Fraction(old_price * billable) * remaining / PERIOD_DAYS
    return math.ceil(exact)


def _charge_cents(new_price, billable, remaining):
    exact = Fraction(new_price * billable) * remaining / PERIOD_DAYS
    return math.floor(exact)


def _charge_vat_cents(charge, has_vat_id):
    if has_vat_id:
        return 0
    return (charge * VAT_PERCENT) // 100


def _end_date(period_end):
    d = period_end.date()
    return f"{d.year:04d}-{d.month:02d}-{d.day:02d}"


def _description(template, plan, end):
    text = template.format(plan=plan, end=end)
    if len(text) <= DESCRIPTION_MAX:
        return text
    base_len = len(template.format(plan="", end=end))
    budget = DESCRIPTION_MAX - base_len
    if budget >= 3:
        plan = plan[:budget - 3] + "..."
    else:
        plan = "..."[:max(budget, 0)]
    return template.format(plan=plan, end=end)


def _approver(credit_cents):
    if credit_cents > LARGE_CREDIT_CENTS:
        return LARGE_CREDIT_APPROVER
    return FINANCE_APPROVER


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == TRIALING_STATUS:
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    billable = subscription["billable_seats"]
    period_end = subscription["period_end"]

    _require_int(old_price, "seat_price_cents")
    _require_int(new_price, "new seat_price_cents")
    _require_int(billable, "billable_seats")
    _require_aware(changed_at, "changed_at")
    _require_aware(period_end, "period_end")
    has_vat = _has_vat_id(subscription["vat_id"])

    status = subscription["status"]
    if status not in ACTIVE_STATUSES:
        raise ValueError(f"unsupported status {status!r}")

    if new_price < old_price:
        return []

    remaining = _remaining_days(changed_at, period_end)
    _check_remaining(remaining)

    end = _end_date(period_end)
    lines = []

    credit = _credit_cents(old_price, billable, remaining)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(_CREDIT_TEMPLATE, subscription["plan_name"], end),
            "approved_by": _approver(credit),
        })

    charge = _charge_cents(new_price, billable, remaining)
    if charge >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": _charge_vat_cents(charge, has_vat),
            "description": _description(_CHARGE_TEMPLATE, new_plan["name"], end),
            "approved_by": None,
        })

    return lines