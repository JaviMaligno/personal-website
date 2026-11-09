"""prorate.py - seat proration for Fernhollow Studios (client: Ingrid).

Run tests with: python3 prorate.py   (unittest). I could not execute them here
because no tools were available, so the tests are unrun.

Assumptions awaiting client confirmation:
 Q1 partial days are floored.
 Q2 equal prices produce no lines.
 Q3 the 50-cent skip is applied per line.
 Q4 VAT is floored.
 Q5 credit amounts are positive, and kind carries direction.
 Q6 non-trialing statuses are processed normally.
 Q7 description templates are as specified in R9.
 Q8 seat_price_cents is per seat per 30-day period.

Notes:
 - The house rules (half-up rounding, VAT on credits) are overridden by
   R6 (credit ceil, charge floor) and R7 (credits vat 0).
 - "seats" is never read, so it is not required to be present.
"""
import unicodedata
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
MAX_DESC = 80
APPROVER_DEFAULT = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
APPROVER_HIGH = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")
HIGH_CREDIT_CENTS = 50000

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def credit_amount(price: int, seats: int, days: int) -> int:
    return ceil_div(price * seats * days, PERIOD_DAYS)


def charge_amount(price: int, seats: int, days: int) -> int:
    return price * seats * days // PERIOD_DAYS


def charge_vat(amount: int, vat_id) -> int:
    if isinstance(vat_id, str) and vat_id.strip():
        return 0
    return amount * VAT_PERCENT // 100


def build_description(kind: str, plan: str, period_end: datetime) -> str:
    verb = "Credit unused " if kind == "credit" else "Charge new "
    suffix = f" until {period_end.date().isoformat()}"
    room = MAX_DESC - len(verb) - len(suffix)
    if len(plan) > room:
        plan = plan[:room - 3].rstrip() + "..."
    return verb + plan + suffix


def select_approver(kind: str, amount: int):
    if kind != "credit":
        return None
    return APPROVER_HIGH if amount > HIGH_CREDIT_CENTS else APPROVER_DEFAULT


def days_left(period_end: datetime, changed_at: datetime) -> int:
    return min(PERIOD_DAYS, (period_end - changed_at) // timedelta(days=1))


def _aware(dt, name):
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _require(d, keys):
    for k in keys:
        if k not in d:
            raise ValueError(f"missing required key: {k}")


def _int_field(v, name):
    if type(v) is not int:
        raise TypeError(f"{name} must be an int")
    if v < 0:
        raise ValueError(f"{name} must be non-negative")
    return v


def _line(sub_id, kind, amount, vat, plan, period_end):
    return {
        "subscription_id": sub_id,
        "kind": kind,
        "amount_cents": amount,
        "vat_cents": vat,
        "description": build_description(kind, plan, period_end),
        "approved_by": select_approver(kind, amount),
    }


def prorate_seats(subscription, new_plan, changed_at):
    _require(subscription, ("status",))
    if subscription["status"] == "trialing":
        return []
    _require(subscription, _SUB_KEYS)
    _require(new_plan, _PLAN_KEYS)
    seats = subscription["billable_seats"]
    if type(seats) is not int or seats < 0:
        raise ValueError("billable_seats must be a non-negative int")
    old_price = _int_field(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _int_field(new_plan["seat_price_cents"], "new_plan.seat_price_cents")
    period_end = subscription["period_end"]
    _aware(period_end, "period_end")
    _aware(changed_at, "changed_at")

    if new_price <= old_price:
        return []
    days = days_left(period_end, changed_at)
    if days <= 0:
        return []

    sid = subscription["id"]
    lines = []
    credit = credit_amount(old_price, seats, days)
    if credit >= MIN_LINE_CENTS:
        lines.append(_line(sid, "credit", credit, 0,
                           subscription["plan_name"], period_end))
    charge = charge_amount(new_price, seats, days)
    if charge >= MIN_LINE_CENTS:
        lines.append(_line(sid, "charge", charge,
                           charge_vat(charge, subscription["vat_id"]),
                           new_plan["name"], period_end))
    return lines


# ---------------------------------------------------------------- tests
END = datetime(2025, 7, 31, 12, 0, tzinfo=timezone.utc)


def _sub(**kw):
    s = {"id": "s1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 1, "billable_seats": 1,
         "vat_id": None, "period_end": END, "legacy_discount": 99}
    s.update(kw)
    return s


def _at(days):
    return END - timedelta(days=days)


class ProrateTests(unittest.TestCase):
    def test_examples(self):
        r = prorate_seats(_sub(), {"name": "Pro", "seat_price_cents": 1300}, _at(7))
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
        self.assertEqual(r[0]["amount_cents"], 234)
        self.assertEqual(r[0]["vat_cents"], 0)
        self.assertEqual(r[1]["amount_cents"], 303)
        self.assertEqual(r[1]["vat_cents"], 63)
        self.assertIsNone(r[1]["approved_by"])
        self.assertEqual(r[0]["approved_by"], APPROVER_DEFAULT)
        self.assertEqual(r[0]["description"], "Credit unused Basic until 2025-07-31")
        self.assertEqual(r[1]["description"], "Charge new Pro until 2025-07-31")
        for x in r:
            self.assertIs(type(x["amount_cents"]), int)
            self.assertIs(type(x["vat_cents"]), int)
            self.assertEqual(x["subscription_id"], "s1")

    def test_skip_boundary(self):
        new = {"name": "P", "seat_price_cents": 200}
        r = prorate_seats(_sub(seat_price_cents=100), new, _at(15))
        self.assertEqual(r[0]["amount_cents"], 50)
        r = prorate_seats(_sub(seat_price_cents=100), new, _at(14))
        self.assertEqual([x["kind"] for x in r], ["charge"])

    def test_billable_seats(self):
        r = prorate_seats(_sub(seats=10, billable_seats=7),
                          {"name": "P", "seat_price_cents": 2000}, _at(30))
        self.assertEqual(r[0]["amount_cents"], 7000)
        self.assertEqual(r[1]["amount_cents"], 14000)

    def test_billable_seats_validation(self):
        new = {"name": "P", "seat_price_cents": 2000}
        for bad in (True, -1, 1.0, "3", None):
            with self.assertRaises(ValueError):
                prorate_seats(_sub(billable_seats=bad), new, _at(5))

    def test_no_lines(self):
        new = {"name": "P", "seat_price_cents": 2000}
        self.assertEqual(prorate_seats(_sub(status="trialing"), new, _at(5)), [])
        self.assertEqual(prorate_seats(_sub(), {"name": "P", "seat_price_cents": 500}, _at(5)), [])
        self.assertEqual(prorate_seats(_sub(), {"name": "P", "seat_price_cents": 1000}, _at(5)), [])
        self.assertEqual(prorate_seats(_sub(), new, END), [])
        self.assertEqual(prorate_seats(_sub(), new, END + timedelta(days=1)), [])
        self.assertEqual(prorate_seats(_sub(), new, END - timedelta(hours=23)), [])

    def test_days_floor_and_clamp(self):
        new = {"name": "P", "seat_price_cents": 2000}
        a = prorate_seats(_sub(), new, END - timedelta(days=2, hours=23))
        b = prorate_seats(_sub(), new, _at(2))
        self.assertEqual(a[0]["amount_cents"], b[0]["amount_cents"])
        c = prorate_seats(_sub(), new, _at(45))
        d = prorate_seats(_sub(), new, _at(30))
        self.assertEqual(c, d)

    def test_vat(self):
        new = {"name": "P", "seat_price_cents": 1300}
        self.assertEqual(prorate_seats(_sub(vat_id="NL123"), new, _at(7))[1]["vat_cents"], 0)
        for v in (None, "", "   "):
            self.assertEqual(prorate_seats(_sub(vat_id=v), new, _at(7))[1]["vat_cents"], 63)

    def test_approver_boundary(self):
        new = {"name": "P", "seat_price_cents": 99999}
        r = prorate_seats(_sub(seat_price_cents=50000), new, _at(30))
        self.assertEqual(r[0]["approved_by"], APPROVER_DEFAULT)
        r = prorate_seats(_sub(seat_price_cents=50001), new, _at(30))
        self.assertEqual(r[0]["approved_by"], APPROVER_HIGH)

    def test_long_description(self):
        new = {"name": "N" * 200, "seat_price_cents": 2000}
        r = prorate_seats(_sub(plan_name="x " * 100), new, _at(10))
        for x in r:
            self.assertLessEqual(len(x["description"]), 80)
            self.assertTrue(x["description"].endswith(" until 2025-07-31"))
            self.assertIn("...", x["description"])
        self.assertNotIn(" ...", r[0]["description"])

    def test_date_in_own_timezone(self):
        tz = timezone(timedelta(hours=10))
        pe = datetime(2025, 8, 1, 3, 0, tzinfo=tz)
        r = prorate_seats(_sub(period_end=pe), {"name": "P", "seat_price_cents": 2000},
                          pe - timedelta(days=5))
        self.assertTrue(r[0]["description"].endswith("2025-08-01"))

    def test_validation_and_purity(self):
        new = {"name": "P", "seat_price_cents": 2000}
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), new, datetime(2025, 7, 1))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(period_end=datetime(2025, 7, 31)), new, _at(5))
        s = _sub()
        del s["vat_id"]
        with self.assertRaisesRegex(ValueError, "vat_id"):
            prorate_seats(s, new, _at(5))
        with self.assertRaisesRegex(ValueError, "name"):
            prorate_seats(_sub(), {"seat_price_cents": 5}, _at(5))
        with self.assertRaises((TypeError, ValueError)):
            prorate_seats(_sub(seat_price_cents=10.5), new, _at(5))
        with self.assertRaises((TypeError, ValueError)):
            prorate_seats(_sub(), {"name": "P", "seat_price_cents": True}, _at(5))
        s, n = _sub(), dict(new)
        s0, n0 = deepcopy(s), deepcopy(n)
        prorate_seats(s, n, _at(5))
        self.assertEqual((s, n), (s0, n0))


if __name__ == "__main__":
    unittest.main()