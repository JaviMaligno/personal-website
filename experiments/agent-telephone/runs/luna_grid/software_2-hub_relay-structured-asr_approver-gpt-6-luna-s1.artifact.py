from datetime import datetime


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    remaining = period_end - changed_at
    remaining_us = (
        (remaining.days * 86400 + remaining.seconds) * 1_000_000
        + remaining.microseconds
    )
    period_us = 30 * 86400 * 1_000_000
    if remaining_us <= 0:
        return []

    seats = subscription["billable_seats"]
    denominator = period_us
    multiplier = seats * remaining_us

    def description(plan_name):
        date = period_end.strftime("%Y-%m-%d")
        prefix, suffix = "Unused time on ", f" through {date}"
        available = 80 - len(prefix) - len(suffix)
        return f"{prefix}{str(plan_name)[:available]}{suffix}"

    credit_numerator = old_price * multiplier
    credit_cents = (credit_numerator + denominator - 1) // denominator
    charge_cents = (new_price * multiplier) // denominator

    lines = []
    if credit_cents >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": description(subscription["plan_name"]),
            "approved_by": (
                "Ramón Etxeberria-Goñi"
                if credit_cents > 50_000
                else "Win Tee Fung Tao"
            ),
        })

    if charge_cents >= 50:
        vat_cents = (
            0
            if subscription["vat_id"]
            else (charge_cents * 21 + 50) // 100
        )
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": description(new_plan["name"]),
            "approved_by": None,
        })

    return lines