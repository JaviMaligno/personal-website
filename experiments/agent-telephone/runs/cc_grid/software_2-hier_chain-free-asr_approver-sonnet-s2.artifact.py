"""Fernhollow Studios seat-upgrade proration (single module, standard library only).

Decisions:
- Currency is EUR; amounts are integer cents. No floats anywhere (int and Fraction).
- status "trialing" -> no lines. Other statuses are prorated normally.
- changed_at >= period_end -> no lines (zero days left).
- New price <= old price (downgrade or same price) -> no lines; a downgrade
  applies at renewal and a same-price change would cancel out.
- Billing uses billable_seats, not seats (seats includes deactivated users).
  billable_seats == 0 -> no lines.
- Days left is fractional (exact Fraction of seconds/86400), capped at 30. A
  period is always 30 days. Fractional because truncating would shortchange
  the customer on credits.
- credit = ceil(old * billable * days / 30); charge = floor(new * billable *
  days / 30). Rounding never favours the company.
- Each line is dropped independently if its pre-VAT amount is < 50 cents;
  exactly 50 is kept.
- Amounts are positive; kind carries the sign.
- VAT: credits always 0. Charges 21% floored (amount*21//100), unless vat_id
  is a non-blank string (reverse charge) -> 0.
- approved_by on credits: "Win Tee Fung Tao"; strictly more than 50000 cents
  (500 EUR) -> "Ramón Etxeberria-Goñi". Charges: None.
- Descriptions are <= 80 chars, name the plan and end with period_end's own
  calendar date (YYYY-MM-DD, no tz conversion). Only the plan name is
  shortened (ending in "...") if needed.
- legacy_discount is ignored entirely.
- Naive datetimes raise ValueError; non-int (incl. bool/float) prices or
  seats raise TypeError; negatives raise ValueError.

NOTE: this agent had no tools, so the tests below are embedded in this module
(run with python -m unittest, or pytest) and were NOT executed by me. If a
separate test_prorate_seats.py is wanted, move the TestCase class there.
"""
import math
import unittest
from datetime import datetime, timedelta, timezone
from fractions import Fraction

__all__ = ["prorate_seats"]

_MAX_DESC = 80
_MIN_LINE = 50
_APPROVER = "Win Tee Fung Tao"
_SENIOR_APPROVER = "Ramón Etxeberria-Goñi"
_SENIOR_THRESHOLD = 50000


def _int(value, label):
    if type(value) is not int:
        raise TypeError(f"{label} must be an int")
    if value < 0:
        raise ValueError(f"{label} must not be negative")
    return value


def _aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value


def _describe(prefix, name, suffix):
    budget = _MAX_DESC - len(prefix) - len(suffix)
    name = str(name)
    if len(name) > budget:
        name = name[: budget - 3] + "..." if budget >= 3 else "..."[: max(budget, 0)]
    return prefix + name + suffix


def prorate_seats(subscription, new_plan, changed_at):
    old_price = _int(subscription["seat_price_cents"], "seat_price_cents")
    _int(subscription["seats"], "seats")
    billable = _int(subscription["billable_seats"], "billable_seats")
    new_price = _int(new_plan["seat_price_cents"], "new seat_price_cents")
    period_end = _aware(subscription["period_end"], "period_end")
    changed_at = _aware(changed_at, "changed_at")

    if subscription["status"] == "trialing":
        return []
    if changed_at >= period_end:
        return []
    if new_price <= old_price:
        return []
    if billable == 0:
        return []

    delta = period_end - changed_at
    seconds = Fraction(delta.days * 86400 + delta.seconds) + Fraction(delta.microseconds, 10**6)
    days_left = min(seconds / 86400, Fraction(30))

    credit = math.ceil(Fraction(old_price * billable) * days_left / 30)
    charge = math.floor(Fraction(new_price * billable) * days_left / 30)

    date = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    if credit >= _MIN_LINE:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit unused ", subscription["plan_name"], f" until {date}"),
            "approved_by": _SENIOR_APPROVER if credit > _SENIOR_THRESHOLD else _APPROVER,
        })

    if charge >= _MIN_LINE:
        vat_id = subscription.get("vat_id")
        reverse = isinstance(vat_id, str) and bool(vat_id.strip())
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * 21 // 100,
            "description": _describe("Charge ", new_plan["name"], f" until {date}"),
            "approved_by": None,
        })

    return lines


# ----------------------------------------------------------------- tests ---
UTC = timezone.utc
T0 = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 500, "seats": 1, "billable_seats": 1,
         "vat_id": None, "period_end": T0 + timedelta(days=10)}
    s.update(kw)
    return s


def _plan(price=1000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


class ProrateSeatsTests(unittest.TestCase):
    def test_rounding_example(self):
        r = prorate_seats(_sub(), _plan(), T0)
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
        self.assertEqual(r[0]["amount_cents"], 167)
        self.assertEqual(r[1]["amount_cents"], 333)

    def test_ordering_and_keys(self):
        r = prorate_seats(_sub(), _plan(), T0)
        self.assertEqual(set(r[0]), {"subscription_id", "kind", "amount_cents",
                                     "vat_cents", "description", "approved_by"})
        self.assertEqual(r[0]["subscription_id"], "sub_1")

    def test_billable_vs_seats(self):
        r = prorate_seats(_sub(seats=10, billable_seats=2), _plan(), T0)
        self.assertEqual(r[0]["amount_cents"], 334)
        self.assertEqual(r[1]["amount_cents"], 666)

    def test_zero_billable(self):
        self.assertEqual(prorate_seats(_sub(billable_seats=0), _plan(), T0), [])

    def test_30_day_month(self):
        r = prorate_seats(_sub(period_end=T0 + timedelta(days=30)), _plan(), T0)
        self.assertEqual((r[0]["amount_cents"], r[1]["amount_cents"]), (500, 1000))

    def test_cap_at_30(self):
        r = prorate_seats(_sub(period_end=T0 + timedelta(days=30)), _plan(), T0 - timedelta(days=60))
        self.assertEqual((r[0]["amount_cents"], r[1]["amount_cents"]), (500, 1000))

    def test_downgrade_and_same_price(self):
        self.assertEqual(prorate_seats(_sub(), _plan(100), T0), [])
        self.assertEqual(prorate_seats(_sub(), _plan(500), T0), [])

    def test_trialing(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(), T0), [])

    def test_other_status_prorated(self):
        self.assertEqual(len(prorate_seats(_sub(status="past_due"), _plan(), T0)), 2)

    def test_credit_below_threshold_only(self):
        r = prorate_seats(_sub(seat_price_cents=100), _plan(1000), T0)
        self.assertEqual([x["kind"] for x in r], ["charge"])

    def test_charge_below_threshold_only(self):
        r = prorate_seats(_sub(seat_price_cents=148), _plan(149), T0)
        self.assertEqual([x["kind"] for x in r], ["credit"])
        self.assertEqual(r[0]["amount_cents"], 50)

    def test_exactly_50_kept(self):
        r = prorate_seats(_sub(seat_price_cents=150), _plan(151), T0)
        self.assertEqual([x["amount_cents"] for x in r], [50, 50])

    def test_vat_floor(self):
        r = prorate_seats(_sub(), _plan(), T0)
        self.assertEqual(r[1]["vat_cents"], 69)

    def test_reverse_charge(self):
        r = prorate_seats(_sub(vat_id="DE123"), _plan(), T0)
        self.assertEqual(r[1]["vat_cents"], 0)

    def test_blank_vat_id_is_none(self):
        r = prorate_seats(_sub(vat_id="   "), _plan(), T0)
        self.assertEqual(r[1]["vat_cents"], 69)

    def test_credit_no_vat(self):
        self.assertEqual(prorate_seats(_sub(), _plan(), T0)[0]["vat_cents"], 0)

    def test_approver_switch(self):
        end = T0 + timedelta(days=30)
        a = prorate_seats(_sub(seat_price_cents=50000, period_end=end), _plan(60000), T0)
        b = prorate_seats(_sub(seat_price_cents=50001, period_end=end), _plan(60000), T0)
        self.assertEqual(a[0]["approved_by"], "Win Tee Fung Tao")
        self.assertEqual(b[0]["approved_by"], "Ramón Etxeberria-Goñi")

    def test_charge_approver_none(self):
        self.assertIsNone(prorate_seats(_sub(), _plan(), T0)[1]["approved_by"])

    def test_description_length_and_date(self):
        r = prorate_seats(_sub(plan_name="A" * 500), _plan(name="B" * 500), T0)
        for x in r:
            self.assertLessEqual(len(x["description"]), 80)
            self.assertIn("2026-03-11", x["description"])
            self.assertIn("...", x["description"])

    def test_description_short_names_intact(self):
        r = prorate_seats(_sub(), _plan(), T0)
        self.assertEqual(r[0]["description"], "Credit unused Basic until 2026-03-11")
        self.assertEqual(r[1]["description"], "Charge Pro until 2026-03-11")

    def test_changed_at_on_or_after_end(self):
        end = _sub()["period_end"]
        self.assertEqual(prorate_seats(_sub(), _plan(), end), [])
        self.assertEqual(prorate_seats(_sub(), _plan(), end + timedelta(hours=1)), [])

    def test_partial_day(self):
        s = _sub(seat_price_cents=6000, period_end=T0 + timedelta(hours=12))
        r = prorate_seats(s, _plan(12000), T0)
        self.assertEqual((r[0]["amount_cents"], r[1]["amount_cents"]), (100, 200))

    def test_naive_datetime(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(), datetime(2026, 3, 1))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(period_end=datetime(2026, 3, 11)), _plan(), T0)

    def test_type_errors(self):
        with self.assertRaises(TypeError):
            prorate_seats(_sub(seat_price_cents=5.0), _plan(), T0)
        with self.assertRaises(TypeError):
            prorate_seats(_sub(), _plan(1000.0), T0)
        with self.assertRaises(TypeError):
            prorate_seats(_sub(billable_seats=True), _plan(), T0)

    def test_negative(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(seats=-1), _plan(), T0)

    def test_legacy_discount_ignored(self):
        a = prorate_seats(_sub(), _plan(), T0)
        b = prorate_seats(_sub(legacy_discount=50), _plan(), T0)
        self.assertEqual(a, b)

    def test_all_ints(self):
        for x in prorate_seats(_sub(), _plan(), T0):
            self.assertIs(type(x["amount_cents"]), int)
            self.assertIs(type(x["vat_cents"]), int)
            self.assertGreater(x["amount_cents"], 0)


if __name__ == "__main__":
    unittest.main()