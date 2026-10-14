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
    period = timedelta(days=30)
    remaining_us = (
        remaining.days * 86_400_000_000
        + remaining.seconds * 1_000_000
        + remaining.microseconds
    )
    period_us = 30 * 86_400_000_000
    remaining_us = max(0, min(period_us, remaining_us))
    seats = subscription["billable_seats"]
    date_text = period_end.strftime("%Y-%m-%d")

    def line(kind, plan_name, price):
        numerator = price * seats * remaining_us
        if kind == "credit":
            amount = (numerator + period_us - 1) // period_us
        else:
            amount = numerator // period_us
        if amount < 50:
            return None

        prefix = "Credit for " if kind == "credit" else "Charge for "
        suffix = f" through {date_text}"
        available = 80 - len(prefix) - len(suffix)
        name = str(plan_name)
        if len(name) > available:
            name = name[: max(0, available - 1)] + "…"
        vat = 0 if kind == "credit" or subscription["vat_id"] else amount * 21 // 100
        approved_by = None
        if kind == "credit":
            approved_by = (
                "Ramón Etxeberria-Goñi" if amount > 50000 else "Win Tee Fung Tao"
            )
        return {
            "subscription_id": subscription["id"],
            "kind": kind,
            "amount_cents": amount,
            "vat_cents": vat,
            "description": prefix + name + suffix,
            "approved_by": approved_by,
        }

    credit = line("credit", subscription["plan_name"], old_price)
    charge = line("charge", new_plan["name"], new_price)
    return [item for item in (credit, charge) if item is not None]