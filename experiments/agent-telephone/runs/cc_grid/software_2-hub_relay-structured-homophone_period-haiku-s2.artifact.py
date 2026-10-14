"""Prorated seat-upgrade invoice lines for Fernhollow Studios.

Assumptions where the spec was open (defaults implemented, pending client confirmation):
- S3: the 13-day billing period is real. period_start = period_end - 13 days. A changed_at earlier than that raises ValueError.
- S2: the day fraction is exact (Fraction over integer microseconds), not whole days.
- S4/S10: rounding and thresholds use net amounts (before VAT).
- S12: approved_by is a name string, not an ID.
- S18: bad input (missing keys, non-int or bool amounts, negative values, non-aware datetimes) raises ValueError.
- S17: description wording is as given in R16.
- S16: only status "active" is prorated. Every other status returns [].
- S2 (UTC): datetimes are compared as aware instants. The date in the description is period_end's own calendar date in its own timezone (R16).
- R14/S8 vs house rule: credits carry vat_cents = 0, which overrides the house rule that VAT applies to credits too. The spec says this explicitly, so it is followed. Flagged for confirmation.
- A whitespace-only vat_id is treated as "no VAT ID" (VAT is charged). Flagged.
- The ellipsis in shortened plan names is U+2026 (one character).
- The credit approver threshold compares the rounded credit amount_cents.
- Lines below 50 cents are dropped independently, so a credit can be dropped while the charge is kept.
- seats is validated for presence and type but never used for billing (R7).

Test status: the tests in this module were written but not executed in this environment. Run with: python3 -I thisfile.py

"""

import math
import unittest
from datetime import datetime, timedelta, timezone
from fractions import Fraction

PERIOD = timedelta(days=13)
PERIOD_US = PERIOD // timedelta(microseconds=1)
THAO = "Nguyễn Thị Phương Thảo"
RAMON = "Ramón Etxeberria-Goñi"
MIN_LINE_CENTS = 50
RAMON_THRESHOLD_CENTS = 50000
VAT_PERCENT = 21
MAX_DESC = 80
ELLIPSIS = "\u2026"


def _int_field(value, name):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _text(value, name):
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value


def _aware(value, name):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value


def _describe(prefix, plan, date_str):
    head = prefix + " "
    tail = f" seats until {date_str}"
    room = MAX_DESC - len(head) - len(tail)
    if len(plan) > room:
        plan = plan[: max(room - 1, 0)] + ELLIPSIS
    return head + plan + tail


def prorate_seats(subscription, new_plan, changed_at):
    for key in ("id", "status", "plan_name", "seat_price_cents", "seats",
                "billable_seats", "vat_id", "period_end"):
        if key not in subscription:
            raise ValueError(f"subscription missing key: {key}")
    for key in ("name", "seat_price_cents"):
        if key not in new_plan:
            raise ValueError(f"new_plan missing key: {key}")

    sub_id = _text(subscription["id"], "id")
    status = _text(subscription["status"], "status")
    plan_name = _text(subscription["plan_name"], "plan_name")
    old_price = _int_field(subscription["seat_price_cents"], "seat_price_cents")
    _int_field(subscription["seats"], "seats")
    billable = _int_field(subscription["billable_seats"], "billable_seats")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise ValueError("vat_id must be a string or None")
    period_end = _aware(subscription["period_end"], "period_end")
    new_name = _text(new_plan["name"], "new_plan name")
    new_price = _int_field(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    changed_at = _aware(changed_at, "changed_at")

    if status != "active":
        return []
    if changed_at >= period_end:
        return []
    if changed_at < period_end - PERIOD:
        raise ValueError("changed_at is more than 13 days before period_end")
    if new_price <= old_price:
        return []

    unused_us = (period_end - changed_at) // timedelta(microseconds=1)
    fraction = Fraction(unused_us, PERIOD_US)
    credit_cents = math.ceil(Fraction(old_price * billable) * fraction)
    charge_cents = math.floor(Fraction(new_price * billable) * fraction)

    date_str = period_end.date().isoformat()
    lines = []
    if credit_cents >= MIN_LINE_CENTS:
        approver = RAMON if credit_cents > RAMON_THRESHOLD_CENTS else THAO
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe("Unused", plan_name, date_str),
            "approved_by": approver,
        })
    if charge_cents >= MIN_LINE_CENTS:
        has_vat_id = vat_id is not None and vat_id.strip() != ""
        vat = 0 if has_vat_id else (charge_cents * VAT_PERCENT) // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat,
            "description": _describe("Prorated", new_name, date_str),
            "approved_by": None,
        })
    return lines


UTC = timezone.utc
END = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
HALF = END - timedelta(days=6, hours=12)   # unused 6.5 of 13 days = 1/2
THIRD = END - timedelta(days=4, hours=8)   # unused 13/3 days = 1/3


def _sub(**over):
    base = {"id": "sub_1", "status": "active", "plan_name": "Studio",
            "seat_price_cents": 1000, "seats": 10, "billable_seats": 10,
            "vat_id": None, "period_end": END}
    base.update(over)
    return base


def _plan(price, name="Studio Plus"):
    return {"name": name, "seat_price_cents": price}


class ProrateTests(unittest.TestCase):
    def test_normal_upgrade_credit_and_charge(self):
        lines = prorate_seats(_sub(), _plan(1500), HALF)
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        self.assertEqual(lines[0]["amount_cents"], 5000)
        self.assertEqual(lines[0]["vat_cents"], 0)
        self.assertEqual(lines[1]["amount_cents"], 7500)
        self.assertEqual(lines[1]["vat_cents"], 1575)
        self.assertIsNone(lines[1]["approved_by"])

    def test_rounding_credit_up_charge_down(self):
        lines = prorate_seats(_sub(seat_price_cents=100, billable_seats=2),
                              _plan(200), THIRD)
        self.assertEqual(lines[0]["amount_cents"], 67)   # 66.67 -> 67
        self.assertEqual(lines[1]["amount_cents"], 133)  # 133.33 -> 133
        self.assertEqual(lines[1]["vat_cents"], 27)      # floor(133*21/100)

    def test_exactly_50_kept_and_under_50_skipped(self):
        lines = prorate_seats(_sub(seat_price_cents=100, billable_seats=1),
                              _plan(150), THIRD)
        self.assertEqual([l["kind"] for l in lines], ["charge"])
        self.assertEqual(lines[0]["amount_cents"], 50)
        self.assertEqual(lines[0]["vat_cents"], 10)

    def test_under_50_both_lines_dropped(self):
        self.assertEqual(
            prorate_seats(_sub(seat_price_cents=100, billable_seats=1),
                          _plan(147), THIRD), [])

    def test_reverse_charge_and_empty_vat_id(self):
        lines = prorate_seats(_sub(vat_id="GB123456789",
                                   seat_price_cents=100, billable_seats=2),
                              _plan(200), THIRD)
        self.assertEqual(lines[1]["vat_cents"], 0)
        for vid in ("", None):
            lines = prorate_seats(_sub(vat_id=vid, seat_price_cents=100,
                                       billable_seats=2), _plan(200), THIRD)
            self.assertEqual(lines[1]["vat_cents"], 27)

    def test_trialing_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(1500), HALF), [])

    def test_non_active_status_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(status="canceled"), _plan(1500), HALF), [])

    def test_downgrade_and_equal_return_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(500), HALF), [])
        self.assertEqual(prorate_seats(_sub(), _plan(1000), HALF), [])

    def test_description_truncates_plan_keeps_date(self):
        lines = prorate_seats(_sub(plan_name="A" * 100), _plan(1500), HALF)
        desc = lines[0]["description"]
        self.assertEqual(len(desc), 80)
        self.assertTrue(desc.endswith("seats until 2026-10-20"))
        self.assertIn(ELLIPSIS, desc)
        self.assertTrue(desc.startswith("Unused "))

    def test_approver_boundary_at_500_euro(self):
        at = prorate_seats(_sub(seat_price_cents=100000), _plan(100001, "P"), HALF)
        self.assertEqual(at[0]["amount_cents"], 50000)
        self.assertEqual(at[0]["approved_by"], THAO)
        over = prorate_seats(_sub(seat_price_cents=100001), _plan(100002, "P"), HALF)
        self.assertEqual(over[0]["amount_cents"], 50001)
        self.assertEqual(over[0]["approved_by"], RAMON)

    def test_billable_seats_used_not_seats(self):
        a = prorate_seats(_sub(seats=99, billable_seats=10), _plan(1500), HALF)
        b = prorate_seats(_sub(seats=10, billable_seats=10), _plan(1500), HALF)
        self.assertEqual(a, b)
        self.assertEqual(a[0]["amount_cents"], 5000)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(1500), HALF.replace(tzinfo=None))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(1500), END - timedelta(days=14))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(seat_price_cents=1000.0), _plan(1500), HALF)
        bad = _sub()
        del bad["vat_id"]
        with self.assertRaises(ValueError):
            prorate_seats(bad, _plan(1500), HALF)


if __name__ == "__main__":
    unittest.main()