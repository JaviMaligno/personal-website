from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from typing import Any, Mapping


def prorate_seats(
    subscription: Mapping[str, Any],
    new_plan: Mapping[str, Any],
    changed_at: datetime,
) -> list[dict[str, Any]]:
    """Return prorated credit and charge lines in integer cents.

    Prices are per-seat integer cents, supplied as ``seat_price_cents`` on the
    plan or subscription (the subscription may also nest its current plan under
    ``plan``). ``period_end`` may be a date, datetime, or YYYY-MM-DD string.
    """
    if subscription.get("status") == "trialing":
        return []
    if changed_at.tzinfo is None or changed_at.utcoffset() is None:
        raise ValueError("changed_at must be timezone-aware")

    def price(obj: Mapping[str, Any]) -> int:
        for key in ("seat_price_cents", "price_per_seat_cents", "price_cents"):
            if key in obj:
                return int(obj[key])
        raise KeyError("seat_price_cents")

    old_plan = subscription.get("plan", subscription)
    old_price = price(old_plan)
    new_price = price(new_plan)
    if new_price < old_price:
        return []

    end = subscription["period_end"]
    if isinstance(end, str):
        end = date.fromisoformat(end)
    if isinstance(end, datetime):
        if end.tzinfo is None or end.utcoffset() is None:
            raise ValueError("period_end datetime must be timezone-aware")
        end_at = end.astimezone(changed_at.tzinfo)
    elif isinstance(end, date):
        end_at = datetime.combine(end, time.min, tzinfo=changed_at.tzinfo)
    else:
        raise TypeError("period_end must be a date, datetime, or YYYY-MM-DD string")

    remaining = Decimal(str((end_at - changed_at).total_seconds())) / Decimal(86400)
    remaining = max(Decimal(0), min(Decimal(30), remaining))
    fraction = remaining / Decimal(30)
    seats = int(subscription["billable_seats"])
    date_text = end_at.date().isoformat()
    subscription_id = subscription["subscription_id"]

    def plan_name(plan: Mapping[str, Any]) -> str:
        return str(plan.get("name", plan.get("plan_name", "plan")))

    def description(action: str, plan: Mapping[str, Any]) -> str:
        suffix = f" {action} through {date_text}"
        return plan_name(plan)[: max(0, 80 - len(suffix))] + suffix

    lines: list[dict[str, Any]] = []
    credit = int(
        (Decimal(old_price * seats) * fraction).to_integral_value(rounding=ROUND_CEILING)
    )
    if credit >= 50:
        lines.append(
            {
                "subscription_id": subscription_id,
                "kind": "credit",
                "amount_cents": -credit,
                "vat_cents": 0,
                "description": description("credit", old_plan),
                "approved_by": (
                    "Ramón Etxeberria-Goñi"
                    if credit > 50_000
                    else "Nguyễn Thị Phương Thảo"
                ),
            }
        )

    charge = int(
        (Decimal(new_price * seats) * fraction).to_integral_value(rounding=ROUND_FLOOR)
    )
    if charge >= 50:
        vat = 0
        if not subscription.get("vat_id"):
            vat = int(
                (Decimal(charge) * Decimal("0.21")).to_integral_value(
                    rounding=ROUND_HALF_UP
                )
            )
        lines.append(
            {
                "subscription_id": subscription_id,
                "kind": "charge",
                "amount_cents": charge,
                "vat_cents": vat,
                "description": description("charge", new_plan),
                "approved_by": None,
            }
        )
    return lines