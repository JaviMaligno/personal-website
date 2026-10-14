from datetime import datetime
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    remaining = period_end - changed_at
    seconds = Decimal(remaining.days * 86400 + remaining.seconds)
    seconds += Decimal(remaining.microseconds) / Decimal(1_000_000)
    fraction = seconds / Decimal(30 * 86400)
    seats = subscription["billable_seats"]
    date_text = period_end.strftime("%Y-%m-%d")

    def description(plan_name):
        prefix = f"{plan_name} — through {date_text}"
        return prefix if len(prefix) <= 80 else f"{plan_name[:80 - len(date_text) - 13]} — through {date_text}"

    lines = []

    credit = int(
        (Decimal(old_price * seats) * fraction).to_integral_value(rounding=ROUND_CEILING)
    )
    if credit >= 50:
        approver = (
            "Ramón Etxeberria-Goñi" if credit > 50_000 else "Win Tee Fung Tao"
        )
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": description(subscription["plan_name"]),
            "approved_by": approver,
        })

    charge = int(
        (Decimal(new_price * seats) * fraction).to_integral_value(rounding=ROUND_FLOOR)
    )
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