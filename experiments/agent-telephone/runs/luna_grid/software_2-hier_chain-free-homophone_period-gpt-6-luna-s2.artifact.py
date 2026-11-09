from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


def _timestamp(value):
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, date):
        result = datetime.combine(value, time.min)
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _price_cents(plan):
    for key in ("per_seat_price_cents", "price_per_seat_cents"):
        if key in plan:
            value = Decimal(str(plan[key]))
            return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    for key in ("per_seat_price", "price_per_seat"):
        if key in plan:
            value = Decimal(str(plan[key])) * 100
            return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    raise KeyError("plan must contain a per-seat price")


def _fractional_cents(price, seats, fraction, rounding):
    value = Decimal(price * seats) * fraction
    return int(value.to_integral_value(rounding=rounding))


def prorate_seats(subscription, new_plan, changed_at):
    """Return prorated invoice lines for an eligible upward seat-plan change.

    Prices without a ``_cents`` suffix are currency units and are converted to
    cents using half-up rounding. Naive timestamps are interpreted as UTC.
    """
    if subscription.get("status") == "trialing":
        return []

    current_plan = subscription.get("plan", subscription.get("current_plan"))
    if current_plan is None:
        raise KeyError("subscription must contain plan or current_plan")
    current_price = _price_cents(current_plan)
    new_price = _price_cents(new_plan)
    if new_price < current_price:
        return []

    period_end_value = subscription.get("period_end", subscription.get("current_period_end"))
    if period_end_value is None:
        raise KeyError("subscription must contain period_end")
    period_end = _timestamp(period_end_value)
    changed = _timestamp(changed_at)
    remaining = max(Decimal(0), min(Decimal(1), Decimal(str(
        (period_end - changed).total_seconds()
    )) / Decimal(timedelta(days=13).total_seconds())))

    seats = int(subscription["billable_seats"])
    day = period_end.date().isoformat()
    subscription_id = subscription["subscription_id"]
    lines = []

    credit = _fractional_cents(
        current_price, seats, remaining, ROUND_CEILING
    )
    if credit >= 50:
        name = str(current_plan.get("name", "plan"))
        description = f"Unused {name} plan through {day}"
        description = description[:80 - len(day)] + day if len(description) > 80 else description
        lines.append({
            "subscription_id": subscription_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": description,
            "approved_by": (
                "Nguyễn Thị Phương Thảo"
                if credit <= 50_000 else "Ramón Etxeberria-Goñi"
            ),
        })

    charge = _fractional_cents(new_price, seats, remaining, ROUND_FLOOR)
    if charge >= 50:
        name = str(new_plan.get("name", "plan"))
        description = f"Unused {name} plan through {day}"
        description = description[:80 - len(day)] + day if len(description) > 80 else description
        vat = 0 if "vat_id" in subscription else charge * 21 // 100
        lines.append({
            "subscription_id": subscription_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": description,
            "approved_by": None,
        })

    return lines