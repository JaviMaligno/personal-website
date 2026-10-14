"""Seat upgrade proration for Fernhollow Studios billing.

Choices made on the open questions, for tech lead confirmation:
1. Equal old and new seat price returns no lines, same as a downgrade.
2. Charge VAT is 21% of the charge amount, rounded half-up to an integer cent.
   VAT is zero when vat_id is a non-empty, non-whitespace string.
3. Credit approval threshold assumes EUR cents, so "over EUR 500" means
   amount_cents > 50000. Ramon approves those; Thao approves the rest.
4. Invalid input raises ValueError: naive or missing-tzinfo datetimes, non-int,
   bool or negative cents, non-string plan names, and vat_id that is neither
   a string nor None. Validation runs before the trialing check.
5. Any line under 50 cents (including zero) is dropped independently of the
   other line. A credit of exactly 50 is kept.
6. Description truncation shortens the plan name to fit 80 characters, appends
   "...", and strips whitespace before the ellipsis. If the template plus "..."
   cannot fit, ValueError is raised. Only kept lines are described.
7. Description wording: "Unused <plan> credit, period ends YYYY-MM-DD" and
   "Prorated <plan> charge, period ends YYYY-MM-DD". The date uses period_end's
   own timezone.
8. days_left is exact: the microsecond difference divided by one day, held as a
   Fraction, clamped to [0, 13].
9. The seats field is ignored. Only billable_seats is billed. legacy_discount is
   never read.
"""

import math
import unittest
from datetime import datetime, timedelta, timezone
from fractions import Fraction

PERIOD_DAYS = 13
MIN_LINE_CENTS = 50
BIG_CREDIT_CENTS = 50000
VAT_PERCENT = 21
MAX_DESCRIPTION = 80
ELLIPSIS = "..."
FINANCE_APPROVER = "Nguyễn Thị Phương Thảo"
SENIOR_APPROVER = "Ramón Etxeberria-Goñi"
CREDIT_TEMPLATE = "Unused {name} credit, period ends {date}"
CHARGE_TEMPLATE = "Prorated {name} charge, period ends {date}"
_MICROS_PER_DAY = 86_400 * 10**6


def _check_aware(value, name):
    if (not isinstance(value, datetime) or value.tzinfo is None
            or value.utcoffset() is None):
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _check_cents(value, name):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative int number of cents")
    return value


def _check_name(value, name):
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value


def _has_vat_id(vat_id):
    if vat_id is None:
        return False
    if not isinstance(vat_id, str):
        raise ValueError("vat_id must be a string or None")
    return vat_id.strip() != ""


def _days_left(changed_at, period_end):
    micros = (period_end - changed_at) // timedelta(microseconds=1)
    days = Fraction(micros, _MICROS_PER_DAY)
    return min(max(days, Fraction(0)), Fraction(PERIOD_DAYS))


def _description(template, plan_name, date_str):
    base = template.format(name="", date=date_str)
    room = MAX_DESCRIPTION - len(base)
    name = plan_name
    if len(name) > room:
        if room < len(ELLIPSIS):
            raise ValueError("description cannot fit within 80 characters")
        name = name[: room - len(ELLIPSIS)].rstrip() + ELLIPSIS
    text = template.format(name=name, date=date_str)
    if len(text) > MAX_DESCRIPTION:
        raise ValueError("description cannot fit within 80 characters")
    return text


def prorate_seats(subscription, new_plan, changed_at):
    _check_aware(changed_at, "changed_at")
    period_end = subscription["period_end"]
    _check_aware(period_end, "period_end")
    old_price = _check_cents(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _check_cents(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    billable = _check_cents(subscription["billable_seats"], "billable_seats")
    plan_name = _check_name(subscription["plan_name"], "plan_name")
    new_name = _check_name(new_plan["name"], "new_plan name")
    has_vat_id = _has_vat_id(subscription.get("vat_id"))

    if subscription["status"] == "trialing":
        return []
    if new_price <= old_price:
        return []
    if changed_at >= period_end:
        return []

    days = _days_left(changed_at, period_end)
    date_str = period_end.strftime("%Y-%m-%d")
    lines = []

    credit = math.ceil(Fraction(old_price * billable) * days / PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        approver = SENIOR_APPROVER if credit > BIG_CREDIT_CENTS else FINANCE_APPROVER
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(CREDIT_TEMPLATE, plan_name, date_str),
            "approved_by": approver,
        })

    charge = math.floor(Fraction(new_price * billable) * days / PERIOD_DAYS)
    if charge >= MIN_LINE_CENTS:
        if has_vat_id:
            vat = 0
        else:
            vat = math.floor(Fraction(charge * VAT_PERCENT, 100) + Fraction(1, 2))
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description(CHARGE_TEMPLATE, new_name, date_str),
            "approved_by": None,
        })

    return lines


PE = datetime(2026, 10, 26, 9, 0, tzinfo=timezone.utc)


def _at(days=0, hours=0):
    return PE - timedelta(days=days, hours=hours)


def _sub(**overrides):
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Studio Pro",
        "seat_price_cents": 1000,
        "seats": 99,
        "billable_seats": 10,
        "vat_id": None,
        "period_end": PE,
    }
    base.update(overrides)
    return base


def _plan(price, name="Studio Business"):
    return {"name": name, "seat_price_cents": price}


class ProrateSeatsTests(unittest.TestCase):

    def test_trialing_returns_nothing(self):
        self.assertEqual(
            prorate_seats(_sub(status="trialing"), _plan(2000), _at(days=13)), [])

    def test_downgrade_returns_nothing(self):
        self.assertEqual(prorate_seats(_sub(), _plan(500), _at(days=13)), [])

    def test_equal_price_returns_nothing(self):
        self.assertEqual(prorate_seats(_sub(), _plan(1000), _at(days=13)), [])

    def test_changed_at_on_or_after_period_end_returns_nothing(self):
        self.assertEqual(prorate_seats(_sub(), _plan(2000), PE), [])
        self.assertEqual(
            prorate_seats(_sub(), _plan(2000), PE + timedelta(days=1)), [])

    def test_full_period_credit_then_charge_with_vat(self):
        lines = prorate_seats(_sub(), _plan(2000), _at(days=13))
        self.assertEqual([x["kind"] for x in lines], ["credit", "charge"])
        self.assertEqual(lines[0]["amount_cents"], 10000)
        self.assertEqual(lines[0]["vat_cents"], 0)
        self.assertEqual(lines[0]["approved_by"], FINANCE_APPROVER)
        self.assertEqual(lines[1]["amount_cents"], 20000)
        self.assertEqual(lines[1]["vat_cents"], 4200)
        self.assertIsNone(lines[1]["approved_by"])
        self.assertEqual(lines[0]["subscription_id"], "sub_1")

    def test_days_left_clamped_to_thirteen(self):
        self.assertEqual(
            prorate_seats(_sub(), _plan(2000), _at(days=20)),
            prorate_seats(_sub(), _plan(2000), _at(days=13)))

    def test_credit_rounds_up_and_charge_rounds_down(self):
        # 8 hours is 1/3 of a day: credit = 20000/39 = 512.82 -> 513,
        # charge = 30000/39 = 769.23 -> 769
        lines = prorate_seats(
            _sub(seat_price_cents=2000), _plan(3000), _at(hours=8))
        self.assertEqual(lines[0]["amount_cents"], 513)
        self.assertEqual(lines[1]["amount_cents"], 769)

    def test_exact_fractional_day_has_no_rounding(self):
        # 6.5 days: credit = 100 * 6.5 / 13 = 50, charge = 200 * 6.5 / 13 = 100
        lines = prorate_seats(
            _sub(seat_price_cents=100, billable_seats=1),
            _plan(200), _at(days=6, hours=12))
        self.assertEqual(lines[0]["amount_cents"], 50)
        self.assertEqual(lines[1]["amount_cents"], 100)

    def test_49_dropped_and_50_kept(self):
        lines = prorate_seats(
            _sub(seat_price_cents=637, billable_seats=1), _plan(1000), _at(days=1))
        self.assertEqual([x["kind"] for x in lines], ["charge"])

        lines = prorate_seats(
            _sub(seat_price_cents=650, billable_seats=1), _plan(1000), _at(days=1))
        self.assertEqual(lines[0]["kind"], "credit")
        self.assertEqual(lines[0]["amount_cents"], 50)

    def test_both_lines_under_fifty_dropped(self):
        # credit = ceil(600/13) = 47, charge = floor(637/13) = 49
        self.assertEqual(
            prorate_seats(_sub(seat_price_cents=600, billable_seats=1),
                          _plan(637), _at(days=1)), [])

    def test_credit_at_threshold_approved_by_finance(self):
        lines = prorate_seats(
            _sub(seat_price_cents=50000, billable_seats=1),
            _plan(50001), _at(days=13))
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], FINANCE_APPROVER)

    def test_credit_over_threshold_approved_by_senior(self):
        lines = prorate_seats(
            _sub(seat_price_cents=50001, billable_seats=1),
            _plan(50002), _at(days=13))
        self.assertEqual(lines[0]["amount_cents"], 50001)
        self.assertEqual(lines[0]["approved_by"], SENIOR_APPROVER)

    def test_vat_id_zeroes_charge_vat(self):
        lines = prorate_seats(
            _sub(vat_id="DE123456789"), _plan(2000), _at(days=13))
        self.assertEqual(lines[1]["vat_cents"], 0)

    def test_whitespace_vat_id_still_charges_vat(self):
        lines = prorate_seats(_sub(vat_id="   "), _plan(2000), _at(days=13))
        self.assertEqual(lines[1]["vat_cents"], 4200)

    def test_vat_rounds_half_up(self):
        # credit 10 is dropped; charge 50 has VAT 10.5 -> 11
        lines = prorate_seats(
            _sub(seat_price_cents=10, billable_seats=1), _plan(50), _at(days=13))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["amount_cents"], 50)
        self.assertEqual(lines[0]["vat_cents"], 11)

    def test_legacy_discount_and_seats_have_no_effect(self):
        plain = prorate_seats(_sub(), _plan(2000), _at(days=13))
        noisy = prorate_seats(
            _sub(legacy_discount=90, seats=1), _plan(2000), _at(days=13))
        self.assertEqual(plain, noisy)

    def test_long_plan_name_truncated_and_date_kept(self):
        lines = prorate_seats(
            _sub(plan_name="X" * 200), _plan(2000), _at(days=13))
        desc = lines[0]["description"]
        self.assertLessEqual(len(desc), MAX_DESCRIPTION)
        self.assertIn(ELLIPSIS, desc)
        self.assertTrue(desc.endswith("period ends 2026-10-26"))

    def test_long_new_plan_name_truncated_and_date_kept(self):
        lines = prorate_seats(
            _sub(), _plan(2000, name="Y" * 200), _at(days=13))
        desc = lines[1]["description"]
        self.assertLessEqual(len(desc), MAX_DESCRIPTION)
        self.assertIn(ELLIPSIS, desc)
        self.assertTrue(desc.endswith("period ends 2026-10-26"))

    def test_description_date_uses_period_end_timezone(self):
        tz = timezone(timedelta(hours=9))
        pe = datetime(2026, 10, 26, 8, 0, tzinfo=tz)  # 2026-10-25 23:00 UTC
        lines = prorate_seats(
            _sub(period_end=pe), _plan(2000), pe - timedelta(days=13))
        self.assertIn("2026-10-26", lines[0]["description"])

    def test_description_that_cannot_fit_raises(self):
        template = "A" * 78 + " {name} {date}"
        with self.assertRaises(ValueError):
            _description(template, "Plan", "2026-10-26")

    def test_naive_changed_at_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(2000), datetime(2026, 10, 20))

    def test_naive_period_end_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(
                _sub(period_end=datetime(2026, 10, 26)),
                _plan(2000), _at(days=13))

    def test_float_cents_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(seat_price_cents=10.0), _plan(2000), _at(days=13))


if __name__ == "__main__":
    unittest.main()