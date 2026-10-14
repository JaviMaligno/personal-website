from datetime import datetime
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


def prorate_seats(subscription, new_plan, changed_at):
    def get(obj, *names, default=None):
        for name in names:
            if isinstance(obj, dict) and name in obj:
                return obj[name]
            if hasattr(obj, name):
                return getattr(obj, name)
        return default

    def price_cents(plan):
        for name in ("seat_price_cents", "price_per_seat_cents", "unit_price_cents"):
            value = get(plan, name)
            if value is not None:
                return Decimal(str(value))
        for name in ("seat_price", "price_per_seat", "unit_price"):
            value = get(plan, name)
            if value is not None:
                return Decimal(str(value)) * 100
        return Decimal(0)

    if get(subscription, "trialing", default=False):
        return []

    period_end = get(subscription, "period_end")
    if changed_at.tzinfo is None or changed_at.utcoffset() is None:
        raise ValueError("changed_at must be timezone-aware")
    if period_end.tzinfo is None or period_end.utcoffset() is None:
        raise ValueError("period_end must be timezone-aware")

    remaining = max(
        Decimal(0),
        Decimal(str((period_end - changed_at).total_seconds()))
        / Decimal(30 * 24 * 60 * 60),
    )
    old_plan = get(subscription, "plan", "current_plan")
    old_price = price_cents(old_plan)
    new_price = price_cents(new_plan)
    if new_price < old_price:
        return []

    seats = Decimal(str(get(subscription, "billable_seats", default=0)))
    end_date = period_end.strftime("%Y-%m-%d")
    subscription_id = get(subscription, "subscription_id", "id")
    lines = []

    def add_line(kind, plan, cents, rounding, vat_rate, approved_by):
        amount = int(cents.to_integral_value(rounding=rounding))
        if amount < 50:
            return
        name = str(get(plan, "name", default="Plan"))
        suffix = f" through {end_date}"
        name = name[: max(0, 80 - len(kind) - len(suffix) - 1)]
        vat = int((Decimal(amount) * vat_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        lines.append({
            "subscription_id": subscription_id,
            "kind": kind,
            "amount_cents": amount,
            "vat_cents": vat,
            "description": f"{kind} {name}{suffix}",
            "approved_by": approved_by,
        })

    credit = seats * old_price * remaining
    add_line(
        "credit",
        old_plan,
        credit,
        ROUND_CEILING,
        Decimal(0),
        "Ramón Etxeberria-Goñi" if credit > 50000 else "Nguyễn Thị Phương Thảo",
    )

    if new_price > old_price:
        charge = seats * new_price * remaining
        add_line(
            "charge",
            new_plan,
            charge,
            ROUND_FLOOR,
            Decimal(0) if get(subscription, "vat_id") else Decimal("0.21"),
            None,
        )

    return lines