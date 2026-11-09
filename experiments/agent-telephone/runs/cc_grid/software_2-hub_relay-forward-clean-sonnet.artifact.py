"""Seat upgrade proration for Fernhollow Studios.

Assumptions to confirm with the client:
- Equal old and new price returns [] (nothing to prorate).
- VAT on charges is floored (never rounded in the company's favour is not
  applicable to VAT, so floor was chosen to follow the charge rule).
- Whole-day flooring of days_left slightly disadvantages the customer on credits.
- Credits carry vat 0 (brief and PM), overriding the generic house rule that VAT
  applies to every line.
"""
import unittest
from datetime import datetime, timedelta, timezone

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
BIG_CREDIT_CENTS = 50000
VAT_PERCENT = 21
MAX_DESC = 80
CONTROLLER = "Nguyễn Thị Phương Thảo"
SENIOR = "Ramón Etxeberria-Goñi"


def _aware(dt, label):
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")


def _describe(prefix, plan, period_end):
    suffix = f" until {period_end.strftime('%Y-%m-%d')}"
    room = MAX_DESC - len(prefix) - len(suffix)
    if len(plan) > room:
        plan = plan[: max(room - 3, 0)] + "..."
    return prefix + plan + suffix


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription["period_end"]
    _aware(changed_at, "changed_at")
    _aware(period_end, "period_end")

    if subscription["status"] == "trialing":
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:
        return []

    days_left = (period_end - changed_at).days  # floors toward negative infinity
    days_left = max(0, min(PERIOD_DAYS, days_left))
    if days_left == 0:
        return []

    seats = subscription["billable_seats"]
    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)
    charge = (new_price * seats * days_left) // PERIOD_DAYS

    lines = []
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit unused ", subscription["plan_name"], period_end),
            "approved_by": SENIOR if credit > BIG_CREDIT_CENTS else CONTROLLER,
        })
    if charge >= MIN_LINE_CENTS:
        vat_id = subscription.get("vat_id")
        reverse = bool(vat_id and str(vat_id).strip())
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * VAT_PERCENT // 100,
            "description": _describe("Charge ", new_plan["name"], period_end),
            "approved_by": None,
        })
    return lines


class ProrateTests(unittest.TestCase):
    def setUp(self):
        self.end = datetime(2026, 11, 30, tzinfo=timezone.utc)
        self.now = self.end - timedelta(days=15)

    def sub(self, price=1000, seats=10, **kw):
        s = {"id": "s1", "status": "active", "plan_name": "Basic",
             "seat_price_cents": price, "seats": 99, "billable_seats": seats,
             "vat_id": None, "period_end": self.end}
        s.update(kw)
        return s

    def run_(self, sub, new_price, now=None):
        return prorate_seats(sub, {"name": "Pro", "seat_price_cents": new_price}, now or self.now)

    def test_basic(self):
        c, ch = self.run_(self.sub(), 2000)
        self.assertEqual((c["kind"], c["amount_cents"], c["vat_cents"], c["approved_by"]),
                         ("credit", 5000, 0, CONTROLLER))
        self.assertEqual((ch["amount_cents"], ch["vat_cents"], ch["approved_by"]), (10000, 2100, None))
        self.assertIn("2026-11-30", c["description"])

    def test_rounding(self):
        c, ch = self.run_(self.sub(101, 1), 201)
        self.assertEqual((c["amount_cents"], ch["amount_cents"]), (51, 100))

    def test_min_line(self):
        lines = self.run_(self.sub(99, 1), 199)
        self.assertEqual(lines[0]["amount_cents"], 50)
        self.assertEqual(self.run_(self.sub(98, 1), 300)[0]["kind"], "charge")

    def test_approver_threshold(self):
        self.assertEqual(self.run_(self.sub(3333, 3), 9999)[0]["approved_by"], CONTROLLER)  # 50000-ish
        self.assertEqual(self.run_(self.sub(100000, 1), 200000)[0]["approved_by"], CONTROLLER)
        l = self.run_(self.sub(100002, 1), 200000)[0]
        self.assertEqual(l["amount_cents"], 50001)
        self.assertEqual(l["approved_by"], SENIOR)

    def test_empty_cases(self):
        self.assertEqual(self.run_(self.sub(), 500), [])
        self.assertEqual(self.run_(self.sub(), 1000), [])
        self.assertEqual(self.run_(self.sub(status="trialing"), 2000), [])
        self.assertEqual(self.run_(self.sub(), 2000, self.end + timedelta(days=1)), [])

    def test_vat_id_and_clamp(self):
        ch = self.run_(self.sub(vat_id="PT123"), 2000)[1]
        self.assertEqual(ch["vat_cents"], 0)
        ch = self.run_(self.sub(vat_id="  "), 2000)[1]
        self.assertEqual(ch["vat_cents"], 2100)
        c = self.run_(self.sub(), 2000, self.end - timedelta(days=90))[0]
        self.assertEqual(c["amount_cents"], 10000)

    def test_naive_rejected(self):
        with self.assertRaises(ValueError):
            self.run_(self.sub(), 2000, datetime(2026, 11, 15))
        with self.assertRaises(ValueError):
            self.run_(self.sub(period_end=datetime(2026, 11, 30)), 2000)

    def test_description_and_no_mutation(self):
        import copy
        s = self.sub(plan_name="P" * 200)
        before = copy.deepcopy(s)
        lines = prorate_seats(s, {"name": "N" * 200, "seat_price_cents": 2000}, self.now)
        self.assertEqual(s, before)
        for l in lines:
            self.assertLessEqual(len(l["description"]), 80)
            self.assertTrue(l["description"].endswith("2026-11-30"))
            self.assertIn("...", l["description"])


if __name__ == "__main__":
    unittest.main()