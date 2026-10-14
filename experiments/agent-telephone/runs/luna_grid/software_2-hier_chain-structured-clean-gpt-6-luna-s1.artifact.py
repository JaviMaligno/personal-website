from datetime import datetime, timedelta

_MICROSECONDS_PER_DAY = 86_400_000_000
_CREDIT_APPROVAL = "Nguyễn Thị Phương Thảo"
_HIGH_CREDIT_APPROVAL = "Ramón Etxeberria-Goñi"


def _prorated_cents(price_cents: int, seats: int, unused_microseconds: int, *, round_up: bool) -> int:
    numerator = price_cents * seats * unused_microseconds
    denominator = 30 * _MICROSECONDS_PER_DAY
    if round_up:
        return (numerator + denominator - 1) // denominator
    return numerator // denominator


def _description(plan_name: str, period_end: datetime) -> str:
    suffix = f" plan ({period_end:%Y-%m-%d})"
    available = max(0, 80 - len(suffix))
    return f"{plan_name[:available]}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    if changed_at >= period_end:
        return []

    remaining = period_end - changed_at
    unused_microseconds = (
        remaining.days * _MICROSECONDS_PER_DAY
        + remaining.seconds * 1_000_000
        + remaining.microseconds
    )
    unused_microseconds = min(unused_microseconds, 30 * _MICROSECONDS_PER_DAY)
    seats = subscription["billable_seats"]
    lines = []

    credit = _prorated_cents(old_price, seats, unused_microseconds, round_up=True)
    if credit >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(subscription["plan_name"], period_end),
            "approved_by": _HIGH_CREDIT_APPROVAL if credit > 50_000 else _CREDIT_APPROVAL,
        })

    charge = _prorated_cents(new_price, seats, unused_microseconds, round_up=False)
    if charge >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if subscription.get("vat_id") else charge * 21 // 100,
            "description": _description(new_plan["name"], period_end),
            "approved_by": None,
        })

    return lines