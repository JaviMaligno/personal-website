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
    remaining_us = max(
        0,
        min(
            30 * 24 * 60 * 60 * 1_000_000,
            (period_end - changed_at) // __import__("datetime").timedelta(microseconds=1),
        ),
    )
    period_us = 30 * 24 * 60 * 60 * 1_000_000
    seats = subscription["billable_seats"]

    def description(plan_name):
        date = period_end.strftime("%Y-%m-%d")
        prefix = f"{plan_name} "
        suffix = f" through {date}"
        return prefix[: max(0, 80 - len(suffix))] + suffix

    def prorated_cents(price, rounding):
        value = Decimal(price * seats * remaining_us) / Decimal(period_us)
        return int(value.to_integral_value(rounding=rounding))

    lines = []
    credit = prorated_cents(old_price, "ROUND_CEILING")
    if credit >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": description(subscription["plan_name"]),
            "approved_by": (
                "Ramón Etxeberria-Goñi" if credit > 50_000
                else "Win Tee Fung Tao"
            ),
        })

    charge = prorated_cents(new_price, "ROUND_FLOOR")
    if charge >= 50:
        vat = 0
        if not subscription["vat_id"]:
            vat = int(
                (Decimal(charge) * Decimal("0.21")).to_integral_value(
                    rounding=ROUND_HALF_UP
                )
            )
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": description(new_plan["name"]),
            "approved_by": None,
        })

    return lines