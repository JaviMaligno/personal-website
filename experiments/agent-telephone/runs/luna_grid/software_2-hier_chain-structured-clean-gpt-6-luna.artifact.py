from datetime import timedelta


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    delta = period_end - changed_at
    unused_us = (
        delta.days * 86_400_000_000
        + delta.seconds * 1_000_000
        + delta.microseconds
    )
    period_us = 30 * 86_400_000_000
    unused_us = max(0, min(period_us, unused_us))
    seats = subscription["billable_seats"]
    denominator = period_us

    def description(kind, plan_name):
        date = period_end.strftime("%Y-%m-%d")
        prefix = f"Plan change {kind}: "
        suffix = f" through {date}"
        available = 80 - len(prefix) - len(suffix)
        return prefix + str(plan_name)[:available] + suffix

    lines = []

    credit_numerator = old_price * seats * unused_us
    credit_amount = (credit_numerator + denominator - 1) // denominator
    if credit_amount >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_amount,
            "vat_cents": 0,
            "description": description("credit", subscription["plan_name"]),
            "approved_by": (
                "Nguyễn Thị Phương Thảo"
                if credit_amount <= 50_000
                else "Ramón Etxeberria-Goñi"
            ),
        })

    charge_amount = (new_price * seats * unused_us) // denominator
    if charge_amount >= 50:
        vat = 0
        if not subscription["vat_id"]:
            vat = charge_amount * 21 // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_amount,
            "vat_cents": vat,
            "description": description("charge", new_plan["name"]),
            "approved_by": None,
        })

    return lines