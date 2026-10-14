# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-mox51g3w/prorate.py =====
# NOT RUN: this agent had no tools, so the tests below were never executed.
# Run them with: python3 -I -m pytest
# Assumptions beyond the spec:
# - Validation also requires plan_name/new_plan name to be str and status to be str.
# - A non-None, non-str vat_id is stringified, then stripped, before the truthiness test.
# - The period end date is formatted from period_end in its own timezone (D7).
# - Microseconds are kept: all arithmetic uses integer microseconds.
"""Seat proration for plan upgrades (integer arithmetic only)."""
from datetime import datetime

PERIOD_DAYS = 13
MIN_LINE_CENTS = 50
VAT_RATE_PERCENT = 21
APPROVAL_LIMIT_CENTS = 50000
APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
APPROVER_HIGH = "Ramón Etxeberria-Goñi"
MAX_DESCRIPTION = 80
_US = 10**6
_PERIOD_US = PERIOD_DAYS * 86400 * _US

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def _is_count(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _aware(v):
    return isinstance(v, datetime) and v.tzinfo is not None and v.utcoffset() is not None


def _validate(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict):
        raise ValueError("subscription must be a dict")
    if not isinstance(new_plan, dict):
        raise ValueError("new_plan must be a dict")
    for k in _SUB_KEYS:
        if k not in subscription:
            raise ValueError(f"subscription is missing key: {k}")
    for k in _PLAN_KEYS:
        if k not in new_plan:
            raise ValueError(f"new_plan is missing key: {k}")
    for label, v in (("subscription.seat_price_cents", subscription["seat_price_cents"]),
                     ("subscription.billable_seats", subscription["billable_seats"]),
                     ("new_plan.seat_price_cents", new_plan["seat_price_cents"])):
        if not _is_count(v):
            raise ValueError(f"{label} must be a non-negative int")
    if not isinstance(subscription["status"], str):
        raise ValueError("subscription.status must be a string")
    if not isinstance(subscription["plan_name"], str):
        raise ValueError("subscription.plan_name must be a string")
    if not isinstance(new_plan["name"], str):
        raise ValueError("new_plan.name must be a string")
    if not _aware(changed_at):
        raise ValueError("changed_at must be a timezone-aware datetime")
    if not _aware(subscription["period_end"]):
        raise ValueError("subscription.period_end must be a timezone-aware datetime")


def _remaining_units(changed_at, period_end):
    """Remaining time in integer microseconds, clamped to [0, full period]."""
    d = period_end - changed_at
    us = (d.days * 86400 + d.seconds) * _US + d.microseconds
    return max(0, min(us, _PERIOD_US))


def _credit_cents(price, seats, remaining):
    return -(-(price * seats * remaining) // _PERIOD_US)  # ceil


def _charge_cents(price, seats, remaining):
    return (price * seats * remaining) // _PERIOD_US  # floor


def _vat_cents(amount, vat_id):
    if vat_id is not None and str(vat_id).strip():
        return 0
    return amount * VAT_RATE_PERCENT // 100


def _approver(amount):
    return APPROVER_HIGH if amount > APPROVAL_LIMIT_CENTS else APPROVER_DEFAULT


def _describe(kind, plan, date):
    prefix = f"{kind.capitalize()} unused "
    suffix = f" until {date}"
    if len(prefix) + len(plan) + len(suffix) > MAX_DESCRIPTION:
        k = max(0, MAX_DESCRIPTION - len(prefix) - len(suffix) - 3)
        plan = plan[:k] + "..."
    return prefix + plan + suffix


def prorate_seats(subscription, new_plan, changed_at):
    _validate(subscription, new_plan, changed_at)
    if subscription["status"].strip().casefold() == "trialing":
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []
    seats = subscription["billable_seats"]
    period_end = subscription["period_end"]
    remaining = _remaining_units(changed_at, period_end)
    date = period_end.strftime("%Y-%m-%d")
    sid = subscription["id"]

    lines = []
    credit = _credit_cents(old_price, seats, remaining)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sid,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("credit", subscription["plan_name"], date),
            "approved_by": _approver(credit),
        })
    charge = _charge_cents(new_price, seats, remaining)
    if charge >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sid,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": _vat_cents(charge, subscription["vat_id"]),
            "description": _describe("charge", new_plan["name"], date),
            "approved_by": None,
        })
    return lines


# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-mox51g3w/test_prorate.py =====
import copy
from datetime import datetime, timedelta, timezone

import pytest

from prorate import prorate_seats

UTC = timezone.utc
END = datetime(2025, 3, 14, 12, 0, tzinfo=UTC)
FULL = END - timedelta(days=13)


def sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 1, "billable_seats": 1,
         "vat_id": None, "period_end": END}
    s.update(kw)
    return s


def plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def test_downgrade_returns_empty():
    assert prorate_seats(sub(), plan(500), FULL) == []


def test_trialing_returns_empty():
    assert prorate_seats(sub(status=" Trialing "), plan(), FULL) == []


def test_equal_price_not_downgrade():
    lines = prorate_seats(sub(), plan(1000), FULL)
    assert [l["kind"] for l in lines] == ["credit", "charge"]


def test_billable_seats_used_not_seats():
    lines = prorate_seats(sub(seats=100, billable_seats=2), plan(), FULL)
    assert lines[0]["amount_cents"] == 2000
    assert lines[1]["amount_cents"] == 4000


def test_credit_ceil_charge_floor():
    lines = prorate_seats(sub(), plan(2000), END - timedelta(days=1))
    assert lines[0]["amount_cents"] == 77   # 76.92 -> 77
    assert lines[1]["amount_cents"] == 153  # 153.84 -> 153


def test_min_line_independent():
    # credit 49 skipped, charge 100 kept
    lines = prorate_seats(sub(seat_price_cents=49), plan(100), FULL)
    assert [l["kind"] for l in lines] == ["charge"]
    # exactly 50 kept
    lines = prorate_seats(sub(seat_price_cents=50), plan(50), FULL)
    assert [l["kind"] for l in lines] == ["credit", "charge"]
    # credit 49.5 -> 50 kept, charge 49.5 -> 49 skipped
    at = END - timedelta(days=6, hours=12)
    lines = prorate_seats(sub(seat_price_cents=99), plan(99), at)
    assert [l["kind"] for l in lines] == ["credit"]
    assert lines[0]["amount_cents"] == 50


def test_vat_floor():
    lines = prorate_seats(sub(), plan(2000), END - timedelta(days=1))
    assert lines[1]["amount_cents"] == 153
    assert lines[1]["vat_cents"] == 32  # 32.13 -> 32


def test_reverse_charge_and_blank_vat_id():
    assert prorate_seats(sub(vat_id="NL123"), plan(), FULL)[1]["vat_cents"] == 0
    for blank in (None, "", "   "):
        assert prorate_seats(sub(vat_id=blank), plan(), FULL)[1]["vat_cents"] == 420


def test_credit_vat_zero():
    assert prorate_seats(sub(vat_id=None), plan(), FULL)[0]["vat_cents"] == 0


def test_approver_threshold():
    a = prorate_seats(sub(seat_price_cents=50000), plan(60000), FULL)[0]
    b = prorate_seats(sub(seat_price_cents=50001), plan(60000), FULL)[0]
    assert a["amount_cents"] == 50000 and a["approved_by"] == "Nguyễn Thị Phương Thảo"
    assert b["amount_cents"] == 50001 and b["approved_by"] == "Ramón Etxeberria-Goñi"
    assert prorate_seats(sub(), plan(), FULL)[1]["approved_by"] is None


def test_description_basic_and_long():
    lines = prorate_seats(sub(), plan(), FULL)
    assert lines[0]["description"] == "Credit unused Basic until 2025-03-14"
    assert lines[1]["description"] == "Charge unused Pro until 2025-03-14"
    long = "X" * 100
    lines = prorate_seats(sub(plan_name=long), plan(name=long), FULL)
    for l in lines:
        assert len(l["description"]) <= 80
        assert l["description"].endswith(" until 2025-03-14")
        assert "..." in l["description"]


def test_order_and_keys():
    lines = prorate_seats(sub(), plan(), FULL)
    assert [l["kind"] for l in lines] == ["credit", "charge"]
    assert set(lines[0]) == {"subscription_id", "kind", "amount_cents",
                             "vat_cents", "description", "approved_by"}


def test_clamping():
    assert prorate_seats(sub(), plan(), END) == []
    assert prorate_seats(sub(), plan(), END + timedelta(days=2)) == []
    assert (prorate_seats(sub(), plan(), END - timedelta(days=30))
            == prorate_seats(sub(), plan(), FULL))


def test_non_utc_timezones():
    tz = timezone(timedelta(hours=14))
    end = datetime(2025, 3, 14, 1, 0, tzinfo=tz)  # 2025-03-13 11:00 UTC
    at = (end - timedelta(days=13)).astimezone(timezone(timedelta(hours=-8)))
    lines = prorate_seats(sub(period_end=end), plan(), at)
    assert lines[0]["amount_cents"] == 1000
    assert lines[1]["amount_cents"] == 2000
    assert lines[0]["description"].endswith("2025-03-14")


def test_all_ints():
    for l in prorate_seats(sub(), plan(), END - timedelta(days=1)):
        assert type(l["amount_cents"]) is int
        assert type(l["vat_cents"]) is int


def test_inputs_not_mutated():
    s, p = sub(), plan()
    s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
    prorate_seats(s, p, FULL)
    assert s == s0 and p == p0


def test_legacy_discount_ignored():
    at = END - timedelta(days=3)
    assert (prorate_seats(sub(legacy_discount=50), plan(), at)
            == prorate_seats(sub(), plan(), at))


def test_zero_billable_seats():
    assert prorate_seats(sub(billable_seats=0), plan(), FULL) == []


def test_validation():
    s = sub()
    del s["vat_id"]
    with pytest.raises(ValueError):
        prorate_seats(s, plan(), FULL)
    with pytest.raises(ValueError):
        prorate_seats(sub(billable_seats=True), plan(), FULL)
    with pytest.raises(ValueError):
        prorate_seats(sub(billable_seats=-1), plan(), FULL)
    with pytest.raises(ValueError):
        prorate_seats(sub(), plan(10.5), FULL)
    with pytest.raises(ValueError):
        prorate_seats(sub(), plan(), datetime(2025, 3, 1))
    with pytest.raises(ValueError):
        prorate_seats(sub(period_end=datetime(2025, 3, 14)), plan(), FULL)