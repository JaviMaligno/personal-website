from datetime import datetime


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    delta = subscription["period_end"] - changed_at
    remaining_us = max(
        0,
        min(
            30 * 86400 * 1_000_000,
            (delta.days * 86400 + delta.seconds) * 1_000_000
            + delta.microseconds,
        ),
    )
    denominator = 30 * 86400 * 1_000_000
    seats = subscription["billable_seats"]
    period_date = subscription["period_end"].strftime("%Y-%m-%d")

    def description(kind, plan_name):
        prefix = f"{kind} plan: "
        suffix = f" through {period_date}"
        available = max(0, 80 - len(prefix) - len(suffix))
        return prefix + str(plan_name)[:available] + suffix

    def line(kind, price, rounding):
        numerator = price * seats * remaining_us
        amount = (
            (numerator + denominator - 1) // denominator
            if rounding == "up"
            else numerator // denominator
        )
        if amount < 50:
            return None
        credit = kind == "credit"
        return {
            "subscription_id": subscription["id"],
            "kind": kind,
            "amount_cents": amount,
            "vat_cents": 0 if credit or subscription.get("vat_id") else amount * 21 // 100,
            "description": description(
                "old" if credit else "new",
                subscription["plan_name"] if credit else new_plan["name"],
            ),
            "approved_by": (
                ("Ramón Etxeberria-Goñi" if amount > 50_000 else "Win Tee Fung Tao")
                if credit
                else None
            ),
        }

    result = []
    credit = line("credit", old_price, "up")
    charge = line("charge", new_price, "down")
    if credit is not None:
        result.append(credit)
    if charge is not None:
        result.append(charge)
    return result