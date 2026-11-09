from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    remaining = period_end - changed_at
    remaining_us = max(
        0,
        remaining.days * 86_400_000_000
        + remaining.seconds * 1_000_000
        + remaining.microseconds,
    )
    fraction = min(remaining_us, 30 * 86_400_000_000)
    denominator = 30 * 86_400_000_000
    seats = subscription["billable_seats"]
    date = period_end.strftime("%Y-%m-%d")
    lines = []

    def add_line(kind, plan_name, price, rounding):
        numerator = price * seats * fraction
        amount = (numerator + denominator - 1) // denominator if rounding == "up" else numerator // denominator
        if amount < 50:
            return

        prefix = "Credit for " if kind == "credit" else "Charge for "
        suffix = f" through {date}"
        name = str(plan_name)[: max(0, 80 - len(prefix) - len(suffix))]
        vat = 0
        if kind == "charge" and not subscription["vat_id"]:
            vat = int(
                (Decimal(amount) * Decimal("0.21")).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )

        lines.append({
            "subscription_id": subscription["id"],
            "kind": kind,
            "amount_cents": amount,
            "vat_cents": vat,
            "description": prefix + name + suffix,
            "approved_by": (
                "Nguyễn Thị Phương Thảo"
                if amount <= 50_000
                else "Ramón Etxeberria-Goñi"
            ) if kind == "credit" else None,
        })

    add_line("credit", subscription["plan_name"], old_price, "up")
    add_line("charge", new_plan["name"], new_price, "down")
    return lines