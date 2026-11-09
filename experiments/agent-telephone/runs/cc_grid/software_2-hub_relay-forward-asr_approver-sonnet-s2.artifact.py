"""Seat-upgrade proration.

Assumptions (from the PM, to be confirmed with the client):
- Equal price means no lines (only a strictly higher new price is prorated).
- amount_cents is a positive magnitude for both credits and charges.
- days_left = (period_end - changed_at).days, so partial days are floored,
  clamped to 0..30. days_left of 0 means no lines.
- Statuses other than "trialing" are prorated.
- VAT = charge * 21 // 100 (floored). Any non-empty vat_id means reverse
  charge, so VAT is 0. Credits always have VAT 0.
- billable_seats <= 0 means no lines. A missing or non-int value raises
  ValueError. `seats` and `legacy_discount` are ignored.
- Naive datetimes raise ValueError. The date in descriptions is period_end's
  own calendar date in its own timezone.
- Credit descriptions name the old plan, charge descriptions the new plan.
- Credits are rounded up, charges down, once, on price * seats * days_left / 30.
  Lines under 50 cents (net) are dropped independently.
- Credit approver is Win Tee Fung Tao, or Ramón Etxeberria-Goñi when the
  credit is strictly above 50000 cents. Charges have approved_by None.
"""
import unittest
from datetime import datetime, timedelta, timezone

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
BIG_CREDIT_CENTS = 50000
VAT_PERCENT = 21
MAX_DESC = 80


def _describe(prefix: str, plan: str, date: str) -> str:
    suffix = f" until {date}"
    budget = MAX_DESC - len(prefix) - len(suffix)
    if len(plan) > budget:
        plan = plan[: max(budget - 1, 0)] + "\u2026"
    return f"{prefix}{plan}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription["period_end"]
    for dt in (period_end, changed_at):
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError("datetimes must be timezone-aware")
    seats = subscription.get("billable_seats")
    if not isinstance(seats, int) or isinstance(seats, bool):
        raise ValueError("billable_seats must be an int")
    if subscription["status"] == "trialing":
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price or seats <= 0:
        return []
    days_left = max(0, min(PERIOD_DAYS, (period_end - changed_at).days))
    if days_left == 0:
        return []

    date = period_end.strftime("%Y-%m-%d")
    sub_id = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit unused ", subscription["plan_name"], date),
            "approved_by": ("Ramón Etxeberria-Goñi" if credit > BIG_CREDIT_CENTS
                            else "Win Tee Fung Tao"),
        })

    charge = (new_price * seats * days_left) // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        vat = 0 if subscription.get("vat_id") else charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe("Charge unused ", new_plan["name"], date),
            "approved_by": None,
        })
    return lines


class ProrateTests(unittest.TestCase):
    END = datetime(2026, 11, 1, tzinfo=timezone.utc)
    NOW = END - timedelta(days=15)

    def sub(self, **kw):
        s = {"id": "s1", "status": "active", "plan_name": "Basic",
             "seat_price_cents": 1000, "seats": 9, "billable_seats": 3,
             "vat_id": "", "period_end": self.END, "legacy_discount": 50}
        s.update(kw)
        return s

    def new(self, price=1500, name="Pro"):
        return {"name": name, "seat_price_cents": price}

    def test_basic(self):
        c, ch = prorate_seats(self.sub(), self.new(), self.NOW)
        self.assertEqual((c["kind"], c["amount_cents"], c["vat_cents"]), ("credit", 1500, 0))
        self.assertEqual((ch["kind"], ch["amount_cents"], ch["vat_cents"]), ("charge", 2250, 472))
        self.assertIsNone(ch["approved_by"])
        self.assertEqual(c["approved_by"], "Win Tee Fung Tao")
        self.assertIn("2026-11-01", c["description"])

    def test_approver_threshold(self):
        # old price * 1 seat * 30 days / 30 = price
        for price, who in ((50000, "Win Tee Fung Tao"), (50001, "Ramón Etxeberria-Goñi")):
            s = self.sub(seat_price_cents=price, billable_seats=1)
            r = prorate_seats(s, self.new(60000), self.END - timedelta(days=30))
            self.assertEqual(r[0]["approved_by"], who)

    def test_min_line(self):
        s = self.sub(seat_price_cents=49, billable_seats=1)
        r = prorate_seats(s, self.new(100), self.END - timedelta(days=30))
        self.assertEqual([x["kind"] for x in r], ["charge"])
        s = self.sub(seat_price_cents=50, billable_seats=1)
        r = prorate_seats(s, self.new(51), self.END - timedelta(days=30))
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])

    def test_vat_id(self):
        r = prorate_seats(self.sub(vat_id="PT123"), self.new(), self.NOW)
        self.assertEqual(r[1]["vat_cents"], 0)

    def test_no_lines(self):
        self.assertEqual(prorate_seats(self.sub(status="trialing"), self.new(), self.NOW), [])
        self.assertEqual(prorate_seats(self.sub(), self.new(500), self.NOW), [])
        self.assertEqual(prorate_seats(self.sub(), self.new(1000), self.NOW), [])
        self.assertEqual(prorate_seats(self.sub(), self.new(), self.END), [])
        self.assertEqual(prorate_seats(self.sub(), self.new(), self.END + timedelta(days=1)), [])

    def test_long_name(self):
        r = prorate_seats(self.sub(plan_name="X" * 100), self.new(name="Y" * 100), self.NOW)
        for line in r:
            self.assertLessEqual(len(line["description"]), 80)
            self.assertTrue(line["description"].endswith("2026-11-01"))

    def test_ignored_fields_and_ints(self):
        a = prorate_seats(self.sub(), self.new(), self.NOW)
        b = prorate_seats(self.sub(seats=99, legacy_discount=0), self.new(), self.NOW)
        self.assertEqual(a, b)
        for line in a:
            self.assertIs(type(line["amount_cents"]), int)
            self.assertIs(type(line["vat_cents"]), int)

    def test_errors(self):
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(billable_seats=None), self.new(), self.NOW)
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), self.new(), datetime(2026, 10, 1))


if __name__ == "__main__":
    unittest.main()