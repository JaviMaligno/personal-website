# -*- coding: utf-8 -*-
"""Seat upgrade proration for Fernhollow Studios.

Assumptions:
- A naive changed_at or period_end raises ValueError before anything else,
  even for trialing subscriptions.
- The 50-cent skip applies to each line independently, so a skipped credit
  does not suppress the charge (and vice versa).
- Equal per-seat prices are not a downgrade: only a strictly cheaper new
  plan returns no lines.
- A blank or whitespace-only vat_id counts as no vat_id.
- Only the plan name is shortened (with "...") when a description exceeds
  80 characters; the date is never cut.
- Status "trialing" is matched case-insensitively, ignoring surrounding
  whitespace.
"""
import unittest
from datetime import datetime, timedelta, timezone

PERIOD = 30 * 86400 * 1_000_000  # microseconds in a billing period
MIN_CENTS = 50
BIG_CREDIT = 50000
APPROVER = "Win Tee Fung Tao"
SENIOR_APPROVER = "Ramón Etxeberria-Goñi"
MAX_DESC = 80


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _describe(prefix, name, date):
    suffix = f" until {date}"
    room = MAX_DESC - len(prefix) - len(suffix)
    if len(name) > room:
        if room > 3:
            name = name[: room - 3].rstrip() + "..."
        else:
            name = name[: max(room, 0)]
    return f"{prefix}{name}{suffix}"


def _has_vat_id(v):
    if isinstance(v, str):
        return bool(v.strip())
    return bool(v)


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription["period_end"]
    if not _aware(changed_at) or not _aware(period_end):
        raise ValueError("datetimes must be timezone-aware")

    if str(subscription.get("status", "")).strip().lower() == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    seats = subscription["billable_seats"]
    if seats <= 0:
        return []

    micro = (period_end - changed_at) // timedelta(microseconds=1)
    if micro <= 0:
        return []
    micro = min(micro, PERIOD)

    credit_amount = -(-(seats * old_price * micro) // PERIOD)  # ceil
    charge_amount = (seats * new_price * micro) // PERIOD  # floor

    date = period_end.strftime("%Y-%m-%d")
    sub_id = subscription["id"]
    lines = []

    if credit_amount >= MIN_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_amount,
            "vat_cents": 0,
            "description": _describe("Credit ", str(subscription["plan_name"]), date),
            "approved_by": SENIOR_APPROVER if credit_amount > BIG_CREDIT else APPROVER,
        })

    if charge_amount >= MIN_CENTS:
        vat = 0 if _has_vat_id(subscription.get("vat_id")) else charge_amount * 21 // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_amount,
            "vat_cents": vat,
            "description": _describe("Charge ", str(new_plan["name"]), date),
            "approved_by": None,
        })

    return lines


class ProrateTests(unittest.TestCase):
    END = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)

    def sub(self, **kw):
        s = {"id": "s1", "status": "active", "plan_name": "Basic", "seat_price_cents": 1000,
             "seats": 10, "billable_seats": 10, "vat_id": None, "period_end": self.END}
        s.update(kw)
        return s

    def plan(self, price=1500, name="Pro"):
        return {"name": name, "seat_price_cents": price}

    def at(self, days):
        return self.END - timedelta(days=days)

    def test_worked_example(self):
        r = prorate_seats(self.sub(), self.plan(), self.at(15))
        self.assertEqual([l["kind"] for l in r], ["credit", "charge"])
        self.assertEqual(r[0]["amount_cents"], 5000)
        self.assertEqual(r[0]["vat_cents"], 0)
        self.assertEqual(r[0]["approved_by"], "Win Tee Fung Tao")
        self.assertEqual(r[1]["amount_cents"], 7500)
        self.assertEqual(r[1]["vat_cents"], 1575)
        self.assertIsNone(r[1]["approved_by"])
        self.assertIn("2026-10-31", r[0]["description"])

    def test_rounding(self):
        r = prorate_seats(self.sub(seats=1, billable_seats=1, seat_price_cents=1001),
                          self.plan(1501), self.at(10))
        self.assertEqual((r[0]["amount_cents"], r[1]["amount_cents"]), (334, 500))

    def test_boundary_49_50(self):
        s = self.sub(billable_seats=1, seat_price_cents=49)
        self.assertEqual(prorate_seats(s, self.plan(49), self.at(30)), [])
        r = prorate_seats(s, self.plan(60), self.at(30))
        self.assertEqual([l["kind"] for l in r], ["charge"])
        s = self.sub(billable_seats=1, seat_price_cents=50)
        r = prorate_seats(s, self.plan(50), self.at(30))
        self.assertEqual([l["amount_cents"] for l in r], [50, 50])

    def test_boundary_50000(self):
        s = self.sub(billable_seats=1, seat_price_cents=50000)
        r = prorate_seats(s, self.plan(50000), self.at(30))
        self.assertEqual(r[0]["approved_by"], "Win Tee Fung Tao")
        self.assertEqual(r[1]["vat_cents"], 10500)
        s = self.sub(billable_seats=1, seat_price_cents=50001)
        r = prorate_seats(s, self.plan(50001), self.at(30))
        self.assertEqual(r[0]["approved_by"], "Ramón Etxeberria-Goñi")

    def test_long_name(self):
        r = prorate_seats(self.sub(plan_name="A" * 100), self.plan(name="B" * 100), self.at(15))
        for l in r:
            self.assertLessEqual(len(l["description"]), 80)
            self.assertTrue(l["description"].endswith("2026-10-31"))
        self.assertIn("A", r[0]["description"])
        self.assertIn("B", r[1]["description"])

    def test_billable_not_seats(self):
        r = prorate_seats(self.sub(seats=99, billable_seats=10), self.plan(), self.at(15))
        self.assertEqual(r[0]["amount_cents"], 5000)
        self.assertEqual(prorate_seats(self.sub(billable_seats=0), self.plan(), self.at(15)), [])

    def test_skips_and_clamp(self):
        self.assertEqual(prorate_seats(self.sub(status="trialing"), self.plan(), self.at(15)), [])
        self.assertEqual(prorate_seats(self.sub(), self.plan(999), self.at(15)), [])
        self.assertEqual(prorate_seats(self.sub(), self.plan(), self.END), [])
        self.assertEqual(prorate_seats(self.sub(), self.plan(), self.at(-1)), [])
        r = prorate_seats(self.sub(), self.plan(), self.at(60))
        self.assertEqual(r[0]["amount_cents"], 10000)

    def test_equal_price_not_downgrade(self):
        r = prorate_seats(self.sub(), self.plan(1000), self.at(15))
        self.assertEqual(len(r), 2)

    def test_vat_id(self):
        r = prorate_seats(self.sub(vat_id="PT123"), self.plan(), self.at(15))
        self.assertEqual(r[1]["vat_cents"], 0)
        r = prorate_seats(self.sub(vat_id="  "), self.plan(), self.at(15))
        self.assertEqual(r[1]["vat_cents"], 1575)

    def test_naive_and_no_mutation(self):
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), self.plan(), datetime(2026, 10, 1))
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(period_end=datetime(2026, 10, 31)), self.plan(), self.at(1))
        s, p = self.sub(), self.plan()
        s0, p0 = dict(s), dict(p)
        prorate_seats(s, p, self.at(15))
        self.assertEqual((s, p), (s0, p0))


if __name__ == "__main__":
    unittest.main()