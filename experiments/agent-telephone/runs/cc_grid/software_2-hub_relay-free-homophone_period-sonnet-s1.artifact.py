"""Fernhollow Studios seat proration.

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list of invoice-line dicts.
All money maths uses integers only. Tests are at the bottom of this file
(run: python -m unittest seat_proration, or pytest seat_proration.py).
NOTE: the tests were written without an execution environment and have NOT been run.

Assumptions to confirm with the client:
  * The billing period is a fixed 13 days (PERIOD_DAYS).
  * VAT is 21% (VAT_PERCENT). Portugal's standard rate is 23%, so please confirm.
  * Equal old/new price returns [] (treated like a downgrade: nothing to bill). Assumption.
  * Fractional days are counted (time left is measured in microseconds).
  * The 50-cent minimum applies to the NET amount, per line, after rounding;
    exactly 50 is kept.
  * Statuses other than "trialing" are processed normally.
  * The house rule "VAT applies to every invoice line, credits included" is
    overridden by the explicit task spec: credit VAT is 0. Please confirm.
  * The explicit spec (credit rounds up, charge and VAT round down) is used instead of the
    generic half-up house rule.
  * A non-empty, non-whitespace vat_id means reverse charge (VAT 0), without
    validating the id format.
"""
import unicodedata
from datetime import datetime, timedelta

PERIOD_DAYS = 13
PERIOD_US = PERIOD_DAYS * 86_400 * 1_000_000
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
APPROVAL_LIMIT_CENTS = 50_000
MAX_DESCRIPTION_LEN = 80
DEFAULT_APPROVER = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
SENIOR_APPROVER = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")
_JOINERS = {"\u200d", "\u200c"}


def _int(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    return value


def _name(value, name):
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a str, got {type(value).__name__}")
    if not value.strip():
        raise ValueError(f"{name} must not be empty")
    return value


def _aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _glues(ch):
    return (ch in _JOINERS or unicodedata.category(ch).startswith("M")
            or 0x1F3FB <= ord(ch) <= 0x1F3FF or 0xE0020 <= ord(ch) <= 0xE007F)


def _describe(prefix, plan, date_str):
    suffix = f" until {date_str}"
    plan = unicodedata.normalize("NFC", plan)
    prefix = unicodedata.normalize("NFC", prefix)
    full = prefix + plan + suffix
    if len(full) <= MAX_DESCRIPTION_LEN:
        return full
    budget = max(0, MAX_DESCRIPTION_LEN - len(prefix) - len(suffix) - 3)
    cut = plan[:budget]
    while cut and ((len(cut) < len(plan) and _glues(plan[len(cut)]))
                   or cut[-1] in _JOINERS):
        cut = cut[:-1]
    cut = cut.rstrip()
    return unicodedata.normalize("NFC", prefix + cut + "..." + suffix)


def prorate_seats(subscription, new_plan, changed_at):
    sub_id = subscription["id"]
    status = subscription["status"]
    old_name = _name(subscription["plan_name"], "plan_name")
    old_price = _int(subscription["seat_price_cents"], "seat_price_cents")
    seats = _int(subscription["billable_seats"], "billable_seats")
    vat_id = subscription.get("vat_id")
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be a str or None")
    period_end = _aware(subscription["period_end"], "period_end")
    new_name = _name(new_plan["name"], "new_plan name")
    new_price = _int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    changed_at = _aware(changed_at, "changed_at")

    if status == "trialing":
        return []
    if new_price <= old_price:  # downgrade, or equal price (assumption)
        return []
    left = (period_end - changed_at) // timedelta(microseconds=1)  # aware subtraction is UTC-exact
    if left <= 0:
        return []
    left = min(left, PERIOD_US)

    date_str = period_end.date().isoformat()
    lines = []

    credit = -((-(seats * old_price * left)) // PERIOD_US)
    if credit >= MIN_LINE_CENTS:
        approver = SENIOR_APPROVER if credit > APPROVAL_LIMIT_CENTS else DEFAULT_APPROVER
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit for unused ", old_name, date_str),
            "approved_by": approver,
        })

    charge = (seats * new_price * left) // PERIOD_US
    if charge >= MIN_LINE_CENTS:
        reverse = isinstance(vat_id, str) and bool(vat_id.strip())
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * VAT_PERCENT // 100,
            "description": _describe("Charge for unused ", new_name, date_str),
            "approved_by": None,
        })
    return lines


# ----------------------------- tests -----------------------------
import copy
import unittest
from datetime import timezone

UTC = timezone.utc
END = datetime(2026, 6, 14, 12, 0, tzinfo=UTC)
START = END - timedelta(days=13)


def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic", "seat_price_cents": 1000,
         "seats": 10, "billable_seats": 10, "vat_id": None, "period_end": END,
         "legacy_discount": 50, "extra": "ignored"}
    s.update(kw)
    return s


def _plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


class ProrationTests(unittest.TestCase):
    def test_basic(self):
        c, ch = prorate_seats(_sub(), _plan(), START)
        self.assertEqual((c["kind"], c["amount_cents"], c["vat_cents"], c["approved_by"]),
                         ("credit", 10000, 0, DEFAULT_APPROVER))
        self.assertEqual((ch["kind"], ch["amount_cents"], ch["vat_cents"], ch["approved_by"]),
                         ("charge", 20000, 4200, None))

    def test_five_days(self):
        c, ch = prorate_seats(_sub(billable_seats=3, seat_price_cents=999), _plan(1499),
                              END - timedelta(days=5))
        self.assertEqual((c["amount_cents"], ch["amount_cents"], ch["vat_cents"]), (1153, 1729, 363))

    def test_vat_id(self):
        self.assertEqual(prorate_seats(_sub(vat_id="PT123456789"), _plan(), START)[1]["vat_cents"], 0)
        for v in (None, "", "   "):
            self.assertEqual(prorate_seats(_sub(vat_id=v), _plan(), START)[1]["vat_cents"], 4200)
        s = _sub()
        del s["vat_id"]
        self.assertEqual(prorate_seats(s, _plan(), START)[1]["vat_cents"], 4200)

    def test_approver_threshold(self):
        c = prorate_seats(_sub(billable_seats=50), _plan(), START)[0]
        self.assertEqual((c["amount_cents"], c["approved_by"]), (50000, DEFAULT_APPROVER))
        c = prorate_seats(_sub(billable_seats=1, seat_price_cents=50001), _plan(60000), START)[0]
        self.assertEqual((c["amount_cents"], c["approved_by"]), (50001, SENIOR_APPROVER))

    def test_min_threshold(self):
        r = prorate_seats(_sub(billable_seats=1, seat_price_cents=49), _plan(100), START)
        self.assertEqual([x["kind"] for x in r], ["charge"])
        r = prorate_seats(_sub(billable_seats=1, seat_price_cents=50), _plan(100), START)
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])

    def test_early_exits(self):
        self.assertEqual(prorate_seats(_sub(), _plan(500), START), [])
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(), START), [])
        self.assertEqual(prorate_seats(_sub(), _plan(1000), START), [])
        self.assertEqual(prorate_seats(_sub(), _plan(), END), [])
        self.assertEqual(prorate_seats(_sub(), _plan(), END + timedelta(seconds=1)), [])

    def test_other_status(self):
        self.assertEqual(len(prorate_seats(_sub(status="past_due"), _plan(), START)), 2)

    def test_cap(self):
        a = prorate_seats(_sub(), _plan(), END - timedelta(days=20))
        self.assertEqual(a, prorate_seats(_sub(), _plan(), START))

    def test_zero_seats_and_ignored_keys(self):
        self.assertEqual(prorate_seats(_sub(billable_seats=0), _plan(), START), [])
        a = prorate_seats(_sub(seats=1, legacy_discount=0), _plan(), START)
        b = prorate_seats(_sub(seats=999, legacy_discount=99), _plan(), START)
        self.assertEqual(a, b)

    def test_long_names(self):
        names = ["É" * 200, "漢字" * 100, "😀" * 100, "e\u0301" * 100,
                 "👨\u200d👩\u200d👧" * 30, "Plan " * 40]
        for n in names:
            for sub_name, plan_name in ((n, "X"), ("Basic", n)):
                for line in prorate_seats(_sub(plan_name=sub_name), _plan(name=plan_name), START):
                    d = line["description"]
                    self.assertLessEqual(len(d), 80)
                    self.assertTrue(d.endswith(" until 2026-06-14"))
                    self.assertEqual(d, unicodedata.normalize("NFC", d))
                    if len(d) > 70:
                        self.assertIn("...", d)
                    body = d[:-len(" until 2026-06-14")].replace("...", "")
                    if body:
                        self.assertFalse(_glues(body[-1]) and body[-1] != "\u0301")

    def test_no_dangling_mark(self):
        n = "a" * 40 + "e\u0301" + "b" * 40
        d = prorate_seats(_sub(), _plan(name=n), START)[1]["description"]
        self.assertNotIn("\u0301", d)
        self.assertLessEqual(len(d), 80)

    def test_short_description(self):
        c, ch = prorate_seats(_sub(), _plan(), START)
        self.assertEqual(c["description"], "Credit for unused Basic until 2026-06-14")
        self.assertEqual(ch["description"], "Charge for unused Pro until 2026-06-14")

    def test_types_keys_and_immutability(self):
        s, p = _sub(), _plan()
        s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
        for line in prorate_seats(s, p, START + timedelta(hours=7)):
            self.assertEqual(set(line), {"subscription_id", "kind", "amount_cents", "vat_cents",
                                         "description", "approved_by"})
            self.assertIs(type(line["amount_cents"]), int)
            self.assertIs(type(line["vat_cents"]), int)
        self.assertEqual(s, s0)
        self.assertEqual(p, p0)

    def test_dst(self):
        try:
            from zoneinfo import ZoneInfo
            lis = ZoneInfo("Europe/Lisbon")
        except Exception:
            self.skipTest("tz data unavailable")
        ca = datetime(2026, 3, 28, 12, 0, tzinfo=lis)
        pe = datetime(2026, 3, 30, 12, 0, tzinfo=lis)
        a = prorate_seats(_sub(period_end=pe), _plan(), ca)
        b = prorate_seats(_sub(period_end=pe.astimezone(UTC)), _plan(), ca.astimezone(UTC))
        self.assertTrue(a)
        for x, y in zip(a, b):
            self.assertEqual({k: v for k, v in x.items()}, y)  # same date: 2026-03-30

    def test_description_date_in_own_tz(self):
        tz = timezone(timedelta(hours=-5))
        pe = datetime(2026, 6, 14, 22, 0, tzinfo=tz)  # 2026-06-15 UTC
        c = prorate_seats(_sub(period_end=pe), _plan(), pe - timedelta(days=13))[0]
        self.assertTrue(c["description"].endswith("2026-06-14"))

    def test_validation(self):
        naive = datetime(2026, 6, 1)
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(), naive)
        with self.assertRaises(ValueError):
            prorate_seats(_sub(period_end=naive), _plan(), START)
        for bad in (1.5, True, "3"):
            with self.assertRaises(TypeError):
                prorate_seats(_sub(billable_seats=bad), _plan(), START)
            with self.assertRaises(TypeError):
                prorate_seats(_sub(seat_price_cents=bad), _plan(), START)
            with self.assertRaises(TypeError):
                prorate_seats(_sub(), _plan(bad), START)
        for kw in ({"billable_seats": -1}, {"seat_price_cents": -1}, {"plan_name": ""},
                   {"plan_name": "  "}):
            with self.assertRaises(ValueError):
                prorate_seats(_sub(**kw), _plan(), START)
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(-5), START)
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(name=""), START)


if __name__ == "__main__":
    unittest.main()