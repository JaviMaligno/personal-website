"""Seat-upgrade proration for Fernhollow Studios.

All amounts are integer cents. Rounding follows the brief: credits round up,
charges round down. Both directions favour the customer, which may conflict
with the stated intent of the consumer-authority ruling. Implemented as
specified; confirm with the PM before release.

Interpretations:
- Only status "trialing" is excluded. Other statuses are prorated normally.
- Equal price is treated as an upgrade, so lines are generated.
- Each line is filtered independently against the 50-cent minimum.
- unused_days is the calendar-date difference from changed_at to period_end,
  with changed_at converted into period_end's timezone first.
- vat_id of None or "" is treated as absent.
- Ramón approves credits strictly greater than 50000 cents (EUR assumed).
- Description: "<plan> seats, ends YYYY-MM-DD". Only the plan name is shortened
  to fit 80 characters. Credits name the old plan, charges name the new plan.
- billable_seats is used; seats and legacy_discount are never read.
"""

import unittest
from datetime import datetime, timedelta, timezone

MAX_DESC = 80
MIN_LINE_CENTS = 50
RAMON_THRESHOLD_CENTS = 50000
WIN_TEE = "Win Tee Fung Tao"
RAMON = "Ramón Etxeberria-Goñi"
VAT_PERCENT = 21
PERIOD_DAYS = 30
_SUFFIX = " seats, ends {date}"


def _describe(plan, date_str):
    suffix = _SUFFIX.format(date=date_str)
    room = MAX_DESC - len(suffix)
    if room < 1:
        raise ValueError("description cannot fit within 80 characters")
    return plan[:room] + suffix


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    if changed_at >= period_end:
        return []

    local_change = changed_at.astimezone(period_end.tzinfo)
    unused_days = (period_end.date() - local_change.date()).days
    seats = subscription["billable_seats"]

    # Credit rounds up (ceiling), charge rounds down (floor), per brief.
    credit = -((-old_price * seats * unused_days) // PERIOD_DAYS)
    charge = (new_price * seats * unused_days) // PERIOD_DAYS

    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    if credit >= MIN_LINE_CENTS:
        approver = RAMON if credit > RAMON_THRESHOLD_CENTS else WIN_TEE
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe(subscription["plan_name"], date_str),
            "approved_by": approver,
        })

    if charge >= MIN_LINE_CENTS:
        vat = 0 if subscription.get("vat_id") else charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe(new_plan["name"], date_str),
            "approved_by": None,
        })

    return lines


UTC = timezone.utc
PE = datetime(2026, 11, 1, tzinfo=UTC)


def _sub(**overrides):
    sub = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Studio",
        "seat_price_cents": 1000,
        "seats": 50,
        "billable_seats": 1,
        "vat_id": None,
        "period_end": PE,
    }
    sub.update(overrides)
    return sub


def _days_left(n):
    return PE - timedelta(days=n)


class ProrateSeatsTests(unittest.TestCase):

    def test_trialing_returns_empty(self):
        sub = _sub(status="trialing")
        self.assertEqual(prorate_seats(sub, {"name": "Pro", "seat_price_cents": 5000}, _days_left(10)), [])

    def test_downgrade_returns_empty(self):
        sub = _sub(seat_price_cents=5000)
        self.assertEqual(prorate_seats(sub, {"name": "Basic", "seat_price_cents": 1000}, _days_left(10)), [])

    def test_change_on_or_after_period_end_returns_empty(self):
        new = {"name": "Pro", "seat_price_cents": 2000}
        self.assertEqual(prorate_seats(_sub(), new, PE), [])
        self.assertEqual(prorate_seats(_sub(), new, PE + timedelta(days=1)), [])

    def test_credit_rounds_up_and_charge_rounds_down(self):
        # 1000 * 1 * 7 / 30 = 233.33 -> credit 234 (up)
        # 2000 * 1 * 7 / 30 = 466.67 -> charge 466 (down)
        sub = _sub(seat_price_cents=1000, vat_id="DE1")
        lines = prorate_seats(sub, {"name": "Pro", "seat_price_cents": 2000}, _days_left(7))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        self.assertEqual(lines[0]["amount_cents"], 234)
        self.assertEqual(lines[1]["amount_cents"], 466)

    def test_line_under_50_cents_is_dropped(self):
        # credit: 100 * 1 * 1 / 30 = 3.33 -> 4, dropped
        # charge: 3000 * 1 * 1 / 30 = 100, kept
        sub = _sub(seat_price_cents=100)
        lines = prorate_seats(sub, {"name": "Pro", "seat_price_cents": 3000}, _days_left(1))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 100)

    def test_ramon_threshold(self):
        new = {"name": "Pro", "seat_price_cents": 60000}
        at_limit = prorate_seats(_sub(seat_price_cents=50000), new, _days_left(30))
        self.assertEqual(at_limit[0]["amount_cents"], 50000)
        self.assertEqual(at_limit[0]["approved_by"], WIN_TEE)

        over = prorate_seats(_sub(seat_price_cents=50001), new, _days_left(30))
        self.assertEqual(over[0]["amount_cents"], 50001)
        self.assertEqual(over[0]["approved_by"], RAMON)

    def test_vat_rules(self):
        new = {"name": "Pro", "seat_price_cents": 1000}
        no_vat = prorate_seats(_sub(seat_price_cents=100), new, _days_left(30))
        self.assertEqual(no_vat[0]["vat_cents"], 0)          # credit
        self.assertEqual(no_vat[1]["amount_cents"], 1000)
        self.assertEqual(no_vat[1]["vat_cents"], 210)        # charge, 21%

        with_id = prorate_seats(_sub(seat_price_cents=100, vat_id="DE1"), new, _days_left(30))
        self.assertEqual(with_id[0]["vat_cents"], 0)
        self.assertEqual(with_id[1]["vat_cents"], 0)

        empty_id = prorate_seats(_sub(seat_price_cents=100, vat_id=""), new, _days_left(30))
        self.assertEqual(empty_id[1]["vat_cents"], 210)

    def test_description_80_chars_kept(self):
        # " seats, ends 2026-11-01" is 23 chars, so a 57-char plan fits exactly.
        plan = "A" * 57
        sub = _sub(plan_name=plan, seat_price_cents=100)
        lines = prorate_seats(sub, {"name": plan, "seat_price_cents": 1000}, _days_left(30))
        expected = plan + " seats, ends 2026-11-01"
        self.assertEqual(len(expected), 80)
        self.assertEqual(lines[0]["description"], expected)
        self.assertEqual(lines[1]["description"], expected)

    def test_description_81_chars_shortened_date_intact(self):
        long_plan = "A" * 58
        sub = _sub(plan_name=long_plan, seat_price_cents=100)
        lines = prorate_seats(sub, {"name": "Pro", "seat_price_cents": 1000}, _days_left(30))
        desc = lines[0]["description"]
        self.assertLessEqual(len(desc), 80)
        self.assertEqual(desc, "A" * 57 + " seats, ends 2026-11-01")

    def test_output_order_credit_then_charge(self):
        sub = _sub(seat_price_cents=100)
        lines = prorate_seats(sub, {"name": "Pro", "seat_price_cents": 1000}, _days_left(30))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])

    def test_seats_field_is_ignored(self):
        new = {"name": "Pro", "seat_price_cents": 2000}
        a = prorate_seats(_sub(seats=99, billable_seats=2), new, _days_left(7))
        b = prorate_seats(_sub(seats=2, billable_seats=2), new, _days_left(7))
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()