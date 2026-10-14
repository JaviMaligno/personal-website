from datetime import datetime, timezone
from typing import Any


def prorate_seats(subscription: Any, new_plan: Any, changed_at: datetime) -> list[dict[str, Any]]:
    """Return prorated invoice lines for a mid-period seat plan change."""
    if subscription["status"] == "trialing":
        return []

    old_price = int(subscription["seat_price_cents"])
    new_price = int(new_plan["seat_price_cents"])
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    if changed_at.tzinfo is None or period_end.tzinfo is None:
        raise ValueError("Datetime inputs must be timezone-aware")

    unused_seconds = max(0, (period_end - changed_at).total_seconds())
    unused_days = unused_seconds / 86400
    seats = int(subscription["billable_seats"])
    date_text = period_end.date().isoformat()

    def description(plan_name: str, action: str) -> str:
        suffix = f" {action} through {date_text}"
        name = str(plan_name)
        max_name_length = max(0, 80 - len(suffix))
        return f"{name[:max_name_length]}{suffix}"

    lines: list[dict[str, Any]] = []

    def add_line(kind: str, price: int, plan_name: str) -> None:
        numerator = price * seats * unused_seconds
        denominator = 30 * 86400
        amount = numerator // denominator
        if kind == "credit" and numerator % denominator:
            amount += 1
        if amount < 50:
            return

        vat = 0
        approved_by = None
        if kind == "credit":
            approved_by = (
                "Ramón Etxeberria-Goñi"
                if amount > 50_000
                else "Nguyễn Thị Phương Thảo"
            )
        elif not subscription["vat_id"]:
            vat = (amount * 21) // 100

        lines.append(
            {
                "subscription_id": subscription["id"],
                "kind": kind,
                "amount_cents": amount,
                "vat_cents": vat,
                "description": description(plan_name, "through"),
                "approved_by": approved_by,
            }
        )

    add_line("credit", old_price, subscription["plan_name"])
    add_line("charge", new_price, new_plan["name"])
    return lines