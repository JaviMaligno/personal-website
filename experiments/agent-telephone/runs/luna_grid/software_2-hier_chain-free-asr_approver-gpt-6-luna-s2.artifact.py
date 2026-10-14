from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


def prorate_seats(subscription, new_plan, changed_at):
    if subscription.get("status") == "trialing":
        return []

    current_plan = subscription.get("current_plan", subscription.get("plan"))
    if current_plan is None:
        raise KeyError("current_plan")

    def field(mapping, *keys):
        for key in keys:
            if key in mapping:
                return mapping[key]
        raise KeyError(keys[0])

    def decimal(value):
        return value if isinstance(value, Decimal) else Decimal(str(value))

    current_price = decimal(field(current_plan, "seat_price", "price_per_seat"))
    new_price = decimal(field(new_plan, "seat_price", "price_per_seat"))
    if new_price <= current_price:
        return []

    period_end = subscription["period_end"]
    if not isinstance(changed_at, datetime) or not isinstance(period_end, datetime):
        raise TypeError("changed_at and period_end must be datetimes")
    if changed_at.utcoffset() is None or period_end.utcoffset() is None:
        raise ValueError("changed_at and period_end must be timezone-aware")

    changed_at = changed_at.astimezone(timezone.utc)
    period_end = period_end.astimezone(timezone.utc)
    unused = Decimal(str((period_end - changed_at).total_seconds()))
    unused = max(Decimal(0), min(Decimal(1), unused / Decimal(timedelta(days=30).total_seconds())))

    seats = decimal(subscription["billable_seats"])
    period_date = period_end.date().isoformat()
    subscription_id = field(subscription, "subscription_id", "id")

    def amount_cents(price, rounding):
        return int((price * seats * unused * 100).to_integral_value(rounding=rounding))

    def description(kind, plan):
        prefix = f"Prorated {kind} for "
        suffix = f" through {period_date}"
        name = str(field(plan, "name", "plan_name"))
        name = name[: max(0, 80 - len(prefix) - len(suffix))]
        return prefix + name + suffix

    lines = []
    credit_cents = amount_cents(current_price, ROUND_CEILING)
    if credit_cents >= 50:
        lines.append({
            "subscription_id": subscription_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": description("credit", current_plan),
            "approved_by": (
                "Win Tee Fung Tao"
                if credit_cents <= 50000
                else "Ramón Etxeberria-Goñi"
            ),
        })

    charge_cents = amount_cents(new_price, ROUND_FLOOR)
    if charge_cents >= 50:
        vat_cents = 0 if subscription.get("vat_id") else int(
            (Decimal(charge_cents) * Decimal("0.21")).to_integral_value(
                rounding=ROUND_HALF_UP
            )
        )
        lines.append({
            "subscription_id": subscription_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": description("charge", new_plan),
            "approved_by": None,
        })

    return lines