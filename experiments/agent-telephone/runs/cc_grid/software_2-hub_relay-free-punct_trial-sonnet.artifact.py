"""Fernhollow Studios seat proration (client: Ingrid).

Public entry point: prorate_seats(subscription, new_plan, changed_at).

Configurable (module constants / single places):
  - PARTIAL_DAY_MODE: "exact_seconds" (default) or "whole_days"
    (ceil days for credit, floor days for charge).
  - _signed(): the only place that defines the amount sign convention.
  - MIN_LINE_CENTS, VAT_RATE_PERCENT, CREDIT_APPROVAL_LIMIT_CENTS,
    approver names, MAX_DESCRIPTION_LEN, PERIOD_DAYS.

Assumptions for Ingrid to confirm:
  1. VAT is rounded down (floor), which she did not state.
  2. Partial days are handled via exact elapsed time (default), not whole days.
  3. Amounts are positive magnitudes for both kinds; "kind" carries direction.
  4. Equal price with a different plan name prorates (credit and charge);
     equal price and equal name returns [].
  5. Statuses other than "trialing" prorate normally.
  6. Prices are net of VAT and in euro cents.
  7. Description wording is our choice.
"""
import unicodedata
from datetime import datetime, timedelta, timezone

PARTIAL_DAY_MODE = "exact_seconds"  # or "whole_days"
PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
VAT_RATE_PERCENT = 21
CREDIT_APPROVAL_LIMIT_CENTS = 50000
MAX_DESCRIPTION_LEN = 80
APPROVER_DEFAULT = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
APPROVER_HIGH = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")

_US = timedelta(microseconds=1)
_DAY_US = 86400 * 10**6
_PERIOD_US = PERIOD_DAYS * _DAY_US


def _signed(kind, magnitude):
    """Sign convention lives here: positive magnitude for both kinds."""
    return magnitude


def _int(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative int")
    return value


def _aware(value, name):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value


def _remaining_us(raw_us, rounding):
    us = max(0, min(raw_us, _PERIOD_US))
    if PARTIAL_DAY_MODE == "whole_days":
        q, r = divmod(us, _DAY_US)
        if rounding == "up" and r:
            q += 1
        us = q * _DAY_US
    return min(us, _PERIOD_US)


def _description(template, plan, date_str):
    full = template.format(plan=plan, date=date_str)
    if len(full) <= MAX_DESCRIPTION_LEN:
        return full
    room = MAX_DESCRIPTION_LEN - len(template.format(plan="", date=date_str))
    cut = plan[: max(room - 3, 1)].rstrip() or plan[:1]
    return template.format(plan=cut + "...", date=date_str)


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise TypeError("subscription and new_plan must be dicts")
    try:
        sub_id = subscription["id"]
        status = subscription["status"]
        old_name = subscription["plan_name"]
        old_price = _int(subscription["seat_price_cents"], "seat_price_cents")
        billable = _int(subscription["billable_seats"], "billable_seats")
        vat_id = subscription["vat_id"]
        period_end = _aware(subscription["period_end"], "period_end")
        new_name = new_plan["name"]
        new_price = _int(new_plan["seat_price_cents"], "new seat_price_cents")
    except KeyError as e:
        raise ValueError(f"missing key: {e}") from None
    _aware(changed_at, "changed_at")
    if not isinstance(status, str):
        raise TypeError("status must be a string")
    for n in (old_name, new_name):
        if not isinstance(n, str) or not n.strip():
            raise ValueError("plan names must be non-empty strings")
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be a string or None")

    if status == "trialing" or billable == 0:
        return []
    if new_price < old_price:
        return []
    if new_name == old_name and new_price == old_price:
        return []
    raw_us = (period_end - changed_at) // _US
    if raw_us <= 0:
        return []

    date_str = period_end.date().isoformat()
    has_vat_id = bool(vat_id and vat_id.strip())
    lines = []

    credit_num = old_price * billable * _remaining_us(raw_us, "up")
    credit = -(-credit_num // _PERIOD_US)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": _signed("credit", credit),
            "vat_cents": 0,
            "description": _description(
                "Credit: unused {plan} seats, period ends {date}", old_name, date_str),
            "approved_by": APPROVER_HIGH if credit > CREDIT_APPROVAL_LIMIT_CENTS
            else APPROVER_DEFAULT,
        })

    charge_num = new_price * billable * _remaining_us(raw_us, "down")
    charge = charge_num // _PERIOD_US
    if charge >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": _signed("charge", charge),
            "vat_cents": 0 if has_vat_id else charge * VAT_RATE_PERCENT // 100,
            "description": _description(
                "Charge: {plan} seats, period ends {date}", new_name, date_str),
            "approved_by": None,
        })
    return lines


# ----------------------------- tests (pytest) -----------------------------
import copy  # noqa: E402

import pytest  # noqa: E402

_END = datetime(2026, 11, 30, 12, 0, tzinfo=timezone.utc)


def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 10, "billable_seats": 10,
         "vat_id": None, "period_end": _END}
    s.update(kw)
    return s


def _new(price=1500, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def _at(days):
    return _END - timedelta(days=days)


def test_basic_upgrade():
    r = prorate_seats(_sub(), _new(), _at(15))
    assert [x["kind"] for x in r] == ["credit", "charge"]
    c, ch = r
    assert (c["amount_cents"], c["vat_cents"], c["approved_by"]) == (5000, 0, APPROVER_DEFAULT)
    assert (ch["amount_cents"], ch["vat_cents"], ch["approved_by"]) == (7500, 1575, None)
    assert set(c) == {"subscription_id", "kind", "amount_cents", "vat_cents",
                      "description", "approved_by"}


def test_vat_id_zeroes_charge_vat():
    r = prorate_seats(_sub(vat_id=" NL123 "), _new(), _at(15))
    assert r[1]["vat_cents"] == 0
    r = prorate_seats(_sub(vat_id="   "), _new(), _at(15))
    assert r[1]["vat_cents"] == 1575


def test_rounding_directions():
    r = prorate_seats(_sub(billable_seats=1), _new(1001), _at(7))
    assert r[0]["amount_cents"] == 234
    assert (r[1]["amount_cents"], r[1]["vat_cents"]) == (233, 48)


def test_half_day():
    r = prorate_seats(_sub(billable_seats=1), _new(), _at(14.5))
    assert r[0]["amount_cents"] == 484


def test_threshold():
    r = prorate_seats(_sub(seat_price_cents=245, billable_seats=1), _new(245, "Pro"), _at(6))
    assert r == []
    r = prorate_seats(_sub(seat_price_cents=250, billable_seats=1), _new(250, "Pro"), _at(6))
    assert [x["amount_cents"] for x in r] == [50, 50]


def test_approver_boundary():
    r = prorate_seats(_sub(seat_price_cents=50000, billable_seats=1), _new(50000), _at(30))
    assert r[0]["amount_cents"] == 50000 and r[0]["approved_by"] == APPROVER_DEFAULT
    r = prorate_seats(_sub(seat_price_cents=50001, billable_seats=1), _new(50001), _at(30))
    assert r[0]["amount_cents"] == 50001 and r[0]["approved_by"] == APPROVER_HIGH


def test_cap_at_30_days():
    a = prorate_seats(_sub(), _new(), _at(45))
    b = prorate_seats(_sub(), _new(), _at(30))
    assert a == b


def test_empty_cases():
    assert prorate_seats(_sub(seat_price_cents=1000), _new(900), _at(15)) == []
    assert prorate_seats(_sub(status="trialing"), _new(), _at(15)) == []
    assert prorate_seats(_sub(), _new(), _at(0)) == []
    assert prorate_seats(_sub(), _new(), _at(-1)) == []
    assert prorate_seats(_sub(billable_seats=0), _new(), _at(15)) == []
    assert prorate_seats(_sub(plan_name="Pro"), _new(1000, "Pro"), _at(15)) == []


def test_other_status_prorates():
    assert len(prorate_seats(_sub(status="past_due"), _new(), _at(15))) == 2


def test_seats_ignored_and_legacy_discount_ignored():
    base = prorate_seats(_sub(), _new(), _at(15))
    assert prorate_seats(_sub(seats=999), _new(), _at(15)) == base
    assert prorate_seats(_sub(legacy_discount=50), _new(), _at(15)) == base


def test_long_plan_name():
    name = "X" * 200
    r = prorate_seats(_sub(plan_name=name), _new(name="Y" * 200), _at(15))
    for line in r:
        assert len(line["description"]) <= 80
        assert "2026-11-30" in line["description"]
        assert "..." in line["description"]
    assert r[0]["description"].startswith("Credit: unused X")


def test_short_description():
    r = prorate_seats(_sub(), _new(), _at(15))
    assert r[0]["description"] == "Credit: unused Basic seats, period ends 2026-11-30"
    assert r[1]["description"] == "Charge: Pro seats, period ends 2026-11-30"


def test_date_in_own_timezone():
    tz = timezone(timedelta(hours=-5))
    end = datetime(2026, 11, 30, 23, 0, tzinfo=tz)
    r = prorate_seats(_sub(period_end=end), _new(), end - timedelta(days=15))
    assert "2026-11-30" in r[0]["description"]


def test_types_and_no_mutation():
    s, n = _sub(), _new()
    s0, n0 = copy.deepcopy(s), copy.deepcopy(n)
    r = prorate_seats(s, n, _at(15))
    assert s == s0 and n == n0
    for line in r:
        assert type(line["amount_cents"]) is int
        assert type(line["vat_cents"]) is int


def test_invalid_inputs():
    with pytest.raises((ValueError, TypeError)):
        prorate_seats(_sub(), _new(), datetime(2026, 11, 1))
    with pytest.raises((ValueError, TypeError)):
        prorate_seats(_sub(period_end=datetime(2026, 11, 30)), _new(), _at(15))
    with pytest.raises((ValueError, TypeError)):
        prorate_seats(_sub(seat_price_cents=10.0), _new(), _at(15))
    with pytest.raises((ValueError, TypeError)):
        prorate_seats(_sub(billable_seats=True), _new(), _at(15))
    with pytest.raises((ValueError, TypeError)):
        prorate_seats(_sub(billable_seats=-1), _new(), _at(15))
    with pytest.raises((ValueError, TypeError)):
        prorate_seats(_sub(), _new(1500.0), _at(15))
    s = _sub()
    del s["vat_id"]
    with pytest.raises((ValueError, TypeError)):
        prorate_seats(s, _new(), _at(15))