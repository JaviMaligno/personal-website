from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


def prorate_seats(subscription, new_plan, changed_at):
    """Return prorated invoice lines for a subscription plan change."""
    def get(obj, key):
        return obj[key] if hasattr(obj, "__getitem__") else getattr(obj, key)

    if get(subscription, "status") != "active":
        return []

    old_price = get(subscription, "seat_price_cents")
    new_price = get(new_plan, "seat_price_cents")
    if new_price < old_price:
        return []

    period_end = get(subscription, "period_end")
    seconds = (period_end - changed_at).total_seconds()
    unused_seconds = max(0, min(30 * 24 * 60 * 60, seconds))
    seats = get(subscription, "billable_seats")

    def prorated(price, rounding):
        value = Decimal(price * seats) * Decimal(str(unused_seconds)) / Decimal(30 * 24 * 60 * 60)
        return int(value.to_integral_value(rounding=rounding))

    date = period_end.strftime("%Y-%m-%d")

    def description(prefix, plan_name):
        text = f"{prefix} {plan_name} through {date}"
        if len(text) <= 80:
            return text
        suffix = f" through {date}"
        return f"{prefix} {plan_name[:80 - len(prefix) - len(suffix) - 1]}{suffix}"

    lines = []
    credit = prorated(old_price, "ROUND_CEILING")
    if credit >= 50:
        lines.append({
            "subscription_id": get(subscription, "id"),
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": description("Credit for", get(subscription, "plan_name")),
            "approved_by": (
                "Ramón Etxeberria-Goñi" if credit > 50000
                else "Nguyễn Thị Phương Thảo"
            ),
        })

    charge = prorated(new_price, "ROUND_FLOOR")
    if charge >= 50:
        vat_id = get(subscription, "vat_id")
        vat = 0 if vat_id else int(
            (Decimal(charge) * Decimal("0.21")).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        lines.append({
            "subscription_id": get(subscription, "id"),
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": description("Charge for", get(new_plan, "name")),
            "approved_by": None,
        })

    return lines