"""Seat upgrade proration for Fernhollow Studios.

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list[dict]

Assumptions (flagged for the client):
- Equal old and new price: returns no lines. The brief only defines a cheaper
  plan as a downgrade, so this is an assumption.
- Statuses other than "trialing" (active, past_due, ...) are prorated.
- VAT on a charge is floor(21% of amount), so VAT is never rounded in our favour.
  Credits never carry VAT, as the brief says. This overrides the generic
  "VAT on every line" house rule.
- days_left is clamped to a maximum of 13. A non-positive value returns [].
- Timezone: changed_at is converted to period_end's timezone, then the calendar
  date difference is taken.
- Only billable_seats is used. seats and legacy_discount are ignored.
- Lines under 50 cents are dropped independently. Exactly 50 is kept.
- Credits over 50000 cents are approved by the senior approver.
"""
import unicodedata
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone

PERIOD_DAYS = 13
MIN_LINE_CENTS = 50
BIG_CREDIT_CENTS = 50000
MAX_DESC = 80
APPROVER = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
SENIOR_APPROVER = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")


def _int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must be >= 0")
    return value


def _aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _describe(prefix, plan, date_str):
    suffix = f" until {date_str}"
    avail = MAX_DESC - len(prefix) - len(suffix)
    if len(plan) > avail:
        plan = plan[: max(avail - 1, 0)] + "\u2026"
    return f"{prefix}{plan}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise TypeError("subscription and new_plan must be dicts")
    for k in ("id", "status", "plan_name", "seat_price_cents",
              "billable_seats", "vat_id", "period_end"):
        if k not in subscription:
            raise ValueError(f"missing subscription key: {k}")
    for k in ("name", "seat_price_cents"):
        if k not in new_plan:
            raise ValueError(f"missing new_plan key: {k}")

    sub_id = subscription["id"]
    status = subscription["status"]
    old_name = subscription["plan_name"]
    new_name = new_plan["name"]
    vat_id = subscription["vat_id"]
    if not isinstance(status, str):
        raise TypeError("status must be a str")
    if not isinstance(old_name, str) or not isinstance(new_name, str):
        raise TypeError("plan names must be str")
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be a str or None")
    old_price = _int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _int(new_plan["seat_price_cents"], "new seat_price_cents")
    seats = _int(subscription["billable_seats"], "billable_seats")
    period_end = _aware(subscription["period_end"], "period_end")
    changed_at = _aware(changed_at, "changed_at")

    local_change = changed_at.astimezone(period_end.tzinfo)
    days_left = min((period_end.date() - local_change.date()).days, PERIOD_DAYS)

    if (days_left <= 0 or seats == 0 or status == "trialing"
            or new_price <= old_price):
        return []

    date_str = period_end.date().isoformat()
    lines = []

    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit unused ", old_name, date_str),
            "approved_by": SENIOR_APPROVER if credit > BIG_CREDIT_CENTS else APPROVER,
        })

    charge = (new_price * seats * days_left) // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        vat = 0 if (vat_id is not None and vat_id.strip()) else charge * 21 // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe("Charge ", new_name, date_str),
            "approved_by": None,
        })
    return lines


class ProrateTests(unittest.TestCase):
    def setUp(self):
        self.end = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
        self.sub = {"id": "s1", "status": "active", "plan_name": "Basic",
                    "seat_price_cents": 1000, "seats": 9, "billable_seats": 3,
                    "vat_id": None, "period_end": self.end}
        self.new = {"name": "Pro", "seat_price_cents": 1500}
        self.now = datetime(2026, 10, 13, 23, 0, tzinfo=timezone.utc)

    def test_example(self):
        before = deepcopy(self.sub)
        c, ch = prorate_seats(self.sub, self.new, self.now)
        self.assertEqual(self.sub, before)
        self.assertEqual((c["kind"], c["amount_cents"], c["vat_cents"]), ("credit", 1154, 0))
        self.assertEqual(c["approved_by"], APPROVER)
        self.assertEqual(c["description"], "Credit unused Basic until 2026-10-18")
        self.assertEqual((ch["amount_cents"], ch["vat_cents"], ch["approved_by"]), (1730, 363, None))

    def test_reverse_charge(self):
        self.sub["vat_id"] = "PT123"
        self.assertEqual(prorate_seats(self.sub, self.new, self.now)[1]["vat_cents"], 0)

    def test_no_lines(self):
        self.assertEqual(prorate_seats(self.sub, {"name": "L", "seat_price_cents": 500}, self.now), [])
        self.assertEqual(prorate_seats(self.sub, {"name": "L", "seat_price_cents": 1000}, self.now), [])
        self.sub["status"] = "trialing"
        self.assertEqual(prorate_seats(self.sub, self.new, self.now), [])
        self.sub["status"] = "active"
        self.sub["billable_seats"] = 0
        self.assertEqual(prorate_seats(self.sub, self.new, self.now), [])
        self.sub["billable_seats"] = 3
        self.assertEqual(prorate_seats(self.sub, self.new, self.end), [])

    def test_clamp_and_senior(self):
        self.sub["billable_seats"] = 100
        early = self.end - timedelta(days=40)
        c = prorate_seats(self.sub, self.new, early)[0]
        self.assertEqual(c["amount_cents"], 100000)
        self.assertEqual(c["approved_by"], SENIOR_APPROVER)

    def test_min_line(self):
        sub = dict(self.sub, seat_price_cents=10, billable_seats=1)
        out = prorate_seats(sub, {"name": "P", "seat_price_cents": 20}, self.now)
        self.assertEqual(out, [])

    def test_long_name(self):
        self.sub["plan_name"] = "X" * 200
        d = prorate_seats(self.sub, self.new, self.now)[0]["description"]
        self.assertLessEqual(len(d), 80)
        self.assertTrue(d.endswith(" until 2026-10-18"))

    def test_validation(self):
        with self.assertRaises(ValueError):
            prorate_seats(self.sub, self.new, datetime(2026, 10, 13))
        with self.assertRaises(TypeError):
            prorate_seats(dict(self.sub, billable_seats=2.0), self.new, self.now)
        bad = dict(self.sub)
        del bad["id"]
        with self.assertRaises(ValueError):
            prorate_seats(bad, self.new, self.now)


if __name__ == "__main__":
    unittest.main()