from datetime import date, datetime, timedelta


def prorate_seats(subscription, new_plan, changed_at):
    """Return prorated invoice lines for a 30-day billing period.

    The period starts 30 days before period_end. Dates, rather than times of
    day, determine the remaining days: changed_at is the start boundary, so
    remaining days are (period_end - changed_at).days, capped at 30.
    """
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    end_date = period_end.date() if isinstance(period_end, datetime) else period_end
    change_date = changed_at.date() if isinstance(changed_at, datetime) else changed_at
    unused_days = max(0, min(30, (end_date - change_date).days))
    if unused_days == 0:
        return []

    seats = subscription["billable_seats"]
    lines = []

    def description(plan_name):
        suffix = end_date.isoformat()
        prefix = f"{plan_name} through "
        available = 80 - len(prefix) - len(suffix)
        return f"{plan_name[:max(0, available)]} through {suffix}"

    def append_line(kind, plan_name, numerator, denominator, approved_by=None):
        amount = (numerator + denominator - 1) // denominator if kind == "credit" else numerator // denominator
        if amount < 50:
            return
        vat = 0
        if kind == "charge" and not subscription["vat_id"]:
            vat = (amount * 21 + 50) // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": kind,
            "amount_cents": amount,
            "vat_cents": vat,
            "description": description(plan_name),
            "approved_by": approved_by,
        })

    credit_numerator = old_price * seats * unused_days
    append_line(
        "credit",
        subscription["plan_name"],
        credit_numerator,
        30,
        "Ramón Etxeberria-Goñi" if credit_numerator > 50000 * 30 else "Win Tee Fung Tao",
    )

    charge_numerator = new_price * seats * unused_days
    append_line("charge", new_plan["name"], charge_numerator, 30)

    return lines