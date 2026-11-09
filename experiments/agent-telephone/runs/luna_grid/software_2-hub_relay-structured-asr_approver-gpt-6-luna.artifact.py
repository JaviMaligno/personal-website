from datetime import datetime
from typing import Any


def prorate_seats(subscription: dict[str, Any], new_plan: dict[str, Any], changed_at: datetime) -> list[dict[str, Any]]:
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    delta = period_end - changed_at
    if delta.total_seconds() <= 0:
        return []

    duration_us = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
    denominator = 30 * 86400 * 1_000_000
    seats = subscription["billable_seats"]
    lines = []

    def description(plan_name: str) -> str:
        date = period_end.strftime("%Y-%m-%d")
        prefix, suffix = "Unused time on ", f" through {date}"
        available = 80 - len(prefix) - len(suffix)
        return f"{prefix}{plan_name[:available]}{suffix}"

    credit_numerator = old_price * seats * duration_us
    credit_amount = (credit_numerator + denominator - 1) // denominator
    if credit_amount >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_amount,
            "vat_cents": 0,
            "description": description(subscription["plan_name"]),
            "approved_by": (
                "Ramón Etxeberria-Goñi"
                if credit_amount > 50_000
                else "Win Tee Fung Tao"
            ),
        })

    charge_numerator = new_price * seats * duration_us
    charge_amount = charge_numerator // denominator
    if charge_amount >= 50:
        vat_cents = 0 if subscription["vat_id"] else (charge_amount * 21 + 50) // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_amount,
            "vat_cents": vat_cents,
            "description": description(new_plan["name"]),
            "approved_by": None,
        })

    return lines