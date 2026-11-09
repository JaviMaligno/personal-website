def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    unused_days = max(0, min(30, (period_end - changed_at).days))
    seats = subscription["billable_seats"]
    date_text = period_end.strftime("%Y-%m-%d")

    def make_line(kind, plan_name, seat_price, amount):
        if amount < 50:
            return None

        prefix = "Credit: " if kind == "credit" else "Charge: "
        suffix = f" {date_text}"
        description = prefix + str(plan_name) + suffix
        if len(description) > 80:
            available = 80 - len(prefix) - len(suffix)
            description = prefix + str(plan_name)[:available] + suffix

        if kind == "credit":
            vat_cents = 0
            approved_by = (
                "Nguyễn Thị Phương Thảo"
                if amount <= 50_000
                else "Ramón Etxebarria-Goñi"
            )
        else:
            vat_cents = 0 if subscription.get("vat_id") else amount * 21 // 100
            approved_by = None

        return {
            "subscription_id": subscription["id"],
            "kind": kind,
            "amount_cents": amount,
            "vat_cents": vat_cents,
            "description": description,
            "approved_by": approved_by,
        }

    credit_numerator = old_price * seats * unused_days
    charge_numerator = new_price * seats * unused_days

    credit = make_line(
        "credit",
        subscription["plan_name"],
        old_price,
        (credit_numerator + 29) // 30,
    )
    charge = make_line(
        "charge",
        new_plan["name"],
        new_price,
        charge_numerator // 30,
    )

    return [line for line in (credit, charge) if line is not None]