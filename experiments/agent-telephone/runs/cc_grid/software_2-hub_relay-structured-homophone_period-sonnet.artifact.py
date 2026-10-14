"""Fernhollow Studios seat proration.

NOTE: I had no tool access, so the tests embedded below (pytest style, run with
`pytest <this file>`) have NOT been executed.

Open questions for the client:
1. Is the 13-day billing period correct (BILLING_PERIOD_DAYS)?
2. Full 24h days (current, R15) or calendar-date differences?
3. Should credits be positive or negative in the ledger (currently non-negative
   magnitude, with kind carrying the direction)?
4. Same-price handling: equal price with a different plan name is processed
   normally, and with the same name it returns []. Is that right?
5. Should statuses other than "trialing" (e.g. canceled, past_due) be excluded?
"""
from datetime import datetime, timedelta

BILLING_PERIOD_DAYS = 13  # client to confirm

_MAX_DESC = 80
_MIN_LINE_CENTS = 50
_APPROVER = "Nguyễn Thị Phương Thảo"
_APPROVER_HIGH = "Ramón Etxeberria-Goñi"
_HIGH_THRESHOLD = 50000
_VAT_PERCENT = 21

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def _check_int(value):
    if type(value) is not int:
        raise TypeError("expected int, got %s" % type(value).__name__)
    if value < 0:
        raise ValueError("negative value not allowed")


def _check_dt(value):
    if not isinstance(value, datetime):
        raise TypeError("expected datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("naive datetime not allowed")


def _validate(subscription, new_plan, changed_at):
    for k in _SUB_KEYS:
        if k not in subscription:
            raise KeyError(k)
    for k in _PLAN_KEYS:
        if k not in new_plan:
            raise KeyError(k)
    _check_dt(changed_at)
    _check_dt(subscription["period_end"])
    for v in (subscription["seat_price_cents"], subscription["seats"],
              subscription["billable_seats"], new_plan["seat_price_cents"]):
        _check_int(v)


def _description(prefix, name, end_date):
    suffix = " until " + end_date
    budget = _MAX_DESC - len(prefix) - len(suffix)
    if len(name) > budget:
        name = name[:max(budget - 3, 0)] + "..."
    return prefix + name + suffix


def prorate_seats(subscription, new_plan, changed_at):
    _validate(subscription, new_plan, changed_at)

    if subscription["status"] == "trialing":
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []
    old_name = subscription["plan_name"]
    new_name = new_plan["name"]
    if new_price == old_price and old_name == new_name:
        return []
    seats = subscription["billable_seats"]
    if seats == 0:
        return []

    period_end = subscription["period_end"]
    delta = period_end - changed_at
    if delta <= timedelta(0):
        return []
    days_left = min(delta // timedelta(days=1), BILLING_PERIOD_DAYS)
    if days_left <= 0:
        return []

    end_date = period_end.date().isoformat()
    sid = subscription["id"]
    lines = []

    # Credit first (priority).
    credit = -(-(old_price * seats * days_left) // BILLING_PERIOD_DAYS)
    if credit >= _MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sid,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit unused ", old_name, end_date),
            "approved_by": _APPROVER_HIGH if credit > _HIGH_THRESHOLD else _APPROVER,
        })

    charge = (new_price * seats * days_left) // BILLING_PERIOD_DAYS
    if charge >= _MIN_LINE_CENTS:
        vat_id = subscription["vat_id"]
        has_vat_id = isinstance(vat_id, str) and vat_id.strip() != ""
        vat = 0 if has_vat_id else (charge * _VAT_PERCENT) // 100
        lines.append({
            "subscription_id": sid,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description("Charge unused ", new_name, end_date),
            "approved_by": None,
        })
    return lines


# ----------------------------- tests -----------------------------
import copy
from datetime import timezone

import pytest

_NOW = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)


def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 9, "billable_seats": 5,
         "vat_id": None, "period_end": _NOW + timedelta(days=6)}
    s.update(kw)
    return s


def _plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def test_worked_example():
    out = prorate_seats(_sub(), _plan(), _NOW)
    assert [l["kind"] for l in out] == ["credit", "charge"]
    c, ch = out
    assert (c["amount_cents"], c["vat_cents"], c["approved_by"]) == (2308, 0, "Nguyễn Thị Phương Thảo")
    assert (ch["amount_cents"], ch["vat_cents"], ch["approved_by"]) == (4615, 969, None)
    assert c["description"] == "Credit unused Basic until 2026-03-07"
    assert ch["description"] == "Charge unused Pro until 2026-03-07"
    assert set(c) == {"subscription_id", "kind", "amount_cents", "vat_cents",
                      "description", "approved_by"}
    assert all(type(l["amount_cents"]) is int and type(l["vat_cents"]) is int for l in out)


def test_vat_id_zero_vat():
    out = prorate_seats(_sub(vat_id=" NL123 "), _plan(), _NOW)
    assert out[1]["vat_cents"] == 0
    out = prorate_seats(_sub(vat_id="   "), _plan(), _NOW)
    assert out[1]["vat_cents"] == 969


def test_downgrade_and_trialing():
    assert prorate_seats(_sub(), _plan(500), _NOW) == []
    assert prorate_seats(_sub(status="trialing"), _plan(), _NOW) == []


def test_other_statuses_prorated():
    assert len(prorate_seats(_sub(status="past_due"), _plan(), _NOW)) == 2


def test_same_price():
    assert prorate_seats(_sub(), _plan(1000, "Basic"), _NOW) == []
    assert len(prorate_seats(_sub(), _plan(1000, "Other"), _NOW)) == 2


def test_period_end_reached():
    assert prorate_seats(_sub(period_end=_NOW), _plan(), _NOW) == []
    assert prorate_seats(_sub(period_end=_NOW - timedelta(days=1)), _plan(), _NOW) == []


def test_zero_billable_seats():
    assert prorate_seats(_sub(billable_seats=0), _plan(), _NOW) == []


def _one_day(old, new):
    return prorate_seats(_sub(seat_price_cents=old, billable_seats=1,
                              period_end=_NOW + timedelta(days=1)), _plan(new), _NOW)


def test_credit_boundary():
    assert [l["kind"] for l in _one_day(637, 2000)] == ["charge"]  # credit 49
    out = _one_day(650, 2000)  # credit 50
    assert out[0]["kind"] == "credit" and out[0]["amount_cents"] == 50


def test_charge_boundary():
    assert _one_day(100, 637) == []  # charge 49, credit 8
    out = _one_day(100, 650)
    assert len(out) == 1 and out[0]["kind"] == "charge" and out[0]["amount_cents"] == 50


def test_credit_approval_threshold():
    def run(p):
        s = _sub(seat_price_cents=p, billable_seats=1,
                 period_end=_NOW + timedelta(days=13))
        return prorate_seats(s, _plan(p + 10000), _NOW)[0]
    assert run(50000)["amount_cents"] == 50000
    assert run(50000)["approved_by"] == "Nguyễn Thị Phương Thảo"
    assert run(50001)["approved_by"] == "Ramón Etxeberria-Goñi"


def test_days_clamp():
    a = prorate_seats(_sub(period_end=_NOW + timedelta(days=13)), _plan(), _NOW)
    b = prorate_seats(_sub(period_end=_NOW + timedelta(days=40)), _plan(), _NOW)
    assert [l["amount_cents"] for l in a] == [l["amount_cents"] for l in b]
    assert a[0]["amount_cents"] == 5000


def test_long_plan_name():
    name = "X" * 100
    out = prorate_seats(_sub(plan_name=name), _plan(name="Y" * 100), _NOW)
    for l in out:
        assert len(l["description"]) <= 80
        assert l["description"].endswith(" until 2026-03-07")
        assert "..." in l["description"]


def test_legacy_discount_and_seats_ignored():
    base = prorate_seats(_sub(), _plan(), _NOW)
    assert prorate_seats(_sub(legacy_discount=50, seats=100), _plan(), _NOW) == base


def test_no_mutation():
    s, p = _sub(), _plan()
    s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
    prorate_seats(s, p, _NOW)
    assert s == s0 and p == p0


def test_validation():
    with pytest.raises(ValueError):
        prorate_seats(_sub(), _plan(), _NOW.replace(tzinfo=None))
    with pytest.raises(ValueError):
        prorate_seats(_sub(period_end=datetime(2026, 3, 7)), _plan(), _NOW)
    s = _sub()
    del s["vat_id"]
    with pytest.raises(KeyError):
        prorate_seats(s, _plan(), _NOW)
    for bad in (1000.0, True):
        with pytest.raises(TypeError):
            prorate_seats(_sub(seat_price_cents=bad), _plan(), _NOW)
    with pytest.raises(TypeError):
        prorate_seats(_sub(billable_seats=5.0), _plan(), _NOW)
    with pytest.raises(ValueError):
        prorate_seats(_sub(billable_seats=-1), _plan(), _NOW)
    with pytest.raises(ValueError):
        prorate_seats(_sub(), _plan(-5), _NOW)