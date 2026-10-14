from datetime import timedelta


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
        remaining.days * 86_400_000_000
        + remaining.seconds * 1_000_000
        + remaining.microseconds
    )
    period_us = 13 * 86_400_000_000
    remaining_us = max(0, min(period_us, remaining_us))

    denominator = period_us
    seats = subscription["billable_seats"]

    def line_amount(price, round_up):
        numerator = price * seats * remaining_us
        if round_up:
            return (numerator + denominator - 1) // denominator
        return numerator // denominator

    date_text = period_end.strftime("%Y-%m-%d")

    def description(label, plan_name):
        suffix = f" through {date_text}"
        prefix = f"{label} for "
        available = max(0, 80 - len(prefix) - len(suffix))
        return f"{prefix}{plan_name[:available]}{suffix}"

    lines = []
    credit = line_amount(old_price, True)
    if credit >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": description("Credit", subscription["plan_name"]),
            "approved_by": (
                "Nguyễn Thị Phương Thảo"
                if credit <= 50_000
                else "Ramón Etxeberria-Goñi"
            ),
        })

    charge = line_amount(new_price, False)
    if charge >= 50:
        vat = 0 if subscription["vat_id"] else (charge * 21 + 50) // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": description("Charge", new_plan["name"]),
            "approved_by": None,
        })

    return lines