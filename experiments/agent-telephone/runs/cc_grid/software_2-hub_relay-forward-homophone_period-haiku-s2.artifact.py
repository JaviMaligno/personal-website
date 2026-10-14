"""
Seat-upgrade proration for Fernhollow Studios.

Assumptions (decided by tech lead, not confirmed by client unless stated):
1. Currency is EUR. A credit goes to Ramon Etxeberria-Goni only if amount_cents > 50000; exactly 50000 goes to Nguyen Thi Phuong Thao.
2. Unused days are whole days between changed_at and period_end, computed on UTC instants so DST shifts do not skew the count. The date in descriptions uses period_end's own timezone. If changed_at >= period_end, no lines are returned.
3. Arithmetic uses fractions.Fraction. Credit rounds up to the next cent, charge rounds down.
4. Lines with a net amount under 50 cents are dropped before VAT. CONFLICT: dropping small credits can keep a credit the customer is owed unpaid, which conflicts with the "never round in our favour" principle. Client must confirm.
5. VAT on charges is floor(amount_cents * 21 / 100), or 0 when vat_id is truthy. Credits always have vat_cents 0.
6. status == "trialing" returns no lines. new price < old price returns no lines. Equal price is not a downgrade.
7. Descriptions are at most 80 Unicode code points. Long plan names are truncated with an ellipsis, and the date is always kept. If the template with an empty name exceeds 80, ValueError is raised.
8. Credits come before charges. legacy_discount is ignored. billable_seats is used, never seats.
9. No clamp is applied to unused days. A period_end more than 13 days after changed_at would produce a credit larger than one period. The brief does not address this; client should confirm.

Status: this module has not been executed in this environment. The unit tests at the bottom are written but unverified.
"""

from datetime import timedelta, timezone
from fractions import Fraction
import unittest

CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
LARGE_CREDIT_THRESHOLD_CENTS = 50000
MIN_LINE_CENTS = 50
PERIOD_DAYS = 13
VAT_PERCENT = 21
MAX_DESCRIPTION_LEN = 80
ELLIPSIS = "…"


def _ceil_fraction(f):
    return -((-f.numerator) // f.denominator)


def _floor_fraction(f):
    return f.numerator // f.denominator


def _describe(prefix, name, suffix):
    base_len = len(prefix) + len(suffix)
    if base_len > MAX_DESCRIPTION_LEN:
        raise ValueError("description template exceeds 80 characters")
    room = MAX_DESCRIPTION_LEN - base_len
    if len(name) > room:
        name = "" if room == 0 else name[: room - 1] + ELLIPSIS
    return prefix + name + suffix


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

    delta = period_end.astimezone(timezone.utc) - changed_at.astimezone(timezone.utc)
    days = delta // timedelta(days=1)
    seats = subscription["billable_seats"]
    sub_id = subscription["id"]
    date_str = period_end.strftime("%Y-%m-%d")
    vat_id = subscription.get("vat_id")

    lines = []

    credit_cents = _ceil_fraction(Fraction(old_price * seats * days, PERIOD_DAYS))
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
            "description": _describe(
                "Unused ", subscription["plan_name"], f" seats to {date_str}"
            ),
            "approved_by": approver,
        })

    charge_cents = _floor_fraction(Fraction(new_price * seats * days, PERIOD_DAYS))
    if charge_cents >= MIN_LINE_CENTS:
        vat_cents = 0 if vat_id else charge_cents * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _describe("", new_plan["name"], f" seats to {date_str}"),
            "approved_by": None,
        })

    return lines


class _ProrateTests(unittest.TestCase):
    END = None

    @classmethod
    def setUpClass(cls):
        from datetime import datetime
        cls.END = datetime(2026, 11, 30, tzinfo=timezone.utc)

    def sub(self, **over):
        base = {
            "id": "sub_1",
            "status": "active",
            "plan_name": "Basic",
            "seat_price_cents": 1000,
            "seats": 99,
            "billable_seats": 3,
            "vat_id": None,
            "period_end": self.END,
        }
        base.update(over)
        return base

    def plan(self, price=1500, name="Pro"):
        return {"name": name, "seat_price_cents": price}

    def test_credit_rounds_up_and_charge_rounds_down(self):
        changed = self.END - timedelta(days=5)
        lines = prorate_seats(self.sub(), self.plan(), changed)
        self.assertEqual(lines[0]["kind"], "credit")
        self.assertEqual(lines[0]["amount_cents"], 1154)
        self.assertEqual(lines[1]["kind"], "charge")
        self.assertEqual(lines[1]["amount_cents"], 1730)

    def test_under_50_cents_is_skipped(self):
        changed = self.END - timedelta(days=2)
        lines = prorate_seats(self.sub(seat_price_cents=100, billable_seats=1),
                              self.plan(price=100), changed)
        self.assertEqual(lines, [])

    def test_reverse_charge_and_vat(self):
        changed = self.END - timedelta(days=5)
        lines = prorate_seats(self.sub(), self.plan(), changed)
        self.assertEqual(lines[1]["vat_cents"], 363)
        self.assertEqual(lines[0]["vat_cents"], 0)
        lines = prorate_seats(self.sub(vat_id="DE123"), self.plan(), changed)
        self.assertEqual(lines[1]["vat_cents"], 0)

    def test_trialing_returns_nothing(self):
        changed = self.END - timedelta(days=5)
        self.assertEqual(prorate_seats(self.sub(status="trialing"), self.plan(), changed), [])

    def test_downgrade_returns_nothing_and_equal_is_not_downgrade(self):
        changed = self.END - timedelta(days=5)
        self.assertEqual(prorate_seats(self.sub(), self.plan(price=900), changed), [])
        lines = prorate_seats(self.sub(), self.plan(price=1000), changed)
        self.assertEqual(len(lines), 2)

    def test_approval_threshold_boundary(self):
        changed = self.END - timedelta(days=13)
        exact = prorate_seats(self.sub(seat_price_cents=50000, billable_seats=1),
                              self.plan(price=50000), changed)
        self.assertEqual(exact[0]["amount_cents"], 50000)
        self.assertEqual(exact[0]["approved_by"], CREDIT_APPROVER)
        over = prorate_seats(self.sub(seat_price_cents=50001, billable_seats=1),
                             self.plan(price=50001), changed)
        self.assertEqual(over[0]["amount_cents"], 50001)
        self.assertEqual(over[0]["approved_by"], LARGE_CREDIT_APPROVER)
        self.assertIsNone(over[1]["approved_by"])

    def test_long_name_truncated_and_date_kept(self):
        long_name = "A" * 100
        changed = self.END - timedelta(days=5)
        lines = prorate_seats(self.sub(plan_name=long_name), self.plan(name=long_name),
                              changed)
        for line in lines:
            self.assertLessEqual(len(line["description"]), 80)
            self.assertIn("2026-11-30", line["description"])
            self.assertIn("…", line["description"])
        self.assertTrue(lines[0]["description"].endswith(" seats to 2026-11-30"))

    def test_template_too_long_raises(self):
        with self.assertRaises(ValueError):
            _describe("x" * 80, "name", " seats to 2026-11-30")


if __name__ == "__main__":
    unittest.main()