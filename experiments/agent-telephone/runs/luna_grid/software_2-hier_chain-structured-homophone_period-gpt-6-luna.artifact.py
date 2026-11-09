from datetime import datetime


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    changed_date = changed_at.astimezone(period_end.tzinfo).date()
    unused_days = max(0, min(13, (period_end.date() - changed_date).days))
    if unused_days == 0:
        return []

    seats = subscription["billable_seats"]
    period_date = period_end.strftime("%Y-%m-%d")
    lines = []

    credit = (old_price * seats * unused_days + 12) // 13
    if credit >= 50:
        plan = subscription["plan_name"]
        prefix = "Credit for "
        suffix = f" through {period_date}"
        description = prefix + plan[: max(0, 80 - len(prefix) - len(suffix))] + suffix
        approver = (
            "Nguyễn Thị Phương Thảo"
            if credit <= 50_000
            else "Ramón Etxeberria-Goñi"
        )
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": description,
            "approved_by": approver,
        })

    charge = new_price * seats * unused_days // 13
    if charge >= 50:
        plan = new_plan["name"]
        prefix = "Charge for "
        suffix = f" through {period_date}"
        description = prefix + plan[: max(0, 80 - len(prefix) - len(suffix))] + suffix
        vat = 0 if subscription.get("vat_id") else charge * 21 // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": description,
            "approved_by": None,
        })

    return lines