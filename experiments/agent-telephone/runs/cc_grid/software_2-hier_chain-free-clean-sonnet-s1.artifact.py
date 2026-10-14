# Not executed: no tools were available, so this module was not run and test_seat_proration.py was not written.
"""Seat proration for Fernhollow Studios billing (EUR, integer math only)."""

import unicodedata
from datetime import datetime, timezone

PERIOD_DAYS = 30
MAX_DESCRIPTION_LEN = 80
MIN_LINE_CENTS = 50
APPROVAL_THRESHOLD_CENTS = 50000
VAT_PERCENT = 21

APPROVER_DEFAULT = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
APPROVER_HIGH = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "billable_seats", "period_end")


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _check_aware(v, name):
    if not isinstance(v, datetime):
        raise TypeError(f"{name} must be a datetime")
    if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
        raise ValueError(f"{name} must be timezone-aware")


def _validate(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict):
        raise TypeError("subscription must be a dict")
    if not isinstance(new_plan, dict):
        raise TypeError("new_plan must be a dict")
    for k in _SUB_KEYS:
        if k not in subscription:
            raise ValueError(f"subscription missing key: {k}")
    for k in ("name", "seat_price_cents"):
        if k not in new_plan:
            raise ValueError(f"new_plan missing key: {k}")
    if subscription["id"] is None:
        raise ValueError("id required")
    if not isinstance(subscription["status"], str):
        raise TypeError("status must be a str")
    for v, n in ((subscription["plan_name"], "plan_name"), (new_plan["name"], "new_plan name")):
        if not isinstance(v, str):
            raise TypeError(f"{n} must be a str")
        if not v:
            raise ValueError(f"{n} must be non-empty")
    for v, n in (
        (subscription["seat_price_cents"], "seat_price_cents"),
        (new_plan["seat_price_cents"], "new_plan seat_price_cents"),
        (subscription["billable_seats"], "billable_seats"),
    ):
        if not _is_int(v):
            raise TypeError(f"{n} must be an int")
        if v < 0:
            raise ValueError(f"{n} must be >= 0")
    vat_id = subscription.get("vat_id")
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be a str or None")
    _check_aware(subscription["period_end"], "period_end")
    _check_aware(changed_at, "changed_at")


def _description(verb, plan_name, end_date):
    prefix = f"{verb} unused "
    suffix = f" seats, period ends {end_date.isoformat()}"
    room = MAX_DESCRIPTION_LEN - len(prefix) - len(suffix)
    name = unicodedata.normalize("NFC", plan_name)
    if len(name) > room:
        if room >= 4:
            name = name[: room - 3].rstrip() + "..."
        elif room > 0:
            name = name[:room]
        else:
            name = ""
    text = unicodedata.normalize("NFC", prefix + name + suffix)
    return text


def prorate_seats(subscription, new_plan, changed_at):
    """Return [credit, charge] lines (either may be omitted) for a mid-period upgrade.

    Assumptions: any status other than "trialing" is prorated; equal or lower
    new price yields []; days_left uses UTC calendar dates, whole days only,
    capped at 30; lines under 50 net cents are skipped independently.
    """
    _validate(subscription, new_plan, changed_at)

    if subscription["status"].strip().lower() == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    seats = subscription["billable_seats"]
    if new_price <= old_price or seats == 0:
        return []

    end_date = subscription["period_end"].astimezone(timezone.utc).date()
    start_date = changed_at.astimezone(timezone.utc).date()
    days_left = (end_date - start_date).days
    if days_left <= 0:
        return []
    days_left = min(days_left, PERIOD_DAYS)

    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)
    charge = (new_price * seats * days_left) // PERIOD_DAYS

    vat_id = subscription.get("vat_id")
    reverse_charge = isinstance(vat_id, str) and vat_id.strip() != ""
    sub_id = subscription["id"]
    lines = []

    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit", subscription["plan_name"], end_date),
            "approved_by": APPROVER_HIGH if credit > APPROVAL_THRESHOLD_CENTS else APPROVER_DEFAULT,
        })
    if charge >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse_charge else (charge * VAT_PERCENT) // 100,
            "description": _description("Charge", new_plan["name"], end_date),
            "approved_by": None,
        })
    return lines