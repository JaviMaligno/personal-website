from datetime import datetime


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    period_end = subscription["period_end"]
    if period_end <= changed_at:
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:
        return []

    elapsed = period_end - changed_at
    elapsed_microseconds = (
        elapsed.days * 86_400_000_000
        + elapsed.seconds * 1_000_000
        + elapsed.microseconds
    )
    denominator = 30 * 86_400_000_000
    multiplier = subscription["billable_seats"] * elapsed_microseconds
    period_date = (
        f"{period_end.year:04d}-{period_end.month:02d}-{period_end.day:02d}"
    )

    def make_line(kind, plan_name, numerator, round_up):
        amount = (
            -(-numerator // denominator)
            if round_up
            else numerator // denominator
        )
        if amount < 50:
            return None

        prefix = "Prorated credit for " if kind == "credit" else "Prorated charge for "
        suffix = f" through {period_date}"
        plan_name = str(plan_name)
        description = prefix + plan_name[: max(0, 80 - len(prefix) - len(suffix))] + suffix

        return {
            "subscription_id": subscription["id"],
            "kind": kind,
            "amount_cents": amount,
            "vat_cents": 0 if kind == "credit" or subscription.get("vat_id") else amount * 21 // 100,
            "description": description,
            "approved_by": (
                ("Nguyễn Thị Phương Thảo" if amount <= 50_000 else "Ramón Etxeberria-Goñi")
                if kind == "credit"
                else None
            ),
        }

    credit = make_line(
        "credit", subscription["plan_name"], old_price * multiplier, True
    )
    charge = make_line("charge", new_plan["name"], new_price * multiplier, False)
    return [line for line in (credit, charge) if line is not None]