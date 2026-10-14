from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from math import ceil, floor


def prorate_seats(subscription, new_plan, changed_at):
    """Return prorated invoice lines for an eligible plan upgrade."""
    if subscription.get("status") == "trialing":
        return []

    old_plan = subscription.get("current_plan", subscription.get("plan"))
    if old_plan is None:
        raise KeyError("subscription must include current_plan or plan")

    def seat_price(plan):
        for key in ("seat_price_cents", "price_per_seat_cents"):
            if key in plan:
                return Decimal(str(plan[key]))
        for key in ("seat_price", "price_per_seat"):
            if key in plan:
                return Decimal(str(plan[key])) * 100
        raise KeyError("plan must include a per-seat price")

    old_price = seat_price(old_plan)
    new_price = seat_price(new_plan)
    if new_price <= old_price:
        return []

    def as_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value)[:10])

    period_end = as_date(subscription["period_end"])
    change_date = as_date(changed_at)
    unused_days = max(0, (period_end - change_date).days)
    seats = int(subscription["billable_seats"])
    divisor = Decimal(30)

    def prorated(price, rounding):
        value = price * seats * unused_days / divisor
        return int(value.to_integral_value(rounding=rounding))

    credit = prorated(old_price, "ROUND_CEILING")
    charge = prorated(new_price, "ROUND_FLOOR")
    date_text = period_end.isoformat()

    def description(action, plan):
        name = str(plan.get("name", "Plan"))
        suffix = f" {action} through {date_text}"
        limit = 80 - len(suffix)
        return f"{name[:limit]}{suffix}"

    lines = []
    if credit >= 50:
        lines.append({
            "subscription_id": subscription["subscription_id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": description("credit", old_plan),
            "approved_by": (
                "Nguyễn Thị Phương Thảo"
                if credit <= 50_000
                else "Ramón Etxeberria-Goñi"
            ),
        })

    if charge >= 50:
        vat = 0
        if not subscription.get("vat_id"):
            vat = int(
                (Decimal(charge) * Decimal("0.21")).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )
        lines.append({
            "subscription_id": subscription["subscription_id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": description("charge", new_plan),
            "approved_by": None,
        })

    return lines