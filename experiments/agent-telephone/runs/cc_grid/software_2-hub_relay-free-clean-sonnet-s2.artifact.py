# ===== FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-n7ggtr8l/seat_proration.py =====
# NOTE: I had no tools in this run, so these files were written but NOT executed. Run pytest to confirm.

"""Seat proration for Fernhollow Studios billing (standard library only)."""

from datetime import datetime, timedelta

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
VAT_RATE_PERCENT = 21
APPROVAL_THRESHOLD_CENTS = 50_000
DEFAULT_APPROVER = "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"
SENIOR_APPROVER = "Ram\u00f3n Etxeberria-Go\u00f1i"
MAX_DESCRIPTION_LEN = 80


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _require_aware(name, value):
    if not isinstance(value, datetime):
        raise ValueError(f"{name} must be a datetime")
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(f"{name} must be timezone-aware (naive datetime rejected)")


def _require_int(name, value, minimum=0):
    if not _is_int(value) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}, got {value!r}")


def _description(prefix, plan_name, date_str):
    suffix = f" until {date_str}"
    available = MAX_DESCRIPTION_LEN - len(prefix) - len(suffix)
    if len(plan_name) <= available:
        name = plan_name
    elif available >= 1:
        name = plan_name[: available - 1] + "\u2026"
    else:
        name = ""
    return f"{prefix}{name}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict):
        raise ValueError("subscription must be a dict")
    if not isinstance(new_plan, dict):
        raise ValueError("new_plan must be a dict")
    for key in ("id", "status", "plan_name", "seat_price_cents", "billable_seats", "period_end"):
        if key not in subscription:
            raise ValueError(f"subscription is missing '{key}'")
    for key in ("name", "seat_price_cents"):
        if key not in new_plan:
            raise ValueError(f"new_plan is missing '{key}'")

    _require_aware("changed_at", changed_at)
    period_end = subscription["period_end"]
    _require_aware("period_end", period_end)

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    seats = subscription["billable_seats"]
    _require_int("seat_price_cents", old_price)
    _require_int("new_plan seat_price_cents", new_price)
    _require_int("billable_seats", seats)
    if not isinstance(subscription["status"], str):
        raise ValueError("status must be a string")
    if not isinstance(subscription["plan_name"], str):
        raise ValueError("plan_name must be a string")
    if not isinstance(new_plan["name"], str):
        raise ValueError("new_plan name must be a string")

    if subscription["status"] == "trialing":
        return []
    if new_price < old_price:
        return []
    if seats == 0:
        return []

    days_left = (period_end - changed_at) // timedelta(days=1)  # integer floor
    if days_left <= 0:
        return []
    days_left = min(days_left, PERIOD_DAYS)

    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)
    charge = (new_price * seats * days_left) // PERIOD_DAYS

    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    if credit >= MIN_LINE_CENTS:
        approver = SENIOR_APPROVER if credit > APPROVAL_THRESHOLD_CENTS else DEFAULT_APPROVER
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit: unused ", subscription["plan_name"], date_str),
            "approved_by": approver,
        })

    if charge >= MIN_LINE_CENTS:
        vat_id = subscription.get("vat_id")
        reverse_charge = bool(vat_id)
        vat = 0 if reverse_charge else (charge * VAT_RATE_PERCENT) // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description("Charge: unused ", new_plan["name"], date_str),
            "approved_by": None,
        })

    return lines


# ===== FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-n7ggtr8l/test_seat_proration.py =====

import copy
from datetime import datetime, timedelta, timezone

import pytest

from seat_proration import (
    DEFAULT_APPROVER,
    SENIOR_APPROVER,
    MIN_LINE_CENTS,
    prorate_seats,
)

UTC = timezone.utc
PERIOD_END = datetime(2026, 11, 1, tzinfo=UTC)


def sub(**kw):
    base = {
        "id": "sub_1", "status": "active", "plan_name": "Basic",
        "seat_price_cents": 1000, "seats": 10, "billable_seats": 5,
        "vat_id": None, "period_end": PERIOD_END,
    }
    base.update(kw)
    return base


def plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def at(days):
    return PERIOD_END - timedelta(days=days)


def test_worked_example():
    lines = prorate_seats(sub(), plan(), at(15))
    assert [l["kind"] for l in lines] == ["credit", "charge"]
    credit, charge = lines
    assert credit["amount_cents"] == 2500
    assert credit["vat_cents"] == 0
    assert credit["approved_by"] == DEFAULT_APPROVER == "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"
    assert charge["amount_cents"] == 5000
    assert charge["vat_cents"] == 1050
    assert charge["approved_by"] is None
    assert credit["description"] == "Credit: unused Basic until 2026-11-01"
    assert charge["description"] == "Charge: unused Pro until 2026-11-01"


def test_vat_id_reverse_charge():
    lines = prorate_seats(sub(vat_id="DE123"), plan(), at(15))
    assert lines[1]["vat_cents"] == 0


def test_empty_vat_id_means_vat():
    assert prorate_seats(sub(vat_id=""), plan(), at(15))[1]["vat_cents"] == 1050


def test_credit_rounds_up():
    # 333*7*3/30 = 233.1
    lines = prorate_seats(sub(seat_price_cents=333, billable_seats=7), plan(333), at(3))
    assert lines[0]["amount_cents"] == 234


def test_charge_rounds_down():
    # 1166*1*12/30 = 466.4
    lines = prorate_seats(sub(seat_price_cents=1166, billable_seats=1), plan(1166), at(12))
    assert lines[1]["amount_cents"] == 466


def test_downgrade_and_trialing():
    assert prorate_seats(sub(), plan(500), at(15)) == []
    assert prorate_seats(sub(status="trialing"), plan(), at(15)) == []


def test_equal_price_not_downgrade():
    assert len(prorate_seats(sub(), plan(1000), at(15))) == 2


def test_zero_billable_seats_and_expired():
    assert prorate_seats(sub(billable_seats=0), plan(), at(15)) == []
    assert prorate_seats(sub(), plan(), PERIOD_END) == []
    assert prorate_seats(sub(), plan(), PERIOD_END + timedelta(days=1)) == []
    assert prorate_seats(sub(), plan(), PERIOD_END - timedelta(hours=23)) == []


def test_days_left_clamped_to_30():
    a = prorate_seats(sub(), plan(), at(45))
    b = prorate_seats(sub(), plan(), at(30))
    assert a == b
    assert a[0]["amount_cents"] == 5000


def test_approval_boundary():
    at_limit = prorate_seats(sub(seat_price_cents=50000, billable_seats=1), plan(60000), at(30))
    assert at_limit[0]["amount_cents"] == 50000
    assert at_limit[0]["approved_by"] == DEFAULT_APPROVER
    over = prorate_seats(sub(seat_price_cents=50001, billable_seats=1), plan(60000), at(30))
    assert over[0]["amount_cents"] == 50001
    assert over[0]["approved_by"] == SENIOR_APPROVER == "Ram\u00f3n Etxeberria-Go\u00f1i"


def test_min_line_boundaries():
    assert MIN_LINE_CENTS == 50
    # credit 49 skipped, charge 49 skipped
    assert prorate_seats(sub(seat_price_cents=49, billable_seats=1), plan(49), at(30)) == []
    # credit 50 kept, charge 50 kept
    lines = prorate_seats(sub(seat_price_cents=50, billable_seats=1), plan(50), at(30))
    assert [l["amount_cents"] for l in lines] == [50, 50]
    # credit 10 skipped, charge 50 kept
    lines = prorate_seats(sub(seat_price_cents=10, billable_seats=1), plan(50), at(30))
    assert [l["kind"] for l in lines] == ["charge"]
    # independent: credit ceil(49.03)=50 kept, charge floor=49 skipped
    lines = prorate_seats(sub(seat_price_cents=1471, billable_seats=1), plan(1471), at(1))
    assert [l["kind"] for l in lines] == ["credit"]
    assert lines[0]["amount_cents"] == 50


def test_long_plan_name():
    name = "X" * 200
    lines = prorate_seats(sub(plan_name=name), plan(name=name), at(15))
    for l in lines:
        assert len(l["description"]) <= 80
        assert l["description"].endswith(" until 2026-11-01")
        assert "\u2026" in l["description"]


def test_description_fits_exactly_unchanged():
    prefix, suffix = "Credit: unused ", " until 2026-11-01"
    name = "N" * (80 - len(prefix) - len(suffix))
    lines = prorate_seats(sub(plan_name=name), plan(), at(15))
    assert lines[0]["description"] == prefix + name + suffix
    assert len(lines[0]["description"]) == 80


def test_ordering_and_subscription_id():
    lines = prorate_seats(sub(id="sub_xyz"), plan(), at(15))
    assert [l["kind"] for l in lines] == ["credit", "charge"]
    assert all(l["subscription_id"] == "sub_xyz" for l in lines)


def test_no_floats():
    for l in prorate_seats(sub(), plan(), at(15)):
        for v in l.values():
            assert not isinstance(v, float)
        assert type(l["amount_cents"]) is int
        assert type(l["vat_cents"]) is int


def test_naive_datetimes_rejected():
    with pytest.raises(ValueError):
        prorate_seats(sub(), plan(), datetime(2026, 10, 17))
    with pytest.raises(ValueError):
        prorate_seats(sub(period_end=datetime(2026, 11, 1)), plan(), at(15))


def test_invalid_data():
    with pytest.raises(ValueError):
        prorate_seats(sub(billable_seats=-1), plan(), at(15))
    with pytest.raises(ValueError):
        prorate_seats(sub(seat_price_cents=10.5), plan(), at(15))
    with pytest.raises(ValueError):
        prorate_seats({"id": 1}, plan(), at(15))


def test_inputs_not_mutated():
    s, p = sub(), plan()
    s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
    prorate_seats(s, p, at(15))
    assert s == s0 and p == p0


def test_legacy_discount_ignored_and_billable_used():
    a = prorate_seats(sub(legacy_discount=50, seats=999), plan(), at(15))
    b = prorate_seats(sub(), plan(), at(15))
    assert a == b
    assert a[0]["amount_cents"] == 2500