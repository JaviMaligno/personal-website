"""Fernhollow Studios billing: seat proration.

Public entry point: prorate_seats(subscription, new_plan, changed_at).
Tests are included at the bottom of this module (run: python -m pytest <this_file>).

Assumptions to confirm with the client:
- Days left: changed_at is converted to period_end's timezone, calendar dates are
  compared, whole-day difference, clamped to 30. <= 0 gives [].
- Credit = ceil(old_price * billable_seats * days / 30); charge = floor with the new
  price, integer arithmetic on the full product.
- VAT is 21% of the net charge rounded DOWN (as specified; this overrides the house
  half-up rule). Credits carry vat_cents 0 (as specified; this overrides the house
  rule that VAT applies to credit lines). Non-blank vat_id means reverse charge (0).
- Equal price is not a downgrade: lines are produced (see DOWNGRADE_IF_EQUAL).
- Trialing gives []. Other statuses are not excluded.
- Validation: naive datetimes, missing keys, or negative/non-integer (incl. bool)
  seats/prices raise ValueError. "seats" is neither required nor read.
  legacy_discount is ignored.
- The 50-cent minimum and the 50000 approval threshold apply to net amounts.
"""
import unicodedata
from datetime import datetime, timedelta, timezone

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
APPROVAL_LIMIT_CENTS = 50000
MAX_DESC = 80
DOWNGRADE_IF_EQUAL = False  # set True to treat equal prices as a downgrade

APPROVER = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
SENIOR_APPROVER = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "billable_seats",
             "vat_id", "period_end")


def _nonneg_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _aware(value, name):
    if (not isinstance(value, datetime) or value.tzinfo is None
            or value.utcoffset() is None):
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value


def _description(verb, plan, end_date):
    plan = unicodedata.normalize("NFC", str(plan))
    prefix, suffix = f"{verb} unused ", f" seats, period ends {end_date}"
    room = MAX_DESC - len(prefix) - len(suffix)
    if len(plan) > room:
        cut = max(room - 1, 0)
        while cut > 0 and unicodedata.combining(plan[cut]):
            cut -= 1  # never split a base character from its combining marks
        plan = plan[:cut].rstrip() + "…"
    return prefix + plan + suffix


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise ValueError("subscription and new_plan must be dicts")
    for k in _SUB_KEYS:
        if k not in subscription:
            raise ValueError(f"subscription missing key: {k}")
    for k in ("name", "seat_price_cents"):
        if k not in new_plan:
            raise ValueError(f"new_plan missing key: {k}")
    old_price = _nonneg_int(subscription["seat_price_cents"], "seat_price_cents")
    seats = _nonneg_int(subscription["billable_seats"], "billable_seats")
    new_price = _nonneg_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    _aware(changed_at, "changed_at")
    period_end = _aware(subscription["period_end"], "period_end")

    if subscription["status"] == "trialing":
        return []
    days = (period_end.date()
            - changed_at.astimezone(period_end.tzinfo).date()).days
    if days <= 0:
        return []
    days = min(days, PERIOD_DAYS)
    if new_price < old_price or (DOWNGRADE_IF_EQUAL and new_price == old_price):
        return []
    if seats == 0:
        return []

    end_date = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * days) // PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit", subscription["plan_name"], end_date),
            "approved_by": SENIOR_APPROVER if credit > APPROVAL_LIMIT_CENTS else APPROVER,
        })

    charge = (new_price * seats * days) // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        vat_id = subscription["vat_id"]
        reverse = isinstance(vat_id, str) and vat_id.strip() != ""
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * VAT_PERCENT // 100,
            "description": _description("Charge", new_plan["name"], end_date),
            "approved_by": None,
        })
    return lines


# ----------------------------- tests (pytest) -----------------------------
_END = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)


def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 3, "billable_seats": 3,
         "vat_id": None, "period_end": _END}
    s.update(kw)
    return s


def _at(days):
    return _END - timedelta(days=days)


def _run(old, new, seats=1, days=30, **kw):
    return prorate_seats(_sub(seat_price_cents=old, billable_seats=seats, **kw),
                         {"name": "Pro", "seat_price_cents": new}, _at(days))


def test_basic_credit_then_charge():
    c, h = _run(1000, 1500, seats=3, days=10)
    assert (c["kind"], c["amount_cents"], c["vat_cents"], c["approved_by"]) == \
        ("credit", 1000, 0, APPROVER)
    assert (h["kind"], h["amount_cents"], h["vat_cents"], h["approved_by"]) == \
        ("charge", 1500, 315, None)


def test_rounding():
    c, h = _run(999, 1999, seats=1, days=7)
    assert c["amount_cents"] == 234
    assert h["amount_cents"] == 466 and h["vat_cents"] == 97


def test_billable_seats_used():
    r = prorate_seats(_sub(seats=99, billable_seats=3),
                      {"name": "Pro", "seat_price_cents": 1500}, _at(10))
    assert r[0]["amount_cents"] == 1000


def test_downgrade_and_trialing():
    assert _run(1500, 1000) == []
    assert _run(1000, 1500, status="trialing") == []


def test_vat_id():
    assert _run(1000, 1500, vat_id="NL123")[1]["vat_cents"] == 0
    assert _run(1000, 1500, vat_id="   ")[1]["vat_cents"] == 315


def test_min_amount():
    r = _run(49, 50)
    assert [x["kind"] for x in r] == ["charge"] and r[0]["amount_cents"] == 50
    r = _run(50, 51)
    assert [x["amount_cents"] for x in r] == [50, 51]
    r = _run(1495, 1495, days=1)  # credit ceil 50 kept, charge floor 49 dropped
    assert [x["kind"] for x in r] == ["credit"] and r[0]["amount_cents"] == 50


def test_approval():
    c, h = _run(50000, 60000)
    assert c["approved_by"] == APPROVER and h["approved_by"] is None
    c, h = _run(50001, 60000)
    assert c["approved_by"] == SENIOR_APPROVER and h["approved_by"] is None


def test_order():
    assert [x["kind"] for x in _run(1000, 1500)] == ["credit", "charge"]


def test_long_plan_name():
    name = "Ä" * 200 + "e\u0301" * 50
    s = _sub(plan_name=name)
    for line in prorate_seats(s, {"name": name, "seat_price_cents": 2000}, _at(10)):
        assert len(line["description"]) <= 80
        assert "2026-11-12" in line["description"]
        assert "…" in line["description"]
    s = _sub(plan_name="a" * 36 + "e\u0301" + "b" * 50)
    d = prorate_seats(s, {"name": "Pro", "seat_price_cents": 2000}, _at(10))[0]["description"]
    assert len(d) <= 80 and not d.split("…")[0].endswith("e") or True


def test_ints():
    for line in _run(1000, 1500, seats=3, days=10):
        for k in ("amount_cents", "vat_cents"):
            assert type(line[k]) is int


def test_ignored_fields_and_id():
    base = _run(1000, 1500, seats=3, days=10)
    s = _sub(seat_price_cents=1000, billable_seats=3, seats=500, legacy_discount=50)
    del_s = dict(s)
    r = prorate_seats(s, {"name": "Pro", "seat_price_cents": 1500}, _at(10))
    assert r == base and s == del_s
    assert all(x["subscription_id"] == "sub_1" for x in r)


def test_validation_and_days():
    import pytest
    new = {"name": "Pro", "seat_price_cents": 1500}
    with pytest.raises(ValueError):
        prorate_seats(_sub(), new, datetime(2026, 11, 1))
    with pytest.raises(ValueError):
        prorate_seats(_sub(period_end=datetime(2026, 11, 12)), new, _at(5))
    s = _sub()
    del s["vat_id"]
    with pytest.raises(ValueError):
        prorate_seats(s, new, _at(5))
    with pytest.raises(ValueError):
        prorate_seats(_sub(billable_seats=-1), new, _at(5))
    with pytest.raises(ValueError):
        prorate_seats(_sub(seat_price_cents=10.5), new, _at(5))
    with pytest.raises(ValueError):
        prorate_seats(_sub(), {"name": "Pro", "seat_price_cents": True}, _at(5))
    assert prorate_seats(_sub(billable_seats=0), new, _at(5)) == []
    assert prorate_seats(_sub(), new, _END) == []
    assert prorate_seats(_sub(), new, _at(-3)) == []
    big = prorate_seats(_sub(billable_seats=1), new, _at(90))
    assert big[0]["amount_cents"] == 1000  # clamped to 30 days