from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


def _required(mapping, key):
    try:
        value = mapping[key]
    except (KeyError, TypeError):
        raise ValueError(f"Missing required field: {key}") from None
    if value is None:
        raise ValueError(f"Invalid required field: {key}")
    return value


def _price(value, field):
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError(f"{field} must be a decimal-compatible currency value")
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field} must be a decimal-compatible currency value") from None
    if not result.is_finite() or result < 0:
        raise ValueError(f"{field} must be a finite, non-negative currency value")
    return result


def _instant(value, field, tz=None):
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, date):
        result = datetime.combine(value, time.min, tzinfo=tz)
    else:
        raise ValueError(f"{field} must be a date or datetime")
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return result


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise ValueError("subscription and new_plan must be mappings")

    if subscription.get("status") == "trialing":
        return []

    old_plan = _required(subscription, "current_plan")
    if not isinstance(old_plan, dict):
        raise ValueError("current_plan must be a mapping")

    old_price = _price(_required(old_plan, "price_per_seat"), "current_plan.price_per_seat")
    new_price = _price(_required(new_plan, "price_per_seat"), "new_plan.price_per_seat")
    if new_price < old_price:
        return []

    seats = _required(subscription, "billable_seats")
    if isinstance(seats, bool) or not isinstance(seats, int) or seats < 0:
        raise ValueError("billable_seats must be a non-negative integer")

    if not isinstance(changed_at, datetime) or changed_at.tzinfo is None or changed_at.utcoffset() is None:
        raise ValueError("changed_at must be a timezone-aware datetime")
    end = _instant(_required(subscription, "period_end"), "period_end", changed_at.tzinfo)
    if end.utcoffset() != changed_at.utcoffset():
        end = end.astimezone(changed_at.tzinfo)

    duration = (end - changed_at).total_seconds()
    fraction = max(Decimal(0), min(Decimal(1), Decimal(str(duration)) / Decimal(13 * 24 * 60 * 60)))

    subscription_id = _required(subscription, "subscription_id")
    end_date = end.strftime("%Y-%m-%d")
    old_name = str(_required(old_plan, "name"))
    new_name = str(_required(new_plan, "name"))

    def description(kind, plan_name):
        prefix = "Credit: " if kind == "credit" else "Charge: "
        suffix = f" ({end_date})"
        available = 80 - len(prefix) - len(suffix)
        if available < 1:
            raise ValueError("period_end leaves no room for a plan name in the description")
        return f"{prefix}{plan_name[:available]}{suffix}"

    def line(kind, price, rounding, plan_name):
        amount = (price * seats * fraction * 100).quantize(Decimal("1"), rounding=rounding)
        cents = int(amount)
        if cents < 50:
            return None
        vat = 0
        if kind == "charge" and not subscription.get("vat_id"):
            vat = int((Decimal(cents) * Decimal("0.21")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        approver = None
        if kind == "credit":
            approver = "Nguyễn Thị Phương Thảo" if cents <= 50000 else "Ramón Etxebarria-Goñi"
        return {
            "subscription_id": subscription_id,
            "kind": kind,
            "amount_cents": cents,
            "vat_cents": vat,
            "description": description(kind, plan_name),
            "approved_by": approver,
        }

    result = []
    credit = line("credit", old_price, ROUND_CEILING, old_name)
    charge = line("charge", new_price, ROUND_FLOOR, new_name)
    if credit is not None:
        result.append(credit)
    if charge is not None:
        result.append(charge)
    return result