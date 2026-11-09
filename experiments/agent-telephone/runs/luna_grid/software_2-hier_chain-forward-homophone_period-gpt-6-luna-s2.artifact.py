from datetime import datetime


def prorate_seats(subscription, new_plan, changed_at):
    """Return prorated invoice lines for a seat plan change."""
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    end_date = period_end.date() if isinstance(period_end, datetime) else period_end
    changed_date = changed_at.date() if isinstance(changed_at, datetime) else changed_at
    remaining_days = max(0, min(13, (end_date - changed_date).days))
    seats = subscription["billable_seats"]
    denominator = 13

    def description(kind, plan_name):
        prefix = "Unused time credit for " if kind == "credit" else "Unused time charge for "
        suffix = f" through {end_date:%Y-%m-%d}"
        available = max(0, 80 - len(prefix) - len(suffix))
        return f"{prefix}{str(plan_name)[:available]}{suffix}"

    lines = []
    credit_product = old_price * seats * remaining_days
    credit_amount = (credit_product + denominator - 1) // denominator
    if credit_amount >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_amount,
            "vat_cents": 0,
            "description": description("credit", subscription["plan_name"]),
            "approved_by": (
                "Nguyễn Thị Phương Thảo"
                if credit_amount <= 50_000
                else "Ramón Etxebarria-Goñi"
            ),
        })

    charge_amount = (new_price * seats * remaining_days) // denominator
    if charge_amount >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_amount,
            "vat_cents": 0 if subscription["vat_id"] else charge_amount * 21 // 100,
            "description": description("charge", new_plan["name"]),
            "approved_by": None,
        })

    return lines