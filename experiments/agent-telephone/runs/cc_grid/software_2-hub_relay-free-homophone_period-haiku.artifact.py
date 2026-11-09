"""Seat-upgrade proration for Fernhollow Studios.

Assumptions for client confirmation:
1. All amounts are EUR cents.
2. Unused days = whole days, floored: (period_end - changed_at) // 1 day.
3. Line amount = billable_seats * seat_price_cents * unused_days / 13, computed exactly.
4. Credits round up (ceiling) and charges round down (floor), both before VAT.
5. Charge VAT = floor(amount * 21 / 100). Reverse charge (VAT 0) when vat_id is non-empty. Credits carry VAT 0.
6. The EUR 500 threshold is applied to the credit amount: strictly greater than 50000 cents goes to Ramón; 50000 exactly goes to Thảo.
7. Equal price is prorated. A downgrade is a strictly lower new price, which returns no lines.
8. Statuses other than "trialing" (canceled, past_due, etc.) are prorated normally.
9. vat_id that is None, "" or whitespace-only counts as absent, so VAT is charged.
10. amount_cents is the positive pre-VAT amount; direction is carried by kind.
11. Unused days are not capped at 13, because no period start is supplied.
12. legacy_discount is ignored.
13. Descriptions read "Credit for <plan> (ends YYYY-MM-DD)" or "Charge for <plan> (ends YYYY-MM-DD)". If over 80 characters, the plan name is cut to 48 characters plus "..." and the full date is kept.

Test status: the tests below were written but not executed, because no execution tool was available. Run them with: python -m unittest <this file>
"""

import unittest
from datetime import datetime, timedelta, timezone

CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
LARGE_CREDIT_THRESHOLD_CENTS = 50000
MIN_LINE_CENTS = 50
PERIOD_DAYS = 13
VAT_PERCENT = 21
MAX_DESCRIPTION = 80


def _description(label, plan_name, period_end):
    date = period_end.strftime("%Y-%m-%d")
    prefix = f"{label} for "
    suffix = f" (ends {date})"
    room = MAX_DESCRIPTION - len(prefix) - len(suffix)
    if len(plan_name) > room:
        plan_name = plan_name[: room - 3] + "..."
    return f"{prefix}{plan_name}{suffix}"


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

    unused_days = (period_end - changed_at) // timedelta(days=1)
    if unused_days <= 0:
        return []

    seats = subscription["billable_seats"]
    credit_num = seats * old_price * unused_days
    charge_num = seats * new_price * unused_days
    credit_cents = -(-credit_num // PERIOD_DAYS)  # ceiling
    charge_cents = charge_num // PERIOD_DAYS      # floor

    has_vat_id = bool((subscription.get("vat_id") or "").strip())
    sub_id = subscription["id"]
    lines = []

    if credit_cents >= MIN_LINE_CENTS:
        approver = (
            LARGE_CREDIT_APPROVER
            if credit_cents > LARGE_CREDIT_THRESHOLD_CENTS
            else CREDIT_APPROVER
        )
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _description("Credit", subscription["plan_name"], period_end),
            "approved_by": approver,
        })

    if charge_cents >= MIN_LINE_CENTS:
        vat_cents = 0 if has_vat_id else charge_cents * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _description("Charge", new_plan["name"], period_end),
            "approved_by": None,
        })

    return lines


PE = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


def _sub(**overrides):
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Studio Pro",
        "seat_price_cents": 1300,
        "seats": 10,
        "billable_seats": 10,
        "vat_id": None,
        "period_end": PE,
    }
    base.update(overrides)
    return base


def _plan(price, name="Studio Max"):
    return {"name": name, "seat_price_cents": price}


def _at(days):
    return PE - timedelta(days=days)


class ProrateSeatsTests(unittest.TestCase):

    def test_thirteen_day_arithmetic(self):
        lines = prorate_seats(_sub(), _plan(2600), _at(6))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        self.assertEqual(lines[0]["amount_cents"], 6000)  # 10*1300*6/13
        self.assertEqual(lines[1]["amount_cents"], 12000)  # 10*2600*6/13
        self.assertEqual(lines[1]["vat_cents"], 2520)

    def test_full_period_gives_full_seat_price(self):
        lines = prorate_seats(_sub(), _plan(2600), _at(13))
        self.assertEqual(lines[0]["amount_cents"], 13000)
        self.assertEqual(lines[1]["amount_cents"], 26000)

    def test_credit_ceiling_and_charge_floor(self):
        lines = prorate_seats(_sub(billable_seats=10, seat_price_cents=100), _plan(200), _at(1))
        self.assertEqual(lines[0]["amount_cents"], 77)   # 1000/13 = 76.92 -> 77
        self.assertEqual(lines[1]["amount_cents"], 153)  # 2000/13 = 153.85 -> 153

    def test_fifty_cent_skip_is_per_line(self):
        # Credit ceil(638/13) = 50 is kept; charge floor(638/13) = 49 is dropped.
        lines = prorate_seats(_sub(billable_seats=1, seat_price_cents=638), _plan(638), _at(1))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "credit")
        self.assertEqual(lines[0]["amount_cents"], 50)

    def test_small_credit_dropped_charge_kept(self):
        lines = prorate_seats(_sub(billable_seats=1, seat_price_cents=26), _plan(13000), _at(1))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 1000)
        self.assertEqual(lines[0]["vat_cents"], 210)

    def test_downgrade_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(1000), _at(6)), [])

    def test_trialing_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(2600), _at(6)), [])

    def test_changed_at_at_period_end_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(2600), PE), [])

    def test_changed_at_after_period_end_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(2600), PE + timedelta(days=1)), [])

    def test_equal_price_is_prorated(self):
        lines = prorate_seats(_sub(), _plan(1300), _at(6))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        self.assertEqual(lines[1]["amount_cents"], 6000)

    def test_past_due_is_prorated(self):
        lines = prorate_seats(_sub(status="past_due"), _plan(2600), _at(6))
        self.assertEqual(len(lines), 2)

    def test_reverse_charge_when_vat_id_set(self):
        lines = prorate_seats(_sub(vat_id="DE123456789"), _plan(2600), _at(6))
        self.assertEqual(lines[1]["vat_cents"], 0)
        self.assertEqual(lines[0]["vat_cents"], 0)

    def test_empty_vat_id_charges_vat(self):
        lines = prorate_seats(_sub(vat_id=""), _plan(2600), _at(6))
        self.assertEqual(lines[1]["vat_cents"], 2520)

    def test_ramon_threshold_exactly_50000_goes_to_thao(self):
        lines = prorate_seats(_sub(billable_seats=1, seat_price_cents=650000), _plan(650000), _at(1))
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], "Nguyễn Thị Phương Thảo")

    def test_ramon_threshold_50001_goes_to_ramon(self):
        lines = prorate_seats(_sub(billable_seats=1, seat_price_cents=650013), _plan(650013), _at(1))
        self.assertEqual(lines[0]["amount_cents"], 50001)
        self.assertEqual(lines[0]["approved_by"], "Ramón Etxeberria-Goñi")

    def test_credit_before_charge(self):
        lines = prorate_seats(_sub(), _plan(2600), _at(6))
        self.assertEqual(lines[0]["kind"], "credit")
        self.assertEqual(lines[1]["kind"], "charge")
        self.assertIsNone(lines[1]["approved_by"])
        self.assertEqual(lines[0]["vat_cents"], 0)

    def test_description_length_and_date_preserved(self):
        long_name = "X" * 200
        lines = prorate_seats(
            _sub(plan_name=long_name), _plan(2600, name=long_name), _at(6)
        )
        for line in lines:
            self.assertLessEqual(len(line["description"]), 80)
            self.assertIn("2026-10-31", line["description"])
        short = prorate_seats(_sub(), _plan(2600), _at(6))
        self.assertIn("Studio Pro", short[0]["description"])
        self.assertIn("Studio Max", short[1]["description"])

    def test_legacy_discount_ignored(self):
        plain = prorate_seats(_sub(), _plan(2600), _at(6))
        with_discount = prorate_seats(_sub(legacy_discount=50), _plan(2600), _at(6))
        self.assertEqual(plain, with_discount)


if __name__ == "__main__":
    unittest.main()