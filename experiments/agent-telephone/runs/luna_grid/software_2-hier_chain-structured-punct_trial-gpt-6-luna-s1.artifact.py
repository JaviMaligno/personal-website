from datetime import datetime


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription["period_end"]

    for value in (changed_at, period_end):
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError("changed_at and period_end must be timezone-aware datetimes")

    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    delta = period_end - changed_at
    unused_microseconds = max(
        0,
        (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds,
    )
    denominator = 30 * 86400 * 1_000_000
    seats = subscription["billable_seats"]
    date = period_end.strftime("%Y-%m-%d")

    def make_line(kind, plan_name, price):
        numerator = price * seats * unused_microseconds
        if kind == "credit":
            amount = (numerator + denominator - 1) // denominator
        else:
            amount = numerator // denominator

        if amount < 50:
            return None

        prefix = "Credit for " if kind == "credit" else "Charge for "
        suffix = f" through {date}"
        description = prefix + str(plan_name)
        description = description[: 80 - len(suffix)] + suffix

        vat = 0 if kind == "credit" or subscription["vat_id"] else (
            amount * 21 + 50
        ) // 100
        approved_by = None
        if kind == "credit":
            approved_by = (
                "Ramón Etxeberria-Goñi"
                if amount > 50_000
                else "Nguyễn Thị Phương Thảo"
            )

        return {
            "subscription_id": subscription["id"],
            "kind": kind,
            "amount_cents": amount,
            "vat_cents": vat,
            "description": description,
            "approved_by": approved_by,
        }

    lines = []
    credit = make_line("credit", subscription["plan_name"], old_price)
    charge = make_line("charge", new_plan["name"], new_price)
    if credit is not None:
        lines.append(credit)
    if charge is not None:
        lines.append(charge)
    return lines