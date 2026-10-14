from datetime import date, datetime
from typing import Any


def prorate_seats(subscription: dict, new_plan: dict, changed_at: datetime) -> list[dict]:
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    end_date = period_end.date() if isinstance(period_end, datetime) else period_end
    change_date = changed_at.date() if isinstance(changed_at, datetime) else changed_at
    unused_days = max(0, min(30, (end_date - change_date).days))

    seats = subscription["billable_seats"]
    denominator = 30
    credit_cents = (old_price * seats * unused_days + denominator - 1) // denominator
    charge_cents = (new_price * seats * unused_days) // denominator
    date_text = end_date.isoformat()

    def description(plan_name: str) -> str:
        prefix = f"Proration for "
        suffix = f" through {date_text}"
        available = 80 - len(prefix) - len(suffix)
        return f"{prefix}{plan_name[:available]}{suffix}" if len(prefix) + len(plan_name) + len(suffix) > 80 else f"{prefix}{plan_name}{suffix}"

    lines = []
    if credit_cents >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": description(subscription["plan_name"]),
            "approved_by": "Nguyễn Thị Phương Thảo" if credit_cents <= 50000 else "Ramón Etxeberria-Goñi",
        })

    if charge_cents >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": 0 if subscription["vat_id"] else charge_cents * 21 // 100,
            "description": description(new_plan["name"]),
            "approved_by": None,
        })

    return lines