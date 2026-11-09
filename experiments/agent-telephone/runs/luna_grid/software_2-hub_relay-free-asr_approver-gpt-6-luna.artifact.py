from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP

__all__ = ["prorate_seats"]


def prorate_seats(subscription, new_plan, changed_at):
    """Return invoice lines for an immediate plan upgrade."""
    if subscription.get("status") == "trialing":
        return []

    old_plan = subscription["plan"]
    old_price = int(old_plan["price_per_seat_cents"])
    new_price = int(new_plan["price_per_seat_cents"])
    if new_price < old_price:
        return []

    if isinstance(changed_at, str):
        changed_at = datetime.fromisoformat(changed_at)
    period_end = subscription["period_end"]
    if isinstance(period_end, str):
        period_end = datetime.fromisoformat(period_end)

    if changed_at.tzinfo is None or period_end.tzinfo is None:
        raise ValueError("changed_at and period_end must be timezone-aware")

    seconds_left = max(
        0, min(30 * 24 * 60 * 60, int((period_end - changed_at).total_seconds()))
    )
    seats = int(subscription["billable_seats"])
    period_end_date = period_end.date().isoformat()
    subscription_id = subscription["subscription_id"]
    vat_exempt = bool(subscription.get("vat_id"))
    lines = []

    def add_line(kind, plan, price, rounding):
        prorated = (
            Decimal(price)
            * seats
            * Decimal(seconds_left)
            / Decimal(30 * 24 * 60 * 60)
        )
        amount = int(prorated.to_integral_value(rounding=rounding))
        if amount < 50:
            return
        name = str(plan["name"])
        suffix = f" through {period_end_date}"
        description = f"{name}{suffix}"
        if len(description) > 80:
            description = f"{name[:80 - len(suffix)]}{suffix}"
        vat = (
            0
            if kind == "credit" or vat_exempt
            else int(
                (Decimal(amount) * Decimal("0.21")).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )
        )
        approved_by = None
        if kind == "credit":
            approved_by = (
                "Win Tee Fung Tao"
                if amount <= 50_000
                else "Ramón Etxeberria-Goñi"
            )
        lines.append(
            {
                "subscription_id": subscription_id,
                "kind": kind,
                "amount_cents": amount,
                "vat_cents": vat,
                "description": description,
                "approved_by": approved_by,
            }
        )

    add_line("credit", old_plan, old_price, ROUND_CEILING)
    add_line("charge", new_plan, new_price, ROUND_FLOOR)
    return lines