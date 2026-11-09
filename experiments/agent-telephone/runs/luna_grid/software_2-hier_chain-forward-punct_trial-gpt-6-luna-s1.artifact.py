from datetime import timedelta


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    period_seconds = 30 * 24 * 60 * 60
    remaining_seconds = max(
        0, min(period_seconds, int((period_end - changed_at).total_seconds()))
    )
    seats = subscription["billable_seats"]
    date = period_end.date().isoformat()

    def description(plan_name):
        prefix = "Proration "
        suffix = f" through {date}"
        available = 80 - len(prefix) - len(suffix)
        return f"{prefix}{plan_name[:available]}{suffix}"

    def line(kind, amount, plan_name, approved_by, vat_cents):
        if amount < 50:
            return None
        return {
            "subscription_id": subscription["id"],
            "kind": kind,
            "amount_cents": amount,
            "vat_cents": vat_cents,
            "description": description(plan_name),
            "approved_by": approved_by,
        }

    result = []
    credit_numerator = seats * old_price * remaining_seconds
    credit = (credit_numerator + period_seconds - 1) // period_seconds
    credit_line = line(
        "credit",
        credit,
        subscription["plan_name"],
        "Nguyễn Thị Phương Thảo"
        if credit <= 50_000
        else "Ramón Etxeberria-Goñi",
        0,
    )
    if credit_line is not None:
        result.append(credit_line)

    charge = seats * new_price * remaining_seconds // period_seconds
    vat = 0 if subscription.get("vat_id") else charge * 21 // 100
    charge_line = line("charge", charge, new_plan["name"], None, vat)
    if charge_line is not None:
        result.append(charge_line)

    return result