"""Seat-plan proration.

Architect follow-ups: define behavior when changed_at is outside the billing
period, and confirm the VAT rounding rule. VAT currently follows the module's
half-up money-rounding rule.
"""

from datetime import datetime
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


def prorate_seats(subscription, new_plan, changed_at):
    """Return the credit and charge lines for a seat-plan change."""
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    if changed_at.tzinfo is None or period_end.tzinfo is None:
        raise ValueError("Datetimes must be timezone-aware")

    days = Decimal(str((period_end - changed_at).total_seconds())) / Decimal(86400)
    fraction = days / Decimal(13)
    seats = subscription["billable_seats"]
    date_text = period_end.strftime("%Y-%m-%d")

    def description(plan_name, action):
        suffix = f" {action} through {date_text}"
        return f"{plan_name[:80 - len(suffix)]}{suffix}"

    def amount_cents(price, rounding):
        value = Decimal(price) * seats * fraction
        return int(value.quantize(Decimal("1"), rounding=rounding))

    lines = []
    credit = amount_cents(old_price, ROUND_CEILING)
    if credit >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": description(subscription["plan_name"], "unused"),
            "approved_by": (
                "Nguyễn Thị Phương Thảo"
                if credit <= 50_000
                else "Ramón Etxebarria-Goñi"
            ),
        })

    charge = amount_cents(new_price, ROUND_FLOOR)
    if charge >= 50:
        vat = 0
        if not subscription["vat_id"]:
            vat = int(
                (Decimal(charge) * Decimal("0.21")).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": description(new_plan["name"], "unused"),
            "approved_by": None,
        })

    return lines