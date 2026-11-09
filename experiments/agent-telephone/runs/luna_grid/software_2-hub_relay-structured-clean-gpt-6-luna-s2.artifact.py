from datetime import datetime

def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    remaining = max(0, (period_end - changed_at).total_seconds())
    period_seconds = 30 * 24 * 60 * 60
    seats = subscription["billable_seats"]

    def description(prefix, plan_name):
        date = period_end.strftime("%Y-%m-%d")
        suffix = f" {date}"
        return f"{prefix}: {plan_name[:max(0, 80 - len(prefix) - len(suffix) - 2)]}{suffix}"[:80]

    lines = []
    credit_numerator = old_price * seats * int(remaining)
    credit_cents = (credit_numerator + period_seconds - 1) // period_seconds
    if credit_cents >= 50:
        approver = (
            "Ramón Etxeberria-Goñi"
            if credit_cents > 50_000
            else "Nguyễn Thị Phương Thảo"
        )
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": description("Unused time credit", subscription["plan_name"]),
            "approved_by": approver,
        })

    charge_cents = new_price * seats * int(remaining) // period_seconds
    if charge_cents >= 50:
        vat_cents = 0 if subscription["vat_id"] else (charge_cents * 21 + 50) // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": description("Plan change", new_plan["name"]),
            "approved_by": None,
        })

    return lines