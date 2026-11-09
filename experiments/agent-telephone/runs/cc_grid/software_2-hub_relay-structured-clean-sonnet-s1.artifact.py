"""Fernhollow Studios seat proration (module: prorate_seats.py; save as test-collectable, e.g. run `pytest prorate_seats.py`).

NOTE: I had no tools in this run, so the tests below were written but NOT executed.

Provisional defaults used (not confirmed with client):
 - description templates; days_left rule (calendar days in period_end's tz, clamped 0..30)
 - equal price is prorated; non-trialing statuses are prorated
 - charge VAT 21% rounded down; validation rules (R15)
 - vat_id is treated as a required key (value may be None or ""); "seats" is not required
If scope must be cut, VAT is deferred first; credit correctness takes priority.
"""
from datetime import datetime, timedelta, timezone
import unicodedata

VAT_RATE_PERCENT = 21
PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
MAX_DESCRIPTION_LEN = 80
APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
APPROVER_SENIOR = "Ramón Etxeberria-Goñi"
APPROVAL_THRESHOLD_CENTS = 50000

_REQUIRED_SUB = ("id", "status", "plan_name", "seat_price_cents",
                 "billable_seats", "vat_id", "period_end")


def _check_int(value, label):
    if type(value) is not int:
        raise TypeError(f"{label} must be int")
    if value < 0:
        raise ValueError(f"{label} must be >= 0")


def _check_aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _description(prefix, name, date_str):
    suffix = f" until {date_str}"
    if len(prefix) + len(name) + len(suffix) > MAX_DESCRIPTION_LEN:
        name = unicodedata.normalize("NFC", name)
        room = MAX_DESCRIPTION_LEN - len(prefix) - len(suffix)
        if len(name) > room:
            name = name[:max(room - 1, 0)] + "…"
    return f"{prefix}{name}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise TypeError("subscription and new_plan must be dicts")
    for k in _REQUIRED_SUB:
        if k not in subscription:
            raise ValueError(f"missing subscription key: {k}")
    for k in ("name", "seat_price_cents"):
        if k not in new_plan:
            raise ValueError(f"missing new_plan key: {k}")
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    seats = subscription["billable_seats"]
    _check_int(old_price, "seat_price_cents")
    _check_int(new_price, "new seat_price_cents")
    _check_int(seats, "billable_seats")
    if not isinstance(subscription["plan_name"], str) or not isinstance(new_plan["name"], str):
        raise TypeError("plan names must be str")
    period_end = subscription["period_end"]
    _check_aware(period_end, "period_end")
    _check_aware(changed_at, "changed_at")

    if subscription["status"] == "trialing":
        return []
    if new_price < old_price:
        return []
    if seats == 0:
        return []

    end_date = period_end.date()
    days_left = (end_date - changed_at.astimezone(period_end.tzinfo).date()).days
    days_left = min(days_left, PERIOD_DAYS)
    if days_left <= 0:
        return []

    date_str = end_date.isoformat()
    sid = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sid,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit unused ", subscription["plan_name"], date_str),
            "approved_by": (APPROVER_SENIOR if credit > APPROVAL_THRESHOLD_CENTS
                            else APPROVER_DEFAULT),
        })

    charge = (new_price * seats * days_left) // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        vat = 0 if subscription["vat_id"] else charge * VAT_RATE_PERCENT // 100
        lines.append({
            "subscription_id": sid,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description("Charge unused ", new_plan["name"], date_str),
            "approved_by": None,
        })
    return lines


# ----------------------------- tests -----------------------------
try:
    import pytest
except ImportError:  # pragma: no cover
    pytest = None

_END = datetime(2025, 3, 31, tzinfo=timezone.utc)


def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 99, "billable_seats": 4,
         "vat_id": None, "period_end": _END}
    s.update(kw)
    return s


def _at(days):
    return _END - timedelta(days=days)


def _new(price=1500, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def test_example_and_shape():
    out = prorate_seats(_sub(), _new(), _at(15))
    assert [l["kind"] for l in out] == ["credit", "charge"]
    c, ch = out
    assert (c["amount_cents"], c["vat_cents"], c["approved_by"]) == (2000, 0, "Nguyễn Thị Phương Thảo")
    assert (ch["amount_cents"], ch["vat_cents"], ch["approved_by"]) == (3000, 630, None)
    assert set(c) == {"subscription_id", "kind", "amount_cents", "vat_cents",
                      "description", "approved_by"}
    assert c["subscription_id"] == "sub_1"
    assert c["description"] == "Credit unused Basic until 2025-03-31"
    assert ch["description"] == "Charge unused Pro until 2025-03-31"
    assert all(type(l["amount_cents"]) is int and type(l["vat_cents"]) is int for l in out)


def test_billable_seats_not_seats():
    out = prorate_seats(_sub(seats=1000), _new(), _at(15))
    assert out[0]["amount_cents"] == 2000
    s = _sub()
    del s["billable_seats"]
    with pytest.raises(ValueError):
        prorate_seats(s, _new(), _at(15))


def test_zero_billable_seats():
    assert prorate_seats(_sub(billable_seats=0), _new(), _at(15)) == []


def test_trialing_and_other_status():
    assert prorate_seats(_sub(status="trialing"), _new(), _at(15)) == []
    assert len(prorate_seats(_sub(status="past_due"), _new(), _at(15))) == 2


def test_downgrade_and_equal():
    assert prorate_seats(_sub(), _new(999), _at(15)) == []
    assert len(prorate_seats(_sub(), _new(1000), _at(15))) == 2


def test_days_left_rules():
    assert prorate_seats(_sub(), _new(), _END) == []
    assert prorate_seats(_sub(), _new(), _END + timedelta(days=2)) == []
    a = prorate_seats(_sub(), _new(), _at(90))
    b = prorate_seats(_sub(), _new(), _at(30))
    assert a == b
    pe = datetime(2025, 3, 31, 1, 0, tzinfo=timezone(timedelta(hours=2)))
    ch = datetime(2025, 3, 30, 23, 30, tzinfo=timezone.utc)  # same local day
    assert prorate_seats(_sub(period_end=pe), _new(), ch) == []


def test_rounding_ceil_credit_floor_charge():
    out = prorate_seats(_sub(seats=1, billable_seats=1, seat_price_cents=1001),
                        _new(1001), _at(1))
    # 1001/30 = 33.37 -> credit 34 and charge 33 both < 50: dropped
    assert out == []
    out = prorate_seats(_sub(billable_seats=1, seat_price_cents=1501), _new(1501), _at(1))
    # 50.03 -> credit 51, charge 50
    assert [l["amount_cents"] for l in out] == [51, 50]


def test_threshold_49_50_and_single_line():
    s = _sub(billable_seats=1, seat_price_cents=49)
    assert prorate_seats(s, _new(49), _at(30)) == []
    s = _sub(billable_seats=1, seat_price_cents=50)
    assert [l["amount_cents"] for l in prorate_seats(s, _new(50), _at(30))] == [50, 50]
    s = _sub(billable_seats=1, seat_price_cents=10)
    out = prorate_seats(s, _new(50), _at(30))
    assert len(out) == 1 and out[0]["kind"] == "charge"
    s = _sub(billable_seats=1, seat_price_cents=1499)
    out = prorate_seats(s, _new(1499), _at(1))  # charge floor 49 dropped, credit 50 kept
    assert [l["kind"] for l in out] == ["credit"] and out[0]["amount_cents"] == 50


def test_approval_threshold():
    s = _sub(billable_seats=1, seat_price_cents=50000)
    assert prorate_seats(s, _new(60000), _at(30))[0]["approved_by"] == "Nguyễn Thị Phương Thảo"
    s = _sub(billable_seats=1, seat_price_cents=50001)
    assert prorate_seats(s, _new(60000), _at(30))[0]["approved_by"] == "Ramón Etxeberria-Goñi"


def test_vat():
    out = prorate_seats(_sub(vat_id="DE123"), _new(), _at(15))
    assert out[1]["vat_cents"] == 0
    assert prorate_seats(_sub(vat_id=""), _new(), _at(15))[1]["vat_cents"] == 630
    out = prorate_seats(_sub(billable_seats=1, seat_price_cents=10), _new(1999), _at(30))
    assert out[0]["amount_cents"] == 1999 and out[0]["vat_cents"] == 419  # 419.79 down


def test_description_length():
    pre, suf = len("Credit unused "), len(" until 2025-03-31")
    n = 80 - pre - suf
    d = prorate_seats(_sub(plan_name="x" * n), _new(), _at(15))[0]["description"]
    assert len(d) == 80 and "x" * n in d
    d = prorate_seats(_sub(plan_name="x" * (n + 5)), _new(), _at(15))[0]["description"]
    assert len(d) == 80 and d.endswith("…" + " until 2025-03-31") and "x" * (n - 1) + "…" in d
    nm = "e\u0301" * 60  # decomposed; NFC is 60 chars
    d = prorate_seats(_sub(plan_name=nm), _new(), _at(15))[0]["description"]
    assert len(d) == 80 and "e\u0301" not in d
    d = prorate_seats(_sub(), _new(name="y" * 100), _at(15))[1]["description"]
    assert len(d) == 80 and d.endswith("2025-03-31")


def test_large_values():
    s = _sub(seat_price_cents=99999, billable_seats=1000)
    out = prorate_seats(s, _new(99999), _at(15))
    assert out[0]["amount_cents"] == 49999500 and out[1]["amount_cents"] == 49999500
    assert out[0]["approved_by"] == "Ramón Etxeberria-Goñi"
    assert out[1]["vat_cents"] == 49999500 * 21 // 100


def test_validation():
    with pytest.raises(TypeError):
        prorate_seats(_sub(seat_price_cents=10.0), _new(), _at(15))
    with pytest.raises(TypeError):
        prorate_seats(_sub(billable_seats=True), _new(), _at(15))
    with pytest.raises(TypeError):
        prorate_seats(_sub(), _new(1500.0), _at(15))
    with pytest.raises(ValueError):
        prorate_seats(_sub(billable_seats=-1), _new(), _at(15))
    with pytest.raises(ValueError):
        prorate_seats(_sub(seat_price_cents=-1), _new(), _at(15))
    with pytest.raises(ValueError):
        prorate_seats(_sub(), _new(), datetime(2025, 3, 10))
    with pytest.raises(ValueError):
        prorate_seats(_sub(period_end=datetime(2025, 3, 31)), _new(), _at(15))
    with pytest.raises(ValueError):
        prorate_seats({"id": 1}, _new(), _at(15))


def test_legacy_discount_ignored_and_pure():
    base = prorate_seats(_sub(), _new(), _at(15))
    assert prorate_seats(_sub(legacy_discount=50), _new(), _at(15)) == base
    assert prorate_seats(_sub(legacy_discount="x"), _new(), _at(15)) == base
    assert prorate_seats(_sub(), _new(), _at(15)) == base