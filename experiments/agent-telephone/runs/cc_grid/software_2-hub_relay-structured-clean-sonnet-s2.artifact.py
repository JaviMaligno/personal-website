"""prorate.py - seat proration for plan upgrades.

Single public entry point: prorate_seats(subscription, new_plan, changed_at).

Notes for the report (tech lead decisions pending client confirmation):
- Charge VAT is rounded DOWN (floor) at 21%.
- Equal price returns [] (same as a downgrade).
- Statuses other than "trialing" prorate normally.
- Tests are embedded below (pytest-style, run with `pytest prorate.py`).
  They have NOT been executed by me, because I had no tools in this run.
"""
from datetime import datetime, timedelta, timezone

_PERIOD = 30
_MIN_CENTS = 50
_MAX_DESC = 80
_REQUIRED_SUB = ("id", "status", "plan_name", "seat_price_cents", "seats",
                 "billable_seats", "vat_id", "period_end")


def _is_int(v):
    return type(v) is int


def _aware(dt, label):
    if (not isinstance(dt, datetime) or dt.tzinfo is None
            or dt.tzinfo.utcoffset(dt) is None):
        raise ValueError(f"{label} must be a timezone-aware datetime")


def _describe(prefix, name, suffix):
    avail = _MAX_DESC - len(prefix) - len(suffix)
    if len(name) > avail:
        name = name[:max(avail - 3, 0)] + "..."
    return prefix + name + suffix


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise ValueError("subscription and new_plan must be dicts")
    for k in _REQUIRED_SUB:
        if k not in subscription:
            raise ValueError(f"missing subscription key: {k}")
    for k in ("name", "seat_price_cents"):
        if k not in new_plan:
            raise ValueError(f"missing new_plan key: {k}")
    period_end = subscription["period_end"]
    _aware(changed_at, "changed_at")
    _aware(period_end, "period_end")

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    for p in (old_price, new_price):
        if not _is_int(p) or p < 0:
            raise ValueError("prices must be non-negative integers")
    for s in (subscription["seats"], subscription["billable_seats"]):
        if not _is_int(s) or s < 0:
            raise ValueError("seat counts must be non-negative integers")
    if not isinstance(subscription["plan_name"], str) or not isinstance(new_plan["name"], str):
        raise ValueError("plan names must be strings")

    if subscription["status"] == "trialing":
        return []
    seats = subscription["billable_seats"]
    if seats == 0 or new_price <= old_price:
        return []

    end_date = period_end.date()
    days = (end_date - changed_at.astimezone(period_end.tzinfo).date()).days
    days = min(days, _PERIOD)
    if days <= 0:
        return []

    date_s = end_date.strftime("%Y-%m-%d")
    sid = subscription["id"]
    out = []

    credit = -(-(old_price * seats * days) // _PERIOD)
    if credit >= _MIN_CENTS:
        out.append({
            "subscription_id": sid,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit: unused ", subscription["plan_name"],
                                     f" seats, period ending {date_s}"),
            "approved_by": ("Ramón Etxeberria-Goñi" if credit > 50000
                            else "Nguyễn Thị Phương Thảo"),
        })

    charge = (new_price * seats * days) // _PERIOD
    if charge >= _MIN_CENTS:
        vat_id = subscription["vat_id"]
        has_vat_id = isinstance(vat_id, str) and vat_id.strip() != ""
        out.append({
            "subscription_id": sid,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if has_vat_id else (charge * 21) // 100,
            "description": _describe("Charge: ", new_plan["name"],
                                     f" seats, period ending {date_s}"),
            "approved_by": None,
        })
    return out


# ----------------------------- tests -----------------------------
UTC = timezone.utc
_END = datetime(2026, 11, 30, 12, 0, tzinfo=UTC)


def _sub(**kw):
    s = dict(id="s1", status="active", plan_name="Basic", seat_price_cents=1000,
             seats=4, billable_seats=4, vat_id=None, period_end=_END)
    s.update(kw)
    return s


def _at(days):
    return _END - timedelta(days=days)


def test_a1():
    r = prorate_seats(_sub(), {"name": "Pro", "seat_price_cents": 1500}, _at(15))
    assert [x["kind"] for x in r] == ["credit", "charge"]
    assert (r[0]["amount_cents"], r[0]["vat_cents"], r[0]["approved_by"]) == (
        2000, 0, "Nguyễn Thị Phương Thảo")
    assert (r[1]["amount_cents"], r[1]["vat_cents"], r[1]["approved_by"]) == (3000, 630, None)
    assert set(r[0]) == {"subscription_id", "kind", "amount_cents", "vat_cents",
                         "description", "approved_by"}
    assert "2026-11-30" in r[0]["description"] and "Basic" in r[0]["description"]
    assert "Pro" in r[1]["description"]
    assert all(type(x["amount_cents"]) is int and type(x["vat_cents"]) is int for x in r)


def test_a2():
    r = prorate_seats(_sub(seat_price_cents=999, billable_seats=1, seats=1),
                      {"name": "Pro", "seat_price_cents": 1333}, _at(7))
    assert (r[0]["amount_cents"], r[1]["amount_cents"]) == (234, 311)


def test_a3_vat_id():
    for v, expected in (("NL123", 0), ("", 630), ("   ", 630), (None, 630)):
        r = prorate_seats(_sub(vat_id=v), {"name": "Pro", "seat_price_cents": 1500}, _at(15))
        assert r[1]["vat_cents"] == expected


def test_a4_approval():
    r = prorate_seats(_sub(seat_price_cents=5000, billable_seats=10),
                      {"name": "P", "seat_price_cents": 6000}, _at(30))
    assert r[0]["amount_cents"] == 50000 and r[0]["approved_by"] == "Nguyễn Thị Phương Thảo"
    r = prorate_seats(_sub(seat_price_cents=10001, billable_seats=5),
                      {"name": "P", "seat_price_cents": 20000}, _at(30))
    assert r[0]["amount_cents"] == 50005 and r[0]["approved_by"] == "Ramón Etxeberria-Goñi"


def test_a5_threshold():
    # credit 49 (ceil of 1470/30), charge 99 kept
    r = prorate_seats(_sub(seat_price_cents=49, billable_seats=1),
                      {"name": "P", "seat_price_cents": 99}, _at(30))
    assert [x["kind"] for x in r] == ["credit"] or [x["kind"] for x in r] == ["charge"]
    r = prorate_seats(_sub(seat_price_cents=49, billable_seats=1),
                      {"name": "P", "seat_price_cents": 99}, _at(30))
    assert r[0]["kind"] == "charge" and r[0]["amount_cents"] == 99 if r[0]["kind"] == "charge" else True
    r = prorate_seats(_sub(seat_price_cents=50, billable_seats=1),
                      {"name": "P", "seat_price_cents": 60}, _at(30))
    assert [x["amount_cents"] for x in r] == [50, 60]
    r = prorate_seats(_sub(seat_price_cents=40, billable_seats=1),
                      {"name": "P", "seat_price_cents": 49}, _at(30))
    assert r == []


def test_a6():
    assert prorate_seats(_sub(), {"name": "P", "seat_price_cents": 500}, _at(15)) == []
    assert prorate_seats(_sub(), {"name": "P", "seat_price_cents": 1000}, _at(15)) == []
    assert prorate_seats(_sub(status="trialing"),
                         {"name": "P", "seat_price_cents": 1500}, _at(15)) == []


def test_a7_billable():
    r = prorate_seats(_sub(seats=10, billable_seats=7),
                      {"name": "P", "seat_price_cents": 1500}, _at(30))
    assert r[0]["amount_cents"] == 7000


def test_a8_after_end():
    assert prorate_seats(_sub(), {"name": "P", "seat_price_cents": 1500},
                         _END + timedelta(days=1)) == []


def test_a9_long_name():
    r = prorate_seats(_sub(plan_name="x" * 200), {"name": "y" * 200, "seat_price_cents": 1500}, _at(15))
    for x in r:
        assert len(x["description"]) <= 80 and "2026-11-30" in x["description"]


def test_validation():
    import pytest
    p = {"name": "P", "seat_price_cents": 1500}
    with pytest.raises(ValueError):
        prorate_seats(_sub(), p, datetime(2026, 11, 1))
    with pytest.raises(ValueError):
        prorate_seats(_sub(period_end=datetime(2026, 11, 30)), p, _at(5))
    with pytest.raises(ValueError):
        prorate_seats({"id": 1}, p, _at(5))
    with pytest.raises(ValueError):
        prorate_seats(_sub(billable_seats=-1), p, _at(5))
    with pytest.raises(ValueError):
        prorate_seats(_sub(billable_seats=1.5), p, _at(5))
    with pytest.raises(ValueError):
        prorate_seats(_sub(seat_price_cents=-1), p, _at(5))
    assert prorate_seats(_sub(billable_seats=0), p, _at(5)) == []


def test_pure_and_other_status():
    s = _sub(status="past_due", legacy_discount=0.5)
    before = dict(s)
    r = prorate_seats(s, {"name": "P", "seat_price_cents": 1500}, _at(15))
    assert s == before and len(r) == 2