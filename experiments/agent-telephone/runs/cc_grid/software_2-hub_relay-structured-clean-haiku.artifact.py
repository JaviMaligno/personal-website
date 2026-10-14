"""Seat upgrade proration for Fernhollow Studios.

Public entry point: prorate_seats(subscription, new_plan, changed_at).

Assumptions to confirm with the client (blocking questions, defaults used):
- Q-a: all amounts are EUR, so the EUR 500 approval threshold is 50000 cents.
- Q-b: "over" means strictly greater than 50000 cents. Exactly 50000 gets the standard approver.
- Q-c: billable_seats is used for both the credit and the charge. seats is never read.
- Q-d: this function reprices only. It does not handle a seat count change in the same operation.
- Q-f: only the status "trialing" is excluded (see I1). Other statuses are prorated as normal.

Implementation decisions to confirm:
- I1: Only "trialing" returns []. Other statuses are prorated; this is an open question for the client.
- I2: changed_at at or after period_end returns []. changed_at earlier than period_end minus 30 days raises ValueError. The window check runs before the status and price checks.
- I3: Equal old and new prices return [].
- I4: Charge VAT is computed on the already-floored charge amount, and the VAT amount is floored. Finance should confirm this.
- I5: The description date is the calendar date of period_end in its own timezone.
- Defaults chosen where the spec is silent:
  - Approval is judged on the net credit amount_cents after ceiling rounding.
  - A vat_id counts as set only if it is a string with non-whitespace content.
  - Naive datetimes raise ValueError even when the subscription is trialing.
  - Descriptions use the template "Proration: {plan} until {YYYY-MM-DD}". Only the plan name is truncated, to fit within 80 characters, using a trailing "...".
- legacy_discount is never read.

All arithmetic uses fractions.Fraction over integer microseconds. No floats are used.

The unit tests in this module use the standard library unittest package. Run them with: python -m unittest. They were not executed in the authoring environment.
"""

import math
import unittest
from datetime import datetime, timedelta, timezone
from fractions import Fraction

VAT_RATE_PERCENT = 21
PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
APPROVAL_THRESHOLD_CENTS = 50000
APPROVER_STANDARD = "Nguyễn Thị Phương Thảo"
APPROVER_OVER_THRESHOLD = "Ramón Etxeberria-Goñi"
DESCRIPTION_MAX = 80

_PERIOD = timedelta(days=PERIOD_DAYS)
_PERIOD_US = PERIOD_DAYS * 24 * 3600 * 10 ** 6
_DESC_PREFIX = "Proration: "
_DESC_INFIX = " until "


def _require_aware(name, value):
    if not isinstance(value, datetime):
        raise ValueError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _is_reverse_charge(vat_id):
    return isinstance(vat_id, str) and vat_id.strip() != ""


def _describe(plan_name, period_end):
    date_str = period_end.date().isoformat()
    full = f"{_DESC_PREFIX}{plan_name}{_DESC_INFIX}{date_str}"
    if len(full) <= DESCRIPTION_MAX:
        return full
    fixed = len(_DESC_PREFIX) + len(_DESC_INFIX) + len(date_str)
    room = DESCRIPTION_MAX - fixed
    if len(plan_name) > room:
        plan_name = plan_name[:max(room - 3, 0)] + "..."
    return f"{_DESC_PREFIX}{plan_name}{_DESC_INFIX}{date_str}"


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription["period_end"]
    _require_aware("changed_at", changed_at)
    _require_aware("period_end", period_end)

    if period_end - changed_at > _PERIOD:
        raise ValueError("changed_at is earlier than period_end minus 30 days")

    if subscription["status"] == "trialing":
        return []
    if changed_at >= period_end:
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:
        return []

    seats = subscription["billable_seats"]
    unused_us = (period_end - changed_at) // timedelta(microseconds=1)
    fraction = Fraction(unused_us, _PERIOD_US)

    credit = math.ceil(old_price * seats * fraction)
    charge = math.floor(new_price * seats * fraction)

    sub_id = subscription["id"]
    lines = []

    if credit >= MIN_LINE_CENTS:
        approver = (
            APPROVER_STANDARD
            if credit <= APPROVAL_THRESHOLD_CENTS
            else APPROVER_OVER_THRESHOLD
        )
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe(subscription["plan_name"], period_end),
            "approved_by": approver,
        })

    if charge >= MIN_LINE_CENTS:
        if _is_reverse_charge(subscription["vat_id"]):
            vat = 0
        else:
            vat = charge * VAT_RATE_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe(new_plan["name"], period_end),
            "approved_by": None,
        })

    return lines


class TestProrateSeats(unittest.TestCase):
    PE = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
    ONE_DAY = timedelta(days=1)
    THIRTY_DAYS = timedelta(days=30)

    def _sub(self, **over):
        s = {
            "id": "sub_1",
            "status": "active",
            "plan_name": "Studio",
            "seat_price_cents": 1000,
            "seats": 1,
            "billable_seats": 1,
            "vat_id": "",
            "period_end": self.PE,
            "legacy_discount": None,
        }
        s.update(over)
        return s

    def test_downgrade_returns_empty(self):
        s = self._sub(seat_price_cents=2000)
        self.assertEqual(prorate_seats(s, {"name": "Lite", "seat_price_cents": 1000},
                                       self.PE - self.ONE_DAY), [])

    def test_equal_price_returns_empty(self):
        s = self._sub(seat_price_cents=1000)
        self.assertEqual(prorate_seats(s, {"name": "Same", "seat_price_cents": 1000},
                                       self.PE - self.ONE_DAY), [])

    def test_trialing_returns_empty(self):
        s = self._sub(status="trialing")
        self.assertEqual(prorate_seats(s, {"name": "Pro", "seat_price_cents": 2000},
                                       self.PE - self.ONE_DAY), [])

    def test_credit_rounds_up_and_charge_rounds_down(self):
        # One unused day is 1/30 of the period.
        # Credit: 3001 / 30 = 100.03... -> 101 (ceiling)
        # Charge: 4001 / 30 = 133.36... -> 133 (floor)
        s = self._sub(seat_price_cents=3001)
        lines = prorate_seats(s, {"name": "Pro", "seat_price_cents": 4001},
                              self.PE - self.ONE_DAY)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["amount_cents"], 101)
        self.assertEqual(lines[1]["amount_cents"], 133)
        # VAT on floored charge: 133 * 21 // 100 = 27
        self.assertEqual(lines[1]["vat_cents"], 27)

    def test_descriptions_within_limit_and_keep_date(self):
        s = self._sub(plan_name="P" * 200, seat_price_cents=1000)
        lines = prorate_seats(s, {"name": "Q" * 200, "seat_price_cents": 3000},
                              self.PE - self.THIRTY_DAYS / 2)
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertLessEqual(len(line["description"]), 80)
            self.assertTrue(line["description"].endswith(" until 2026-11-01"))

    def test_short_names_are_not_truncated(self):
        s = self._sub()
        lines = prorate_seats(s, {"name": "Pro", "seat_price_cents": 2000},
                              self.PE - self.THIRTY_DAYS)
        self.assertEqual(lines[0]["description"], "Proration: Studio until 2026-11-01")
        self.assertEqual(lines[1]["description"], "Proration: Pro until 2026-11-01")

    def test_approval_boundary_50000_vs_50001(self):
        plan = {"name": "Pro", "seat_price_cents": 60000}
        at_limit = self._sub(seat_price_cents=50000)
        lines = prorate_seats(at_limit, plan, self.PE - self.THIRTY_DAYS)
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], APPROVER_STANDARD)

        over_limit = self._sub(seat_price_cents=50001)
        lines = prorate_seats(over_limit, plan, self.PE - self.THIRTY_DAYS)
        self.assertEqual(lines[0]["amount_cents"], 50001)
        self.assertEqual(lines[0]["approved_by"], APPROVER_OVER_THRESHOLD)

    def test_credit_comes_before_charge(self):
        s = self._sub()
        lines = prorate_seats(s, {"name": "Pro", "seat_price_cents": 2000},
                              self.PE - self.THIRTY_DAYS)
        self.assertEqual([line["kind"] for line in lines], ["credit", "charge"])

    def test_priced_on_billable_seats_not_seats(self):
        s = self._sub(seats=5, billable_seats=2, seat_price_cents=1000)
        lines = prorate_seats(s, {"name": "Pro", "seat_price_cents": 2000},
                              self.PE - self.THIRTY_DAYS)
        self.assertEqual(lines[0]["amount_cents"], 2000)
        self.assertEqual(lines[1]["amount_cents"], 4000)

    def test_legacy_discount_has_no_effect(self):
        plan = {"name": "Pro", "seat_price_cents": 2000}
        changed = self.PE - self.ONE_DAY
        with_discount = prorate_seats(self._sub(legacy_discount=0.9), plan, changed)
        without = prorate_seats(self._sub(legacy_discount=None), plan, changed)
        self.assertEqual(with_discount, without)

    def test_lines_under_50_cents_are_dropped(self):
        # Credit: 1 / 30 ceiling = 1, dropped. Charge: 2000 / 30 floor = 66, kept.
        s = self._sub(seat_price_cents=1)
        lines = prorate_seats(s, {"name": "Pro", "seat_price_cents": 2000},
                              self.PE - self.ONE_DAY)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 66)

    def test_vat_zero_with_vat_id_and_21_percent_without(self):
        plan = {"name": "Pro", "seat_price_cents": 2000}
        changed = self.PE - self.THIRTY_DAYS
        no_vat_id = prorate_seats(self._sub(vat_id=""), plan, changed)
        self.assertEqual(no_vat_id[1]["vat_cents"], 420)
        with_vat_id = prorate_seats(self._sub(vat_id="GB123456789"), plan, changed)
        self.assertEqual(with_vat_id[1]["vat_cents"], 0)

    def test_credits_never_carry_vat(self):
        s = self._sub(vat_id="")
        lines = prorate_seats(s, {"name": "Pro", "seat_price_cents": 2000},
                              self.PE - self.THIRTY_DAYS)
        self.assertEqual(lines[0]["kind"], "credit")
        self.assertEqual(lines[0]["vat_cents"], 0)

    def test_line_keys_are_exact(self):
        s = self._sub()
        lines = prorate_seats(s, {"name": "Pro", "seat_price_cents": 2000},
                              self.PE - self.THIRTY_DAYS)
        expected = {"subscription_id", "kind", "amount_cents", "vat_cents",
                    "description", "approved_by"}
        for line in lines:
            self.assertEqual(set(line), expected)
        self.assertIsNone(lines[1]["approved_by"])

    def test_naive_datetime_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(self._sub(), {"name": "Pro", "seat_price_cents": 2000},
                          datetime(2026, 10, 31, 12, 0))

    def test_changed_at_too_early_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(self._sub(), {"name": "Pro", "seat_price_cents": 2000},
                          self.PE - timedelta(days=31))

    def test_changed_at_at_or_after_period_end_returns_empty(self):
        plan = {"name": "Pro", "seat_price_cents": 2000}
        self.assertEqual(prorate_seats(self._sub(), plan, self.PE), [])
        self.assertEqual(prorate_seats(self._sub(), plan, self.PE + self.ONE_DAY), [])

    def test_date_uses_period_end_own_timezone(self):
        pe = datetime(2026, 11, 1, 1, 0, tzinfo=timezone(timedelta(hours=5)))
        s = self._sub(period_end=pe)
        lines = prorate_seats(s, {"name": "Pro", "seat_price_cents": 2000},
                              pe - self.ONE_DAY)
        self.assertTrue(lines[0]["description"].endswith("2026-11-01"))


if __name__ == "__main__":
    unittest.main()