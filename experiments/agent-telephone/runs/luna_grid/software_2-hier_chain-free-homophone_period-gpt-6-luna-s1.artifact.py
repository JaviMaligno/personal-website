"""Prorate a 13-day seat-plan change into credit and charge invoice lines.

Expected mappings: subscription has ``id``, ``status``, ``billable_seats``,
``period_end``, ``vat_id``, and ``current_plan``; each plan has ``name`` and
``seat_price``. Datetimes must be timezone-aware. Prices and seat counts are
converted through Decimal(str(value)) for predictable arithmetic.
"""

from datetime import timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_plan = subscription["current_plan"]
    old_price = Decimal(str(old_plan["seat_price"]))
    new_price = Decimal(str(new_plan["seat_price"]))
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    elapsed = (
        period_end.astimezone(timezone.utc)
        - changed_at.astimezone(timezone.utc)
    ).total_seconds()
    if elapsed <= 0:
        return []

    fraction = Decimal(str(elapsed)) / Decimal(13 * 24 * 60 * 60)
    seats = Decimal(str(subscription["billable_seats"]))
    date = period_end.strftime("%Y-%m-%d")

    def line(kind, plan, price, rounding):
        cents = (price * seats * fraction * 100).to_integral_value(
            rounding=rounding
        )
        amount = int(cents)
        if amount < 50:
            return None
        vat = (
            0
            if kind == "credit" or "vat_id" in subscription
            else (amount * 21 + 50) // 100
        )
        description = f"{kind.title()} for {plan['name']} through {date}"
        if len(description) > 80:
            prefix = f"{kind.title()} for "
            suffix = f" through {date}"
            description = prefix + plan["name"][: 80 - len(prefix) - len(suffix)] + suffix
        approved_by = None
        if kind == "credit":
            approved_by = (
                "Nguyễn Thị Phương Thảo"
                if amount <= 50_000
                else "Ramón Etxebarria-Goñi"
            )
        return {
            "subscription_id": subscription["id"],
            "kind": kind,
            "amount_cents": amount,
            "vat_cents": vat,
            "description": description,
            "approved_by": approved_by,
        }

    result = []
    credit = line("credit", old_plan, old_price, ROUND_CEILING)
    charge = line("charge", new_plan, new_price, ROUND_FLOOR)
    if credit is not None:
        result.append(credit)
    if charge is not None:
        result.append(charge)
    return result