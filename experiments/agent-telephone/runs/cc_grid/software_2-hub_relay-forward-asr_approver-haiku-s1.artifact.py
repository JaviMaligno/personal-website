"""Seat-upgrade proration for Fernhollow Studios.

Open items resolved in this module (each labelled PROPOSED in the code):
- Day count: exact fractional days, computed with Fraction (no whole-day rounding).
- Lines under 50 cents are dropped on the final rounded amount, 50 is kept. CONFLICT: see question 1.
- Charge VAT: 21% of the net amount, rounded down to the cent. Credits carry no VAT, as the brief says.
- Equal-price plans: treated as a no-op, returns [].
- changed_at before period start: days clamped to 30.
- changed_at at or after period_end: returns [].
- billable_seats of 0: returns [].
- Currency assumed EUR (amounts are cents with no currency field).
- Description template: "Credit unused {plan}, period end {YYYY-MM-DD}" or "Charge unused {plan}, period end {YYYY-MM-DD}". A long plan name is cut to 40 characters plus "...". The date is always kept.
- Approval: credits strictly over 50000 cents go to Ramón Etxeberria-Goñi, all other credits to Win Tee Fung Tao.

Open questions for the client:
1. Dropping credits under 50 cents withholds money owed to the customer. That conflicts with "never round in our favour". Implemented as briefed, pending confirmation. Should sub-50-cent credits be kept?
2. Confirm exact fractional-day proration rather than whole days.
3. Confirm that equal-price plans produce no lines.
4. Confirm 21% VAT on the net amount with round-down.
5. Confirm EUR currency.
6. Confirm the approval threshold is strictly over 50000 cents.
"""

import math
import unittest
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from fractions import Fraction

PERIOD = timedelta(days=30)
PERIOD_US = PERIOD // timedelta(microseconds=1)
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
CREDIT_APPROVER = "Win Tee Fung Tao"
BIG_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
BIG_CREDIT_CENTS = 50000
MAX_DESCRIPTION = 80


def _get(mapping, key):
    if not isinstance(mapping, Mapping) or key not in mapping:
        raise ValueError(f"missing field: {key}")
    return mapping[key]


def _cents(value, key):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{key} must be a non-negative integer number of cents")
    return value


def _text(value, key):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _aware(value, key):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{key} must be a timezone-aware datetime")
    return value


def _describe(verb, plan_name, period_end):
    head = f"{verb} unused "
    tail = f", period end {period_end.date().isoformat()}"
    budget = MAX_DESCRIPTION - len(head) - len(tail)
    name = plan_name if len(plan_name) <= budget else plan_name[: budget - 3] + "..."
    return head + name + tail


def prorate_seats(subscription, new_plan, changed_at):
    sub_id = _get(subscription, "id")
    if isinstance(sub_id, bool) or not isinstance(sub_id, (str, int)):
        raise ValueError("id must be a string or integer")
    status = _get(subscription, "status")
    if not isinstance(status, str):
        raise ValueError("status must be a string")
    plan_name = _text(_get(subscription, "plan_name"), "plan_name")
    old_price = _cents(_get(subscription, "seat_price_cents"), "seat_price_cents")
    _cents(_get(subscription, "seats"), "seats")
    billable = _cents(_get(subscription, "billable_seats"), "billable_seats")
    vat_id = _get(subscription, "vat_id")
    if vat_id is not None and not isinstance(vat_id, str):
        raise ValueError("vat_id must be a string or None")
    period_end = _aware(_get(subscription, "period_end"), "period_end")
    new_name = _text(_get(new_plan, "name"), "name")
    new_price = _cents(_get(new_plan, "seat_price_cents"), "seat_price_cents")
    changed_at = _aware(changed_at, "changed_at")

    if status == "trialing":
        return []
    # Downgrade (new < old) applies at renewal; equal price is a no-op (PROPOSED).
    if new_price <= old_price:
        return []
    if billable == 0:
        return []
    if changed_at >= period_end:
        return []

    # Clamp to the 30-day period (PROPOSED for changed_at before period start).
    unused = min(period_end - changed_at, PERIOD)
    # Exact fractional-day proration (PROPOSED day-count method).
    fraction = Fraction(unused // timedelta(microseconds=1), PERIOD_US)

    # Never round in our favour: credits up, charges down.
    credit = math.ceil(Fraction(old_price * billable) * fraction)
    charge = math.floor(Fraction(new_price * billable) * fraction)

    lines = []
    # Lines under 50 cents are dropped on the final amount (PROPOSED; conflicts
    # with "never round in our favour", see question 1 in the module header).
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit", plan_name, period_end),
            "approved_by": BIG_CREDIT_APPROVER if credit > BIG_CREDIT_CENTS else CREDIT_APPROVER,
        })
    if charge >= MIN_LINE_CENTS:
        # PROPOSED: VAT on the net amount, rounded down.
        has_vat_id = vat_id is not None and vat_id.strip() != ""
        vat = 0 if has_vat_id else charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe("Charge", new_name, period_end),
            "approved_by": None,
        })
    return lines


PE = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


def _sub(**over):
    s = dict(id="sub_1", status="active", plan_name="Studio Seat", seat_price_cents=1000,
             seats=10, billable_seats=10, vat_id=None, period_end=PE)
    s.update(over)
    return s


def _plan(price, name="Studio Pro"):
    return {"name": name, "seat_price_cents": price}


def _at(days_left, end=PE):
    return end - timedelta(days=days_left)


class ProrateTests(unittest.TestCase):
    def test_trialing_returns_nothing(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(2000), _at(30)), [])

    def test_downgrade_returns_nothing(self):
        self.assertEqual(prorate_seats(_sub(), _plan(500), _at(30)), [])

    def test_equal_price_returns_nothing(self):
        self.assertEqual(prorate_seats(_sub(), _plan(1000), _at(30)), [])

    def test_full_period_credit_before_charge_with_vat(self):
        lines = prorate_seats(_sub(), _plan(1500), _at(30))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        credit, charge = lines
        self.assertEqual(credit["amount_cents"], 10000)
        self.assertEqual(credit["vat_cents"], 0)
        self.assertEqual(credit["approved_by"], CREDIT_APPROVER)
        self.assertEqual(charge["amount_cents"], 15000)
        self.assertEqual(charge["vat_cents"], 3150)
        self.assertIsNone(charge["approved_by"])

    def test_credit_rounds_up_and_charge_rounds_down(self):
        lines = prorate_seats(_sub(seat_price_cents=1001, billable_seats=1), _plan(1000), _at(20))
        self.assertEqual(lines[0]["amount_cents"], 334)  # 333.67 -> 334
        self.assertEqual(lines[1]["amount_cents"], 333)  # 333.33 -> 333

    def test_fifty_cent_rule_drops_small_credit_keeps_charge(self):
        lines = prorate_seats(_sub(seat_price_cents=10, billable_seats=1), _plan(100000), _at(29))
        self.assertEqual([l["kind"] for l in lines], ["charge"])

    def test_exactly_fifty_cents_is_kept(self):
        lines = prorate_seats(_sub(seat_price_cents=1500, billable_seats=1), _plan(3000), _at(29))
        self.assertEqual(lines[0]["amount_cents"], 50)

    def test_big_credit_routed_to_senior_approver(self):
        lines = prorate_seats(_sub(seat_price_cents=100000, billable_seats=1), _plan(200000), _at(30))
        self.assertEqual(lines[0]["approved_by"], BIG_CREDIT_APPROVER)

    def test_credit_at_threshold_goes_to_controller(self):
        lines = prorate_seats(_sub(seat_price_cents=50000, billable_seats=1), _plan(100000), _at(30))
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], CREDIT_APPROVER)

    def test_vat_absent_for_none_empty_or_whitespace_vat_id(self):
        for vat in (None, "", "   "):
            lines = prorate_seats(_sub(vat_id=vat), _plan(1500), _at(30))
            self.assertEqual(lines[1]["vat_cents"], 3150)

    def test_vat_zero_with_vat_id_and_credit_never_has_vat(self):
        lines = prorate_seats(_sub(vat_id="DE123"), _plan(1500), _at(30))
        self.assertEqual(lines[1]["vat_cents"], 0)
        self.assertEqual(lines[0]["vat_cents"], 0)

    def test_clamp_before_period_start_to_thirty_days(self):
        lines = prorate_seats(_sub(), _plan(1500), _at(400))
        self.assertEqual(lines[0]["amount_cents"], 10000)

    def test_changed_at_on_or_after_period_end_returns_nothing(self):
        self.assertEqual(prorate_seats(_sub(), _plan(1500), PE), [])
        self.assertEqual(prorate_seats(_sub(), _plan(1500), PE + timedelta(days=1)), [])

    def test_zero_billable_seats_returns_nothing(self):
        self.assertEqual(prorate_seats(_sub(billable_seats=0), _plan(1500), _at(30)), [])

    def test_description_fits_and_keeps_date_for_long_plan_name(self):
        lines = prorate_seats(_sub(plan_name="A" * 200), _plan(1500, "B" * 200), _at(30))
        for line in lines:
            self.assertLessEqual(len(line["description"]), MAX_DESCRIPTION)
            self.assertIn("2026-11-01", line["description"])

    def test_date_uses_period_end_own_timezone(self):
        pe = datetime(2026, 11, 1, 0, 30, tzinfo=timezone(timedelta(hours=2)))
        lines = prorate_seats(_sub(period_end=pe), _plan(1500), pe - timedelta(days=30))
        self.assertIn("2026-11-01", lines[0]["description"])

    def test_invalid_fields_raise(self):
        bad = _sub()
        del bad["period_end"]
        with self.assertRaises(ValueError):
            prorate_seats(bad, _plan(1500), _at(30))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(seat_price_cents="1000"), _plan(1500), _at(30))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(1500), datetime(2026, 10, 20))


if __name__ == "__main__":
    unittest.main()