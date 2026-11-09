from datetime import datetime

PERIOD_MICROSECONDS = 30 * 24 * 60 * 60 * 1_000_000
MINIMUM_LINE_CENTS = 50
CREDIT_APPROVAL_LIMIT_CENTS = 50_000
LOWER_CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
HIGHER_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"


def _description(kind: str, plan_name: object, period_end: datetime) -> str:
    date_text = period_end.strftime("%Y-%m-%d")
    prefix = f"Prorated {kind}: "
    suffix = f" through {date_text}"
    name = str(plan_name)
    name = name[: max(0, 80 - len(prefix) - len(suffix))]
    return f"{prefix}{name}{suffix}"


def prorate_seats(subscription: dict, new_plan: dict, changed_at: datetime) -> list[dict]:
    if subscription["status"] == "trialing":
        return []

    old_plan = subscription["plan"]
    if new_plan["seat_price_cents"] < old_plan["seat_price_cents"]:
        return []

    period_end = subscription["period_end"]
    if changed_at >= period_end:
        return []

    remaining = period_end - changed_at
    remaining_microseconds = (
        (remaining.days * 86_400 + remaining.seconds) * 1_000_000
        + remaining.microseconds
    )
    seats = subscription["billable_seats"]
    divisor = PERIOD_MICROSECONDS

    old_numerator = old_plan["seat_price_cents"] * seats * remaining_microseconds
    new_numerator = new_plan["seat_price_cents"] * seats * remaining_microseconds

    credit_cents = (old_numerator + divisor - 1) // divisor
    charge_cents = new_numerator // divisor
    lines = []
    subscription_id = subscription["subscription_id"]

    if credit_cents >= MINIMUM_LINE_CENTS:
        lines.append({
            "subscription_id": subscription_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _description("credit", old_plan["name"], period_end),
            "approved_by": (
                LOWER_CREDIT_APPROVER
                if credit_cents <= CREDIT_APPROVAL_LIMIT_CENTS
                else HIGHER_CREDIT_APPROVER
            ),
        })

    if charge_cents >= MINIMUM_LINE_CENTS:
        vat_cents = (
            0
            if subscription.get("vat_id")
            else (charge_cents * 21 + 50) // 100
        )
        lines.append({
            "subscription_id": subscription_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _description("charge", new_plan["name"], period_end),
            "approved_by": None,
        })

    return lines