# -*- coding: utf-8 -*-
"""Seat upgrade proration for Fernhollow Studios (EUR, integer cents, stdlib only).

Assumptions:
- Early exits return []: trialing, downgrade (new price < old price), same plan
  name and price, billable_seats missing/None/0, days_left <= 0. Other statuses
  are treated as active. Only billable_seats is used, never seats. A negative
  billable_seats raises ValueError. legacy_discount is ignored.
- days_left is the calendar-date difference in period_end's tzinfo, clamped to 13.
- credit = ceil(old*seats*days/13), charge = floor(new*seats*days/13), using
  integer math only. Each line is skipped independently if its amount < 50 cents.
- Credits carry vat_cents 0. Charges carry floor(amount*21/100), or 0 when
  vat_id is a non-blank string (reverse charge).
- Credit approver is APPROVER_DEFAULT, or APPROVER_SENIOR when the credit is
  strictly above 50000 cents. Charges have approved_by None.
- Descriptions are at most 80 code points (NFC); only the plan name is shortened
  with a trailing ellipsis, and the date is always kept.
- Explicit design decisions here (ceil/floor rounding, no VAT on credits) take
  precedence over the generic house defaults (half-up rounding, VAT on credits).
- Note: the tooling available for this task could not create files or run
  tests, so no separate test module was run or created.
"""
import unicodedata
from datetime import datetime

APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
APPROVER_SENIOR = "Ramón Etxeberria-Goñi"

PERIOD_DAYS = 13
MIN_LINE_CENTS = 50
APPROVAL_LIMIT_CENTS = 50000
VAT_PERCENT = 21
MAX_DESC = 80
ELLIPSIS = "\u2026"


def _check_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an int")
    return value


def _check_aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _description(verb, name, date_str):
    prefix = f"{verb} unused "
    suffix = f" until {date_str}"
    fallback = f"{prefix}plan{suffix}"
    if not isinstance(name, str):
        return fallback
    name = unicodedata.normalize("NFC", name).strip()
    if not name:
        return fallback
    full = f"{prefix}{name}{suffix}"
    if len(full) <= MAX_DESC:
        return full
    avail = MAX_DESC - len(prefix) - len(suffix) - len(ELLIPSIS)
    if avail < 1:
        return fallback
    cut = name[:avail].rstrip()
    while cut and unicodedata.combining(cut[-1]):
        cut = cut[:-1]
    cut = cut.rstrip()
    if not cut:
        return fallback
    return f"{prefix}{cut}{ELLIPSIS}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription["period_end"]
    _check_aware(changed_at, "changed_at")
    _check_aware(period_end, "period_end")

    old_price = _check_int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _check_int(new_plan["seat_price_cents"], "new seat_price_cents")
    if "seats" in subscription and subscription["seats"] is not None:
        _check_int(subscription["seats"], "seats")
    seats = subscription.get("billable_seats")
    if seats is not None:
        _check_int(seats, "billable_seats")
        if seats < 0:
            raise ValueError("billable_seats must not be negative")

    if subscription.get("status") == "trialing":
        return []
    if new_price < old_price:
        return []
    old_name = subscription.get("plan_name")
    new_name = new_plan.get("name")
    if old_name == new_name and old_price == new_price:
        return []
    if not seats:
        return []

    tz = period_end.tzinfo
    end_date = period_end.date()
    days_left = (end_date - changed_at.astimezone(tz).date()).days
    if days_left <= 0:
        return []
    days_left = min(days_left, PERIOD_DAYS)

    base_old = old_price * seats * days_left
    base_new = new_price * seats * days_left
    credit = -(-base_old // PERIOD_DAYS)
    charge = base_new // PERIOD_DAYS

    date_str = end_date.isoformat()
    sub_id = subscription.get("id")
    lines = []

    if credit >= MIN_LINE_CENTS:
        approver = APPROVER_SENIOR if credit > APPROVAL_LIMIT_CENTS else APPROVER_DEFAULT
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit", old_name, date_str),
            "approved_by": approver,
        })

    if charge >= MIN_LINE_CENTS:
        vat_id = subscription.get("vat_id")
        reverse = isinstance(vat_id, str) and vat_id.strip() != ""
        vat = 0 if reverse else (charge * VAT_PERCENT) // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description("Charge", new_name, date_str),
            "approved_by": None,
        })

    return lines