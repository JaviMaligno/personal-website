"""Seat upgrade proration for Fernhollow Studios (client contact: Ingrid).

Pure function, standard library only, integer-cent money in EUR.

Defaults adopted, pending client confirmation:
- R17 threshold: credit approver switches only when credit amount_cents is strictly greater than 50000.
- R19 unused days: fractional days (exact elapsed duration), not whole days.
- R12 description wording: credit "Unused {old plan} seats until {YYYY-MM-DD}", charge "Unused {new plan} seats until {YYYY-MM-DD}".
- R24 equal seat price: empty list (no-op).
- R25 input validation: missing keys, naive datetimes, non-int or negative cents/seats raise ValueError.
- R27 statuses other than "trialing" (canceled, past_due, paused) are prorated.
- R22 changed_at before period start (period_end minus 30 days) raises ValueError.
- R23 billable_seats of 0 returns an empty list.

Status: the tests below were written but not executed in this environment.
Run with: python3 -I -m unittest <this file>
"""

import math
import unicodedata
import unittest
from datetime import datetime, timedelta, timezone
from fractions import Fraction

CREDIT_APPROVER = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
LARGE_CREDIT_APPROVER = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")
LARGE_CREDIT_CENTS = 50000
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
PERIOD_DAYS = 30
MAX_DESC = 80
MICROS_PER_DAY = 86_400_000_000
TEMPLATE = "Unused {name} seats until {date}"
SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
            "billable_seats", "vat_id", "period_end")
PLAN_KEYS = ("name", "seat_price_cents")


def _require(d, keys, label):
    if not isinstance(d, dict):
        raise ValueError(f"{label} must be a dict")
    missing = [k for k in keys if k not in d]
    if missing:
        raise ValueError(f"{label} missing keys: {missing}")


def _nonneg_int(v, label):
    if type(v) is not int or v < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return v


def _text(v, label):
    if not isinstance(v, str) or not v:
        raise ValueError(f"{label} must be a non-empty string")
    return v


def _aware(v, label):
    if not isinstance(v, datetime) or v.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")
    return v


def _describe(template, name, date_str):
    fixed = len(template.format(name="", date=date_str))
    budget = MAX_DESC - fixed
    if budget < 0:
        raise ValueError("description template exceeds 80 characters")
    if len(name) > budget:
        if budget < 4:
            raise ValueError("plan name cannot fit in the description")
        name = name[:budget - 3] + "..."
    return template.format(name=name, date=date_str)


def prorate_seats(subscription, new_plan, changed_at):
    _require(subscription, SUB_KEYS, "subscription")
    _require(new_plan, PLAN_KEYS, "new_plan")
    sub_id = _text(subscription["id"], "id")
    status = _text(subscription["status"], "status")
    old_name = _text(subscription["plan_name"], "plan_name")
    old_price = _nonneg_int(subscription["seat_price_cents"], "seat_price_cents")
    _nonneg_int(subscription["seats"], "seats")
    billable = _nonneg_int(subscription["billable_seats"], "billable_seats")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise ValueError("vat_id must be a string or None")
    period_end = _aware(subscription["period_end"], "period_end")
    new_name = _text(new_plan["name"], "new plan name")
    new_price = _nonneg_int(new_plan["seat_price_cents"], "new seat_price_cents")
    changed_at = _aware(changed_at, "changed_at")

    if changed_at >= period_end:
        return []
    if changed_at < period_end - timedelta(days=PERIOD_DAYS):
        raise ValueError("changed_at is before the billing period start")
    if status == "trialing":
        return []
    if billable == 0 or new_price <= old_price:
        return []

    elapsed_micros = (period_end - changed_at) // timedelta(microseconds=1)
    unused_days = Fraction(elapsed_micros, MICROS_PER_DAY)
    fraction = unused_days / PERIOD_DAYS
    credit_cents = math.ceil(old_price * billable * fraction)
    charge_cents = math.floor(new_price * billable * fraction)
    date_str = period_end.astimezone(timezone.utc).date().isoformat()

    lines = []
    if credit_cents >= MIN_LINE_CENTS:
        approver = (LARGE_CREDIT_APPROVER if credit_cents > LARGE_CREDIT_CENTS
                    else CREDIT_APPROVER)
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe(TEMPLATE, old_name, date_str),
            "approved_by": approver,
        })
    if charge_cents >= MIN_LINE_CENTS:
        vat = 0 if vat_id else charge_cents * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat,
            "description": _describe(TEMPLATE, new_name, date_str),
            "approved_by": None,
        })
    return lines


UTC = timezone.utc
END = datetime(2026, 11, 30, 12, 0, tzinfo=UTC)


def _sub(old=1000, billable=10, vat_id=None, status="active", name="Basic"):
    return {"id": "sub_1", "status": status, "plan_name": name,
            "seat_price_cents": old, "seats": billable + 2,
            "billable_seats": billable, "vat_id": vat_id, "period_end": END}


def _plan(price, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def _at(days_unused):
    return END - timedelta(days=days_unused)


class ProrateTests(unittest.TestCase):

    def test_e1_basic_upgrade(self):
        lines = prorate_seats(_sub(), _plan(1500), _at(10))
        self.assertEqual(len(lines), 2)
        credit, charge = lines
        self.assertEqual(credit["kind"], "credit")
        self.assertEqual(credit["amount_cents"], 3334)
        self.assertEqual(credit["vat_cents"], 0)
        self.assertEqual(credit["approved_by"], CREDIT_APPROVER)
        self.assertEqual(charge["kind"], "charge")
        self.assertEqual(charge["amount_cents"], 5000)
        self.assertEqual(charge["vat_cents"], 1050)
        self.assertIsNone(charge["approved_by"])

    def test_e2_large_credit(self):
        lines = prorate_seats(_sub(old=5000, billable=20), _plan(6000), _at(30))
        credit, charge = lines
        self.assertEqual(credit["amount_cents"], 100000)
        self.assertEqual(credit["approved_by"], LARGE_CREDIT_APPROVER)
        self.assertEqual(charge["amount_cents"], 120000)
        self.assertEqual(charge["vat_cents"], 25200)

    def test_e3_credit_exactly_threshold(self):
        lines = prorate_seats(_sub(old=5000, billable=10), _plan(6000), _at(30))
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], CREDIT_APPROVER)
        self.assertEqual(lines[1]["amount_cents"], 60000)
        self.assertEqual(lines[1]["vat_cents"], 12600)

    def test_e4_downgrade(self):
        self.assertEqual(prorate_seats(_sub(old=1500), _plan(1000), _at(10)), [])

    def test_e5_trialing(self):
        self.assertEqual(
            prorate_seats(_sub(status="trialing"), _plan(1500), _at(10)), [])

    def test_e6_equal_price(self):
        self.assertEqual(prorate_seats(_sub(old=1000), _plan(1000), _at(10)), [])

    def test_e7_both_lines_skipped(self):
        self.assertEqual(
            prorate_seats(_sub(old=100, billable=1), _plan(110), _at(10)), [])

    def test_e8_reverse_charge(self):
        lines = prorate_seats(_sub(vat_id="DE123456789"), _plan(1500), _at(10))
        self.assertEqual(lines[0]["amount_cents"], 3334)
        self.assertEqual(lines[0]["vat_cents"], 0)
        self.assertEqual(lines[1]["amount_cents"], 5000)
        self.assertEqual(lines[1]["vat_cents"], 0)

    def test_e9_changed_at_equals_period_end(self):
        self.assertEqual(prorate_seats(_sub(), _plan(1500), END), [])

    def test_e10_long_name_truncated_date_kept(self):
        long_name = "P" * 100
        lines = prorate_seats(_sub(name=long_name), _plan(1500, long_name), _at(10))
        expected = "Unused " + "P" * 47 + "..." + " seats until 2026-11-30"
        self.assertEqual(lines[0]["description"], expected)
        self.assertEqual(lines[1]["description"], expected)
        self.assertLessEqual(len(expected), MAX_DESC)

    def test_name_that_cannot_fit_raises(self):
        with self.assertRaises(ValueError):
            _describe("X" * 66 + " {name} {date}", "Basic", "2026-11-30")
        with self.assertRaises(ValueError):
            _describe("X" * 80 + " {name} {date}", "Basic", "2026-11-30")

    def test_validation(self):
        bad = _sub()
        del bad["vat_id"]
        with self.assertRaises(ValueError):
            prorate_seats(bad, _plan(1500), _at(10))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(1500), datetime(2026, 11, 20))


if __name__ == "__main__":
    unittest.main()