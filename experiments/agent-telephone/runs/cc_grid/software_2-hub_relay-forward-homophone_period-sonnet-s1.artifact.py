"""Seat-upgrade proration for Fernhollow Studios.

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list[dict]

Assumptions (to relay to the client):
 1. Skipping small lines: lines are rounded first, then any line under 50
    cents is dropped (50 is kept). Dropping a small credit favours the
    company, not the customer.
 2. Equal-price plan swaps with a different name are processed as a normal
    change (credit old, charge new). Identical plan name and price returns [].
 3. VAT is floor(21% of the net charge amount), i.e. rounded down to the cent.
    This deviates from the house half-up rule because the brief says never to
    round in the company's favour only for credits/charges as specified;
    PM chose floor for VAT. Credits carry 0 VAT. A non-blank vat_id means
    reverse charge (VAT 0).
 4. Only status "trialing" is treated specially (returns []). Every other
    status (active, past_due, canceled, ...) is prorated normally.
 5. A billing period is always 13 days. days_left is the calendar-date
    difference in period_end's timezone, clamped to 0..13.
 6. Only billable_seats is used; seats and legacy_discount are ignored.
 7. Downgrades (new price < old price) return [].
 8. Credit above 50000 cents (strictly) is approved by Ramon Etxeberria-Goni,
    otherwise by Nguyen Thi Phuong Thao (exact Unicode names in code).
 9. Descriptions are at most 80 chars; only the plan name is shortened, with
    ASCII "...". The YYYY-MM-DD period end date is never cut.
10. Naive datetimes raise ValueError; invalid prices/seats (non-int, bool,
    negative) raise ValueError. Inputs are never mutated.
"""
import unittest
from datetime import datetime, timedelta, timezone

PERIOD_DAYS = 13
MIN_LINE_CENTS = 50
BIG_CREDIT_CENTS = 50000
VAT_PERCENT = 21
MAX_DESC = 80
APPROVER = "Nguyễn Thị Phương Thảo"
BIG_APPROVER = "Ramón Etxeberria-Goñi"


def _nonneg_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative int")
    return value


def _aware(value, name):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value


def _describe(prefix, plan, end_date):
    suffix = f" until {end_date}"
    avail = MAX_DESC - len(prefix) - len(suffix)
    if len(plan) > avail:
        plan = plan[: max(avail - 3, 0)] + "..."
    return prefix + plan + suffix


def prorate_seats(subscription, new_plan, changed_at):
    period_end = _aware(subscription["period_end"], "period_end")
    _aware(changed_at, "changed_at")
    if subscription.get("status") == "trialing":
        return []

    old_price = _nonneg_int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _nonneg_int(new_plan["seat_price_cents"], "new seat_price_cents")
    seats = _nonneg_int(subscription["billable_seats"], "billable_seats")
    old_name, new_name = subscription["plan_name"], new_plan["name"]
    if not isinstance(old_name, str) or not isinstance(new_name, str):
        raise ValueError("plan names must be strings")

    if old_name == new_name and old_price == new_price:
        return []
    if new_price < old_price:
        return []

    local_change = changed_at.astimezone(period_end.tzinfo).date()
    days_left = (period_end.date() - local_change).days
    days_left = max(0, min(PERIOD_DAYS, days_left))
    if days_left == 0 or seats == 0:
        return []

    end_date = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit unused ", old_name, end_date),
            "approved_by": BIG_APPROVER if credit > BIG_CREDIT_CENTS else APPROVER,
        })

    charge = (new_price * seats * days_left) // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        vat_id = subscription.get("vat_id")
        reverse = isinstance(vat_id, str) and vat_id.strip() != ""
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * VAT_PERCENT // 100,
            "description": _describe("Charge ", new_name, end_date),
            "approved_by": None,
        })
    return lines


class ProrateTests(unittest.TestCase):
    def sub(self, **kw):
        s = {"id": "s1", "status": "active", "plan_name": "Basic",
             "seat_price_cents": 1000, "seats": 9, "billable_seats": 3,
             "vat_id": None,
             "period_end": datetime(2026, 10, 20, tzinfo=timezone.utc)}
        s.update(kw)
        return s

    NEW = {"name": "Pro", "seat_price_cents": 2000}
    NOW = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)

    def test_basic(self):
        r = prorate_seats(self.sub(), self.NEW, self.NOW)
        self.assertEqual([l["kind"] for l in r], ["credit", "charge"])
        self.assertEqual(r[0]["amount_cents"], 1616)
        self.assertEqual(r[0]["approved_by"], APPROVER)
        self.assertEqual(r[1]["amount_cents"], 3230)
        self.assertEqual(r[1]["vat_cents"], 678)
        self.assertIsNone(r[1]["approved_by"])
        self.assertTrue(r[0]["description"].endswith("2026-10-20"))
        self.assertEqual(set(r[0]), {"subscription_id", "kind", "amount_cents",
                                     "vat_cents", "description", "approved_by"})

    def test_vat_id(self):
        r = prorate_seats(self.sub(vat_id="PT123"), self.NEW, self.NOW)
        self.assertEqual(r[1]["vat_cents"], 0)
        r = prorate_seats(self.sub(vat_id="  "), self.NEW, self.NOW)
        self.assertEqual(r[1]["vat_cents"], 678)

    def test_empty_cases(self):
        self.assertEqual(prorate_seats(self.sub(status="trialing"), self.NEW, self.NOW), [])
        self.assertEqual(prorate_seats(self.sub(), {"name": "L", "seat_price_cents": 500}, self.NOW), [])
        self.assertEqual(prorate_seats(self.sub(), {"name": "Basic", "seat_price_cents": 1000}, self.NOW), [])
        self.assertEqual(prorate_seats(self.sub(billable_seats=0), self.NEW, self.NOW), [])

    def test_days_clamp_and_tz(self):
        tz = timezone(timedelta(hours=2))
        s = self.sub(period_end=datetime(2026, 10, 20, 1, tzinfo=tz))
        late = datetime(2026, 10, 19, 23, 30, tzinfo=timezone.utc)
        self.assertEqual(prorate_seats(s, self.NEW, late), [])
        early = datetime(2026, 9, 1, tzinfo=timezone.utc)
        r = prorate_seats(self.sub(), self.NEW, early)
        self.assertEqual(r[0]["amount_cents"], 3000)

    def test_small_lines(self):
        s = self.sub(seat_price_cents=100, billable_seats=1)
        new = {"name": "Pro", "seat_price_cents": 100}
        # 100*1*6/13 = 46.15 -> credit 47 dropped
        now = datetime(2026, 10, 14, tzinfo=timezone.utc)
        self.assertEqual(prorate_seats(s, new, now), [])
        # 100*1*7/13 = 53.8 -> credit 54 kept, charge 53 kept
        r = prorate_seats(s, new, self.NOW)
        self.assertEqual([l["amount_cents"] for l in r], [54, 53])

    def test_approver_threshold(self):
        new = {"name": "Pro", "seat_price_cents": 6000}
        now = datetime(2026, 10, 7, tzinfo=timezone.utc)
        r = prorate_seats(self.sub(seat_price_cents=5000, billable_seats=10), new, now)
        self.assertEqual(r[0]["amount_cents"], 50000)
        self.assertEqual(r[0]["approved_by"], APPROVER)
        r = prorate_seats(self.sub(seat_price_cents=5001, billable_seats=10), new, now)
        self.assertEqual(r[0]["approved_by"], BIG_APPROVER)

    def test_long_name(self):
        r = prorate_seats(self.sub(plan_name="X" * 200), {"name": "Y" * 200, "seat_price_cents": 2000}, self.NOW)
        for l in r:
            self.assertLessEqual(len(l["description"]), 80)
            self.assertIn("...", l["description"])
            self.assertTrue(l["description"].endswith("2026-10-20"))

    def test_validation_and_no_mutation(self):
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), self.NEW, datetime(2026, 10, 13))
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(period_end=datetime(2026, 10, 20)), self.NEW, self.NOW)
        for bad in (True, 1.0, -1):
            with self.assertRaises(ValueError):
                prorate_seats(self.sub(billable_seats=bad), self.NEW, self.NOW)
            with self.assertRaises(ValueError):
                prorate_seats(self.sub(seat_price_cents=bad), self.NEW, self.NOW)
        s, n = self.sub(), dict(self.NEW)
        s0, n0 = dict(s), dict(n)
        prorate_seats(s, n, self.NOW)
        self.assertEqual((s, n), (s0, n0))


if __name__ == "__main__":
    unittest.main()