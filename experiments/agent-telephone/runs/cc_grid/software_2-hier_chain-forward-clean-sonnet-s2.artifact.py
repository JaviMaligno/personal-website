"""Seat upgrade proration.

Assumptions and flags:
- Partial unused days round down to whole days (not run against tests; no tools were available).
- Unused days are clamped to [0, 30]. If changed_at >= period_end, no lines are returned.
- Equal price is treated as not an upgrade, so no lines are returned.
- Each line is skipped independently if its amount is under 50 cents, so a lone line may be returned.
- VAT on a charge is floor(amount * 21 / 100). Credits carry no VAT.
  This follows the client brief, which overrides the house rule that credits carry VAT.
- Credits round up and charges round down per the brief, which overrides the house half-up rule.
- The period_end date is taken in period_end's own timezone.
- Description length is counted in code points, with the plan name NFC-normalized.
- Only the plan name is truncated. A "…" is added if there is room.
- Credit lines use the old plan name and charge lines use the new plan name.
- Tests were not written or run, because no execution tools were available.
"""
import unicodedata
from datetime import datetime, timedelta

_CTRL = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
_CTRL_BIG = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")
_MIN_CENTS = 50
_MAX_DESC = 80
_VAT_PCT = 21


def _int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    return value


def _aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _describe(prefix, plan, date_str):
    plan = unicodedata.normalize("NFC", str(plan))
    suffix = f" seats until {date_str}"
    budget = _MAX_DESC - len(prefix) - len(suffix)
    if len(plan) > budget:
        budget = max(budget, 0)
        plan = plan[: budget - 1] + "…" if budget >= 1 else ""
    return f"{prefix}{plan}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    old_price = _int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _int(new_plan["seat_price_cents"], "new seat_price_cents")
    seats = _int(subscription["billable_seats"], "billable_seats")
    period_end = _aware(subscription["period_end"], "period_end")
    changed_at = _aware(changed_at, "changed_at")

    if subscription.get("status") == "trialing":
        return []
    if new_price <= old_price or seats <= 0:
        return []

    total_seconds = (period_end - changed_at) // timedelta(seconds=1)
    unused = max(0, min(30, total_seconds // 86400))
    if unused == 0:
        return []

    sub_id = subscription["id"]
    date_str = period_end.date().isoformat()
    lines = []

    credit = -(-(old_price * seats * unused) // 30)
    if credit >= _MIN_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit unused ", subscription["plan_name"], date_str),
            "approved_by": _CTRL_BIG if credit > 50000 else _CTRL,
        })

    charge = (new_price * seats * unused) // 30
    if charge >= _MIN_CENTS:
        vat_id = subscription.get("vat_id")
        reverse = isinstance(vat_id, str) and bool(vat_id.strip())
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else (charge * _VAT_PCT) // 100,
            "description": _describe("Charge unused ", new_plan["name"], date_str),
            "approved_by": None,
        })

    return lines