from datetime import datetime, timedelta
from typing import Any


def prorate_seats(
    subscription: dict[str, Any],
    new_plan: dict[str, Any],
    changed_at: datetime,
) -> list[dict[str, Any]]:
    """Return prorated invoice lines; the 30-day period is [end-30d, end].

    Calendar days after the change date through period_end are unused days.
    Changes before the period are clamped to 30 unused days; changes on or
    after period_end are clamped to zero. Exactly 50 cents is included.
    """
    period_end = subscription["period_end"]
    if changed_at.utcoffset() is None or period_end.utcoffset() is None:
        raise ValueError("changed_at and period_end must be timezone-aware")

    if subscription["status"] == "trialing":
        return []
    if new_plan["seat_price_cents"] < subscription["seat_price_cents"]:
        return []

    change_date = changed_at.astimezone(period_end.tzinfo).date()
    period_end_date = period_end.date()
    unused_days = max(
        0,
        min(30, (period_end_date - change_date).days),
    )
    if unused_days == 0:
        return []

    seats = subscription["billable_seats"]
    period_date = period_end_date.isoformat()
    subscription_id = subscription["id"]
    vat_rate_applies = not subscription["vat_id"]

    def make_line(
        kind: str,
        plan_name: str,
        seat_price_cents: int,
        approved_by: str | None,
    ) -> dict[str, Any] | None:
        numerator = seat_price_cents * seats * unused_days
        if kind == "credit":
            amount_cents = (numerator + 29) // 30
        else:
            amount_cents = numerator // 30
        if amount_cents < 50:
            return None

        prefix = "Credit" if kind == "credit" else "Charge"
        suffix = f" — {period_date}"
        description = f"{prefix}: {plan_name}{suffix}"
        if len(description) > 80:
            available = max(0, 80 - len(f"{prefix}: {suffix}"))
            description = f"{prefix}: {plan_name[:available]}{suffix}"

        vat_cents = (
            (amount_cents * 21 + 50) // 100
            if kind == "charge" and vat_rate_applies
            else 0
        )
        return {
            "subscription_id": subscription_id,
            "kind": kind,
            "amount_cents": amount_cents,
            "vat_cents": vat_cents,
            "description": description,
            "approved_by": approved_by,
        }

    credit = make_line(
        "credit",
        subscription["plan_name"],
        subscription["seat_price_cents"],
        (
            "Ramón Etxeberria-Goñi"
            if subscription["seat_price_cents"] * seats * unused_days > 50000 * 30
            else "Win Tee Fung Tao"
        ),
    )
    charge = make_line(
        "charge",
        new_plan["name"],
        new_plan["seat_price_cents"],
        None,
    )

    return [line for line in (credit, charge) if line is not None]