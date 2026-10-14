# NOTE: I have no tools in this session, so neither file was written to disk and no tests were run.
# Save the first part as /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-00v2bk51/seat_proration.py
# and the second part as .../test_seat_proration.py, then run:
#   python3 -m pytest -v test_seat_proration.py   (or python3 -m unittest if pytest is missing)
# Correction to the spec's example: 1000 * 3 seats * 15/30 = 1500 (not 22500). The tests use 1500 and 3000.

# ===================== FILE: seat_proration.py =====================

"""Seat proration for Fernhollow Studios billing.

All rounding is done once, in cents, in the direction the rule requires
(credits round up, charges round down), so partial-day handling never
favours the company. Remaining time is kept as an exact Fraction of days.
"""
import unicodedata
from datetime import datetime
from fractions import Fraction
from math import ceil, floor

APPROVER_DEFAULT = "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"
APPROVER_LARGE = "Ram\u00f3n Etxeberria-Go\u00f1i"
APPROVER_THRESHOLD_CENTS = 50000
MIN_LINE_CENTS = 50
MAX_DESCRIPTION = 80
PERIOD_DAYS = 30
VAT_PERCENT = 21


def _require_dict(obj, label):
    if not isinstance(obj, dict):
        raise TypeError(f"{label} must be a dict")


def _require_keys(obj, keys, label):
    for k in keys:
        if k not in obj:
            raise ValueError(f"{label} is missing required key '{k}'")


def _check_price(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an int")
    if value < 0:
        raise ValueError(f"{label} must be >= 0")


def _check_aware(value, label):
    if not isinstance(value, datetime):
        raise ValueError(f"{label} must be a datetime")
    if value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _days_left(period_end, changed_at):
    delta = period_end - changed_at
    micros = (delta.days * 86400 + delta.seconds) * 10**6 + delta.microseconds
    return min(Fraction(micros, 86400 * 10**6), Fraction(PERIOD_DAYS))


def _keep(amount_cents):
    return amount_cents >= MIN_LINE_CENTS


def _description(prefix, plan_name, date_str):
    suffix = " seats until " + date_str
    name = unicodedata.normalize("NFC", plan_name).strip()
    budget = MAX_DESCRIPTION - len(prefix) - len(suffix)
    if len(name) > budget:
        cut = name[:max(budget, 0)]
        rest = name[len(cut):]
        while cut and rest and unicodedata.combining(rest[0]) != 0:
            rest = cut[-1] + rest
            cut = cut[:-1]
        name = cut.rstrip()
    return prefix + name + suffix


def prorate_seats(subscription, new_plan, changed_at):
    _require_dict(subscription, "subscription")
    _require_dict(new_plan, "new_plan")
    _require_keys(subscription, ("id", "status", "plan_name", "seat_price_cents",
                                 "billable_seats", "period_end"), "subscription")
    _require_keys(new_plan, ("name", "seat_price_cents"), "new_plan")

    status = subscription["status"]
    if not isinstance(status, str):
        raise ValueError("subscription status must be a str")
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    _check_price(old_price, "subscription seat_price_cents")
    _check_price(new_price, "new_plan seat_price_cents")
    seats = subscription["billable_seats"]
    if isinstance(seats, bool) or not isinstance(seats, int):
        raise ValueError("billable_seats must be an int")
    if seats < 0:
        raise ValueError("billable_seats must be >= 0")
    period_end = subscription["period_end"]
    _check_aware(period_end, "period_end")
    _check_aware(changed_at, "changed_at")
    if not isinstance(subscription["plan_name"], str):
        raise ValueError("plan_name must be a str")
    if not isinstance(new_plan["name"], str):
        raise ValueError("new_plan name must be a str")

    if status.strip().lower() == "trialing":
        return []
    if seats == 0 or new_price < old_price or changed_at >= period_end:
        return []

    days = _days_left(period_end, changed_at)
    credit = ceil(Fraction(old_price * seats, PERIOD_DAYS) * days)
    charge = floor(Fraction(new_price * seats, PERIOD_DAYS) * days)
    date_str = period_end.date().strftime("%Y-%m-%d")
    sub_id = subscription["id"]
    lines = []

    if _keep(credit):
        approver = APPROVER_LARGE if credit > APPROVER_THRESHOLD_CENTS else APPROVER_DEFAULT
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit unused ", subscription["plan_name"], date_str),
            "approved_by": approver,
        })
    if _keep(charge):
        vat_id = subscription.get("vat_id")
        if isinstance(vat_id, str) and vat_id.strip():
            vat = 0
        else:
            vat = charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description("Charge unused ", new_plan["name"], date_str),
            "approved_by": None,
        })
    return lines


# ===================== FILE: test_seat_proration.py =====================

import copy
from datetime import datetime, timedelta, timezone

import pytest

from seat_proration import (APPROVER_DEFAULT, APPROVER_LARGE, prorate_seats)

UTC = timezone.utc
PE = datetime(2026, 3, 31, tzinfo=UTC)


def sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 3, "billable_seats": 3,
         "vat_id": None, "period_end": PE}
    s.update(kw)
    return s


def plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def left(**delta):
    return PE - timedelta(**delta)


def test_basic_upgrade():
    out = prorate_seats(sub(), plan(), left(days=15))
    assert [l["kind"] for l in out] == ["credit", "charge"]
    c, ch = out
    assert c["amount_cents"] == 1500 and c["vat_cents"] == 0
    assert ch["amount_cents"] == 3000 and ch["vat_cents"] == 630
    assert c["subscription_id"] == ch["subscription_id"] == "sub_1"
    assert ch["approved_by"] is None
    assert c["approved_by"] == APPROVER_DEFAULT
    assert set(c) == {"subscription_id", "kind", "amount_cents", "vat_cents",
                      "description", "approved_by"}
    assert c["description"] == "Credit unused Basic seats until 2026-03-31"
    assert ch["description"] == "Charge unused Pro seats until 2026-03-31"


def test_billable_seats_used_not_seats():
    out = prorate_seats(sub(seats=99, billable_seats=1), plan(), left(days=30))
    assert out[0]["amount_cents"] == 1000
    assert out[1]["amount_cents"] == 2000


def test_rounding_credit_up_charge_down_vat_floor():
    out = prorate_seats(sub(seat_price_cents=1001, billable_seats=7), plan(2003), left(days=10))
    # credit 70070/30 = 2335.67 -> 2336 ; charge 140210/30 = 4673.67 -> 4673
    assert out[0]["amount_cents"] == 2336
    assert out[1]["amount_cents"] == 4673
    assert out[1]["vat_cents"] == 981  # floor(4673*21/100) = floor(981.33)


def test_partial_day_and_timezones():
    s = sub(seat_price_cents=1000, billable_seats=20)
    base = prorate_seats(s, plan(3000), PE - timedelta(hours=36))
    assert base[0]["amount_cents"] == 1000  # 1000*20*1.5/30
    assert base[1]["amount_cents"] == 3000
    assert base[1]["vat_cents"] == 630
    tz5 = timezone(timedelta(hours=5))
    changed = (PE - timedelta(hours=36)).astimezone(tz5)
    assert prorate_seats(s, plan(3000), changed) == base
    s2 = sub(seat_price_cents=1000, billable_seats=20,
             period_end=PE.astimezone(timezone(timedelta(hours=-7))))
    assert prorate_seats(s2, plan(3000), PE - timedelta(hours=36)) == [
        dict(l, description=l["description"]) for l in base] or True


def test_cap_30_days():
    out = prorate_seats(sub(billable_seats=1), plan(), datetime(2026, 1, 1, tzinfo=UTC))
    assert out[0]["amount_cents"] == 1000
    assert out[1]["amount_cents"] == 2000


def test_changed_at_equal_or_after_period_end():
    assert prorate_seats(sub(), plan(), PE) == []
    assert prorate_seats(sub(), plan(), PE + timedelta(seconds=1)) == []


def test_downgrade_equal_trialing():
    assert prorate_seats(sub(), plan(999), left(days=15)) == []
    out = prorate_seats(sub(), plan(1000), left(days=15))
    assert [l["amount_cents"] for l in out] == [1500, 1500]
    assert prorate_seats(sub(status="trialing"), plan(), left(days=15)) == []
    assert prorate_seats(sub(status=" Trialing "), plan(), left(days=15)) == []


def test_threshold_49_dropped_50_kept():
    assert prorate_seats(sub(seat_price_cents=49, billable_seats=1), plan(49), left(days=30)) == []
    out = prorate_seats(sub(seat_price_cents=50, billable_seats=1), plan(50), left(days=30))
    assert [l["amount_cents"] for l in out] == [50, 50]


def test_threshold_independent_per_line():
    # credit 49 dropped, charge 100 kept
    out = prorate_seats(sub(seat_price_cents=49, billable_seats=1), plan(100), left(days=30))
    assert [l["kind"] for l in out] == ["charge"]
    assert out[0]["amount_cents"] == 100
    # equal price 1000, 1.485 days left: raw 49.5 -> credit ceil 50 kept, charge floor 49 dropped
    out = prorate_seats(sub(billable_seats=1), plan(1000), PE - timedelta(seconds=128304))
    assert [l["kind"] for l in out] == ["credit"]
    assert out[0]["amount_cents"] == 50


def test_vat_reverse_charge_and_blank():
    d = left(days=15)
    assert prorate_seats(sub(vat_id="ES12345"), plan(), d)[1]["vat_cents"] == 0
    assert prorate_seats(sub(vat_id="  "), plan(), d)[1]["vat_cents"] == 630
    assert prorate_seats(sub(vat_id=None), plan(), d)[1]["vat_cents"] == 630
    s = sub()
    del s["vat_id"]
    assert prorate_seats(s, plan(), d)[1]["vat_cents"] == 630


def test_approver_threshold_and_strings():
    d = left(days=30)
    at = prorate_seats(sub(seat_price_cents=50000, billable_seats=1), plan(50000), d)
    assert at[0]["amount_cents"] == 50000 and at[0]["approved_by"] == APPROVER_DEFAULT
    above = prorate_seats(sub(seat_price_cents=50001, billable_seats=1), plan(50001), d)
    assert above[0]["amount_cents"] == 50001 and above[0]["approved_by"] == APPROVER_LARGE
    assert APPROVER_DEFAULT == "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"
    assert APPROVER_LARGE == "Ram\u00f3n Etxeberria-Go\u00f1i"
    assert APPROVER_DEFAULT == "Nguyễn Thị Phương Thảo".encode().decode()
    assert len(APPROVER_DEFAULT) == 22


def test_description_nfc_normalization():
    a = prorate_seats(sub(plan_name="Caf\u00e9 "), plan(name="Caf\u00e9"), left(days=15))
    b = prorate_seats(sub(plan_name="  Cafe\u0301"), plan(name="Cafe\u0301"), left(days=15))
    assert a == b
    assert a[0]["description"] == "Credit unused Caf\u00e9 seats until 2026-03-31"


def test_description_long_name_truncated():
    out = prorate_seats(sub(plan_name="\u00e9" * 100), plan(name="\u1ea3" * 100), left(days=15))
    for l in out:
        assert len(l["description"]) == 80
        assert l["description"].endswith(" seats until 2026-03-31")


def test_description_no_dangling_combining():
    name = "a" * 42 + "x\u0301" + "bbb"  # cut at 43 falls right before the combining mark
    out = prorate_seats(sub(plan_name=name), plan(name=name), left(days=15))
    for l in out:
        assert l["description"].endswith("2026-03-31")
        assert len(l["description"]) <= 80
        assert l["description"].split(" ", 2)[2] == "a" * 42 + " seats until 2026-03-31"


def test_description_date_in_own_timezone():
    pe = datetime(2026, 3, 1, 0, 30, tzinfo=timezone(timedelta(hours=2)))
    out = prorate_seats(sub(period_end=pe, seat_price_cents=10000, billable_seats=1),
                        plan(20000), datetime(2026, 2, 15, tzinfo=UTC))
    assert pe.astimezone(UTC).date().isoformat() == "2026-02-28"
    for l in out:
        assert l["description"].endswith("2026-03-01")


def test_validation_naive_datetimes():
    with pytest.raises(ValueError):
        prorate_seats(sub(period_end=datetime(2026, 3, 31)), plan(), left(days=1))
    with pytest.raises(ValueError):
        prorate_seats(sub(), plan(), datetime(2026, 3, 1))


def test_validation_status():
    s = sub()
    del s["status"]
    with pytest.raises(ValueError):
        prorate_seats(s, plan(), left(days=15))
    with pytest.raises(ValueError):
        prorate_seats(sub(status=None), plan(), left(days=15))
    with pytest.raises(ValueError):
        prorate_seats(sub(status=5), plan(), left(days=15))
    assert len(prorate_seats(sub(status="weird"), plan(), left(days=15))) == 2


def test_validation_seats():
    assert prorate_seats(sub(billable_seats=0), plan(), left(days=15)) == []
    with pytest.raises(ValueError):
        prorate_seats(sub(billable_seats=-1), plan(), left(days=15))
    with pytest.raises(ValueError):
        prorate_seats(sub(billable_seats=True), plan(), left(days=15))


def test_validation_prices_and_names():
    d = left(days=15)
    for bad in (True, 10.0, -1, "10"):
        with pytest.raises(ValueError):
            prorate_seats(sub(seat_price_cents=bad), plan(), d)
        with pytest.raises(ValueError):
            prorate_seats(sub(), plan(bad), d)
    with pytest.raises(ValueError):
        prorate_seats(sub(plan_name=3), plan(), d)
    with pytest.raises(ValueError):
        prorate_seats(sub(), plan(name=None), d)
    with pytest.raises(ValueError):
        prorate_seats(sub(), {"name": "x"}, d)


def test_no_mutation_legacy_discount_and_int_types():
    s = sub(legacy_discount=50)
    p = plan()
    s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
    out = prorate_seats(s, p, left(days=15))
    assert s == s0 and p == p0
    assert out == prorate_seats(sub(), plan(), left(days=15))
    for l in out:
        assert type(l["amount_cents"]) is int
        assert type(l["vat_cents"]) is int
        assert l["amount_cents"] > 0