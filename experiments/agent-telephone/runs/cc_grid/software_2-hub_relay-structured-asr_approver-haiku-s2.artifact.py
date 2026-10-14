"""Seat-upgrade proration for Fernhollow Studios (client contact: Ingrid).

Implements R1-R25. Amounts are EUR cents, integer arithmetic only.

Flags for client and product manager confirmation:
- R9 vs R8 conflict: R9 drops any line under 50 cents, including credits. Dropping a
  credit keeps money from the customer, which conflicts with R8 (rounding never favours
  the company). Applied to both credits and charges as written. Ingrid to confirm.
- R19: proration uses exact elapsed microseconds, not whole days left. Client may have
  meant whole days.
- R23: status values other than "trialing" are prorated normally, since the client gave
  no list of valid statuses. Ingrid to confirm.
- R18: all amounts are EUR.
- R20: the 50000-cent threshold is strict (credit > 50000 uses the large approver).
- R21: the 50-cent minimum is checked before VAT, and exactly 50 is kept.
- R22: equal price is a no-op and returns [].
- R24: charge VAT = floor(net * 21 / 100) on the rounded-down net charge.
- R25: description templates. The plan name is truncated with "..." when the text
  exceeds 80 code points. The date comes from period_end in its own timezone.
  If even an empty name cannot fit, ValueError is raised. If only the "..." cannot
  fit alongside an empty name, the description is returned without the name and
  without "...".

The unit tests at the bottom of this file were written but NOT executed in this session.
Run with: python3 -I thismodule.py
"""

from datetime import datetime, timedelta, timezone
import unittest

PERIOD_MICROS = 30 * 86400 * 10**6
MICRO = timedelta(microseconds=1)
MIN_LINE_CENTS = 50
LARGE_CREDIT_CENTS = 50000
APPROVER_STANDARD = "Win Tee Fung Tao"
APPROVER_LARGE = "Ramón Etxeberria-Goñi"
VAT_PERCENT = 21
DESC_MAX = 80


def _check_aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _check_cents(value, name):
    if type(value) is not int:
        raise TypeError(f"{name} must be an int (cents)")


def _check_text(value, name):
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a str")


def _description(prefix, plan_name, suffix):
    if len(prefix) + len(suffix) > DESC_MAX:
        raise ValueError("description cannot fit even with an empty plan name")
    full = prefix + plan_name + suffix
    if len(full) <= DESC_MAX:
        return full
    keep = DESC_MAX - len(prefix) - len(suffix) - 3
    if keep < 0:
        return prefix + suffix
    return prefix + plan_name[:keep] + "..." + suffix


def prorate_seats(subscription, new_plan, changed_at):
    _check_aware(changed_at, "changed_at")
    period_end = subscription["period_end"]
    _check_aware(period_end, "period_end")

    if subscription["status"] == "trialing":
        return []

    seats = subscription["billable_seats"]
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    old_name = subscription["plan_name"]
    new_name = new_plan["name"]
    _check_cents(seats, "billable_seats")
    _check_cents(old_price, "seat_price_cents")
    _check_cents(new_price, "seat_price_cents")
    _check_text(old_name, "plan_name")
    _check_text(new_name, "name")
    if seats < 0:
        raise ValueError("billable_seats must not be negative")
    if seats == 0:
        return []

    unused = (period_end - changed_at) // MICRO
    if unused < 0 or unused > PERIOD_MICROS:
        raise ValueError("changed_at must fall within the 30 days before period_end")
    if unused == 0:
        return []
    if new_price <= old_price:
        return []

    old_total = old_price * seats
    new_total = new_price * seats
    credit = -((-(old_total * unused)) // PERIOD_MICROS)
    charge = (new_total * unused) // PERIOD_MICROS

    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    if credit >= MIN_LINE_CENTS:
        approver = APPROVER_LARGE if credit > LARGE_CREDIT_CENTS else APPROVER_STANDARD
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit: ", old_name, f" seats, to {date_str}"),
            "approved_by": approver,
        })

    if charge >= MIN_LINE_CENTS:
        vat = 0 if subscription["vat_id"] else (charge * VAT_PERCENT) // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description("Charge: ", new_name, f" seats, to {date_str}"),
            "approved_by": None,
        })

    return lines


class ProrateTests(unittest.TestCase):
    END = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)

    def sub(self, **kw):
        s = {
            "id": "sub_1",
            "status": "active",
            "plan_name": "Team",
            "seat_price_cents": 1000,
            "seats": 1,
            "billable_seats": 1,
            "vat_id": "",
            "period_end": self.END,
            "legacy_discount": 99,
        }
        s.update(kw)
        return s

    def plan(self, price, name="Pro"):
        return {"name": name, "seat_price_cents": price}

    def at(self, days_left):
        return self.END - timedelta(days=days_left)

    def test_r4_description_has_plan_and_date(self):
        lines = prorate_seats(self.sub(), self.plan(2000, "Studio"), self.at(15))
        self.assertIn("Team", lines[0]["description"])
        self.assertIn("Studio", lines[1]["description"])
        self.assertIn("2026-11-01", lines[0]["description"])

    def test_r5_bills_billable_seats_not_seats(self):
        lines = prorate_seats(
            self.sub(seats=10, billable_seats=2), self.plan(2000), self.at(30)
        )
        self.assertEqual(lines[0]["amount_cents"], 2000)
        self.assertEqual(lines[1]["amount_cents"], 4000)

    def test_r6_30_day_rule(self):
        lines = prorate_seats(
            self.sub(seats=5, billable_seats=5), self.plan(2000), self.at(15)
        )
        self.assertEqual(lines[0]["kind"], "credit")
        self.assertEqual(lines[0]["amount_cents"], 2500)
        self.assertEqual(lines[1]["kind"], "charge")
        self.assertEqual(lines[1]["amount_cents"], 5000)

    def test_r7_downgrade_returns_empty(self):
        self.assertEqual(prorate_seats(self.sub(), self.plan(500), self.at(15)), [])

    def test_r22_equal_price_returns_empty(self):
        self.assertEqual(prorate_seats(self.sub(), self.plan(1000), self.at(15)), [])

    def test_r8_rounding_directions(self):
        # 1000 * 10/30 = 333.33 -> credit rounds up to 334
        # 2000 * 10/30 = 666.67 -> charge rounds down to 666
        lines = prorate_seats(self.sub(), self.plan(2000), self.at(10))
        self.assertEqual(lines[0]["amount_cents"], 334)
        self.assertEqual(lines[1]["amount_cents"], 666)

    def test_r9_49_cents_skipped(self):
        lines = prorate_seats(self.sub(seat_price_cents=49), self.plan(100), self.at(30))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")

    def test_r9_50_cents_kept(self):
        lines = prorate_seats(self.sub(seat_price_cents=50), self.plan(100), self.at(30))
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["amount_cents"], 50)

    def test_r10_vat_with_and_without_vat_id(self):
        lines = prorate_seats(self.sub(), self.plan(3000), self.at(15))
        self.assertEqual(lines[0]["vat_cents"], 0)
        self.assertEqual(lines[1]["amount_cents"], 1500)
        self.assertEqual(lines[1]["vat_cents"], 315)

        lines = prorate_seats(self.sub(vat_id="DE123"), self.plan(3000), self.at(15))
        self.assertEqual(lines[0]["vat_cents"], 0)
        self.assertEqual(lines[1]["vat_cents"], 0)

    def test_r11_trialing_returns_empty(self):
        self.assertEqual(
            prorate_seats(self.sub(status="trialing"), self.plan(2000), self.at(15)), []
        )

    def test_r12_truncation_keeps_date(self):
        lines = prorate_seats(
            self.sub(plan_name="X" * 200), self.plan(2000), self.at(15)
        )
        desc = lines[0]["description"]
        self.assertLessEqual(len(desc), 80)
        self.assertIn("...", desc)
        self.assertTrue(desc.endswith("seats, to 2026-11-01"))

    def test_r25_date_in_own_timezone(self):
        end = datetime(2026, 11, 1, 1, 0, tzinfo=timezone(timedelta(hours=5)))
        lines = prorate_seats(
            self.sub(period_end=end), self.plan(2000), end - timedelta(days=15)
        )
        self.assertIn("to 2026-11-01", lines[0]["description"])

    def test_r13_threshold_at_50000(self):
        lines = prorate_seats(
            self.sub(seat_price_cents=50000), self.plan(60000), self.at(30)
        )
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], "Win Tee Fung Tao")

    def test_r13_threshold_at_50001(self):
        lines = prorate_seats(
            self.sub(seat_price_cents=50001), self.plan(60000), self.at(30)
        )
        self.assertEqual(lines[0]["amount_cents"], 50001)
        self.assertEqual(lines[0]["approved_by"], "Ramón Etxeberria-Goñi")
        self.assertIsNone(lines[1]["approved_by"])

    def test_r15_credit_before_charge(self):
        lines = prorate_seats(self.sub(), self.plan(3000), self.at(15))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])

    def test_r16_all_amounts_are_int(self):
        lines = prorate_seats(self.sub(), self.plan(3000), self.at(15))
        for line in lines:
            self.assertIs(type(line["amount_cents"]), int)
            self.assertIs(type(line["vat_cents"]), int)

    def test_r2_naive_datetime_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), self.plan(2000), datetime(2026, 10, 20))

    def test_r23_window_violations_raise(self):
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), self.plan(2000), self.at(31))
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), self.plan(2000), self.END + timedelta(days=1))

    def test_r23_changed_at_equals_period_end_empty(self):
        self.assertEqual(prorate_seats(self.sub(), self.plan(2000), self.END), [])


if __name__ == "__main__":
    unittest.main()