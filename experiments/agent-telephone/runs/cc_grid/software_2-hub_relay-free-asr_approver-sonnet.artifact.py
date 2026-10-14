"""Fernhollow Studios mid-period plan change proration (integer arithmetic only).

Assumptions (unconfirmed with the client):
- Days left is the calendar-date difference, in period_end's timezone, between
  changed_at and period_end, clamped to 0..30 (period is always 30 days).
- VAT (21%) is rounded down.
- Credit and charge amounts are positive ints; "kind" carries the meaning.
- amount_cents is net of VAT.
- The 50-cent drop threshold and the 50,000-cent approver threshold apply to
  the net amount.

Note: no pytest file was produced and no tests were run in this delivery.
"""
from datetime import datetime

CREDIT_APPROVER = "Win Tee Fung Tao"
HIGH_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
HIGH_CREDIT_THRESHOLD_CENTS = 50_000
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
PERIOD_DAYS = 30
MAX_DESCRIPTION = 80


def _int(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"invalid {name}")
    return value


def _aware(value, name):
    if (not isinstance(value, datetime) or value.tzinfo is None
            or value.utcoffset() is None):
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value


def _describe(template, name, date_str):
    """template contains {name} and {date}; shorten name so total <= 80."""
    fixed = len(template.format(name="", date=date_str))
    budget = MAX_DESCRIPTION - fixed
    if len(name) > budget:
        name = name[:max(budget - 1, 0)] + "…" if budget > 0 else ""
    return template.format(name=name, date=date_str)


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise ValueError("subscription and new_plan must be dicts")
    try:
        sub_id = subscription["id"]
        status = subscription["status"]
        old_name = subscription["plan_name"]
        old_price = subscription["seat_price_cents"]
        billable = subscription["billable_seats"]
        period_end = subscription["period_end"]
        new_name = new_plan["name"]
        new_price = new_plan["seat_price_cents"]
    except KeyError as exc:
        raise ValueError(f"missing field: {exc.args[0]}") from None
    if sub_id is None:
        raise ValueError("invalid id")
    if not isinstance(status, str):
        raise ValueError("invalid status")
    if not isinstance(old_name, str) or not isinstance(new_name, str):
        raise ValueError("invalid plan name")
    _int(old_price, "seat_price_cents")
    _int(new_price, "new seat_price_cents")
    _int(billable, "billable_seats")
    _aware(period_end, "period_end")
    _aware(changed_at, "changed_at")
    vat_id = subscription.get("vat_id")

    if status == "trialing" or billable == 0:
        return []
    days_left = (period_end.date()
                 - changed_at.astimezone(period_end.tzinfo).date()).days
    days_left = max(0, min(PERIOD_DAYS, days_left))
    if days_left == 0:
        return []
    if new_price < old_price:
        return []

    date_str = period_end.strftime("%Y-%m-%d")
    credit = -(-(old_price * billable * days_left) // PERIOD_DAYS)
    charge = (new_price * billable * days_left) // PERIOD_DAYS

    lines = []
    if credit >= MIN_LINE_CENTS:
        approver = (HIGH_CREDIT_APPROVER
                    if credit > HIGH_CREDIT_THRESHOLD_CENTS else CREDIT_APPROVER)
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit {name} until {date}",
                                     old_name, date_str),
            "approved_by": approver,
        })
    if charge >= MIN_LINE_CENTS:
        vat = 0 if vat_id else charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe("Charge {name} until {date}",
                                     new_name, date_str),
            "approved_by": None,
        })
    return lines