from datetime import datetime, timezone


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    end_utc = period_end.astimezone(timezone.utc)
    change_utc = changed_at.astimezone(timezone.utc)
    remaining = end_utc - change_utc
    remaining_us = (
        remaining.days * 86_400_000_000
        + remaining.seconds * 1_000_000
        + remaining.microseconds
    )
    if remaining_us <= 0:
        return []

    denominator = 30 * 86_400_000_000
    seats = subscription["billable_seats"]

    def description(plan_name, kind):
        prefix = "Credit unused " if kind == "credit" else "Charge unused "
        suffix = f" through {period_end:%Y-%m-%d}"
        available = max(0, 80 - len(prefix) - len(suffix))
        return f"{prefix}{str(plan_name)[:available]}{suffix}"

    lines = []

    credit_numerator = old_price * seats * remaining_us
    credit_amount = (credit_numerator + denominator - 1) // denominator
    if credit_amount >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_amount,
            "vat_cents": 0,
            "description": description(subscription["plan_name"], "credit"),
            "approved_by": (
                "Ramón Etxeberria-Goñi"
                if credit_amount > 50_000
                else "Nguyễn Thị Phương Thảo"
            ),
        })

    charge_numerator = new_price * seats * remaining_us
    charge_amount = charge_numerator // denominator
    if charge_amount >= 50:
        vat_cents = (charge_amount * 21 + 50) // 100 if not subscription["vat_id"] else 0
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_amount,
            "vat_cents": vat_cents,
            "description": description(new_plan["name"], "charge"),
            "approved_by": None,
        })

    return lines