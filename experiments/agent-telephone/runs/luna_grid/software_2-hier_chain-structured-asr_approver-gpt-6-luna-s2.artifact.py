"""Seat-change proration, calculated in integer cents.

Elapsed time uses the actual duration to microsecond precision, including
fractional days. Charge VAT is rounded half-up to the nearest cent.
"""

from datetime import datetime
from fractions import Fraction


def prorate_seats(subscription, new_plan, changed_at):
    """Return proration invoice lines for a subscription plan change."""
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    elapsed = period_end - changed_at
    elapsed_us = (
        elapsed.days * 86_400_000_000
        + elapsed.seconds * 1_000_000
        + elapsed.microseconds
    )
    unused_us = min(max(elapsed_us, 0), 30 * 86_400_000_000)
    unused_days = Fraction(unused_us, 86_400_000_000)
    seats = subscription["billable_seats"]
    period_end_text = period_end.strftime("%Y-%m-%d")

    def description(plan_name):
        prefix = f"Proration for {plan_name} through "
        return prefix[: max(0, 80 - len(period_end_text))] + period_end_text

    def ceil_fraction(value):
        return -(-value.numerator // value.denominator)

    lines = []
    credit = ceil_fraction(Fraction(seats * old_price) * unused_days / 30)
    if credit >= 50:
        lines.append(
            {
                "subscription_id": subscription["id"],
                "kind": "credit",
                "amount_cents": credit,
                "vat_cents": 0,
                "description": description(subscription["plan_name"]),
                "approved_by": (
                    "Win Tee Fung Tao"
                    if credit <= 50_000
                    else "Ramón Etxeberria-Goñi"
                ),
            }
        )

    charge = (Fraction(seats * new_price) * unused_days / 30).numerator // (
        Fraction(seats * new_price) * unused_days / 30
    ).denominator
    if charge >= 50:
        vat = 0
        if not subscription["vat_id"]:
            vat = (charge * 21 + 50) // 100
        lines.append(
            {
                "subscription_id": subscription["id"],
                "kind": "charge",
                "amount_cents": charge,
                "vat_cents": vat,
                "description": description(new_plan["name"]),
                "approved_by": None,
            }
        )

    return lines