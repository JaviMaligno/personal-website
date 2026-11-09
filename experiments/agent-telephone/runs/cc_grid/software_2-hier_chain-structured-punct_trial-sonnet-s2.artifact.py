# ===== /billing_proration.py =====
```
"""Fernhollow Studios billing: seat proration on plan change."""
from datetime import datetime

_PERIOD_DAYS = 30
_DAY = 86400
_MAX_DESC = 80
_APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
_APPROVER_HIGH = "Ramón Etxeberria-Goñi"
_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def _check_int(value, label):
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative int")


def _check_aware(value, label):
    if not isinstance(value, datetime):
        raise ValueError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _validate(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise ValueError("subscription and new_plan must be dicts")
    for k in _SUB_KEYS:
        if k not in subscription:
            raise ValueError(f"subscription missing key: {k}")
    for k in _PLAN_KEYS:
        if k not in new_plan:
            raise ValueError(f"new_plan missing key: {k}")
    _check_int(subscription["seat_price_cents"], "seat_price_cents")
    _check_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    _check_int(subscription["billable_seats"], "billable_seats")
    _check_aware(changed_at, "changed_at")
    _check_aware(subscription["period_end"], "period_end")


def _describe(template, plan, date_str):
    plan = str(plan)
    full = template.format(plan=plan, date=date_str)
    if len(full) <= _MAX_DESC:
        return full
    overhead = len(template.format(plan="", date=date_str))
    keep = _MAX_DESC - overhead - 1
    short = plan[:keep] + "…" if keep > 0 else "…"
    return template.format(plan=short, date=date_str)


def prorate_seats(subscription, new_plan, changed_at):
    _validate(subscription, new_plan, changed_at)

    if subscription["status"] == "trialing":
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    delta = period_end - changed_at
    remaining = delta.days * _DAY + delta.seconds  # microseconds floored away
    if remaining <= 0:
        return []
    remaining = min(remaining, _PERIOD_DAYS * _DAY)

    credit_days = min(_PERIOD_DAYS, -(-remaining // _DAY))
    charge_days = min(_PERIOD_DAYS, remaining // _DAY)

    seats = subscription["billable_seats"]
    credit = -(-(old_price * seats * credit_days) // _PERIOD_DAYS)
    charge = (new_price * seats * charge_days) // _PERIOD_DAYS

    vat_id = subscription["vat_id"]
    reverse_charge = isinstance(vat_id, str) and vat_id.strip() != ""
    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]

    lines = []
    if credit >= 50:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe(
                "Credit: unused {plan}, period ends {date}",
                subscription["plan_name"], date_str),
            "approved_by": _APPROVER_HIGH if credit > 50000
            else _APPROVER_DEFAULT,
        })
    if charge >= 50:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse_charge else charge * 21 // 100,
            "description": _describe(
                "Charge: {plan} remaining term, period ends {date}",
                new_plan["name"], date_str),
            "approved_by": None,
        })
    return lines
```

# ===== /test_billing_proration.py =====
```
# Note: tests could not be executed in this environment (no tools available).
import copy
import unicodedata
from datetime import datetime, timedelta, timezone

import pytest

from billing_proration import prorate_seats

UTC = timezone.utc
END = datetime(2030, 1, 31, 0, 0, tzinfo=UTC)


def sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 5, "billable_seats": 3,
         "vat_id": None, "period_end": END}
    s.update(kw)
    return s


def plan(price=1500, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def at(days=0, seconds=0):
    return END - timedelta(days=days, seconds=seconds)


def test_R3_keys_and_R16_order():
    out = prorate_seats(sub(), plan(), at(15))
    assert [l["kind"] for l in out] == ["credit", "charge"]
    for l in out:
        assert set(l) == {"subscription_id", "kind", "amount_cents",
                          "vat_cents", "description", "approved_by"}
        assert l["subscription_id"] == "sub_1"


def test_R5_uses_billable_seats():
    out = prorate_seats(sub(seats=100, billable_seats=3), plan(), at(15))
    assert out[0]["amount_cents"] == 1500
    assert out[1]["amount_cents"] == 2250


def test_R6_example():
    out = prorate_seats(sub(), plan(), at(15))
    assert out[0]["amount_cents"] == 1500
    assert out[1]["amount_cents"] == 2250
    assert out[1]["vat_cents"] == 472  # R10 + floor of 472.5
    assert out[0]["vat_cents"] == 0  # R11
    assert out[1]["approved_by"] is None


def test_R7_downgrade():
    assert prorate_seats(sub(), plan(999), at(15)) == []


def test_R8_rounding():
    out = prorate_seats(sub(seat_price_cents=1001, billable_seats=1),
                        plan(1501), at(15))
    assert out[0]["amount_cents"] == 501  # 500.5 up
    assert out[1]["amount_cents"] == 750  # 750.5 down
    assert out[1]["vat_cents"] == 157


def test_R9_boundaries():
    assert prorate_seats(sub(seat_price_cents=49, billable_seats=1),
                         plan(49), at(30)) == []
    out = prorate_seats(sub(seat_price_cents=50, billable_seats=1),
                        plan(50), at(30))
    assert [l["amount_cents"] for l in out] == [50, 50]


def test_R9_one_line_skipped_other_kept():
    # credit 50 kept (30 days ceil), charge 50*29//30 = 48 skipped
    out = prorate_seats(sub(seat_price_cents=50, billable_seats=1),
                        plan(50), at(29, 1))
    assert [l["kind"] for l in out] == ["credit"]
    out = prorate_seats(sub(seat_price_cents=49, billable_seats=1),
                        plan(100), at(30))
    assert [l["kind"] for l in out] == ["charge"]


def test_R10_vat_id_reverse_charge():
    out = prorate_seats(sub(vat_id="DE123"), plan(), at(15))
    assert out[1]["vat_cents"] == 0


@pytest.mark.parametrize("v", [None, "", "   "])
def test_R10_blank_vat_id_means_vat(v):
    out = prorate_seats(sub(vat_id=v), plan(), at(15))
    assert out[1]["vat_cents"] == 472


def test_R12_trialing():
    assert prorate_seats(sub(status="trialing"), plan(), at(15)) == []


def test_D3_past_due_prorated():
    assert len(prorate_seats(sub(status="past_due"), plan(), at(15))) == 2


def test_R13_long_names():
    out = prorate_seats(sub(plan_name="X" * 200), plan(name="Y" * 100), at(15))
    for l in out:
        assert len(l["description"]) <= 80
        assert l["description"].endswith("2030-01-31")
        assert l["description"].count("…") == 1


def test_R4_description_formats():
    out = prorate_seats(sub(), plan(), at(15))
    assert out[0]["description"] == "Credit: unused Basic, period ends 2030-01-31"
    assert out[1]["description"] == "Charge: Pro remaining term, period ends 2030-01-31"


def test_R14_approvers():
    a = "Nguyễn Thị Phương Thảo"
    b = "Ramón Etxeberria-Goñi"
    assert unicodedata.is_normalized("NFC", a)
    assert unicodedata.is_normalized("NFC", b)
    lo = prorate_seats(sub(seat_price_cents=50000, billable_seats=1),
                       plan(60000), at(30))
    hi = prorate_seats(sub(seat_price_cents=50001, billable_seats=1),
                       plan(60000), at(30))
    assert lo[0]["amount_cents"] == 50000 and lo[0]["approved_by"] == a
    assert hi[0]["amount_cents"] == 50001 and hi[0]["approved_by"] == b


def test_R17_ints():
    for l in prorate_seats(sub(), plan(), at(15)):
        assert type(l["amount_cents"]) is int
        assert type(l["vat_cents"]) is int


def test_R18_legacy_discount_ignored():
    a = prorate_seats(sub(), plan(), at(15))
    b = prorate_seats(sub(legacy_discount=50), plan(), at(15))
    assert a == b


def test_D2_partial_day():
    out = prorate_seats(sub(seat_price_cents=3000, billable_seats=1),
                        plan(3000), at(10, 1))
    assert out[0]["amount_cents"] == 1100  # 11 days
    assert out[1]["amount_cents"] == 1000  # 10 days


def test_D3_past_and_far_early():
    assert prorate_seats(sub(), plan(), END) == []
    assert prorate_seats(sub(), plan(), END + timedelta(days=1)) == []
    out = prorate_seats(sub(), plan(), at(100))
    assert out[0]["amount_cents"] == 3000
    assert out[1]["amount_cents"] == 4500


def test_D4_equal_price():
    assert len(prorate_seats(sub(), plan(1000), at(15))) == 2


def test_D7_value_errors():
    with pytest.raises(ValueError):
        prorate_seats(sub(), plan(), datetime(2030, 1, 1))
    with pytest.raises(ValueError):
        prorate_seats(sub(period_end=datetime(2030, 1, 31)), plan(), at(1))
    with pytest.raises(ValueError):
        prorate_seats(sub(seat_price_cents=-1), plan(), at(1))
    with pytest.raises(ValueError):
        prorate_seats(sub(), plan(-1), at(1))
    with pytest.raises(ValueError):
        prorate_seats(sub(billable_seats=True), plan(), at(1))
    with pytest.raises(ValueError):
        prorate_seats(sub(billable_seats=2.0), plan(), at(1))
    with pytest.raises(ValueError):
        prorate_seats(sub(period_end="2030-01-31"), plan(), at(1))
    s = sub()
    del s["vat_id"]
    with pytest.raises(ValueError):
        prorate_seats(s, plan(), at(1))
    # validation precedes trialing short-circuit
    with pytest.raises(ValueError):
        prorate_seats(sub(status="trialing", billable_seats=-1), plan(), at(1))


def test_period_end_own_timezone_date():
    tz = timezone(timedelta(hours=5))
    pe = datetime(2030, 2, 1, 2, 0, tzinfo=tz)  # 2030-01-31 21:00 UTC
    out = prorate_seats(sub(period_end=pe), plan(), pe - timedelta(days=15))
    assert all(l["description"].endswith("2030-02-01") for l in out)


def test_non_mutation():
    s, p = sub(), plan()
    s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
    prorate_seats(s, p, at(15))
    assert s == s0 and p == p0
```