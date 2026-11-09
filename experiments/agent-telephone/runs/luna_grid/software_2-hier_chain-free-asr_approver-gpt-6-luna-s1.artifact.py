from datetime import date, datetime, timedelta
from fractions import Fraction


def prorate_seats(subscription: dict, new_plan: dict, changed_at: datetime) -> list[dict]:
    """Prorate an upgrade over 30 days. Equal-price changes are no-ops.

    VAT is rounded half-up to the nearest cent. Credit amounts round up;
    charge amounts round down. The current plan's price and name come from
    subscription["seat_price_cents"] and subscription["plan_name"].
    """
    if subscription.get("status") == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:
        return []

    period_end = subscription["period_end"]
    end = period_end if isinstance(period_end, datetime) else datetime.combine(
        period_end, datetime.min.time(), tzinfo=changed_at.tzinfo
    )
    remaining = end - changed_at
    remaining_us = (
        remaining.days * 86_400_000_000
        + remaining.seconds * 1_000_000
        + remaining.microseconds
    )
    fraction = Fraction(min(max(remaining_us, 0), 30 * 86_400_000_000),
                        30 * 86_400_000_000)
    seats = subscription["billable_seats"]

    def rounded_amount(price: int, *, round_up: bool) -> int:
        value = Fraction(price * seats) * fraction
        quotient, remainder = divmod(value.numerator, value.denominator)
        return quotient + int(round_up and remainder != 0)

    date_text = period_end.strftime("%Y-%m-%d")
    vat_exempt = subscription.get("vat_id") is not None
    lines = []

    credit = rounded_amount(old_price, round_up=True)
    if credit >= 50:
        plan_name = str(subscription["plan_name"])
        description = f"Credit {plan_name} through {date_text}"
        description = description[:80 - len(date_text) - len("Credit  through ")] if len(description) > 80 else description
        description = f"Credit {description} through {date_text}"
        lines.append({
            "subscription_id": subscription["subscription_id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": description[:80],
            "approved_by": "Win Tee Fung Tao" if credit <= 50_000 else "Ramón Etxeberria-Goñi",
        })

    charge = rounded_amount(new_price, round_up=False)
    if charge >= 50:
        plan_name = str(new_plan["name"])
        suffix = f" through {date_text}"
        description = f"Charge {plan_name}{suffix}"
        if len(description) > 80:
            description = f"Charge {plan_name[:80 - len('Charge ') - len(suffix)]}{suffix}"
        vat_cents = 0 if vat_exempt else (charge * 21 + 50) // 100
        lines.append({
            "subscription_id": subscription["subscription_id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat_cents,
            "description": description,
            "approved_by": None,
        })

    return lines