# -*- coding: utf-8 -*-
# Seat proration for mid-period upgrades. All money is integer EUR cents.
# Run the bundled unit tests with: python3 seat_proration.py
import math
import unittest
from datetime import datetime, timedelta, timezone
from fractions import Fraction

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")
_PERIOD_US = 30 * 86400 * 10 ** 6
_MIN_LINE_CENTS = 50
_VAT_PERCENT = 21
_CREDIT_TPL = "Credit for unused {name} seats, period ends {date}"
_CHARGE_TPL = "Charge for unused {name} seats, period ends {date}"
_DEFAULT_APPROVER = "Win Tee Fung Tao"
_LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
_LARGE_CREDIT_CENTS = 50000
_MAX_DESC = 80


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _check_money(name, v):
    if not _is_int(v):
        raise TypeError(f"{name} must be int")
    if v <= 0:
        raise ValueError(f"{name} must be > 0")


def _check_plan_name(name, v):
    if not isinstance(v, str):
        raise TypeError(f"{name} must be str")
    if not v.strip():
        raise ValueError(f"{name} must be non-empty")
    return v.strip()


def _check_aware(name, v):
    if not isinstance(v, datetime) or v.tzinfo is None or v.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _describe(tpl, name, date_s):
    budget = _MAX_DESC - len(tpl.format(name="", date=date_s))
    if budget <= 0:
        raise ValueError("no room for plan name in description")
    if len(name) > budget:
        name = name[:budget - 3].rstrip() + "..." if budget >= 4 else name[:budget]
    desc = tpl.format(name=name, date=date_s)
    assert len(desc) <= _MAX_DESC and date_s in desc
    return desc


def _line(sub_id, kind, amount, vat, desc, approved_by):
    return {
        "subscription_id": sub_id,
        "kind": kind,
        "amount_cents": amount,
        "vat_cents": vat,
        "description": desc,
        "approved_by": approved_by,
    }


def prorate_seats(subscription: dict, new_plan: dict, changed_at: datetime) -> list[dict]:
    missing = [k for k in _SUB_KEYS if k not in subscription]
    missing += [f"new_plan.{k}" for k in _PLAN_KEYS if k not in new_plan]
    if missing:
        raise ValueError("missing keys: " + ", ".join(missing))

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    _check_money("seat_price_cents", old_price)
    _check_money("new_plan seat_price_cents", new_price)

    billable = subscription["billable_seats"]
    seats = subscription["seats"]
    if not _is_int(billable):
        raise TypeError("billable_seats must be int")
    if not _is_int(seats):
        raise TypeError("seats must be int")
    if billable < 0:
        raise ValueError("billable_seats must be >= 0")
    if seats < billable:
        raise ValueError("billable_seats must not exceed seats")

    old_name = _check_plan_name("plan_name", subscription["plan_name"])
    new_name = _check_plan_name("new_plan name", new_plan["name"])

    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be str or None")
    reverse_charge = vat_id is not None and vat_id.strip() != ""

    _check_aware("changed_at", changed_at)
    period_end = subscription["period_end"]
    _check_aware("period_end", period_end)

    status = subscription["status"]
    if status == "trialing":
        return []
    if status != "active":
        raise ValueError(f"unsupported status: {status!r}")

    if new_price <= old_price:
        return []

    if changed_at >= period_end:
        return []
    remaining_us = (period_end - changed_at) // timedelta(microseconds=1)
    fraction = Fraction(remaining_us, _PERIOD_US)
    if fraction > 1:
        raise ValueError("remaining time exceeds the 30-day period")

    credit_net = math.ceil(Fraction(old_price * billable) * fraction)
    charge_net = math.floor(Fraction(new_price * billable) * fraction)

    sub_id = subscription["id"]
    date_s = period_end.date().isoformat()
    lines = []
    if credit_net >= _MIN_LINE_CENTS:
        approver = (_LARGE_CREDIT_APPROVER if credit_net > _LARGE_CREDIT_CENTS
                    else _DEFAULT_APPROVER)
        lines.append(_line(sub_id, "credit", credit_net, 0,
                           _describe(_CREDIT_TPL, old_name, date_s), approver))
    if charge_net >= _MIN_LINE_CENTS:
        vat = 0 if reverse_charge else (charge_net * _VAT_PERCENT) // 100
        lines.append(_line(sub_id, "charge", charge_net, vat,
                           _describe(_CHARGE_TPL, new_name, date_s), None))
    return lines


# ---------------- tests ----------------

UTC = timezone.utc
PE = datetime(2026, 11, 30, 12, 0, tzinfo=UTC)


def _sub(**kw):
    base = {"id": "sub_1", "status": "active", "plan_name": "Pro",
            "seat_price_cents": 1000, "seats": 10, "billable_seats": 10,
            "vat_id": None, "period_end": PE}
    base.update(kw)
    return base


def _plan(price=1500, name="Business"):
    return {"name": name, "seat_price_cents": price}


def _before(**kw):
    return PE - timedelta(**kw)


class SeatProrationTests(unittest.TestCase):

    def test_worked_example(self):
        c, ch = prorate_seats(_sub(), _plan(1500), _before(days=15))
        self.assertEqual((c["kind"], c["amount_cents"], c["vat_cents"], c["approved_by"]),
                         ("credit", 5000, 0, "Win Tee Fung Tao"))
        self.assertEqual((ch["kind"], ch["amount_cents"], ch["vat_cents"], ch["approved_by"]),
                         ("charge", 7500, 1575, None))

    def test_credit_ceil_one_third(self):
        c, ch = prorate_seats(_sub(billable_seats=1, seats=1), _plan(1500), _before(days=10))
        self.assertEqual(c["amount_cents"], 334)
        self.assertEqual((ch["amount_cents"], ch["vat_cents"]), (500, 105))

    def test_fractional_days_ceil_and_floor(self):
        # fraction 1/20: credit 1001/20 = 50.05 -> 51; charge 1501/20 = 75.05 -> 75
        c, ch = prorate_seats(_sub(seat_price_cents=1001, billable_seats=1, seats=1),
                              _plan(1501), _before(days=1, hours=12))
        self.assertEqual(c["amount_cents"], 51)
        self.assertEqual((ch["amount_cents"], ch["vat_cents"]), (75, 15))

    def test_charge_floor_kept_credit_ceil(self):
        # fraction 0.33: credit 149*0.33=49.17 -> 50 (kept); charge 150*0.33=49.5 -> 49 (skipped)
        lines = prorate_seats(_sub(seat_price_cents=149, billable_seats=1, seats=1),
                              _plan(150), _before(days=9, hours=21, minutes=36))
        self.assertEqual(len(lines), 1)
        self.assertEqual((lines[0]["kind"], lines[0]["amount_cents"]), ("credit", 50))

    def test_credit_skipped_charge_kept(self):
        lines = prorate_seats(_sub(seat_price_cents=1, billable_seats=10, seats=10),
                              _plan(1000), _before(days=15))
        self.assertEqual(len(lines), 1)
        self.assertEqual((lines[0]["kind"], lines[0]["amount_cents"], lines[0]["vat_cents"]),
                         ("charge", 5000, 1050))

    def test_charge_skipped_credit_kept(self):
        lines = prorate_seats(_sub(seat_price_cents=149, billable_seats=1, seats=1),
                              _plan(150), _before(days=9, hours=21, minutes=36))
        self.assertEqual([l["kind"] for l in lines], ["credit"])

    def test_downgrade_and_equal_price_return_empty(self):
        self.assertEqual(prorate_seats(_sub(seat_price_cents=1500), _plan(1000), _before(days=15)), [])
        self.assertEqual(prorate_seats(_sub(seat_price_cents=1000), _plan(1000), _before(days=15)), [])

    def test_trialing_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(), _before(days=15)), [])

    def test_unknown_status_raises(self):
        for status in ("canceled", "past_due", "unpaid"):
            with self.subTest(status=status):
                with self.assertRaises(ValueError):
                    prorate_seats(_sub(status=status), _plan(), _before(days=15))

    def test_uses_billable_seats_not_seats(self):
        a = prorate_seats(_sub(seats=20, billable_seats=10), _plan(), _before(days=15))
        b = prorate_seats(_sub(seats=10, billable_seats=10), _plan(), _before(days=15))
        self.assertEqual(a, b)

    def test_zero_billable_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(billable_seats=0), _plan(), _before(days=15)), [])

    def test_billable_validation(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(seats=5, billable_seats=6), _plan(), _before(days=15))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(billable_seats=-1), _plan(), _before(days=15))
        with self.assertRaises(TypeError):
            prorate_seats(_sub(billable_seats=10.0), _plan(), _before(days=15))
        with self.assertRaises(TypeError):
            prorate_seats(_sub(billable_seats=True), _plan(), _before(days=15))

    def test_price_validation(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(seat_price_cents=0), _plan(), _before(days=15))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(-5), _before(days=15))
        with self.assertRaises(TypeError):
            prorate_seats(_sub(seat_price_cents=10.0), _plan(), _before(days=15))
        with self.assertRaises(TypeError):
            prorate_seats(_sub(), _plan(True), _before(days=15))

    def test_missing_keys_named(self):
        bad = _sub()
        del bad["vat_id"]
        with self.assertRaises(ValueError) as cm:
            prorate_seats(bad, _plan(), _before(days=15))
        self.assertIn("vat_id", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            prorate_seats(_sub(), {"seat_price_cents": 1500}, _before(days=15))
        self.assertIn("name", str(cm.exception))

    def test_naive_datetime_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(), datetime(2026, 11, 15, 12))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(period_end=datetime(2026, 11, 30, 12)), _plan(), _before(days=15))

    def test_changed_at_equal_or_after_period_end_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(), PE), [])
        self.assertEqual(prorate_seats(_sub(), _plan(), PE + timedelta(hours=1)), [])

    def test_more_than_30_days_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(), _before(days=31))

    def test_exactly_30_days_works(self):
        c, ch = prorate_seats(_sub(), _plan(1500), _before(days=30))
        self.assertEqual(c["amount_cents"], 10000)
        self.assertEqual((ch["amount_cents"], ch["vat_cents"]), (15000, 3150))

    def test_vat_rules(self):
        _, ch = prorate_seats(_sub(vat_id=None), _plan(1500), _before(days=15))
        self.assertEqual(ch["vat_cents"], 1575)
        _, ch = prorate_seats(_sub(vat_id=""), _plan(1500), _before(days=15))
        self.assertEqual(ch["vat_cents"], 1575)
        c, ch = prorate_seats(_sub(vat_id="DE123456789"), _plan(1500), _before(days=15))
        self.assertEqual((c["vat_cents"], ch["vat_cents"]), (0, 0))

    def test_descriptions_short_and_date_rendered(self):
        c, ch = prorate_seats(_sub(), _plan(1500), _before(days=15))
        self.assertEqual(c["description"], "Credit for unused Pro seats, period ends 2026-11-30")
        self.assertEqual(ch["description"], "Charge for unused Business seats, period ends 2026-11-30")

    def test_long_plan_name_shortened_date_intact(self):
        c, _ = prorate_seats(_sub(plan_name="P" * 200), _plan(1500), _before(days=15))
        self.assertLessEqual(len(c["description"]), 80)
        self.assertTrue(c["description"].endswith("..."))
        self.assertIn("2026-11-30", c["description"])

    def test_date_uses_period_end_own_timezone(self):
        pe = datetime(2026, 11, 30, 1, 0, tzinfo=timezone(timedelta(hours=5)))
        c, ch = prorate_seats(_sub(period_end=pe), _plan(1500), pe - timedelta(days=15))
        for line in (c, ch):
            self.assertIn("2026-11-30", line["description"])
            self.assertNotIn("2026-11-29", line["description"])

    def test_different_zones_same_instant_difference(self):
        changed = datetime(2026, 11, 15, 7, 0, tzinfo=timezone(timedelta(hours=-5)))  # 12:00 UTC
        c, _ = prorate_seats(_sub(), _plan(1500), changed)
        self.assertEqual(c["amount_cents"], 5000)

    def test_approver_threshold(self):
        c, _ = prorate_seats(_sub(seat_price_cents=50000, billable_seats=1, seats=1),
                             _plan(60000), _before(days=30))
        self.assertEqual((c["amount_cents"], c["approved_by"]), (50000, "Win Tee Fung Tao"))
        c, _ = prorate_seats(_sub(seat_price_cents=50001, billable_seats=1, seats=1),
                             _plan(60000), _before(days=30))
        self.assertEqual((c["amount_cents"], c["approved_by"]), (50001, "Ramón Etxeberria-Goñi"))

    def test_output_shape_and_order(self):
        lines = prorate_seats(_sub(), _plan(1500), _before(days=15))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        for line in lines:
            self.assertEqual(set(line), {"subscription_id", "kind", "amount_cents",
                                         "vat_cents", "description", "approved_by"})
            self.assertEqual(line["subscription_id"], "sub_1")
            self.assertIsInstance(line["amount_cents"], int)
            self.assertIsInstance(line["vat_cents"], int)

    def test_legacy_discount_ignored(self):
        plain = prorate_seats(_sub(), _plan(1500), _before(days=15))
        with_legacy = prorate_seats(_sub(legacy_discount="garbage"), _plan(1500), _before(days=15))
        self.assertEqual(plain, with_legacy)

    def test_plan_name_must_be_non_empty(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(plan_name="   "), _plan(), _before(days=15))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(name=""), _before(days=15))


if __name__ == "__main__":
    unittest.main()