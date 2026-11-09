from datetime import datetime
from typing import Any


def prorate_seats(
    subscription: dict[str, Any],
    new_plan: dict[str, Any],
    changed_at: datetime,
) -> list[dict[str, Any]]:
    """Return prorated credit and charge invoice lines, with amounts in cents."""
    if subscription.get("status") == "trialing":
        return []

    old_plan = subscription["plan"]
    old_price = old_plan["price_per_seat_cents"]
    new_price = new_plan["price_per_seat_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    seconds_left = max(0, (period_end - changed_at).total_seconds())
    fraction = min(seconds_left, 30 * 24 * 60 * 60) / (30 * 24 * 60 * 60)
    seats = subscription["billable_seats"]

    def prorated(price: int, round_up: bool) -> int:
        numerator = price * seats * int(seconds_left * 1_000_000)
        denominator = 30 * 24 * 60 * 60 * 1_000_000
        if round_up:
            return (numerator + denominator - 1) // denominator
        return numerator // denominator

    date = period_end.strftime("%Y-%m-%d")

    def description(plan: dict[str, Any]) -> str:
        suffix = f" through {date}"
        name = str(plan.get("name", "Plan"))
        return f"{name[:80 - len(suffix)]}{suffix}"

    credit = prorated(old_price, True)
    charge = prorated(new_price, False)
    lines: list[dict[str, Any]] = []

    if credit >= 50:
        lines.append(
            {
                "description": description(old_plan),
                "amount_cents": -credit,
                "vat_cents": 0,
                "approved_by": (
                    "Ramón Etxeberria-Goñi"
                    if credit > 50_000
                    else "Win Tee Fung Tao"
                ),
            }
        )

    if charge >= 50:
        vat = 0 if "vat_id" in subscription else (charge * 21 + 50) // 100
        lines.append(
            {
                "description": description(new_plan),
                "amount_cents": charge,
                "vat_cents": vat,
                "approved_by": None,
            }
        )

    return lines