"""Seat-upgrade proration for Fernhollow Studios billing.

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list[dict]

Open assumptions, to be confirmed with the client (each is marked ASSUMPTION in the code):
1. Currency: the data has no currency field, so LARGE_CREDIT_THRESHOLD_CENTS is applied to amount_cents as-is.
2. Equal price is not a downgrade and is prorated. The asymmetric rounding can then yield a 1-cent credit above the charge.
3. VAT on charges is rounded down (floor).
4. Long descriptions: the plan name is truncated with an ellipsis. The period end date is never dropped.
5. Every non-trialing status (active, canceled, past_due, ...) is prorated.
6. One-sided invoices are emitted: each line stands alone after the 50-cent skip.

Not included or executed: the pytest suite was not written into this module and no tests were run in this session.
"""

from datetime import datetime, timedelta

PERIOD_DAYS = 30
VAT_RATE_PERCENT = 21
MIN_LINE_CENTS = 50
LARGE_CREDIT_THRESHOLD_CENTS = 50000  # ASSUMPTION 1: applied to amount_cents as-is, no currency field exists.
MAX_DESCRIPTION_LENGTH = 80
ELLIPSIS = "\u2026"  # ASSUMPTION 4: plan names are truncated with this character.
TRIALING_STATUS = "trialing"
CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
CREDIT_TEMPLATE = "Unused {plan} seats, period end {date}"
CHARGE_TEMPLATE = "Prorated {plan} seats, period end {date}"


def _require_aware(value, field):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")
    return value


def _require_int(value, field, minimum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if value < minimum:
        raise ValueError(f"{field} must be >= {minimum}")
    return value


def _require_str(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _describe(template, plan_name, date_str):
    skeleton_len = len(template.format(plan="", date=date_str))
    room = MAX_DESCRIPTION_LENGTH - skeleton_len
    if room < 1:
        raise ValueError("description cannot fit the date")
    if len(plan_name) <= room:
        plan = plan_name
    else:
        if room < 2:
            raise ValueError("description cannot fit a shortened plan name and the date")
        plan = plan_name[: room - 1] + ELLIPSIS
    text = template.format(plan=plan, date=date_str)
    if len(text) > MAX_DESCRIPTION_LENGTH:
        raise ValueError("description exceeds 80 characters")
    return text


def _credit_cents(price, seats, days):
    # Round up to the next cent (ceiling division on non-negative numerator).
    return -((-price * seats * days) // PERIOD_DAYS)


def _charge_cents(price, seats, days):
    # Round down to the cent (floor division).
    return (price * seats * days) // PERIOD_DAYS


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict):
        raise ValueError("subscription must be a dict")
    if not isinstance(new_plan, dict):
        raise ValueError("new_plan must be a dict")
    for key in ("id", "status", "plan_name", "seat_price_cents", "billable_seats", "vat_id", "period_end"):
        if key not in subscription:
            raise ValueError(f"subscription is missing {key!r}")

    sub_id = subscription["id"]
    status = _require_str(subscription["status"], "status")
    old_plan_name = _require_str(subscription["plan_name"], "plan_name")
    old_price = _require_int(subscription["seat_price_cents"], "seat_price_cents", 0)
    seats = _require_int(subscription["billable_seats"], "billable_seats", 1)  # `seats` is never used.
    vat_id = subscription["vat_id"]
    period_end = _require_aware(subscription["period_end"], "period_end")

    new_plan_name = _require_str(new_plan.get("name"), "new_plan name")
    new_price = _require_int(new_plan.get("seat_price_cents"), "new_plan seat_price_cents", 0)
    changed_at = _require_aware(changed_at, "changed_at")

    # Trialing subscriptions are never prorated. Downgrades apply at renewal, not now.
    if status == TRIALING_STATUS:
        return []
    if new_price < old_price:
        return []

    # Whole days from change to period end (floor). Zero or negative yields no lines.
    days = (period_end - changed_at) // timedelta(days=1)
    if days <= 0:
        return []
    if days > PERIOD_DAYS:
        raise ValueError("days left cannot exceed the 30-day billing period")

    date_str = period_end.date().isoformat()
    reverse_charge = bool(vat_id and str(vat_id).strip())
    lines = []

    credit = _credit_cents(old_price, seats, days)
    if credit >= MIN_LINE_CENTS:
        approver = LARGE_CREDIT_APPROVER if credit > LARGE_CREDIT_THRESHOLD_CENTS else CREDIT_APPROVER
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe(CREDIT_TEMPLATE, old_plan_name, date_str),
            "approved_by": approver,
        })

    charge = _charge_cents(new_price, seats, days)
    if charge >= MIN_LINE_CENTS:
        vat = 0 if reverse_charge else charge * VAT_RATE_PERCENT // 100  # ASSUMPTION 3: floor.
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe(CHARGE_TEMPLATE, new_plan_name, date_str),
            "approved_by": None,
        })

    return lines