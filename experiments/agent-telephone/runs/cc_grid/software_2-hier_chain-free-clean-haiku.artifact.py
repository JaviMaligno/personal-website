# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-ydki1r37/seat_proration/seat_proration.py
"""Seat upgrade proration for Fernhollow Studios.

Assumptions and ambiguities beyond the brief:
- Input validation runs before the trialing and downgrade checks, so malformed
  input always raises, even when the function would otherwise return [].
- A non-datetime time argument raises TypeError. A naive datetime raises ValueError.
- bool is rejected wherever an integer is required.
- Credit lines carry zero VAT, as the brief states. This overrides the house
  rule that VAT applies to credits too.
- Credit uses ceiling and charge and VAT use floor, as the brief states. This
  overrides the house half-up rule. The directions are isolated in the
  Rounding section for review.
- A vat_id that is not None and is not a string is treated as present.
"""

from datetime import datetime, timedelta

# Rounding: directions are under review. Change them only here.

def _round_credit(numerator):
    """Credit amount: ceiling of numerator / 30."""
    return -((-numerator) // 30)


def _round_charge(numerator):
    """Charge amount: floor of numerator / 30."""
    return numerator // 30


def _round_vat(amount_cents):
    """Charge VAT: floor of amount_cents * 21 / 100."""
    return amount_cents * 21 // 100


# Constants

PERIOD_DAYS = 30
MICROS_PER_DAY = 86_400_000_000
MIN_LINE_CENTS = 50
HIGH_CREDIT_CENTS = 50_000
APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
APPROVER_HIGH = "Ramón Etxeberria-Goñi"
MAX_DESCRIPTION = 80
PLAN_NAME_LIMIT = 43
PLAN_NAME_PREFIX = 40


# Validation helpers

def _check_money(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _check_aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


# Computation helpers

def _days_left(changed_at, period_end):
    delta = period_end - changed_at
    micros = delta // timedelta(microseconds=1)
    days = micros // MICROS_PER_DAY
    return min(max(days, 0), PERIOD_DAYS)


def _description(kind_word, plan_name, period_end):
    date = f"{period_end.year:04d}-{period_end.month:02d}-{period_end.day:02d}"

    def build(name):
        return f"{kind_word}: {name} seats, period end {date}"

    text = build(plan_name)
    if len(text) > MAX_DESCRIPTION:
        text = build(plan_name[:PLAN_NAME_PREFIX] + "...")
    if len(text) > MAX_DESCRIPTION:
        raise ValueError("description exceeds 80 characters")
    return text


def _line(sub_id, kind, amount, vat, description, approved_by):
    return {
        "subscription_id": sub_id,
        "kind": kind,
        "amount_cents": amount,
        "vat_cents": vat,
        "description": description,
        "approved_by": approved_by,
    }


# Public entry point

def prorate_seats(subscription, new_plan, changed_at):
    billable = subscription["billable_seats"]
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    period_end = subscription["period_end"]

    _check_aware(changed_at, "changed_at")
    _check_aware(period_end, "period_end")
    _check_money(billable, "billable_seats")
    _check_money(old_price, "seat_price_cents")
    _check_money(new_price, "seat_price_cents")

    if subscription["status"] == "trialing":
        return []

    if new_price < old_price:
        return []

    days = _days_left(changed_at, period_end)
    sub_id = subscription["id"]

    credit_amount = _round_credit(billable * old_price * days)
    charge_amount = _round_charge(billable * new_price * days)

    vat_id = subscription["vat_id"]
    reverse_charge = vat_id is not None and str(vat_id).strip() != ""
    charge_vat = 0 if reverse_charge else _round_vat(charge_amount)

    lines = []

    if credit_amount >= MIN_LINE_CENTS:
        approver = APPROVER_HIGH if credit_amount > HIGH_CREDIT_CENTS else APPROVER_DEFAULT
        lines.append(_line(
            sub_id,
            "credit",
            credit_amount,
            0,
            _description("Credit", subscription["plan_name"], period_end),
            approver,
        ))

    if charge_amount >= MIN_LINE_CENTS:
        lines.append(_line(
            sub_id,
            "charge",
            charge_amount,
            charge_vat,
            _description("Charge", new_plan["name"], period_end),
            None,
        ))

    return lines

# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-ydki1r37/seat_proration/test_seat_proration.py
# Not executed: this environment has no way to run Python, so these tests are unverified.

import unittest
from datetime import datetime, timedelta, timezone

from seat_proration import prorate_seats

PE = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
PE_DATE = "2026-11-10"


def make_sub(**over):
    sub = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Basic",
        "seat_price_cents": 999,
        "seats": 99,
        "billable_seats": 3,
        "vat_id": None,
        "period_end": PE,
    }
    sub.update(over)
    return sub


def make_plan(price=1499, name="Pro"):
    return {"name": name, "seat_price_cents": price}


class SeatProrationTests(unittest.TestCase):

    def test_worked_example(self):
        result = prorate_seats(make_sub(), make_plan(), PE - timedelta(days=7))
        self.assertEqual(result, [
            {
                "subscription_id": "sub_1",
                "kind": "credit",
                "amount_cents": 700,
                "vat_cents": 0,
                "description": "Credit: Basic seats, period end 2026-11-10",
                "approved_by": "Nguyễn Thị Phương Thảo",
            },
            {
                "subscription_id": "sub_1",
                "kind": "charge",
                "amount_cents": 1049,
                "vat_cents": 220,
                "description": "Charge: Pro seats, period end 2026-11-10",
                "approved_by": None,
            },
        ])

    def test_trialing_returns_empty(self):
        sub = make_sub(status="trialing")
        self.assertEqual(prorate_seats(sub, make_plan(), PE - timedelta(days=7)), [])

    def test_downgrade_returns_empty(self):
        result = prorate_seats(make_sub(), make_plan(price=500), PE - timedelta(days=7))
        self.assertEqual(result, [])

    def test_equal_price_proceeds(self):
        result = prorate_seats(make_sub(), make_plan(price=999), PE - timedelta(days=7))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["amount_cents"], 700)
        self.assertEqual(result[1]["amount_cents"], 699)
        self.assertEqual(result[1]["vat_cents"], 146)

    def test_changed_at_equal_period_end_returns_empty(self):
        self.assertEqual(prorate_seats(make_sub(), make_plan(), PE), [])

    def test_changed_at_after_period_end_returns_empty(self):
        self.assertEqual(prorate_seats(make_sub(), make_plan(), PE + timedelta(days=1)), [])

    def test_fifty_cent_line_kept(self):
        result = prorate_seats(
            make_sub(billable_seats=1, seat_price_cents=150),
            make_plan(price=150),
            PE - timedelta(days=10),
        )
        self.assertEqual([r["amount_cents"] for r in result], [50, 50])
        self.assertEqual(result[1]["vat_cents"], 10)

    def test_forty_nine_cent_line_dropped(self):
        result = prorate_seats(
            make_sub(billable_seats=1, seat_price_cents=147),
            make_plan(price=147),
            PE - timedelta(days=10),
        )
        self.assertEqual(result, [])

    def test_forty_nine_cent_credit_dropped_charge_kept(self):
        result = prorate_seats(
            make_sub(billable_seats=1, seat_price_cents=147),
            make_plan(price=150),
            PE - timedelta(days=10),
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["kind"], "charge")
        self.assertEqual(result[0]["amount_cents"], 50)

    def test_credit_exactly_50000_approved_by_thao(self):
        result = prorate_seats(
            make_sub(billable_seats=1, seat_price_cents=50_000),
            make_plan(price=50_000),
            PE - timedelta(days=30),
        )
        self.assertEqual(result[0]["amount_cents"], 50_000)
        self.assertEqual(result[0]["approved_by"], "Nguyễn Thị Phương Thảo")

    def test_credit_50001_approved_by_ramon(self):
        result = prorate_seats(
            make_sub(billable_seats=1, seat_price_cents=50_001),
            make_plan(price=50_001),
            PE - timedelta(days=30),
        )
        self.assertEqual(result[0]["amount_cents"], 50_001)
        self.assertEqual(result[0]["approved_by"], "Ramón Etxeberria-Goñi")

    def test_vat_id_gives_zero_charge_vat(self):
        result = prorate_seats(make_sub(vat_id="DE123456789"), make_plan(), PE - timedelta(days=7))
        self.assertEqual(result[1]["amount_cents"], 1049)
        self.assertEqual(result[1]["vat_cents"], 0)

    def test_none_empty_or_blank_vat_id_gives_vat(self):
        for vat in (None, "", "   "):
            with self.subTest(vat_id=vat):
                result = prorate_seats(make_sub(vat_id=vat), make_plan(), PE - timedelta(days=7))
                self.assertEqual(result[1]["vat_cents"], 220)

    def test_credit_vat_always_zero(self):
        result = prorate_seats(make_sub(vat_id=None), make_plan(), PE - timedelta(days=7))
        self.assertEqual(result[0]["vat_cents"], 0)
        result = prorate_seats(make_sub(vat_id="DE1"), make_plan(), PE - timedelta(days=7))
        self.assertEqual(result[0]["vat_cents"], 0)

    def test_zero_billable_seats_returns_empty(self):
        result = prorate_seats(make_sub(billable_seats=0), make_plan(), PE - timedelta(days=7))
        self.assertEqual(result, [])

    def test_seats_field_has_no_effect(self):
        a = prorate_seats(make_sub(seats=1), make_plan(), PE - timedelta(days=7))
        b = prorate_seats(make_sub(seats=500), make_plan(), PE - timedelta(days=7))
        self.assertEqual(a, b)
        self.assertEqual(a[0]["amount_cents"], 700)

    def test_legacy_discount_ignored(self):
        plain = prorate_seats(make_sub(), make_plan(), PE - timedelta(days=7))
        with_discount = prorate_seats(
            make_sub(legacy_discount=90), make_plan(), PE - timedelta(days=7)
        )
        self.assertEqual(plain, with_discount)

    def test_more_than_30_days_clamped(self):
        result = prorate_seats(make_sub(), make_plan(), PE - timedelta(days=60))
        self.assertEqual(result[0]["amount_cents"], 2997)
        self.assertEqual(result[1]["amount_cents"], 4497)
        self.assertEqual(result[1]["vat_cents"], 944)

    def test_partial_days_not_counted(self):
        result = prorate_seats(make_sub(), make_plan(), PE - timedelta(days=7, hours=23))
        self.assertEqual(result[0]["amount_cents"], 700)
        self.assertEqual(result[1]["amount_cents"], 1049)

    def test_long_plan_names_shortened(self):
        result = prorate_seats(
            make_sub(plan_name="X" * 60),
            make_plan(name="Y" * 60),
            PE - timedelta(days=7),
        )
        credit_desc = "Credit: " + "X" * 40 + "..." + " seats, period end " + PE_DATE
        charge_desc = "Charge: " + "Y" * 40 + "..." + " seats, period end " + PE_DATE
        self.assertEqual(result[0]["description"], credit_desc)
        self.assertEqual(result[1]["description"], charge_desc)
        self.assertEqual(len(credit_desc), 80)
        self.assertTrue(result[0]["description"].endswith(PE_DATE))

    def test_43_char_plan_name_not_truncated(self):
        name = "C" * 43
        result = prorate_seats(make_sub(plan_name=name), make_plan(), PE - timedelta(days=7))
        expected = "Credit: " + name + " seats, period end " + PE_DATE
        self.assertEqual(result[0]["description"], expected)
        self.assertEqual(len(expected), 80)

    def test_date_uses_own_timezone(self):
        pe = datetime(2026, 11, 10, 23, 30, tzinfo=timezone(timedelta(hours=-5)))
        sub = make_sub(period_end=pe)
        result = prorate_seats(sub, make_plan(), pe - timedelta(days=7))
        self.assertTrue(result[0]["description"].endswith(PE_DATE))
        self.assertTrue(result[1]["description"].endswith(PE_DATE))

    def test_naive_changed_at_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(make_sub(), make_plan(), datetime(2026, 11, 3, 12, 0))

    def test_naive_period_end_raises(self):
        sub = make_sub(period_end=datetime(2026, 11, 10, 12, 0))
        with self.assertRaises(ValueError):
            prorate_seats(sub, make_plan(), datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc))

    def test_non_integer_billable_seats_raises(self):
        for bad in (3.0, "3", True, -1):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    prorate_seats(make_sub(billable_seats=bad), make_plan(), PE - timedelta(days=7))

    def test_bad_money_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(make_sub(seat_price_cents=-1), make_plan(), PE - timedelta(days=7))
        with self.assertRaises(ValueError):
            prorate_seats(make_sub(seat_price_cents=999.0), make_plan(), PE - timedelta(days=7))
        with self.assertRaises(ValueError):
            prorate_seats(make_sub(), make_plan(price=1499.0), PE - timedelta(days=7))


if __name__ == "__main__":
    unittest.main()