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
    changed_utc = changed_at.astimezone(timezone.utc)
    if changed_utc >= end_utc:
        return []

    remaining = end_utc - changed_utc
    elapsed_us = (
        (remaining.days * 86400 + remaining.seconds) * 1_000_000
        + remaining.microseconds
    )
    period_us = 30 * 86400 * 1_000_000
    base = subscription["billable_seats"] * elapsed_us

    def description(kind, plan_name):
        prefix = "Prorated credit: " if kind == "credit" else "Prorated charge: "
        suffix = f" through {period_end:%Y-%m-%d}"
        available = max(0, 80 - len(prefix) - len(suffix))
        return f"{prefix}{str(plan_name)[:available]}{suffix}"

    lines = []
    for kind, price, plan_name in (
        ("credit", old_price, subscription["plan_name"]),
        ("charge", new_price, new_plan["name"]),
    ):
        numerator = price * base
        if kind == "credit":
            amount = (numerator + period_us - 1) // period_us
        else:
            amount = numerator // period_us

        if amount < 50:
            continue

        if kind == "credit":
            approved_by = (
                "Nguyễn Thị Phương Thảo"
                if amount <= 50_000
                else "Ramón Etxeberria-Goñi"
            )
            vat = 0
        else:
            approved_by = None
            vat = 0 if subscription["vat_id"] else amount * 21 // 100

        lines.append(
            {
                "subscription_id": subscription["id"],
                "kind": kind,
                "amount_cents": amount,
                "vat_cents": vat,
                "description": description(kind, plan_name),
                "approved_by": approved_by,
            }
        )

    return lines