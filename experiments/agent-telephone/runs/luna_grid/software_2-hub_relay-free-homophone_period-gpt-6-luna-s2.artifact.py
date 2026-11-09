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
    remaining_units = max(
        0,
        (remaining.days * 86400 + remaining.seconds) * 1_000_000
        + remaining.microseconds,
    )
    denominator = 13 * 86400 * 1_000_000
    seats = subscription["billable_seats"]
    period_date = period_end.strftime("%Y-%m-%d")

    def description(plan_name):
        suffix = f" through {period_date}"
        return f"{plan_name[:80 - len(suffix)]}{suffix}"

    lines = []

    credit_numerator = old_price * seats * remaining_units
    credit_cents = (credit_numerator + denominator - 1) // denominator
    if credit_cents >= 50:
        approver = (
            "Ramón Etxebarria-Goñi"
            if credit_cents > 50_000
            else "Nguyễn Thị Phương Thảo"
        )
        lines.append(
            {
                "subscription_id": subscription["id"],
                "kind": "credit",
                "amount_cents": credit_cents,
                "vat_cents": 0,
                "description": description(subscription["plan_name"]),
                "approved_by": approver,
            }
        )

    charge_numerator = new_price * seats * remaining_units
    charge_cents = charge_numerator // denominator
    if charge_cents >= 50:
        vat_cents = (
            0
            if subscription["vat_id"]
            else (charge_cents * 21 + 50) // 100
        )
        lines.append(
            {
                "subscription_id": subscription["id"],
                "kind": "charge",
                "amount_cents": charge_cents,
                "vat_cents": vat_cents,
                "description": description(new_plan["name"]),
                "approved_by": None,
            }
        )

    return lines