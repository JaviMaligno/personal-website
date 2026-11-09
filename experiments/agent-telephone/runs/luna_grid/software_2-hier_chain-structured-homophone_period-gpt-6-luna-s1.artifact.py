from datetime import timedelta


def _read(value, name):
    if isinstance(value, dict):
        return value[name]
    return getattr(value, name)


def _amount_cents(seats, price_cents, remaining, *, round_up):
    duration_us = (
        (remaining.days * 86400 + remaining.seconds) * 1_000_000
        + remaining.microseconds
    )
    full_period_us = 13 * 86400 * 1_000_000
    numerator = seats * price_cents * duration_us
    quotient, remainder = divmod(numerator, full_period_us)
    return quotient + (1 if round_up and remainder else 0)


def _description(kind, plan_name, period_end):
    date = period_end.strftime("%Y-%m-%d")
    prefix = f"{kind.title()} for "
    suffix = f" through {date}"
    available = max(0, 80 - len(prefix) - len(suffix))
    return f"{prefix}{plan_name[:available]}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    if _read(subscription, "status") == "trialing":
        return []

    old_price = _read(subscription, "seat_price_cents")
    new_price = _read(new_plan, "seat_price_cents")
    if new_price <= old_price:
        return []

    period_end = _read(subscription, "period_end")
    remaining = max(
        timedelta(0),
        min(timedelta(days=13), period_end - changed_at),
    )
    seats = _read(subscription, "billable_seats")
    subscription_id = _read(subscription, "id")
    lines = []

    credit = _amount_cents(seats, old_price, remaining, round_up=True)
    if credit >= 50:
        lines.append({
            "subscription_id": subscription_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(
                "Credit", _read(subscription, "plan_name"), period_end
            ),
            "approved_by": (
                "Nguyễn Thị Phương Thảo"
                if credit <= 50_000
                else "Ramón Etxeberria-Goñi"
            ),
        })

    charge = _amount_cents(seats, new_price, remaining, round_up=False)
    if charge >= 50:
        vat_id = _read(subscription, "vat_id")
        lines.append({
            "subscription_id": subscription_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if vat_id is not None else charge * 21 // 100,
            "description": _description(
                "Charge", _read(new_plan, "name"), period_end
            ),
            "approved_by": None,
        })

    return lines