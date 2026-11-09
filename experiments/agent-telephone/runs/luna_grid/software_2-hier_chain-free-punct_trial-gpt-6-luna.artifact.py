from datetime import date, datetime, timedelta


def _as_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return datetime.fromisoformat(value)


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_plan = subscription["plan"]
    old_price = old_plan["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = _as_datetime(subscription["period_end"])
    changed_at = _as_datetime(changed_at)
    remaining = period_end - changed_at
    total = timedelta(days=30)
    remaining_us = (
        (remaining.days * 86400 + remaining.seconds) * 1_000_000
        + remaining.microseconds
    )
    total_us = total.days * 86400 * 1_000_000
    remaining_us = min(max(remaining_us, 0), total_us)

    seats = subscription["billable_seats"]
    end_date = period_end.date().isoformat()
    lines = []

    def description(action, plan):
        prefix = f"{action}: "
        suffix = f" through {end_date}"
        name = str(plan["name"])
        return prefix + name[: max(0, 80 - len(prefix) - len(suffix))] + suffix

    credit_numerator = old_price * seats * remaining_us
    credit_cents = (credit_numerator + total_us - 1) // total_us
    if credit_cents >= 50:
        lines.append({
            "subscription_id": subscription["subscription_id"],
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": description("Credit", old_plan),
            "approved_by": (
                "Nguyễn Thị Phương Thảo"
                if credit_cents <= 50_000
                else "Ramón Etxeberria-Goñi"
            ),
        })

    charge_cents = (new_price * seats * remaining_us) // total_us
    if charge_cents >= 50:
        vat_cents = (
            0
            if subscription.get("vat_id")
            else (charge_cents * 21 + 50) // 100
        )
        lines.append({
            "subscription_id": subscription["subscription_id"],
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": description("Charge", new_plan),
            "approved_by": None,
        })

    return lines