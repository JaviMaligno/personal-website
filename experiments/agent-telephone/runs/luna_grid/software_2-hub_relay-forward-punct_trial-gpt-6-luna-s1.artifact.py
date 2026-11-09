from datetime import datetime, timezone


def prorate_seats(subscription, new_plan, changed_at):
    """Return prorated invoice lines for a seat-plan upgrade."""
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    start = changed_at.astimezone(timezone.utc)
    end = subscription["period_end"].astimezone(timezone.utc)
    delta = end - start
    remaining_us = (
        (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
    )
    if remaining_us <= 0:
        return []

    denominator = 30 * 86400 * 1_000_000
    seats = subscription["billable_seats"]
    date_text = subscription["period_end"].date().isoformat()

    def make_line(kind, plan_name, numerator, rounding):
        if rounding == "up":
            amount = (numerator + denominator - 1) // denominator
        else:
            amount = numerator // denominator
        if amount < 50:
            return None

        prefix = f"Prorated {kind} for "
        suffix = f" through {date_text}"
        name = str(plan_name)
        name = name[: max(0, 80 - len(prefix) - len(suffix))]
        description = prefix + name + suffix

        vat = 0
        approved_by = None
        if kind == "credit":
            approved_by = (
                "Ramón Etxebarria-Goñi"
                if amount > 50_000
                else "Nguyễn Thị Phương Thảo"
            )
        elif not subscription["vat_id"]:
            vat = (amount * 21 + 50) // 100

        return {
            "subscription_id": subscription["id"],
            "kind": kind,
            "amount_cents": amount,
            "vat_cents": vat,
            "description": description,
            "approved_by": approved_by,
        }

    lines = []
    credit = make_line(
        "credit",
        subscription["plan_name"],
        old_price * seats * remaining_us,
        "up",
    )
    if credit:
        lines.append(credit)

    charge = make_line(
        "charge",
        new_plan["name"],
        (new_price - old_price) * seats * remaining_us,
        "down",
    )
    if charge:
        lines.append(charge)

    return lines