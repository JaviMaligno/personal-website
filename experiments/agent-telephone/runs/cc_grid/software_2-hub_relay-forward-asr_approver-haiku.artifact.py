"""Seat-upgrade proration for Fernhollow Studios billing.

Open-item defaults (client has not answered; conservative choices):
- Currency assumed EUR, so EUR 500 = 50000 cents (APPROVER_THRESHOLD_CENTS).
- "Over EUR 500" is read as strictly greater than 50000 cents.
- The 50-cent minimum applies to credit lines as well as charges ("any line").
  This is in tension with "never round in our favour": a dropped credit is a
  small under-refund to the customer.
- Days are whole days, floored: days_left = floor(elapsed / 1 day).
- Charge VAT is rounded down to the cent (integer floor).
- Only status "trialing" is exempt; all other statuses are prorated.
- Dates are formatted in period_end's own timezone. The day count uses absolute
  elapsed time, so it does not depend on either timezone.

This module has not been executed in this environment.
"""
import unittest
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from math import ceil, floor

BILLING_PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
APPROVER_CREDITS = "Win Tee Fung Tao"
APPROVER_LARGE_CREDITS = "Ramón Etxeberria-Goñi"
APPROVER_THRESHOLD_CENTS = 50000  # EUR 500; strictly greater goes to large-credit approver
DESCRIPTION_MAX = 80


def _ensure_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    return value


def _describe(prefix, plan, period_end):
    suffix = f", period ends {period_end.strftime('%Y-%m-%d')}"
    text = f"{prefix}{plan}{suffix}"
    if len(text) <= DESCRIPTION_MAX:
        return text
    available = DESCRIPTION_MAX - len(prefix) - len(suffix)
    if available < 1:
        raise ValueError("description cannot fit in 80 characters with the period end date")
    if available >= 4:
        plan = plan[:available - 3] + "..."
    else:
        plan = plan[:available]
    text = f"{prefix}{plan}{suffix}"
    if len(text) > DESCRIPTION_MAX:
        raise ValueError("description exceeds 80 characters after shortening plan name")
    return text


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = _ensure_int("seat_price_cents", subscription["seat_price_cents"])
    new_price = _ensure_int("new_plan seat_price_cents", new_plan["seat_price_cents"])
    if new_price <= old_price:  # downgrade or equal price: applies at renewal
        return []

    period_end = subscription["period_end"]
    if changed_at >= period_end:
        return []

    days_left = (period_end - changed_at) // timedelta(days=1)
    seats = _ensure_int("billable_seats", subscription["billable_seats"])
    fraction = Fraction(days_left, BILLING_PERIOD_DAYS)

    credit_cents = ceil(seats * old_price * fraction)   # never round in our favour: up
    charge_cents = floor(seats * new_price * fraction)  # never round in our favour: down

    sub_id = subscription["id"]
    lines = []

    if credit_cents >= MIN_LINE_CENTS:
        approver = (APPROVER_LARGE_CREDITS
                    if credit_cents > APPROVER_THRESHOLD_CENTS
                    else APPROVER_CREDITS)
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe("Seat credit: ", subscription["plan_name"], period_end),
            "approved_by": approver,
        })

    if charge_cents >= MIN_LINE_CENTS:
        if subscription.get("vat_id"):  # reverse charge
            vat = 0
        else:
            vat = floor(Fraction(charge_cents * VAT_PERCENT, 100))
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat,
            "description": _describe("Seat charge: ", new_plan["name"], period_end),
            "approved_by": None,
        })

    return lines


class ProrateSeatsTests(unittest.TestCase):
    PERIOD_END = datetime(2026, 11, 1, tzinfo=timezone.utc)

    def sub(self, **overrides):
        base = {
            "id": "sub_1",
            "status": "active",
            "plan_name": "Studio",
            "seat_price_cents": 1000,
            "seats": 5,
            "billable_seats": 1,
            "vat_id": None,
            "period_end": self.PERIOD_END,
        }
        base.update(overrides)
        return base

    def changed(self, days_left):
        return self.PERIOD_END - timedelta(days=days_left)

    def test_trialing_returns_empty(self):
        out = prorate_seats(self.sub(status="trialing"),
                            {"name": "Pro", "seat_price_cents": 2000},
                            self.changed(10))
        self.assertEqual(out, [])

    def test_downgrade_and_equal_return_empty(self):
        self.assertEqual(prorate_seats(self.sub(), {"name": "Lite", "seat_price_cents": 900},
                                       self.changed(10)), [])
        self.assertEqual(prorate_seats(self.sub(), {"name": "Same", "seat_price_cents": 1000},
                                       self.changed(10)), [])

    def test_credit_rounds_up_and_charge_rounds_down(self):
        # credit: 1 * 1000 * 10/30 = 333.33 -> 334
        # charge: 1 * 1001 * 10/30 = 333.67 -> 333
        out = prorate_seats(self.sub(), {"name": "Pro", "seat_price_cents": 1001},
                            self.changed(10))
        self.assertEqual(out[0]["amount_cents"], 334)
        self.assertEqual(out[1]["amount_cents"], 333)

    def test_sub_fifty_cent_lines_dropped(self):
        # credit: 100 * 10/30 = 33.33 -> 34; charge: 101 * 10/30 = 33.67 -> 33
        out = prorate_seats(self.sub(seat_price_cents=100),
                            {"name": "Pro", "seat_price_cents": 101},
                            self.changed(10))
        self.assertEqual(out, [])

    def test_vat_21_percent_on_charge_only(self):
        out = prorate_seats(self.sub(), {"name": "Pro", "seat_price_cents": 1001},
                            self.changed(10))
        credit, charge = out
        self.assertEqual(credit["vat_cents"], 0)
        self.assertEqual(charge["vat_cents"], 69)  # floor(333 * 0.21) = 69

    def test_reverse_charge_when_vat_id_present(self):
        out = prorate_seats(self.sub(vat_id="DE123456789"),
                            {"name": "Pro", "seat_price_cents": 1001},
                            self.changed(10))
        self.assertEqual(out[1]["vat_cents"], 0)
        self.assertEqual(out[0]["vat_cents"], 0)

    def test_approver_at_exactly_50000_is_win_tee(self):
        out = prorate_seats(self.sub(seat_price_cents=50000),
                            {"name": "Pro", "seat_price_cents": 50001},
                            self.changed(30))
        self.assertEqual(out[0]["amount_cents"], 50000)
        self.assertEqual(out[0]["approved_by"], APPROVER_CREDITS)

    def test_approver_at_50001_is_large_credit_approver(self):
        out = prorate_seats(self.sub(seat_price_cents=50001),
                            {"name": "Pro", "seat_price_cents": 50002},
                            self.changed(30))
        self.assertEqual(out[0]["amount_cents"], 50001)
        self.assertEqual(out[0]["approved_by"], APPROVER_LARGE_CREDITS)

    def test_description_contains_date_and_fits(self):
        out = prorate_seats(self.sub(plan_name="A" * 200),
                            {"name": "Pro", "seat_price_cents": 1001},
                            self.changed(10))
        self.assertIn("2026-11-01", out[0]["description"])
        self.assertLessEqual(len(out[0]["description"]), DESCRIPTION_MAX)
        self.assertIn("2026-11-01", out[1]["description"])
        self.assertIn("Pro", out[1]["description"])

    def test_output_order_credit_then_charge(self):
        out = prorate_seats(self.sub(), {"name": "Pro", "seat_price_cents": 1001},
                            self.changed(10))
        self.assertEqual([line["kind"] for line in out], ["credit", "charge"])
        self.assertIsNone(out[1]["approved_by"])

    def test_amounts_are_int(self):
        out = prorate_seats(self.sub(), {"name": "Pro", "seat_price_cents": 1001},
                            self.changed(10))
        for line in out:
            self.assertIs(type(line["amount_cents"]), int)
            self.assertIs(type(line["vat_cents"]), int)


if __name__ == "__main__":
    unittest.main()