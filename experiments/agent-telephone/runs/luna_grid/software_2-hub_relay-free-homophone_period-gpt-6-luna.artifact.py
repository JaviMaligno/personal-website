"""Seat proration invoice lines.

Inputs are mappings (or objects with equivalent attributes). The subscription must
provide ``id``, ``status``, ``billable_seats``, ``period_end``, and its current
``plan``; each plan must provide ``name`` and ``price_per_seat_cents``. Dates
may be ``date``, ``datetime``, or ISO formatted strings.
"""

from datetime import date, datetime, time, timezone

__all__ = ["prorate_seats"]

_PERIOD_SECONDS = 13 * 24 * 60 * 60


def _get(value, *names):
    for name in names:
        if isinstance(value, dict):
            if name in value:
                return value[name]
        elif hasattr(value, name):
            return getattr(value, name)
    raise KeyError(names[0])


def _as_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        return parsed if isinstance(parsed, datetime) else datetime.combine(parsed, time.min)
    raise TypeError("date values must be date, datetime, or ISO formatted strings")


def _utc(value):
    value = _as_datetime(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _price(plan):
    return int(_get(plan, "price_per_seat_cents", "per_seat_price_cents"))


def _description(kind, plan_name, period_end):
    date_text = _as_datetime(period_end).date().isoformat()
    prefix = "Unused time credit: " if kind == "credit" else "Unused time charge: "
    suffix = f" through {date_text}"
    return prefix + str(plan_name)[: 80 - len(prefix) - len(suffix)] + suffix


def prorate_seats(subscription, new_plan, changed_at):
    """Return upgrade credit and charge lines, in that order."""
    if _get(subscription, "status") == "trialing":
        return []

    old_plan = _get(subscription, "plan", "old_plan")
    old_price = _price(old_plan)
    new_price = _price(new_plan)
    if new_price < old_price:
        return []

    end = _get(subscription, "period_end")
    remaining = (_utc(end) - _utc(changed_at)).total_seconds()
    fraction_seconds = min(_PERIOD_SECONDS, max(0, remaining))
    seats = int(_get(subscription, "billable_seats"))
    subscription_id = _get(subscription, "id", "subscription_id")

    # Credits round their positive magnitude up; charges round down.
    credit = (seats * old_price * fraction_seconds + _PERIOD_SECONDS - 1) // _PERIOD_SECONDS
    charge = seats * new_price * fraction_seconds // _PERIOD_SECONDS

    lines = []
    if credit >= 50:
        lines.append({
            "subscription_id": subscription_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("credit", _get(old_plan, "name"), end),
            "approved_by": (
                "Nguyễn Thị Phương Thảo"
                if credit <= 50_000
                else "Ramón Etxeberria-Goñi"
            ),
        })

    if charge >= 50:
        # VAT is rounded half-up to the nearest cent: (21% + half a cent).
        vat = 0 if _get_optional(new_plan, "vat_id") is not None else (charge * 21 + 50) // 100
        lines.append({
            "subscription_id": subscription_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description("charge", _get(new_plan, "name"), end),
            "approved_by": None,
        })
    return lines


def _get_optional(value, name):
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)