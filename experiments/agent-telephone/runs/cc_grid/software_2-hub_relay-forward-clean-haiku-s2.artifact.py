"""Seat upgrade proration for Fernhollow Studios.

Working decisions where the client has not answered (all amounts in EUR cents):
- Amounts are integer cents. All arithmetic uses fractions.Fraction, never floats.
- D is the exact elapsed time from changed_at to period_end, in days, not rounded. The unused fraction is D / 30.
- Return [] when D <= 0, status is "trialing", the new price is lower (downgrade), or the price is equal.
- Credit = ceil(old_price * billable_seats * D / 30). No VAT. Approver is Ramón Etxeberria-Goñi when the credit exceeds 50000 cents, otherwise Nguyễn Thị Phương Thảo.
- Charge = floor(new_price * billable_seats * D / 30). Approver is None. VAT is 21% floored, or 0 when vat_id is truthy (reverse charge).
- Lines under 50 cents are dropped. The charge threshold is tested on the net amount, before VAT.
- Credits carry no VAT. The client brief overrides the house rule that VAT applies to every line.
- Credit line comes first, then charge line.
- Only billable_seats is used. seats and legacy_discount are ignored.
- Descriptions are capped at 80 code points. The plan name is truncated with an ellipsis so the YYYY-MM-DD period end date is always kept.
- Status values other than "trialing" are treated as normal.

Open questions for the client (not blocking):
- Day-count convention: elapsed time is used, not calendar months.
- The 50-cent test is on the net amount (chosen). Confirm.
- VAT rounding is floor (chosen). Confirm.
- Currency is assumed EUR.
- Confirm other status values and whether approver assertion is wanted as specified.

Tests were not executed in the authoring session because no tools were available. The unittest suite at the bottom of this module covers the acceptance examples.
"""

import math
import unittest
from datetime import datetime, timedelta, timezone
from fractions import Fraction

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
LARGE_CREDIT_CENTS = 50000
APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
APPROVER_LARGE = "Ramón Etxeberria-Goñi"
MAX_DESCRIPTION = 80
ELLIPSIS = "…"
_MICROS_PER_DAY = 86_400_000_000


def _require_aware(dt, name):
    if not isinstance(dt, datetime):
        raise TypeError(f"{name} must be a datetime")
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _require_int(value, name):
    if type(value) is not int:
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    return value


def _require_str(value, name):
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a str")
    return value


def _elapsed_days(changed_at, period_end):
    micros = (period_end - changed_at) // timedelta(microseconds=1)
    return Fraction(micros, _MICROS_PER_DAY)


def _description(plan_name, period_end):
    head = "Unused "
    tail = f" seats until {period_end.date().isoformat()}"
    budget = MAX_DESCRIPTION - len(head) - len(tail)
    if budget <= 0:
        raise ValueError("no room for plan name in description")
    if len(plan_name) > budget:
        plan_name = plan_name[: budget - 1] + ELLIPSIS
    return head + plan_name + tail


def prorate_seats(subscription, new_plan, changed_at):
    sub_id = subscription["id"]
    status = subscription["status"]
    old_name = _require_str(subscription["plan_name"], "plan_name")
    old_price = _require_int(subscription["seat_price_cents"], "seat_price_cents")
    billable = _require_int(subscription["billable_seats"], "billable_seats")
    period_end = subscription["period_end"]
    vat_id = subscription.get("vat_id")

    new_name = _require_str(new_plan["name"], "new plan name")
    new_price = _require_int(new_plan["seat_price_cents"], "new seat_price_cents")

    _require_aware(changed_at, "changed_at")
    _require_aware(period_end, "period_end")

    if billable < 0:
        raise ValueError("billable_seats must not be negative")
    if old_price < 0 or new_price < 0:
        raise ValueError("seat prices must not be negative")

    if status == "trialing":
        return []

    days = _elapsed_days(changed_at, period_end)
    if days <= 0:
        return []

    if new_price <= old_price:
        return []

    unused = days / PERIOD_DAYS
    lines = []

    credit_cents = math.ceil(old_price * billable * unused)
    if credit_cents >= MIN_LINE_CENTS:
        approver = APPROVER_LARGE if credit_cents > LARGE_CREDIT_CENTS else APPROVER_DEFAULT
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _description(old_name, period_end),
            "approved_by": approver,
        })

    charge_cents = math.floor(new_price * billable * unused)
    if charge_cents >= MIN_LINE_CENTS:
        vat_cents = 0 if vat_id else charge_cents * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _description(new_name, period_end),
            "approved_by": None,
        })

    return lines


# ---------------------------------------------------------------- tests

CHANGE = datetime(2026, 11, 15, tzinfo=timezone.utc)
PERIOD_END = datetime(2026, 11, 30, tzinfo=timezone.utc)


def _sub(**overrides):
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Basic",
        "seat_price_cents": 5000,
        "seats": 9,
        "billable_seats": 2,
        "vat_id": None,
        "period_end": PERIOD_END,
    }
    base.update(overrides)
    return base


def _plan(price=7500, name="Pro"):
    return {"name": name, "seat_price_cents": price}


class ProrateSeatsTests(unittest.TestCase):

    def test_basic_upgrade_with_vat(self):
        lines = prorate_seats(_sub(), _plan(7500), CHANGE)
        self.assertEqual(len(lines), 2)
        credit, charge = lines
        self.assertEqual(credit["kind"], "credit")
        self.assertEqual(credit["amount_cents"], 5000)
        self.assertEqual(credit["vat_cents"], 0)
        self.assertEqual(credit["approved_by"], APPROVER_DEFAULT)
        self.assertEqual(credit["description"], "Unused Basic seats until 2026-11-30")
        self.assertEqual(charge["kind"], "charge")
        self.assertEqual(charge["amount_cents"], 7500)
        self.assertEqual(charge["vat_cents"], 1575)
        self.assertIsNone(charge["approved_by"])
        self.assertEqual(charge["description"], "Unused Pro seats until 2026-11-30")
        self.assertEqual(credit["subscription_id"], "sub_1")

    def test_rounding_credit_up_charge_down(self):
        sub = _sub(seat_price_cents=1000, billable_seats=1, vat_id="ES123",
                   period_end=CHANGE + timedelta(days=10))
        credit, charge = prorate_seats(sub, _plan(1001), CHANGE)
        self.assertEqual(credit["amount_cents"], 334)
        self.assertEqual(charge["amount_cents"], 333)
        self.assertEqual(charge["vat_cents"], 0)

    def test_both_lines_under_minimum_gives_empty(self):
        sub = _sub(seat_price_cents=10, billable_seats=1)
        self.assertEqual(prorate_seats(sub, _plan(11), CHANGE), [])

    def test_approval_boundary_at_50000_uses_default(self):
        sub = _sub(seat_price_cents=50000, billable_seats=1, vat_id="X",
                   period_end=CHANGE + timedelta(days=30))
        credit, _ = prorate_seats(sub, _plan(60000), CHANGE)
        self.assertEqual(credit["amount_cents"], 50000)
        self.assertEqual(credit["approved_by"], APPROVER_DEFAULT)

    def test_approval_boundary_above_50000_uses_large(self):
        sub = _sub(seat_price_cents=50001, billable_seats=1, vat_id="X",
                   period_end=CHANGE + timedelta(days=30))
        credit, _ = prorate_seats(sub, _plan(60000), CHANGE)
        self.assertEqual(credit["amount_cents"], 50001)
        self.assertEqual(credit["approved_by"], APPROVER_LARGE)

    def test_downgrade_gives_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(4000), CHANGE), [])

    def test_equal_price_gives_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(5000), CHANGE), [])

    def test_trialing_gives_empty(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(7500), CHANGE), [])

    def test_no_time_left_gives_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(7500), PERIOD_END), [])

    def test_long_plan_name_is_truncated_and_keeps_date(self):
        sub = _sub(plan_name="A" * 100)
        credit, _ = prorate_seats(sub, _plan(7500), CHANGE)
        desc = credit["description"]
        self.assertLessEqual(len(desc), MAX_DESCRIPTION)
        self.assertEqual(len(desc), MAX_DESCRIPTION)
        self.assertIn(ELLIPSIS, desc)
        self.assertTrue(desc.endswith("seats until 2026-11-30"))

    def test_date_uses_period_end_own_timezone(self):
        tz = timezone(timedelta(hours=1))
        sub = _sub(period_end=datetime(2026, 12, 1, 0, 30, tzinfo=tz))
        credit, _ = prorate_seats(sub, _plan(7500), CHANGE)
        self.assertTrue(credit["description"].endswith("until 2026-12-01"))

    def test_naive_period_end_raises(self):
        sub = _sub(period_end=datetime(2026, 11, 30))
        with self.assertRaises(ValueError):
            prorate_seats(sub, _plan(7500), CHANGE)

    def test_naive_changed_at_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(7500), datetime(2026, 11, 15))

    def test_non_int_price_raises(self):
        with self.assertRaises(TypeError):
            prorate_seats(_sub(seat_price_cents=50.0), _plan(7500), CHANGE)

    def test_negative_billable_seats_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(billable_seats=-1), _plan(7500), CHANGE)


if __name__ == "__main__":
    unittest.main()