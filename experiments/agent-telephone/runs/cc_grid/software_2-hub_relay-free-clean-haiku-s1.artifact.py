/private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-9nh28iij/seat_proration.py
```python
# /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-9nh28iij/seat_proration.py
"""Seat-upgrade proration for Fernhollow Studios.

All money is integer cents. Fraction is used for exact intermediate arithmetic.
Only the standard library is used.

Open-question defaults (each kept in a named constant below):
  - Large-credit threshold: EUR 500 (50000 cents), applied as strictly greater than.
  - Currency: all amounts are EUR.
  - Fraction: exact elapsed time (microsecond resolution), divided by 30 days.
  - Descriptions: period_end date taken in UTC.
  - Description length: len() of the str, max 80 characters, plan name shortened first.
  - Equal prices return [].
  - Changed more than 30 days before period_end raises ValueError.
  - VAT rounds down.
"""

import math
from datetime import timedelta, timezone
from fractions import Fraction

PERIOD_DAYS = 30
PERIOD_LENGTH = timedelta(days=PERIOD_DAYS)
PERIOD_MICROS = PERIOD_DAYS * 24 * 60 * 60 * 10**6

MIN_LINE_CENTS = 50                        # lines under 50 cents are dropped (rule 6)
VAT_PERCENT = 21                           # VAT rate on charges (rule 7)
DEFAULT_CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
LARGE_CREDIT_THRESHOLD_CENTS = 50000       # EUR 500; applies when strictly greater (rule 8)
MAX_DESCRIPTION_LEN = 80
ELLIPSIS = "…"                             # one character, so it counts as 1 toward the limit


def _is_aware(dt):
    return dt.tzinfo is not None and dt.utcoffset() is not None


def _fraction_unused(changed_at, period_end):
    # timedelta // timedelta(microseconds=1) is an exact integer count of microseconds.
    micros = (period_end - changed_at) // timedelta(microseconds=1)
    return Fraction(micros, PERIOD_MICROS)


def _describe(head, plan, tail):
    text = f"{head}{plan}{tail}"
    if len(text) <= MAX_DESCRIPTION_LEN:
        return text
    room = MAX_DESCRIPTION_LEN - len(head) - len(tail)
    if room < 1:
        raise ValueError("description cannot fit within 80 characters")
    if len(plan) > room:
        plan = plan[: room - 1] + ELLIPSIS
    return f"{head}{plan}{tail}"


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription["period_end"]
    if not (_is_aware(changed_at) and _is_aware(period_end)):
        raise ValueError("changed_at and period_end must be timezone-aware")

    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:
        # Strict downgrade applies at renewal (rule 2); equal prices mean no change (rule 12).
        return []

    if changed_at >= period_end:
        return []

    if period_end - changed_at > PERIOD_LENGTH:
        raise ValueError("changed_at is more than 30 days before period_end")

    billable = subscription["billable_seats"]
    fraction = _fraction_unused(changed_at, period_end)

    credit_cents = math.ceil(old_price * billable * fraction)   # credit rounds up
    charge_cents = math.floor(new_price * billable * fraction)  # charge rounds down

    date_str = period_end.astimezone(timezone.utc).strftime("%Y-%m-%d")
    sub_id = subscription["id"]
    lines = []

    if credit_cents >= MIN_LINE_CENTS:
        approver = (
            LARGE_CREDIT_APPROVER
            if credit_cents > LARGE_CREDIT_THRESHOLD_CENTS
            else DEFAULT_CREDIT_APPROVER
        )
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,  # credits carry no VAT (rule 4)
            "description": _describe(
                "Credit for unused ",
                subscription["plan_name"],
                f" seats, period end {date_str}",
            ),
            "approved_by": approver,
        })

    if charge_cents >= MIN_LINE_CENTS:
        # VAT is rounded DOWN (floor) because rounding never favours the company.
        # Integer floor division on non-negative cents gives exactly that.
        # A set vat_id (e.g. reverse-charge customers) suppresses VAT entirely.
        if subscription["vat_id"]:
            vat_cents = 0
        else:
            vat_cents = charge_cents * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _describe(
                "Upgrade to ",
                new_plan["name"],
                f" seats, period end {date_str}",
            ),
            "approved_by": None,
        })

    return lines
```

/private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-9nh28iij/test_seat_proration.py
```python
# /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-9nh28iij/test_seat_proration.py
"""Unit tests for seat_proration. Run with: python -m unittest test_seat_proration

Note: these tests were written but not executed in this session.
"""

import unittest
from datetime import datetime, timedelta, timezone

from seat_proration import (
    DEFAULT_CREDIT_APPROVER,
    LARGE_CREDIT_APPROVER,
    MAX_DESCRIPTION_LEN,
    _describe,
    prorate_seats,
)

UTC = timezone.utc
PE = datetime(2026, 11, 1, 0, 0, tzinfo=UTC)


def make_sub(**overrides):
    sub = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Basic",
        "seat_price_cents": 1000,
        "seats": 10,
        "billable_seats": 10,
        "vat_id": None,
        "period_end": PE,
    }
    sub.update(overrides)
    return sub


PRO = {"name": "Pro", "seat_price_cents": 1500}


class WorkedExample(unittest.TestCase):
    def test_credit_charge_and_vat(self):
        lines = prorate_seats(make_sub(), PRO, PE - timedelta(days=10))
        self.assertEqual(len(lines), 2)
        credit, charge = lines
        self.assertEqual(credit["kind"], "credit")
        self.assertEqual(credit["amount_cents"], 3334)
        self.assertEqual(credit["vat_cents"], 0)
        self.assertEqual(credit["approved_by"], DEFAULT_CREDIT_APPROVER)
        self.assertEqual(charge["kind"], "charge")
        self.assertEqual(charge["amount_cents"], 5000)
        self.assertEqual(charge["vat_cents"], 1050)
        self.assertIsNone(charge["approved_by"])
        self.assertEqual(credit["subscription_id"], "sub_1")

    def test_charge_rounds_down_and_vat_rounds_down(self):
        lines = prorate_seats(make_sub(seat_price_cents=1000, billable_seats=1),
                              {"name": "Pro", "seat_price_cents": 1001},
                              PE - timedelta(days=10))
        credit, charge = lines
        self.assertEqual(credit["amount_cents"], 334)   # ceil(333.33)
        self.assertEqual(charge["amount_cents"], 333)   # floor(333.67)
        self.assertEqual(charge["vat_cents"], 69)       # floor(69.93)


class ReturnsEmpty(unittest.TestCase):
    def test_trialing(self):
        self.assertEqual(prorate_seats(make_sub(status="trialing"), PRO,
                                       PE - timedelta(days=10)), [])

    def test_downgrade(self):
        self.assertEqual(prorate_seats(make_sub(), {"name": "Lite", "seat_price_cents": 500},
                                       PE - timedelta(days=10)), [])

    def test_equal_prices(self):
        self.assertEqual(prorate_seats(make_sub(), {"name": "Same", "seat_price_cents": 1000},
                                       PE - timedelta(days=10)), [])

    def test_changed_at_at_or_after_period_end(self):
        self.assertEqual(prorate_seats(make_sub(), PRO, PE), [])
        self.assertEqual(prorate_seats(make_sub(), PRO, PE + timedelta(hours=1)), [])


class Rules(unittest.TestCase):
    def test_credit_under_50_cents_dropped_charge_kept(self):
        # Credit: ceil(1000 * 1/30) = 34 -> dropped. Charge: floor(1500 * 1/30) = 50 -> kept.
        lines = prorate_seats(make_sub(billable_seats=1), PRO, PE - timedelta(days=1))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 50)
        self.assertEqual(lines[0]["vat_cents"], 10)

    def test_credit_over_50000_gets_large_approver(self):
        lines = prorate_seats(make_sub(seat_price_cents=100000, billable_seats=1),
                              {"name": "Pro", "seat_price_cents": 200000},
                              PE - timedelta(days=30))
        self.assertEqual(lines[0]["amount_cents"], 100000)
        self.assertEqual(lines[0]["approved_by"], LARGE_CREDIT_APPROVER)

    def test_credit_exactly_50000_uses_default_approver(self):
        lines = prorate_seats(make_sub(seat_price_cents=50000, billable_seats=1),
                              {"name": "Pro", "seat_price_cents": 60000},
                              PE - timedelta(days=30))
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], DEFAULT_CREDIT_APPROVER)

    def test_vat_id_suppresses_vat(self):
        lines = prorate_seats(make_sub(vat_id="DE123456789"), PRO, PE - timedelta(days=10))
        self.assertTrue(all(line["vat_cents"] == 0 for line in lines))
        self.assertEqual(lines[1]["amount_cents"], 5000)

    def test_seats_ignored_in_favour_of_billable_seats(self):
        lines = prorate_seats(make_sub(seats=100, billable_seats=10), PRO,
                              PE - timedelta(days=10))
        self.assertEqual(lines[0]["amount_cents"], 3334)
        self.assertEqual(lines[1]["amount_cents"], 5000)

    def test_over_30_days_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(make_sub(), PRO, PE - timedelta(days=31))

    def test_naive_datetimes_raise(self):
        naive = datetime(2026, 10, 22, 0, 0)
        with self.assertRaises(ValueError):
            prorate_seats(make_sub(), PRO, naive)
        with self.assertRaises(ValueError):
            prorate_seats(make_sub(period_end=naive.replace(tzinfo=None)), PRO,
                          PE - timedelta(days=10))


class Descriptions(unittest.TestCase):
    def test_long_plan_name_is_shortened_and_date_kept(self):
        long_name = "X" * 200
        lines = prorate_seats(make_sub(plan_name=long_name), {"name": long_name,
                              "seat_price_cents": 1500}, PE - timedelta(days=10))
        for line in lines:
            self.assertLessEqual(len(line["description"]), MAX_DESCRIPTION_LEN)
            self.assertIn("2026-11-01", line["description"])
            self.assertIn("\u2026", line["description"])

    def test_plan_named_and_date_utc(self):
        pe_plus5 = datetime(2026, 11, 1, 3, 0, tzinfo=timezone(timedelta(hours=5)))  # 2026-10-31 22:00 UTC
        lines = prorate_seats(make_sub(period_end=pe_plus5), PRO,
                              pe_plus5 - timedelta(days=10))
        self.assertIn("Basic", lines[0]["description"])
        self.assertIn("2026-10-31", lines[0]["description"])
        self.assertIn("Pro", lines[1]["description"])
        self.assertIn("2026-10-31", lines[1]["description"])

    def test_describe_raises_when_still_too_long(self):
        with self.assertRaises(ValueError):
            _describe("h" * 70, "plan", "t" * 20)


if __name__ == "__main__":
    unittest.main()
```