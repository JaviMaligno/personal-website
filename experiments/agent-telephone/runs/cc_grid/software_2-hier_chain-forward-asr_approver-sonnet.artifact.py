# Written without file or test access: this module has not been run, and test_prorate.py was not created.
# Decisions:
# - Brief overrides house rules: credits carry no VAT, and credits round up while charges round down.
# - VAT on a charge is floor(charge*21/100), as specified in the design guidance.
from datetime import datetime

_PERIOD_DAYS = 30
_MIN_LINE_CENTS = 50
_BIG_CREDIT_CENTS = 50000
_MAX_DESC = 80
_VAT_PERCENT = 21
_CREDIT_APPROVER = "Win Tee Fung Tao"
_BIG_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def _floor_div(a: int, b: int) -> int:
    return a // b


def _check_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an int (not bool/float), got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{label} must be non-negative, got {value}")


def _check_dt(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime, got {type(value).__name__}")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _validate(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict):
        raise TypeError("subscription must be a dict")
    if not isinstance(new_plan, dict):
        raise TypeError("new_plan must be a dict")
    sid = subscription.get("id")
    if sid is None or sid == "":
        raise ValueError("subscription id is required")
    if not isinstance(subscription.get("plan_name"), str):
        raise TypeError("subscription plan_name must be a str")
    if not isinstance(new_plan.get("name"), str):
        raise TypeError("new_plan name must be a str")
    _check_int(subscription.get("seat_price_cents"), "subscription seat_price_cents")
    _check_int(new_plan.get("seat_price_cents"), "new_plan seat_price_cents")
    _check_int(subscription.get("billable_seats"), "subscription billable_seats")
    _check_dt(subscription.get("period_end"), "period_end")
    _check_dt(changed_at, "changed_at")


def _days_left(period_end: datetime, changed_at: datetime) -> int:
    delta = period_end - changed_at
    secs = delta.days * 86400 + delta.seconds  # integer math, floor to whole days
    days = secs // 86400
    return max(0, min(_PERIOD_DAYS, days))


def _describe(kind: str, name: str, period_end: datetime) -> str:
    date = period_end.isoformat()[:10]
    head = "Credit:" if kind == "credit" else "Charge:"
    tail = f"unused seats to {date}" if kind == "credit" else f"seats to {date}"
    name = name.strip()
    if name:
        full = f"{head} {name} - {tail}"
        if len(full) <= _MAX_DESC:
            return full
        budget = _MAX_DESC - len(f"{head}  - {tail}") - 1  # 1 for the ellipsis
        if budget >= 1:
            cut = name[:budget].rstrip()
            return f"{head} {cut}… - {tail}"
    return f"{head} {tail}"


def prorate_seats(subscription: dict, new_plan: dict, changed_at: datetime) -> list[dict]:
    _validate(subscription, new_plan, changed_at)
    if subscription.get("status") == "trialing":
        return []
    old = subscription["seat_price_cents"]
    new = new_plan["seat_price_cents"]
    if new <= old:  # downgrade applies at renewal; equal price is a no-op
        return []
    period_end = subscription["period_end"]
    days = _days_left(period_end, changed_at)
    if days == 0:
        return []
    seats = subscription["billable_seats"]
    sid = subscription["id"]
    lines = []

    credit = _ceil_div(old * seats * days, _PERIOD_DAYS)
    if credit >= _MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sid,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("credit", subscription["plan_name"], period_end),
            "approved_by": _BIG_CREDIT_APPROVER if credit > _BIG_CREDIT_CENTS else _CREDIT_APPROVER,
        })

    charge = _floor_div(new * seats * days, _PERIOD_DAYS)
    if charge >= _MIN_LINE_CENTS:
        vat = 0 if subscription.get("vat_id") else _floor_div(charge * _VAT_PERCENT, 100)
        lines.append({
            "subscription_id": sid,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe("charge", new_plan["name"], period_end),
            "approved_by": None,
        })
    return lines