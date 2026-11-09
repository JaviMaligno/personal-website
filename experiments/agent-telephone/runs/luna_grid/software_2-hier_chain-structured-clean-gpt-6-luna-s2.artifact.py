from collections.abc import Mapping
from datetime import datetime, timezone


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    seats = subscription["billable_seats"]
    if seats == 0:
        return []

    period_end = subscription["period_end"]
    if not isinstance(changed_at, datetime) or not isinstance(period_end, datetime):
        raise TypeError("changed_at and period_end must be datetimes")
    if (
        changed_at.tzinfo is None
        or changed_at.utcoffset() is None
        or period_end.tzinfo is None
        or period_end.utcoffset() is None
    ):
        raise ValueError("changed_at and period_end must be timezone-aware")

    start_utc = changed_at.astimezone(timezone.utc)
    end_utc = period_end.astimezone(timezone.utc)
    remaining = max(0, (end_utc - start_utc).days * 86400
                    + (end_utc - start_utc).seconds)
    remaining = min(remaining, 30 * 86400)
    denominator = 30 * 86400

    def description(plan_name):
        suffix = f" through {period_end:%Y-%m-%d}"
        return f"{str(plan_name)[:80 - len(suffix)]}{suffix}"

    lines = []

    credit_numerator = seats * old_price * remaining
    credit_amount = (credit_numerator + denominator - 1) // denominator
    if credit_amount >= 50:
        approver = (
            "Ramón Etxeberria-Goñi"
            if credit_amount > 50_000
            else "Nguyễn Thị Phương Thảo"
        )
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_amount,
            "vat_cents": 0,
            "description": description(subscription["plan_name"]),
            "approved_by": approver,
        })

    charge_amount = seats * new_price * remaining // denominator
    if charge_amount >= 50:
        vat = 0 if subscription["vat_id"] is not None else charge_amount * 21 // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_amount,
            "vat_cents": vat,
            "description": description(new_plan["name"]),
            "approved_by": None,
        })

    return lines