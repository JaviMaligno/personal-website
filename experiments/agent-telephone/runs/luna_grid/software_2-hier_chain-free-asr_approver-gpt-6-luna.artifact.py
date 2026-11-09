from datetime import date, datetime
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


def prorate_seats(subscription, new_plan, changed_at):
    """Return prorated credit and charge invoice lines for a plan change."""
    if subscription.get("status") == "trialing":
        return []

    old_plan = subscription["plan"]

    def price_cents(plan):
        if "price_per_seat_cents" in plan:
            return Decimal(str(plan["price_per_seat_cents"]))
        return Decimal(str(plan["price_per_seat"])) * 100

    old_price = price_cents(old_plan)
    new_price = price_cents(new_plan)
    if new_price < old_price:
        return []

    period_end = date.fromisoformat(str(subscription["period_end"])[:10])
    if isinstance(changed_at, datetime):
        changed_date = changed_at.date()
    elif isinstance(changed_at, date):
        changed_date = changed_at
    else:
        changed_date = date.fromisoformat(str(changed_at)[:10])

    unused_days = max(0, min(30, (period_end - changed_date).days))
    seats = int(subscription["billable_seats"])
    factor = Decimal(unused_days) * seats / Decimal(30)

    def rounded_amount(price, rounding):
        return int((price * factor).quantize(Decimal("1"), rounding=rounding))

    credit_cents = rounded_amount(old_price, ROUND_CEILING)
    charge_cents = rounded_amount(new_price, ROUND_FLOOR)
    date_text = period_end.isoformat()

    def description(kind, plan):
        suffix = f" {kind} through {date_text}"
        name = str(plan["name"])
        return name[: max(0, 80 - len(suffix))] + suffix

    lines = []
    if credit_cents >= 50:
        approver = (
            "Win Tee Fung Tao"
            if credit_cents <= 50000
            else "Ramón Etxeberria-Goñi"
        )
        lines.append({
            "subscription_id": subscription["subscription_id"],
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": description("credit", old_plan),
            "approved_by": approver,
        })

    if charge_cents >= 50:
        vat_cents = 0
        if not subscription.get("vat_id"):
            vat_cents = int(
                (Decimal(charge_cents) * Decimal("0.21")).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )
        lines.append({
            "subscription_id": subscription["subscription_id"],
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": description("charge", new_plan),
            "approved_by": None,
        })

    return lines