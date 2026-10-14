"""Seat upgrade proration for Fernhollow Studios.

Public entry point: prorate_seats(subscription, new_plan, changed_at).

Design choices and defaults:
- Early exits return []: status "trialing", downgrade (new price < old price),
  same price (default: no lines), changed_at at or after period_end (default: no lines).
- Inputs are validated first. Naive datetimes and negative or non-integer seat counts
  or prices raise ValueError. legacy_discount is ignored.
- Unused fraction = (period_end - changed_at) / 30 days, computed exactly from
  microseconds as a Fraction. Whole days are not used.
- Credit = old price * billable_seats * unused, rounded up (exact ceiling).
  Charge = new price * billable_seats * unused, rounded down (exact floor).
- Lines with a net amount_cents under 50 are dropped. The 50-cent check applies to
  the net amount for both kinds.
- Credit lines carry vat_cents 0. Charge VAT = floor(net * 21 / 100). A non-empty
  vat_id (treated as truthy; None and "" are absent) gives reverse charge and VAT 0.
- Descriptions use the fixed templates CREDIT_TEMPLATE and CHARGE_TEMPLATE. The
  period end is YYYY-MM-DD. If the description exceeds 80 code points, only the plan
  name is shortened, with a trailing ellipsis.
- Approver: credits above 50000 cents go to LARGE_CREDIT_APPROVER, otherwise to
  DEFAULT_APPROVER. Charges have approved_by None.

The unit tests are in this module. Run them with: python3 <this file>.
The tests were written but not executed in the authoring environment.
"""

import unittest
from datetime import datetime, timedelta, timezone
from fractions import Fraction

VAT_RATE_PERCENT = 21
MIN_LINE_CENTS = 50
APPROVAL_THRESHOLD_CENTS = 50000
DEFAULT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
MAX_DESCRIPTION_LENGTH = 80
ELLIPSIS = "…"
CREDIT_TEMPLATE = "Credit for unused {plan} seats, period ending {date}"
CHARGE_TEMPLATE = "Prorated {plan} seats, period ending {date}"

_BILLING_PERIOD_MICROS = 30 * 24 * 3600 * 10**6


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription["period_end"]
    _require_aware(changed_at, "changed_at")
    _require_aware(period_end, "period_end")
    old_price = _non_negative_int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _non_negative_int(new_plan["seat_price_cents"], "new seat_price_cents")
    _non_negative_int(subscription["seats"], "seats")
    billable = _non_negative_int(subscription["billable_seats"], "billable_seats")

    if subscription["status"] == "trialing":
        return []
    # Downgrades apply at renewal; equal prices produce no lines by default.
    if new_price <= old_price:
        return []
    # Changes at or after period end produce no lines by default.
    if changed_at >= period_end:
        return []

    unused = Fraction(_micros(period_end - changed_at), _BILLING_PERIOD_MICROS)
    credit_amount = _ceil(Fraction(old_price * billable) * unused)
    charge_amount = _floor(Fraction(new_price * billable) * unused)

    sub_id = subscription["id"]
    end_date = period_end.date().isoformat()
    lines = []

    if credit_amount >= MIN_LINE_CENTS:
        approver = (
            LARGE_CREDIT_APPROVER
            if credit_amount > APPROVAL_THRESHOLD_CENTS
            else DEFAULT_APPROVER
        )
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_amount,
            "vat_cents": 0,
            "description": _describe(CREDIT_TEMPLATE, subscription["plan_name"], end_date),
            "approved_by": approver,
        })

    if charge_amount >= MIN_LINE_CENTS:
        reverse_charge = bool(subscription["vat_id"])
        vat = 0 if reverse_charge else charge_amount * VAT_RATE_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_amount,
            "vat_cents": vat,
            "description": _describe(CHARGE_TEMPLATE, new_plan["name"], end_date),
            "approved_by": None,
        })

    return lines


def _describe(template, plan_name, end_date):
    full = template.format(plan=plan_name, date=end_date)
    if len(full) <= MAX_DESCRIPTION_LENGTH:
        return full
    fixed_len = len(template.format(plan="", date=end_date))
    room = MAX_DESCRIPTION_LENGTH - fixed_len
    if room < 2:
        raise ValueError("description template leaves no room for the plan name")
    short = plan_name[: room - 1] + ELLIPSIS
    return template.format(plan=short, date=end_date)


def _require_aware(value, name):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _non_negative_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _micros(delta):
    return (delta.days * 86400 + delta.seconds) * 10**6 + delta.microseconds


def _floor(q):
    return q.numerator // q.denominator


def _ceil(q):
    return -((-q.numerator) // q.denominator)


PE = datetime(2026, 11, 1, tzinfo=timezone.utc)


def _sub(**overrides):
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Studio",
        "seat_price_cents": 1000,
        "seats": 10,
        "billable_seats": 10,
        "vat_id": None,
        "period_end": PE,
        "legacy_discount": 99,
    }
    base.update(overrides)
    return base


def _plan(price, name="Studio Pro"):
    return {"name": name, "seat_price_cents": price}


class ProrateSeatsTests(unittest.TestCase):

    def test_normal_upgrade(self):
        lines = prorate_seats(_sub(), _plan(2000), PE - timedelta(days=15))
        self.assertEqual(len(lines), 2)
        credit, charge = lines
        self.assertEqual(credit["kind"], "credit")
        self.assertEqual(credit["amount_cents"], 5000)
        self.assertEqual(credit["vat_cents"], 0)
        self.assertEqual(credit["approved_by"], DEFAULT_APPROVER)
        self.assertIn("2026-11-01", credit["description"])
        self.assertEqual(charge["kind"], "charge")
        self.assertEqual(charge["subscription_id"], "sub_1")
        self.assertEqual(charge["amount_cents"], 10000)
        self.assertEqual(charge["vat_cents"], 2100)
        self.assertIsNone(charge["approved_by"])
        self.assertIn("Studio Pro", charge["description"])

    def test_trialing_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(2000), PE - timedelta(days=15)), [])

    def test_downgrade_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(500), PE - timedelta(days=15)), [])

    def test_same_price_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(1000), PE - timedelta(days=15)), [])

    def test_change_at_or_after_period_end_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(2000), PE), [])
        self.assertEqual(prorate_seats(_sub(), _plan(2000), PE + timedelta(days=1)), [])

    def test_credit_rounds_up_and_charge_rounds_down(self):
        sub = _sub(seat_price_cents=1000, seats=1, billable_seats=1)
        lines = prorate_seats(sub, _plan(1001), PE - timedelta(days=10))
        credit, charge = lines
        self.assertEqual(credit["amount_cents"], 334)
        self.assertEqual(charge["amount_cents"], 333)
        self.assertEqual(charge["vat_cents"], 69)

    def test_sub_50_cent_lines_dropped(self):
        sub = _sub(seat_price_cents=100, billable_seats=1)
        lines = prorate_seats(sub, _plan(5000), PE - timedelta(days=1))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 166)
        self.assertEqual(lines[0]["vat_cents"], 34)

    def test_all_lines_dropped_returns_empty(self):
        sub = _sub(seat_price_cents=100, billable_seats=1)
        self.assertEqual(prorate_seats(sub, _plan(200), PE - timedelta(days=1)), [])

    def test_bills_on_billable_seats_not_seats(self):
        sub = _sub(seats=10, billable_seats=3)
        credit, charge = prorate_seats(sub, _plan(2000), PE - timedelta(days=15))
        self.assertEqual(credit["amount_cents"], 1500)
        self.assertEqual(charge["amount_cents"], 3000)

    def test_reverse_charge_gives_zero_vat(self):
        lines = prorate_seats(_sub(vat_id="DE123456789"), _plan(2000), PE - timedelta(days=15))
        self.assertEqual(lines[1]["vat_cents"], 0)

    def test_empty_vat_id_is_treated_as_absent(self):
        lines = prorate_seats(_sub(vat_id=""), _plan(2000), PE - timedelta(days=15))
        self.assertEqual(lines[1]["vat_cents"], 2100)

    def test_long_description_shortens_plan_name_only(self):
        sub = _sub(plan_name="A" * 100)
        lines = prorate_seats(sub, _plan(2000, name="B" * 100), PE - timedelta(days=15))
        credit, charge = lines
        for line in lines:
            self.assertLessEqual(len(line["description"]), MAX_DESCRIPTION_LENGTH)
            self.assertIn("2026-11-01", line["description"])
            self.assertIn(ELLIPSIS, line["description"])
        self.assertTrue(credit["description"].startswith("Credit for unused A"))
        self.assertTrue(charge["description"].startswith("Prorated B"))

    def test_non_ascii_plan_name_counted_in_code_points(self):
        sub = _sub(plan_name="ễ" * 100)
        credit, _ = prorate_seats(sub, _plan(2000), PE - timedelta(days=15))
        self.assertLessEqual(len(credit["description"]), MAX_DESCRIPTION_LENGTH)
        self.assertIn("2026-11-01", credit["description"])

    def test_approver_threshold_at_50000_is_default(self):
        sub = _sub(seat_price_cents=50000, seats=1, billable_seats=1)
        credit, _ = prorate_seats(sub, _plan(50001), PE - timedelta(days=30))
        self.assertEqual(credit["amount_cents"], 50000)
        self.assertEqual(credit["approved_by"], DEFAULT_APPROVER)

    def test_approver_threshold_at_50001_is_large_credit_approver(self):
        sub = _sub(seat_price_cents=50001, seats=1, billable_seats=1)
        credit, _ = prorate_seats(sub, _plan(50002), PE - timedelta(days=30))
        self.assertEqual(credit["amount_cents"], 50001)
        self.assertEqual(credit["approved_by"], LARGE_CREDIT_APPROVER)

    def test_naive_changed_at_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(2000), datetime(2026, 10, 1))

    def test_naive_period_end_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(period_end=datetime(2026, 11, 1)), _plan(2000), PE - timedelta(days=15))

    def test_negative_seats_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(seats=-1), _plan(2000), PE - timedelta(days=15))


if __name__ == "__main__":
    unittest.main()