from datetime import datetime
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

__all__ = ["prorate_seats"]

_CENT = Decimal("0.01")
_DAYS = Decimal("30")
_CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
_LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"


def prorate_seats(subscription, new_plan, changed_at):
    """Return upgrade proration invoice lines for a subscription."""
    def get(obj, key):
        return obj[key] if isinstance(obj, dict) else getattr(obj, key)

    if get(subscription, "status") == "trialing":
        return []

    period_end = get(subscription, "period_end")
    if changed_at.tzinfo is None or changed_at.utcoffset() is None:
        raise ValueError("changed_at must be timezone-aware")
    if period_end.tzinfo is None or period_end.utcoffset() is None:
        raise ValueError("period_end must be timezone-aware")

    remaining = Decimal(str((period_end - changed_at).total_seconds())) / Decimal("86400")
    if remaining <= 0:
        return []

    seats = Decimal(str(get(subscription, "billable_seats")))
    old_plan = get(subscription, "current_plan")
    old_price = Decimal(str(get(old_plan, "seat_price")))
    new_price = Decimal(str(get(new_plan, "seat_price")))
    if new_price <= old_price:
        return []

    period_date = period_end.strftime("%Y-%m-%d")

    def description(plan):
        name = str(get(plan, "name"))
        suffix = f" through {period_date}"
        return name[: max(0, 80 - len(suffix))] + suffix

    lines = []
    credit = (old_price * seats * remaining / _DAYS).quantize(
        _CENT, rounding=ROUND_CEILING
    )
    if credit >= Decimal("0.50"):
        lines.append({
            "description": description(old_plan),
            "amount": -credit,
            "vat_rate": Decimal("0"),
            "approved_by": (
                _LARGE_CREDIT_APPROVER if credit > 500 else _CREDIT_APPROVER
            ),
        })

    charge = ((new_price - old_price) * seats * remaining / _DAYS).quantize(
        _CENT, rounding=ROUND_FLOOR
    )
    if charge >= Decimal("0.50"):
        lines.append({
            "description": description(new_plan),
            "amount": charge,
            "vat_rate": Decimal("0") if get(subscription, "vat_id") else Decimal("0.21"),
            "approved_by": None,
        })

    return lines