"""prorate.py - seat proration for plan changes (stdlib only).

Notes for the reviewer:
- Tests are embedded below as test_* functions (single-module delivery).
  Run with: pytest /absolute/path/to/prorate.py
  They were not executed in this session (no tools were available).
- Deviation: the house rule "VAT on every line, credits included" is
  overridden by R7 (credits always have vat_cents 0).
- Finance to confirm (D6): vat_cents = floor(amount_cents * 21 / 100).
- Check order: trialing, then validation, then downgrade, days_left <= 0.
"""
from datetime import datetime, timedelta, timezone

CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
CREDIT_APPROVER_HIGH = "Ramón Etxeberria-Goñi"
CREDIT_HIGH_THRESHOLD = 50000
MIN_LINE_CENTS = 50
MAX_DESC = 80
VAT_PERCENT = 21


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _ceil_div(a, b):
    return -(-a // b)


def _days_left(changed_at, period_end):
    local = changed_at.astimezone(period_end.tzinfo)
    days = (period_end.date() - local.date()).days
    return max(0, min(30, days))


def _describe(prefix, plan_name, date):
    suffix = f" until {date.isoformat()}"
    avail = MAX_DESC - len(prefix) - len(suffix)
    name = str(plan_name)
    if len(name) > avail:
        name = name[: avail - 3] + "..." if avail >= 3 else name[: max(avail, 0)]
    return f"{prefix}{name}{suffix}"


def _credit_line(sub, seats, days, date):
    amount = _ceil_div(seats * sub["seat_price_cents"] * days, 30)
    if amount < MIN_LINE_CENTS:
        return None
    approver = CREDIT_APPROVER_HIGH if amount > CREDIT_HIGH_THRESHOLD else CREDIT_APPROVER
    return {
        "subscription_id": sub["id"],
        "kind": "credit",
        "amount_cents": amount,
        "vat_cents": 0,
        "description": _describe("Credit unused ", sub["plan_name"], date),
        "approved_by": approver,
    }


def _charge_line(sub, new_plan, seats, days, date):
    amount = (seats * new_plan["seat_price_cents"] * days) // 30
    if amount < MIN_LINE_CENTS:
        return None
    vat_id = sub.get("vat_id")
    reverse = bool(vat_id) and bool(str(vat_id).strip())
    vat = 0 if reverse else (amount * VAT_PERCENT) // 100
    return {
        "subscription_id": sub["id"],
        "kind": "charge",
        "amount_cents": amount,
        "vat_cents": vat,
        "description": _describe("Charge unused ", new_plan["name"], date),
        "approved_by": None,
    }


def prorate_seats(subscription, new_plan, changed_at):
    if subscription.get("status") == "trialing":
        return []
    period_end = subscription["period_end"]
    if changed_at.tzinfo is None or period_end.tzinfo is None:
        raise ValueError("naive datetime not allowed")
    seats = subscription["billable_seats"]
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    for v in (seats, old_price, new_price):
        if not _is_int(v) or v < 0:
            raise ValueError("seats and prices must be non-negative ints")
    if new_price < old_price:
        return []
    days = _days_left(changed_at, period_end)
    if days <= 0 or seats == 0:
        return []
    date = period_end.date()
    lines = [
        _credit_line(subscription, seats, days, date),
        _charge_line(subscription, new_plan, seats, days, date),
    ]
    return [l for l in lines if l is not None]


# ----------------------------- tests -----------------------------

_PE = datetime(2025, 1, 31, 12, 0, tzinfo=timezone.utc)


def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "billable_seats": 1, "seats": 1,
         "seat_price_cents": 3000, "plan_name": "Basic", "period_end": _PE,
         "vat_id": None}
    s.update(kw)
    return s


def _plan(price=3000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def _at(days):
    return _PE - timedelta(days=days)


def test_uses_billable_seats_not_seats():
    out = prorate_seats(_sub(billable_seats=2, seats=10), _plan(), _at(30))
    assert out[0]["amount_cents"] == 6000
    assert out[1]["amount_cents"] == 6000


def test_downgrade_and_equal_price():
    assert prorate_seats(_sub(), _plan(2999), _at(30)) == []
    assert len(prorate_seats(_sub(), _plan(3000), _at(30))) == 2


def test_trialing():
    assert prorate_seats(_sub(status="trialing"), _plan(), _at(30)) == []


def test_ceil_vs_floor():
    out = prorate_seats(_sub(seat_price_cents=2000), _plan(2000), _at(1))
    assert out[0]["amount_cents"] == 67
    assert out[1]["amount_cents"] == 66


def test_sub_50_omitted_independently():
    out = prorate_seats(_sub(seat_price_cents=1000), _plan(2000), _at(1))
    assert [l["kind"] for l in out] == ["charge"]
    out = prorate_seats(_sub(seat_price_cents=1480), _plan(1480), _at(1))
    assert [l["kind"] for l in out] == ["credit"]
    assert out[0]["amount_cents"] == 50


def test_vat():
    out = prorate_seats(_sub(), _plan(), _at(30))
    assert out[0]["vat_cents"] == 0
    assert out[1]["vat_cents"] == 630
    out = prorate_seats(_sub(vat_id="DE123"), _plan(), _at(30))
    assert out[1]["vat_cents"] == 0
    out = prorate_seats(_sub(vat_id="   "), _plan(), _at(30))
    assert out[1]["vat_cents"] == 630


def test_threshold_and_names():
    out = prorate_seats(_sub(seat_price_cents=50000), _plan(60000), _at(30))
    assert out[0]["amount_cents"] == 50000
    assert out[0]["approved_by"] == "Nguyễn Thị Phương Thảo"
    out = prorate_seats(_sub(seat_price_cents=50001), _plan(60000), _at(30))
    assert out[0]["amount_cents"] == 50001
    assert out[0]["approved_by"] == "Ramón Etxeberria-Goñi"
    assert out[1]["approved_by"] is None


def test_long_plan_name():
    name = "X" * 200
    out = prorate_seats(_sub(plan_name=name), _plan(name=name), _at(30))
    for l in out:
        assert len(l["description"]) <= 80
        assert l["description"].endswith(" until 2025-01-31")
        assert "..." in l["description"]


def test_short_description():
    out = prorate_seats(_sub(), _plan(), _at(30))
    assert out[0]["description"] == "Credit unused Basic until 2025-01-31"
    assert out[1]["description"] == "Charge unused Pro until 2025-01-31"


def test_order_and_ints():
    out = prorate_seats(_sub(), _plan(), _at(10))
    assert [l["kind"] for l in out] == ["credit", "charge"]
    for l in out:
        assert type(l["amount_cents"]) is int
        assert type(l["vat_cents"]) is int


def test_days_clamp():
    assert prorate_seats(_sub(), _plan(), _at(45))[0]["amount_cents"] == 3000
    assert prorate_seats(_sub(), _plan(), _at(0)) == []
    assert prorate_seats(_sub(), _plan(), _at(-3)) == []


def test_timezone_local_date():
    tz = timezone(timedelta(hours=2))
    pe = datetime(2025, 2, 10, 0, 30, tzinfo=tz)
    changed = datetime(2025, 2, 8, 23, 0, tzinfo=timezone.utc)  # 02-09 local
    out = prorate_seats(_sub(period_end=pe), _plan(), changed)
    assert out[0]["amount_cents"] == 100
    assert out[0]["description"].endswith("2025-02-10")


def test_naive_raises():
    import pytest
    with pytest.raises(ValueError):
        prorate_seats(_sub(), _plan(), datetime(2025, 1, 1))
    with pytest.raises(ValueError):
        prorate_seats(_sub(period_end=datetime(2025, 1, 31)), _plan(), _at(1))


def test_bad_numbers_raise():
    import pytest
    with pytest.raises(ValueError):
        prorate_seats(_sub(billable_seats=1.0), _plan(), _at(1))
    with pytest.raises(ValueError):
        prorate_seats(_sub(billable_seats=True), _plan(), _at(1))
    with pytest.raises(ValueError):
        prorate_seats(_sub(), _plan(-1), _at(1))


def test_legacy_discount_ignored():
    a = prorate_seats(_sub(), _plan(), _at(10))
    b = prorate_seats(_sub(legacy_discount=50), _plan(), _at(10))
    assert a == b