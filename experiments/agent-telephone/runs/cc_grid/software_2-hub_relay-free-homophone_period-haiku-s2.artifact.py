# seat_proration.py
"""Seat proration for Fernhollow Studios billing.

Assumptions where the spec was silent or ambiguous:
- Unused time is exact elapsed time (microseconds), not whole days.
- All amounts are EUR; there is no currency field.
- amount_cents is net of VAT; charge VAT is 21% rounded half up to the cent.
- Description templates are provisional.
- Validation order: aware-datetime check, negative seats, period-start check, then the early-return rules (trialing, zero seats, downgrade, after period end).
- Datetime arithmetic is done in UTC so DST or mixed offsets do not change the 13-day length.
- The description date is taken from period_end in its own timezone.
- Other statuses prorate normally.
"""

import math
from datetime import datetime, timedelta, timezone
from fractions import Fraction

__all__ = ["prorate_seats"]

PERIOD = timedelta(days=13)
_ONE_US = timedelta(microseconds=1)
_PERIOD_US = PERIOD // _ONE_US
_UTC = timezone.utc
_MIN_LINE_CENTS = 50
_APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
_APPROVER_LARGE = "Ramón Etxeberria-Goñi"
_LARGE_CREDIT_CENTS = 50000
_VAT_RATE = Fraction(21, 100)
_DESC_MAX = 80
_ELLIPSIS = "…"


def _require_aware(value, label):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")


def _has_vat_id(vat_id):
    return isinstance(vat_id, str) and vat_id.strip() != ""


def _vat_half_up(amount_cents):
    return math.floor(_VAT_RATE * amount_cents + Fraction(1, 2))


def _describe(prefix, name, suffix):
    name = str(name)
    avail = _DESC_MAX - len(prefix) - len(suffix)
    if avail <= 0:
        raise ValueError("description exceeds 80 characters")
    if len(name) > avail:
        name = name[:avail - 1] + _ELLIPSIS
    return prefix + name + suffix


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription["period_end"]
    _require_aware(period_end, "period_end")
    _require_aware(changed_at, "changed_at")

    billable = subscription["billable_seats"]
    if billable < 0:
        raise ValueError("billable_seats must not be negative")

    end_utc = period_end.astimezone(_UTC)
    changed_utc = changed_at.astimezone(_UTC)
    if changed_utc < end_utc - PERIOD:
        raise ValueError("changed_at is before the period start")

    if changed_utc >= end_utc:
        return []
    if subscription["status"] == "trialing":
        return []
    if billable == 0:
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:
        return []

    unused_us = (end_utc - changed_utc) // _ONE_US
    unused_fraction = Fraction(unused_us, _PERIOD_US)
    date_str = period_end.date().isoformat()

    lines = []

    credit_cents = math.ceil(Fraction(old_price * billable) * unused_fraction)
    if credit_cents >= _MIN_LINE_CENTS:
        approver = _APPROVER_LARGE if credit_cents > _LARGE_CREDIT_CENTS else _APPROVER_DEFAULT
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe(
                "Unused ", subscription["plan_name"], f" credit, period ends {date_str}"
            ),
            "approved_by": approver,
        })

    charge_cents = math.floor(Fraction(new_price * billable) * unused_fraction)
    if charge_cents >= _MIN_LINE_CENTS:
        vat_cents = 0 if _has_vat_id(subscription["vat_id"]) else _vat_half_up(charge_cents)
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _describe(
                "Proration ", new_plan["name"], f" charge, period ends {date_str}"
            ),
            "approved_by": None,
        })

    return lines


# FILE: test_seat_proration.py
# Not executed: no tool access in this session.

import unittest
from datetime import datetime, timedelta, timezone

from seat_proration import prorate_seats

UTC = timezone.utc
PE = datetime(2026, 3, 14, tzinfo=UTC)
DEFAULT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_APPROVER = "Ramón Etxeberria-Goñi"


def sub(**over):
    # Deliberately has no 'seats' or 'legacy_discount' key.
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Studio",
        "seat_price_cents": 1000,
        "billable_seats": 1,
        "vat_id": None,
        "period_end": PE,
    }
    base.update(over)
    return base


def plan(price, name="Studio Pro"):
    return {"name": name, "seat_price_cents": price}


class ProrationTests(unittest.TestCase):

    def test_credit_rounds_up_and_charge_rounds_down(self):
        changed = PE - timedelta(days=6, hours=12)
        s = sub(seat_price_cents=1001)
        lines = prorate_seats(s, plan(2001), changed)
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        self.assertEqual(lines[0]["amount_cents"], 501)
        self.assertEqual(lines[1]["amount_cents"], 1000)
        self.assertEqual(lines[1]["vat_cents"], 210)
        self.assertEqual(lines[0]["vat_cents"], 0)

    def test_thirteen_day_period_across_february_and_31_day_month(self):
        for pe in (datetime(2027, 3, 1, tzinfo=UTC), datetime(2026, 8, 31, tzinfo=UTC)):
            with self.subTest(period_end=pe):
                lines = prorate_seats(sub(seat_price_cents=1300, period_end=pe),
                                      plan(2600), pe - timedelta(days=1))
                self.assertEqual(lines[0]["amount_cents"], 100)
                self.assertEqual(lines[1]["amount_cents"], 200)

    def test_changed_at_exactly_13_days_before_end_is_allowed(self):
        lines = prorate_seats(sub(seat_price_cents=1300), plan(2600), PE - timedelta(days=13))
        self.assertEqual(lines[0]["amount_cents"], 1300)
        self.assertEqual(lines[1]["amount_cents"], 2600)
        self.assertEqual(lines[1]["vat_cents"], 546)

    def test_fifty_cent_skip_is_asymmetric(self):
        changed = PE - timedelta(days=1)
        lines = prorate_seats(sub(seat_price_cents=600), plan(10000), changed)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 769)
        self.assertEqual(lines[0]["vat_cents"], 161)

    def test_credit_kept_while_charge_dropped(self):
        lines = prorate_seats(sub(seat_price_cents=640), plan(645), PE - timedelta(days=1))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "credit")
        self.assertEqual(lines[0]["amount_cents"], 50)

    def test_both_lines_under_fifty_cents_gives_empty(self):
        self.assertEqual(prorate_seats(sub(seat_price_cents=600), plan(601),
                                       PE - timedelta(days=1)), [])

    def test_charge_vat_half_up(self):
        lines = prorate_seats(sub(seat_price_cents=49), plan(50), PE - timedelta(days=13))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 50)
        self.assertEqual(lines[0]["vat_cents"], 11)

    def test_trialing_returns_empty(self):
        self.assertEqual(prorate_seats(sub(status="trialing"), plan(2000),
                                       PE - timedelta(days=1)), [])

    def test_other_statuses_prorate(self):
        self.assertTrue(prorate_seats(sub(status="active"), plan(2000),
                                      PE - timedelta(days=1)))

    def test_downgrade_and_same_price_return_empty(self):
        changed = PE - timedelta(days=1)
        self.assertEqual(prorate_seats(sub(), plan(1000), changed), [])
        self.assertEqual(prorate_seats(sub(), plan(900), changed), [])

    def test_zero_billable_seats_returns_empty(self):
        self.assertEqual(prorate_seats(sub(billable_seats=0), plan(2000),
                                       PE - timedelta(days=1)), [])

    def test_negative_billable_seats_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(sub(billable_seats=-1), plan(2000), PE - timedelta(days=1))

    def test_reverse_charge_with_vat_id(self):
        lines = prorate_seats(sub(vat_id="DE123456789"), plan(2000), PE - timedelta(days=13))
        charge = [l for l in lines if l["kind"] == "charge"][0]
        self.assertEqual(charge["amount_cents"], 2000)
        self.assertEqual(charge["vat_cents"], 0)

    def test_blank_vat_id_is_not_reverse_charge(self):
        for vat in (None, "", "   "):
            with self.subTest(vat_id=vat):
                lines = prorate_seats(sub(vat_id=vat), plan(2000), PE - timedelta(days=13))
                charge = [l for l in lines if l["kind"] == "charge"][0]
                self.assertEqual(charge["vat_cents"], 420)

    def test_fifty_thousand_cent_threshold_is_strict(self):
        changed = PE - timedelta(days=13)
        at = prorate_seats(sub(seat_price_cents=50000), plan(60000), changed)[0]
        self.assertEqual(at["amount_cents"], 50000)
        self.assertEqual(at["approved_by"], DEFAULT_APPROVER)
        over = prorate_seats(sub(seat_price_cents=50001), plan(60000), changed)[0]
        self.assertEqual(over["amount_cents"], 50001)
        self.assertEqual(over["approved_by"], LARGE_APPROVER)

    def test_credit_approver_is_default_and_charge_has_none(self):
        lines = prorate_seats(sub(), plan(2000), PE - timedelta(days=13))
        self.assertEqual(lines[0]["approved_by"], DEFAULT_APPROVER)
        self.assertIsNone(lines[1]["approved_by"])

    def test_short_description_is_exact(self):
        lines = prorate_seats(sub(), plan(2000), PE - timedelta(days=13))
        self.assertEqual(lines[0]["description"],
                         "Unused Studio credit, period ends 2026-03-14")
        self.assertEqual(lines[1]["description"],
                         "Proration Studio Pro charge, period ends 2026-03-14")

    def test_long_description_truncates_name_and_keeps_date(self):
        pe = datetime(2026, 3, 1, 0, 30, tzinfo=timezone(timedelta(hours=2)))
        s = sub(plan_name="A" * 100, period_end=pe)
        lines = prorate_seats(s, plan(2000, name="B" * 100), pe - timedelta(days=13))
        credit_desc, charge_desc = lines[0]["description"], lines[1]["description"]
        self.assertLessEqual(len(credit_desc), 80)
        self.assertLessEqual(len(charge_desc), 80)
        self.assertIn(_ELLIPSIS, credit_desc)
        self.assertTrue(credit_desc.endswith("period ends 2026-03-01"))
        self.assertTrue(charge_desc.startswith("Proration "))
        self.assertTrue(charge_desc.endswith("charge, period ends 2026-03-01"))

    def test_date_is_local_date_of_period_end(self):
        pe = datetime(2026, 3, 1, 0, 30, tzinfo=timezone(timedelta(hours=2)))
        lines = prorate_seats(sub(period_end=pe), plan(2000), pe - timedelta(days=13))
        self.assertIn("period ends 2026-03-01", lines[0]["description"])

    def test_mixed_timezones_give_same_result(self):
        changed = (PE - timedelta(days=6, hours=12)).astimezone(timezone(timedelta(hours=-5)))
        lines = prorate_seats(sub(seat_price_cents=1001), plan(2001), changed)
        self.assertEqual(lines[0]["amount_cents"], 501)
        self.assertEqual(lines[1]["amount_cents"], 1000)

    def test_output_keys(self):
        lines = prorate_seats(sub(), plan(2000), PE - timedelta(days=13))
        expected = {"subscription_id", "kind", "amount_cents", "vat_cents",
                    "description", "approved_by"}
        for line in lines:
            self.assertEqual(set(line), expected)
            self.assertEqual(line["subscription_id"], "sub_1")

    def test_naive_changed_at_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(sub(), plan(2000), datetime(2026, 3, 10))

    def test_naive_period_end_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(sub(period_end=datetime(2026, 3, 14)), plan(2000),
                          datetime(2026, 3, 10, tzinfo=UTC))

    def test_changed_before_period_start_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(sub(), plan(2000), PE - timedelta(days=14))

    def test_changed_at_or_after_period_end_returns_empty(self):
        self.assertEqual(prorate_seats(sub(), plan(2000), PE), [])
        self.assertEqual(prorate_seats(sub(), plan(2000), PE + timedelta(hours=1)), [])


if __name__ == "__main__":
    unittest.main()