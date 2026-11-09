from datetime import datetime
from typing import Any


def _description(prefix: str, plan_name: str, period_end: datetime) -> str:
    date = period_end.date().isoformat()
    suffix = f" through {date}"
    available = 80 - len(prefix) - len(suffix)
    return f"{prefix}{plan_name[:max(0, available)]}{suffix}"


def prorate_seats(
    subscription: dict[str, Any],
    new_plan: dict[str, Any],
    changed_at: datetime,
) -> list[dict[str, Any]]:
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    days_left = max(0, min(30, (period_end.date() - changed_at.date()).days))
    seats = subscription["billable_seats"]
    denominator = 30

    credit_numerator = old_price * seats * days_left
    credit_amount = (credit_numerator + denominator - 1) // denominator
    charge_amount = new_price * seats * days_left // denominator

    lines = []
    if credit_amount >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_amount,
            "vat_cents": 0,
            "description": _description("Credit for ", subscription["plan_name"], period_end),
            "approved_by": (
                "Ramón Etxeberria-Goñi"
                if credit_amount > 50_000
                else "Win Tee Fung Tao"
            ),
        })

    if charge_amount >= 50:
        vat_cents = (
            0
            if subscription["vat_id"]
            else (charge_amount * 21 + 50) // 100
        )
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_amount,
            "vat_cents": vat_cents,
            "description": _description("Charge for ", new_plan["name"], period_end),
            "approved_by": None,
        })

    return lines