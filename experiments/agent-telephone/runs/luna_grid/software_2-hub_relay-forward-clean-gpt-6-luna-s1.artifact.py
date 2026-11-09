from datetime import datetime, timezone

CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"

_PERIOD_MICROSECONDS = 30 * 24 * 60 * 60 * 1_000_000


def _round_half_up(numerator: int, denominator: int) -> int:
    """Round a nonnegative ratio to the nearest integer, ties upward."""
    return (2 * numerator + denominator) // (2 * denominator)


def _unused_microseconds(changed_at: datetime, period_end: datetime) -> int:
    """Use elapsed UTC time: a day is 24 hours, and the change instant is excluded."""
    if changed_at.utcoffset() is None or period_end.utcoffset() is None:
        raise ValueError("changed_at and period_end must be timezone-aware")

    changed_utc = changed_at.astimezone(timezone.utc)
    end_utc = period_end.astimezone(timezone.utc)
    delta = end_utc - changed_utc
    microseconds = (
        (delta.days * 86_400 + delta.seconds) * 1_000_000
        + delta.microseconds
    )
    return max(0, min(microseconds, _PERIOD_MICROSECONDS))


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    unused = _unused_microseconds(changed_at, subscription["period_end"])
    if unused == 0:
        return []

    seats = subscription["billable_seats"]
    period_end_date = subscription["period_end"].strftime("%Y-%m-%d")

    def amount_for(price):
        return _round_half_up(
            price * seats * unused,
            _PERIOD_MICROSECONDS,
        )

    def description(action, plan_name):
        suffix = f"{action} {period_end_date}"
        name = str(plan_name)
        available = max(0, 80 - len(suffix) - 2)
        return f"{name[:available]}: {suffix}" if available else suffix

    lines = []
    credit_amount = amount_for(old_price)
    if credit_amount >= 50:
        lines.append(
            {
                "subscription_id": subscription["id"],
                "kind": "credit",
                "amount_cents": credit_amount,
                "vat_cents": _round_half_up(credit_amount * 21, 100),
                "description": description("Credit through", subscription["plan_name"]),
                "approved_by": (
                    LARGE_CREDIT_APPROVER
                    if credit_amount > 50_000
                    else CREDIT_APPROVER
                ),
            }
        )

    charge_amount = amount_for(new_price)
    if charge_amount >= 50:
        vat_id = subscription["vat_id"]
        lines.append(
            {
                "subscription_id": subscription["id"],
                "kind": "charge",
                "amount_cents": charge_amount,
                "vat_cents": 0 if vat_id else _round_half_up(charge_amount * 21, 100),
                "description": description("Charge through", new_plan["name"]),
                "approved_by": None,
            }
        )

    return lines