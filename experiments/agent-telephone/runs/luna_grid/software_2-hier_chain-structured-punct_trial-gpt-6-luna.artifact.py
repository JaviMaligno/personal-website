from datetime import datetime, timedelta


def prorate_seats(subscription, new_plan, changed_at):
    def required(mapping, key):
        if not isinstance(mapping, dict) or key not in mapping:
            raise ValueError(f"Missing required field: {key}")
        return mapping[key]

    def nonnegative_int(value, field):
        if type(value) is not int or value < 0:
            raise ValueError(f"{field} must be a nonnegative integer")
        return value

    def aware_datetime(value, field):
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field} must be a timezone-aware datetime")
        return value

    sub_id = required(subscription, "id")
    status = required(subscription, "status")
    if not isinstance(status, str):
        raise ValueError("status must be a string")

    old_name = required(subscription, "plan_name")
    new_name = required(new_plan, "name")
    if not isinstance(old_name, str) or not isinstance(new_name, str):
        raise ValueError("plan names must be strings")

    old_price = nonnegative_int(required(subscription, "seat_price_cents"), "seat_price_cents")
    new_price = nonnegative_int(required(new_plan, "seat_price_cents"), "new_plan.seat_price_cents")
    seats = nonnegative_int(required(subscription, "seats"), "seats")
    billable_seats = nonnegative_int(required(subscription, "billable_seats"), "billable_seats")
    if "vat_id" not in subscription:
        raise ValueError("Missing required field: vat_id")
    vat_id = subscription["vat_id"]

    period_end = aware_datetime(required(subscription, "period_end"), "period_end")
    changed_at = aware_datetime(changed_at, "changed_at")

    if status == "trialing" or new_price < old_price:
        return []

    remaining = period_end - changed_at
    remaining_us = (
        remaining.days * 86_400_000_000
        + remaining.seconds * 1_000_000
        + remaining.microseconds
    )
    period_us = 30 * 86_400_000_000
    unused_us = min(period_us, max(0, remaining_us))
    if unused_us == 0:
        return []

    def description(prefix, name):
        date = period_end.strftime("%Y-%m-%d")
        fixed = f"{prefix} for  through {date}"
        return f"{prefix} for {name[:max(0, 80 - len(fixed))]} through {date}"

    def line(kind, price, name):
        numerator = price * billable_seats * unused_us
        amount = (
            (numerator + period_us - 1) // period_us
            if kind == "credit"
            else numerator // period_us
        )
        if amount < 50:
            return None

        if kind == "credit":
            vat = 0
            approver = "Ramón Etxeberria-Goñi" if amount > 50_000 else "Nguyễn Thị Phương Thảo"
        else:
            vat = 0 if vat_id is not None else (amount * 21 * 2 + 100) // 200
            approver = None

        return {
            "subscription_id": sub_id,
            "kind": kind,
            "amount_cents": amount,
            "vat_cents": vat,
            "description": description("Credit" if kind == "credit" else "Charge", name),
            "approved_by": approver,
        }

    credit = line("credit", old_price, old_name)
    charge = line("charge", new_price, new_name)
    return [item for item in (credit, charge) if item is not None]