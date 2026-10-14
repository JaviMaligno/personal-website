from datetime import datetime
from typing import Any


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
    unused_days = max(0, min(13, (period_end.date() - changed_at.date()).days))
    if unused_days == 0:
        return []

    seats = subscription["billable_seats"]

    def prorated_cents(price: int) -> int:
        numerator = price * seats * unused_days
        return (numerator + 6) // 13

    def vat_cents(amount: int) -> int:
        if subscription["vat_id"]:
            return 0
        return (amount * 21 + 50) // 100

    end_date = period_end.date().isoformat()
    lines = []

    credit = prorated_cents(old_price)
    if credit >= 50:
        approver = (
            "Ramón Etxeberria-Goñi"
            if credit > 50_000
            else "Nguyễn Thị Phương Thảo"
        )
        prefix = "Credit: "
        suffix = f" to {end_date}"
        plan_name = subscription["plan_name"]
        description = prefix + plan_name[: 80 - len(prefix) - len(suffix)] + suffix
        lines.append(
            {
                "subscription_id": subscription["id"],
                "kind": "credit",
                "amount_cents": credit,
                "vat_cents": vat_cents(credit),
                "description": description,
                "approved_by": approver,
            }
        )

    charge = prorated_cents(new_price)
    if charge >= 50:
        prefix = "Charge: "
        suffix = f" to {end_date}"
        plan_name = new_plan["name"]
        description = prefix + plan_name[: 80 - len(prefix) - len(suffix)] + suffix
        lines.append(
            {
                "subscription_id": subscription["id"],
                "kind": "charge",
                "amount_cents": charge,
                "vat_cents": vat_cents(charge),
                "description": description,
                "approved_by": None,
            }
        )

    return lines