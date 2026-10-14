# /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-fcotngfj/prorate.py
# NOT EXECUTED: this run had no file or shell access, so the code and tests below are unverified.
# Deviations and open points:
# - Validation (TypeError/ValueError) runs before the trialing check, so trialing subscriptions with bad money fields still raise.
# - Credits carry no VAT, as the client brief requires. This overrides the house default that VAT applies to credits too.
# - Currency is assumed to be EUR, so GROUP_LIMIT = 50000 cents is EUR 500. Not confirmed with the client.

"""Seat upgrade proration for Fernhollow Studios.

Assumption: inputs carry no currency field. All amounts are assumed to be EUR
(client is Euro-based), so GROUP_LIMIT = 50000 cents means EUR 500.

Amounts are integer cents. Credits round up (math.ceil), charges round down
(math.floor), computed on exact Fractions. Lines whose net amount is under
MIN_LINE cents are dropped before VAT is added.
"""

import math
from datetime import timedelta
from fractions import Fraction

PERIOD_MICROS = 30 * 86400 * 10**6
GROUP_LIMIT = 50000
MIN_LINE = 50
VAT_RATE = 21
DESC_MAX = 80
CREDIT_APPROVER = "Win Tee Fung Tao"
BIG_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"

_ONE_MICRO = timedelta(microseconds=1)
_CREDIT_PREFIX = "Credit: "
_CHARGE_PREFIX = "Charge: "
_SEATS_UNTIL = " seats until "


def _check_money(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int (cents), got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must not be negative")


def _describe(prefix, plan, date_str):
    budget = DESC_MAX - len(prefix) - len(_SEATS_UNTIL) - len(date_str)
    desc = f"{prefix}{plan}{_SEATS_UNTIL}{date_str}"
    if len(desc) > DESC_MAX:
        plan = plan[:budget].rstrip()
        desc = f"{prefix}{plan}{_SEATS_UNTIL}{date_str}"
    if len(desc) > DESC_MAX:
        raise ValueError("description exceeds maximum length")
    return desc


def prorate_seats(subscription, new_plan, changed_at):
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    billable = subscription["billable_seats"]
    _check_money("seat_price_cents (old plan)", old_price)
    _check_money("seat_price_cents (new plan)", new_price)
    _check_money("billable_seats", billable)

    if subscription["status"] == "trialing":
        return []
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    micro = (period_end - changed_at) // _ONE_MICRO
    if micro <= 0:
        return []
    if micro > PERIOD_MICROS:
        raise ValueError("changed_at is more than 30 days before period_end")
    f = Fraction(micro, PERIOD_MICROS)

    credit_exact = Fraction(old_price * billable) * f
    charge_exact = Fraction(new_price * billable) * f
    credit_cents = math.ceil(credit_exact)
    charge_cents = math.floor(charge_exact)

    date_str = period_end.strftime("%Y-%m-%d")
    sub_id = subscription["id"]
    lines = []

    if credit_cents >= MIN_LINE:
        approver = BIG_CREDIT_APPROVER if credit_cents > GROUP_LIMIT else CREDIT_APPROVER
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe(_CREDIT_PREFIX, subscription["plan_name"], date_str),
            "approved_by": approver,
        })

    if charge_cents >= MIN_LINE:
        vat_id = subscription["vat_id"]
        if vat_id is None or vat_id.strip() == "":
            vat = math.floor(Fraction(charge_cents * VAT_RATE, 100))
        else:
            vat = 0
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat,
            "description": _describe(_CHARGE_PREFIX, new_plan["name"], date_str),
            "approved_by": None,
        })

    return lines


# /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-fcotngfj/test_prorate.py

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prorate import (  # noqa: E402
    BIG_CREDIT_APPROVER,
    CREDIT_APPROVER,
    prorate_seats,
)

UTC = timezone.utc
PE = datetime(2026, 11, 1, 0, 0, tzinfo=UTC)


def sub(**kw):
    d = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Starter",
        "seat_price_cents": 1000,
        "seats": 3,
        "billable_seats": 1,
        "vat_id": None,
        "period_end": PE,
    }
    d.update(kw)
    return d


def plan(name="Pro", price=1100):
    return {"name": name, "seat_price_cents": price}


def before(days):
    return PE - timedelta(days=days)


class TestProrateSeats(unittest.TestCase):

    def test_worked_example(self):
        lines = prorate_seats(sub(), plan(), before(10))
        self.assertEqual(lines, [
            {
                "subscription_id": "sub_1",
                "kind": "credit",
                "amount_cents": 334,
                "vat_cents": 0,
                "description": "Credit: Starter seats until 2026-11-01",
                "approved_by": CREDIT_APPROVER,
            },
            {
                "subscription_id": "sub_1",
                "kind": "charge",
                "amount_cents": 366,
                "vat_cents": 76,
                "description": "Charge: Pro seats until 2026-11-01",
                "approved_by": None,
            },
        ])

    def test_trialing_returns_empty(self):
        self.assertEqual(prorate_seats(sub(status="trialing"), plan(), before(10)), [])

    def test_downgrade_returns_empty(self):
        self.assertEqual(prorate_seats(sub(), plan(price=900), before(10)), [])

    def test_vat_id_gives_zero_charge_vat(self):
        lines = prorate_seats(sub(vat_id="DE123"), plan(), before(10))
        charge = [l for l in lines if l["kind"] == "charge"][0]
        self.assertEqual(charge["amount_cents"], 366)
        self.assertEqual(charge["vat_cents"], 0)

    def test_blank_vat_id_still_charges_vat(self):
        lines = prorate_seats(sub(vat_id="   "), plan(), before(10))
        charge = [l for l in lines if l["kind"] == "charge"][0]
        self.assertEqual(charge["vat_cents"], 76)

    def test_billable_seats_used_not_seats(self):
        lines = prorate_seats(sub(seats=50, billable_seats=1), plan(), before(10))
        self.assertEqual(lines[0]["amount_cents"], 334)

    def test_credit_exactly_50000_not_big(self):
        lines = prorate_seats(sub(seat_price_cents=50000), plan(price=50000), before(30))
        credit = lines[0]
        self.assertEqual(credit["amount_cents"], 50000)
        self.assertEqual(credit["approved_by"], CREDIT_APPROVER)

    def test_credit_over_50000_gets_big_approver(self):
        lines = prorate_seats(sub(seat_price_cents=60000), plan(price=60000), before(30))
        credit = lines[0]
        self.assertEqual(credit["amount_cents"], 60000)
        self.assertEqual(credit["approved_by"], BIG_CREDIT_APPROVER)

    def test_under_50_cents_both_lines_dropped(self):
        # 1 day left: credit ceil(999/30)=34, charge floor(1000/30)=33, both under 50
        lines = prorate_seats(sub(seat_price_cents=999), plan(price=1000), before(1))
        self.assertEqual(lines, [])

    def test_charge_49_dropped_charge_50_kept(self):
        # old price 0 so the credit is 0 and dropped; full month so f = 1
        self.assertEqual(prorate_seats(sub(seat_price_cents=0), plan(price=49), before(30)), [])
        lines = prorate_seats(sub(seat_price_cents=0), plan(price=50), before(30))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 50)
        self.assertEqual(lines[0]["vat_cents"], 10)

    def test_long_plan_name_truncated_keeps_date(self):
        lines = prorate_seats(sub(plan_name="A" * 100), plan(), before(10))
        desc = lines[0]["description"]
        self.assertLessEqual(len(desc), 80)
        self.assertEqual(desc, "Credit: " + "A" * 49 + " seats until 2026-11-01")
        self.assertTrue(desc.endswith("2026-11-01"))

    def test_change_at_or_after_period_end_returns_empty(self):
        self.assertEqual(prorate_seats(sub(), plan(), PE), [])
        self.assertEqual(prorate_seats(sub(), plan(), PE + timedelta(days=1)), [])

    def test_more_than_30_days_before_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(sub(), plan(), before(31))

    def test_float_money_raises_type_error(self):
        with self.assertRaises(TypeError):
            prorate_seats(sub(seat_price_cents=10.0), plan(), before(10))
        with self.assertRaises(TypeError):
            prorate_seats(sub(), plan(price=1100.0), before(10))
        with self.assertRaises(TypeError):
            prorate_seats(sub(billable_seats=1.0), plan(), before(10))

    def test_bool_money_raises_type_error(self):
        with self.assertRaises(TypeError):
            prorate_seats(sub(billable_seats=True), plan(), before(10))

    def test_negative_values_raise_value_error(self):
        with self.assertRaises(ValueError):
            prorate_seats(sub(seat_price_cents=-1), plan(), before(10))
        with self.assertRaises(ValueError):
            prorate_seats(sub(billable_seats=-1), plan(), before(10))

    def test_timezone_offsets_give_same_day_count(self):
        plus2 = timezone(timedelta(hours=2))
        changed = datetime(2026, 10, 22, 2, 0, tzinfo=plus2)  # == 2026-10-22T00:00Z
        lines = prorate_seats(sub(), plan(), changed)
        self.assertEqual(lines[0]["amount_cents"], 334)
        self.assertEqual(lines[1]["amount_cents"], 366)


if __name__ == "__main__":
    unittest.main()