"""Seat upgrade proration for Fernhollow Studios.

Open-question defaults (the client has not answered; each is set in one place below):
1. Currency is EUR. APPROVAL_THRESHOLD_CENTS (50000) is compared directly, with no conversion.
2. Equal old and new seat prices are not a downgrade. They are prorated normally, so the net may be 1 cent.
3. Days are whole days, the floor of elapsed time. changed_at == period_end gives 0 days, so the result is [].
4. period_end is rendered as its own date, in its own offset, not converted to UTC.
5. VAT is floored, like charges. The 50-cent minimum applies to the net amount before VAT.
6. An empty or whitespace-only vat_id is treated as absent, so VAT applies.
7. changed_at after period_end, and naive datetimes, raise ValueError.
8. A description still too long after shortening the plan name raises ValueError.
9. The status match is exact "trialing" only.
10. A credit below 50 cents is dropped.
11. Description is "Seats {plan} until {YYYY-MM-DD}" for both kinds. The plan is shortened with an ellipsis. Length is counted in code points.
Other choices: datetimes are validated before the gates. Descriptions are built only for emitted lines. Days are not capped at 30.
"""

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

CURRENCY = "EUR"  # open question 1
APPROVAL_THRESHOLD_CENTS = 50000
MIN_LINE_CENTS = 50
MAX_DESCRIPTION_LEN = 80
PERIOD_DAYS = 30
VAT_RATE = Decimal("0.21")
FINANCE_APPROVER = "Nguyễn Thị Phương Thảo"
BIG_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
ELLIPSIS = "…"


def _aware(name, value):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value


def _int_field(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _has_vat_id(subscription):
    vat_id = subscription.get("vat_id")
    return vat_id is not None and str(vat_id).strip() != ""


def _vat(amount_cents):
    return int((Decimal(amount_cents) * VAT_RATE).to_integral_value(rounding=ROUND_FLOOR))


def _description(plan_name, period_end):
    prefix = "Seats "
    suffix = f" until {period_end.date().isoformat()}"
    room = MAX_DESCRIPTION_LEN - len(prefix) - len(suffix)
    plan = plan_name
    if len(plan) > room:
        if room < 1:
            raise ValueError("description cannot fit within 80 characters")
        plan = plan[: room - 1] + ELLIPSIS
    return f"{prefix}{plan}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    period_end = _aware("period_end", subscription["period_end"])
    _aware("changed_at", changed_at)
    if changed_at > period_end:
        raise ValueError("changed_at is after period_end")

    old_price = _int_field("seat_price_cents", subscription["seat_price_cents"])
    new_price = _int_field("new_plan seat_price_cents", new_plan["seat_price_cents"])
    seats = _int_field("billable_seats", subscription["billable_seats"])

    if subscription["status"] == "trialing":
        return []
    if new_price < old_price:
        return []

    days_left = (period_end - changed_at) // timedelta(days=1)
    period = Decimal(PERIOD_DAYS)
    seat_days = Decimal(seats) * Decimal(days_left)

    credit_cents = int(((Decimal(old_price) * seat_days) / period).to_integral_value(rounding=ROUND_CEILING))
    charge_cents = int(((Decimal(new_price) * seat_days) / period).to_integral_value(rounding=ROUND_FLOOR))

    lines = []
    if credit_cents >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _description(subscription["plan_name"], period_end),
            "approved_by": BIG_CREDIT_APPROVER if credit_cents > APPROVAL_THRESHOLD_CENTS else FINANCE_APPROVER,
        })
    if charge_cents >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": 0 if _has_vat_id(subscription) else _vat(charge_cents),
            "description": _description(new_plan["name"], period_end),
            "approved_by": None,
        })
    return lines


# ===== test_prorate_seats.py (separate file; not executed in this session) =====

import unittest
from datetime import datetime, timedelta, timezone

from prorate_seats import prorate_seats, FINANCE_APPROVER, BIG_CREDIT_APPROVER

UTC = timezone.utc
PE = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def sub(**overrides):
    base = {
        "id": "sub_1", "status": "active", "plan_name": "Studio",
        "seat_price_cents": 1000, "seats": 5, "billable_seats": 3,
        "vat_id": None, "period_end": PE,
    }
    base.update(overrides)
    return base


def plan(price, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def days_before_end(n):
    return PE - timedelta(days=n)


class ProrateSeatsTests(unittest.TestCase):

    def test_credit_comes_before_charge(self):
        lines = prorate_seats(sub(), plan(2000), days_before_end(30))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])

    def test_downgrade_returns_empty(self):
        self.assertEqual(prorate_seats(sub(), plan(500), days_before_end(10)), [])

    def test_trialing_returns_empty(self):
        self.assertEqual(prorate_seats(sub(status="trialing"), plan(2000), days_before_end(10)), [])

    def test_billable_seats_used_not_seats(self):
        lines = prorate_seats(sub(seats=100, billable_seats=1), plan(2000), days_before_end(30))
        self.assertEqual(lines[0]["amount_cents"], 1000)
        self.assertEqual(lines[1]["amount_cents"], 2000)

    def test_credit_rounds_up_and_charge_rounds_down(self):
        # 1001 * 10 / 30 = 333.67: credit ceil 334, charge floor 333
        lines = prorate_seats(sub(seats=1, billable_seats=1, seat_price_cents=1001),
                              plan(1001), days_before_end(10))
        self.assertEqual(lines[0]["amount_cents"], 334)
        self.assertEqual(lines[1]["amount_cents"], 333)

    def test_lines_under_50_cents_dropped(self):
        lines = prorate_seats(sub(seats=1, billable_seats=1, seat_price_cents=49),
                              plan(50), days_before_end(30))
        self.assertEqual([l["kind"] for l in lines], ["charge"])

    def test_exactly_50_cents_kept(self):
        lines = prorate_seats(sub(seats=1, billable_seats=1, seat_price_cents=50),
                              plan(50), days_before_end(30))
        self.assertEqual([l["amount_cents"] for l in lines], [50, 50])

    def test_vat_21_percent_on_charge(self):
        lines = prorate_seats(sub(seats=1, billable_seats=1, seat_price_cents=1000),
                              plan(1001), days_before_end(30))
        self.assertEqual(lines[1]["vat_cents"], 210)  # floor(1001 * 0.21) = 210
        self.assertEqual(lines[0]["vat_cents"], 0)

    def test_reverse_charge_when_vat_id_set(self):
        lines = prorate_seats(sub(seats=1, billable_seats=1, vat_id="DE123456789"),
                              plan(2000), days_before_end(30))
        self.assertEqual(lines[1]["vat_cents"], 0)

    def test_whitespace_vat_id_treated_as_absent(self):
        lines = prorate_seats(sub(seats=1, billable_seats=1, vat_id="   "),
                              plan(2000), days_before_end(30))
        self.assertEqual(lines[1]["vat_cents"], 420)

    def test_credit_exactly_threshold_goes_to_finance(self):
        lines = prorate_seats(sub(seats=1, billable_seats=1, seat_price_cents=50000),
                              plan(50000), days_before_end(30))
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], FINANCE_APPROVER)
        self.assertEqual(FINANCE_APPROVER, "Nguyễn Thị Phương Thảo")

    def test_credit_above_threshold_goes_to_ramon(self):
        lines = prorate_seats(sub(seats=1, billable_seats=1, seat_price_cents=50001),
                              plan(50001), days_before_end(30))
        self.assertEqual(lines[0]["amount_cents"], 50001)
        self.assertEqual(lines[0]["approved_by"], BIG_CREDIT_APPROVER)
        self.assertEqual(BIG_CREDIT_APPROVER, "Ramón Etxeberria-Goñi")

    def test_charge_has_no_approver(self):
        lines = prorate_seats(sub(), plan(2000), days_before_end(30))
        self.assertIsNone(lines[1]["approved_by"])

    def test_description_length_and_date_preserved(self):
        long_name = "X" * 200
        lines = prorate_seats(sub(plan_name=long_name), plan(2000, name="Y" * 200), days_before_end(30))
        for line in lines:
            self.assertLessEqual(len(line["description"]), 80)
            self.assertTrue(line["description"].endswith("until 2026-11-01"))
            self.assertIn(ELLIPSIS_CHAR, line["description"])

    def test_date_uses_own_offset_not_converted(self):
        pe = datetime(2026, 11, 1, 1, 0, tzinfo=timezone(timedelta(hours=5)))
        lines = prorate_seats(sub(period_end=pe), plan(2000), pe - timedelta(days=30))
        self.assertTrue(lines[0]["description"].endswith("until 2026-11-01"))

    def test_zero_days_returns_empty(self):
        self.assertEqual(prorate_seats(sub(), plan(2000), PE), [])

    def test_changed_after_period_end_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(sub(), plan(2000), PE + timedelta(days=1))

    def test_naive_datetime_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(sub(), plan(2000), datetime(2026, 10, 20, 12, 0))


ELLIPSIS_CHAR = "…"

if __name__ == "__main__":
    unittest.main()