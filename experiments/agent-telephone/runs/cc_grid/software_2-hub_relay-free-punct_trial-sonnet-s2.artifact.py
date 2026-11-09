"""Fernhollow Studios seat proration (stdlib only, integer arithmetic only).

Public entry point: prorate_seats(subscription, new_plan, changed_at).
Tests are at the bottom of this module: python -m unittest <this_module>

Open assumptions, each changeable via a constant or helper:
- Day counting: _days_left() uses the calendar-date difference in period_end's
  timezone, clamped to 0..PERIOD_DAYS.
- Equal prices proceed normally; only strictly lower new prices return [] (_is_downgrade).
- VAT is floored: amount * VAT_PERCENT // 100 (_vat_for_charge).
- Only status "trialing" is excluded (NO_PRORATION_STATUSES).
- Credits carry vat_cents 0 (CREDIT_VAT_CENTS), per the explicit spec. This
  overrides the house default of VAT on every line.
- Lines under MIN_LINE_CENTS are dropped, each judged independently.
- billable_seats is required; there is no fallback to seats.
- legacy_discount is never read.
"""
from datetime import datetime

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
CREDIT_VAT_CENTS = 0
NO_PRORATION_STATUSES = frozenset({"trialing"})
MAX_DESCRIPTION_LEN = 80
APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
APPROVER_HIGH = "Ramón Etxeberria-Goñi"
HIGH_CREDIT_THRESHOLD_CENTS = 50000  # strictly greater than this needs APPROVER_HIGH


def _check_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _check_str(value, name):
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a str")
    return value


def _check_aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _days_left(period_end, changed_at):
    local = changed_at.astimezone(period_end.tzinfo)
    delta = (period_end.date() - local.date()).days
    return max(0, min(PERIOD_DAYS, delta))


def _is_downgrade(old_price, new_price):
    return new_price < old_price


def _vat_for_charge(amount, vat_id):
    if vat_id is not None and vat_id.strip():
        return 0
    return amount * VAT_PERCENT // 100


def _describe(verb, plan_name, date_str):
    template = f"{verb} unused {{}} to {date_str}"
    avail = MAX_DESCRIPTION_LEN - len(template.format(""))
    if len(plan_name) > avail:
        plan_name = plan_name[: avail - 3] + "..."
    return template.format(plan_name)


def prorate_seats(subscription, new_plan, changed_at):
    sub_id = subscription["id"]
    status = subscription["status"]
    old_name = _check_str(subscription["plan_name"], "plan_name")
    old_price = _check_int(subscription["seat_price_cents"], "seat_price_cents")
    _check_int(subscription["seats"], "seats")
    if "billable_seats" not in subscription or subscription["billable_seats"] is None:
        raise ValueError("billable_seats is required")
    seats = _check_int(subscription["billable_seats"], "billable_seats")
    vat_id = subscription.get("vat_id")
    if vat_id is not None:
        _check_str(vat_id, "vat_id")
    period_end = _check_aware(subscription["period_end"], "period_end")
    _check_aware(changed_at, "changed_at")
    new_name = _check_str(new_plan["name"], "new_plan name")
    new_price = _check_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")

    if status in NO_PRORATION_STATUSES or seats == 0:
        return []
    if _is_downgrade(old_price, new_price):
        return []

    days = _days_left(period_end, changed_at)
    date_str = period_end.strftime("%Y-%m-%d")
    lines = []

    credit = -(-(old_price * seats * days) // PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        approver = (APPROVER_HIGH if credit > HIGH_CREDIT_THRESHOLD_CENTS
                    else APPROVER_DEFAULT)
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": CREDIT_VAT_CENTS,
            "description": _describe("Credit", old_name, date_str),
            "approved_by": approver,
        })

    charge = new_price * seats * days // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": _vat_for_charge(charge, vat_id),
            "description": _describe("Charge", new_name, date_str),
            "approved_by": None,
        })
    return lines


# ---------------------------------------------------------------- tests
import copy
import unicodedata
import unittest
from datetime import timedelta, timezone

_UTC = timezone.utc
_END = datetime(2025, 1, 31, 12, 0, tzinfo=_UTC)


def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 5, "billable_seats": 5,
         "vat_id": None, "period_end": _END}
    s.update(kw)
    return s


def _at(days):
    return _END - timedelta(days=days)


def _plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


class ProrateTests(unittest.TestCase):
    def test_trialing(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(), _at(15)), [])

    def test_downgrade_and_equal(self):
        self.assertEqual(prorate_seats(_sub(), _plan(500), _at(15)), [])
        out = prorate_seats(_sub(), _plan(1000), _at(15))
        self.assertEqual([l["kind"] for l in out], ["credit", "charge"])

    def test_upgrade_example(self):
        out = prorate_seats(_sub(), _plan(), _at(15))
        self.assertEqual([l["kind"] for l in out], ["credit", "charge"])
        c, ch = out
        self.assertEqual((c["amount_cents"], c["vat_cents"]), (2500, 0))
        self.assertEqual((ch["amount_cents"], ch["vat_cents"]), (5000, 1050))
        self.assertEqual(c["approved_by"], APPROVER_DEFAULT)
        self.assertIsNone(ch["approved_by"])
        self.assertEqual(c["subscription_id"], "sub_1")
        self.assertEqual(c["description"], "Credit unused Basic to 2025-01-31")
        self.assertEqual(ch["description"], "Charge unused Pro to 2025-01-31")

    def test_rounding_example(self):
        out = prorate_seats(_sub(seat_price_cents=1001, billable_seats=1, seats=1),
                            _plan(2002), _at(10))
        self.assertEqual(out[0]["amount_cents"], 334)
        self.assertEqual((out[1]["amount_cents"], out[1]["vat_cents"]), (667, 140))

    def test_vat_id(self):
        self.assertEqual(prorate_seats(_sub(vat_id="NL123"), _plan(), _at(15))[1]["vat_cents"], 0)
        for blank in (None, "", "   "):
            self.assertEqual(prorate_seats(_sub(vat_id=blank), _plan(), _at(15))[1]["vat_cents"], 1050)

    def test_thresholds(self):
        s = _sub(seat_price_cents=49, billable_seats=1)
        out = prorate_seats(s, _plan(100), _at(30))
        self.assertEqual([l["kind"] for l in out], ["charge"])
        s = _sub(seat_price_cents=50, billable_seats=1)
        out = prorate_seats(s, _plan(50), _at(30))
        self.assertEqual([(l["kind"], l["amount_cents"]) for l in out],
                         [("credit", 50), ("charge", 50)])
        s = _sub(seat_price_cents=10, billable_seats=1)
        self.assertEqual(prorate_seats(s, _plan(49), _at(30)), [])
        out = prorate_seats(s, _plan(50), _at(30))
        self.assertEqual([l["kind"] for l in out], ["charge"])

    def test_approver(self):
        s = _sub(seat_price_cents=50000, billable_seats=1)
        self.assertEqual(prorate_seats(s, _plan(60000), _at(30))[0]["approved_by"], APPROVER_DEFAULT)
        s = _sub(seat_price_cents=50001, billable_seats=1)
        self.assertEqual(prorate_seats(s, _plan(60000), _at(30))[0]["approved_by"], APPROVER_HIGH)

    def test_approver_nfc(self):
        for n in (APPROVER_DEFAULT, APPROVER_HIGH):
            self.assertTrue(unicodedata.is_normalized("NFC", n))

    def test_billable_seats(self):
        out = prorate_seats(_sub(seats=10, billable_seats=2), _plan(), _at(15))
        self.assertEqual(out[0]["amount_cents"], 1000)
        s = _sub()
        del s["billable_seats"]
        with self.assertRaises(ValueError):
            prorate_seats(s, _plan(), _at(15))
        self.assertEqual(prorate_seats(_sub(billable_seats=0), _plan(), _at(15)), [])

    def test_long_names(self):
        for name in ("x" * 200, "é" * 200, "日本語" * 70):
            out = prorate_seats(_sub(plan_name=name), _plan(name=name), _at(15))
            self.assertEqual(len(out), 2)
            for l in out:
                self.assertLessEqual(len(l["description"]), 80)
                self.assertTrue(l["description"].endswith("2025-01-31"))
                self.assertIn("...", l["description"])

    def test_legacy_discount_ignored(self):
        self.assertEqual(prorate_seats(_sub(legacy_discount=50), _plan(), _at(15)),
                         prorate_seats(_sub(), _plan(), _at(15)))

    def test_ints_only(self):
        for l in prorate_seats(_sub(), _plan(), _at(15)):
            self.assertIs(type(l["amount_cents"]), int)
            self.assertIs(type(l["vat_cents"]), int)
        for bad in (1000.0, True, "1000"):
            with self.assertRaises(TypeError):
                prorate_seats(_sub(seat_price_cents=bad), _plan(), _at(15))
            with self.assertRaises(TypeError):
                prorate_seats(_sub(), _plan(bad), _at(15))
            with self.assertRaises(TypeError):
                prorate_seats(_sub(billable_seats=bad), _plan(), _at(15))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(seat_price_cents=-1), _plan(), _at(15))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(billable_seats=-1), _plan(), _at(15))

    def test_no_mutation(self):
        s, p = _sub(), _plan()
        s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
        prorate_seats(s, p, _at(15))
        self.assertEqual((s, p), (s0, p0))

    def test_clamping(self):
        self.assertEqual(prorate_seats(_sub(), _plan(), _at(100)),
                         prorate_seats(_sub(), _plan(), _at(30)))
        self.assertEqual(prorate_seats(_sub(), _plan(), _END + timedelta(days=5)), [])

    def test_timezone_dates(self):
        tz = timezone(timedelta(hours=2))
        end = datetime(2025, 1, 31, 0, 30, tzinfo=tz)  # Jan 30 22:30 UTC
        changed = datetime(2025, 1, 30, 23, 0, tzinfo=_UTC)  # Jan 31 01:00 local
        self.assertEqual(prorate_seats(_sub(period_end=end), _plan(), changed), [])
        changed = datetime(2025, 1, 20, 23, 0, tzinfo=_UTC)  # Jan 21 local -> 10 days
        out = prorate_seats(_sub(period_end=end), _plan(), changed)
        self.assertEqual(out[0]["amount_cents"], 1667)
        self.assertTrue(out[0]["description"].endswith("2025-01-31"))

    def test_naive_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(), datetime(2025, 1, 16))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(period_end=datetime(2025, 1, 31)), _plan(), _at(15))


if __name__ == "__main__":
    unittest.main()