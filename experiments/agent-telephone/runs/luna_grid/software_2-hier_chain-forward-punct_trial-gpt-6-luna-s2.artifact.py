from datetime import datetime
from typing import Any


def prorate_seats(
    subscription: dict[str, Any],
    new_plan: dict[str, Any],
    changed_at: datetime,
) -> list[dict[str, Any]]:
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]

    if subscription["status"] == "trialing" or new_price < old_price:
        return []

    period_end = subscription["period_end"]
    remaining_us = (
        (period_end - changed_at).days * 86_400_000_000
        + (period_end - changed_at).seconds * 1_000_000
        + (period_end - changed_at).microseconds
    )
    period_us = 30 * 86_400_000_000
    remaining_us = min(max(remaining_us, 0), period_us)
    seats = subscription["billable_seats"]
    date = period_end.strftime("%Y-%m-%d")

    def description(plan_name: str) -> str:
        prefix, suffix = "Proration: ", f" through {date}"
        name_limit = max(0, 80 - len(prefix) - len(suffix))
        return f"{prefix}{plan_name[:name_limit]}{suffix}"

    lines: list[dict[str, Any]] = []

    credit_numerator = (old_price - new_price) * seats * remaining_us
    credit_amount = (credit_numerator + period_us - 1) // period_us
    if credit_amount >= 50:
        lines.append(
            {
                "subscription_id": subscription["id"],
                "kind": "credit",
                "amount_cents": credit_amount,
                "vat_cents": 0,
                "description": description(subscription["plan_name"]),
                "approved_by": (
                    "Nguyễn Thị Phương Thảo"
                    if credit_amount <= 50_000
                    else "Ramón Etxeberria-Goñi"
                ),
            }
        )

    charge_numerator = new_price * seats * remaining_us
    charge_amount = charge_numerator // period_us
    if charge_amount >= 50:
        lines.append(
            {
                "subscription_id": subscription["id"],
                "kind": "charge",
                "amount_cents": charge_amount,
                "vat_cents": (
                    0
                    if subscription["vat_id"]
                    else charge_amount * 21 // 100
                ),
                "description": description(new_plan["name"]),
                "approved_by": None,
            }
        )

    return lines