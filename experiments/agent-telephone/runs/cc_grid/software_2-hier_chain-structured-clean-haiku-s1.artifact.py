"""Seat-upgrade proration for Fernhollow Studios (client contact: Ingrid).

Entry point: prorate_seats(subscription, new_plan, changed_at).

PROVISIONAL items, all flagged in the code below and needing client confirmation:
  R18  APPROVAL_THRESHOLD_CENTS = 50000 is assumed to be EUR cents.
  R19  MIN_LINE_CENTS (50) is applied to the pre-VAT amount.
  R20  The approval threshold compares amount_cents (credits carry no VAT).
  R21  Charge VAT rounds down (VAT_ROUND_UP = False).
  R22  changed_at at or after period_end returns [].
  R23  An unchanged price returns [].
  R24  Description wording is in CREDIT_TEMPLATE and CHARGE_TEMPLATE.
  N1   Unused time is the exact elapsed time at microsecond resolution, with no whole-day truncation.
  N2   Only "trialing" blocks proration. Other statuses are prorated.
  N3   vat_id counts as set when it is not None and str(vat_id).strip() is non-empty.
  N4   period_end is formatted in its own timezone, with no conversion.
  N5   The 80-character limit counts code points. The plan name is truncated with "...", and the date is never cut.
  N6   billable_seats and prices must be int >= 0, otherwise ValueError (non-int raises TypeError).

Guard, not a spec rule: if the remaining time exceeds one 30-day period (R6), ValueError is raised rather than crediting more than a full period.
"""

from datetime import datetime, timedelta

PERIOD_DAYS = 30                                    # R6: a billing period always counts as 30 days
PERIOD_MICROSECONDS = PERIOD_DAYS * 86400 * 10**6   # N1 (provisional): exact elapsed time, microsecond resolution
MIN_LINE_CENTS = 50                                 # R9/R19 PROVISIONAL: compared against the pre-VAT amount
APPROVAL_THRESHOLD_CENTS = 50000                    # R18 PROVISIONAL: assumed EUR cents, needs client confirmation
VAT_PERCENT = 21                                    # R10
VAT_ROUND_UP = False                                # R21 PROVISIONAL: charge VAT rounds down (floor)
MAX_DESCRIPTION_LEN = 80                            # R12 / N5 PROVISIONAL: counted in code points
TRIALING = "trialing"                               # R11
FINANCE_APPROVER = "Nguyễn Thị Phương Thảo"         # R13
HIGH_VALUE_APPROVER = "Ramón Etxeberria-Goñi"       # R13
CREDIT_TEMPLATE = "Credit for unused {plan} seats, period ends {date}"  # R24 PROVISIONAL
CHARGE_TEMPLATE = "Charge for {plan} seats, period ends {date}"         # R24 PROVISIONAL


def _check_int(value, name):
    # R15 and N6: integer cents and seats only, non-negative.
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must be >= 0")
    return value


def _check_aware(value, name):
    # R2: all datetimes must be timezone-aware.
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _ceil_div(numerator, denominator):
    return -(-numerator // denominator)


def _amount(price, seats, remaining_us, round_up):
    # R5, R6, R8: exact integer arithmetic.
    numerator = price * seats * remaining_us
    if round_up:
        return _ceil_div(numerator, PERIOD_MICROSECONDS)  # credits round up
    return numerator // PERIOD_MICROSECONDS               # charges round down


def _vat(amount):
    # R10, R21 PROVISIONAL: 21% on charges, rounding controlled by VAT_ROUND_UP.
    raw = amount * VAT_PERCENT
    if VAT_ROUND_UP:
        return _ceil_div(raw, 100)
    return raw // 100


def _describe(template, plan, date_str):
    # R12 and N5: keep the full date. Truncate the plan name with "..." inside the budget.
    base = len(template.format(plan="", date=date_str))
    budget = MAX_DESCRIPTION_LEN - base
    if budget < 0:
        raise ValueError("description text plus date exceeds 80 characters")
    if len(plan) <= budget:
        name = plan
    elif budget >= 3:
        name = plan[: budget - 3] + "..."
    else:
        name = ""  # the plan name is dropped entirely; the date stays
    text = template.format(plan=name, date=date_str)
    return text if name else text.replace("  ", " ")


def prorate_seats(subscription, new_plan, changed_at):
    # Validate everything first (R2, R15, N6).
    sub_id = subscription["id"]
    status = subscription["status"]
    old_price = _check_int(subscription["seat_price_cents"], "seat_price_cents")
    billable = _check_int(subscription["billable_seats"], "billable_seats")  # R4: never read `seats`
    period_end = _check_aware(subscription["period_end"], "period_end")
    old_name = subscription["plan_name"]
    vat_id = subscription["vat_id"]
    # R16: legacy_discount is intentionally not read.
    new_price = _check_int(new_plan["seat_price_cents"], "new seat_price_cents")
    new_name = new_plan["name"]
    _check_aware(changed_at, "changed_at")

    if status == TRIALING:  # R11, N2
        return []
    if changed_at >= period_end:  # R22 PROVISIONAL
        return []
    if new_price <= old_price:  # R7 downgrade (defers to renewal), R23 PROVISIONAL for equal price
        return []

    remaining_us = (period_end - changed_at) // timedelta(microseconds=1)  # N1
    if remaining_us > PERIOD_MICROSECONDS:  # guard, see module docstring
        raise ValueError("remaining time exceeds one 30-day period")

    vat_exempt = vat_id is not None and str(vat_id).strip() != ""  # N3 PROVISIONAL
    date_str = period_end.strftime("%Y-%m-%d")  # N4 PROVISIONAL

    lines = []

    # Credit comes first (R14). It has no VAT (R10) and rounds up (R8).
    credit = _amount(old_price, billable, remaining_us, round_up=True)
    if credit >= MIN_LINE_CENTS:  # R9/R19 PROVISIONAL
        # R13, R20 PROVISIONAL: compare amount_cents (no VAT on credits).
        approver = HIGH_VALUE_APPROVER if credit > APPROVAL_THRESHOLD_CENTS else FINANCE_APPROVER
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe(CREDIT_TEMPLATE, old_name, date_str),
            "approved_by": approver,
        })

    # Charge second (R14). It rounds down (R8) and carries VAT (R10).
    charge = _amount(new_price, billable, remaining_us, round_up=False)
    if charge >= MIN_LINE_CENTS:  # R9/R19 PROVISIONAL
        vat = 0 if vat_exempt else _vat(charge)
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe(CHARGE_TEMPLATE, new_name, date_str),
            "approved_by": None,
        })

    return lines


# ===== test_proration.py (separate file, standard library unittest) =====

import unittest
from datetime import datetime, timedelta, timezone

from proration import prorate_seats, _describe, CREDIT_TEMPLATE, FINANCE_APPROVER, HIGH_VALUE_APPROVER

UTC = timezone.utc
PE = datetime(2026, 11, 30, 12, 0, tzinfo=UTC)


def sub(**over):
    d = dict(
        id="sub_1", status="active", plan_name="Studio Basic", seat_price_cents=1000,
        seats=5, billable_seats=3, vat_id=None, period_end=PE, legacy_discount=0.25,
    )
    d.update(over)
    return d


def plan(price, name="Studio Pro"):
    return {"name": name, "seat_price_cents": price}


class ProrationTests(unittest.TestCase):

    def test_worked_example(self):
        lines = prorate_seats(sub(), plan(2000), PE - timedelta(days=15))
        self.assertEqual(len(lines), 2)
        credit, charge = lines
        self.assertEqual(credit["kind"], "credit")
        self.assertEqual(credit["amount_cents"], 1500)
        self.assertEqual(credit["vat_cents"], 0)
        self.assertEqual(credit["approved_by"], FINANCE_APPROVER)
        self.assertEqual(charge["kind"], "charge")
        self.assertEqual(charge["amount_cents"], 3000)
        self.assertEqual(charge["vat_cents"], 630)
        self.assertIsNone(charge["approved_by"])

    def test_trialing_returns_empty(self):
        self.assertEqual(prorate_seats(sub(status="trialing"), plan(2000), PE - timedelta(days=15)), [])

    def test_downgrade_returns_empty(self):
        self.assertEqual(prorate_seats(sub(), plan(500), PE - timedelta(days=15)), [])

    def test_equal_price_returns_empty(self):
        self.assertEqual(prorate_seats(sub(), plan(1000), PE - timedelta(days=15)), [])

    def test_changed_at_on_or_after_period_end_returns_empty(self):
        self.assertEqual(prorate_seats(sub(), plan(2000), PE), [])
        self.assertEqual(prorate_seats(sub(), plan(2000), PE + timedelta(days=1)), [])

    def test_credit_of_49_cents_is_skipped(self):
        full_period = PE - timedelta(days=30)
        lines = prorate_seats(sub(seat_price_cents=49, billable_seats=1), plan(100), full_period)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 100)
        self.assertEqual(lines[0]["vat_cents"], 21)

    def test_credit_rounds_up(self):
        lines = prorate_seats(sub(seat_price_cents=1001, billable_seats=3), plan(2000), PE - timedelta(days=15))
        self.assertEqual(lines[0]["amount_cents"], 1502)  # ceil(1501.5)
        self.assertEqual(lines[1]["amount_cents"], 3000)  # floor(3000)

    def test_reverse_charge_gives_zero_vat_on_charge(self):
        lines = prorate_seats(sub(vat_id="NL123456789B01"), plan(2000), PE - timedelta(days=15))
        self.assertEqual(lines[1]["kind"], "charge")
        self.assertEqual(lines[1]["vat_cents"], 0)

    def test_blank_vat_id_is_not_reverse_charge(self):
        lines = prorate_seats(sub(vat_id="   "), plan(2000), PE - timedelta(days=15))
        self.assertEqual(lines[1]["vat_cents"], 630)

    def test_credit_always_has_zero_vat(self):
        lines = prorate_seats(sub(), plan(2000), PE - timedelta(days=15))
        self.assertEqual(lines[0]["vat_cents"], 0)

    def test_credit_over_threshold_goes_to_ramon(self):
        lines = prorate_seats(sub(seat_price_cents=100000, billable_seats=1),
                              plan(200000), PE - timedelta(days=30))
        self.assertEqual(lines[0]["amount_cents"], 100000)
        self.assertEqual(lines[0]["approved_by"], HIGH_VALUE_APPROVER)

    def test_credit_exactly_threshold_goes_to_thao(self):
        lines = prorate_seats(sub(seat_price_cents=50000, billable_seats=1),
                              plan(200000), PE - timedelta(days=30))
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], FINANCE_APPROVER)

    def test_seats_is_ignored_in_favour_of_billable_seats(self):
        a = prorate_seats(sub(seats=5, billable_seats=3), plan(2000), PE - timedelta(days=15))
        b = prorate_seats(sub(seats=500, billable_seats=3), plan(2000), PE - timedelta(days=15))
        self.assertEqual(a, b)
        self.assertEqual(a[0]["amount_cents"], 1500)

    def test_legacy_discount_is_ignored(self):
        a = prorate_seats(sub(legacy_discount=0.25), plan(2000), PE - timedelta(days=15))
        b = prorate_seats(sub(legacy_discount="not-a-number"), plan(2000), PE - timedelta(days=15))
        self.assertEqual(a, b)

    def test_description_keeps_full_date_at_80_char_limit(self):
        long_name = "X" * 200
        lines = prorate_seats(sub(plan_name=long_name), plan(2000), PE - timedelta(days=15))
        desc = lines[0]["description"]
        self.assertLessEqual(len(desc), 80)
        self.assertEqual(len(desc), 80)
        self.assertTrue(desc.endswith("period ends 2026-11-30"))
        self.assertTrue(desc.endswith("..." + " seats, period ends 2026-11-30") or "..." in desc)

    def test_description_raises_when_fixed_text_too_long(self):
        with self.assertRaises(ValueError):
            _describe(CREDIT_TEMPLATE + "x" * 80, "A", "2026-11-30")

    def test_float_price_raises(self):
        with self.assertRaises(TypeError):
            prorate_seats(sub(seat_price_cents=1000.0), plan(2000), PE - timedelta(days=15))
        with self.assertRaises(TypeError):
            prorate_seats(sub(), plan(2000.0), PE - timedelta(days=15))

    def test_float_seats_raises(self):
        with self.assertRaises(TypeError):
            prorate_seats(sub(billable_seats=3.0), plan(2000), PE - timedelta(days=15))

    def test_naive_datetime_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(sub(), plan(2000), datetime(2026, 11, 15, 12, 0))


if __name__ == "__main__":
    unittest.main()