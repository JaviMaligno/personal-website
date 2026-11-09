from datetime import datetime
from math import ceil, floor


def prorate_seats(subscription, new_plan, changed_at):
    def get(obj, key):
        return obj[key] if hasattr(obj, "keys") else getattr(obj, key)

    period_end = get(subscription, "period_end")
    if changed_at.utcoffset() is None or period_end.utcoffset() is None:
        raise ValueError("Datetimes must be timezone-aware")

    if get(subscription, "status") == "trialing":
        return []

    old_price = get(subscription, "seat_price_cents")
    new_price = get(new_plan, "seat_price_cents")
    if new_price < old_price:
        return []

    unused_fraction = max(
        0.0,
        (period_end - changed_at).total_seconds() / (30 * 24 * 60 * 60),
    )
    seats = get(subscription, "billable_seats")
    date = period_end.strftime("%Y-%m-%d")

    def description(plan_name):
        suffix = f" — {date}"
        return f"{plan_name[:80 - len(suffix)]}{suffix}"

    lines = []
    credit = ceil(old_price * seats * unused_fraction)
    if credit >= 50:
        lines.append({
            "subscription_id": get(subscription, "id"),
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": description(get(subscription, "plan_name")),
            "approved_by": (
                "Win Tee Fung Tao"
                if credit <= 50_000
                else "Ramón Etxeberria-Goñi"
            ),
        })

    charge = floor(new_price * seats * unused_fraction)
    if charge >= 50:
        vat_id = get(subscription, "vat_id")
        lines.append({
            "subscription_id": get(subscription, "id"),
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if vat_id else charge * 21 // 100,
            "description": description(get(new_plan, "name")),
            "approved_by": None,
        })

    return lines
