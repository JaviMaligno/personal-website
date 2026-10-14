from datetime import datetime, timedelta

DAY = timedelta(days=1)
PERIOD = 30 * DAY
MIN_LINE_CENTS = 50
CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"


def prorate_seats(subscription: dict, new_plan: dict, changed_at: datetime) -> list[dict]:
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:
        return []

    period_end = subscription["period_end"]
    remaining = min(max(period_end - changed_at, timedelta(0)), PERIOD)
    numerator = subscription["billable_seats"] * remaining
    denominator = PERIOD

    def prorated_cents(price: int, round_up: bool) -> int:
        value, remainder = divmod(price * numerator, denominator)
        return value + int(round_up and remainder != 0)

    date_text = period_end.strftime("%Y-%m-%d")

    def description(plan_name: str) -> str:
        suffix = f" through {date_text}"
        return f"{plan_name[:80 - len(suffix)]}{suffix}"

    credit_cents = prorated_cents(old_price, True)
    charge_cents = prorated_cents(new_price, False)
    lines = []

    if credit_cents >= MIN_LINE_CENTS:
        approver = (
            LARGE_CREDIT_APPROVER
            if credit_cents > 50_000
            else CREDIT_APPROVER
        )
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": description(subscription["plan_name"]),
            "approved_by": approver,
        })

    if charge_cents >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": 0 if subscription["vat_id"] else (charge_cents * 21 + 50) // 100,
            "description": description(new_plan["name"]),
            "approved_by": None,
        })

    return lines