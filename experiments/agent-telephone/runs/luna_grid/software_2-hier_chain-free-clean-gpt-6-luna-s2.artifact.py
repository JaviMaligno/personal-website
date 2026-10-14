from datetime import datetime


def prorate_seats(subscription, new_plan, changed_at) -> list[dict]:
    if subscription.get("status") == "trialing":
        return []

    old_plan = subscription.get("current_plan", subscription.get("plan"))
    old_price = old_plan["per_seat_price_cents"]
    new_price = new_plan["per_seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    if changed_at.tzinfo is None or period_end.tzinfo is None:
        raise ValueError("Datetimes must be timezone-aware")

    fraction = max(0.0, min(1.0, (period_end - changed_at).total_seconds() / (30 * 86400)))
    seats = subscription["billable_seats"]
    old_raw = seats * old_price * fraction
    new_raw = seats * new_price * fraction
    old_cents = int(-(-old_raw // 1))
    new_cents = int(new_raw // 1)

    date = period_end.strftime("%Y-%m-%d")
    subscription_id = subscription["subscription_id"]
    lines = []

    def description(kind, name):
        prefix = f"Prorated {kind} for "
        suffix = f" through {date}"
        return prefix + name[: 80 - len(prefix) - len(suffix)] + suffix

    if old_cents >= 50:
        lines.append({
            "subscription_id": subscription_id,
            "kind": "credit",
            "amount_cents": old_cents,
            "vat_cents": 0,
            "description": description("credit", old_plan["name"]),
            "approved_by": (
                "Nguyễn Thị Phương Thảo"
                if old_cents <= 50_000
                else "Ramón Etxebarria-Goñi"
            ),
        })

    if new_cents >= 50:
        vat_cents = 0 if subscription.get("vat_id") else (new_cents * 21 + 50) // 100
        lines.append({
            "subscription_id": subscription_id,
            "kind": "charge",
            "amount_cents": new_cents,
            "vat_cents": vat_cents,
            "description": description("charge", new_plan["name"]),
            "approved_by": None,
        })

    return lines