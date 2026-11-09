from datetime import date, datetime


def prorate_seats(subscription, new_plan, changed_at):
    """Return upgrade invoice lines.

    Unused days are the calendar-date difference from changed_at to period_end,
    clamped to 0–13. Credits round up and charges round down. VAT is rounded
    half-up to cents and applies to all lines unless vat_id is present.
    """
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:
        return []

    if changed_at.utcoffset() is None:
        raise ValueError("changed_at must be timezone-aware")

    period_end = subscription["period_end"]
    if isinstance(period_end, datetime):
        end_date = period_end.date()
    elif isinstance(period_end, date):
        end_date = period_end
    else:
        raise TypeError("period_end must be a date or datetime")

    unused_days = max(0, min(13, (end_date - changed_at.date()).days))
    seats = subscription["billable_seats"]
    lines = []

    def add_line(kind, price, round_up):
        numerator = price * seats * unused_days
        amount = (numerator + 12) // 13 if round_up else numerator // 13
        if amount < 50:
            return

        vat = 0
        if not subscription.get("vat_id"):
            vat = (amount * 21 + 50) // 100

        plan_name = subscription["plan_name"] if kind == "credit" else new_plan["name"]
        suffix = f" through {end_date:%Y-%m-%d}"
        description = f"{plan_name}{suffix}"
        if len(description) > 80:
            description = f"{plan_name[:80 - len(suffix)]}{suffix}"

        lines.append({
            "subscription_id": subscription["id"],
            "kind": kind,
            "amount_cents": amount,
            "vat_cents": vat,
            "description": description,
            "approved_by": (
                "Ramón Etxeberria-Goñi" if amount > 50_000
                else "Nguyễn Thị Phương Thảo"
            ) if kind == "credit" else None,
        })

    add_line("credit", old_price, True)
    add_line("charge", new_price, False)
    return lines