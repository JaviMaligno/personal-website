from datetime import datetime

def prorate_seats(subscription: dict, new_plan: dict, changed_at: datetime) -> list[dict]:
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    remaining = period_end - changed_at
    remaining_us = (
        remaining.days * 86_400_000_000
        + remaining.seconds * 1_000_000
        + remaining.microseconds
    )
    period_us = 30 * 86_400_000_000
    remaining_us = max(0, min(period_us, remaining_us))
    seats = subscription["billable_seats"]
    date = period_end.date().isoformat()

    def amount(price: int, round_up: bool) -> int:
        numerator = price * seats * remaining_us
        return (numerator + period_us - 1) // period_us if round_up else numerator // period_us

    def description(prefix: str, plan_name: str) -> str:
        label = f"{prefix}: "
        suffix = f" {date}"
        return label + plan_name[:max(0, 80 - len(label) - len(suffix))] + suffix

    lines = []
    credit = amount(old_price, True)
    if credit >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": description("Proration credit", subscription["plan_name"]),
            "approved_by": "Nguyễn Thị Phương Thảo" if credit <= 50_000 else "Ramón Etxeberria-Goñi",
        })

    charge = amount(new_price, False)
    if charge >= 50:
        vat = 0 if subscription.get("vat_id") else (charge * 21 + 50) // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": description("Proration charge", new_plan["name"]),
            "approved_by": None,
        })

    return lines