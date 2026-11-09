"""Seat-upgrade proration for Fernhollow Studios.

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list of invoice line dicts.
Standard library only. Amounts are integer cents (EUR).

Run the tests from the project directory with: python3 -I <this file>

Proposed defaults where the spec is open (each is isolated in one place so it is easy to change):
  A. Equal old and new seat price returns no lines.                        (prorate_seats, price check)
  B. changed_at at or after period_end returns no lines.                   (prorate_seats, elapsed check)
  C. changed_at more than 30 days before period_end raises ValueError.     (prorate_seats, elapsed check; alternative is clamping to a full period)
  D. The 50-cent minimum applies to the net amount before VAT.             (_MIN_LINE_CENTS checks)
  E. VAT rounds down: net * 21 // 100.                                     (_vat_cents)
  F. Description wording: "Credit, unused {plan} seats to {date}" and "Charge, {plan} seats to {date}". Pending review by Dagny.  (_describe)

Spec conflict noted: the house rule says VAT applies to credits too. The client spec explicitly says credit lines always have vat_cents = 0. The client rule was followed.

Open questions for the client:
  1. Confirm that EUR 500 equals 50,000 cents and that all amounts are EUR.
  2. Confirm whether trialing is the only status that blocks proration. Should canceled or past_due also block it?
  3. Should billable_seats greater than seats raise an error? This code does not check it.
  4. Confirm the description wording and the date basis (period_end in its own timezone).
"""

import math
import unittest
from datetime import datetime, timedelta, timezone

PERIOD_US = 30 * 24 * 60 * 60 * 10**6  # 30-day billing period in microseconds
_MIN_LINE_CENTS = 50
_APPROVAL_THRESHOLD_CENTS = 50_000
_CREDIT_APPROVER = "Win Tee Fung Tao"
_LARGE_CREDIT_APPROVER = "Ram\u00f3n Etxeberria-Go\u00f1i"
_VAT_PERCENT = 21
_MAX_DESCRIPTION = 80
_ELLIPSIS = "..."


def _require_aware(name, dt):
    if not isinstance(dt, datetime) or dt.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _plan_name(name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("plan name must be a non-empty string")
    return name


def _describe(kind, plan, period_end):
    date = period_end.date().isoformat()  # date in period_end's own timezone
    if kind == "credit":
        head, mid = "Credit, unused ", " seats to "
    else:
        head, mid = "Charge, ", " seats to "
    room = _MAX_DESCRIPTION - (len(head) + len(mid) + len(date))
    if len(plan) > room:
        plan = plan[: room - len(_ELLIPSIS)] + _ELLIPSIS
    desc = f"{head}{plan}{mid}{date}"
    assert len(desc) <= _MAX_DESCRIPTION and desc.endswith(date), "description overflow"
    return desc


def _vat_cents(net, vat_id):
    if isinstance(vat_id, str) and vat_id.strip():
        return 0  # reverse charge
    return net * _VAT_PERCENT // 100


def prorate_seats(subscription, new_plan, changed_at):
    _require_aware("changed_at", changed_at)
    period_end = subscription.get("period_end")
    _require_aware("period_end", period_end)

    if subscription.get("status") == "trialing":
        return []

    old_cents = subscription["seat_price_cents"]
    new_cents = new_plan["seat_price_cents"]
    if new_cents <= old_cents:  # downgrade applies at renewal; equal price is default A
        return []

    elapsed_us = (period_end - changed_at) // timedelta(microseconds=1)
    if elapsed_us <= 0:  # default B
        return []
    if elapsed_us > PERIOD_US:  # default C
        raise ValueError("changed_at is more than 30 days before period_end")

    credit_plan = _plan_name(subscription.get("plan_name"))
    charge_plan = _plan_name(new_plan.get("name"))

    seats = subscription["billable_seats"]
    sub_id = subscription["id"]
    lines = []

    credit = math.ceil(_fraction(old_cents * seats * elapsed_us))
    if credit >= _MIN_LINE_CENTS:  # default D: tested per line, before VAT
        approver = _LARGE_CREDIT_APPROVER if credit > _APPROVAL_THRESHOLD_CENTS else _CREDIT_APPROVER
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("credit", credit_plan, period_end),
            "approved_by": approver,
        })

    charge = math.floor(_fraction(new_cents * seats * elapsed_us))
    if charge >= _MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": _vat_cents(charge, subscription.get("vat_id")),
            "description": _describe("charge", charge_plan, period_end),
            "approved_by": None,
        })

    return lines


def _fraction(numerator_us_scaled):
    from fractions import Fraction
    return Fraction(numerator_us_scaled, PERIOD_US)


class ProrateSeatsTests(unittest.TestCase):
    END = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
    ONE_HOUR_BEFORE = END - timedelta(hours=1)  # unused fraction = 1/720

    def sub(self, **overrides):
        base = {
            "id": "sub_1",
            "status": "active",
            "plan_name": "Studio",
            "seat_price_cents": 3601,
            "seats": 99,
            "billable_seats": 10,
            "vat_id": None,
            "period_end": self.END,
            "legacy_discount": 0.5,
        }
        base.update(overrides)
        return base

    def plan(self, price=3602, name="Studio Plus"):
        return {"name": name, "seat_price_cents": price}

    def test_trialing_returns_nothing(self):
        self.assertEqual(prorate_seats(self.sub(status="trialing"), self.plan(), self.ONE_HOUR_BEFORE), [])

    def test_downgrade_returns_nothing(self):
        self.assertEqual(prorate_seats(self.sub(seat_price_cents=3602), self.plan(3601), self.ONE_HOUR_BEFORE), [])

    def test_equal_price_returns_nothing(self):
        self.assertEqual(prorate_seats(self.sub(), self.plan(3601), self.ONE_HOUR_BEFORE), [])

    def test_changed_at_at_or_after_period_end_returns_nothing(self):
        self.assertEqual(prorate_seats(self.sub(), self.plan(), self.END), [])
        self.assertEqual(prorate_seats(self.sub(), self.plan(), self.END + timedelta(hours=1)), [])

    def test_more_than_30_days_raises_and_exactly_30_days_does_not(self):
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), self.plan(), self.END - timedelta(days=30, seconds=1))
        lines = prorate_seats(self.sub(), self.plan(), self.END - timedelta(days=30))
        self.assertEqual(len(lines), 2)

    def test_naive_datetimes_raise(self):
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), self.plan(), datetime(2026, 10, 31, 11, 0))
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(period_end=datetime(2026, 10, 31, 12, 0)), self.plan(), self.ONE_HOUR_BEFORE)

    def test_rounding_direction_credit_up_charge_down(self):
        # 36010/720 = 50.0139 -> credit rounds up to 51; 36020/720 = 50.0278 -> charge rounds down to 50
        credit, charge = prorate_seats(self.sub(), self.plan(3602), self.ONE_HOUR_BEFORE)
        self.assertEqual(credit["amount_cents"], 51)
        self.assertEqual(charge["amount_cents"], 50)

    def test_minimum_per_line_drops_only_the_small_line(self):
        # credit = ceil(35290/720) = 50 (kept); charge = floor(35291/720) = 49 (dropped)
        lines = prorate_seats(self.sub(seat_price_cents=35290, billable_seats=1), self.plan(35291), self.ONE_HOUR_BEFORE)
        self.assertEqual([l["kind"] for l in lines], ["credit"])
        self.assertEqual(lines[0]["amount_cents"], 50)

    def test_both_lines_under_minimum_returns_nothing(self):
        # credit = ceil(1/720) = 1; charge = floor(35280/720) = 49
        lines = prorate_seats(self.sub(seat_price_cents=1, billable_seats=1), self.plan(35280), self.ONE_HOUR_BEFORE)
        self.assertEqual(lines, [])

    def test_charge_only_when_credit_dropped(self):
        lines = prorate_seats(self.sub(seat_price_cents=1, billable_seats=1), self.plan(36000), self.ONE_HOUR_BEFORE)
        self.assertEqual([l["kind"] for l in lines], ["charge"])
        self.assertEqual(lines[0]["amount_cents"], 50)
        self.assertIsNone(lines[0]["approved_by"])

    def test_approval_boundary_exactly_50000_goes_to_win_tee(self):
        lines = prorate_seats(self.sub(seat_price_cents=36000000, billable_seats=1), self.plan(36000001), self.ONE_HOUR_BEFORE)
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], "Win Tee Fung Tao")

    def test_approval_boundary_50001_goes_to_ramon(self):
        lines = prorate_seats(self.sub(seat_price_cents=36000720, billable_seats=1), self.plan(36000721), self.ONE_HOUR_BEFORE)
        self.assertEqual(lines[0]["amount_cents"], 50001)
        self.assertEqual(lines[0]["approved_by"], "Ram\u00f3n Etxeberria-Go\u00f1i")

    def test_reverse_charge_with_vat_id(self):
        lines = prorate_seats(self.sub(vat_id="DE123456789"), self.plan(3602), self.ONE_HOUR_BEFORE)
        self.assertEqual(lines[1]["vat_cents"], 0)

    def test_blank_vat_id_is_treated_as_absent(self):
        for vat_id in (None, "", "   "):
            lines = prorate_seats(self.sub(vat_id=vat_id), self.plan(3602), self.ONE_HOUR_BEFORE)
            self.assertEqual(lines[1]["vat_cents"], 10, vat_id)  # 21% of 50 rounded down

    def test_21_percent_vat_on_charge_and_zero_on_credit(self):
        credit, charge = prorate_seats(self.sub(), self.plan(3602), self.ONE_HOUR_BEFORE)
        self.assertEqual(charge["vat_cents"], 10)
        self.assertEqual(credit["vat_cents"], 0)

    def test_description_limit_with_accented_plan_names(self):
        credit, charge = prorate_seats(
            self.sub(plan_name="\u00c9" * 100), self.plan(3602, name="\u00d6" * 100), self.ONE_HOUR_BEFORE
        )
        self.assertEqual(len(credit["description"]), 80)
        self.assertEqual(credit["description"], "Credit, unused " + "\u00c9" * 42 + "..." + " seats to 2026-10-31")
        self.assertEqual(len(charge["description"]), 80)
        self.assertEqual(charge["description"], "Charge, " + "\u00d6" * 49 + "..." + " seats to 2026-10-31")

    def test_date_uses_period_end_own_timezone(self):
        tz_end = datetime(2026, 10, 31, 1, 0, tzinfo=timezone(timedelta(hours=5)))  # UTC is 2026-10-30 20:00
        credit, charge = prorate_seats(
            self.sub(period_end=tz_end), self.plan(3602), tz_end - timedelta(hours=1)
        )
        self.assertTrue(credit["description"].endswith("2026-10-31"))
        self.assertTrue(charge["description"].endswith("2026-10-31"))

    def test_credit_comes_first(self):
        lines = prorate_seats(self.sub(), self.plan(3602), self.ONE_HOUR_BEFORE)
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])

    def test_empty_plan_name_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(plan_name=""), self.plan(3602), self.ONE_HOUR_BEFORE)
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), self.plan(3602, name="   "), self.ONE_HOUR_BEFORE)


if __name__ == "__main__":
    unittest.main()