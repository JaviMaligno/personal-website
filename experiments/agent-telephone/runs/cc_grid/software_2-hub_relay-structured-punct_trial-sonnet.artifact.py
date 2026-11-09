# prorate.py
# Notes on assumptions ([DEFAULT] items, not yet confirmed by the client):
#  - Credit line names the old plan, charge line names the new plan; the date is
#    period_end's own local date (no UTC conversion). Templates as in R3.
#  - Exact remaining time (microsecond integer math, Fraction), no whole-day rounding;
#    fraction clamped to [0, 1].
#  - Minimum-line test (>= 50 cents) applies to the net amount before VAT, per line.
#  - VAT (21%) rounds DOWN; no vat_id format validation.
#  - changed_at >= period_end -> [] without raising.
#  - Equal price -> []. Statuses other than "trialing" are prorated normally.
#  - Conflict noted: the house rule "VAT applies to credits" is overridden by the
#    explicit requirement R10 (credits always vat_cents 0). Likewise explicit R7
#    (credits ceil, charges floor) and R9 (VAT floor) override the house half-up rule.
#  - Validation of types/tz/keys runs before any early return ([]).
#  - `seats` is type-validated but never used in calculations (R4).
#  - Tests are embedded; run: python -I prorate.py  (or python -m unittest prorate)

import math
import unicodedata
from datetime import datetime, timedelta
from fractions import Fraction

__all__ = ["prorate_seats"]

_PERIOD_US = 30 * 86400 * 10**6
_MAX_DESC = 80
_MIN_LINE = 50
_APPROVER = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
_SENIOR_APPROVER = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")
_CREDIT_LIMIT = 50000
_VAT_PERCENT = 21
_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")


def _int(value, name):
    if type(value) is not int:
        raise TypeError(f"{name} must be int, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must be >= 0")
    return value


def _aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _describe(prefix, plan, date_str):
    mid = " until "
    avail = _MAX_DESC - len(prefix) - len(mid) - len(date_str)
    if len(plan) > avail:
        plan = plan[:max(avail - 1, 0)] + "\u2026"
    return f"{prefix}{plan}{mid}{date_str}"


def prorate_seats(subscription, new_plan, changed_at):
    vals = {k: subscription[k] for k in _SUB_KEYS}  # KeyError on missing
    new_name = new_plan["name"]
    new_price = _int(new_plan["seat_price_cents"], "new_plan.seat_price_cents")
    old_price = _int(vals["seat_price_cents"], "seat_price_cents")
    _int(vals["seats"], "seats")
    billable = _int(vals["billable_seats"], "billable_seats")
    period_end = _aware(vals["period_end"], "period_end")
    changed_at = _aware(changed_at, "changed_at")
    vat_id = vals["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be str or None")
    for n, v in (("plan_name", vals["plan_name"]), ("new_plan.name", new_name)):
        if not isinstance(v, str):
            raise TypeError(f"{n} must be str")

    if vals["status"] == "trialing" or billable == 0:
        return []
    if new_price <= old_price:
        return []
    remaining = (period_end - changed_at) // timedelta(microseconds=1)
    if remaining <= 0:
        return []
    fraction = min(Fraction(remaining, _PERIOD_US), Fraction(1))

    date_str = period_end.strftime("%Y-%m-%d")
    lines = []

    credit = math.ceil(Fraction(old_price * billable) * fraction)
    if credit >= _MIN_LINE:
        lines.append({
            "subscription_id": vals["id"],
            "kind": "credit",
            "amount_cents": int(credit),
            "vat_cents": 0,
            "description": _describe("Credit: unused ", vals["plan_name"], date_str),
            "approved_by": _SENIOR_APPROVER if credit > _CREDIT_LIMIT else _APPROVER,
        })

    charge = math.floor(Fraction(new_price * billable) * fraction)
    if charge >= _MIN_LINE:
        reverse = vat_id is not None and vat_id.strip() != ""
        lines.append({
            "subscription_id": vals["id"],
            "kind": "charge",
            "amount_cents": int(charge),
            "vat_cents": 0 if reverse else int(charge * _VAT_PERCENT // 100),
            "description": _describe("Charge: ", new_name, date_str),
            "approved_by": None,
        })
    return lines


# ---------------------------------------------------------------- tests
import unittest  # noqa: E402
from copy import deepcopy  # noqa: E402
from datetime import timezone  # noqa: E402

_UTC = timezone.utc
_END = datetime(2026, 11, 1, 12, 0, tzinfo=_UTC)


def _sub(**kw):
    s = dict(id="s1", status="active", plan_name="Basic", seat_price_cents=1000,
             seats=5, billable_seats=5, vat_id=None, period_end=_END)
    s.update(kw)
    return s


def _at(days):
    return _END - timedelta(days=days)


class ProrateTests(unittest.TestCase):
    def test_basic(self):
        r = prorate_seats(_sub(), {"name": "Pro", "seat_price_cents": 2000}, _at(15))
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
        self.assertEqual((r[0]["amount_cents"], r[0]["vat_cents"]), (2500, 0))
        self.assertEqual(r[0]["approved_by"], "Nguyễn Thị Phương Thảo")
        self.assertEqual((r[1]["amount_cents"], r[1]["vat_cents"]), (5000, 1050))
        self.assertIsNone(r[1]["approved_by"])
        self.assertEqual(r[0]["description"], "Credit: unused Basic until 2026-11-01")
        self.assertEqual(r[1]["description"], "Charge: Pro until 2026-11-01")
        self.assertEqual(set(r[0]), {"subscription_id", "kind", "amount_cents",
                                     "vat_cents", "description", "approved_by"})

    def test_reverse_charge(self):
        n = {"name": "Pro", "seat_price_cents": 2000}
        self.assertEqual(prorate_seats(_sub(vat_id="NL123"), n, _at(15))[1]["vat_cents"], 0)
        for v in (None, "", "  "):
            self.assertEqual(prorate_seats(_sub(vat_id=v), n, _at(15))[1]["vat_cents"], 1050)

    def test_rounding(self):
        r = prorate_seats(_sub(billable_seats=1), {"name": "P", "seat_price_cents": 1999}, _at(10))
        self.assertEqual((r[0]["amount_cents"], r[1]["amount_cents"], r[1]["vat_cents"]),
                         (334, 666, 139))
        for x in r:
            self.assertIs(type(x["amount_cents"]), int)
            self.assertIs(type(x["vat_cents"]), int)

    def test_approver_threshold(self):
        n = {"name": "P", "seat_price_cents": 10**6}
        for price, who in ((50000, "Nguyễn Thị Phương Thảo"), (50001, "Ramón Etxeberria-Goñi")):
            r = prorate_seats(_sub(seat_price_cents=price, billable_seats=1), n, _at(30))
            self.assertEqual(r[0]["amount_cents"], price)
            self.assertEqual(r[0]["approved_by"], who)

    def test_minimum(self):
        n = {"name": "P", "seat_price_cents": 10**6}
        self.assertEqual(prorate_seats(_sub(seat_price_cents=49, billable_seats=1), n, _at(30))[0:0], [])
        r49 = prorate_seats(_sub(seat_price_cents=49, billable_seats=1), n, _at(30))
        self.assertEqual([x["kind"] for x in r49], ["charge"])
        r50 = prorate_seats(_sub(seat_price_cents=50, billable_seats=1), n, _at(30))
        self.assertEqual([x["kind"] for x in r50], ["credit", "charge"])

    def test_empty_cases(self):
        n = {"name": "P", "seat_price_cents": 2000}
        self.assertEqual(prorate_seats(_sub(seats=10, billable_seats=0), n, _at(15)), [])
        self.assertEqual(prorate_seats(_sub(), {"name": "P", "seat_price_cents": 500}, _at(15)), [])
        self.assertEqual(prorate_seats(_sub(), {"name": "P", "seat_price_cents": 1000}, _at(15)), [])
        self.assertEqual(prorate_seats(_sub(status="trialing"), n, _at(15)), [])
        self.assertEqual(prorate_seats(_sub(), n, _END + timedelta(days=1)), [])
        self.assertEqual(prorate_seats(_sub(), n, _END), [])
        self.assertEqual(len(prorate_seats(_sub(status="past_due"), n, _at(15))), 2)

    def test_clamp(self):
        r = prorate_seats(_sub(), {"name": "P", "seat_price_cents": 2000}, _at(45))
        self.assertEqual(r[0]["amount_cents"], 5000)

    def test_errors(self):
        n = {"name": "P", "seat_price_cents": 2000}
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), n, datetime(2026, 10, 20))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(period_end=datetime(2026, 11, 1)), n, _at(15))
        s = _sub()
        del s["billable_seats"]
        with self.assertRaises(KeyError):
            prorate_seats(s, n, _at(15))
        for bad in (10.0, True, "10"):
            with self.assertRaises(TypeError):
                prorate_seats(_sub(seat_price_cents=bad), n, _at(15))
            with self.assertRaises(TypeError):
                prorate_seats(_sub(billable_seats=bad), n, _at(15))
        with self.assertRaises(TypeError):
            prorate_seats(_sub(), {"name": "P", "seat_price_cents": 2000.0}, _at(15))

    def test_no_mutation(self):
        s, n = _sub(), {"name": "P", "seat_price_cents": 2000}
        s0, n0 = deepcopy(s), deepcopy(n)
        prorate_seats(s, n, _at(15))
        self.assertEqual((s, n), (s0, n0))

    def test_long_and_unicode_names(self):
        for name in ("x" * 200, "Ünï–çødé™" * 30, "日本語プラン" * 40):
            r = prorate_seats(_sub(plan_name=name), {"name": name, "seat_price_cents": 2000}, _at(15))
            for x in r:
                d = x["description"]
                self.assertLessEqual(len(d), 80)
                self.assertTrue(d.endswith(" until 2026-11-01"))
                self.assertIn("\u2026", d)
        r = prorate_seats(_sub(plan_name="Basic"), {"name": "P", "seat_price_cents": 2000}, _at(15))
        self.assertNotIn("\u2026", r[0]["description"])

    def test_date_in_own_timezone(self):
        tz = timezone(timedelta(hours=-5))
        end = datetime(2026, 11, 1, 22, 0, tzinfo=tz)  # 2026-11-02 UTC
        r = prorate_seats(_sub(period_end=end), {"name": "P", "seat_price_cents": 2000},
                          end - timedelta(days=15))
        self.assertTrue(r[0]["description"].endswith("2026-11-01"))

    def test_legacy_discount_ignored(self):
        n = {"name": "P", "seat_price_cents": 2000}
        self.assertEqual(prorate_seats(_sub(legacy_discount=50), n, _at(15)),
                         prorate_seats(_sub(), n, _at(15)))


if __name__ == "__main__":
    unittest.main()