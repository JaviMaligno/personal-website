"""Seat-upgrade proration for Fernhollow Studios billing.

Run the tests with: python3 -m unittest <this_file>.py

Deviations from the house rules, both required by the client brief:
- Rounding is directional (credits up, charges down), not half-up.
- Credits carry vat_cents 0, although the house rule says VAT applies to every line.
"""
from datetime import datetime
import unittest

# Amounts are always positive ints; direction is carried by "kind".
# Change this single constant if the ledger ever wants signed credits (-1).
CREDIT_SIGN = 1

MIN_LINE_CENTS = 50
PERIOD_DAYS = 30
VAT_PERCENT = 21
BIG_CREDIT_CENTS = 50000
APPROVER = "Nguyễn Thị Phương Thảo"
BIG_APPROVER = "Ramón Etxeberria-Goñi"
MAX_DESC = 80


def _int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _str(value, name):
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a str")
    return value


def _aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _description(prefix, plan, date_str):
    suffix = f" until {date_str}"
    avail = MAX_DESC - len(prefix) - len(suffix)
    if len(plan) > avail:
        plan = plan[:max(avail - 1, 0)] + "…"
    return prefix + plan + suffix


def prorate_seats(subscription, new_plan, changed_at):
    sub_id = subscription["id"]
    status = _str(subscription["status"], "status")
    old_name = _str(subscription["plan_name"], "plan_name")
    old_price = _int(subscription["seat_price_cents"], "seat_price_cents")
    seats = _int(subscription["billable_seats"], "billable_seats")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be a str or None")
    period_end = _aware(subscription["period_end"], "period_end")
    new_name = _str(new_plan["name"], "name")
    new_price = _int(new_plan["seat_price_cents"], "seat_price_cents")
    _aware(changed_at, "changed_at")

    if status.strip().lower() == "trialing":
        return []
    if new_price < old_price:
        return []
    if new_name == old_name and new_price == old_price:
        return []
    if seats == 0:
        return []

    local_change = changed_at.astimezone(period_end.tzinfo)
    days_left = min((period_end.date() - local_change.date()).days, PERIOD_DAYS)
    if days_left <= 0:
        return []

    date_str = period_end.date().isoformat()
    lines = []

    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)  # round up
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit * CREDIT_SIGN,
            "vat_cents": 0,
            "description": _description("Credit unused ", old_name, date_str),
            "approved_by": BIG_APPROVER if credit > BIG_CREDIT_CENTS else APPROVER,
        })

    charge = (new_price * seats * days_left) // PERIOD_DAYS  # round down
    if charge >= MIN_LINE_CENTS:
        reverse = isinstance(vat_id, str) and vat_id.strip() != ""
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * VAT_PERCENT // 100,
            "description": _description("Charge unused ", new_name, date_str),
            "approved_by": None,
        })
    return lines


class ProrateTests(unittest.TestCase):
    def setUp(self):
        from datetime import timezone, timedelta
        self.tz = timezone(timedelta(hours=1))
        self.end = datetime(2025, 7, 31, 12, tzinfo=self.tz)
        self.sub = {"id": "s1", "status": "active", "plan_name": "Basic",
                    "seat_price_cents": 1000, "seats": 9, "billable_seats": 5,
                    "vat_id": None, "period_end": self.end}
        self.new = {"name": "Pro", "seat_price_cents": 1500}
        self.at = datetime(2025, 7, 16, 9, tzinfo=self.tz)

    def run_(self, **kw):
        sub = dict(self.sub, **kw.get("sub", {}))
        new = dict(self.new, **kw.get("new", {}))
        return prorate_seats(sub, new, kw.get("at", self.at))

    def test_example(self):
        c, ch = self.run_()
        self.assertEqual((c["kind"], c["amount_cents"], c["vat_cents"]), ("credit", 2500, 0))
        self.assertEqual(c["approved_by"], APPROVER)
        self.assertEqual((ch["amount_cents"], ch["vat_cents"], ch["approved_by"]), (3750, 787, None))
        self.assertEqual(c["description"], "Credit unused Basic until 2025-07-31")
        self.assertEqual(ch["description"], "Charge unused Pro until 2025-07-31")

    def test_vat_id(self):
        self.assertEqual(self.run_(sub={"vat_id": "PT123"})[1]["vat_cents"], 0)
        self.assertEqual(self.run_(sub={"vat_id": "  "})[1]["vat_cents"], 787)

    def test_rounding(self):
        c, ch = self.run_(sub={"seat_price_cents": 999, "billable_seats": 1},
                          new={"seat_price_cents": 1333},
                          at=datetime(2025, 7, 24, 9, tzinfo=self.tz))
        self.assertEqual((c["amount_cents"], ch["amount_cents"], ch["vat_cents"]), (234, 311, 65))

    def test_min_line(self):
        at = datetime(2025, 7, 21, 9, tzinfo=self.tz)
        kept = self.run_(sub={"seat_price_cents": 150, "billable_seats": 1},
                         new={"seat_price_cents": 150, "name": "X"}, at=at)
        self.assertEqual(kept[0]["amount_cents"], 50)
        dropped = self.run_(sub={"seat_price_cents": 100, "billable_seats": 1},
                            new={"seat_price_cents": 100, "name": "X"}, at=at)
        self.assertEqual(dropped, [])

    def test_approver_threshold(self):
        # 30 days: credit = price * seats
        at = datetime(2025, 7, 1, 9, tzinfo=self.tz)
        end = datetime(2025, 7, 31, 12, tzinfo=self.tz)
        for amount, who in ((50000, APPROVER), (50001, BIG_APPROVER)):
            r = self.run_(sub={"seat_price_cents": amount, "billable_seats": 1,
                               "period_end": end},
                          new={"seat_price_cents": amount}, at=at)
            self.assertEqual(r[0]["approved_by"], who)

    def test_empty_cases(self):
        self.assertEqual(self.run_(sub={"status": " Trialing "}), [])
        self.assertEqual(self.run_(new={"seat_price_cents": 900}), [])
        self.assertEqual(self.run_(sub={"billable_seats": 0}), [])
        self.assertEqual(self.run_(new={"name": "Basic", "seat_price_cents": 1000}), [])
        self.assertEqual(self.run_(at=datetime(2025, 8, 1, tzinfo=self.tz)), [])

    def test_days_clamped(self):
        r = self.run_(at=datetime(2025, 1, 1, tzinfo=self.tz))
        self.assertEqual(r[0]["amount_cents"], 5000)

    def test_long_name(self):
        r = self.run_(new={"name": "Ü" * 100})
        self.assertEqual(len(r[1]["description"]), 80)
        self.assertTrue(r[1]["description"].endswith("…" + " until 2025-07-31"))

    def test_errors(self):
        with self.assertRaises(ValueError):
            self.run_(at=datetime(2025, 7, 16))
        with self.assertRaises(KeyError):
            prorate_seats({}, self.new, self.at)
        with self.assertRaises(TypeError):
            self.run_(sub={"billable_seats": True})
        with self.assertRaises(TypeError):
            self.run_(new={"seat_price_cents": 15.0})
        with self.assertRaises(ValueError):
            self.run_(sub={"billable_seats": -1})

    def test_no_mutation(self):
        import copy
        before = copy.deepcopy(self.sub)
        prorate_seats(self.sub, self.new, self.at)
        self.assertEqual(before, self.sub)


if __name__ == "__main__":
    unittest.main()