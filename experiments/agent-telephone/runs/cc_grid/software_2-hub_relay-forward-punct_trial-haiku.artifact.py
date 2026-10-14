"""Seat upgrade proration for Fernhollow Studios.

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list of invoice line dicts.

Open-question defaults used:
- Currency is EUR; all amounts are integer cents.
- Equal price still prorates (credit and charge are both emitted).
- Known statuses are active, past_due and trialing; any other status raises ValueError.
- changed_at earlier than period_end minus 30 days raises ValueError.
- Naive datetimes raise ValueError.
- Float (or bool) prices and seat counts raise TypeError.
- legacy_discount is ignored.

Test status: the unittest suite at the bottom was written but NOT executed in this environment. Run with: python3 -I <this file>.
The pm's numbered acceptance cases 1-15 were not available to the author, so the tests cover each rule in the spec rather than being mapped one-to-one to those case numbers.
"""

import math
import unittest
from datetime import datetime, timedelta, timezone
from fractions import Fraction

PERIOD_DAYS = 30
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
LARGE_CREDIT_CENTS = 50000
FINANCE_APPROVER = "Nguyễn Thị Phương Thảo"
CONTROLLER_APPROVER = "Ramón Etxeberria-Goñi"
KNOWN_STATUSES = frozenset({"active", "past_due", "trialing"})
MAX_DESCRIPTION = 80
_MICROS_PER_DAY = 86400 * 10**6
CREDIT_TEMPLATE = "Credit for unused {plan} seats, period end {date}"
CHARGE_TEMPLATE = "Charge for prorated {plan} seats, period end {date}"


def _check_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer number of cents or seats")
    return value


def _check_aware(name, value):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _has_vat_id(value):
    if value is None:
        return False
    if not isinstance(value, str):
        raise TypeError("vat_id must be a string or None")
    return value.strip() != ""


def _describe(template, plan_name, period_end):
    date = period_end.strftime("%Y-%m-%d")
    room = MAX_DESCRIPTION - len(template.format(plan="", date=date))
    plan = str(plan_name)
    if len(plan) > room:
        plan = plan[:room - 3] + "..." if room >= 4 else plan[:max(room, 0)]
    return template.format(plan=plan, date=date)


def prorate_seats(subscription, new_plan, changed_at):
    status = subscription["status"]
    if status not in KNOWN_STATUSES:
        raise ValueError(f"unknown subscription status: {status!r}")

    old_price = _check_int("seat_price_cents", subscription["seat_price_cents"])
    billable = _check_int("billable_seats", subscription["billable_seats"])
    new_price = _check_int("new_plan seat_price_cents", new_plan["seat_price_cents"])
    period_end = _check_aware("period_end", subscription["period_end"])
    changed_at = _check_aware("changed_at", changed_at)
    vat_present = _has_vat_id(subscription.get("vat_id"))

    if changed_at < period_end - timedelta(days=PERIOD_DAYS):
        raise ValueError("changed_at is more than 30 days before period_end")

    if status == "trialing":
        return []
    if new_price < old_price:
        return []

    td = period_end - changed_at
    micros = (td.days * 86400 + td.seconds) * 10**6 + td.microseconds
    if micros <= 0:
        return []
    days = Fraction(micros, _MICROS_PER_DAY)

    lines = []

    credit = math.ceil(Fraction(old_price * billable) * days / PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe(CREDIT_TEMPLATE, subscription["plan_name"], period_end),
            "approved_by": CONTROLLER_APPROVER if credit > LARGE_CREDIT_CENTS else FINANCE_APPROVER,
        })

    charge = math.floor(Fraction(new_price * billable) * days / PERIOD_DAYS)
    if charge >= MIN_LINE_CENTS:
        vat = 0 if vat_present else charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe(CHARGE_TEMPLATE, new_plan["name"], period_end),
            "approved_by": None,
        })

    return lines


PE = datetime(2026, 11, 30, 0, 0, tzinfo=timezone.utc)


def _sub(**overrides):
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Starter",
        "seat_price_cents": 1000,
        "seats": 99,
        "billable_seats": 10,
        "vat_id": None,
        "period_end": PE,
    }
    base.update(overrides)
    return base


def _plan(price, name="Business"):
    return {"name": name, "seat_price_cents": price}


class ProrateSeatsTests(unittest.TestCase):

    def test_basic_upgrade_credit_ceil_charge_floor_vat(self):
        lines = prorate_seats(_sub(), _plan(1500), PE - timedelta(days=10))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        self.assertEqual(lines[0]["amount_cents"], 3334)  # 10000*10/30 = 3333.33 -> up
        self.assertEqual(lines[1]["amount_cents"], 5000)  # 15000*10/30 exact
        self.assertEqual(lines[1]["vat_cents"], 1050)
        self.assertEqual(lines[0]["vat_cents"], 0)

    def test_credit_rounds_up_and_charge_rounds_down(self):
        lines = prorate_seats(_sub(seat_price_cents=1000, billable_seats=1),
                              _plan(1001), PE - timedelta(days=10))
        self.assertEqual(lines[0]["amount_cents"], 334)  # 333.33 -> 334
        self.assertEqual(lines[1]["amount_cents"], 333)  # 333.67 -> 333
        self.assertEqual(lines[1]["vat_cents"], 69)

    def test_fractional_days_from_elapsed_time(self):
        lines = prorate_seats(_sub(seat_price_cents=3000, billable_seats=1),
                              _plan(6000), PE - timedelta(hours=12))
        self.assertEqual(lines[0]["amount_cents"], 50)
        self.assertEqual(lines[1]["amount_cents"], 100)
        self.assertEqual(lines[1]["vat_cents"], 21)

    def test_downgrade_returns_nothing(self):
        self.assertEqual(prorate_seats(_sub(seat_price_cents=2000), _plan(1000),
                                       PE - timedelta(days=10)), [])

    def test_equal_price_still_prorates(self):
        lines = prorate_seats(_sub(seat_price_cents=1000, billable_seats=3),
                              _plan(1000), PE - timedelta(days=15))
        self.assertEqual([l["amount_cents"] for l in lines], [1500, 1500])
        self.assertEqual(lines[1]["vat_cents"], 315)

    def test_trialing_returns_nothing(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(1500),
                                       PE - timedelta(days=10)), [])

    def test_zero_unused_days_returns_nothing(self):
        self.assertEqual(prorate_seats(_sub(), _plan(1500), PE), [])

    def test_negative_unused_days_returns_nothing(self):
        self.assertEqual(prorate_seats(_sub(), _plan(1500), PE + timedelta(days=1)), [])

    def test_exactly_30_days_before_period_end_allowed(self):
        lines = prorate_seats(_sub(billable_seats=2), _plan(1200),
                              PE - timedelta(days=30))
        self.assertEqual(lines[0]["amount_cents"], 2000)
        self.assertEqual(lines[1]["amount_cents"], 2400)

    def test_more_than_30_days_before_period_end_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(1500), PE - timedelta(days=31))

    def test_naive_changed_at_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(1500), datetime(2026, 11, 20))

    def test_naive_period_end_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(period_end=datetime(2026, 11, 30)), _plan(1500),
                          PE - timedelta(days=10))

    def test_float_prices_and_seats_raise(self):
        with self.assertRaises(TypeError):
            prorate_seats(_sub(seat_price_cents=10.5), _plan(1500), PE - timedelta(days=10))
        with self.assertRaises(TypeError):
            prorate_seats(_sub(billable_seats=2.0), _plan(1500), PE - timedelta(days=10))
        with self.assertRaises(TypeError):
            prorate_seats(_sub(), _plan(1500.0), PE - timedelta(days=10))

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(status="paused"), _plan(1500), PE - timedelta(days=10))

    def test_lines_under_50_cents_are_dropped(self):
        self.assertEqual(prorate_seats(_sub(seat_price_cents=10, billable_seats=1),
                                       _plan(10), PE - timedelta(days=1)), [])

    def test_credit_kept_when_charge_dropped(self):
        # credit = ceil(49.5) = 50 kept; charge = floor(49.5) = 49 dropped
        lines = prorate_seats(_sub(seat_price_cents=99, billable_seats=1),
                              _plan(99), PE - timedelta(days=15))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "credit")
        self.assertEqual(lines[0]["amount_cents"], 50)

    def test_exactly_50_cents_is_kept(self):
        lines = prorate_seats(_sub(seat_price_cents=50, billable_seats=1),
                              _plan(50), PE - timedelta(days=30))
        self.assertEqual([l["amount_cents"] for l in lines], [50, 50])
        self.assertEqual(lines[1]["vat_cents"], 10)

    def test_vat_zero_with_vat_id(self):
        lines = prorate_seats(_sub(vat_id="DE123456789"), _plan(1500),
                              PE - timedelta(days=10))
        self.assertEqual(lines[1]["vat_cents"], 0)

    def test_vat_applies_for_blank_vat_id(self):
        for value in (None, "", "   "):
            lines = prorate_seats(_sub(vat_id=value), _plan(1500), PE - timedelta(days=10))
            self.assertEqual(lines[1]["vat_cents"], 1050, repr(value))

    def test_credit_approver_finance_at_threshold(self):
        lines = prorate_seats(_sub(seat_price_cents=50000, billable_seats=1),
                              _plan(50000), PE - timedelta(days=30))
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], FINANCE_APPROVER)

    def test_credit_approver_controller_over_threshold(self):
        lines = prorate_seats(_sub(seat_price_cents=60000, billable_seats=1),
                              _plan(60000), PE - timedelta(days=30))
        self.assertEqual(lines[0]["approved_by"], CONTROLLER_APPROVER)
        self.assertIsNone(lines[1]["approved_by"])

    def test_descriptions_name_plans_and_date(self):
        lines = prorate_seats(_sub(plan_name="Starter"), _plan(1500, "Business"),
                              PE - timedelta(days=10))
        self.assertIn("Starter", lines[0]["description"])
        self.assertIn("Business", lines[1]["description"])
        for line in lines:
            self.assertIn("2026-11-30", line["description"])

    def test_long_plan_name_is_shortened_not_date(self):
        lines = prorate_seats(_sub(plan_name="X" * 200), _plan(1500, "Y" * 200),
                              PE - timedelta(days=10))
        for line in lines:
            self.assertLessEqual(len(line["description"]), MAX_DESCRIPTION)
            self.assertIn("2026-11-30", line["description"])

    def test_output_order_is_credit_then_charge(self):
        lines = prorate_seats(_sub(), _plan(1500), PE - timedelta(days=10))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        self.assertEqual(lines[0]["subscription_id"], "sub_1")

    def test_legacy_discount_is_ignored(self):
        plain = prorate_seats(_sub(), _plan(1500), PE - timedelta(days=10))
        with_legacy = prorate_seats(_sub(legacy_discount=0.5), _plan(1500),
                                    PE - timedelta(days=10))
        self.assertEqual(plain, with_legacy)


if __name__ == "__main__":
    unittest.main()