"""Fernhollow Studios seat proration (Python 3.12, stdlib only).

Files: this single module. The pytest tests (R19) are the test_* functions at the
bottom, so run: python -m pytest <this file>
Test results: I had no tools in this run, so the tests have NOT been executed.

House-rule overrides (the requirements said otherwise): rounding is ceil for
credits and floor for charges (R7), not half-up, and credits carry vat_cents = 0
(R8), not VAT.

[DEFAULT] assumptions (PM defaults, not confirmed by the client):
  - amount_cents is net of VAT.
  - Description templates (CREDIT_TEMPLATE, CHARGE_TEMPLATE).
  - days_left = floor of whole 24h days, clamped to 0..PERIOD_DAYS.
  - VAT is floored (VAT_ROUNDING / vat_for).
  - Statuses other than "trialing" prorate normally (is_prorated_status).
  - Equal per-seat price, including a rename at the same price, returns [].
  - Currency is EUR.

Open questions for the client:
  1. Is the 13-day period intentional (PERIOD_DAYS = 13)?
  2. Floor whole days vs exact elapsed time? Floor of days favours the company on
     credits, which sits awkwardly with the no-rounding-in-our-favour rule.
  3. Is flooring VAT acceptable?
  4. What should happen for statuses other than trialing?
  5. Is the description wording right?
  6. Should equal price return no lines?
  7. The per-line 50-cent skip can drop only one line. A dropped small credit
     favours the company.
"""
import unicodedata
from datetime import datetime, timedelta

PERIOD_DAYS = 13
MIN_AMOUNT_CENTS = 50
VAT_PERCENT = 21
MAX_DESCRIPTION = 80
APPROVAL_THRESHOLD_CENTS = 50000
APPROVER_DEFAULT = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
APPROVER_HIGH = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")
CREDIT_TEMPLATE = "Credit: unused {plan} seats until {date}"  # [DEFAULT]
CHARGE_TEMPLATE = "Charge: {plan} seats until {date}"  # [DEFAULT]

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def is_prorated_status(status):
    """[DEFAULT] Only trialing is not prorated."""
    return status != "trialing"


def vat_for(amount_cents):
    """[DEFAULT] floor(amount * 21 / 100)."""
    return amount_cents * VAT_PERCENT // 100


def _check_int(value, label):
    if type(value) is not int:
        raise TypeError(f"{label} must be an int")
    if value < 0:
        raise ValueError(f"{label} must not be negative")


def _check_aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _description(template, plan, period_end):
    date = period_end.strftime("%Y-%m-%d")
    avail = MAX_DESCRIPTION - len(template.format(plan="", date=date))
    plan = str(plan)
    if len(plan) > avail:
        plan = plan[:max(0, avail - 3)].rstrip() + "..."
        plan = plan[:max(0, avail)]
    return template.format(plan=plan, date=date)


def prorate_seats(subscription, new_plan, changed_at):
    for k in _SUB_KEYS:
        if k not in subscription:
            raise ValueError(f"missing subscription key: {k}")
    for k in _PLAN_KEYS:
        if k not in new_plan:
            raise ValueError(f"missing new_plan key: {k}")
    period_end = subscription["period_end"]
    _check_aware(changed_at, "changed_at")
    _check_aware(period_end, "period_end")
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    seats = subscription["billable_seats"]
    _check_int(old_price, "seat_price_cents")
    _check_int(new_price, "new_plan seat_price_cents")
    _check_int(seats, "billable_seats")

    if not is_prorated_status(subscription["status"]):
        return []
    if seats == 0 or new_price <= old_price:  # R4, R6, R18
        return []
    if changed_at >= period_end:
        return []
    days = (period_end - changed_at) // timedelta(days=1)
    days = max(0, min(PERIOD_DAYS, days))

    credit_raw = old_price * seats * days
    charge_raw = new_price * seats * days
    credit = -(-credit_raw // PERIOD_DAYS)
    charge = charge_raw // PERIOD_DAYS

    sid = subscription["id"]
    out = []
    if credit >= MIN_AMOUNT_CENTS:
        out.append({
            "subscription_id": sid,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(CREDIT_TEMPLATE, subscription["plan_name"], period_end),
            "approved_by": APPROVER_HIGH if credit > APPROVAL_THRESHOLD_CENTS else APPROVER_DEFAULT,
        })
    if charge >= MIN_AMOUNT_CENTS:
        vat_id = subscription["vat_id"]
        reverse = isinstance(vat_id, str) and vat_id.strip() != ""
        out.append({
            "subscription_id": sid,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else vat_for(charge),
            "description": _description(CHARGE_TEMPLATE, new_plan["name"], period_end),
            "approved_by": None,
        })
    return out


# ---------------------------------------------------------------- tests
def _sub(**kw):
    from datetime import timezone
    s = {"id": "s1", "status": "active", "plan_name": "Basic", "seat_price_cents": 1000,
         "seats": 5, "billable_seats": 5, "vat_id": None,
         "period_end": datetime(2026, 10, 20, tzinfo=__import__("datetime").timezone.utc)}
    s.update(kw)
    return s


def _at(day=14):
    from datetime import timezone
    return datetime(2026, 10, day, tzinfo=timezone.utc)


_NEW = {"name": "Pro", "seat_price_cents": 2000}


def test_a_basic():
    r = prorate_seats(_sub(), _NEW, _at())
    assert [x["kind"] for x in r] == ["credit", "charge"]
    assert (r[0]["amount_cents"], r[0]["vat_cents"], r[0]["approved_by"]) == (2308, 0, "Nguyễn Thị Phương Thảo")
    assert (r[1]["amount_cents"], r[1]["vat_cents"], r[1]["approved_by"]) == (4615, 969, None)
    assert r[0]["description"] == "Credit: unused Basic seats until 2026-10-20"
    assert r[0]["subscription_id"] == "s1"


def test_b_reverse_charge():
    assert prorate_seats(_sub(vat_id="ES123"), _NEW, _at())[1]["vat_cents"] == 0
    assert prorate_seats(_sub(vat_id="  "), _NEW, _at())[1]["vat_cents"] == 969


def test_c_approval():
    new = {"name": "Pro", "seat_price_cents": 20000}
    from datetime import timezone
    start = datetime(2026, 10, 7, tzinfo=timezone.utc)  # 13 days
    r = prorate_seats(_sub(seat_price_cents=10000), new, start)
    assert r[0]["amount_cents"] == 50000 and r[0]["approved_by"] == "Nguyễn Thị Phương Thảo"
    r = prorate_seats(_sub(seat_price_cents=10001), new, start)
    assert r[0]["amount_cents"] == 50005 and r[0]["approved_by"] == "Ramón Etxeberria-Goñi"


def test_d_skip_boundary():
    r = prorate_seats(_sub(seat_price_cents=640, billable_seats=1),
                      {"name": "Pro", "seat_price_cents": 649}, _at(19))
    assert [x["kind"] for x in r] == ["credit"] and r[0]["amount_cents"] == 50


def test_e_empty_cases():
    assert prorate_seats(_sub(status="trialing"), _NEW, _at()) == []
    assert prorate_seats(_sub(), {"name": "L", "seat_price_cents": 500}, _at()) == []
    assert prorate_seats(_sub(), {"name": "R", "seat_price_cents": 1000}, _at()) == []
    assert prorate_seats(_sub(), _NEW, _at(20)) == []
    assert prorate_seats(_sub(), _NEW, _at(21)) == []
    assert prorate_seats(_sub(billable_seats=0), _NEW, _at()) == []


def test_f_billable_seats():
    r = prorate_seats(_sub(seats=10, billable_seats=4), _NEW, _at())
    assert r[0]["amount_cents"] == -(-1000 * 4 * 6 // 13)


def test_g_long_name():
    r = prorate_seats(_sub(plan_name="X" * 200), {"name": "Y" * 200, "seat_price_cents": 2000}, _at())
    for line in r:
        assert len(line["description"]) <= 80
        assert line["description"].endswith("until 2026-10-20")
        assert "..." in line["description"]


def test_h_types_and_validation():
    import pytest
    for line in prorate_seats(_sub(), _NEW, _at()):
        assert type(line["amount_cents"]) is int and type(line["vat_cents"]) is int
    with pytest.raises(ValueError, match="vat_id"):
        s = _sub()
        del s["vat_id"]
        prorate_seats(s, _NEW, _at())
    with pytest.raises(ValueError):
        prorate_seats(_sub(), _NEW, datetime(2026, 10, 14))
    with pytest.raises(TypeError):
        prorate_seats(_sub(billable_seats=True), _NEW, _at())
    with pytest.raises(TypeError):
        prorate_seats(_sub(seat_price_cents=10.0), _NEW, _at())
    with pytest.raises(ValueError):
        prorate_seats(_sub(billable_seats=-1), _NEW, _at())