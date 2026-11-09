"""Seat upgrade proration for Fernhollow Studios.

Public entry point: prorate_seats(subscription, new_plan, changed_at).
All money is integer cents. No floats are used anywhere.

OPEN QUESTIONS FOR THE CLIENT (implemented as stated, to be confirmed):
1. Partial days are floored to whole days. Flooring reduces the credit owed to
   the customer and also reduces the charge. Confirm this is the intended rule.
2. Equal price (new == old) returns no lines. The brief does not cover this.
   It is a single branch in prorate_seats and easy to change.
3. Unknown status values are prorated as normal. Confirm, or should they be rejected?
4. If more than 30 days remain (changed_at before the period start), days are
   clamped to 30. Confirm.
5. The approval threshold assumes EUR cents: 50000 cents = EUR 500, and the
   threshold is strictly greater than that. Confirm currency and boundary.
6. Skipping credits under 50 cents forfeits money owed to the customer. This
   looks like rounding in our favour, which conflicts with the "never round in
   our favour" rule. Confirm that the skip applies to credits too.
7. VAT on charges is floored per line, not per invoice. Confirm.
8. Any non-blank vat_id is accepted as a reverse-charge ID. No format check. Confirm.
9. Description dates use period_end in its own timezone, with no conversion. Confirm.
10. Seat counts are read once at change time. Mid-period seat changes are not handled.
11. The worked check "old=1001, B=1, days=1, charge (new=1001) = 33" cannot occur,
    because equal price returns no lines. The tests use new=1002 for that check.
    Confirm the equal-price rule or the worked check.
"""

from datetime import datetime, timedelta

PERIOD_DAYS = 30
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
LARGE_CREDIT_CENTS = 50000
APPROVER_DEFAULT = "Win Tee Fung Tao"
APPROVER_LARGE = "Ramón Etxeberria-Goñi"
MAX_DESCRIPTION = 80
ELLIPSIS = "..."


def _check_aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _check_cents(value, name):
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an int number of cents")
    if value < 0:
        raise ValueError(f"{name} must not be negative")


def _check_name(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _validate(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise TypeError("subscription and new_plan must be dicts")
    _check_aware(changed_at, "changed_at")
    _check_aware(subscription["period_end"], "period_end")
    _check_cents(subscription["seat_price_cents"], "seat_price_cents")
    _check_cents(subscription["billable_seats"], "billable_seats")
    _check_cents(new_plan["seat_price_cents"], "new seat_price_cents")
    _check_name(subscription["plan_name"], "plan_name")
    _check_name(new_plan["name"], "new plan name")
    if not isinstance(subscription["status"], str):
        raise TypeError("status must be a string")
    vat_id = subscription.get("vat_id")
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be a string or None")


def _days_remaining(period_end, changed_at):
    days = (period_end - changed_at) // timedelta(days=1)
    return min(max(days, 0), PERIOD_DAYS)


def _credit_cents(old_price, billable, days):
    n = old_price * billable * days
    return -((-n) // PERIOD_DAYS)


def _charge_cents(new_price, billable, days):
    n = new_price * billable * days
    return n // PERIOD_DAYS


def _vat_cents(charge_amount, vat_id):
    if vat_id is not None and vat_id.strip():
        return 0
    return (charge_amount * VAT_PERCENT) // 100


def _approver_for_credit(amount_cents):
    if amount_cents > LARGE_CREDIT_CENTS:
        return APPROVER_LARGE
    return APPROVER_DEFAULT


def _description(kind, plan_name, period_end):
    date_text = period_end.strftime("%Y-%m-%d")
    verb = "Credit" if kind == "credit" else "Charge"
    prefix = f"{verb} unused "
    suffix = f" seats, period end {date_text}"
    fixed_len = len(prefix) + len(suffix)
    if fixed_len > MAX_DESCRIPTION:
        raise ValueError("description too long even without plan name")
    budget = MAX_DESCRIPTION - fixed_len
    name = plan_name
    if len(name) > budget:
        if budget < len(ELLIPSIS) + 1:
            raise ValueError("no room left for plan name")
        name = name[: budget - len(ELLIPSIS)] + ELLIPSIS
    return prefix + name + suffix


def _line(subscription_id, kind, amount_cents, vat_cents, description, approved_by):
    return {
        "subscription_id": subscription_id,
        "kind": kind,
        "amount_cents": amount_cents,
        "vat_cents": vat_cents,
        "description": description,
        "approved_by": approved_by,
    }


def prorate_seats(subscription, new_plan, changed_at):
    _validate(subscription, new_plan, changed_at)

    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]

    # Downgrades apply at renewal.
    if new_price < old_price:
        return []
    # Equal price is not specified. Flagged decision, single easy-to-change branch.
    if new_price == old_price:
        return []

    period_end = subscription["period_end"]
    days = _days_remaining(period_end, changed_at)
    if days == 0:
        return []

    billable = subscription["billable_seats"]
    credit_amt = _credit_cents(old_price, billable, days)
    charge_amt = _charge_cents(new_price, billable, days)

    subscription_id = subscription["id"]
    vat_id = subscription.get("vat_id")

    lines = []
    if credit_amt >= MIN_LINE_CENTS:
        lines.append(_line(
            subscription_id,
            "credit",
            credit_amt,
            0,
            _description("credit", subscription["plan_name"], period_end),
            _approver_for_credit(credit_amt),
        ))
    if charge_amt >= MIN_LINE_CENTS:
        lines.append(_line(
            subscription_id,
            "charge",
            charge_amt,
            _vat_cents(charge_amt, vat_id),
            _description("charge", new_plan["name"], period_end),
            None,
        ))
    return lines

# ---- test_seat_proration.py ----

"""Tests for seat_proration.prorate_seats.

Test list:
- trialing subscription returns no lines
- downgrade returns no lines
- equal price returns no lines
- worked example: old=1000, B=10, days=15 gives credit 5000
- rounding: credit rounds up (old=1001, B=1, days=1 gives 34)
- rounding: charge rounds down (new=1002 gives 33)
- VAT floor: charge 1000 gives 210, charge 999 gives 209
- reverse charge: vat_id present gives VAT 0
- whitespace vat_id counts as no VAT ID
- credit never carries VAT
- approval threshold: credit 50000 approved by default, 50001 by large approver
- 50-cent skip: credit 49 skipped, credit 50 kept
- charge under 50 pre-VAT is skipped
- order: credit before charge
- 30-day period independent of calendar month
- changed_at at period_end or after returns no lines
- days clamped to 30
- naive changed_at or period_end rejected
- description keeps period end date when truncated
- description untouched when short
- truncation counts code points
- empty plan name rejected
- date uses period_end's own timezone
"""

from datetime import datetime, timedelta, timezone

import pytest

from seat_proration import prorate_seats

UTC = timezone.utc
PERIOD_END = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def sub(**overrides):
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Studio",
        "seat_price_cents": 1000,
        "seats": 99,
        "billable_seats": 10,
        "vat_id": None,
        "period_end": PERIOD_END,
    }
    base.update(overrides)
    return base


def plan(price, name="Studio Plus"):
    return {"name": name, "seat_price_cents": price}


def days_before(days, period_end=PERIOD_END):
    return period_end - timedelta(days=days)


def test_trialing_returns_no_lines():
    assert prorate_seats(sub(status="trialing"), plan(2000), days_before(15)) == []


def test_downgrade_returns_no_lines():
    assert prorate_seats(sub(seat_price_cents=2000), plan(1000), days_before(15)) == []


def test_equal_price_returns_no_lines():
    assert prorate_seats(sub(seat_price_cents=1000), plan(1000), days_before(15)) == []


def test_worked_example_credit_exact():
    lines = prorate_seats(sub(seat_price_cents=1000, billable_seats=10), plan(2000), days_before(15))
    credit = lines[0]
    assert credit["kind"] == "credit"
    assert credit["amount_cents"] == 5000


def test_credit_rounds_up():
    lines = prorate_seats(sub(seat_price_cents=1001, billable_seats=1), plan(1002), days_before(1))
    assert lines[0]["amount_cents"] == 34


def test_charge_rounds_down():
    lines = prorate_seats(sub(seat_price_cents=1001, billable_seats=1), plan(1002), days_before(1))
    assert lines[1]["kind"] == "charge"
    assert lines[1]["amount_cents"] == 33


def test_vat_on_charge_floored():
    lines = prorate_seats(sub(seat_price_cents=500, billable_seats=1), plan(1000), days_before(30))
    assert lines[1]["amount_cents"] == 1000
    assert lines[1]["vat_cents"] == 210


def test_vat_floored_below_whole_euro():
    lines = prorate_seats(sub(seat_price_cents=500, billable_seats=1), plan(999), days_before(30))
    assert lines[1]["amount_cents"] == 999
    assert lines[1]["vat_cents"] == 209


def test_reverse_charge_with_vat_id():
    lines = prorate_seats(sub(seat_price_cents=500, billable_seats=1, vat_id="DE123"),
                          plan(1000), days_before(30))
    assert lines[1]["vat_cents"] == 0


def test_whitespace_vat_id_means_no_vat_id():
    lines = prorate_seats(sub(seat_price_cents=500, billable_seats=1, vat_id="   "),
                          plan(1000), days_before(30))
    assert lines[1]["vat_cents"] == 210


def test_credit_never_carries_vat():
    lines = prorate_seats(sub(seat_price_cents=1000, billable_seats=10), plan(2000), days_before(15))
    assert lines[0]["vat_cents"] == 0


def test_credit_exactly_50000_approved_by_default():
    lines = prorate_seats(sub(seat_price_cents=50000, billable_seats=1), plan(50100), days_before(30))
    assert lines[0]["amount_cents"] == 50000
    assert lines[0]["approved_by"] == "Win Tee Fung Tao"


def test_credit_50001_approved_by_large_approver():
    lines = prorate_seats(sub(seat_price_cents=50001, billable_seats=1), plan(60000), days_before(30))
    assert lines[0]["amount_cents"] == 50001
    assert lines[0]["approved_by"] == "Ramón Etxeberria-Goñi"


def test_charge_approved_by_is_none():
    lines = prorate_seats(sub(seat_price_cents=500, billable_seats=1), plan(1000), days_before(30))
    assert lines[1]["approved_by"] is None


def test_credit_49_skipped():
    lines = prorate_seats(sub(seat_price_cents=49, billable_seats=1), plan(100), days_before(30))
    assert [line["kind"] for line in lines] == ["charge"]


def test_credit_50_kept():
    lines = prorate_seats(sub(seat_price_cents=50, billable_seats=1), plan(100), days_before(30))
    assert lines[0]["kind"] == "credit"
    assert lines[0]["amount_cents"] == 50


def test_charge_under_50_pre_vat_skipped():
    lines = prorate_seats(sub(seat_price_cents=10, billable_seats=1), plan(49), days_before(30))
    assert [line["kind"] for line in lines] == ["credit"]


def test_both_lines_skipped_returns_empty():
    assert prorate_seats(sub(seat_price_cents=1, billable_seats=1), plan(2), days_before(30)) == []


def test_credit_comes_before_charge():
    lines = prorate_seats(sub(seat_price_cents=500, billable_seats=1), plan(1000), days_before(30))
    assert [line["kind"] for line in lines] == ["credit", "charge"]


def test_line_keys_and_subscription_id():
    lines = prorate_seats(sub(seat_price_cents=500, billable_seats=1), plan(1000), days_before(30))
    for line in lines:
        assert set(line) == {"subscription_id", "kind", "amount_cents", "vat_cents",
                             "description", "approved_by"}
        assert line["subscription_id"] == "sub_1"


def test_uses_billable_seats_not_seats():
    lines = prorate_seats(sub(seat_price_cents=1000, billable_seats=10, seats=500),
                          plan(2000), days_before(15))
    assert lines[0]["amount_cents"] == 5000


@pytest.mark.parametrize("period_end", [
    datetime(2027, 3, 1, 12, 0, tzinfo=UTC),
    datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
])
def test_thirty_day_period_regardless_of_month(period_end):
    lines = prorate_seats(sub(seat_price_cents=1000, billable_seats=10, period_end=period_end),
                          plan(2000), days_before(15, period_end))
    assert lines[0]["amount_cents"] == 5000


def test_changed_at_equal_to_period_end_returns_no_lines():
    assert prorate_seats(sub(), plan(2000), PERIOD_END) == []


def test_changed_at_after_period_end_returns_no_lines():
    assert prorate_seats(sub(), plan(2000), PERIOD_END + timedelta(days=3)) == []


def test_days_clamped_to_thirty():
    lines = prorate_seats(sub(seat_price_cents=1000, billable_seats=10), plan(2000),
                          days_before(45))
    assert lines[0]["amount_cents"] == 10000


def test_naive_changed_at_rejected():
    with pytest.raises(ValueError):
        prorate_seats(sub(), plan(2000), datetime(2026, 10, 15, 12, 0))


def test_naive_period_end_rejected():
    with pytest.raises(ValueError):
        prorate_seats(sub(period_end=datetime(2026, 11, 1, 12, 0)), plan(2000), days_before(15))


def test_long_plan_name_truncated_keeps_date():
    long_name = "A" * 60
    lines = prorate_seats(sub(plan_name=long_name, seat_price_cents=500, billable_seats=1),
                          plan(1000), days_before(30))
    description = lines[0]["description"]
    assert len(description) == 80
    assert description.endswith("period end 2026-11-01")
    assert "..." in description


def test_short_description_untouched():
    lines = prorate_seats(sub(plan_name="Basic", seat_price_cents=500, billable_seats=1),
                          plan(1000), days_before(30))
    assert lines[0]["description"] == "Credit unused Basic seats, period end 2026-11-01"
    assert lines[1]["description"] == "Charge unused Studio Plus seats, period end 2026-11-01"


def test_truncation_counts_code_points():
    name = "Ñ" * 40
    lines = prorate_seats(sub(plan_name=name, seat_price_cents=500, billable_seats=1),
                          plan(1000), days_before(30))
    description = lines[0]["description"]
    assert len(description) == 80
    assert description.startswith("Credit unused " + "Ñ" * 34 + "...")
    assert description.endswith("period end 2026-11-01")


def test_empty_plan_name_rejected():
    with pytest.raises(ValueError):
        prorate_seats(sub(plan_name=""), plan(2000), days_before(15))


def test_date_uses_period_end_own_timezone():
    tz = timezone(timedelta(hours=5))
    period_end = datetime(2026, 11, 1, 0, 30, tzinfo=tz)
    lines = prorate_seats(sub(seat_price_cents=500, billable_seats=1, period_end=period_end),
                          plan(1000), period_end - timedelta(days=30))
    assert lines[0]["description"].endswith("period end 2026-11-01")