from datetime import datetime


def prorate_seats(subscription: dict, new_plan: dict, changed_at: datetime) -> list[dict]:
    if subscription["status"] == "trialing":
        return []

    period_end = subscription["period_end"]
    if changed_at >= period_end:
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    unused_seconds = (period_end - changed_at).total_seconds()
    denominator = 30 * 86400
    seats = subscription["billable_seats"]
    period_date = period_end.strftime("%Y-%m-%d")
    lines = []

    def description(label: str, plan_name: str) -> str:
        prefix = f"{label}: "
        suffix = f" — {period_date}"
        return prefix + plan_name[: max(0, 80 - len(prefix) - len(suffix))] + suffix

    credit_numerator = old_price * seats * unused_seconds
    credit_amount = (int(credit_numerator) + denominator - 1) // denominator
    if credit_amount >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_amount,
            "vat_cents": 0,
            "description": description("Credit", subscription["plan_name"]),
            "approved_by": (
                "Ramón Etxebarria-Goñi"
                if credit_amount > 50000
                else "Nguyễn Thị Phương Thảo"
            ),
        })

    charge_numerator = new_price * seats * unused_seconds
    charge_amount = int(charge_numerator) // denominator
    if charge_amount >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_amount,
            "vat_cents": 0 if subscription["vat_id"] else charge_amount * 21 // 100,
            "description": description("Charge", new_plan["name"]),
            "approved_by": None,
        })

    return lines