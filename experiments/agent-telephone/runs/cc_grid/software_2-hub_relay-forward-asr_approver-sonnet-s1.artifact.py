import unittest
from datetime import datetime, timedelta, timezone

WIN = "Win Tee Fung Tao"
RAMON = "Ramón Etxeberria-Goñi"
MAX_DESC = 80
MIN_LINE = 50
BIG_CREDIT = 50000

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents",
             "billable_seats", "vat_id", "period_end")


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _describe(prefix, plan, date_str):
    plan = str(plan)
    suffix = f" until {date_str}"
    room = MAX_DESC - len(prefix) - len(suffix)
    if len(plan) > room:
        plan = plan[:max(room - 3, 0)].rstrip() + "..."
        plan = plan[:max(room, 0)]
    return f"{prefix}{plan}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise ValueError("subscription and new_plan must be dicts")
    for k in _SUB_KEYS:
        if k not in subscription:
            raise ValueError(f"missing subscription key: {k}")
    for k in ("name", "seat_price_cents"):
        if k not in new_plan:
            raise ValueError(f"missing new_plan key: {k}")

    seats = subscription["billable_seats"]
    if not _is_int(seats) or seats < 0:
        raise ValueError("invalid billable_seats")
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    for p in (old_price, new_price):
        if not _is_int(p) or p < 0:
            raise ValueError("invalid price")
    period_end = subscription["period_end"]
    if not _aware(changed_at) or not _aware(period_end):
        raise ValueError("datetimes must be timezone-aware")

    status = subscription["status"]
    if isinstance(status, str) and status.strip().lower() == "trialing":
        return []
    if new_price <= old_price or seats == 0:
        return []

    local_change = changed_at.astimezone(period_end.tzinfo).date()
    days_left = min(max((period_end.date() - local_change).days, 0), 30)
    if days_left <= 0:
        return []

    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * days_left) // 30)
    if credit >= MIN_LINE:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit: unused ", subscription["plan_name"], date_str),
            "approved_by": RAMON if credit > BIG_CREDIT else WIN,
        })

    charge = (new_price * seats * days_left) // 30
    if charge >= MIN_LINE:
        vat_id = subscription["vat_id"]
        reverse = isinstance(vat_id, str) and vat_id.strip() != ""
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * 21 // 100,
            "description": _describe("Charge: remaining ", new_plan["name"], date_str),
            "approved_by": None,
        })
    return lines


class ProrateTests(unittest.TestCase):
    def sub(self, **kw):
        s = {"id": 7, "status": "active", "plan_name": "Basic",
             "seat_price_cents": 1001, "seats": 99, "billable_seats": 2,
             "vat_id": None,
             "period_end": datetime(2026, 11, 1, 12, tzinfo=timezone.utc)}
        s.update(kw)
        return s

    CH = datetime(2026, 10, 12, 8, tzinfo=timezone.utc)  # 20 days left

    def test_example(self):
        r = prorate_seats(self.sub(), {"name": "Pro", "seat_price_cents": 1501}, self.CH)
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
        self.assertEqual(r[0]["amount_cents"], 1335)
        self.assertEqual(r[0]["vat_cents"], 0)
        self.assertEqual(r[0]["approved_by"], WIN)
        self.assertEqual(r[1]["amount_cents"], 2001)
        self.assertEqual(r[1]["vat_cents"], 420)
        self.assertIsNone(r[1]["approved_by"])
        self.assertEqual(r[0]["description"], "Credit: unused Basic until 2026-11-01")

    def test_reverse_charge(self):
        r = prorate_seats(self.sub(vat_id="PT123"), {"name": "Pro", "seat_price_cents": 1501}, self.CH)
        self.assertEqual(r[1]["vat_cents"], 0)
        r = prorate_seats(self.sub(vat_id="  "), {"name": "Pro", "seat_price_cents": 1501}, self.CH)
        self.assertEqual(r[1]["vat_cents"], 420)

    def test_approval_threshold(self):
        ch = datetime(2026, 10, 2, tzinfo=timezone.utc)  # 30 days
        s = self.sub(seat_price_cents=5000, billable_seats=10)
        r = prorate_seats(s, {"name": "P", "seat_price_cents": 6000}, ch)
        self.assertEqual((r[0]["amount_cents"], r[0]["approved_by"]), (50000, WIN))
        s = self.sub(seat_price_cents=5001, billable_seats=10)
        r = prorate_seats(s, {"name": "P", "seat_price_cents": 6000}, ch)
        self.assertEqual((r[0]["amount_cents"], r[0]["approved_by"]), (50010, RAMON))

    def test_empty_cases(self):
        new = {"name": "Pro", "seat_price_cents": 1501}
        self.assertEqual(prorate_seats(self.sub(status=" Trialing "), new, self.CH), [])
        self.assertEqual(prorate_seats(self.sub(), {"name": "x", "seat_price_cents": 1001}, self.CH), [])
        self.assertEqual(prorate_seats(self.sub(billable_seats=0), new, self.CH), [])
        late = datetime(2026, 11, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(prorate_seats(self.sub(), new, late), [])

    def test_skip_small_independently(self):
        s = self.sub(seat_price_cents=40, billable_seats=1)
        ch = datetime(2026, 10, 2, tzinfo=timezone.utc)
        r = prorate_seats(s, {"name": "P", "seat_price_cents": 60}, ch)
        self.assertEqual([x["kind"] for x in r], ["charge"])

    def test_long_name(self):
        r = prorate_seats(self.sub(plan_name="N" * 100), {"name": "M" * 100, "seat_price_cents": 1501}, self.CH)
        for x in r:
            self.assertEqual(len(x["description"]), 80)
            self.assertTrue(x["description"].endswith("... until 2026-11-01"))

    def test_errors(self):
        new = {"name": "Pro", "seat_price_cents": 1501}
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), new, datetime(2026, 10, 12))
        for bad in (None, True, 1.5, "2", -1):
            with self.assertRaises(ValueError):
                prorate_seats(self.sub(billable_seats=bad), new, self.CH)
        s = self.sub()
        del s["vat_id"]
        with self.assertRaises(ValueError):
            prorate_seats(s, new, self.CH)
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), {"name": "x", "seat_price_cents": -1}, self.CH)


if __name__ == "__main__":
    unittest.main()