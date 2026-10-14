# Fernhollow Studios billing: prorate_seats, with pytest tests in the same file.
# Save as billing.py (pytest also collects the test_* functions below).
# NOT EXECUTED: this environment had no tools, so the tests have not been run.
# Assumptions: month-end style template wording below; 80-char limit counts code points;
# a non-string vat_id (e.g. None) counts as "no VAT id"; time-left > 30 days raises
# ValueError only after the early-return checks (R20 order); fractions use microsecond-exact integer math.

import unicodedata
from datetime import datetime, timedelta, timezone

PERIOD_DAYS = 30
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
APPROVAL_THRESHOLD_CENTS = 50000
MAX_DESCRIPTION = 80
CREDIT_TEMPLATE = "Credit unused {plan} seats to {date}"
CHARGE_TEMPLATE = "Charge new {plan} seats to {date}"
APPROVER_LOW = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
APPROVER_HIGH = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")
TRIALING = "trialing"

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def _require(d, keys, label):
    if not isinstance(d, dict):
        raise ValueError(f"{label} must be a dict")
    for k in keys:
        if k not in d:
            raise ValueError(f"{label} missing required key: {k}")


def _int(v, label):
    if isinstance(v, bool) or not isinstance(v, int):
        raise TypeError(f"{label} must be an int")
    return v


def _aware(v, label):
    if not isinstance(v, datetime) or v.tzinfo is None or v.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")
    return v


def _describe(template, plan, date_str):
    plan = str(plan)
    avail = MAX_DESCRIPTION - len(template.format(plan="", date=date_str))
    if len(plan) > avail:
        plan = (plan[:avail - 1].rstrip() + "…") if avail >= 1 else ""
    return template.format(plan=plan, date=date_str).rstrip()


def prorate_seats(subscription, new_plan, changed_at):
    _require(subscription, _SUB_KEYS, "subscription")
    _require(new_plan, _PLAN_KEYS, "new_plan")
    old_price = _int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    seats = _int(subscription["billable_seats"], "billable_seats")
    if seats < 0:
        raise ValueError("billable_seats must not be negative")
    _aware(changed_at, "changed_at")
    period_end = _aware(subscription["period_end"], "period_end")

    if subscription["status"] == TRIALING:
        return []
    if new_price < old_price:
        return []
    if changed_at >= period_end:
        return []
    micros = (period_end - changed_at) // timedelta(microseconds=1)
    den = PERIOD_DAYS * 86400 * 1_000_000
    if micros > den:
        raise ValueError("more than 30 days left in period")
    if seats == 0:
        return []

    date_str = period_end.date().isoformat()
    sid = subscription["id"]
    out = []

    credit = -(-(old_price * seats * micros) // den)
    if credit >= MIN_LINE_CENTS:
        out.append({
            "subscription_id": sid,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe(CREDIT_TEMPLATE, subscription["plan_name"], date_str),
            "approved_by": APPROVER_LOW if credit <= APPROVAL_THRESHOLD_CENTS else APPROVER_HIGH,
        })

    charge = (new_price * seats * micros) // den
    if charge >= MIN_LINE_CENTS:
        vat_id = subscription["vat_id"]
        reverse = isinstance(vat_id, str) and vat_id.strip() != ""
        out.append({
            "subscription_id": sid,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * VAT_PERCENT // 100,
            "description": _describe(CHARGE_TEMPLATE, new_plan["name"], date_str),
            "approved_by": None,
        })
    return out


# ----------------------------- tests -----------------------------

import copy
import pytest

_END = datetime(2026, 11, 30, 12, 0, tzinfo=timezone.utc)


def _sub(**kw):
    s = dict(id="s1", status="active", plan_name="Basic", seat_price_cents=1000,
             seats=10, billable_seats=10, vat_id=None, period_end=_END)
    s.update(kw)
    return s


def _at(days):
    return _END - timedelta(days=days)


def _plan(price, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def test_e1():
    c, ch = prorate_seats(_sub(), _plan(1500), _at(15))
    assert (c["kind"], c["amount_cents"], c["vat_cents"], c["approved_by"]) == ("credit", 5000, 0, APPROVER_LOW)
    assert (ch["kind"], ch["amount_cents"], ch["vat_cents"], ch["approved_by"]) == ("charge", 7500, 1575, None)
    assert set(c) == {"subscription_id", "kind", "amount_cents", "vat_cents", "description", "approved_by"}
    assert "2026-11-30" in c["description"] and "Basic" in c["description"]
    assert "Pro" in ch["description"]


def test_e2_reverse_charge():
    assert prorate_seats(_sub(vat_id=" NL123 "), _plan(1500), _at(15))[1]["vat_cents"] == 0
    assert prorate_seats(_sub(vat_id="  "), _plan(1500), _at(15))[1]["vat_cents"] == 1575


def test_e3_rounding():
    c, ch = prorate_seats(_sub(seat_price_cents=1001, billable_seats=1), _plan(1501), _at(10))
    assert c["amount_cents"] == 334 and ch["amount_cents"] == 500 and ch["vat_cents"] == 105


def test_e4_e5_empty():
    assert prorate_seats(_sub(), _plan(900), _at(15)) == []
    assert prorate_seats(_sub(status="trialing"), _plan(1500), _at(15)) == []


def test_e6_approver():
    c = prorate_seats(_sub(seat_price_cents=10000, billable_seats=5), _plan(12000), _at(30))[0]
    assert c["amount_cents"] == 50000 and c["approved_by"] == APPROVER_LOW
    c = prorate_seats(_sub(seat_price_cents=10001, billable_seats=5), _plan(12000), _at(30))[0]
    assert c["amount_cents"] == 50005 and c["approved_by"] == "Ramón Etxeberria-Goñi"


def test_e7_threshold():
    # 30 days left, 1 seat: amount equals price
    r = prorate_seats(_sub(seat_price_cents=40, billable_seats=1), _plan(50), _at(30))
    assert [x["kind"] for x in r] == ["charge"]
    r = prorate_seats(_sub(seat_price_cents=49, billable_seats=1), _plan(49), _at(30))
    assert r == []
    r = prorate_seats(_sub(seat_price_cents=50, billable_seats=1), _plan(50), _at(30))
    assert [x["kind"] for x in r] == ["credit", "charge"]


def test_e8_billable_only():
    r = prorate_seats(_sub(seats=20, billable_seats=12), _plan(1500), _at(15))
    assert r[0]["amount_cents"] == 6000
    with pytest.raises(ValueError):
        s = _sub()
        del s["billable_seats"]
        prorate_seats(s, _plan(1500), _at(15))


def test_e9_long_name():
    r = prorate_seats(_sub(plan_name="X" * 200), _plan(1500, "Y" * 200), _at(15))
    for line in r:
        assert len(line["description"]) <= 80
        assert line["description"].endswith("2026-11-30")


def test_validation_and_bounds():
    with pytest.raises(ValueError):
        prorate_seats(_sub(), _plan(1500), datetime(2026, 11, 1))
    with pytest.raises(TypeError):
        prorate_seats(_sub(billable_seats=True), _plan(1500), _at(5))
    with pytest.raises(TypeError):
        prorate_seats(_sub(seat_price_cents=10.0), _plan(1500), _at(5))
    with pytest.raises(ValueError):
        prorate_seats(_sub(billable_seats=-1), _plan(1500), _at(5))
    with pytest.raises(ValueError):
        prorate_seats(_sub(), _plan(1500), _at(31))
    assert prorate_seats(_sub(billable_seats=0), _plan(1500), _at(5)) == []
    assert prorate_seats(_sub(), _plan(1500), _END) == []


def test_legacy_discount_ignored_and_no_mutation():
    base = prorate_seats(_sub(), _plan(1500), _at(15))
    s = _sub(legacy_discount=50)
    p = _plan(1500)
    s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
    assert prorate_seats(s, p, _at(15)) == base
    assert s == s0 and p == p0
    for line in base:
        assert type(line["amount_cents"]) is int and type(line["vat_cents"]) is int
```