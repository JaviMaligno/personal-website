# prorate.py
# Note: the file-writing and test-running tools were not available to me, so the
# tests are embedded below (run: python3 -I prorate.py) and have NOT been executed.
#
# Choices and ambiguities:
# - House rule "VAT on credits" is overridden by explicit R10 (credit VAT = 0).
# - House rule "half-up" is overridden by R7 (credit ceil, charge floor).
# - Equal prices are not a downgrade (R6): proceed normally.
# - Mid-day changed_at: floor of whole elapsed days (timedelta // 1 day).
# - changed_at >= period_end: days_left 0, so no lines.
# - Strictly greater than 50000 selects the second approver.
# - The date is formatted from period_end in its own tz.
# - Validation (naive datetimes, bad ints) runs before the trialing/downgrade shortcuts.
# - Charge VAT is floor(amount*21//100); R14: credit is never altered for VAT.
import unittest
from datetime import datetime, timedelta, timezone

APPROVER_DEFAULT = "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"  # NFC
APPROVER_HIGH = "Ram\u00f3n Etxeberria-Go\u00f1i"  # NFC
_PERIOD_DAYS = 30
_MAX_DESC = 80


def _check_int(value, name):
    # R16: bool is a subclass of int, so test the exact type.
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative int")
    return value


def _check_dt(value, name):
    if (not isinstance(value, datetime) or value.tzinfo is None
            or value.utcoffset() is None):
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _describe(prefix, plan, date):
    # R12: the date stays last; only the plan name is truncated.
    suffix = f" seats, period ends {date}"
    room = _MAX_DESC - len(prefix) - len(suffix)
    plan = str(plan)
    if len(plan) > room:
        plan = plan[:max(room - 1, 0)] + "\u2026"
    return f"{prefix}{plan}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    """R1: return prorated credit/charge lines for a mid-period plan change."""
    old_price = _check_int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _check_int(new_plan["seat_price_cents"], "new seat_price_cents")
    seats = _check_int(subscription["billable_seats"], "billable_seats")  # R4
    period_end = subscription["period_end"]
    _check_dt(period_end, "period_end")
    _check_dt(changed_at, "changed_at")

    if subscription["status"] == "trialing":  # R11
        return []
    if new_price < old_price:  # R6 (equal is not a downgrade)
        return []

    days_left = (period_end - changed_at) // timedelta(days=1)  # R5 floor
    days_left = max(0, min(_PERIOD_DAYS, days_left))
    date = period_end.strftime("%Y-%m-%d")  # R3, period_end's own tz
    sub_id = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * days_left) // _PERIOD_DAYS)  # R7 up
    if credit >= 50:  # R8
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,  # R10
            "description": _describe("Credit unused ",
                                     subscription["plan_name"], date),
            "approved_by": APPROVER_HIGH if credit > 50000
            else APPROVER_DEFAULT,  # R13
        })

    charge = (new_price * seats * days_left) // _PERIOD_DAYS  # R7 down
    if charge >= 50:  # R8
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if subscription.get("vat_id") else charge * 21 // 100,  # R9
            "description": _describe("Charge ", new_plan["name"], date),
            "approved_by": None,
        })
    return lines  # R15: credit first; R17: legacy_discount ignored


# ---------------------------------------------------------------- tests
UTC = timezone.utc
END = datetime(2025, 1, 31, tzinfo=UTC)
START = END - timedelta(days=30)


def _sub(**kw):
    s = dict(id="s1", status="active", plan_name="Basic", seat_price_cents=1000,
             seats=99, billable_seats=3, vat_id=None, period_end=END)
    s.update(kw)
    return s


def _new(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


class TestProrate(unittest.TestCase):
    def test_r1_r2_keys_and_values(self):  # R1, R2
        out = prorate_seats(_sub(), _new(), START)
        self.assertEqual(len(out), 2)
        for line in out:
            self.assertEqual(set(line), {"subscription_id", "kind", "amount_cents",
                                         "vat_cents", "description", "approved_by"})
        self.assertEqual(out[0]["amount_cents"], 3000)
        self.assertEqual(out[1]["amount_cents"], 6000)

    def test_r3_descriptions(self):
        out = prorate_seats(_sub(), _new(), START)
        self.assertEqual(out[0]["description"],
                         "Credit unused Basic seats, period ends 2025-01-31")
        self.assertEqual(out[1]["description"],
                         "Charge Pro seats, period ends 2025-01-31")

    def test_r4_billable_not_seats(self):
        out = prorate_seats(_sub(seats=1000, billable_seats=1), _new(), START)
        self.assertEqual(out[0]["amount_cents"], 1000)

    def test_r5_days_left_clamp_and_floor(self):
        self.assertEqual(prorate_seats(_sub(), _new(), START - timedelta(days=9))[0]["amount_cents"], 3000)
        mid = END - timedelta(days=10, hours=5)  # floors to 10 days
        self.assertEqual(prorate_seats(_sub(), _new(), mid)[0]["amount_cents"], 1000)
        self.assertEqual(prorate_seats(_sub(), _new(), END), [])
        self.assertEqual(prorate_seats(_sub(), _new(), END + timedelta(days=3)), [])

    def test_r6_downgrade_and_equal(self):
        self.assertEqual(prorate_seats(_sub(), _new(999), START), [])
        self.assertEqual(len(prorate_seats(_sub(), _new(1000), START)), 2)

    def test_r7_rounding(self):
        # 1 seat, price 1, ... use price 100, 1 seat, 1 day: 100/30 -> credit 4, charge 3
        s = _sub(seat_price_cents=100, billable_seats=1)
        n = _new(100)
        out = prorate_seats(s, n, END - timedelta(days=1))
        self.assertEqual(out, [])  # both under 50 (R8), check rounding below
        s = _sub(seat_price_cents=1600, billable_seats=1)
        out = prorate_seats(s, _new(1600), END - timedelta(days=1))
        self.assertEqual(out[0]["amount_cents"], 54)  # 1600/30=53.33 -> up 54
        self.assertEqual(out[1]["amount_cents"], 53)  # down

    def test_r8_threshold_and_independent(self):
        s = _sub(seat_price_cents=1500, billable_seats=1)
        out = prorate_seats(s, _new(1500), END - timedelta(days=1))
        self.assertEqual([l["amount_cents"] for l in out], [50, 50])  # exactly 50 kept
        s = _sub(seat_price_cents=1470, billable_seats=1)  # credit 49 skipped
        out = prorate_seats(s, _new(1500), END - timedelta(days=1))
        self.assertEqual([l["kind"] for l in out], ["charge"])

    def test_r9_vat(self):
        out = prorate_seats(_sub(), _new(), START)
        self.assertEqual(out[1]["vat_cents"], 6000 * 21 // 100)
        out = prorate_seats(_sub(vat_id="DE123"), _new(), START)
        self.assertEqual(out[1]["vat_cents"], 0)
        out = prorate_seats(_sub(vat_id=""), _new(), START)
        self.assertEqual(out[1]["vat_cents"], 1260)

    def test_r10_credit_vat_zero(self):
        self.assertEqual(prorate_seats(_sub(), _new(), START)[0]["vat_cents"], 0)

    def test_r11_trialing(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _new(), START), [])

    def test_r12_truncation(self):
        long = "X" * 100
        out = prorate_seats(_sub(plan_name=long), _new(name=long), START)
        for line in out:
            self.assertLessEqual(len(line["description"]), 80)
            self.assertTrue(line["description"].endswith("period ends 2025-01-31"))
            self.assertIn("\u2026 seats", line["description"])

    def test_r13_approvers(self):
        self.assertEqual(prorate_seats(_sub(), _new(), START)[0]["approved_by"],
                         "Nguyễn Thị Phương Thảo")
        s = _sub(seat_price_cents=50000, billable_seats=1)  # credit exactly 50000
        out = prorate_seats(s, _new(50000), START)
        self.assertEqual(out[0]["amount_cents"], 50000)
        self.assertEqual(out[0]["approved_by"], "Nguyễn Thị Phương Thảo")
        s = _sub(seat_price_cents=50001, billable_seats=1)
        out = prorate_seats(s, _new(50001), START)
        self.assertEqual(out[0]["approved_by"], "Ramón Etxeberria-Goñi")
        self.assertIsNone(out[1]["approved_by"])

    def test_r14_credit_exact(self):
        s = _sub(vat_id=None)
        out = prorate_seats(s, _new(), START)
        self.assertEqual(out[0]["amount_cents"], 3000)

    def test_r15_order(self):
        self.assertEqual([l["kind"] for l in prorate_seats(_sub(), _new(), START)],
                         ["credit", "charge"])

    def test_r16_types(self):
        out = prorate_seats(_sub(), _new(), START)
        for l in out:
            self.assertIs(type(l["amount_cents"]), int)
            self.assertIs(type(l["vat_cents"]), int)
        for bad in (1.5, True, -1, "3", None):
            with self.assertRaises(ValueError):
                prorate_seats(_sub(billable_seats=bad), _new(), START)
            with self.assertRaises(ValueError):
                prorate_seats(_sub(seat_price_cents=bad), _new(), START)
            with self.assertRaises(ValueError):
                prorate_seats(_sub(), _new(bad), START)

    def test_r17_legacy_discount_ignored(self):
        a = prorate_seats(_sub(), _new(), START)
        b = prorate_seats(_sub(legacy_discount=50), {**_new(), "legacy_discount": 9}, START)
        self.assertEqual(a, b)

    def test_edges(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _new(), datetime(2025, 1, 1))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(period_end=datetime(2025, 1, 31)), _new(), START)
        self.assertEqual(prorate_seats(_sub(billable_seats=0), _new(), START), [])
        # date uses period_end's own tz
        tz = timezone(timedelta(hours=-5))
        pe = datetime(2025, 1, 31, 22, 0, tzinfo=tz)  # 2025-02-01 in UTC
        out = prorate_seats(_sub(period_end=pe), _new(), pe - timedelta(days=30))
        self.assertIn("2025-01-31", out[0]["description"])
        # no mutation
        import copy
        s, n = _sub(), _new()
        s0, n0 = copy.deepcopy(s), copy.deepcopy(n)
        prorate_seats(s, n, START)
        self.assertEqual((s, n), (s0, n0))


if __name__ == "__main__":
    unittest.main()