"""prorate_seats.py - seat upgrade proration for Fernhollow Studios.

Design decisions and ambiguities (flagged for the client):
- Days left: no day rounding. The fraction is whole remaining seconds / (30*86400),
  using integer math only. Microseconds are dropped (floored), and the remaining
  time is clamped to [0, 30 days].
- changed_at at or after period_end returns [].
- VAT: charge VAT = floor(net*21/100), in the customer's favour. A truthy string
  vat_id gives 0 VAT. The house rule "VAT applies to credits too" conflicts with R9
  (credit VAT is always 0). The explicit requirement R9 wins, so credits carry
  vat_cents = 0.
- Rounding: the house rule "half-up" conflicts with R7. R7 wins: credit is ceiling,
  charge is floor.
- R8 is judged on the net amount, before VAT, for each line independently.
- Statuses other than "trialing" (e.g. "canceled", "past_due") are processed normally.
- Equal price is not a downgrade, so the credit and charge lines are both produced
  (subject to R8).
- Zero billable_seats gives amounts of 0, which R8 omits, so the result is [].
- Inputs are validated before the trialing and downgrade checks. A bool, a non-int
  or a negative value raises TypeError or ValueError. A naive datetime raises ValueError.
- legacy_discount is ignored.
- NOT DONE: the pytest file test_prorate_seats.py was not produced and no tests were
  run. This reply was restricted to a single module and no tools were available.
"""
from datetime import datetime

PERIOD_SECONDS = 30 * 86400
MAX_DESC = 80
LOW_APPROVER = "Win Tee Fung Tao"
HIGH_APPROVER = "Ramón Etxeberria-Goñi"


def _int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _describe(verb, plan, date_str):
    prefix = f"{verb} unused "
    suffix = f" until {date_str}"
    room = MAX_DESC - len(prefix) - len(suffix)
    name = str(plan)
    if len(name) > room:
        if room >= 3:
            name = name[: room - 3] + "..."
        else:
            name = name[: max(room, 0)]
    return prefix + name + suffix


def prorate_seats(subscription, new_plan, changed_at):
    old_price = _int(subscription["seat_price_cents"], "seat_price_cents")
    _int(subscription["seats"], "seats")
    seats = _int(subscription["billable_seats"], "billable_seats")
    new_price = _int(new_plan["seat_price_cents"], "new seat_price_cents")
    period_end = _aware(subscription["period_end"], "period_end")
    _aware(changed_at, "changed_at")

    if subscription["status"] == "trialing":
        return []
    if new_price < old_price:
        return []

    delta = period_end - changed_at
    remaining = delta.days * 86400 + delta.seconds
    if remaining <= 0:
        return []
    remaining = min(remaining, PERIOD_SECONDS)

    credit = -(-(old_price * seats * remaining) // PERIOD_SECONDS)
    charge = (new_price * seats * remaining) // PERIOD_SECONDS

    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    vat_id = subscription.get("vat_id")
    exempt = isinstance(vat_id, str) and bool(vat_id.strip())

    lines = []
    if credit >= 50:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit", subscription["plan_name"], date_str),
            "approved_by": HIGH_APPROVER if credit > 50000 else LOW_APPROVER,
        })
    if charge >= 50:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if exempt else (charge * 21) // 100,
            "description": _describe("Charge", new_plan["name"], date_str),
            "approved_by": None,
        })
    return lines