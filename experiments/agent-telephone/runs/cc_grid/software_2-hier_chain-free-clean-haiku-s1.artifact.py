# Open items for client or tech lead (not blocking):
# 1. Proration uses exact fractional time (microseconds), not whole days.
# 2. Threshold and minimum are applied to net amounts (before VAT).
# 3. Charge VAT rounds down (floor), not half-up.
# 4. Equal-price case returns [] (no price change, nothing to prorate).
# 5. Statuses other than "active" and "trialing" raise ValueError.
# 6. changed_at after period_end raises ValueError.
# 7. Dates are taken in UTC.
# 8. Approvers are identified by name only; no IDs were provided.
# 9. All subscriptions are assumed EUR when no currency key is present.
# 10. The same billable_seats value is used on both the old and new side.

import unicodedata
from datetime import datetime, timedelta, timezone

__all__ = ["prorate_seats"]

PERIOD_US = 30 * 86400 * 1000000
MIN_LINE_CENTS = 50
APPROVAL_THRESHOLD_CENTS = 50000
VAT_PERCENT = 21
MAX_DESC_LEN = 80
ELLIPSIS = "..."
FINANCE_CONTROLLER = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
OTHER_APPROVER = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")
_ONE_US = timedelta(microseconds=1)


def _require(mapping, key):
    try:
        return mapping[key]
    except KeyError:
        raise ValueError(f"missing required key: {key}") from None


def _cents(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an int")
    if value < 0:
        raise ValueError(f"{label} must be non-negative")
    return value


def _aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value


def _name(value, label):
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a str")
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{label} must not be empty")
    return stripped


def _describe(prefix, name, middle, date_str):
    full = f"{prefix}{name}{middle}{date_str}"
    if len(full) <= MAX_DESC_LEN:
        return full
    fixed = len(prefix) + len(middle) + len(date_str) + len(ELLIPSIS)
    keep = MAX_DESC_LEN - fixed
    kept = name[:keep].rstrip() if keep > 0 else ""
    if not kept:
        raise ValueError("plan name cannot be shortened to a usable length")
    return f"{prefix}{kept}{ELLIPSIS}{middle}{date_str}"


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise TypeError("subscription and new_plan must be dicts")

    # Input validation
    _aware(changed_at, "changed_at")
    if "currency" in subscription and subscription["currency"] != "EUR":
        raise ValueError("only EUR subscriptions are supported")
    subscription_id = _require(subscription, "id")
    status = _require(subscription, "status")
    period_end = _aware(_require(subscription, "period_end"), "period_end")
    old_price = _cents(_require(subscription, "seat_price_cents"), "seat_price_cents")
    billable = _cents(_require(subscription, "billable_seats"), "billable_seats")
    new_price = _cents(_require(new_plan, "seat_price_cents"), "new seat_price_cents")
    new_name_raw = _require(new_plan, "name")
    old_name_raw = _require(subscription, "plan_name")
    vat_id = subscription.get("vat_id")
    reverse_charge = isinstance(vat_id, str) and vat_id.strip() != ""

    # Status and timing checks
    if not isinstance(status, str):
        raise ValueError("status must be a str")
    if status == "trialing":
        return []
    if status != "active":
        raise ValueError(f"unsupported subscription status: {status!r}")
    if changed_at == period_end:
        return []
    if changed_at > period_end:
        raise ValueError("changed_at is after period_end")
    if new_price <= old_price:
        return []

    old_name = _name(old_name_raw, "plan_name")
    new_name = _name(new_name_raw, "new plan name")

    # Integer-only proration
    remaining_us = (period_end - changed_at) // _ONE_US
    credit_num = old_price * billable * remaining_us
    credit = (credit_num + PERIOD_US - 1) // PERIOD_US
    charge = (new_price * billable * remaining_us) // PERIOD_US

    date_str = period_end.astimezone(timezone.utc).strftime("%Y-%m-%d")
    lines = []

    if credit >= MIN_LINE_CENTS:
        approver = FINANCE_CONTROLLER if credit <= APPROVAL_THRESHOLD_CENTS else OTHER_APPROVER
        lines.append({
            "subscription_id": subscription_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit: ", old_name, " unused to ", date_str),
            "approved_by": approver,
        })

    if charge >= MIN_LINE_CENTS:
        vat_cents = 0 if reverse_charge else charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": subscription_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat_cents,
            "description": _describe("Charge: ", new_name, " until ", date_str),
            "approved_by": None,
        })

    return lines