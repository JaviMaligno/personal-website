from datetime import datetime

def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    remaining = max(0, min(
        (period_end - changed_at).days * 86_400_000_000
        + (period_end - changed_at).seconds * 1_000_000
        + (period_end - changed_at).microseconds,
        13 * 86_400_000_000,
    ))
    denominator = 13 * 86_400_000_000
    seats = subscription["billable_seats"]

    def prorated(price, round_up):
        numerator = price * seats * remaining
        quotient, remainder = divmod(numerator, denominator)
        return quotient + (1 if round_up and remainder else 0)

    def description(label, plan_name):
        date = period_end.strftime("%Y-%m-%d")
        prefix = f"{label}: "
        suffix = f" through {date}"
        return prefix + plan_name[: max(0, 80 - len(prefix) - len(suffix))] + suffix

    lines = []
    credit = prorated(old_price, True)
    if credit >= 50:
        approver = (
            "Ramón Etxeberria-Goñi"
            if credit > 50_000
            else "Nguyễn Thị Phương Thảo"
        )
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": description("Credit", subscription["plan_name"]),
            "approved_by": approver,
        })

    charge = prorated(new_price, False)
    if charge >= 50:
        vat = 0 if subscription["vat_id"] else (charge * 21 + 50) // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": description("Charge", new_plan["name"]),
            "approved_by": None,
        })

    return lines