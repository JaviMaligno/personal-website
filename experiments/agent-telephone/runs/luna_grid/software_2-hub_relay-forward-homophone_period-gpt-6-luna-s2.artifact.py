from datetime import datetime
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR


def prorate_seats(subscription, new_plan, changed_at):
    """Return credit then charge invoice lines for a seat plan change.

    Clarification is needed before locking behavior: whether the change date
    and period end count; what to do when remaining days are outside 0–13;
    how to round VAT; and whether a missing or empty vat_id means reverse
    charge. This implementation rejects out-of-range periods and treats a
    nonempty vat_id as reverse charge. Its date difference uses calendar days
    (period_end.date() - changed_at.date()); confirm inclusivity before use.
    """
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    if not isinstance(changed_at, datetime) or not isinstance(period_end, datetime):
        raise TypeError("changed_at and period_end must be datetimes")
    if changed_at.utcoffset() is None or period_end.utcoffset() is None:
        raise ValueError("changed_at and period_end must be timezone-aware")

    remaining_days = (period_end.date() - changed_at.date()).days
    if not 0 <= remaining_days <= 13:
        raise ValueError("remaining period must be between 0 and 13 days")

    fraction = Decimal(remaining_days) / Decimal(13)
    seats = subscription["billable_seats"]
    end_date = period_end.strftime("%Y-%m-%d")
    lines = []

    def description(plan_name, kind):
        suffix = f" {kind} through {end_date}"
        name = str(plan_name)
        return name[: max(0, 80 - len(suffix))] + suffix

    credit = int(
        (Decimal(old_price * seats) * fraction).to_integral_value(
            rounding=ROUND_CEILING
        )
    )
    if credit >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": description(subscription["plan_name"], "credit"),
            "approved_by": (
                "Nguyễn Thị Phương Thảo"
                if credit <= 50000
                else "Ramón Etxebarria-Goñi"
            ),
        })

    charge = int(
        (Decimal(new_price * seats) * fraction).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )
    if charge >= 50:
        if subscription.get("vat_id"):
            vat = 0
        else:
            exact_vat = Decimal(charge) * Decimal("0.21")
            if exact_vat != exact_vat.to_integral_value():
                raise ValueError("VAT rounding rule requires clarification")
            vat = int(exact_vat)
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": description(new_plan["name"], "charge"),
            "approved_by": None,
        })

    return lines