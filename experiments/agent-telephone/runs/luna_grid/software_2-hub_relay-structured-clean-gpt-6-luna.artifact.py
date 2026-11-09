from datetime import datetime


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    remaining = max(0, (period_end - changed_at).days * 86_400_000_000
                    + (period_end - changed_at).seconds * 1_000_000
                    + (period_end - changed_at).microseconds)
    period_us = 30 * 86_400_000_000
    remaining = min(remaining, period_us)
    seats = subscription["billable_seats"]
    date = period_end.strftime("%Y-%m-%d")

    def make_line(kind, plan_name, price, round_up):
        product = price * seats * remaining
        amount = (product + period_us - 1) // period_us if round_up else product // period_us
        if amount < 50:
            return None
        prefix = "Proration credit: " if kind == "credit" else "Proration charge: "
        description = prefix + str(plan_name) + " through " + date
        description = description[:80 - len(date) - len(prefix + " through ")]
        description = prefix + description[len(prefix):] + " through " + date
        vat = 0 if kind == "credit" or subscription["vat_id"] else (amount * 21 + 50) // 100
        approved_by = None
        if kind == "credit":
            approved_by = (
                "Ramón Etxeberria-Goñi" if amount > 50_000
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
    credit = make_line("credit", subscription["plan_name"], old_price, True)
    if credit is not None:
        lines.append(credit)
    charge = make_line("charge", new_plan["name"], new_price, False)
    if charge is not None:
        lines.append(charge)
    return lines