# FILE: fernhollow_seats.py
# NOTE: This file was written without execution. No files were created and the tests below were NOT run.
# Open questions for the client:
# 1. billable_seats <= seats is not enforced (spec: note only).
# 2. Statuses other than active and trialing raise ValueError (provisional).
# 3. Downgrade and equal price return [] (provisional).
# 4. Credit lines always carry vat_cents 0. This overrides the house rule that VAT applies to credits too. Confirm with the client.
# 5. Whitespace-only plan names are rejected as empty. The spec only says "empty".
# 6. Approver is chosen by a hardcoded EUR 500 threshold. Confirm the names and routing.
# 7. Any non-blank vat_id means reverse charge, with no format check.
# 8. status and plan names must be str. id is required but its type is not checked.

from collections.abc import Mapping
from datetime import datetime
import unicodedata

PERIOD_US = 30 * 86400 * 1000000
_APPROVER_LOW = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
_APPROVER_HIGH = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")
_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def _int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _aware(value, name):
    if not isinstance(value, datetime):
        raise ValueError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _plan_name(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _micros(td):
    return (td.days * 86400 + td.seconds) * 10**6 + td.microseconds


def _description(kind, plan, period_end):
    if len(plan) > 43:
        plan = plan[:40] + "..."
    return f"{kind}: {plan} seats, period end {period_end.date().isoformat()}"


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, Mapping) or not isinstance(new_plan, Mapping):
        raise ValueError("subscription and new_plan must be mappings")
    for key in _SUB_KEYS:
        if key not in subscription:
            raise ValueError(f"subscription missing key {key!r}")
    for key in _PLAN_KEYS:
        if key not in new_plan:
            raise ValueError(f"new_plan missing key {key!r}")

    status = subscription["status"]
    plan_name = _plan_name(subscription["plan_name"], "plan_name")
    old = _int(subscription["seat_price_cents"], "seat_price_cents")
    _int(subscription["seats"], "seats")
    billable = _int(subscription["billable_seats"], "billable_seats")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise ValueError("vat_id must be a str or None")
    period_end = _aware(subscription["period_end"], "period_end")
    new_name = _plan_name(new_plan["name"], "new_plan name")
    new = _int(new_plan["seat_price_cents"], "new seat_price_cents")
    changed_at = _aware(changed_at, "changed_at")

    if not isinstance(status, str):
        raise ValueError("status must be a str")
    if status == "trialing":
        return []
    if status != "active":
        raise ValueError(f"unsupported status {status!r}")
    if new <= old:
        return []

    unused = _micros(period_end - changed_at)
    if unused <= 0 or billable == 0:
        return []

    credit = -((-(old * billable * unused)) // PERIOD_US)
    charge = (new * billable * unused) // PERIOD_US

    lines = []
    if credit >= 50:
        approver = _APPROVER_LOW if credit <= 50000 else _APPROVER_HIGH
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit", plan_name, period_end),
            "approved_by": approver,
        })
    if charge >= 50:
        if vat_id is None or not vat_id.strip():
            vat = charge * 21 // 100
        else:
            vat = 0
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description("Charge", new_name, period_end),
            "approved_by": None,
        })
    return lines


# FILE: test_fernhollow_seats.py
import copy
import datetime as dt
import unittest

from fernhollow_seats import prorate_seats

UTC = dt.timezone.utc
PE = dt.datetime(2026, 11, 30, tzinfo=UTC)
CH15 = PE - dt.timedelta(days=15)
THAO = "Nguyễn Thị Phương Thảo"
RAMON = "Ramón Etxeberria-Goñi"
CRED_PRO = "Credit: Pro seats, period end 2026-11-30"
ENT = "Charge: Enterprise seats, period end 2026-11-30"


def sub(**kw):
    d = {"id": "sub_1", "status": "active", "plan_name": "Pro",
         "seat_price_cents": 1000, "seats": 10, "billable_seats": 8,
         "vat_id": None, "period_end": PE}
    d.update(kw)
    return d


def plan(name="Enterprise", price=2000):
    return {"name": name, "seat_price_cents": price}


def cr(amount, desc, approver):
    return {"subscription_id": "sub_1", "kind": "credit", "amount_cents": amount,
            "vat_cents": 0, "description": desc, "approved_by": approver}


def ch(amount, vat, desc):
    return {"subscription_id": "sub_1", "kind": "charge", "amount_cents": amount,
            "vat_cents": vat, "description": desc, "approved_by": None}


def _walk(v):
    yield v
    if isinstance(v, dict):
        for x in v.values():
            yield from _walk(x)
    elif isinstance(v, list):
        for x in v:
            yield from _walk(x)


class SeatProrationTests(unittest.TestCase):

    def test_t01_baseline(self):
        self.assertEqual(prorate_seats(sub(), plan(), CH15),
                         [cr(4000, CRED_PRO, THAO), ch(8000, 1680, ENT)])

    def test_t02_seats_ignored(self):
        self.assertEqual(prorate_seats(sub(seats=100, billable_seats=8), plan(), CH15),
                         [cr(4000, CRED_PRO, THAO), ch(8000, 1680, ENT)])

    def test_t03_thirty_day_period(self):
        pe = dt.datetime(2026, 12, 31, tzinfo=UTC)
        out = prorate_seats(sub(period_end=pe), plan(), pe - dt.timedelta(days=15))
        self.assertEqual(out, [
            cr(4000, "Credit: Pro seats, period end 2026-12-31", THAO),
            ch(8000, 1680, "Charge: Enterprise seats, period end 2026-12-31"),
        ])

    def test_t04_downgrade(self):
        self.assertEqual(prorate_seats(sub(), plan(price=800), CH15), [])

    def test_t05_rounding_both_ways(self):
        out = prorate_seats(sub(billable_seats=1), plan(price=1001),
                            PE - dt.timedelta(days=10))
        self.assertEqual(out, [cr(334, CRED_PRO, THAO), ch(333, 69, ENT)])

    def test_t06_boundary_50_kept(self):
        out = prorate_seats(sub(billable_seats=1, seat_price_cents=100),
                            plan(price=200), CH15)
        self.assertEqual(out, [cr(50, CRED_PRO, THAO), ch(100, 21, ENT)])

    def test_t07_boundary_49_dropped(self):
        out = prorate_seats(sub(billable_seats=1, seat_price_cents=98),
                            plan(price=196), CH15)
        self.assertEqual(out, [ch(98, 20, ENT)])

    def test_t08_reverse_charge(self):
        out = prorate_seats(sub(vat_id="DE123456789"), plan(), CH15)
        self.assertEqual(out, [cr(4000, CRED_PRO, THAO), ch(8000, 0, ENT)])

    def test_t09_blank_vat_id(self):
        for v in ("", "   "):
            with self.subTest(vat_id=v):
                out = prorate_seats(sub(vat_id=v), plan(), CH15)
                self.assertEqual(out, [cr(4000, CRED_PRO, THAO), ch(8000, 1680, ENT)])

    def test_t10_trialing(self):
        self.assertEqual(prorate_seats(sub(status="trialing"), plan(), CH15), [])

    def test_t11_description_exactly_80(self):
        out = prorate_seats(sub(plan_name="A" * 43), plan(), CH15)
        self.assertEqual(out, [
            cr(4000, "Credit: " + "A" * 43 + " seats, period end 2026-11-30", THAO),
            ch(8000, 1680, ENT),
        ])
        self.assertEqual(len(out[0]["description"]), 80)

    def test_t12_credit_description_truncated(self):
        out = prorate_seats(sub(plan_name="B" * 60), plan(), CH15)
        desc = "Credit: " + "B" * 40 + "..." + " seats, period end 2026-11-30"
        self.assertEqual(out, [cr(4000, desc, THAO), ch(8000, 1680, ENT)])
        self.assertEqual(len(out[0]["description"]), 80)

    def test_t13_charge_description_truncated(self):
        out = prorate_seats(sub(), plan(name="C" * 44), CH15)
        desc = "Charge: " + "C" * 40 + "..." + " seats, period end 2026-11-30"
        self.assertEqual(out, [cr(4000, CRED_PRO, THAO), ch(8000, 1680, desc)])
        self.assertEqual(len(out[1]["description"]), 80)

    def test_t14_credit_exactly_500(self):
        out = prorate_seats(sub(seat_price_cents=50000, billable_seats=1),
                            plan(price=100000), PE - dt.timedelta(days=30))
        self.assertEqual(out, [cr(50000, CRED_PRO, THAO), ch(100000, 21000, ENT)])

    def test_t15_credit_just_over_500(self):
        out = prorate_seats(sub(seat_price_cents=50001, billable_seats=1),
                            plan(price=100000), PE - dt.timedelta(days=30))
        self.assertEqual(out, [cr(50001, CRED_PRO, RAMON), ch(100000, 21000, ENT)])

    def test_t16_legacy_discount_ignored(self):
        out = prorate_seats(sub(legacy_discount=25), plan(), CH15)
        self.assertEqual(out, [cr(4000, CRED_PRO, THAO), ch(8000, 1680, ENT)])

    def test_t17_zero_billable(self):
        self.assertEqual(prorate_seats(sub(billable_seats=0), plan(), CH15), [])

    def test_t18_period_ended(self):
        self.assertEqual(prorate_seats(sub(), plan(), PE + dt.timedelta(days=1)), [])
        self.assertEqual(prorate_seats(sub(), plan(), PE), [])

    def test_t19_equal_price(self):
        self.assertEqual(prorate_seats(sub(), plan(price=1000), CH15), [])

    def test_t20_other_statuses_raise(self):
        for status in ("canceled", "past_due"):
            with self.subTest(status=status):
                with self.assertRaises(ValueError):
                    prorate_seats(sub(status=status), plan(), CH15)

    def test_t21_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            prorate_seats(sub(), plan(), dt.datetime(2026, 11, 15))
        missing = sub()
        del missing["billable_seats"]
        with self.assertRaises(ValueError):
            prorate_seats(missing, plan(), CH15)
        with self.assertRaises(ValueError):
            prorate_seats(sub(seat_price_cents=10.5), plan(), CH15)
        with self.assertRaises(ValueError):
            prorate_seats(sub(seat_price_cents="1000"), plan(), CH15)
        with self.assertRaises(ValueError):
            prorate_seats(sub(billable_seats=True), plan(), CH15)

    def test_t22_date_in_own_zone(self):
        pe = dt.datetime(2026, 11, 30, 23, 30,
                         tzinfo=dt.timezone(dt.timedelta(hours=-5)))
        out = prorate_seats(sub(period_end=pe), plan(), pe - dt.timedelta(days=15))
        self.assertEqual(out, [cr(4000, CRED_PRO, THAO), ch(8000, 1680, ENT)])

    def test_t23_fractional_days(self):
        out = prorate_seats(sub(billable_seats=1, seat_price_cents=1000),
                            plan(price=2000), PE - dt.timedelta(hours=12))
        self.assertEqual(out, [cr(17, CRED_PRO, THAO), ch(33, 6, ENT)])

    def test_t24_credit_dropped_charge_kept(self):
        out = prorate_seats(sub(billable_seats=1, seat_price_cents=98),
                            plan(price=300), CH15)
        self.assertEqual(out, [ch(150, 31, ENT)])

    def test_amounts_are_int(self):
        out = prorate_seats(sub(), plan(), CH15)
        for line in out:
            self.assertIs(type(line["amount_cents"]), int)
            self.assertIs(type(line["vat_cents"]), int)

    def test_no_float_anywhere(self):
        out = prorate_seats(sub(billable_seats=1, seat_price_cents=1000),
                            plan(price=2000), PE - dt.timedelta(hours=12))
        for v in _walk(out):
            self.assertNotIsInstance(v, float)

    def test_input_not_mutated(self):
        s = sub(legacy_discount=25)
        p = plan()
        s_before, p_before = copy.deepcopy(s), copy.deepcopy(p)
        prorate_seats(s, p, CH15)
        self.assertEqual(s, s_before)
        self.assertEqual(p, p_before)


if __name__ == "__main__":
    unittest.main()