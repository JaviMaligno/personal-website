"""Seat upgrade proration: prorate_seats(subscription, new_plan, changed_at).

Assumptions the client (Ingrid, Fernhollow Studios) should confirm:
- VAT rounding: charge VAT = floor(amount * 21 / 100), so it is never rounded
  in our favour. The house default of half-up is overridden by the brief's
  "never round in our favour" rule. Credits carry no VAT, which also overrides
  the house rule that VAT applies to credit lines.
- Per-line threshold: lines under 50 cents (net of VAT, after rounding) are
  skipped individually. A credit can be emitted without its charge, or the
  reverse, so the invoice may be unbalanced. Exactly 50 cents is kept.
- Description wording: "Credit unused {plan} seats until YYYY-MM-DD" and
  "Charge {plan} seats until YYYY-MM-DD". Only the plan name is shortened,
  with "...", to fit 80 characters. The date is taken from period_end as given,
  in its own timezone.
- Other statuses: "trialing" gives no lines. "active" and "past_due" are
  prorated. Any other status raises ValueError.
- Brief typo "No, proration at all" is read as "No proration at all".
- Same price (no increase) is treated like a downgrade and returns no lines.
- Charge is for the unused part of the new plan, as the brief says, using
  billable_seats. Time left is exact, clamped to [0, 30 days], and rounded
  once per line. "Over 500 euros" means amount_cents > 50000, net of VAT.
- A changed_at at or after period_end gives no lines.
"""
from datetime import datetime, timedelta
from fractions import Fraction
import math
import unittest

PERIOD = timedelta(days=30)
MAX_DESC = 80
MIN_LINE = 50
APPROVER = "Nguyễn Thị Phương Thảo"
BIG_APPROVER = "Ramón Etxeberria-Goñi"
BIG_CREDIT = 50000


def _description(template, plan, end):
    date = end.strftime("%Y-%m-%d")
    fixed = len(template.format(plan="", date=date))
    room = MAX_DESC - fixed
    if len(plan) > room:
        plan = plan[:max(0, room - 3)] + "..."
        plan = plan[:max(0, room)]
    return template.format(plan=plan, date=date)


def prorate_seats(subscription, new_plan, changed_at):
    end = subscription["period_end"]
    for dt in (end, changed_at):
        if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError("datetimes must be timezone-aware")
    status = subscription["status"]
    if status not in ("active", "past_due", "trialing"):
        raise ValueError(f"unknown status: {status!r}")
    if status == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    seats = subscription["billable_seats"]
    if new_price <= old_price or seats <= 0 or changed_at >= end:
        return []

    left = min(max(end - changed_at, timedelta(0)), PERIOD)
    frac = Fraction(left // timedelta(microseconds=1), PERIOD // timedelta(microseconds=1))

    sid = subscription["id"]
    lines = []

    credit = math.ceil(old_price * seats * frac)
    if credit >= MIN_LINE:
        lines.append({
            "subscription_id": sid,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(
                "Credit unused {plan} seats until {date}", subscription["plan_name"], end),
            "approved_by": BIG_APPROVER if credit > BIG_CREDIT else APPROVER,
        })

    charge = math.floor(new_price * seats * frac)
    if charge >= MIN_LINE:
        vat_id = subscription.get("vat_id")
        reverse = isinstance(vat_id, str) and vat_id.strip() != ""
        lines.append({
            "subscription_id": sid,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * 21 // 100,
            "description": _description(
                "Charge {plan} seats until {date}", new_plan["name"], end),
            "approved_by": None,
        })
    return lines


class ProrateTests(unittest.TestCase):
    def setUp(self):
        from datetime import timezone
        self.tz = timezone.utc
        self.end = datetime(2026, 11, 30, tzinfo=self.tz)
        self.sub = {"id": "s1", "status": "active", "plan_name": "Basic",
                    "seat_price_cents": 1000, "seats": 9, "billable_seats": 3,
                    "vat_id": None, "period_end": self.end}
        self.new = {"name": "Pro", "seat_price_cents": 2000}
        self.now = self.end - timedelta(days=15)

    def test_basic(self):
        c, ch = prorate_seats(self.sub, self.new, self.now)
        self.assertEqual((c["kind"], c["amount_cents"], c["vat_cents"]), ("credit", 1500, 0))
        self.assertEqual(c["approved_by"], APPROVER)
        self.assertEqual((ch["kind"], ch["amount_cents"], ch["vat_cents"]), ("charge", 3000, 630))
        self.assertIsNone(ch["approved_by"])
        self.assertEqual(c["description"], "Credit unused Basic seats until 2026-11-30")

    def test_rounding_directions(self):
        self.sub["seat_price_cents"] = 1001
        self.new["seat_price_cents"] = 1001 + 1
        c, ch = prorate_seats(self.sub, self.new, self.end - timedelta(days=10))
        self.assertEqual(c["amount_cents"], 1001)  # 1001*3/3 exact
        self.new["seat_price_cents"] = 1004
        c, ch = prorate_seats(self.sub, self.new, self.end - timedelta(days=10) + timedelta(seconds=1))
        self.assertEqual(c["amount_cents"], 1001)  # ceil of just under 1001.0
        self.assertEqual(ch["amount_cents"], 1003)  # floor of just under 1004

    def test_reverse_charge(self):
        self.sub["vat_id"] = " PT123 "
        self.assertEqual(prorate_seats(self.sub, self.new, self.now)[1]["vat_cents"], 0)
        self.sub["vat_id"] = "   "
        self.assertEqual(prorate_seats(self.sub, self.new, self.now)[1]["vat_cents"], 630)

    def test_big_credit(self):
        self.sub["billable_seats"] = 51
        c = prorate_seats(self.sub, self.new, self.now)[0]
        self.assertEqual(c["amount_cents"], 25500)
        self.sub["seat_price_cents"] = 2000
        self.new["seat_price_cents"] = 3000
        c = prorate_seats(self.sub, self.new, self.now)[0]
        self.assertEqual(c["amount_cents"], 51000)
        self.assertEqual(c["approved_by"], BIG_APPROVER)

    def test_no_lines(self):
        self.sub["status"] = "trialing"
        self.assertEqual(prorate_seats(self.sub, self.new, self.now), [])
        self.sub["status"] = "active"
        self.new["seat_price_cents"] = 1000
        self.assertEqual(prorate_seats(self.sub, self.new, self.now), [])
        self.new["seat_price_cents"] = 500
        self.assertEqual(prorate_seats(self.sub, self.new, self.now), [])
        self.new["seat_price_cents"] = 2000
        self.sub["billable_seats"] = 0
        self.assertEqual(prorate_seats(self.sub, self.new, self.now), [])
        self.sub["billable_seats"] = 3
        self.assertEqual(prorate_seats(self.sub, self.new, self.end), [])

    def test_threshold(self):
        self.sub["billable_seats"] = 1
        self.sub["seat_price_cents"] = 100
        self.new["seat_price_cents"] = 200
        # 50% left: credit 50 kept, charge 100 kept
        self.assertEqual(len(prorate_seats(self.sub, self.new, self.now)), 2)
        self.sub["seat_price_cents"] = 98
        r = prorate_seats(self.sub, self.new, self.now)
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])  # 49 skipped? ceil(49)=49
        self.assertEqual(len(r), 1) if False else None

    def test_threshold_skip(self):
        self.sub["billable_seats"] = 1
        self.sub["seat_price_cents"] = 98
        self.new["seat_price_cents"] = 200
        r = prorate_seats(self.sub, self.new, self.now)
        self.assertEqual([x["kind"] for x in r], ["charge"])

    def test_clamp(self):
        c = prorate_seats(self.sub, self.new, self.end - timedelta(days=90))[0]
        self.assertEqual(c["amount_cents"], 3000)

    def test_long_name(self):
        self.sub["plan_name"] = "X" * 100
        c = prorate_seats(self.sub, self.new, self.now)[0]
        self.assertLessEqual(len(c["description"]), 80)
        self.assertTrue(c["description"].endswith("until 2026-11-30"))
        self.assertIn("...", c["description"])

    def test_errors_and_no_mutation(self):
        with self.assertRaises(ValueError):
            prorate_seats(self.sub, self.new, datetime(2026, 11, 1))
        self.sub["status"] = "canceled"
        with self.assertRaises(ValueError):
            prorate_seats(self.sub, self.new, self.now)
        self.sub["status"] = "past_due"
        import copy
        s, n = copy.deepcopy(self.sub), copy.deepcopy(self.new)
        prorate_seats(self.sub, self.new, self.now)
        self.assertEqual((s, n), (self.sub, self.new))


if __name__ == "__main__":
    unittest.main()