"""prorate.py - seat proration on plan change.

Assumptions and easy-to-change resolutions (R15+):
- days_left = floor((period_end - changed_at) / 24h), clamped to 0..30 (DAYS_* in _days_left).
- Equal or lower new price returns [] (R5, R17). Only "trialing" is excluded (EXCLUDED_STATUSES).
- The `seats` key must be present (R1/R22) but is never read or type-checked.
- Non-string plan names or a non-string, non-None vat_id raise ValueError (so VAT is never silently wrong).
- Tests are embedded below (run: python3 prorate.py) because a single module was requested.
  They have not been executed by me, as I had no execution tool.
"""
from datetime import datetime, timedelta

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
APPROVAL_THRESHOLD_CENTS = 50000
DEFAULT_APPROVER = "Win Tee Fung Tao"
SENIOR_APPROVER = "Ramón Etxeberria-Goñi"
EXCLUDED_STATUSES = frozenset({"trialing"})
MAX_DESCRIPTION = 80
VAT_PERCENT = 21

_REQUIRED_SUB = ("id", "status", "plan_name", "seat_price_cents", "seats",
                 "billable_seats", "period_end")
_REQUIRED_PLAN = ("name", "seat_price_cents")


def _vat_cents(amount_cents: int, vat_id) -> int:
    """Isolated VAT rule: 21% floored; reverse charge (0) when a VAT id is present."""
    if vat_id is not None and vat_id.strip():
        return 0
    return amount_cents * VAT_PERCENT // 100


def _nonneg_int(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative int")


def _validate(subscription, new_plan, changed_at):
    for k in _REQUIRED_SUB:
        if k not in subscription:
            raise ValueError(f"subscription missing {k}")
    for k in _REQUIRED_PLAN:
        if k not in new_plan:
            raise ValueError(f"new_plan missing {k}")
    _nonneg_int(subscription["billable_seats"], "billable_seats")
    _nonneg_int(subscription["seat_price_cents"], "seat_price_cents")
    _nonneg_int(new_plan["seat_price_cents"], "new seat_price_cents")
    for v, n in ((changed_at, "changed_at"), (subscription["period_end"], "period_end")):
        if not isinstance(v, datetime) or v.tzinfo is None or v.utcoffset() is None:
            raise ValueError(f"{n} must be a timezone-aware datetime")
    if not isinstance(subscription["plan_name"], str) or not isinstance(new_plan["name"], str):
        raise ValueError("plan names must be strings")
    vat_id = subscription.get("vat_id")
    if vat_id is not None and not isinstance(vat_id, str):
        raise ValueError("vat_id must be a string or None")


def _days_left(period_end, changed_at) -> int:
    days = (period_end - changed_at) // timedelta(hours=24)
    return max(0, min(PERIOD_DAYS, days))


def _description(prefix, plan, suffix):
    fixed = len(prefix) + len(suffix)
    if fixed + len(plan) > MAX_DESCRIPTION:
        room = MAX_DESCRIPTION - fixed - 3
        plan = plan[:max(room, 0)] + "..."
    return prefix + plan + suffix


def prorate_seats(subscription, new_plan, changed_at):
    _validate(subscription, new_plan, changed_at)
    if subscription["status"] in EXCLUDED_STATUSES:
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:
        return []
    period_end = subscription["period_end"]
    days = _days_left(period_end, changed_at)
    seats = subscription["billable_seats"]
    if days == 0 or seats == 0:
        return []

    credit = -(-(seats * old_price * days) // PERIOD_DAYS)  # round up
    charge = (seats * new_price * days) // PERIOD_DAYS      # round down

    suffix = f" seats, period ends {period_end.date().isoformat()}"
    out = []
    if credit >= MIN_LINE_CENTS:
        approver = SENIOR_APPROVER if credit > APPROVAL_THRESHOLD_CENTS else DEFAULT_APPROVER
        out.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit for unused ", subscription["plan_name"], suffix),
            "approved_by": approver,
        })
    if charge >= MIN_LINE_CENTS:
        out.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": _vat_cents(charge, subscription.get("vat_id")),
            "description": _description("Charge for prorated ", new_plan["name"], suffix),
            "approved_by": None,
        })
    return out


# ---------------------------------------------------------------- tests
import unittest
from datetime import timezone

UTC = timezone.utc
END = datetime(2026, 7, 31, tzinfo=UTC)


def _sub(**kw):
    s = {"id": "s1", "status": "active", "plan_name": "Basic", "seat_price_cents": 1000,
         "seats": 5, "billable_seats": 5, "vat_id": None, "period_end": END}
    s.update(kw)
    return s


def _at(days):
    return END - timedelta(days=days)


class ProrateTests(unittest.TestCase):
    def test_a1(self):
        r = prorate_seats(_sub(), {"name": "Pro", "seat_price_cents": 2000}, _at(15))
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
        self.assertEqual((r[0]["amount_cents"], r[0]["vat_cents"], r[0]["approved_by"]),
                         (2500, 0, "Win Tee Fung Tao"))
        self.assertEqual((r[1]["amount_cents"], r[1]["vat_cents"], r[1]["approved_by"]),
                         (5000, 1050, None))
        self.assertEqual(set(r[0]), {"subscription_id", "kind", "amount_cents",
                                     "vat_cents", "description", "approved_by"})

    def test_a2(self):
        r = prorate_seats(_sub(seat_price_cents=999, billable_seats=1),
                          {"name": "Pro", "seat_price_cents": 1999}, _at(7))
        self.assertEqual([(x["amount_cents"], x["vat_cents"]) for x in r], [(234, 0), (466, 97)])

    def test_a3_vat_id(self):
        for v, expected in (("NL123456789B01", 0), ("  ", 1050), ("", 1050), (None, 1050)):
            r = prorate_seats(_sub(vat_id=v), {"name": "Pro", "seat_price_cents": 2000}, _at(15))
            self.assertEqual(r[1]["vat_cents"], expected)
            self.assertEqual(r[0]["amount_cents"], 2500)
        s = _sub(); del s["vat_id"]
        self.assertEqual(prorate_seats(s, {"name": "P", "seat_price_cents": 2000}, _at(15))[1]["vat_cents"], 1050)

    def test_a4_approver(self):
        r = prorate_seats(_sub(seat_price_cents=5000, billable_seats=10),
                          {"name": "P", "seat_price_cents": 6000}, _at(30))
        self.assertEqual((r[0]["amount_cents"], r[0]["approved_by"]), (50000, "Win Tee Fung Tao"))
        r = prorate_seats(_sub(seat_price_cents=10000, billable_seats=10),
                          {"name": "P", "seat_price_cents": 11000}, _at(30))
        self.assertEqual((r[0]["amount_cents"], r[0]["approved_by"]), (100000, "Ramón Etxeberria-Goñi"))

    def test_a5_single_line(self):
        r = prorate_seats(_sub(seat_price_cents=100, billable_seats=1),
                          {"name": "P", "seat_price_cents": 200}, _at(10))
        self.assertEqual([(x["kind"], x["amount_cents"], x["vat_cents"]) for x in r],
                         [("charge", 66, 13)])

    def test_a6_empty(self):
        self.assertEqual(prorate_seats(_sub(seat_price_cents=100, billable_seats=1),
                                       {"name": "P", "seat_price_cents": 150}, _at(5)), [])

    def test_empty_cases(self):
        up = {"name": "P", "seat_price_cents": 2000}
        self.assertEqual(prorate_seats(_sub(seat_price_cents=3000), up, _at(15)), [])
        self.assertEqual(prorate_seats(_sub(seat_price_cents=2000), up, _at(15)), [])
        self.assertEqual(prorate_seats(_sub(status="trialing"), up, _at(15)), [])
        self.assertEqual(prorate_seats(_sub(), up, END), [])
        self.assertEqual(prorate_seats(_sub(), up, END + timedelta(days=1)), [])
        self.assertEqual(prorate_seats(_sub(billable_seats=0), up, _at(15)), [])
        self.assertNotEqual(prorate_seats(_sub(status="past_due"), up, _at(15)), [])

    def test_a9_long_name(self):
        r = prorate_seats(_sub(plan_name="x" * 200), {"name": "y" * 200, "seat_price_cents": 2000}, _at(15))
        for x in r:
            self.assertLessEqual(len(x["description"]), 80)
            self.assertIn("2026-07-31", x["description"])
            self.assertIn("...", x["description"])
        self.assertEqual(r[0]["description"].count("x"), 80 - len("Credit for unused ") -
                         len(" seats, period ends 2026-07-31") - 3)

    def test_descriptions(self):
        r = prorate_seats(_sub(), {"name": "Pro", "seat_price_cents": 2000}, _at(15))
        self.assertEqual(r[0]["description"], "Credit for unused Basic seats, period ends 2026-07-31")
        self.assertEqual(r[1]["description"], "Charge for prorated Pro seats, period ends 2026-07-31")

    def test_a10_seats_and_legacy_ignored(self):
        up = {"name": "P", "seat_price_cents": 2000}
        base = prorate_seats(_sub(seats=5), up, _at(15))
        self.assertEqual(base, prorate_seats(_sub(seats=50, legacy_discount="junk"), up, _at(15)))

    def test_a11_ints_and_float_hazard(self):
        r = prorate_seats(_sub(), {"name": "P", "seat_price_cents": 2000}, _at(15))
        for x in r:
            self.assertIs(type(x["amount_cents"]), int)
            self.assertIs(type(x["vat_cents"]), int)
        seats, old, days = 10**6, 10**10 + 1, 29
        n = seats * old * days
        r = prorate_seats(_sub(billable_seats=seats, seat_price_cents=old),
                          {"name": "P", "seat_price_cents": old + 1}, _at(days))
        self.assertEqual(r[0]["amount_cents"], -(-n // 30))
        import math
        self.assertNotEqual(math.ceil(n / 30), -(-n // 30))

    def test_timezone_date_and_partial_day(self):
        tz = timezone(timedelta(hours=14))
        pe = datetime(2026, 7, 31, 1, tzinfo=tz)
        r = prorate_seats(_sub(period_end=pe), {"name": "P", "seat_price_cents": 2000},
                          pe - timedelta(hours=47))
        self.assertIn("2026-07-31", r[0]["description"])
        self.assertEqual(r[0]["amount_cents"], -(-(5 * 1000 * 1) // 30) if False else 167)

    def test_validation(self):
        up = {"name": "P", "seat_price_cents": 2000}
        bad = [
            (_sub(billable_seats=True), up, _at(1)),
            (_sub(billable_seats=-1), up, _at(1)),
            (_sub(billable_seats=1.0), up, _at(1)),
            (_sub(seat_price_cents=True), up, _at(1)),
            (_sub(seat_price_cents=-5), up, _at(1)),
            (_sub(), {"name": "P", "seat_price_cents": -1}, _at(1)),
            (_sub(), {"name": "P"}, _at(1)),
            (_sub(), up, datetime(2026, 7, 1)),
            (_sub(period_end=datetime(2026, 7, 31)), up, _at(1)),
            (_sub(status="trialing", billable_seats=-1), up, _at(1)),
        ]
        for a in bad:
            with self.assertRaises(ValueError):
                prorate_seats(*a)
        s = _sub(); del s["period_end"]
        with self.assertRaises(ValueError):
            prorate_seats(s, up, _at(1))
        prorate_seats(_sub(billable_seats=9, seats=2), up, _at(1))  # allowed

    def test_no_mutation(self):
        import copy
        s, p = _sub(), {"name": "P", "seat_price_cents": 2000}
        s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
        prorate_seats(s, p, _at(15))
        self.assertEqual((s, p), (s0, p0))


if __name__ == "__main__":
    unittest.main()