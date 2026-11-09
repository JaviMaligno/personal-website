"""Fernhollow Studios seat proration.

Public entry point: prorate_seats(subscription, new_plan, changed_at).

Assumptions:
- Equal prices yield no lines, same as a downgrade.
- Prices must be non-negative ints. Non-int or negative values raise.
- A missing or invalid billable_seats raises ValueError. It never falls back to seats.
- Inputs are validated before the trialing, zero-seat and downgrade early returns.
- Statuses other than "trialing" are prorated, including canceled.
- The 80-char limit counts characters, not bytes.

Open questions for the client:
- Is a 13-day period really intended (maybe 30)?
- Should equal prices yield no lines?
- Which VAT rounding does finance want (half-up on the charge is used here)?
- Should canceled or other statuses be prorated?
- Does "never round in their favour" mean credits up and charges down, as written?

Tests are included at the bottom (pytest-style functions). They have NOT been run:
no execution tool was available. Run with: pytest <this file> (or rename to test_prorate.py).
"""
from datetime import datetime, timedelta, timezone

PERIOD_DAYS = 13
MIN_LINE_CENTS = 50
APPROVAL_LIMIT_CENTS = 50_000
DEFAULT_APPROVER = "Nguyễn Thị Phương Thảo"
SENIOR_APPROVER = "Ramón Etxeberria-Goñi"
MAX_DESCRIPTION = 80


def _check_int(value, name, minimum=0):
    if type(value) is not int:
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    return value


def _check_aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _days_left(changed_at, period_end):
    local = changed_at.astimezone(period_end.tzinfo).date()
    return max(0, min(PERIOD_DAYS, (period_end.date() - local).days))


def _credit_cents(old_price, seats, days_left):
    """Unused-time credit, rounded UP (ceil), net of VAT."""
    return -(-(old_price * seats * days_left) // PERIOD_DAYS)


def _charge_cents(new_price, seats, days_left):
    """New-plan charge, rounded DOWN (floor), net of VAT."""
    return (new_price * seats * days_left) // PERIOD_DAYS


def _vat_cents(charge, vat_id):
    """21% VAT on a charge, half-up; 0 under reverse charge (vat_id present)."""
    if isinstance(vat_id, str):
        has_id = bool(vat_id.strip())
    else:
        has_id = vat_id is not None
    if has_id:
        return 0
    return (charge * 21 + 50) // 100


def _approver(credit):
    return SENIOR_APPROVER if credit > APPROVAL_LIMIT_CENTS else DEFAULT_APPROVER


def _describe(prefix, plan, date_str):
    bare = f"{prefix} seats to {date_str}"
    room = MAX_DESCRIPTION - len(bare) - 1
    name = plan[:room].strip() if room > 0 else ""
    text = f"{prefix} {name} seats to {date_str}" if name else bare
    return text


def prorate_seats(subscription, new_plan, changed_at):
    try:
        sub_id = subscription["id"]
        status = subscription["status"]
        old_plan_name = subscription["plan_name"]
        old_price = subscription["seat_price_cents"]
        seats = subscription["billable_seats"]
        vat_id = subscription.get("vat_id")
        period_end = subscription["period_end"]
        new_name = new_plan["name"]
        new_price = new_plan["seat_price_cents"]
    except KeyError as exc:
        raise ValueError(f"missing required field: {exc.args[0]}") from None

    _check_int(old_price, "seat_price_cents")
    _check_int(new_price, "new_plan.seat_price_cents")
    _check_int(seats, "billable_seats")
    _check_aware(changed_at, "changed_at")
    _check_aware(period_end, "period_end")
    if not isinstance(old_plan_name, str) or not isinstance(new_name, str):
        raise TypeError("plan names must be strings")

    if status == "trialing" or seats == 0 or new_price <= old_price:
        return []
    days = _days_left(changed_at, period_end)
    if days <= 0:
        return []

    date_str = period_end.strftime("%Y-%m-%d")
    lines = []

    credit = _credit_cents(old_price, seats, days)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit unused", old_plan_name, date_str),
            "approved_by": _approver(credit),
        })

    charge = _charge_cents(new_price, seats, days)
    if charge >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": _vat_cents(charge, vat_id),
            "description": _describe("Charge", new_name, date_str),
            "approved_by": None,
        })
    return lines


# ----------------------------- tests (pytest) -----------------------------
PE = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


def _sub(**kw):
    base = dict(id="sub_1", status="active", plan_name="Pro", seat_price_cents=1000,
                seats=99, billable_seats=10, vat_id=None, period_end=PE)
    base.update(kw)
    return base


def _run(sub=None, new_price=1500, name="Team", days=5, **kw):
    return prorate_seats(sub or _sub(**kw), {"name": name, "seat_price_cents": new_price},
                         PE - timedelta(days=days))


def test_acceptance_example():
    credit, charge = _run()
    assert (credit["kind"], credit["amount_cents"], credit["vat_cents"]) == ("credit", 3847, 0)
    assert credit["approved_by"] == "Nguyễn Thị Phương Thảo"
    assert (charge["kind"], charge["amount_cents"], charge["vat_cents"]) == ("charge", 5769, 1211)
    assert charge["approved_by"] is None
    assert credit["description"] == "Credit unused Pro seats to 2026-11-03"
    assert all(type(l[k]) is int for l in (credit, charge) for k in ("amount_cents", "vat_cents"))


def test_vat_id_reverse_charge_and_blank():
    assert _run(vat_id="DE123")[1]["vat_cents"] == 0
    assert _run(vat_id="   ")[1]["vat_cents"] == 1211
    assert _run(vat_id="")[1]["vat_cents"] == 1211


def test_seats_and_legacy_discount_ignored():
    assert _run(seats=1, legacy_discount=50) == _run()


def test_vat_half_up():
    assert _vat_cents(50, None) == 11  # 10.5 -> 11
    assert _vat_cents(52, None) == 11  # 10.92
    assert _vat_cents(0, None) == 0


def test_approval_threshold():
    kw = dict(billable_seats=1, seat_price_cents=50000)
    assert _run(new_price=60000, days=13, **kw)[0]["approved_by"] == DEFAULT_APPROVER
    kw["seat_price_cents"] = 50001
    c = _run(new_price=60000, days=13, **kw)[0]
    assert c["amount_cents"] == 50001 and c["approved_by"] == SENIOR_APPROVER


def test_fifty_cent_threshold():
    assert _run(new_price=100, days=13, billable_seats=1, seat_price_cents=49) == [
        l for l in _run(new_price=100, days=13, billable_seats=1, seat_price_cents=49)
        if l["kind"] == "charge"]
    r = _run(new_price=100, days=13, billable_seats=1, seat_price_cents=50)
    assert [l["kind"] for l in r] == ["credit", "charge"]
    r = _run(new_price=50, days=13, billable_seats=1, seat_price_cents=0)
    assert [l["kind"] for l in r] == ["charge"]
    assert _run(new_price=49, days=13, billable_seats=1, seat_price_cents=0) == []


def test_no_lines_cases():
    assert _run(new_price=900) == []
    assert _run(new_price=1000) == []
    assert _run(status="trialing") == []
    assert _run(billable_seats=0) == []
    assert _run(days=0) == []
    assert _run(days=-3) == []


def test_clamping():
    assert _run(days=40) == _run(days=13)


def test_timezone_days():
    tz = timezone(timedelta(hours=14))
    pe = datetime(2026, 11, 3, 1, 0, tzinfo=tz)
    ch = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)  # Nov 3 02:00 local
    assert prorate_seats(_sub(period_end=pe), {"name": "T", "seat_price_cents": 1500}, ch) == []


def test_long_non_ascii_names():
    name = "Ünïcödé–Plan" * 20
    for line in _run(plan_name=name, name=name):
        assert len(line["description"]) <= 80
        assert line["description"].endswith("seats to 2026-11-03")
    only_date = _describe("Credit unused", "x" * 500, "2026-11-03")
    assert len(only_date) == 80 and only_date.endswith("2026-11-03")


def test_validation():
    import pytest
    for bad in (10.0, True, "10", None, -1):
        with pytest.raises((TypeError, ValueError)):
            _run(billable_seats=bad)
        with pytest.raises((TypeError, ValueError)):
            _run(seat_price_cents=bad)
        with pytest.raises((TypeError, ValueError)):
            _run(new_price=bad)
    s = _sub()
    del s["billable_seats"]
    with pytest.raises(ValueError):
        _run(sub=s)
    with pytest.raises(ValueError):
        prorate_seats(_sub(), {"name": "T", "seat_price_cents": 1500}, datetime(2026, 11, 1))
    with pytest.raises(ValueError):
        _run(period_end=datetime(2026, 11, 3))


def test_inputs_not_mutated():
    s = _sub()
    snap = dict(s)
    _run(sub=s)
    assert s == snap