from datetime import date, datetime, timezone
from fractions import Fraction


def _plan_price(plan):
    for key in ("price_per_seat_cents", "per_seat_price_cents"):
        if key in plan:
            return int(plan[key])
    raise KeyError("plan must contain price_per_seat_cents")


def _plan_name(plan):
    return str(plan.get("name", plan.get("id", "plan")))


def _as_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return datetime.fromisoformat(value)


def _ceil_fraction(value):
    return -(-value.numerator // value.denominator)


def _vat(amount_cents):
    value = Fraction(amount_cents * 21, 100)
    return (2 * value.numerator + value.denominator) // (2 * value.denominator)


def _description(plan, period_end):
    date_text = period_end.strftime("%Y-%m-%d")
    suffix = f" through {date_text}"
    name = _plan_name(plan)
    return name[: 80 - len(suffix)] + suffix


def prorate_seats(subscription, new_plan, changed_at) -> list[dict]:
    if subscription.get("status") == "trialing":
        return []

    old_plan = subscription.get("current_plan", subscription.get("plan"))
    if old_plan is None:
        raise KeyError("subscription must contain current_plan")
    old_price = _plan_price(old_plan)
    new_price = _plan_price(new_plan)
    if new_price < old_price:
        return []

    period_end = _as_datetime(subscription["period_end"])
    changed_at = _as_datetime(changed_at)
    if period_end.utcoffset() is None or changed_at.utcoffset() is None:
        raise ValueError("changed_at and period_end must be timezone-aware")

    period_start = _as_datetime(subscription.get("period_start", changed_at))
    if period_start.utcoffset() is None:
        raise ValueError("period_start must be timezone-aware")

    elapsed = changed_at - period_start
    unused_seconds = max(0, min(30 * 86400, 30 * 86400 - elapsed.days * 86400 - elapsed.seconds - elapsed.microseconds / 1_000_000))
    fraction = Fraction(int(unused_seconds * 1_000_000), 30 * 86400 * 1_000_000)
    seats = int(subscription["billable_seats"])
    result = []

    credit = _ceil_fraction(Fraction(old_price * seats) * fraction)
    if credit >= 50:
        result.append({
            "subscription_id": subscription["subscription_id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(old_plan, period_end),
            "approved_by": "Nguyễn Thị Phương Thảo" if credit <= 50_000 else "Ramón Etxebarria-Goñi",
        })

    charge = (new_price * seats * fraction.numerator) // fraction.denominator
    if charge >= 50:
        result.append({
            "subscription_id": subscription["subscription_id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if subscription.get("vat_id") else _vat(charge),
            "description": _description(new_plan, period_end),
            "approved_by": None,
        })
    return result