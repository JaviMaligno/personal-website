"""Seat upgrade proration for Fernhollow Studios.

Assumptions (chosen from the PM spec defaults):
- days_left = whole days (floor) from changed_at to period_end, capped at 30.
- The billing period is always 30 days.
- Downgrade means new price strictly lower than old price. Equal prices produce lines.
- Credit = ceil(old_price * billable_seats * days_left / 30); charge = floor(new_price * billable_seats * days_left / 30).
- A line is skipped when its net amount (before VAT) is under 50 cents. The check is applied to each line independently.
- Charge VAT = floor(net * 21 / 100), or 0 when vat_id is truthy. Credits carry zero VAT.
- Credits over 50000 cents go to Ramón Etxeberria-Goñi, otherwise to Nguyễn Thị Phương Thảo. Amounts are assumed to be EUR cents, so EUR 500 = 50000 cents.
- Dates in descriptions are YYYY-MM-DD taken from period_end in its own timezone.
- Descriptions are capped at 80 code points. An over-long plan name is cut and followed by U+2026 "…"; the date is always kept.
- Non-integer prices or seat counts raise TypeError. Legacy_discount is ignored.

Open questions for the client (not decided here):
- Day counting convention: calendar days versus 24-hour days, and whether the change day counts.
- Currency confirmation for the approval threshold.
- Whether the 50-cent skip applies per line or per credit/charge pair.

Test status: the PM worked examples A through K were not included in the material supplied, so the tests below cover the spec rules directly. They have not been executed in this environment.
"""

import math
import unittest
from datetime import datetime, timedelta, timezone
from fractions import Fraction

PERIOD_DAYS = 30
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
APPROVAL_THRESHOLD_CENTS = 50000
DESCRIPTION_MAX = 80
ELLIPSIS = "\u2026"
THAO = "Nguyễn Thị Phương Thảo"
RAMON = "Ramón Etxeberria-Goñi"


def _round_cents(value, up):
    """Single rounding point: ceil when up is True (credits), floor otherwise (charges, VAT)."""
    if not isinstance(value, Fraction):
        raise TypeError("value must be a Fraction")
    return math.ceil(value) if up else math.floor(value)


def _require_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    return value


def _description(verb, plan, period_end):
    date = period_end.date().isoformat()
    suffix = f" seats, period end {date}"
    full = f"{verb} {plan}{suffix}"
    if len(full) <= DESCRIPTION_MAX:
        return full
    # Fixed parts are at most 36 code points, so this budget is always positive.
    budget = DESCRIPTION_MAX - len(f"{verb} ") - len(suffix) - len(ELLIPSIS)
    return f"{verb} {plan[:budget]}{ELLIPSIS}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = _require_int("seat_price_cents", subscription["seat_price_cents"])
    new_price = _require_int("new_plan seat_price_cents", new_plan["seat_price_cents"])
    seats = _require_int("billable_seats", subscription["billable_seats"])
    period_end = subscription["period_end"]

    if new_price < old_price:
        return []
    if changed_at >= period_end:
        return []

    whole_days = (period_end - changed_at) // timedelta(days=1)
    days_left = min(PERIOD_DAYS, whole_days)

    lines = []
    sub_id = subscription["id"]

    credit = _round_cents(
        Fraction(old_price * seats * days_left, PERIOD_DAYS), up=True
    )
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit", subscription["plan_name"], period_end),
            "approved_by": THAO if credit <= APPROVAL_THRESHOLD_CENTS else RAMON,
        })

    charge = _round_cents(
        Fraction(new_price * seats * days_left, PERIOD_DAYS), up=False
    )
    if charge >= MIN_LINE_CENTS:
        if subscription["vat_id"]:
            vat = 0
        else:
            vat = _round_cents(Fraction(charge * VAT_PERCENT, 100), up=False)
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description("Charge", new_plan["name"], period_end),
            "approved_by": None,
        })

    return lines


PE = datetime(2026, 11, 1, tzinfo=timezone.utc)


def _sub(**overrides):
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Pro",
        "seat_price_cents": 1000,
        "seats": 3,
        "billable_seats": 3,
        "vat_id": None,
        "period_end": PE,
    }
    base.update(overrides)
    return base


class ProrateSeatsTests(unittest.TestCase):

    def test_basic_credit_then_charge_with_vat(self):
        lines = prorate_seats(
            _sub(),
            {"name": "Business", "seat_price_cents": 1500},
            PE - timedelta(days=15),
        )
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        credit, charge = lines
        self.assertEqual(credit["amount_cents"], 1500)
        self.assertEqual(credit["vat_cents"], 0)
        self.assertEqual(credit["approved_by"], THAO)
        self.assertEqual(credit["description"], "Credit Pro seats, period end 2026-11-01")
        self.assertEqual(charge["amount_cents"], 2250)
        self.assertEqual(charge["vat_cents"], 472)
        self.assertIsNone(charge["approved_by"])
        self.assertEqual(charge["description"], "Charge Business seats, period end 2026-11-01")
        self.assertEqual(charge["subscription_id"], "sub_1")

    def test_trialing_returns_nothing(self):
        self.assertEqual(
            prorate_seats(_sub(status="trialing"),
                          {"name": "Business", "seat_price_cents": 1500},
                          PE - timedelta(days=15)),
            [],
        )

    def test_downgrade_returns_nothing(self):
        self.assertEqual(
            prorate_seats(_sub(),
                          {"name": "Basic", "seat_price_cents": 500},
                          PE - timedelta(days=15)),
            [],
        )

    def test_rounding_credit_up_and_charge_down(self):
        lines = prorate_seats(
            _sub(seat_price_cents=2000, billable_seats=1, seats=1),
            {"name": "Business", "seat_price_cents": 2050},
            PE - timedelta(days=1),
        )
        self.assertEqual(lines[0]["amount_cents"], 67)   # ceil(66.67)
        self.assertEqual(lines[1]["amount_cents"], 68)   # floor(68.33)
        self.assertEqual(lines[1]["vat_cents"], 14)      # floor(14.28)

    def test_lines_under_50_cents_are_skipped(self):
        lines = prorate_seats(
            _sub(seat_price_cents=1000, billable_seats=1, seats=1),
            {"name": "Business", "seat_price_cents": 1000},
            PE - timedelta(days=1),
        )
        self.assertEqual(lines, [])  # credit 34, charge 33, both under 50

    def test_reverse_charge_when_vat_id_set(self):
        lines = prorate_seats(
            _sub(vat_id="DE123", seat_price_cents=2000, billable_seats=1, seats=1),
            {"name": "Business", "seat_price_cents": 2050},
            PE - timedelta(days=1),
        )
        self.assertEqual(lines[1]["kind"], "charge")
        self.assertEqual(lines[1]["vat_cents"], 0)

    def test_approval_threshold_ramon_above_50000(self):
        lines = prorate_seats(
            _sub(seat_price_cents=100000, billable_seats=1, seats=1),
            {"name": "Business", "seat_price_cents": 100000},
            PE - timedelta(days=30),
        )
        self.assertEqual(lines[0]["amount_cents"], 100000)
        self.assertEqual(lines[0]["approved_by"], RAMON)
        self.assertEqual(lines[1]["vat_cents"], 21000)

    def test_approval_threshold_thao_at_exactly_50000(self):
        lines = prorate_seats(
            _sub(seat_price_cents=50000, billable_seats=1, seats=1),
            {"name": "Business", "seat_price_cents": 50000},
            PE - timedelta(days=30),
        )
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], THAO)

    def test_days_capped_at_30(self):
        lines = prorate_seats(
            _sub(seat_price_cents=1000, billable_seats=2, seats=2),
            {"name": "Business", "seat_price_cents": 1000},
            PE - timedelta(days=60),
        )
        self.assertEqual(lines[0]["amount_cents"], 2000)

    def test_change_at_or_after_period_end_returns_nothing(self):
        plan = {"name": "Business", "seat_price_cents": 1500}
        self.assertEqual(prorate_seats(_sub(), plan, PE), [])
        self.assertEqual(prorate_seats(_sub(), plan, PE + timedelta(hours=1)), [])

    def test_billable_seats_used_not_seats(self):
        lines = prorate_seats(
            _sub(seats=10, billable_seats=1, seat_price_cents=3000),
            {"name": "Business", "seat_price_cents": 3000},
            PE - timedelta(days=30),
        )
        self.assertEqual(lines[0]["amount_cents"], 3000)

    def test_long_plan_name_truncated_keeps_date(self):
        name = "A" * 60
        lines = prorate_seats(
            _sub(seat_price_cents=1000, billable_seats=1, seats=1),
            {"name": name, "seat_price_cents": 1500},
            PE - timedelta(days=30),
        )
        desc = lines[1]["description"]
        self.assertLessEqual(len(desc), DESCRIPTION_MAX)
        self.assertEqual(desc, "Charge " + "A" * 43 + ELLIPSIS + " seats, period end 2026-11-01")

    def test_float_price_rejected(self):
        with self.assertRaises(TypeError):
            prorate_seats(_sub(seat_price_cents=10.5),
                          {"name": "Business", "seat_price_cents": 1500},
                          PE - timedelta(days=15))


if __name__ == "__main__":
    unittest.main()