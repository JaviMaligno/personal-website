import datetime as _datetime


_PERIOD_MICROSECONDS = 13 * 24 * 60 * 60 * 1_000_000
_CREDIT_APPROVER_LIMIT_CENTS = 50_000


def _validate_nonnegative_integer(value, field):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} must be an integer")
    if value < 0:
        raise ValueError(f"{field} must be nonnegative")
    return value


def _unused_fraction(changed_at, period_end):
    for field, value in (("changed_at", changed_at), ("period_end", period_end)):
        if not isinstance(value, _datetime.datetime):
            raise TypeError(f"{field} must be a datetime")
        if value.utcoffset() is None:
            raise ValueError(f"{field} must be timezone-aware")

    elapsed = (
        period_end.astimezone(_datetime.timezone.utc)
        - changed_at.astimezone(_datetime.timezone.utc)
    )
    elapsed_microseconds = (
        elapsed.days * 24 * 60 * 60 * 1_000_000
        + elapsed.seconds * 1_000_000
        + elapsed.microseconds
    )
    return min(max(elapsed_microseconds, 0), _PERIOD_MICROSECONDS)


def _rounded_amounts(old_price, new_price, billable_seats, fraction_numerator):
    denominator = _PERIOD_MICROSECONDS
    credit_product = old_price * billable_seats * fraction_numerator
    charge_product = new_price * billable_seats * fraction_numerator
    credit = (credit_product + denominator - 1) // denominator
    charge = charge_product // denominator
    return credit, charge


def _description(kind, plan_name, period_end):
    date = period_end.strftime("%Y-%m-%d")
    prefix = "Credit" if kind == "credit" else "Charge"
    suffix = f" through {date}"
    available = 80 - len(prefix) - 2 - len(suffix)
    name = str(plan_name)[:max(0, available)]
    return f"{prefix}: {name}{suffix}"


def _build_line(subscription, kind, amount, plan_name, period_end):
    vat = 0
    if kind == "charge" and subscription["vat_id"] is None:
        vat = amount * 21 // 100

    approved_by = None
    if kind == "credit":
        approved_by = (
            "Nguyễn Thị Phương Thảo"
            if amount <= _CREDIT_APPROVER_LIMIT_CENTS
            else "Ramón Etxebarria-Goñi"
        )

    return {
        "subscription_id": subscription["id"],
        "kind": kind,
        "amount_cents": amount,
        "vat_cents": vat,
        "description": _description(kind, plan_name, period_end),
        "approved_by": approved_by,
    }


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = _validate_nonnegative_integer(
        subscription["seat_price_cents"], "seat_price_cents"
    )
    new_price = _validate_nonnegative_integer(
        new_plan["seat_price_cents"], "new_plan.seat_price_cents"
    )
    billable_seats = _validate_nonnegative_integer(
        subscription["billable_seats"], "billable_seats"
    )

    if new_price <= old_price:
        return []

    period_end = subscription["period_end"]
    fraction_numerator = _unused_fraction(changed_at, period_end)
    if fraction_numerator == 0:
        return []

    credit, charge = _rounded_amounts(
        old_price, new_price, billable_seats, fraction_numerator
    )

    lines = []
    if credit >= 50:
        lines.append(
            _build_line(
                subscription, "credit", credit, subscription["plan_name"], period_end
            )
        )
    if charge >= 50:
        lines.append(
            _build_line(subscription, "charge", charge, new_plan["name"], period_end)
        )
    return lines
