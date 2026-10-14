# === FILE: seat_proration.py ===
"""Prorated seat-change billing (Fernhollow Studios).

Public entry point: prorate_seats(subscription, new_plan, changed_at).

Open-spec assumptions, to be confirmed with the client:
A1  Charge VAT (21%) is computed on the net charge and floored to the cent.
A2  Credit amounts are positive; kind="credit" carries the sign.
A3  Equal price is a no-op and returns [], the same as a downgrade.
A4  All amounts are EUR cents; there is no currency field.
A5  Day count is exact elapsed time at microsecond precision (fractional days allowed).
A6  If changed_at is more than 30 days before period_end, raise ValueError rather than clamp.
A7  Description truncation: the plan name is shortened and "…" (U+2026) is appended.
    Length is counted in Python characters. If fewer than 2 name characters fit, raise ValueError.
A8  vat_id counts as set only if it is a non-empty string after stripping whitespace.
A9  The status check is an exact, case-sensitive match on "trialing".
A10 Minimum line: a line is dropped when its net amount_cents is < 50. Applied to credit and charge independently.
A11 The approval threshold uses the credit line's rounded amount_cents.
A12 seat_price_cents may be 0 but not negative. billable_seats must be an int >= 0.
    seats is checked for presence and type only and is never used in billing.
A13 Dates are formatted from period_end's own tzinfo, with no UTC conversion.
A14 Subscription id is passed through unchanged.
"""

from collections.abc import Mapping
from datetime import datetime, timedelta
from fractions import Fraction
import math

PERIOD = timedelta(days=30)
PERIOD_US = PERIOD // timedelta(microseconds=1)
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
SENIOR_APPROVAL_THRESHOLD = 50_000
DEFAULT_APPROVER = "Win Tee Fung Tao"
SENIOR_APPROVER = "Ramón Etxeberria-Goñi"
DESCRIPTION_MAX = 80
ELLIPSIS = "…"

REQUIRED_SUBSCRIPTION_KEYS = (
    "id", "status", "plan_name", "seat_price_cents",
    "seats", "billable_seats", "vat_id", "period_end",
)
REQUIRED_PLAN_KEYS = ("name", "seat_price_cents")


def _require_keys(mapping, keys, label):
    for key in keys:
        if key not in mapping:
            raise ValueError(f"{label} is missing required key {key!r}")


def _require_int(value, label, minimum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer, got {type(value).__name__}")
    if minimum is not None and value < minimum:
        raise ValueError(f"{label} must be >= {minimum}, got {value}")
    return value


def _require_name(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _require_aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime, got {type(value).__name__}")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value


def _describe(before, name, after):
    full = f"{before}{name}{after}"
    if len(full) <= DESCRIPTION_MAX:
        return full
    room = DESCRIPTION_MAX - len(before) - len(after)
    if room < 2:
        raise ValueError(
            f"description cannot fit in {DESCRIPTION_MAX} characters with the full date"
        )
    return f"{before}{name[:room - 1]}{ELLIPSIS}{after}"


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, Mapping):
        raise TypeError("subscription must be a mapping")
    if not isinstance(new_plan, Mapping):
        raise TypeError("new_plan must be a mapping")
    _require_keys(subscription, REQUIRED_SUBSCRIPTION_KEYS, "subscription")
    _require_keys(new_plan, REQUIRED_PLAN_KEYS, "new_plan")

    _require_aware(changed_at, "changed_at")
    period_end = _require_aware(subscription["period_end"], "subscription.period_end")

    status = subscription["status"]
    if not isinstance(status, str):
        raise TypeError("subscription.status must be a string")

    old_name = _require_name(subscription["plan_name"], "subscription.plan_name")
    new_name = _require_name(new_plan["name"], "new_plan.name")
    old_price = _require_int(subscription["seat_price_cents"],
                             "subscription.seat_price_cents", 0)
    new_price = _require_int(new_plan["seat_price_cents"],
                             "new_plan.seat_price_cents", 0)
    billable = _require_int(subscription["billable_seats"],
                            "subscription.billable_seats", 0)
    _require_int(subscription["seats"], "subscription.seats")  # never used for billing

    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("subscription.vat_id must be a string or None")
    reverse_charge = vat_id is not None and vat_id.strip() != ""

    if status == "trialing":
        return []
    if changed_at >= period_end:
        return []
    if billable == 0:
        return []
    if new_price <= old_price:
        return []

    remaining = period_end - changed_at
    if remaining > PERIOD:
        raise ValueError("changed_at is more than 30 days before period_end")
    unused = Fraction(remaining // timedelta(microseconds=1), PERIOD_US)

    credit = math.ceil(Fraction(old_price * billable) * unused)
    charge = math.floor(Fraction(new_price * billable) * unused)

    period_date = period_end.date().isoformat()
    lines = []

    if credit >= MIN_LINE_CENTS:
        approver = (SENIOR_APPROVER if credit > SENIOR_APPROVAL_THRESHOLD
                    else DEFAULT_APPROVER)
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe(
                "Credit: ", old_name,
                f" seats unused, period end {period_date}"),
            "approved_by": approver,
        })

    if charge >= MIN_LINE_CENTS:
        vat = 0 if reverse_charge else charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe(
                "Charge: ", new_name,
                f" seats, period end {period_date}"),
            "approved_by": None,
        })

    return lines


# === FILE: test_seat_proration.py ===
# Pytest tests for seat_proration.prorate_seats.
# Note: these tests were written without execution access in this session and
# have not been run. Run `pytest` before release.

from datetime import datetime, timedelta, timezone

import pytest

import seat_proration as mod
from seat_proration import prorate_seats

UTC = timezone.utc
PERIOD_END = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
TEN_DAYS_UNUSED = PERIOD_END - timedelta(days=10)


def sub(**overrides):
    d = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Pro",
        "seat_price_cents": 1000,
        "seats": 2,
        "billable_seats": 2,
        "vat_id": None,
        "period_end": PERIOD_END,
    }
    d.update(overrides)
    return d


def plan(price, name="Enterprise"):
    return {"name": name, "seat_price_cents": price}


def test_worked_example():
    lines = prorate_seats(sub(), plan(1500), TEN_DAYS_UNUSED)
    assert len(lines) == 2
    credit, charge = lines
    assert credit["kind"] == "credit"
    assert credit["amount_cents"] == 667
    assert credit["vat_cents"] == 0
    assert credit["approved_by"] == "Win Tee Fung Tao"
    assert charge["kind"] == "charge"
    assert charge["amount_cents"] == 1000
    assert charge["vat_cents"] == 210
    assert charge["approved_by"] is None


def test_downgrade_returns_empty():
    assert prorate_seats(sub(), plan(500), TEN_DAYS_UNUSED) == []


def test_equal_price_returns_empty():
    assert prorate_seats(sub(), plan(1000), TEN_DAYS_UNUSED) == []


def test_trialing_returns_empty():
    assert prorate_seats(sub(status="trialing"), plan(1500), TEN_DAYS_UNUSED) == []


def test_changed_at_at_or_after_period_end_returns_empty():
    assert prorate_seats(sub(), plan(1500), PERIOD_END) == []
    assert prorate_seats(sub(), plan(1500), PERIOD_END + timedelta(hours=1)) == []


def test_zero_billable_seats_returns_empty():
    assert prorate_seats(sub(billable_seats=0), plan(1500), TEN_DAYS_UNUSED) == []


def test_seats_field_does_not_change_amounts():
    base = prorate_seats(sub(), plan(1500), TEN_DAYS_UNUSED)
    other = prorate_seats(sub(seats=999), plan(1500), TEN_DAYS_UNUSED)
    assert [(l["kind"], l["amount_cents"], l["vat_cents"]) for l in base] == \
           [(l["kind"], l["amount_cents"], l["vat_cents"]) for l in other]


def test_credit_precedes_charge():
    lines = prorate_seats(sub(), plan(1500), TEN_DAYS_UNUSED)
    assert [l["kind"] for l in lines] == ["credit", "charge"]


def test_all_amounts_are_int():
    for line in prorate_seats(sub(), plan(1500), TEN_DAYS_UNUSED):
        assert type(line["amount_cents"]) is int
        assert type(line["vat_cents"]) is int


def test_credit_exactly_50000_goes_to_default_approver():
    # Full period unused: credit = 25000 * 2 = 50000
    start = PERIOD_END - timedelta(days=30)
    lines = prorate_seats(sub(seat_price_cents=25000, billable_seats=2),
                          plan(30000), start)
    credit = lines[0]
    assert credit["amount_cents"] == 50000
    assert credit["approved_by"] == "Win Tee Fung Tao"


def test_credit_50001_goes_to_senior_approver():
    start = PERIOD_END - timedelta(days=30)
    lines = prorate_seats(sub(seat_price_cents=50001, billable_seats=1),
                          plan(60000), start)
    credit = lines[0]
    assert credit["amount_cents"] == 50001
    assert credit["approved_by"] == "Ramón Etxeberria-Goñi"


def test_49_cent_line_dropped_and_50_kept():
    start = PERIOD_END - timedelta(days=30)
    # Charge 49 (old price 0 so no credit line): dropped.
    assert prorate_seats(sub(seat_price_cents=0, billable_seats=1),
                         plan(49), start) == []
    # Charge 50: kept, VAT floor(50 * 0.21) = 10.
    lines = prorate_seats(sub(seat_price_cents=0, billable_seats=1),
                          plan(50), start)
    assert len(lines) == 1
    assert lines[0]["amount_cents"] == 50
    assert lines[0]["vat_cents"] == 10


def test_credit_49_dropped_credit_50_kept():
    start = PERIOD_END - timedelta(days=30)
    lines = prorate_seats(sub(seat_price_cents=49, billable_seats=1),
                          plan(60), start)
    assert [l["kind"] for l in lines] == ["charge"]
    lines = prorate_seats(sub(seat_price_cents=50, billable_seats=1),
                          plan(60), start)
    assert [l["kind"] for l in lines] == ["credit", "charge"]


def test_reverse_charge_gives_zero_charge_vat():
    lines = prorate_seats(sub(vat_id="DE123456789"), plan(1500), TEN_DAYS_UNUSED)
    charge = [l for l in lines if l["kind"] == "charge"][0]
    assert charge["vat_cents"] == 0
    assert charge["amount_cents"] == 1000


def test_empty_vat_id_still_charges_vat():
    lines = prorate_seats(sub(vat_id=""), plan(1500), TEN_DAYS_UNUSED)
    charge = [l for l in lines if l["kind"] == "charge"][0]
    assert charge["vat_cents"] == 210


def test_credits_have_zero_vat():
    lines = prorate_seats(sub(), plan(1500), TEN_DAYS_UNUSED)
    credit = [l for l in lines if l["kind"] == "credit"][0]
    assert credit["vat_cents"] == 0


def test_descriptions_fit_80_chars_and_contain_date():
    lines = prorate_seats(sub(plan_name="P" * 200), plan(1500, name="Q" * 200),
                          TEN_DAYS_UNUSED)
    for line in lines:
        assert len(line["description"]) <= 80
        assert "2026-11-01" in line["description"]
    credit = lines[0]
    charge = lines[1]
    assert credit["description"].startswith("Credit: ")
    assert "…" in credit["description"]
    assert "…" in charge["description"]


def test_description_uses_period_end_timezone_without_conversion():
    tz = timezone(timedelta(hours=5))
    period_end = datetime(2026, 11, 1, 1, 0, tzinfo=tz)  # 2026-10-31 20:00 UTC
    lines = prorate_seats(sub(period_end=period_end), plan(1500),
                          period_end - timedelta(days=10))
    for line in lines:
        assert "2026-11-01" in line["description"]
        assert "2026-10-31" not in line["description"]


def test_description_too_long_raises(monkeypatch):
    monkeypatch.setattr(mod, "DESCRIPTION_MAX", 20)
    with pytest.raises(ValueError):
        prorate_seats(sub(), plan(1500), TEN_DAYS_UNUSED)


def test_legacy_discount_has_no_effect():
    base = prorate_seats(sub(), plan(1500), TEN_DAYS_UNUSED)
    with_discount = prorate_seats(sub(legacy_discount=0.5), plan(1500),
                                  TEN_DAYS_UNUSED)
    assert base == with_discount


def test_fractional_day_count_is_exact():
    # 36 hours unused = 1.5 days => fraction 1/20; credit = 2000/20 = 100.
    changed = PERIOD_END - timedelta(hours=36)
    lines = prorate_seats(sub(), plan(1500), changed)
    assert lines[0]["amount_cents"] == 100
    assert lines[1]["amount_cents"] == 150


def test_missing_subscription_key_raises():
    d = sub()
    del d["vat_id"]
    with pytest.raises(ValueError):
        prorate_seats(d, plan(1500), TEN_DAYS_UNUSED)


def test_missing_plan_key_raises():
    with pytest.raises(ValueError):
        prorate_seats(sub(), {"name": "Enterprise"}, TEN_DAYS_UNUSED)


def test_naive_changed_at_raises():
    with pytest.raises(ValueError):
        prorate_seats(sub(), plan(1500), datetime(2026, 10, 22, 12, 0))


def test_naive_period_end_raises():
    with pytest.raises(ValueError):
        prorate_seats(sub(period_end=datetime(2026, 11, 1, 12, 0)), plan(1500),
                      TEN_DAYS_UNUSED)


def test_changed_at_not_datetime_raises():
    with pytest.raises(TypeError):
        prorate_seats(sub(), plan(1500), "2026-10-22")


def test_float_price_raises():
    with pytest.raises(TypeError):
        prorate_seats(sub(seat_price_cents=10.5), plan(1500), TEN_DAYS_UNUSED)


def test_bool_price_raises():
    with pytest.raises(TypeError):
        prorate_seats(sub(), plan(True), TEN_DAYS_UNUSED)


def test_non_integer_seats_raises():
    with pytest.raises(TypeError):
        prorate_seats(sub(seats="2"), plan(1500), TEN_DAYS_UNUSED)


def test_negative_billable_seats_raises():
    with pytest.raises(ValueError):
        prorate_seats(sub(billable_seats=-1), plan(1500), TEN_DAYS_UNUSED)