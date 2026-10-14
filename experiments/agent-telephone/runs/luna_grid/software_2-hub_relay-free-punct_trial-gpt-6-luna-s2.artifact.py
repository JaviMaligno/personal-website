from datetime import datetime
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


def prorate_seats(subscription, new_plan, changed_at):
    """Return prorated credit and charge invoice lines, with amounts in cents."""
    if subscription.get("status") == "trialing":
        return []

    if changed_at.tzinfo is None or changed_at.utcoffset() is None:
        raise ValueError("changed_at must be timezone-aware")

    period_end = subscription.get("period_end", subscription.get("current_period_end"))
    if not isinstance(period_end, datetime) or period_end.tzinfo is None or period_end.utcoffset() is None:
        raise ValueError("period_end must be a timezone-aware datetime")

    old_plan = subscription.get("plan", subscription.get("current_plan", {}))
    seats = subscription["billable_seats"]
    old_price = old_plan.get("seat_price_cents", old_plan.get("seat_price", 0))
    new_price = new_plan.get("seat_price_cents", new_plan.get("seat_price", 0))

    if Decimal(str(new_price)) < Decimal(str(old_price)):
        return []

    remaining = max(
        Decimal(0),
        min(Decimal(30), Decimal(str((period_end - changed_at).total_seconds())) / Decimal(86400)),
    )
    factor = remaining / Decimal(30)

    def prorated(price, rounding):
        return int(
            (Decimal(str(price)) * Decimal(seats) * factor).to_integral_value(rounding=rounding)
        )

    end_date = period_end.date().isoformat()

    def description(plan):
        name = str(plan.get("name", ""))
        suffix = f" ({end_date})"
        return name[: 80 - len(suffix)] + suffix

    lines = []
    credit = prorated(old_price, ROUND_CEILING)
    if credit >= 50:
        approver = (
            "Ramón Etxeberria-Goñi"
            if credit > 50_000
            else "Nguyễn Thị Phương Thảo"
        )
        lines.append(
            {
                "type": "credit",
                "description": description(old_plan),
                "amount_cents": -credit,
                "vat_cents": 0,
                "approver": approver,
            }
        )

    charge = prorated(new_price, ROUND_FLOOR)
    if charge >= 50:
        vat = (
            0
            if subscription.get("vat_id")
            else int((Decimal(charge) * Decimal("0.21")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        )
        lines.append(
            {
                "type": "charge",
                "description": description(new_plan),
                "amount_cents": charge,
                "vat_cents": vat,
                "approver": None,
            }
        )

    return lines