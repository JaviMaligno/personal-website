"""prorate.py - seat upgrade proration for Fernhollow Studios. All money is int cents.

Assumptions:
- Equal price is treated like a downgrade: returns [].
- days_left: changed_at is converted to period_end's timezone, then calendar
  dates are subtracted, clamped to 0..30.
- Credit uses ceil, charge uses floor. Lines under 50 cents net are dropped.
- Charge VAT is 21% floored, or 0 with a non-blank vat_id (reverse charge).
- Credit VAT is always 0. This follows the explicit instruction and overrides
  the house rule that VAT applies to credits.
- Every status other than "trialing" is prorated.
- The 80 limit counts characters (code points), not bytes.
- Tests below were written but not executed here (no tools available).
  Run with: pytest prorate.py
"""
from datetime import datetime, timedelta, timezone

CREDIT_TEMPLATE = "Credit for unused {plan} plan, period ends {date}"
CHARGE_TEMPLATE = "Charge for unused {plan} plan, period ends {date}"
MAX_DESCRIPTION = 80
PERIOD_DAYS = 30
MIN_AMOUNT_CENTS = 50
VAT_PERCENT = 21
APPROVER = "Win Tee Fung Tao"
SENIOR_APPROVER = "Ramón Etxeberria-Goñi"
SENIOR_THRESHOLD_CENTS = 50000


def _check_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _check_aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _describe(template, plan, date_str):
    plan = str(plan)
    room = MAX_DESCRIPTION - len(template.format(plan="", date=date_str))
    if len(plan) > room:
        plan = plan[:room - 3] + "..." if room >= 3 else "..."[:max(room, 0)]
    return template.format(plan=plan, date=date_str)


def prorate_seats(subscription, new_plan, changed_at):
    old_price = _check_int(subscription["seat_price_cents"], "seat_price_cents")
    seats = _check_int(subscription["billable_seats"], "billable_seats")
    new_price = _check_int(new_plan["seat_price_cents"], "new seat_price_cents")
    period_end = subscription["period_end"]
    _check_aware(period_end, "period_end")
    _check_aware(changed_at, "changed_at")

    if subscription.get("status") == "trialing":
        return []
    if new_price <= old_price:
        return []

    local_change = changed_at.astimezone(period_end.tzinfo)
    days_left = (period_end.date() - local_change.date()).days
    days_left = max(0, min(PERIOD_DAYS, days_left))

    credit = (old_price * seats * days_left + PERIOD_DAYS - 1) // PERIOD_DAYS
    charge = (new_price * seats * days_left) // PERIOD_DAYS

    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    vat_id = subscription.get("vat_id")
    reverse = isinstance(vat_id, str) and vat_id.strip() != ""
    lines = []

    if credit >= MIN_AMOUNT_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe(CREDIT_TEMPLATE, subscription.get("plan_name", ""), date_str),
            "approved_by": SENIOR_APPROVER if credit > SENIOR_THRESHOLD_CENTS else APPROVER,
        })
    if charge >= MIN_AMOUNT_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * VAT_PERCENT // 100,
            "description": _describe(CHARGE_TEMPLATE, new_plan.get("name", ""), date_str),
            "approved_by": None,
        })
    return lines


# ---------------------------------------------------------------- tests
import copy as _copy
import pytest as _pytest

_END = datetime(2026, 11, 30, 12, tzinfo=timezone.utc)


def _sub(**kw):
    s = {"id": "s1", "status": "active", "plan_name": "Basic", "seat_price_cents": 1000,
         "seats": 5, "billable_seats": 5, "vat_id": None, "period_end": _END}
    s.update(kw)
    return s


def _plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def _at(days):
    return _END - timedelta(days=days)


def test_basic():
    r = prorate_seats(_sub(), _plan(), _at(15))
    assert [x["kind"] for x in r] == ["credit", "charge"]
    assert (r[0]["amount_cents"], r[0]["vat_cents"], r[0]["approved_by"]) == (2500, 0, APPROVER)
    assert (r[1]["amount_cents"], r[1]["vat_cents"], r[1]["approved_by"]) == (5000, 1050, None)
    assert r[0]["description"] == "Credit for unused Basic plan, period ends 2026-11-30"
    assert r[1]["description"] == "Charge for unused Pro plan, period ends 2026-11-30"


def test_rounding_and_vat():
    s = _sub(seat_price_cents=999, billable_seats=1)
    r = prorate_seats(s, _plan(1999), _at(7))
    assert (r[0]["amount_cents"], r[1]["amount_cents"], r[1]["vat_cents"]) == (234, 466, 97)
    r = prorate_seats(_sub(seat_price_cents=999, billable_seats=1, vat_id="DE123"), _plan(1999), _at(7))
    assert r[1]["vat_cents"] == 0
    r = prorate_seats(_sub(seat_price_cents=999, billable_seats=1, vat_id="  "), _plan(1999), _at(7))
    assert r[1]["vat_cents"] == 97


def test_no_lines():
    assert prorate_seats(_sub(status="trialing"), _plan(), _at(15)) == []
    assert prorate_seats(_sub(), _plan(500), _at(15)) == []
    assert prorate_seats(_sub(), _plan(1000), _at(15)) == []
    assert prorate_seats(_sub(), _plan(), _END + timedelta(days=2)) == []


def test_billable_seats_and_clamp():
    s = _sub(seats=10, billable_seats=7, legacy_discount=50)
    assert prorate_seats(s, _plan(), _at(30))[0]["amount_cents"] == 7000
    assert prorate_seats(s, _plan(), _at(90))[0]["amount_cents"] == 7000


def test_threshold():
    s = _sub(seat_price_cents=100, billable_seats=1)
    r = prorate_seats(s, _plan(5000), _at(15))
    assert r[0]["amount_cents"] == 50
    r = prorate_seats(s, _plan(5000), _at(14))
    assert [x["kind"] for x in r] == ["charge"]


def test_approvers():
    r = prorate_seats(_sub(seat_price_cents=10000), _plan(20000), _at(30))
    assert (r[0]["amount_cents"], r[0]["approved_by"]) == (50000, "Win Tee Fung Tao")
    r = prorate_seats(_sub(seat_price_cents=50001, billable_seats=1), _plan(60000), _at(30))
    assert (r[0]["amount_cents"], r[0]["approved_by"]) == (50001, "Ramón Etxeberria-Goñi")


@_pytest.mark.parametrize("name", ["", "x" * 200, "é" * 200, "日本語" * 50])
def test_description_length(name):
    r = prorate_seats(_sub(plan_name=name), _plan(name=name), _at(15))
    for line in r:
        assert len(line["description"]) <= 80
        assert line["description"].endswith("period ends 2026-11-30")


def test_types_errors_and_no_mutation():
    s = _sub()
    before = _copy.deepcopy(s)
    r = prorate_seats(s, _plan(), _at(15))
    assert s == before
    assert all(type(x["amount_cents"]) is int and type(x["vat_cents"]) is int for x in r)
    with _pytest.raises(ValueError):
        prorate_seats(s, _plan(), datetime(2026, 11, 15))
    with _pytest.raises(ValueError):
        prorate_seats(_sub(period_end=datetime(2026, 11, 30)), _plan(), _at(15))
    for bad in (True, 1.5, "5"):
        with _pytest.raises(TypeError):
            prorate_seats(_sub(billable_seats=bad), _plan(), _at(15))
    with _pytest.raises(ValueError):
        prorate_seats(_sub(seat_price_cents=-1), _plan(), _at(15))
    with _pytest.raises(ValueError):
        prorate_seats(_sub(), _plan(-5), _at(15))