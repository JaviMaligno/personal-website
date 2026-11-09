from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR


def prorate_seats(subscription, new_plan, changed_at):
    if subscription.status == "trialing":
        return []

    old_price = subscription.seat_price_cents
    new_price = new_plan.seat_price_cents
    if new_price < old_price:
        return []

    period_end = subscription.period_end
    elapsed = period_end - changed_at
    fraction = Decimal(elapsed.days * 86400 + elapsed.seconds)
    fraction += Decimal(elapsed.microseconds) / Decimal(1_000_000)
    fraction = min(Decimal(1), max(Decimal(0), fraction / Decimal(30 * 86400)))

    seats = subscription.billable_seats
    old_amount = int(
        (fraction * old_price * seats).to_integral_value(rounding=ROUND_CEILING)
    )
    new_amount = int(
        (fraction * new_price * seats).to_integral_value(rounding=ROUND_FLOOR)
    )

    date_text = period_end.strftime("%Y-%m-%d")
    old_plan = getattr(subscription, "plan_name", None)
    if old_plan is None:
        old_plan = getattr(getattr(subscription, "plan", None), "name", "")
    new_plan_name = getattr(new_plan, "name", "")

    def description(kind, plan_name):
        label = "Credit" if kind == "credit" else "Charge"
        suffix = f" {date_text}"
        prefix = f"{label}: "
        available = 80 - len(prefix) - len(suffix)
        return f"{prefix}{str(plan_name)[:max(0, available)]}{suffix}"

    lines = []
    if old_amount >= 50:
        lines.append({
            "subscription_id": subscription.id,
            "kind": "credit",
            "amount_cents": old_amount,
            "vat_cents": 0,
            "description": description("credit", old_plan),
            "approved_by": (
                "Nguyễn Thị Phương Thảo"
                if old_amount <= 50_000
                else "Ramón Etxeberria-Goñi"
            ),
        })

    if new_amount >= 50:
        vat = 0 if getattr(subscription, "vat_id", None) else int(
            (Decimal(new_amount) * Decimal("0.21")).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )
        lines.append({
            "subscription_id": subscription.id,
            "kind": "charge",
            "amount_cents": new_amount,
            "vat_cents": vat,
            "description": description("charge", new_plan_name),
            "approved_by": None,
        })

    return lines