"""Fernhollow Studios seat proration.

Public API: prorate_seats(subscription, new_plan, changed_at) -> list[dict].

NOTE: no tools were available when this was written, so the file was not saved
and the tests (test_seat_proration.py) were not written or run.

Conventions chosen for the ambiguities in the requirements:
- Each line is a dict with exactly: subscription_id, kind, amount_cents,
  vat_cents, description, approved_by. Credit line first, then charge line.
- amount_cents is always a positive int magnitude; "kind" carries the direction.
- All arithmetic is integer-only (no /, float or Decimal).
- days_left = whole elapsed days, floored (partial days dropped), computed from
  the aware-datetime difference (no timezone conversion), clamped to 0..13.
  A period is always 13 days. elapsed <= 0 gives [].
- Credit = ceil(old_price * seats * days_left / 13); charge = floor(same, new price).
- Skip rule: a line is judged alone on its pre-VAT amount; < 50 is dropped, 50 kept.
- Status "trialing" returns []. Other statuses (canceled, past_due, ...) are
  treated like active because only "trialing" is named.
- Downgrade (new price < old price) returns []. Equal price is NOT a downgrade
  and proceeds; there rounding makes credit >= charge by up to one cent, which
  is the intended no-company-favour behaviour.
- Billing uses billable_seats; "seats" and "legacy_discount" are ignored.
- VAT: credits always 0 (the explicit requirement overrides the generic house
  rule that VAT applies to credits). Charge VAT = amount * 21 // 100 (rounded
  down), 0 if vat_id is truthy and not whitespace-only (reverse charge). The
  explicit floor/ceil rounding likewise overrides the generic half-up rule.
- approved_by on credits: THAO, or RAMON if amount_cents > 50000 (strictly).
  None on charges.
- Descriptions are at most 80 chars; only the plan name is shortened (ending in
  "..."), the date (period_end's own timezone, ISO YYYY-MM-DD) is never cut.
  If the budget is under 3 chars the plan name shrinks to what fits (possibly
  empty); this cannot happen with the current template.
- Validation: ValueError for naive datetimes and for non-int, bool or negative
  cents/seat values; KeyError naming the missing key for missing keys.
"""
from datetime import datetime, timedelta

# Approvers, NFC, written with \u escapes so the source is encoding-proof.
APPROVER_DEFAULT = "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"
APPROVER_LARGE = "Ram\u00f3n Etxeberria-Go\u00f1i"

_PERIOD_DAYS = 13
_MIN_LINE_CENTS = 50
_LARGE_CREDIT_CENTS = 50000
_MAX_DESC = 80
_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def _require(d, keys, label):
    for k in keys:
        if k not in d:
            raise KeyError(f"missing key {k!r} in {label}")


def _check_int(v, name):
    # bool is a subclass of int, so test the exact type.
    if type(v) is not int or v < 0:
        raise ValueError(f"{name} must be a non-negative int, got {v!r}")


def _check_aware(dt, name):
    if (not isinstance(dt, datetime) or dt.tzinfo is None
            or dt.utcoffset() is None):
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _describe(verb, plan, date_str):
    """Build '<verb> unused <plan> seats until <date>' within 80 chars."""
    prefix, suffix = f"{verb} unused ", f" seats until {date_str}"
    budget = _MAX_DESC - len(prefix) - len(suffix)
    if len(plan) > budget:
        plan = plan[:budget - 3] + "..." if budget >= 3 else "..."[:max(budget, 0)]
    return prefix + plan + suffix


def prorate_seats(subscription, new_plan, changed_at):
    _require(subscription, _SUB_KEYS, "subscription")
    _require(new_plan, _PLAN_KEYS, "new_plan")
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    seats = subscription["billable_seats"]
    _check_int(old_price, "subscription.seat_price_cents")
    _check_int(new_price, "new_plan.seat_price_cents")
    _check_int(seats, "subscription.billable_seats")
    _check_aware(changed_at, "changed_at")
    period_end = subscription["period_end"]
    _check_aware(period_end, "period_end")

    if subscription["status"] == "trialing":
        return []
    if new_price < old_price:  # downgrade; equal price proceeds
        return []
    if seats == 0:
        return []

    elapsed = period_end - changed_at
    if elapsed <= timedelta(0):
        return []
    days_left = min(elapsed // timedelta(days=1), _PERIOD_DAYS)

    credit = -(-(old_price * seats * days_left) // _PERIOD_DAYS)  # ceil
    charge = (new_price * seats * days_left) // _PERIOD_DAYS      # floor

    date_str = f"{period_end.year:04d}-{period_end.month:02d}-{period_end.day:02d}"
    sub_id = subscription["id"]
    lines = []

    if credit >= _MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit", subscription["plan_name"], date_str),
            "approved_by": APPROVER_LARGE if credit > _LARGE_CREDIT_CENTS
            else APPROVER_DEFAULT,
        })

    if charge >= _MIN_LINE_CENTS:
        vat_id = subscription["vat_id"]
        reverse = bool(vat_id) and bool(str(vat_id).strip())
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else (charge * 21) // 100,
            "description": _describe("Charge", new_plan["name"], date_str),
            "approved_by": None,
        })

    return lines