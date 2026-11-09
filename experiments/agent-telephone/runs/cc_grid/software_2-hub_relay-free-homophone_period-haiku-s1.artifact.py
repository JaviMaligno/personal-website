# /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-xe9h8hdl/seat_proration.py
"""Seat-change proration for Fernhollow Studios.

Interpretations not yet confirmed by the client:
- Equal seat prices are not a downgrade and are prorated normally.
- unused_days is the floor of whole elapsed days from changed_at to period_end.
- changed_at more than one 13-day period before period_end raises ValueError (provisional).
- Trialing, downgrade, and changed_at >= period_end return [] before the 13-day check runs.
- DESCRIPTION_TEMPLATE is provisional. Truncation keeps the start of the plan name and appends an ellipsis.
- VAT is floor(charge * 21 / 100) on the rounded-down charge. Whitespace-only vat_id counts as empty.
- The approval threshold assumes EUR cents.
"""

from datetime import datetime, timedelta

PERIOD_DAYS = 13
MIN_AMOUNT_CENTS = 50
VAT_PERCENT = 21
LARGE_CREDIT_CENTS = 50000
DEFAULT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
DESCRIPTION_TEMPLATE = "Seat change: {plan} until {date}"
MAX_DESCRIPTION_LEN = 80
ELLIPSIS = "…"


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _vat_cents(amount_cents: int, vat_id) -> int:
    if vat_id is not None and str(vat_id).strip():
        return 0
    return amount_cents * VAT_PERCENT // 100


def _description(plan: str, period_end: datetime) -> str:
    date = period_end.date().isoformat()
    skeleton = DESCRIPTION_TEMPLATE.format(plan="", date=date)
    avail = MAX_DESCRIPTION_LEN - len(skeleton)
    if avail < 0:
        raise ValueError("description template cannot fit within 80 characters")
    if len(plan) > avail:
        if avail < 2:
            raise ValueError("description cannot fit within 80 characters")
        plan = plan[: avail - 1] + ELLIPSIS
    return DESCRIPTION_TEMPLATE.format(plan=plan, date=date)


def prorate_seats(subscription: dict, new_plan: dict, changed_at: datetime) -> list[dict]:
    period_end = subscription["period_end"]
    if not (_is_aware(changed_at) and _is_aware(period_end)):
        raise ValueError("datetimes must be timezone-aware")

    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    if changed_at >= period_end:
        return []

    unused_days = (period_end - changed_at) // timedelta(days=1)
    if unused_days > PERIOD_DAYS:
        raise ValueError("changed_at is more than one billing period before period_end")

    seats = subscription["billable_seats"]
    credit = -((-(old_price * seats * unused_days)) // PERIOD_DAYS)
    charge = new_price * seats * unused_days // PERIOD_DAYS

    sub_id = subscription["id"]
    lines = []

    if credit >= MIN_AMOUNT_CENTS:
        approver = LARGE_CREDIT_APPROVER if credit > LARGE_CREDIT_CENTS else DEFAULT_APPROVER
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(subscription["plan_name"], period_end),
            "approved_by": approver,
        })

    if charge >= MIN_AMOUNT_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": _vat_cents(charge, subscription.get("vat_id")),
            "description": _description(new_plan["name"], period_end),
            "approved_by": None,
        })

    return lines


# ---- test_seat_proration.py ----
# Not executed in this session: no execution tool was available, so these tests have not been run.

import datetime as dt
from zoneinfo import ZoneInfo

import pytest

import seat_proration as sp

UTC = dt.timezone.utc
PERIOD_END = dt.datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
THAO = "Nguyễn Thị Phương Thảo"
RAMON = "Ramón Etxeberria-Goñi"


def sub(old=1000, billable=10, status="active", vat_id=None, period_end=PERIOD_END):
    return {
        "id": "sub_1",
        "status": status,
        "plan_name": "Studio",
        "seat_price_cents": old,
        "seats": 999,
        "billable_seats": billable,
        "vat_id": vat_id,
        "period_end": period_end,
        "legacy_discount": 90,
    }


def plan(new, name="Studio Pro"):
    return {"name": name, "seat_price_cents": new}


def at(unused, hours=0):
    return PERIOD_END - dt.timedelta(days=unused, hours=hours)


def by_kind(lines):
    return {line["kind"]: line for line in lines}


def test_example_1_full_period():
    lines = sp.prorate_seats(sub(1000, 10), plan(1300), at(13))
    assert [l["kind"] for l in lines] == ["credit", "charge"]
    credit, charge = lines
    assert credit["amount_cents"] == 10000 and credit["vat_cents"] == 0
    assert credit["approved_by"] == THAO
    assert charge["amount_cents"] == 13000 and charge["vat_cents"] == 2730
    assert charge["approved_by"] is None


def test_example_2_partial_period():
    lines = by_kind(sp.prorate_seats(sub(1000, 10), plan(1300), at(6)))
    assert lines["credit"]["amount_cents"] == 4616
    assert lines["charge"]["amount_cents"] == 6000
    assert lines["charge"]["vat_cents"] == 1260


def test_example_3_upgrade_smaller_delta():
    lines = by_kind(sp.prorate_seats(sub(1000, 10), plan(1100), at(6)))
    assert lines["credit"]["amount_cents"] == 4616
    assert lines["charge"]["amount_cents"] == 5076
    assert lines["charge"]["vat_cents"] == 1065


def test_example_4_downgrade_returns_empty():
    assert sp.prorate_seats(sub(1300, 10), plan(1000), at(6)) == []


def test_example_5_trialing_returns_empty():
    assert sp.prorate_seats(sub(1000, 10, status="trialing"), plan(1300), at(6)) == []


def test_example_6_vat_id_reverse_charge():
    lines = by_kind(sp.prorate_seats(sub(1000, 10, vat_id="DE123"), plan(1300), at(6)))
    assert lines["credit"]["amount_cents"] == 4616 and lines["credit"]["vat_cents"] == 0
    assert lines["charge"]["amount_cents"] == 6000 and lines["charge"]["vat_cents"] == 0


def test_example_7_both_lines_below_minimum_dropped():
    assert sp.prorate_seats(sub(100, 1), plan(150), at(1)) == []


def test_example_8_equal_prices_prorated_and_kept():
    lines = by_kind(sp.prorate_seats(sub(650, 1), plan(650), at(1)))
    assert lines["credit"]["amount_cents"] == 50
    assert lines["charge"]["amount_cents"] == 50
    assert lines["charge"]["vat_cents"] == 10


def test_example_9_credit_exactly_50000_is_thao():
    lines = by_kind(sp.prorate_seats(sub(5000, 10), plan(6000), at(13)))
    assert lines["credit"]["amount_cents"] == 50000
    assert lines["credit"]["approved_by"] == THAO
    assert lines["charge"]["amount_cents"] == 60000
    assert lines["charge"]["vat_cents"] == 12600


def test_example_10_credit_over_50000_is_ramon():
    lines = by_kind(sp.prorate_seats(sub(5000, 11), plan(6000), at(13)))
    assert lines["credit"]["amount_cents"] == 55000
    assert lines["credit"]["approved_by"] == RAMON
    assert lines["charge"]["amount_cents"] == 66000
    assert lines["charge"]["vat_cents"] == 13860


def test_downgrade_is_strictly_less_only():
    assert sp.prorate_seats(sub(1000, 1), plan(999), at(1)) == []


def test_minimum_applied_per_line():
    lines = sp.prorate_seats(sub(100, 1), plan(1000), at(1))
    assert len(lines) == 1
    assert lines[0]["kind"] == "charge"
    assert lines[0]["amount_cents"] == 76
    assert lines[0]["vat_cents"] == 15


def test_sub_day_remainder_returns_empty():
    assert sp.prorate_seats(sub(1000, 10), plan(1300), at(0, hours=5)) == []


def test_partial_day_is_floored():
    lines = by_kind(sp.prorate_seats(sub(1000, 10), plan(1300), at(6, hours=5)))
    assert lines["credit"]["amount_cents"] == 4616


def test_changed_at_on_or_after_period_end_returns_empty():
    assert sp.prorate_seats(sub(), plan(1300), PERIOD_END) == []
    assert sp.prorate_seats(sub(), plan(1300), PERIOD_END + dt.timedelta(days=1)) == []


def test_more_than_one_period_raises():
    with pytest.raises(ValueError):
        sp.prorate_seats(sub(), plan(1300), at(14))


def test_naive_changed_at_raises():
    with pytest.raises(ValueError):
        sp.prorate_seats(sub(), plan(1300), dt.datetime(2026, 10, 10, 12, 0))


def test_naive_period_end_raises():
    naive_end = dt.datetime(2026, 10, 20, 12, 0)
    with pytest.raises(ValueError):
        sp.prorate_seats(sub(period_end=naive_end), plan(1300), dt.datetime(2026, 10, 10, tzinfo=UTC))


def test_date_uses_period_end_timezone():
    berlin_end = dt.datetime(2026, 10, 14, 0, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    changed = berlin_end - dt.timedelta(days=6)
    lines = sp.prorate_seats(sub(period_end=berlin_end), plan(1300), changed)
    for line in lines:
        assert line["description"].endswith("until 2026-10-14")


def test_description_names_plans():
    lines = by_kind(sp.prorate_seats(sub(1000, 10), plan(1300), at(6)))
    assert lines["credit"]["description"] == "Seat change: Studio until 2026-10-20"
    assert lines["charge"]["description"] == "Seat change: Studio Pro until 2026-10-20"


def test_long_plan_name_is_truncated_and_keeps_date():
    lines = sp.prorate_seats(sub(1000, 10), plan(1300, name="A" * 120), at(6))
    desc = by_kind(lines)["charge"]["description"]
    assert len(desc) == 80
    assert desc.endswith(" until 2026-10-20")
    assert sp.ELLIPSIS in desc


def test_description_cannot_fit_raises(monkeypatch):
    monkeypatch.setattr(sp, "DESCRIPTION_TEMPLATE", "Seat change: {plan} until {date}" + "x" * 60)
    with pytest.raises(ValueError):
        sp.prorate_seats(sub(1000, 10), plan(1300), at(6))


def test_vat_function_rounds_down():
    assert sp._vat_cents(50, None) == 10
    assert sp._vat_cents(13000, "") == 2730
    assert sp._vat_cents(13000, "NL1") == 0