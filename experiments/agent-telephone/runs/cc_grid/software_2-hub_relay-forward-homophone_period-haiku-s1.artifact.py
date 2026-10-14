"""Seat upgrade proration for Fernhollow Studios.

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list[dict]

Assumptions for client confirmation:
- Unused days: whole days only. unused = floor((period_end - changed_at) / 24h),
  capped at PERIOD_DAYS (13). Partial days are not counted. See _unused_days().
- Amounts are EUR cents, since no currency field exists. APPROVAL_THRESHOLD_CENTS
  (50000) is the "over EUR 500" boundary. A credit of exactly 50000 is approved by
  the finance controller; above 50000 it goes to Ramon Etxeberria-Goñi.
- Credit = ceil(old_price * billable_seats * unused / 13).
  Charge = floor(new_price * billable_seats * unused / 13).
  All arithmetic is exact, using Fraction. Only the final values are rounded.
- Equal price is not a downgrade, but it returns []. The brief says equal prices
  produce no lines because of rounding. That is incorrect: with equal prices the
  credit and charge are ceil(x) and floor(x), which differ for non-integer x (for
  example 23077 and 23076). An explicit guard handles this case instead.
- Lines under 50 cents are dropped, judged on the net amount before VAT.
- VAT on charges is floor(21% of net) in integer cents, or 0 when vat_id is a
  non-empty string. Credits always have vat_cents = 0.
- Descriptions use the calendar date of period_end in its own timezone. If a plan
  name is too long, it is cut and marked with a trailing ellipsis; the date is never cut.
  If the name cannot fit at all, ValueError is raised.
- Approver names are fixed constants, not configurable.
- seats and legacy_discount are ignored.
"""

import math
from datetime import datetime, timedelta, timezone
from fractions import Fraction

PERIOD_DAYS = 13
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
APPROVAL_THRESHOLD_CENTS = 50000
DEFAULT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
MAX_DESCRIPTION_LEN = 80
TRIAL_STATUS = "trialing"


def _require_aware(dt, name):
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _unused_days(changed_at, period_end):
    """Whole days from changed_at to period_end (floored), capped at PERIOD_DAYS."""
    days = (period_end - changed_at) // timedelta(days=1)
    return min(days, PERIOD_DAYS)


def _credit_cents(price, seats, days):
    return math.ceil(Fraction(price * seats * days, PERIOD_DAYS))


def _charge_cents(price, seats, days):
    return math.floor(Fraction(price * seats * days, PERIOD_DAYS))


def _vat_cents(net, vat_id):
    if vat_id and str(vat_id).strip():
        return 0
    return net * VAT_PERCENT // 100


def _describe(plan_name, kind_word, period_end, limit=MAX_DESCRIPTION_LEN):
    if not plan_name:
        raise ValueError("plan name must not be empty")
    date = period_end.date().isoformat()
    suffix = f" {kind_word}, period ends {date}"
    avail = limit - len(suffix)
    if len(plan_name) <= avail:
        name = plan_name
    elif avail >= 2:
        name = plan_name[: avail - 1] + "…"
    else:
        raise ValueError("description cannot fit plan name and period end date")
    return name + suffix


def prorate_seats(subscription, new_plan, changed_at):
    _require_aware(changed_at, "changed_at")
    period_end = subscription["period_end"]
    _require_aware(period_end, "period_end")

    if subscription["status"] == TRIAL_STATUS:
        return []

    old_price = int(subscription["seat_price_cents"])
    new_price = int(new_plan["seat_price_cents"])
    # Downgrade: applies at renewal. Equal price: no change, no lines.
    if new_price <= old_price:
        return []
    if changed_at >= period_end:
        return []

    days = _unused_days(changed_at, period_end)
    seats = int(subscription["billable_seats"])
    sub_id = subscription["id"]
    lines = []

    credit = _credit_cents(old_price, seats, days)
    if credit >= MIN_LINE_CENTS:
        approver = (
            LARGE_CREDIT_APPROVER
            if credit > APPROVAL_THRESHOLD_CENTS
            else DEFAULT_APPROVER
        )
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe(subscription["plan_name"], "seat credit", period_end),
            "approved_by": approver,
        })

    charge = _charge_cents(new_price, seats, days)
    if charge >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": _vat_cents(charge, subscription.get("vat_id")),
            "description": _describe(new_plan["name"], "seat charge", period_end),
            "approved_by": None,
        })

    return lines


# ---------------------------------------------------------------------------
# Tests (run with pytest, or `python3 -I <this file>` for a stdlib runner)
# ---------------------------------------------------------------------------

UTC = timezone.utc
END = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def _sub(**over):
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Studio Basic",
        "seat_price_cents": 1000,
        "seats": 5,
        "billable_seats": 1,
        "vat_id": None,
        "period_end": END,
        "legacy_discount": 0,
    }
    base.update(over)
    return base


def _plan(price, name="Studio Pro"):
    return {"name": name, "seat_price_cents": price}


def _raises(exc, fn, *args):
    try:
        fn(*args)
    except exc:
        return True
    return False


def test_rounding_directions():
    lines = prorate_seats(_sub(), _plan(2000), END - timedelta(days=1))
    credit, charge = lines
    assert credit["amount_cents"] == 77    # ceil(1000/13) = ceil(76.92)
    assert charge["amount_cents"] == 153   # floor(2000/13) = floor(153.84)
    assert isinstance(credit["amount_cents"], int)
    assert isinstance(charge["amount_cents"], int)


def test_partial_day_is_floored():
    a = prorate_seats(_sub(), _plan(2000), END - timedelta(hours=36))
    b = prorate_seats(_sub(), _plan(2000), END - timedelta(days=1))
    assert a == b


def test_fifty_cent_boundary():
    # credit exactly 50 kept, charge exactly 50 kept
    lines = prorate_seats(_sub(seat_price_cents=650), _plan(651), END - timedelta(days=1))
    assert [l["amount_cents"] for l in lines] == [50, 50]
    # credit 49 dropped, charge 50 kept
    lines = prorate_seats(_sub(seat_price_cents=637), _plan(651), END - timedelta(days=1))
    assert [(l["kind"], l["amount_cents"]) for l in lines] == [("charge", 50)]
    # credit 47 and charge 49 both dropped
    assert prorate_seats(_sub(seat_price_cents=600), _plan(637), END - timedelta(days=1)) == []


def test_vat_without_and_with_vat_id():
    lines = prorate_seats(_sub(), _plan(2000), END - timedelta(days=1))
    credit, charge = lines
    assert charge["vat_cents"] == 32       # floor(153 * 0.21) = 32
    assert credit["vat_cents"] == 0
    lines = prorate_seats(_sub(vat_id="DE123456789"), _plan(2000), END - timedelta(days=1))
    assert lines[1]["vat_cents"] == 0
    assert lines[0]["vat_cents"] == 0
    lines = prorate_seats(_sub(vat_id=""), _plan(2000), END - timedelta(days=1))
    assert lines[1]["vat_cents"] == 32


def test_approval_boundary():
    at13 = END - timedelta(days=13)
    lines = prorate_seats(_sub(seat_price_cents=50000), _plan(50001), at13)
    assert lines[0]["amount_cents"] == 50000
    assert lines[0]["approved_by"] == DEFAULT_APPROVER
    lines = prorate_seats(_sub(seat_price_cents=50001), _plan(50002), at13)
    assert lines[0]["amount_cents"] == 50001
    assert lines[0]["approved_by"] == LARGE_CREDIT_APPROVER
    assert lines[1]["approved_by"] is None


def test_downgrade_returns_nothing():
    assert prorate_seats(_sub(seat_price_cents=2000), _plan(1000), END - timedelta(days=5)) == []


def test_equal_price_returns_nothing():
    # Non-integer base (10000 * 3 * 10 / 13) would otherwise yield lines.
    assert prorate_seats(_sub(seat_price_cents=10000, billable_seats=3),
                         _plan(10000), END - timedelta(days=10)) == []


def test_trialing_returns_nothing():
    assert prorate_seats(_sub(status="trialing"), _plan(2000), END - timedelta(days=1)) == []


def test_changed_at_on_or_after_period_end():
    assert prorate_seats(_sub(), _plan(2000), END) == []
    assert prorate_seats(_sub(), _plan(2000), END + timedelta(days=1)) == []


def test_naive_datetime_rejected():
    naive = datetime(2026, 10, 31, 12, 0)
    assert _raises(ValueError, prorate_seats, _sub(), _plan(2000), naive)
    assert _raises(ValueError, prorate_seats, _sub(period_end=datetime(2026, 11, 1)),
                   _plan(2000), END - timedelta(days=1))


def test_credit_before_charge():
    lines = prorate_seats(_sub(), _plan(2000), END - timedelta(days=1))
    assert [l["kind"] for l in lines] == ["credit", "charge"]


def test_seats_field_ignored():
    a = prorate_seats(_sub(seats=1), _plan(2000), END - timedelta(days=1))
    b = prorate_seats(_sub(seats=999), _plan(2000), END - timedelta(days=1))
    assert a == b
    c = prorate_seats(_sub(seats=999, billable_seats=2), _plan(2000), END - timedelta(days=1))
    d = prorate_seats(_sub(seats=2, billable_seats=2), _plan(2000), END - timedelta(days=1))
    assert c == d


def test_description_names_plan_and_date():
    credit, charge = prorate_seats(_sub(), _plan(2000), END - timedelta(days=1))
    assert credit["description"] == "Studio Basic seat credit, period ends 2026-11-01"
    assert charge["description"] == "Studio Pro seat charge, period ends 2026-11-01"
    assert len(credit["description"]) <= 80 and len(charge["description"]) <= 80


def test_long_plan_name_shortened_date_kept():
    long_name = "X" * 200
    credit, _ = prorate_seats(_sub(plan_name=long_name), _plan(2000), END - timedelta(days=1))
    desc = credit["description"]
    assert len(desc) <= MAX_DESCRIPTION_LEN
    assert desc.endswith("seat credit, period ends 2026-11-01")
    assert desc.startswith("X")


def test_description_unfit_raises_and_never_cuts_date():
    assert _raises(ValueError, _describe, "Studio", "seat credit", END, 10)
    out = _describe("Studio Basic Plus Extra", "seat credit", END, 45)
    assert out.endswith("2026-11-01")


if __name__ == "__main__":
    for _name, _fn in list(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print("ok", _name)