from datetime import datetime, timezone


def _aware_datetime(value, field):
    if not isinstance(value, datetime):
        raise ValueError(f"{field} must be a timezone-aware datetime")
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise ValueError(f"{field} must be a timezone-aware datetime") from exc
    if value.tzinfo is None or offset is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _integer(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _truncated_description(kind, plan_name, period_end):
    prefix = f"{kind.capitalize()} for "
    suffix = f" through {period_end:%Y-%m-%d}"
    available = 80 - len(prefix) - len(suffix)
    if available < 1:
        raise ValueError("description cannot fit within 80 characters")
    return prefix + plan_name[:available] + suffix


def _line(subscription_id, kind, amount, vat, plan_name, period_end, approved_by):
    return {
        "subscription_id": subscription_id,
        "kind": kind,
        "amount_cents": amount,
        "vat_cents": vat,
        "description": _truncated_description(kind, plan_name, period_end),
        "approved_by": approved_by,
    }


def _round_up(numerator, denominator):
    return (numerator + denominator - 1) // denominator


def _round_down(numerator, denominator):
    return numerator // denominator


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise ValueError("subscription and new_plan must be dictionaries")

    required_subscription = (
        "id", "status", "plan_name", "seat_price_cents",
        "billable_seats", "vat_id", "period_end",
    )
    if any(key not in subscription for key in required_subscription):
        raise ValueError("subscription is missing a required field")
    if any(key not in new_plan for key in ("name", "seat_price_cents")):
        raise ValueError("new_plan is missing a required field")

    subscription_id = subscription["id"]
    status = subscription["status"]
    old_name = subscription["plan_name"]
    new_name = new_plan["name"]
    if subscription_id is None or not isinstance(status, str):
        raise ValueError("invalid subscription id or status")
    if not isinstance(old_name, str) or not isinstance(new_name, str):
        raise ValueError("plan names must be strings")

    old_price = _integer(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _integer(new_plan["seat_price_cents"], "new seat_price_cents")
    billable_seats = _integer(subscription["billable_seats"], "billable_seats")
    period_end = _aware_datetime(subscription["period_end"], "period_end")
    changed_at = _aware_datetime(changed_at, "changed_at")

    if status == "trialing" or new_price < old_price:
        return []

    remaining_seconds = max(
        0, min(13 * 86400, (period_end - changed_at).total_seconds())
    )
    denominator = 13 * 86400
    credit_amount = _round_up(
        old_price * billable_seats * int(remaining_seconds), denominator
    )
    charge_amount = _round_down(
        new_price * billable_seats * int(remaining_seconds), denominator
    )
    lines = []

    if credit_amount >= 50:
        approver = (
            "Ramón Etxeberria-Goñi"
            if credit_amount > 50_000
            else "Nguyễn Thị Phương Thảo"
        )
        lines.append(
            _line(
                subscription_id, "credit", credit_amount, 0,
                old_name, period_end, approver,
            )
        )

    if charge_amount >= 50:
        vat = 0 if subscription["vat_id"] is not None else (
            charge_amount * 21 + 50
        ) // 100
        lines.append(
            _line(
                subscription_id, "charge", charge_amount, vat,
                new_name, period_end, None,
            )
        )

    return lines