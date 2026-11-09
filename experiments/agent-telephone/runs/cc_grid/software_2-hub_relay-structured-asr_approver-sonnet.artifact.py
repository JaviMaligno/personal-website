# Single module: implementation first, then pytest tests (run with `pytest prorate.py`).
# Not executed: I had no tools in this session, so the tests have not been run.
from __future__ import annotations

from datetime import datetime, timedelta

# ---- Provisional defaults, each isolated so it is easy to change ----
PERIOD_DAYS = 30
MIN_LINE_CENTS = 50            # applied to the rounded net amount
APPROVAL_LIMIT_CENTS = 50000   # credit strictly above this needs senior approval
VAT_PERCENT = 21
DESC_MAX = 80
APPROVER_DEFAULT = "Win Tee Fung Tao"
APPROVER_SENIOR = "Ramón Etxeberria-Goñi"
_DAY = timedelta(hours=24)


def _days_left(period_end: datetime, changed_at: datetime) -> int:
    """Whole 24h blocks remaining (floor), clamped to 0..PERIOD_DAYS."""
    d = (period_end - changed_at) // _DAY
    return max(0, min(PERIOD_DAYS, d))


def _credit_amount(seats: int, price: int, days: int) -> int:
    """Credits round UP."""
    return -(-(seats * price * days) // PERIOD_DAYS)


def _charge_amount(seats: int, price: int, days: int) -> int:
    """Charges round DOWN."""
    return (seats * price * days) // PERIOD_DAYS


def _passes_threshold(amount_cents: int) -> bool:
    return amount_cents >= MIN_LINE_CENTS


def _charge_vat(amount_cents: int, has_vat_id: bool) -> int:
    """VAT floor on the rounded charge; zero when a VAT ID is present."""
    return 0 if has_vat_id else amount_cents * VAT_PERCENT // 100


def _credit_vat() -> int:
    # Explicit requirement R9 (credit VAT always 0) overrides the house VAT-on-credits default.
    return 0


def _approver(credit_cents: int) -> str:
    return APPROVER_SENIOR if credit_cents > APPROVAL_LIMIT_CENTS else APPROVER_DEFAULT


def _describe(prefix: str, name: str, date_str: str) -> str:
    """'{prefix}{name} until DATE'; only the name is shortened, with a single ellipsis."""
    suffix = f" until {date_str}"
    full = f"{prefix}{name}{suffix}"
    if len(full) <= DESC_MAX:
        return full
    room = DESC_MAX - len(prefix) - len(suffix)
    if room < 1:
        room = 1
    short = name[: room - 1].rstrip().rstrip("…") + "…"
    return f"{prefix}{short}{suffix}"


def _credit_description(name: str, date_str: str) -> str:
    return _describe("Credit: unused ", name, date_str)


def _charge_description(name: str, date_str: str) -> str:
    return _describe("Charge: ", name, date_str)


# ---- Validation ----
def _check_dt(v, label):
    if not isinstance(v, datetime) or v.tzinfo is None or v.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")


def _check_int(v, label):
    if type(v) is not int or v < 0:
        raise ValueError(f"{label} must be a non-negative int")


def _has_vat_id(v) -> bool:
    if not v:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    return True


def prorate_seats(subscription, new_plan, changed_at):
    # Missing keys raise KeyError here.
    sub_id = subscription["id"]
    status = subscription["status"]
    old_name = subscription["plan_name"]
    old_price = subscription["seat_price_cents"]
    seats = subscription["seats"]
    billable = subscription["billable_seats"]
    vat_id = subscription["vat_id"]
    period_end = subscription["period_end"]
    new_name = new_plan["name"]
    new_price = new_plan["seat_price_cents"]

    _check_dt(period_end, "period_end")
    _check_dt(changed_at, "changed_at")
    _check_int(old_price, "seat_price_cents")
    _check_int(new_price, "new seat_price_cents")
    _check_int(seats, "seats")
    _check_int(billable, "billable_seats")

    if status == "trialing":
        return []
    if new_price <= old_price:  # downgrade or equal price
        return []

    days = _days_left(period_end, changed_at)
    date_str = period_end.date().isoformat()
    lines = []

    credit = _credit_amount(billable, old_price, days)
    if _passes_threshold(credit):
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": _credit_vat(),
            "description": _credit_description(str(old_name), date_str),
            "approved_by": _approver(credit),
        })

    charge = _charge_amount(billable, new_price, days)
    if _passes_threshold(charge):
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": _charge_vat(charge, _has_vat_id(vat_id)),
            "description": _charge_description(str(new_name), date_str),
            "approved_by": None,
        })
    return lines


# ======================= Tests (pytest) =======================
from datetime import timezone  # noqa: E402

import pytest  # noqa: E402

_END = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)
_START = _END - timedelta(days=30)


def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 10, "billable_seats": 10,
         "vat_id": None, "period_end": _END}
    s.update(kw)
    return s


def _plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def test_upgrade_without_vat_id():
    out = prorate_seats(_sub(), _plan(), _START)
    assert [l["kind"] for l in out] == ["credit", "charge"]
    c, ch = out
    assert c["amount_cents"] == 10000 and c["vat_cents"] == 0
    assert c["approved_by"] == "Win Tee Fung Tao"
    assert c["description"] == "Credit: unused Basic until 2026-11-12"
    assert ch["amount_cents"] == 20000 and ch["vat_cents"] == 4200
    assert ch["approved_by"] is None
    assert ch["description"] == "Charge: Pro until 2026-11-12"
    assert set(c) == {"subscription_id", "kind", "amount_cents", "vat_cents",
                      "description", "approved_by"}


def test_upgrade_with_vat_id():
    out = prorate_seats(_sub(vat_id="ES123"), _plan(), _START)
    assert out[1]["vat_cents"] == 0
    out = prorate_seats(_sub(vat_id="   "), _plan(), _START)
    assert out[1]["vat_cents"] == 4200


def test_downgrade_and_equal():
    assert prorate_seats(_sub(), _plan(500), _START) == []
    assert prorate_seats(_sub(), _plan(1000), _START) == []


def test_trialing():
    assert prorate_seats(_sub(status="trialing"), _plan(), _START) == []


def test_billable_not_seats():
    out = prorate_seats(_sub(seats=100, billable_seats=1, seat_price_cents=100),
                        _plan(200), _START)
    assert out[0]["amount_cents"] == 100 and out[1]["amount_cents"] == 200


def test_days_zero_thirty_clamp():
    assert prorate_seats(_sub(), _plan(), _END) == []
    assert prorate_seats(_sub(), _plan(), _END + timedelta(days=3)) == []
    a = prorate_seats(_sub(), _plan(), _START)
    b = prorate_seats(_sub(), _plan(), _START - timedelta(days=15))
    assert a == b
    # 29 days 23h -> D=29 (floor)
    c = prorate_seats(_sub(), _plan(), _START + timedelta(hours=1))
    assert c[0]["amount_cents"] == -(-(10 * 1000 * 29) // 30)


def test_threshold_49_vs_50():
    s = dict(billable_seats=1)
    out = prorate_seats(_sub(seat_price_cents=49, **s), _plan(100), _START)
    assert [l["kind"] for l in out] == ["charge"]
    out = prorate_seats(_sub(seat_price_cents=50, **s), _plan(100), _START)
    assert [l["kind"] for l in out] == ["credit", "charge"]
    # charge judged independently
    out = prorate_seats(_sub(seat_price_cents=49, **s), _plan(50), _START)
    assert [l["kind"] for l in out] == ["charge"] and out[0]["amount_cents"] == 50


def test_approver_boundary():
    s = dict(billable_seats=1)
    out = prorate_seats(_sub(seat_price_cents=50000, **s), _plan(60000), _START)
    assert out[0]["approved_by"] == "Win Tee Fung Tao"
    out = prorate_seats(_sub(seat_price_cents=50001, **s), _plan(60000), _START)
    assert out[0]["approved_by"] == "Ramón Etxeberria-Goñi"


def test_long_non_ascii_name():
    name = "Ünïcödé Plän ☃ " * 10
    out = prorate_seats(_sub(plan_name=name), _plan(name=name), _START)
    for l in out:
        d = l["description"]
        assert len(d) <= 80
        assert d.endswith(" until 2026-11-12")
        assert d.count("…") == 1
        assert "…" in d.split(" until")[0]


def test_legacy_discount_ignored():
    assert prorate_seats(_sub(legacy_discount=50), _plan(), _START) == \
        prorate_seats(_sub(), _plan(), _START)


def test_int_types():
    for l in prorate_seats(_sub(), _plan(), _START):
        assert type(l["amount_cents"]) is int and type(l["vat_cents"]) is int


def test_ordering():
    assert [l["kind"] for l in prorate_seats(_sub(), _plan(), _START)] == ["credit", "charge"]


def test_invalid_input():
    with pytest.raises(ValueError):
        prorate_seats(_sub(), _plan(), datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        prorate_seats(_sub(seats=True), _plan(), _START)
    with pytest.raises(ValueError):
        prorate_seats(_sub(seat_price_cents=10.0), _plan(), _START)
    with pytest.raises(ValueError):
        prorate_seats(_sub(billable_seats=-1), _plan(), _START)
    with pytest.raises(KeyError):
        s = _sub()
        del s["vat_id"]
        prorate_seats(s, _plan(), _START)


def test_no_mutation():
    s, p = _sub(), _plan()
    s0, p0 = dict(s), dict(p)
    prorate_seats(s, p, _START)
    assert s == s0 and p == p0