"""Seat proration for Fernhollow Studios.

Assumptions (beyond the PM defaults):
- Validation (naive datetimes, non-integer money fields, bools rejected) runs
  before any early return.
- days_left uses calendar-date difference in period_end's timezone.
- A non-string truthy vat_id counts as present; strings must be non-blank.
"""
import unittest
from datetime import datetime, timedelta, timezone

MIN_CENTS = 50
APPROVER = "Nguyễn Thị Phương Thảo"
BIG_APPROVER = "Ramón Etxeberria-Goñi"
MAX_DESC = 80


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _aware(v, name):
    if not isinstance(v, datetime) or v.tzinfo is None or v.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _describe(prefix, plan, date_s):
    suffix = f" until {date_s}"
    full = f"{prefix} {plan}{suffix}"
    if len(full) <= MAX_DESC:
        return full
    avail = MAX_DESC - len(prefix) - 1 - len(suffix)
    plan = plan[:max(avail - 3, 0)] + "..."
    return f"{prefix} {plan}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    seats = subscription["billable_seats"]
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    for v in (seats, old_price, new_price):
        if not _is_int(v):
            raise ValueError("money/seat fields must be integers")
    period_end = subscription["period_end"]
    _aware(period_end, "period_end")
    _aware(changed_at, "changed_at")

    if subscription["status"] == "trialing" or new_price < old_price:
        return []
    if changed_at >= period_end:
        return []
    local = changed_at.astimezone(period_end.tzinfo)
    days = (period_end.date() - local.date()).days
    days = max(0, min(30, days))
    if days == 0:
        return []

    date_s = period_end.date().isoformat()
    sub_id = subscription["id"]
    credit = -(-(seats * old_price * days) // 30)
    charge = (seats * new_price * days) // 30

    vat_id = subscription.get("vat_id")
    has_vat_id = bool(vat_id.strip()) if isinstance(vat_id, str) else bool(vat_id)

    lines = []
    if credit >= MIN_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit unused", subscription["plan_name"], date_s),
            "approved_by": BIG_APPROVER if credit > 50000 else APPROVER,
        })
    if charge >= MIN_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if has_vat_id else charge * 21 // 100,
            "description": _describe("Charge unused", new_plan["name"], date_s),
            "approved_by": None,
        })
    return lines


class ProrateTests(unittest.TestCase):
    END = datetime(2026, 11, 1, tzinfo=timezone.utc)

    def sub(self, **kw):
        s = {"id": "s1", "status": "active", "plan_name": "Basic",
             "seat_price_cents": 1000, "seats": 99, "billable_seats": 10,
             "vat_id": None, "period_end": self.END}
        s.update(kw)
        return s

    def at(self, days):
        return self.END - timedelta(days=days)

    def test_basic(self):
        r = prorate_seats(self.sub(), {"name": "Pro", "seat_price_cents": 2000}, self.at(15))
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
        self.assertEqual((r[0]["amount_cents"], r[0]["approved_by"]), (5000, APPROVER))
        self.assertEqual((r[1]["amount_cents"], r[1]["vat_cents"]), (10000, 2100))
        self.assertEqual(r[0]["description"], "Credit unused Basic until 2026-11-01")

    def test_rounding_and_vat_id(self):
        s = self.sub(billable_seats=1, seat_price_cents=1001)
        p = {"name": "Pro", "seat_price_cents": 1501}
        r = prorate_seats(s, p, self.at(7))
        self.assertEqual((r[0]["amount_cents"], r[1]["amount_cents"], r[1]["vat_cents"]),
                         (234, 350, 73))
        r = prorate_seats(self.sub(billable_seats=1, seat_price_cents=1001, vat_id="PT1"), p, self.at(7))
        self.assertEqual(r[1]["vat_cents"], 0)
        r = prorate_seats(self.sub(billable_seats=1, seat_price_cents=1001, vat_id="  "), p, self.at(7))
        self.assertEqual(r[1]["vat_cents"], 73)

    def test_approver_threshold(self):
        p = {"name": "Basic", "seat_price_cents": 1000}
        r = prorate_seats(self.sub(billable_seats=100), p, self.at(30))
        self.assertEqual(r[0]["approved_by"], BIG_APPROVER)
        r = prorate_seats(self.sub(billable_seats=50), p, self.at(30))
        self.assertEqual((r[0]["amount_cents"], r[0]["approved_by"]), (50000, APPROVER))

    def test_minimum(self):
        def run(price):
            return prorate_seats(self.sub(billable_seats=1, seat_price_cents=price),
                                 {"name": "B", "seat_price_cents": price}, self.at(30))
        self.assertEqual(run(49), [])
        self.assertEqual(len(run(50)), 2)

    def test_skips(self):
        p = {"name": "Pro", "seat_price_cents": 2000}
        self.assertEqual(prorate_seats(self.sub(status="trialing"), p, self.at(15)), [])
        self.assertEqual(prorate_seats(self.sub(), {"name": "x", "seat_price_cents": 500}, self.at(15)), [])
        self.assertEqual(prorate_seats(self.sub(), p, self.END), [])
        self.assertEqual(prorate_seats(self.sub(), p, self.END + timedelta(days=1)), [])

    def test_long_name(self):
        r = prorate_seats(self.sub(plan_name="a" * 120), {"name": "b" * 120, "seat_price_cents": 2000}, self.at(15))
        for x in r:
            self.assertLessEqual(len(x["description"]), 80)
            self.assertTrue(x["description"].endswith("until 2026-11-01"))
            self.assertIn("...", x["description"])

    def test_errors_and_purity(self):
        p = {"name": "Pro", "seat_price_cents": 2000}
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), p, datetime(2026, 10, 1))
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(seat_price_cents=10.5), p, self.at(5))
        s = self.sub()
        before = dict(s)
        prorate_seats(s, p, self.at(15))
        self.assertEqual(s, before)


if __name__ == "__main__":
    unittest.main()