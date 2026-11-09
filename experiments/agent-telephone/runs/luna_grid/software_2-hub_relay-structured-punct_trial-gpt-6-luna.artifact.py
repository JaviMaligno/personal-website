from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:
        return []

    period_end = subscription["period_end"]
    remaining = max(0, (period_end - changed_at).days * 86_400_000_000 +
                    (period_end - changed_at).seconds * 1_000_000 +
                    (period_end - changed_at).microseconds)
    period_micros = 30 * 86_400_000_000
    seats = subscription["billable_seats"]
    date = period_end.strftime("%Y-%m-%d")

    def description(plan_name, action):
        suffix = f" {action} through {date}"
        return str(plan_name)[:80 - len(suffix)] + suffix

    def line(kind, amount, plan_name):
        if amount < 50:
            return None
        vat = (
            int((Decimal(amount) * Decimal("0.21")).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            ))
            if kind == "charge" and not subscription["vat_id"]
            else 0
        )
        return {
            "subscription_id": subscription["id"],
            "kind": kind,
            "amount_cents": amount,
            "vat_cents": vat,
            "description": description(
                plan_name, "unused credit" if kind == "credit" else "prorated charge"
            ),
            "approved_by": (
                "Nguyễn Thị Phương Thảo"
                if kind == "credit" and amount <= 50_000
                else "Ramón Etxeberria-Goñi"
                if kind == "credit"
                else None
            ),
        }

    credit_numerator = old_price * seats * remaining
    charge_numerator = new_price * seats * remaining
    credit_amount = (credit_numerator + period_micros - 1) // period_micros
    charge_amount = charge_numerator // period_micros

    lines = []
    credit = line("credit", credit_amount, subscription["plan_name"])
    charge = line("charge", charge_amount, new_plan["name"])
    if credit:
        lines.append(credit)
    if charge:
        lines.append(charge)
    return lines