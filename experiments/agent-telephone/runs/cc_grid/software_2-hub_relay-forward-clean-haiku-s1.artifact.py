"""Seat-upgrade proration for Fernhollow Studios billing.

Open questions and the defaults chosen:
Q1: changed_at after period_end returns [] and does not raise.
Q2: the 50-cent minimum is applied to each line independently.
Q3: an equal seat price is treated as no change and returns [].
Q4 (assumed): the 500 EUR approval threshold is 50000 cents, treating the currency as EUR.
Q5 (assumed): billable_seats must be a non-negative int and is the only seat count read. seats is ignored.
Credits carry VAT 0 per the PM spec. This overrides the generic house rule that VAT applies to credits too.
The PM's acceptance examples E1-E11 were not included in the material received. The tests below are derived from the stated rules and must be reconciled against E1-E11 before sign-off.
"""

import math
import unittest
from datetime import datetime, timedelta, timezone
from fractions import Fraction

PERIOD_US = 30 * 24 * 3600 * 10**6
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
APPROVER_STANDARD = "Nguyễn Thị Phương Thảo"
APPROVER_LARGE = "Ramón Etxeberria-Goñi"
LARGE_CREDIT_CENTS = 50000
MAX_DESC = 80
CREDIT_TEMPLATE = "Credit unused {plan} seats, period ends {date}"
CHARGE_TEMPLATE = "Charge new {plan} seats, period ends {date}"


def _check_int(value, name):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer number of cents")
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _check_aware(dt, name):
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return dt


def _describe(template, plan, date_str):
    if not isinstance(plan, str):
        raise ValueError("plan name must be a string")
    budget = MAX_DESC - len(template.format(plan="", date=date_str))
    if len(plan) > budget:
        if budget < 4:
            raise ValueError("description budget too small for plan name")
        plan = plan[: budget - 3].rstrip() + "..."
    return template.format(plan=plan, date=date_str)


def prorate_seats(subscription, new_plan, changed_at):
    _check_aware(changed_at, "changed_at")
    period_end = _check_aware(subscription["period_end"], "period_end")
    old_price = _check_int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _check_int(new_plan["seat_price_cents"], "new seat_price_cents")
    seats = _check_int(subscription["billable_seats"], "billable_seats")

    if subscription["status"] == "trialing":
        return []
    if new_price <= old_price:
        return []

    remaining_us = (period_end - changed_at) // timedelta(microseconds=1)
    if remaining_us < 0:
        return []
    fraction = min(Fraction(remaining_us, PERIOD_US), Fraction(1))

    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    vat_id = subscription.get("vat_id")
    reverse_charge = isinstance(vat_id, str) and vat_id.strip() != ""

    lines = []

    credit = math.ceil(old_price * seats * fraction)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe(CREDIT_TEMPLATE, subscription["plan_name"], date_str),
            "approved_by": APPROVER_LARGE if credit > LARGE_CREDIT_CENTS else APPROVER_STANDARD,
        })

    charge = math.floor(new_price * seats * fraction)
    if charge >= MIN_LINE_CENTS:
        vat = 0 if reverse_charge else charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe(CHARGE_TEMPLATE, new_plan["name"], date_str),
            "approved_by": None,
        })

    return lines


UTC = timezone.utc
PERIOD_END = datetime(2026, 11, 12, 0, 0, tzinfo=UTC)


def _sub(**overrides):
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Studio",
        "seat_price_cents": 1000,
        "seats": 99,
        "billable_seats": 1,
        "vat_id": None,
        "period_end": PERIOD_END,
    }
    base.update(overrides)
    return base


def _plan(price, name="Studio Plus"):
    return {"name": name, "seat_price_cents": price}


def _left(days):
    return PERIOD_END - timedelta(days=days)


class ProrateSeatsTests(unittest.TestCase):

    def test_half_period_credit_then_charge_with_vat(self):
        lines = prorate_seats(_sub(seat_price_cents=1000, billable_seats=10), _plan(1500), _left(15))
        self.assertEqual(lines, [
            {"subscription_id": "sub_1", "kind": "credit", "amount_cents": 5000, "vat_cents": 0,
             "description": "Credit unused Studio seats, period ends 2026-11-12",
             "approved_by": APPROVER_STANDARD},
            {"subscription_id": "sub_1", "kind": "charge", "amount_cents": 7500, "vat_cents": 1575,
             "description": "Charge new Studio Plus seats, period ends 2026-11-12",
             "approved_by": None},
        ])

    def test_billable_seats_used_not_seats(self):
        lines = prorate_seats(_sub(seat_price_cents=1000, seats=99, billable_seats=1), _plan(1500), _left(15))
        self.assertEqual(lines[0]["amount_cents"], 500)
        self.assertEqual(lines[1]["amount_cents"], 750)

    def test_credit_rounds_up_charge_rounds_down(self):
        # credit 1000/3 -> 334, charge 1001/3 -> 333
        lines = prorate_seats(_sub(seat_price_cents=1000), _plan(1001), _left(10))
        self.assertEqual(lines[0]["amount_cents"], 334)
        self.assertEqual(lines[1]["amount_cents"], 333)
        self.assertEqual(lines[1]["vat_cents"], 69)

    def test_half_cent_credit_rounds_to_fifty_and_is_kept(self):
        # credit 99/2 = 49.5 -> 50; charge 100/2 = 50 exact
        lines = prorate_seats(_sub(seat_price_cents=99), _plan(100), _left(15))
        self.assertEqual([l["amount_cents"] for l in lines], [50, 50])
        self.assertEqual([l["vat_cents"] for l in lines], [0, 10])

    def test_line_under_fifty_skipped_independently(self):
        # credit 60/2 = 30 skipped; charge 200/2 = 100 kept
        lines = prorate_seats(_sub(seat_price_cents=60), _plan(200), _left(15))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 100)
        self.assertEqual(lines[0]["vat_cents"], 21)

    def test_both_lines_under_fifty_gives_empty(self):
        self.assertEqual(prorate_seats(_sub(seat_price_cents=10), _plan(20), _left(15)), [])

    def test_trialing_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(2000), _left(15)), [])

    def test_downgrade_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(seat_price_cents=2000), _plan(1000), _left(15)), [])

    def test_equal_price_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(seat_price_cents=1000), _plan(1000), _left(15)), [])

    def test_changed_after_period_end_returns_empty(self):
        after = PERIOD_END + timedelta(days=1)
        self.assertEqual(prorate_seats(_sub(), _plan(2000), after), [])

    def test_fraction_clamped_to_one(self):
        # changed 60 days before period end -> fraction clamps to 1
        lines = prorate_seats(_sub(seat_price_cents=1000), _plan(2000), _left(60))
        self.assertEqual(lines[0]["amount_cents"], 1000)
        self.assertEqual(lines[1]["amount_cents"], 2000)
        self.assertEqual(lines[1]["vat_cents"], 420)

    def test_reverse_charge_with_vat_id(self):
        lines = prorate_seats(_sub(vat_id=" DE123456789 "), _plan(2000), _left(15))
        self.assertEqual(lines[1]["vat_cents"], 0)

    def test_blank_vat_id_still_charges_vat(self):
        lines = prorate_seats(_sub(vat_id="   "), _plan(2000), _left(15))
        self.assertEqual(lines[1]["vat_cents"], 1000 * 21 // 100)

    def test_approval_threshold_at_50000_is_standard(self):
        lines = prorate_seats(_sub(seat_price_cents=50000), _plan(50001), _left(30))
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], APPROVER_STANDARD)

    def test_approval_above_50000_is_large(self):
        lines = prorate_seats(_sub(seat_price_cents=50001), _plan(50002), _left(30))
        self.assertEqual(lines[0]["amount_cents"], 50001)
        self.assertEqual(lines[0]["approved_by"], APPROVER_LARGE)

    def test_credit_description_truncated_keeps_date(self):
        lines = prorate_seats(_sub(plan_name="P" * 60), _plan(2000), _left(15))
        desc = lines[0]["description"]
        self.assertEqual(desc, "Credit unused " + "P" * 33 + "... seats, period ends 2026-11-12")
        self.assertLessEqual(len(desc), 80)
        self.assertTrue(desc.endswith("period ends 2026-11-12"))

    def test_charge_description_truncated_keeps_date(self):
        lines = prorate_seats(_sub(), _plan(2000, name="Q" * 60), _left(15))
        desc = lines[1]["description"]
        self.assertEqual(desc, "Charge new " + "Q" * 36 + "... seats, period ends 2026-11-12")
        self.assertEqual(len(desc), 80)

    def test_date_uses_period_end_own_timezone(self):
        tz = timezone(timedelta(hours=-5))
        pe = datetime(2026, 11, 12, 23, 30, tzinfo=tz)
        lines = prorate_seats(_sub(period_end=pe), _plan(2000), pe - timedelta(days=15))
        self.assertIn("period ends 2026-11-12", lines[0]["description"])

    def test_naive_datetime_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(2000), datetime(2026, 10, 28))

    def test_naive_period_end_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(period_end=datetime(2026, 11, 12)), _plan(2000), _left(15))

    def test_float_price_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(seat_price_cents=1000.0), _plan(2000), _left(15))

    def test_bool_seats_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(billable_seats=True), _plan(2000), _left(15))

    def test_negative_seats_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(billable_seats=-1), _plan(2000), _left(15))

    def test_negative_price_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(-5), _left(15))

    def test_output_keys_exact(self):
        lines = prorate_seats(_sub(), _plan(2000), _left(15))
        for line in lines:
            self.assertEqual(set(line), {"subscription_id", "kind", "amount_cents",
                                         "vat_cents", "description", "approved_by"})


if __name__ == "__main__":
    unittest.main()