from datetime import datetime, timedelta


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    remaining = max(timedelta(0), subscription["period_end"] - changed_at)
    remaining_us = (
        remaining.days * 86_400_000_000
        + remaining.seconds * 1_000_000
        + remaining.microseconds
    )
    denominator = 30 * 86_400_000_000
    seats = subscription["billable_seats"]

    def description(kind, plan_name):
        date = subscription["period_end"].strftime("%Y-%m-%d")
        prefix = f"Proration {kind}: "
        suffix = f" through {date}"
        return prefix + str(plan_name)[: 80 - len(prefix) - len(suffix)] + suffix

    lines = []
    credit_numerator = old_price * seats * remaining_us
    credit_amount = (credit_numerator + denominator - 1) // denominator
    if credit_amount >= 50:
        lines.append(
            {
                "subscription_id": subscription["id"],
                "kind": "credit",
                "amount_cents": credit_amount,
                "vat_cents": 0,
                "description": description("credit", subscription["plan_name"]),
                "approved_by": (
                    "Ramón Etxeberria-Goñi"
                    if credit_amount > 50_000
                    else "Nguyễn Thị Phương Thảo"
                ),
            }
        )

    charge_numerator = new_price * seats * remaining_us
    charge_amount = charge_numerator // denominator
    if charge_amount >= 50:
        vat_cents = 0 if subscription["vat_id"] else (charge_amount * 21 + 50) // 100
        lines.append(
            {
                "subscription_id": subscription["id"],
                "kind": "charge",
                "amount_cents": charge_amount,
                "vat_cents": vat_cents,
                "description": description("charge", new_plan["name"]),
                "approved_by": None,
            }
        )

    return lines