from datetime import datetime


def prorate_seats(subscription: dict, new_plan: dict, changed_at: datetime) -> list[dict]:
    """Return prorated credit and charge lines for a seat plan change."""
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise TypeError("subscription and new_plan must be dictionaries")
    if not isinstance(changed_at, datetime) or changed_at.tzinfo is None or changed_at.utcoffset() is None:
        raise ValueError("changed_at must be timezone-aware")

    try:
        period_end = subscription["period_end"]
        old_price = subscription["seat_price_cents"]
        new_price = new_plan["seat_price_cents"]
        seats = subscription["billable_seats"]
        old_name = subscription["plan_name"]
        new_name = new_plan["name"]
        subscription_id = subscription["id"]
        status = subscription["status"]
    except KeyError as exc:
        raise ValueError(f"missing required field: {exc.args[0]}") from None

    if not isinstance(period_end, datetime) or period_end.tzinfo is None or period_end.utcoffset() is None:
        raise ValueError("period_end must be a timezone-aware datetime")
    if period_end < changed_at:
        raise ValueError("period_end cannot be earlier than changed_at")
    if isinstance(seats, bool) or not isinstance(seats, int) or seats < 0:
        raise ValueError("billable_seats must be a nonnegative integer")
    for label, price in (("old", old_price), ("new", new_price)):
        if isinstance(price, bool) or not isinstance(price, int) or price < 0:
            raise ValueError(f"{label} seat price must be a nonnegative integer")
    if not isinstance(old_name, str) or not isinstance(new_name, str):
        raise ValueError("plan names must be strings")

    if status == "trialing" or new_price < old_price:
        return []

    days = min(30, max(0, (period_end - changed_at).days))
    date_text = period_end.strftime("%Y-%m-%d")

    def description(prefix: str, plan_name: str) -> str:
        fixed = f"{prefix} through {date_text}"
        available = max(0, 80 - len(fixed) - 1)
        return f"{prefix} {plan_name[:available]} through {date_text}" if available else fixed

    lines = []
    credit_numerator = seats * old_price * days
    credit_amount = (credit_numerator + 29) // 30
    if credit_amount >= 50:
        lines.append({
            "subscription_id": subscription_id,
            "kind": "credit",
            "amount_cents": credit_amount,
            "vat_cents": 0,
            "description": description("Unused time on", old_name),
            "approved_by": "Win Tee Fung Tao" if credit_amount <= 50_000 else "Ramón Etxeberria-Goñi",
        })

    charge_amount = seats * new_price * days // 30
    if charge_amount >= 50:
        lines.append({
            "subscription_id": subscription_id,
            "kind": "charge",
            "amount_cents": charge_amount,
            "vat_cents": 0 if subscription.get("vat_id") is not None else charge_amount * 21 // 100,
            "description": description("Prorated seats on", new_name),
            "approved_by": None,
        })

    return lines