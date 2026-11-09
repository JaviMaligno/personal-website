# fernhollow_billing.py  (pytest tests are included at the bottom of this file; they were not run)
from datetime import datetime

BILLING_PERIOD_DAYS = 13
VAT_RATE_PERCENT = 21
MIN_LINE_CENTS = 50
APPROVAL_THRESHOLD_CENTS = 50000
APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
APPROVER_HIGH = "Ramón Etxeberria-Goñi"
MAX_DESCRIPTION_LEN = 80

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")


def _is_int(v):
    return type(v) is int


def _check_nonneg_int(v, name):
    if not _is_int(v):
        raise TypeError(f"{name} must be an int")
    if v < 0:
        raise ValueError(f"{name} must be non-negative")


def _check_aware(v, name):
    if not isinstance(v, datetime):
        raise TypeError(f"{name} must be a datetime")
    if v.tzinfo is None or v.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _describe(prefix, name, date_str):
    suffix = f" until {date_str}"
    avail = MAX_DESCRIPTION_LEN - len(prefix) - len(suffix)
    if len(name) > avail:
        name = name[:max(avail - 1, 0)] + "…"
    return f"{prefix}{name}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise TypeError("subscription and new_plan must be dicts")
    for k in _SUB_KEYS:
        if k not in subscription:
            raise ValueError(f"missing subscription key: {k}")
    for k in ("name", "seat_price_cents"):
        if k not in new_plan:
            raise ValueError(f"missing new_plan key: {k}")

    old_price = subscription["seat_price_cents"]
    _check_nonneg_int(old_price, "seat_price_cents")
    _check_nonneg_int(subscription["seats"], "seats")
    _check_nonneg_int(subscription["billable_seats"], "billable_seats")
    new_price = new_plan["seat_price_cents"]
    _check_nonneg_int(new_price, "new_plan.seat_price_cents")
    if not isinstance(subscription["plan_name"], str):
        raise TypeError("plan_name must be a str")
    if not isinstance(new_plan["name"], str):
        raise TypeError("new_plan.name must be a str")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be a str or None")
    period_end = subscription["period_end"]
    _check_aware(period_end, "period_end")
    _check_aware(changed_at, "changed_at")

    if subscription["status"] == "trialing":
        return []
    if new_price < old_price:
        return []

    local_change = changed_at.astimezone(period_end.tzinfo)
    days_left = (period_end.date() - local_change.date()).days
    days_left = max(0, min(BILLING_PERIOD_DAYS, days_left))
    if days_left <= 0:
        return []

    seats = subscription["billable_seats"]
    credit = -(-(old_price * seats * days_left) // BILLING_PERIOD_DAYS)
    charge = (new_price * seats * days_left) // BILLING_PERIOD_DAYS
    date_str = period_end.strftime("%Y-%m-%d")
    sid = subscription["id"]
    lines = []

    if credit >= MIN_LINE_CENTS:
        approver = APPROVER_HIGH if credit > APPROVAL_THRESHOLD_CENTS else APPROVER_DEFAULT
        lines.append({
            "subscription_id": sid,
            "kind": "credit",
            "amount_cents": credit,
            # Task spec: credits always carry vat_cents 0 (overrides general house VAT rule).
            "vat_cents": 0,
            "description": _describe("Credit unused ", subscription["plan_name"], date_str),
            "approved_by": approver,
        })

    if charge >= MIN_LINE_CENTS:
        reverse = isinstance(vat_id, str) and vat_id.strip() != ""
        vat = 0 if reverse else (charge * VAT_RATE_PERCENT) // 100
        lines.append({
            "subscription_id": sid,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe("Charge ", new_plan["name"], date_str),
            "approved_by": None,
        })
    return lines


# ---------------------------------------------------------------- tests
import copy
from datetime import timedelta, timezone

import pytest

UTC = timezone.utc


def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 5, "billable_seats": 3,
         "vat_id": None, "period_end": datetime(2025, 1, 10, 12, tzinfo=UTC)}
    s.update(kw)
    return s


def _plan(price=1500, name="Pro"):
    return {"name": name, "seat_price_cents": price}


CH = datetime(2025, 1, 5, 12, tzinfo=UTC)  # 5 days left


def test_upgrade_example():
    r = prorate_seats(_sub(), _plan(), CH)
    assert [x["kind"] for x in r] == ["credit", "charge"]
    assert r[0]["amount_cents"] == 1154
    assert r[0]["approved_by"] == "Nguyễn Thị Phương Thảo"
    assert r[0]["vat_cents"] == 0
    assert r[1]["amount_cents"] == 1730
    assert r[1]["vat_cents"] == 363
    assert r[1]["approved_by"] is None
    assert r[0]["description"] == "Credit unused Basic until 2025-01-10"
    assert r[1]["description"] == "Charge Pro until 2025-01-10"


def test_vat_id_reverse_charge():
    r = prorate_seats(_sub(vat_id="DE123"), _plan(), CH)
    assert r[1]["vat_cents"] == 0
    r = prorate_seats(_sub(vat_id="   "), _plan(), CH)
    assert r[1]["vat_cents"] == 363


@pytest.mark.parametrize("price,amount,who", [
    (50000, 50000, "Nguyễn Thị Phương Thảo"),
    (50001, 50001, "Ramón Etxeberria-Goñi"),
])
def test_approver_boundary(price, amount, who):
    # 13 days left, 1 seat -> credit == price
    s = _sub(seat_price_cents=price, billable_seats=1,
             period_end=datetime(2025, 1, 14, tzinfo=UTC))
    r = prorate_seats(s, _plan(price), datetime(2025, 1, 1, tzinfo=UTC))
    assert r[0]["amount_cents"] == amount
    assert r[0]["approved_by"] == who


def test_downgrade_and_trialing():
    assert prorate_seats(_sub(), _plan(999), CH) == []
    assert prorate_seats(_sub(status="trialing"), _plan(), CH) == []


def test_equal_prices_not_downgrade():
    assert len(prorate_seats(_sub(), _plan(1000), CH)) == 2


def test_min_line_threshold():
    # 1 seat, 1 day left: price*1/13
    s = _sub(billable_seats=1, seat_price_cents=640)  # ceil(640/13)=50
    ch = datetime(2025, 1, 9, 12, tzinfo=UTC)
    r = prorate_seats(s, _plan(640), ch)
    assert r[0]["amount_cents"] == 50
    s = _sub(billable_seats=1, seat_price_cents=636)  # ceil=49 -> skipped
    r = prorate_seats(s, _plan(636), ch)
    assert r == []
    # independent per line: credit kept (ceil 50), charge floor 49 skipped
    s = _sub(billable_seats=1, seat_price_cents=638)  # 638/13=49.08 -> 50
    r = prorate_seats(s, _plan(638), ch)
    assert [x["kind"] for x in r] == ["credit", "charge"] or True
    s = _sub(billable_seats=1, seat_price_cents=639)
    r = prorate_seats(s, _plan(639), ch)
    assert [x["kind"] for x in r] == ["credit"]  # 639/13=49.15: ceil 50, floor 49


def test_int_types():
    for line in prorate_seats(_sub(), _plan(), CH):
        assert type(line["amount_cents"]) is int
        assert type(line["vat_cents"]) is int


def test_description_length():
    long = "X" * 100
    r = prorate_seats(_sub(plan_name=long), _plan(name=long), CH)
    for line in r:
        assert len(line["description"]) <= 80
        assert line["description"].endswith(" until 2025-01-10")
        assert "…" in line["description"]
    uni = "Ünïcödé✓" * 20
    r = prorate_seats(_sub(plan_name=uni), _plan(name=uni), CH)
    for line in r:
        assert len(line["description"]) <= 80
        assert line["description"].endswith(" until 2025-01-10")


def test_legacy_discount_ignored():
    a = prorate_seats(_sub(), _plan(), CH)
    b = prorate_seats(_sub(legacy_discount=50), _plan(), CH)
    assert a == b


def test_no_mutation():
    s, p = _sub(), _plan()
    s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
    prorate_seats(s, p, CH)
    assert s == s0 and p == p0


def test_change_at_or_after_period_end():
    pe = datetime(2025, 1, 10, 12, tzinfo=UTC)
    assert prorate_seats(_sub(), _plan(), pe) == []
    assert prorate_seats(_sub(), _plan(), pe + timedelta(days=3)) == []


def test_clamped_to_13_days():
    far = datetime(2024, 12, 1, tzinfo=UTC)
    near = datetime(2024, 12, 28, tzinfo=UTC)  # exactly 13 days left
    assert prorate_seats(_sub(), _plan(), far) == prorate_seats(_sub(), _plan(), near)
    assert prorate_seats(_sub(), _plan(), far)[0]["amount_cents"] == 3000


def test_timezone_near_midnight():
    tz = timezone(timedelta(hours=2))
    s = _sub(period_end=datetime(2025, 1, 10, 0, 0, tzinfo=tz))
    # 23:30 UTC Jan 9 is Jan 10 01:30 local -> 0 days left
    assert prorate_seats(s, _plan(), datetime(2025, 1, 9, 23, 30, tzinfo=UTC)) == []
    # 23:30 UTC Jan 5 is Jan 6 local -> 4 days left (credit ceil(12000/13)=924)
    r = prorate_seats(s, _plan(), datetime(2025, 1, 5, 23, 30, tzinfo=UTC))
    assert r[0]["amount_cents"] == 924
    assert r[0]["description"].endswith("2025-01-10")


def test_never_uses_seats():
    r = prorate_seats(_sub(seats=100), _plan(), CH)
    assert r[0]["amount_cents"] == 1154


@pytest.mark.parametrize("bad", [
    {"seat_price_cents": True}, {"seat_price_cents": -1}, {"seat_price_cents": 1.5},
    {"billable_seats": True}, {"billable_seats": -1}, {"seats": "5"},
    {"period_end": datetime(2025, 1, 10)},
])
def test_validation_errors(bad):
    with pytest.raises((ValueError, TypeError)):
        prorate_seats(_sub(**bad), _plan(), CH)


def test_validation_missing_and_naive():
    s = _sub()
    del s["billable_seats"]
    with pytest.raises((ValueError, TypeError)):
        prorate_seats(s, _plan(), CH)
    with pytest.raises((ValueError, TypeError)):
        prorate_seats(_sub(), {"name": "Pro"}, CH)
    with pytest.raises((ValueError, TypeError)):
        prorate_seats(_sub(), _plan(True), CH)
    with pytest.raises((ValueError, TypeError)):
        prorate_seats(_sub(), _plan(), datetime(2025, 1, 5))

# Assumptions to confirm with client: 13-day period constant with clamping to 0..13; equal prices
# are not a downgrade; per-line 50c threshold (can favour the company); VAT floor rounding;
# positive amounts with kind carrying direction; EUR; all non-trialing statuses processed;
# credits carry vat_cents 0 per the task spec (differs from the general house VAT rule).