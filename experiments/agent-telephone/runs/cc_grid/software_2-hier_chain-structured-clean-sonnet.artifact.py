"""prorate_seats: prorated seat credit/charge invoice lines for a plan change.

Tests are embedded below (run: pytest prorate_seats.py). They were NOT executed
when this was written, since no tools were available.

Design decisions:
D1 remaining = period_end - changed_at (signed, aware datetimes, so timezones
   are handled by datetime subtraction), measured in integer microseconds and
   capped at 30 days. remaining <= 0 -> []. Credit = ceil(n/d), charge = n//d,
   with n = billable_seats * price * remaining_us and d = 30*86400*10**6.
D2 Credit uses the old price/name, charge the new price/name, both on billable_seats.
D3 Downgrade = new price strictly lower -> []. Equal price is prorated normally.
D4 A line with net amount_cents < 50 is skipped; each line is decided independently.
D5 Charge VAT = net*21//100, 0 if vat_id is a non-blank string. Credit VAT is 0.
D6 Credit > 50000 cents is approved by the second approver. Currency is EUR.
D7 Amounts are positive; kind carries the sign.
D8 Descriptions "Credit unused {plan} until {date}" / "Charge prorated {plan} until {date}",
   date = period_end's own-timezone date. Only the plan name is shortened (with "..."),
   total <= 80 characters, date never cut.
D9 status "trialing" -> []; "active" proceeds; anything else raises ValueError
   (open question for the client).
D10 Invalid input raises ValueError/TypeError. legacy_discount is ignored. Inputs are not mutated.
"""
from datetime import datetime, timedelta

APPROVER = "Nguyễn Thị Phương Thảo"
APPROVER_HIGH = "Ramón Etxeberria-Goñi"
_DEN = 30 * 86400 * 10**6
_MAX_DESC = 80


def _int(d, key, what):
    if key not in d:
        raise ValueError(f"missing key {key!r} in {what}")
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{what}[{key!r}] must be an int")
    if v < 0:
        raise ValueError(f"{what}[{key!r}] must not be negative")
    return v


def _aware(v, name):
    if not isinstance(v, datetime):
        raise TypeError(f"{name} must be a datetime")
    if v.tzinfo is None or v.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _desc(prefix, plan, date):
    suffix = f" until {date}"
    text = prefix + plan + suffix
    if len(text) <= _MAX_DESC:
        return text
    avail = _MAX_DESC - len(prefix) - len(suffix)
    plan = plan[: avail - 3] + "..." if avail >= 3 else "..."
    prefix = prefix[: max(0, _MAX_DESC - len(plan) - len(suffix))]
    return prefix + plan + suffix


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription.get("period_end")
    _aware(changed_at, "changed_at")
    _aware(period_end, "period_end")
    status = subscription.get("status")
    if status == "trialing":
        return []
    if status != "active":
        raise ValueError(f"unsupported subscription status: {status!r}")
    for k in ("id", "plan_name", "vat_id"):
        if k not in subscription:
            raise ValueError(f"missing key {k!r} in subscription")
    old_price = _int(subscription, "seat_price_cents", "subscription")
    _int(subscription, "seats", "subscription")
    seats = _int(subscription, "billable_seats", "subscription")
    if "name" not in new_plan:
        raise ValueError("missing key 'name' in new_plan")
    new_price = _int(new_plan, "seat_price_cents", "new_plan")
    old_name, new_name = str(subscription["plan_name"]), str(new_plan["name"])

    if new_price < old_price:
        return []
    remaining = (period_end - changed_at) // timedelta(microseconds=1)
    if remaining <= 0:
        return []
    remaining = min(remaining, _DEN)

    date = period_end.date().isoformat()
    vat_id = subscription["vat_id"]
    reverse = isinstance(vat_id, str) and vat_id.strip() != ""
    lines = []

    credit = -(-(seats * old_price * remaining) // _DEN)
    if credit >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _desc("Credit unused ", old_name, date),
            "approved_by": APPROVER_HIGH if credit > 50000 else APPROVER,
        })
    charge = (seats * new_price * remaining) // _DEN
    if charge >= 50:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * 21 // 100,
            "description": _desc("Charge prorated ", new_name, date),
            "approved_by": None,
        })
    return lines


# ---------------------------------------------------------------- tests
import copy
from datetime import timezone

import pytest

_END = datetime(2025, 1, 31, 0, 0, tzinfo=timezone.utc)


def _sub(**kw):
    s = {"id": "s1", "status": "active", "plan_name": "Basic", "seat_price_cents": 1000,
         "seats": 10, "billable_seats": 10, "vat_id": None, "period_end": _END}
    s.update(kw)
    return s


def _new(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def _run(sub=None, new=None, days=15):
    return prorate_seats(sub or _sub(), new or _new(), _END - timedelta(days=days))


def test_basic_order_and_exact_values():
    c, ch = _run()
    assert (c["kind"], ch["kind"]) == ("credit", "charge")
    assert (c["amount_cents"], ch["amount_cents"], ch["vat_cents"]) == (5000, 10000, 2100)
    assert list(c) == ["subscription_id", "kind", "amount_cents", "vat_cents",
                       "description", "approved_by"]
    assert c["subscription_id"] == "s1" and ch["approved_by"] is None
    assert "Basic" in c["description"] and c["description"].endswith("2025-01-31")


def test_rounding_credit_up_charge_down():
    s = _sub(seats=1, billable_seats=1, seat_price_cents=1000)
    c, ch = _run(s, _new(1001), days=2)
    assert c["amount_cents"] == 67 and ch["amount_cents"] == 66


def test_billable_vs_seats():
    c, _ = _run(_sub(seats=99, billable_seats=2))
    assert c["amount_cents"] == 1000


def test_downgrade_and_equal():
    assert _run(new=_new(500)) == []
    c, ch = _run(new=_new(1000))
    assert c["amount_cents"] == ch["amount_cents"] == 5000


def test_status():
    assert _run(_sub(status="trialing")) == []
    with pytest.raises(ValueError):
        _run(_sub(status="canceled"))


def test_remaining_nonpositive_and_cap():
    assert prorate_seats(_sub(), _new(), _END) == []
    assert prorate_seats(_sub(), _new(), _END + timedelta(days=1)) == []
    capped = _run(days=90)
    assert capped == _run(days=30) and capped[0]["amount_cents"] == 10000


def test_fractional_and_timezone():
    pe = datetime(2025, 1, 31, 12, 0, tzinfo=timezone(timedelta(hours=5)))
    at = datetime(2025, 1, 30, 19, 0, tzinfo=timezone.utc)  # 12h left
    s = _sub(seats=1, billable_seats=1, seat_price_cents=6000, period_end=pe)
    c, ch = prorate_seats(s, _new(9000), at)
    assert (c["amount_cents"], ch["amount_cents"]) == (100, 150)
    assert c["description"].endswith("2025-01-31")


def test_min_amount_per_line():
    s = _sub(seats=1, billable_seats=1, seat_price_cents=49)
    out = _run(s, _new(50), days=30)
    assert len(out) == 1 and out[0]["kind"] == "charge" and out[0]["amount_cents"] == 50
    assert out[0]["vat_cents"] == 10
    assert _run(_sub(seats=0, billable_seats=0)) == []


def test_vat():
    s = _sub(seats=1, billable_seats=1, seat_price_cents=100)
    _, ch = _run(s, _new(333), days=30)
    assert ch["amount_cents"] == 333 and ch["vat_cents"] == 69
    c, ch = _run(_sub(vat_id="NL123"))
    assert c["vat_cents"] == 0 and ch["vat_cents"] == 0
    assert _run(_sub(vat_id="  "))[1]["vat_cents"] == 2100


def test_approval():
    assert APPROVER == "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"
    assert APPROVER_HIGH == "Ram\u00f3n Etxeberria-Go\u00f1i"
    lo = _run(_sub(seats=1, billable_seats=1, seat_price_cents=50000), _new(60000), 30)[0]
    hi = _run(_sub(seats=1, billable_seats=1, seat_price_cents=50001), _new(60000), 30)[0]
    assert lo["approved_by"] == APPROVER and hi["approved_by"] == APPROVER_HIGH


def test_long_description():
    for out in (_run(_sub(plan_name="X" * 200), _new(name="Y" * 200))):
        assert len(out["description"]) <= 80
        assert out["description"].endswith(" until 2025-01-31")
        assert "..." in out["description"]


def test_types():
    for line in _run():
        assert type(line["amount_cents"]) is int and type(line["vat_cents"]) is int


def test_invalid_input():
    with pytest.raises(ValueError):
        prorate_seats(_sub(), _new(), datetime(2025, 1, 1))
    with pytest.raises(TypeError):
        _run(_sub(billable_seats=True))
    with pytest.raises(TypeError):
        _run(_sub(seat_price_cents=10.0))


def test_no_mutation_and_legacy_discount():
    s, n = _sub(legacy_discount=50), _new()
    s0, n0 = copy.deepcopy(s), copy.deepcopy(n)
    out = prorate_seats(s, n, _END - timedelta(days=15))
    assert s == s0 and n == n0 and out == _run()