from datetime import date, datetime
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR


def prorate_seats(subscription, new_plan, changed_at):
    def get(obj, *names, default=None):
        for name in names:
            if isinstance(obj, dict) and name in obj:
                return obj[name]
            if hasattr(obj, name):
                return getattr(obj, name)
        return default

    if get(subscription, "status") == "trialing":
        return []

    old_plan = get(subscription, "plan", "current_plan", default={})
    old_price = get(old_plan, "seat_price", "price_per_seat", "price")
    new_price = get(new_plan, "seat_price", "price_per_seat", "price")
    old_price = Decimal(str(old_price))
    new_price = Decimal(str(new_price))

    if new_price <= old_price:
        return []

    period_end = get(subscription, "period_end")
    remaining_days = Decimal(str((period_end - changed_at).total_seconds())) / Decimal(86400)
    fraction = remaining_days / Decimal(30)
    seats = int(get(subscription, "billable_seats", default=0))

    end_date = period_end.date() if isinstance(period_end, datetime) else period_end
    end_text = end_date.strftime("%Y-%m-%d")
    subscription_id = get(subscription, "subscription_id", "id")
    vat_id = get(subscription, "vat_id")
    lines = []

    def description(kind, plan):
        name = str(get(plan, "name", "plan_name", default="Plan"))
        suffix = f" ({end_text})"
        return name[: max(0, 80 - len(suffix))] + suffix

    credit_cents = int(
        (old_price * seats * fraction * 100).to_integral_value(rounding=ROUND_CEILING)
    )
    if credit_cents >= 50:
        lines.append(
            {
                "subscription_id": subscription_id,
                "kind": "credit",
                "amount_cents": credit_cents,
                "vat_cents": 0,
                "description": description("credit", old_plan),
                "approved_by": (
                    "Nguyễn Thị Phương Thảo"
                    if credit_cents <= 50000
                    else "Ramón Etxeberria-Goñi"
                ),
            }
        )

    charge_cents = int(
        (new_price * seats * fraction * 100).to_integral_value(rounding=ROUND_FLOOR)
    )
    if charge_cents >= 50:
        vat_cents = 0 if vat_id is not None else int(
            (Decimal(charge_cents) * Decimal("0.21")).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        lines.append(
            {
                "subscription_id": subscription_id,
                "kind": "charge",
                "amount_cents": charge_cents,
                "vat_cents": vat_cents,
                "description": description("charge", new_plan),
                "approved_by": None,
            }
        )

    return lines

