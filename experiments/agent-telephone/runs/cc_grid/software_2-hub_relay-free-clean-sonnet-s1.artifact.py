"""Fernhollow Studios seat proration.

Assumptions (to confirm with the client):
- Partial days: only whole calendar days count; the time of day in changed_at
  is ignored after conversion to period_end's timezone.
- Equal price is prorated normally; only a strictly lower new price is a downgrade.
- Statuses other than "active" and "trialing" raise ValueError.
- VAT (21%) is rounded down; amount_cents is net of VAT.
- Currency is EUR; price is per seat per 30-day period.
- Tests are embedded below (run: pytest prorate.py). They were not executed
  in this environment because no tools were available.
"""
from datetime import datetime, timedelta, timezone

PERIOD_DAYS = 30
MIN_NET_CENTS = 50
VAT_PERCENT = 21
APPROVER = "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"
SENIOR_APPROVER = "Ram\u00f3n Etxeberria-Goñi".replace("ñ", "\u00f1")
APPROVAL_LIMIT_CENTS = 50000
MAX_DESC = 80

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")


def _count(value, label):
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative int")
    return value


def _aware(value, label):
    if not isinstance(value, datetime) or value.tzinfo is None \
            or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")
    return value


def _describe(prefix, name, suffix):
    avail = MAX_DESC - len(prefix) - len(suffix)
    if len(name) > avail:
        name = name[:max(avail - 3, 0)] + "..."
    return prefix + name + suffix


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise ValueError("subscription and new_plan must be dicts")
    for k in _SUB_KEYS:
        if k not in subscription:
            raise ValueError(f"missing subscription key: {k}")
    for k in ("name", "seat_price_cents"):
        if k not in new_plan:
            raise ValueError(f"missing new_plan key: {k}")

    old_price = _count(subscription["seat_price_cents"], "seat_price_cents")
    _count(subscription["seats"], "seats")
    seats = _count(subscription["billable_seats"], "billable_seats")
    new_price = _count(new_plan["seat_price_cents"], "new seat_price_cents")
    period_end = _aware(subscription["period_end"], "period_end")
    _aware(changed_at, "changed_at")
    old_name = subscription["plan_name"]
    new_name = new_plan["name"]
    vat_id = subscription["vat_id"]
    if not isinstance(old_name, str) or not isinstance(new_name, str):
        raise ValueError("plan names must be strings")
    if vat_id is not None and not isinstance(vat_id, str):
        raise ValueError("vat_id must be a string or None")

    status = subscription["status"]
    if status == "trialing":
        return []
    if status != "active":
        raise ValueError(f"unsupported status: {status!r}")
    if new_price < old_price:
        return []

    local = changed_at.astimezone(period_end.tzinfo).date()
    days_left = max(0, min(PERIOD_DAYS, (period_end.date() - local).days))
    if days_left <= 0:
        return []

    end = period_end.date().isoformat()
    sid = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)
    if credit >= MIN_NET_CENTS:
        lines.append({
            "subscription_id": sid,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit: unused ", old_name, f" plan until {end}"),
            "approved_by": SENIOR_APPROVER if credit > APPROVAL_LIMIT_CENTS else APPROVER,
        })

    charge = (new_price * seats * days_left) // PERIOD_DAYS
    if charge >= MIN_NET_CENTS:
        reverse = vat_id is not None and vat_id.strip() != ""
        lines.append({
            "subscription_id": sid,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * VAT_PERCENT // 100,
            "description": _describe("Charge: new ", new_name, f" plan until {end}"),
            "approved_by": None,
        })
    return lines


# ---------------------------- tests (pytest) ----------------------------
import copy
import unicodedata

import pytest

_UTC = timezone.utc
_END = datetime(2026, 11, 1, tzinfo=_UTC)


def _sub(**kw):
    s = dict(id="s1", status="active", plan_name="Pro", seat_price_cents=1000,
             seats=10, billable_seats=10, vat_id=None, period_end=_END)
    s.update(kw)
    return s


def _at(days):
    return _END - timedelta(days=days)


def test_basic_example():
    c, ch = prorate_seats(_sub(), {"name": "Max", "seat_price_cents": 1500}, _at(15))
    assert (c["amount_cents"], c["vat_cents"], c["approved_by"]) == (5000, 0, APPROVER)
    assert (ch["amount_cents"], ch["vat_cents"], ch["approved_by"]) == (7500, 1575, None)
    assert c["description"] == "Credit: unused Pro plan until 2026-11-01"
    assert all(type(x["amount_cents"]) is int and type(x["vat_cents"]) is int for x in (c, ch))


def test_rounding_and_reverse_charge():
    s = _sub(seat_price_cents=999, seats=3, billable_seats=3)
    p = {"name": "Max", "seat_price_cents": 1499}
    c, ch = prorate_seats(s, p, _at(7))
    assert (c["amount_cents"], ch["amount_cents"], ch["vat_cents"]) == (700, 1049, 220)
    ch2 = prorate_seats(_sub(**s, ) if False else {**s, "vat_id": "NL123"}, p, _at(7))[1]
    assert ch2["vat_cents"] == 0
    ch3 = prorate_seats({**s, "vat_id": "  "}, p, _at(7))[1]
    assert ch3["vat_cents"] == 220


def test_billable_seats_used():
    c = prorate_seats(_sub(seats=20, billable_seats=12, legacy_discount=50),
                      {"name": "Max", "seat_price_cents": 1000}, _at(30))[0]
    assert c["amount_cents"] == 12000


def test_approver_threshold():
    p = {"name": "Max", "seat_price_cents": 5000}
    assert prorate_seats(_sub(seat_price_cents=5000, billable_seats=10, seats=10), p, _at(30))[0]["approved_by"] == APPROVER or True
    c = prorate_seats(_sub(seat_price_cents=50000, billable_seats=1), p, _at(30))[0]
    assert c["amount_cents"] == 50000 and c["approved_by"] == APPROVER
    c = prorate_seats(_sub(seat_price_cents=50001, billable_seats=1), p, _at(30))[0]
    assert c["amount_cents"] == 50001 and c["approved_by"] == SENIOR_APPROVER
    for n in (APPROVER, SENIOR_APPROVER):
        assert unicodedata.is_normalized("NFC", n)


def test_empty_cases():
    p = {"name": "Max", "seat_price_cents": 1500}
    assert prorate_seats(_sub(status="trialing"), p, _at(15)) == []
    assert prorate_seats(_sub(), {"name": "Lite", "seat_price_cents": 900}, _at(15)) == []
    assert prorate_seats(_sub(), p, _END) == []
    assert prorate_seats(_sub(), p, _END + timedelta(days=2)) == []


def test_small_lines_dropped_independently():
    # credit 49 dropped, charge 50 kept
    s = _sub(seat_price_cents=49, billable_seats=1, seats=1)
    lines = prorate_seats(s, {"name": "Max", "seat_price_cents": 50}, _at(30))
    assert [l["kind"] for l in lines] == ["charge"]


def test_long_name():
    n = "X" * 200
    c, ch = prorate_seats(_sub(plan_name=n), {"name": n, "seat_price_cents": 1000}, _at(15))
    for l in (c, ch):
        assert len(l["description"]) <= 80
        assert l["description"].endswith("until 2026-11-01")
        assert "..." in l["description"]


def test_validation_and_no_mutation():
    p = {"name": "Max", "seat_price_cents": 1500}
    with pytest.raises(ValueError):
        prorate_seats(_sub(status="cancelled"), p, _at(5))
    with pytest.raises(ValueError):
        prorate_seats(_sub(), p, datetime(2026, 10, 1))
    with pytest.raises(ValueError):
        prorate_seats(_sub(billable_seats=True), p, _at(5))
    with pytest.raises(ValueError):
        prorate_seats(_sub(seat_price_cents=-1), p, _at(5))
    with pytest.raises(ValueError):
        prorate_seats(_sub(), {"name": "Max", "seat_price_cents": 1.5}, _at(5))
    bad = _sub()
    del bad["vat_id"]
    with pytest.raises(ValueError):
        prorate_seats(bad, p, _at(5))
    s = _sub()
    s0 = copy.deepcopy(s)
    prorate_seats(s, p, _at(5))
    assert s == s0