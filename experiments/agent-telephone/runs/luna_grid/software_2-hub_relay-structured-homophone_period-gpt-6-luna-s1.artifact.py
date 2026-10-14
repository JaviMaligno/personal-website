from datetime import date, datetime


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:
        return []

    period_end = subscription["period_end"]
    remaining_days = max(0, min(13, (period_end - changed_at).days))
    if remaining_days == 0:
        return []

    seats = subscription["billable_seats"]

    def prorated(price, *, credit):
        numerator = price * seats * remaining_days
        return (numerator + 12) // 13 if credit else numerator // 13

    def description(plan_name):
        end_date = period_end.date() if isinstance(period_end, datetime) else period_end
        suffix = f" through {end_date:%Y-%m-%d}"
        return f"{plan_name[:80 - len(suffix)]}{suffix}"

    lines = []
    credit_amount = prorated(old_price, credit=True)
    if credit_amount >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_amount,
            "vat_cents": 0,
            "description": description(subscription["plan_name"]),
            "approved_by": (
                "Ramón Etxeberria-Goñi"
                if credit_amount > 50000
                else "Nguyễn Thị Phương Thảo"
            ),
        })

    charge_amount = prorated(new_price, credit=False)
    if charge_amount >= 50:
        vat_cents = (
            0 if subscription["vat_id"]
            else (charge_amount * 21 + 50) // 100
        )
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_amount,
            "vat_cents": vat_cents,
            "description": description(new_plan["name"]),
            "approved_by": None,
        })

    return lines