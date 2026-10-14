"""prorate.py -- seat proration for plan changes (stdlib only, Python 3.12).

Single module: implementation first, unittest suite at the bottom
(run with: python3 -m unittest prorate -v).

Decisions and ambiguities resolved:
- days_left = (period_end.date() - changed_at.date()).days, with both datetimes
  first converted to period_end's tzinfo. Clamped to 30; <= 0 returns [].
- Equal price is NOT a downgrade (R6); only strictly lower new price returns [].
- Credit = ceil(num/30), charge = floor(num/30), integers only. These explicit
  rules override the house half-up default.
- VAT on charges is floor(amount*21/100). Credits carry 0 VAT (R10), which
  overrides the house "VAT on every line" rule as the task states it explicitly.
- R8 uses the net amount before VAT, per line, so a credit may be dropped while
  the charge is kept (and vice versa).
- Approval threshold is strictly > 50000 cents (EUR assumed); exactly 50000 is
  not escalated. The check uses the final (post-R8) credit amount.
- trialing is checked first (before any validation). Other statuses proceed.
- legacy_discount and other unknown keys are ignored.
- Descriptions are NFC-normalized; the plan name is truncated with "..." to fit 80.
"""
import unicodedata
import unittest
from datetime import datetime, timedelta, timezone

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
APPROVAL_LIMIT_CENTS = 50000
MAX_DESC = 80
APPROVER = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
SENIOR_APPROVER = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")


def _check_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _check_aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _describe(prefix, plan, date_str):
    plan = unicodedata.normalize("NFC", str(plan))
    head, tail = f"{prefix} unused ", f" seats until {date_str}"
    room = MAX_DESC - len(head) - len(tail)
    if len(plan) > room:
        plan = plan[: max(room - 3, 0)] + "..."
        plan = plan[:room]
    return unicodedata.normalize("NFC", head + plan + tail)


def _credit(num):
    # R7: ceiling with integer math; independent of any VAT logic (R14).
    return -(-num // PERIOD_DAYS)


def _charge(num):
    return num // PERIOD_DAYS


def prorate_seats(subscription, new_plan, changed_at):
    if subscription.get("status") == "trialing":
        return []
    _check_aware(changed_at, "changed_at")
    period_end = subscription["period_end"]
    _check_aware(period_end, "period_end")
    old_price = _check_int(subscription["seat_price_cents"], "seat_price_cents")
    _check_int(subscription["seats"], "seats")
    seats = _check_int(subscription["billable_seats"], "billable_seats")  # R4
    new_price = _check_int(new_plan["seat_price_cents"], "new seat_price_cents")

    if new_price < old_price:
        return []

    tz = period_end.tzinfo
    days_left = (period_end.date() - changed_at.astimezone(tz).date()).days
    days_left = min(days_left, PERIOD_DAYS)
    if days_left <= 0:
        return []

    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    credit = _credit(old_price * seats * days_left)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit", subscription["plan_name"], date_str),
            "approved_by": SENIOR_APPROVER if credit > APPROVAL_LIMIT_CENTS else APPROVER,
        })

    charge = _charge(new_price * seats * days_left)
    if charge >= MIN_LINE_CENTS:
        vat_id = subscription.get("vat_id")
        exempt = isinstance(vat_id, str) and vat_id.strip() != ""
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if exempt else charge * VAT_PERCENT // 100,
            "description": _describe("Charge", new_plan["name"], date_str),
            "approved_by": None,
        })
    return lines


# ----------------------------------------------------------------- tests
UTC = timezone.utc


def _sub(**kw):
    s = dict(id="sub_1", status="active", plan_name="Basic", seat_price_cents=1000,
             seats=5, billable_seats=1, vat_id=None,
             period_end=datetime(2025, 7, 31, 12, tzinfo=UTC))
    s.update(kw)
    return s


def _plan(price=1000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def _at(days_before_end):
    return datetime(2025, 7, 31, 12, tzinfo=UTC) - timedelta(days=days_before_end)


class ProrateTests(unittest.TestCase):
    def test_R1_naive_datetimes_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(), datetime(2025, 7, 21))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(period_end=datetime(2025, 7, 31)), _plan(), _at(10))

    def test_R2_keys_and_order_R15(self):
        out = prorate_seats(_sub(), _plan(), _at(10))
        self.assertEqual([l["kind"] for l in out], ["credit", "charge"])
        for l in out:
            self.assertEqual(set(l), {"subscription_id", "kind", "amount_cents",
                                      "vat_cents", "description", "approved_by"})
        self.assertIsNone(out[1]["approved_by"])
        self.assertEqual(out[0]["subscription_id"], "sub_1")

    def test_R3_descriptions(self):
        c, ch = prorate_seats(_sub(), _plan(), _at(10))
        self.assertEqual(c["description"], "Credit unused Basic seats until 2025-07-31")
        self.assertEqual(ch["description"], "Charge unused Pro seats until 2025-07-31")

    def test_R4_uses_billable_seats_not_seats(self):
        a = prorate_seats(_sub(seats=99, billable_seats=3), _plan(), _at(30))
        b = prorate_seats(_sub(seats=1, billable_seats=3), _plan(), _at(30))
        self.assertEqual(a, b)
        self.assertEqual(a[0]["amount_cents"], 3000)

    def test_R5_clamp_and_nonpositive_days(self):
        self.assertEqual(prorate_seats(_sub(), _plan(), _at(60))[0]["amount_cents"], 1000)
        self.assertEqual(prorate_seats(_sub(), _plan(), _at(0)), [])
        self.assertEqual(prorate_seats(_sub(), _plan(), _at(-3)), [])

    def test_R5_timezone_edge(self):
        tz = timezone(timedelta(hours=10))
        sub = _sub(period_end=datetime(2025, 7, 31, 10, tzinfo=tz))
        changed = datetime(2025, 7, 20, 22, 0, tzinfo=UTC)  # 21st at +10:00
        out = prorate_seats(sub, _plan(), changed)
        self.assertEqual(out[0]["amount_cents"], -(-1000 * 10 // 30))  # 10 days, not 11
        self.assertIn("2025-07-31", out[0]["description"])

    def test_R6_downgrade_empty_equal_proceeds(self):
        self.assertEqual(prorate_seats(_sub(), _plan(999), _at(10)), [])
        self.assertEqual(len(prorate_seats(_sub(), _plan(1000), _at(10))), 2)

    def test_R7_credit_up_charge_down(self):
        c, ch = prorate_seats(_sub(), _plan(1000), _at(10))  # 10000/30 = 333.33
        self.assertEqual(c["amount_cents"], 334)
        self.assertEqual(ch["amount_cents"], 333)

    def test_R8_boundary_net_amount_independent_lines(self):
        out = prorate_seats(_sub(seat_price_cents=1470), _plan(1500), _at(1))
        self.assertEqual([l["kind"] for l in out], ["charge"])  # credit 49 dropped
        self.assertEqual(out[0]["amount_cents"], 50)
        out = prorate_seats(_sub(seat_price_cents=1470), _plan(1470), _at(1))
        self.assertEqual(out, [])  # both 49
        out = prorate_seats(_sub(seat_price_cents=1500), _plan(1500), _at(1))
        self.assertEqual(len(out), 2)

    def test_R9_charge_vat_floor_and_vat_id(self):
        ch = prorate_seats(_sub(), _plan(), _at(10))[1]
        self.assertEqual(ch["vat_cents"], 333 * 21 // 100)
        for v in (None, "", "   "):
            ch = prorate_seats(_sub(vat_id=v), _plan(), _at(10))[1]
            self.assertEqual(ch["vat_cents"], 69)
        ch = prorate_seats(_sub(vat_id="NL123"), _plan(), _at(10))[1]
        self.assertEqual(ch["vat_cents"], 0)

    def test_R10_credit_vat_zero(self):
        self.assertEqual(prorate_seats(_sub(), _plan(), _at(10))[0]["vat_cents"], 0)

    def test_R11_trialing_empty(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(), _at(10)), [])
        self.assertEqual(len(prorate_seats(_sub(status="canceled"), _plan(), _at(10))), 2)

    def test_R12_description_length(self):
        for name in ("X" * 300, "Ünïcødé–計画 " * 30, "Phương Thảo" * 20):
            c, ch = prorate_seats(_sub(plan_name=name), _plan(name=name), _at(10))
            for l in (c, ch):
                self.assertLessEqual(len(l["description"]), 80)
                self.assertIn("2025-07-31", l["description"])
                self.assertTrue(l["description"].endswith(" seats until 2025-07-31"))
                self.assertIn("...", l["description"])

    def test_R13_approval_threshold(self):
        at50000 = prorate_seats(_sub(seat_price_cents=1500000), _plan(1500000), _at(1))[0]
        self.assertEqual(at50000["amount_cents"], 50000)
        self.assertEqual(at50000["approved_by"], "Nguyễn Thị Phương Thảo")
        over = prorate_seats(_sub(seat_price_cents=1500001), _plan(1500001), _at(1))[0]
        self.assertEqual(over["amount_cents"], 50001)
        self.assertEqual(over["approved_by"], "Ramón Etxeberria-Goñi")
        self.assertTrue(unicodedata.is_normalized("NFC", over["approved_by"]))

    def test_R14_credit_independent_of_vat(self):
        a = prorate_seats(_sub(vat_id=None), _plan(), _at(10))[0]
        b = prorate_seats(_sub(vat_id="NL1"), _plan(), _at(10))[0]
        self.assertEqual(a, b)

    def test_R16_types_and_negatives(self):
        for bad in (True, 1.5, "10"):
            with self.assertRaises((TypeError, ValueError)):
                prorate_seats(_sub(seat_price_cents=bad), _plan(), _at(10))
            with self.assertRaises((TypeError, ValueError)):
                prorate_seats(_sub(billable_seats=bad), _plan(), _at(10))
            with self.assertRaises((TypeError, ValueError)):
                prorate_seats(_sub(), _plan(bad), _at(10))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(billable_seats=-1), _plan(), _at(10))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(-5), _at(10))
        for l in prorate_seats(_sub(), _plan(), _at(10)):
            self.assertIs(type(l["amount_cents"]), int)
            self.assertIs(type(l["vat_cents"]), int)

    def test_R17_legacy_discount_ignored(self):
        base = prorate_seats(_sub(), _plan(), _at(10))
        self.assertEqual(base, prorate_seats(_sub(legacy_discount=50), _plan(), _at(10)))

    def test_inputs_not_mutated(self):
        import copy
        s, p = _sub(), _plan()
        s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
        prorate_seats(s, p, _at(10))
        self.assertEqual((s, p), (s0, p0))


if __name__ == "__main__":
    unittest.main()