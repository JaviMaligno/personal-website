"""Seat upgrade proration.

Assumptions (documented per the architect's note):
- Check order: trialing -> []; downgrade (new price < old price) -> []; billable_seats <= 0 -> [];
  days_left == 0 -> [].
- Equal price is allowed: credit and charge are computed and come out equal
  (before the VAT line and the 50-cent skip rule).
- Only billable_seats is used, never seats. legacy_discount is ignored.
- days_left = floor((period_end - changed_at) / 1 day) on aware datetimes, clamped to 0..30.
- Credit = ceil(old_price * seats * days / 30); charge = floor(new_price * seats * days / 30).
  Integer math only.
- Each line under 50 cents is skipped independently (a skipped credit does not skip the charge).
- Charge VAT = 21% rounded DOWN (charge * 21 // 100). This is an assumption: the brief does not
  state VAT rounding, and the architect chose down. The house default of half-up is overridden.
  A truthy vat_id means reverse charge, so VAT is 0. A None or empty vat_id means VAT applies.
  Credits always have vat_cents = 0 (per the brief).
- Credit approver is "Win Tee Fung Tao"; strictly above 50000 cents it is "Ramón Etxeberria-Goñi".
  Charges have approved_by None.
- Descriptions are "Credit unused {plan} until YYYY-MM-DD" and "Charge {plan} until YYYY-MM-DD",
  at most 80 characters. Only the plan name is truncated, with a trailing ellipsis inside the
  budget. The date is period_end.date() in period_end's own tzinfo. If no room is left for the
  name, it is dropped.
- Amounts are EUR cents.

Note: tests (test_prorate_seats.py) were not created or run, because this agent has no tools.
"""
from datetime import timedelta

MAX_DESC = 80
MIN_LINE_CENTS = 50
PERIOD_DAYS = 30
VAT_PERCENT = 21
CREDIT_APPROVER = "Win Tee Fung Tao"
BIG_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
BIG_CREDIT_THRESHOLD = 50000


def _description(prefix: str, plan: str, date_str: str) -> str:
    suffix = f" until {date_str}"
    budget = MAX_DESC - len(prefix) - len(suffix) - 1  # 1 for the space before plan
    if len(plan) <= budget:
        name = plan
    elif budget >= 2:
        name = plan[: budget - 1].rstrip() + "\u2026"
    elif budget == 1:
        name = "\u2026"
    else:
        name = ""
    if not name:
        return f"{prefix}{suffix}"
    return f"{prefix} {name}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    if subscription.get("status") == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    seats = subscription.get("billable_seats")
    if not seats or seats <= 0:
        return []

    period_end = subscription["period_end"]
    days = (period_end - changed_at) // timedelta(days=1)
    days = max(0, min(PERIOD_DAYS, days))
    if days == 0:
        return []

    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * days) // PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit unused", subscription["plan_name"], date_str),
            "approved_by": BIG_CREDIT_APPROVER if credit > BIG_CREDIT_THRESHOLD else CREDIT_APPROVER,
        })

    charge = (new_price * seats * days) // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        vat = 0 if subscription.get("vat_id") else charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description("Charge", new_plan["name"], date_str),
            "approved_by": None,
        })

    return lines