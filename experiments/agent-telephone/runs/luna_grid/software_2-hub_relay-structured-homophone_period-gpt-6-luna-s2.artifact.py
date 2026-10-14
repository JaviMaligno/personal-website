from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal


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
    period_us = 13 * 86400 * 1_000_000
    if remaining_us <= 0:
        return []

    billable_seats = subscription["billable_seats"]
    date_text = period_end.date().isoformat()

    def line(kind, plan_name, price, credit=False):
        numerator = price * billable_seats * remaining_us
        amount = (
            (numerator + period_us - 1) // period_us
            if credit
            else numerator // period_us
        )
        if amount < 50:
            return None

        prefix = "Unused " if credit else "Prorated "
        suffix = f" through {date_text}"
        description = prefix + str(plan_name)
        description = description[: 80 - len(suffix)] + suffix

        vat = 0
        if not credit and not subscription["vat_id"]:
            vat = int(
                (Decimal(amount) * Decimal("0.21")).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )

        if credit:
            approved_by = (
                "Ramón Etxeberria-Goñi"
                if amount > 50000
                else "Nguyễn Thị Phương Thảo"
            )
        else:
            approved_by = None

        return {
            "subscription_id": subscription["id"],
            "kind": kind,
            "amount_cents": amount,
            "vat_cents": vat,
            "description": description,
            "approved_by": approved_by,
        }

    credit = line("credit", subscription["plan_name"], old_price, credit=True)
    charge = line("charge", new_plan["name"], new_price)
    return [item for item in (credit, charge) if item is not None]