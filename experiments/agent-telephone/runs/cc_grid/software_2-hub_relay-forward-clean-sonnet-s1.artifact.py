import re
from datetime import datetime, timedelta

CONTROLLER = "Nguyễn Thị Phương Thảo"
SENIOR = "Ramón Etxeberria-Goñi"
MAX_DESC = 80
MIN_CENTS = 50
PERIOD_DAYS = 30
VAT_PERCENT = 21
SENIOR_LIMIT_CENTS = 50000


def _describe(prefix: str, name: str, date: str) -> str:
    suffix = f" seats until {date}"
    room = MAX_DESC - len(prefix) - len(suffix)
    if len(name) > room:
        name = name[: max(room - 1, 0)] + "…"
    return prefix + name + suffix


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription["period_end"]
    for dt in (changed_at, period_end):
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError("datetimes must be timezone-aware")

    if subscription["status"] in ("trialing", "canceled"):
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:
        return []
    seats = subscription["billable_seats"]
    if seats == 0:
        return []

    days_left = max(0, min(PERIOD_DAYS, (period_end - changed_at).days))
    date = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)
    if credit >= MIN_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit unused ", subscription["plan_name"], date),
            "approved_by": SENIOR if credit > SENIOR_LIMIT_CENTS else CONTROLLER,
        })

    charge = (new_price * seats * days_left) // PERIOD_DAYS
    if charge >= MIN_CENTS:
        vat = 0 if subscription.get("vat_id") else (charge * VAT_PERCENT + 50) // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe("Charge ", new_plan["name"], date),
            "approved_by": None,
        })
    return lines


# ---------------------------------------------------------------- tests
from copy import deepcopy
from datetime import timezone

import pytest

END = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 99, "billable_seats": 10,
         "vat_id": None, "period_end": END, "legacy_discount": 50}
    s.update(kw)
    return s


def _plan(price=1500, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def _at(days):
    return END - timedelta(days=days)


def test_basic_upgrade():
    sub = _sub()
    snapshot = deepcopy(sub)
    credit, charge = prorate_seats(sub, _plan(), _at(15))
    assert sub == snapshot
    assert credit["kind"] == "credit" and credit["amount_cents"] == 5000
    assert credit["vat_cents"] == 0 and credit["approved_by"] == CONTROLLER
    assert charge["amount_cents"] == 7500 and charge["vat_cents"] == 1575
    assert charge["approved_by"] is None
    assert credit["description"] == "Credit unused Basic seats until 2026-11-01"
    assert charge["description"] == "Charge Pro seats until 2026-11-01"
    assert credit["subscription_id"] == "sub_1"
    for line in (credit, charge):
        assert type(line["amount_cents"]) is int and type(line["vat_cents"]) is int


def test_vat_id_reverse_charge():
    _, charge = prorate_seats(_sub(vat_id="PT123"), _plan(), _at(15))
    assert charge["vat_cents"] == 0


def test_credit_rounds_up_charge_down():
    lines = prorate_seats(_sub(seat_price_cents=999, billable_seats=1), _plan(1000), _at(7))
    assert lines[0]["amount_cents"] == 234  # 233.1 up
    assert lines[1]["amount_cents"] == 233  # 233.33 down


def test_approver_threshold():
    l = prorate_seats(_sub(billable_seats=50), _plan(1001), _at(30))
    assert l[0]["amount_cents"] == 50000 and l[0]["approved_by"] == CONTROLLER
    l = prorate_seats(_sub(billable_seats=51), _plan(1001), _at(30))
    assert l[0]["amount_cents"] == 51000 and l[0]["approved_by"] == SENIOR


def test_min_50_each_line_independent():
    assert prorate_seats(_sub(seat_price_cents=10, billable_seats=1), _plan(11), _at(15)) == []
    l = prorate_seats(_sub(seat_price_cents=100, billable_seats=1), _plan(110), _at(14))
    assert [x["kind"] for x in l] == ["charge"] and l[0]["amount_cents"] == 51
    l = prorate_seats(_sub(seat_price_cents=99, billable_seats=1), _plan(100), _at(15))
    assert [x["amount_cents"] for x in l] == [50, 50]


def test_empty_cases():
    assert prorate_seats(_sub(status="trialing"), _plan(), _at(15)) == []
    assert prorate_seats(_sub(status="canceled"), _plan(), _at(15)) == []
    assert prorate_seats(_sub(), _plan(500), _at(15)) == []
    assert prorate_seats(_sub(), _plan(1000), _at(15)) == []
    assert prorate_seats(_sub(billable_seats=0), _plan(), _at(15)) == []


def test_days_clamped_and_floored():
    l = prorate_seats(_sub(), _plan(), _at(90))
    assert l[0]["amount_cents"] == 10000
    assert prorate_seats(_sub(), _plan(), END + timedelta(days=3)) == []
    l = prorate_seats(_sub(), _plan(), _at(15) - timedelta(hours=23))
    assert l[0]["amount_cents"] == 5000  # 15 days 23h floors to 15


def test_naive_raises():
    with pytest.raises(ValueError):
        prorate_seats(_sub(), _plan(), datetime(2026, 10, 1))
    with pytest.raises(ValueError):
        prorate_seats(_sub(period_end=datetime(2026, 11, 1)), _plan(), _at(15))


def test_long_names_keep_date():
    l = prorate_seats(_sub(plan_name="A" * 200), _plan(name="é" * 200), _at(15))
    for line in l:
        assert len(line["description"]) <= 80
        assert line["description"].endswith(" seats until 2026-11-01")
        assert "…" in line["description"]
    assert len(l[0]["description"]) == 80


def test_period_end_own_calendar_date():
    pe = datetime(2026, 11, 1, 23, 30, tzinfo=timezone(timedelta(hours=-5)))
    l = prorate_seats(_sub(period_end=pe), _plan(), pe - timedelta(days=15))
    assert l[0]["description"].endswith("2026-11-01")


def test_uses_billable_seats():
    l = prorate_seats(_sub(seats=1000, billable_seats=10), _plan(), _at(15))
    assert l[0]["amount_cents"] == 5000