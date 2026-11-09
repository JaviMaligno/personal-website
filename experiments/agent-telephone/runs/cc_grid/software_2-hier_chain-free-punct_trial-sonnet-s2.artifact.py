"""Seat upgrade proration for Fernhollow Studios.

Assumptions:
- Currency is EUR; all amounts are integer cents, no floats anywhere.
- Validation: naive datetimes raise ValueError; floats (or any non-int, and bool)
  for prices/seat counts raise TypeError; negatives raise ValueError.
- legacy_discount and the plain `seats` field are ignored; billable_seats is used.
- Trialing (strip+lowercase) and strict downgrades return []. Equal price proceeds.
- days_left = whole elapsed 24h units until period_end, clamped to 0..30 (30-day period).
- Credit = ceil(old*seats*days/30); charge = floor(new*seats*days/30).
- Lines under 50 cents are dropped independently (exactly 50 is kept).
- Credits have vat 0 (explicit client rule); charges carry 21% VAT rounded down,
  or 0 under reverse charge (non-blank vat_id).
- Credit approver is the first name, or the second if amount > 50000.
- Credit line first, then charge. Descriptions are at most 80 code points; only the
  plan name is shortened (with "..."), the date is never cut.
"""
from datetime import datetime, timedelta
import unittest

APPROVER_LOW = "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"
APPROVER_HIGH = "Ram\u00f3n Etxeberria-Go\u00f1i"
MAX_DESC = 80
MIN_AMOUNT = 50


def _check_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _check_dt(value, name):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


def build_description(verb, plan_name, date_str):
    """Build '<verb> unused <plan> seats until <date>' within 80 code points,
    shortening only the plan name."""
    prefix, suffix = f"{verb} unused ", f" seats until {date_str}"
    budget = MAX_DESC - len(prefix) - len(suffix)
    plan = str(plan_name)
    if len(plan) > budget:
        if budget >= 4:
            plan = plan[:budget - 3] + "..."
        else:
            plan = plan[:max(budget, 0)]
    return prefix + plan + suffix


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription["period_end"]
    _check_dt(changed_at, "changed_at")
    _check_dt(period_end, "period_end")
    old_price = _check_int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _check_int(new_plan["seat_price_cents"], "new seat_price_cents")
    seats = _check_int(subscription["billable_seats"], "billable_seats")

    if str(subscription["status"]).strip().lower() == "trialing":
        return []
    if new_price < old_price:
        return []

    days = (period_end - changed_at) // timedelta(days=1)
    days = max(0, min(30, days))
    if days == 0:
        return []

    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * days) // 30)
    if credit >= MIN_AMOUNT:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": build_description("Credit", subscription["plan_name"], date_str),
            "approved_by": APPROVER_HIGH if credit > 50000 else APPROVER_LOW,
        })

    charge = (new_price * seats * days) // 30
    if charge >= MIN_AMOUNT:
        vat_id = subscription.get("vat_id")
        reverse = isinstance(vat_id, str) and vat_id.strip() != ""
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else (charge * 21) // 100,
            "description": build_description("Charge", new_plan["name"], date_str),
            "approved_by": None,
        })
    return lines


# ---------------------------------------------------------------- tests
from datetime import timezone as _tz

_END = datetime(2025, 6, 30, 12, 0, tzinfo=_tz.utc)


def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 9, "billable_seats": 5,
         "vat_id": None, "period_end": _END}
    s.update(kw)
    return s


def _plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def _at(days=15, hours=0):
    return _END - timedelta(days=days, hours=hours)


class ProrateTests(unittest.TestCase):
    def test_basic(self):
        c, ch = prorate_seats(_sub(), _plan(), _at(15))
        self.assertEqual((c["kind"], c["amount_cents"], c["vat_cents"]), ("credit", 2500, 0))
        self.assertEqual((ch["kind"], ch["amount_cents"], ch["vat_cents"]), ("charge", 5000, 1050))
        self.assertIsNone(ch["approved_by"])
        self.assertEqual(set(c), {"subscription_id", "kind", "amount_cents",
                                  "vat_cents", "description", "approved_by"})

    def test_reverse_charge(self):
        _, ch = prorate_seats(_sub(vat_id="DE123"), _plan(), _at(15))
        self.assertEqual(ch["vat_cents"], 0)
        _, ch = prorate_seats(_sub(vat_id="   "), _plan(), _at(15))
        self.assertEqual(ch["vat_cents"], 1050)

    def test_rounding(self):
        c, ch = prorate_seats(_sub(seat_price_cents=1001, billable_seats=1),
                              _plan(1003), _at(15))
        self.assertEqual(c["amount_cents"], 501)   # 500.5 up
        self.assertEqual(ch["amount_cents"], 501)  # 501.5 down

    def test_min_amount(self):
        sub = _sub(seat_price_cents=49, billable_seats=1)
        self.assertEqual(prorate_seats(sub, _plan(49), _at(30)), [])
        sub = _sub(seat_price_cents=50, billable_seats=1)
        self.assertEqual(len(prorate_seats(sub, _plan(50), _at(30))), 2)

    def test_independent_drop(self):
        sub = _sub(seat_price_cents=0, billable_seats=1)
        res = prorate_seats(sub, _plan(100), _at(30))
        self.assertEqual([r["kind"] for r in res], ["charge"])

    def test_trialing_and_downgrade_and_equal(self):
        self.assertEqual(prorate_seats(_sub(status=" Trialing "), _plan(), _at()), [])
        self.assertEqual(prorate_seats(_sub(), _plan(999), _at()), [])
        self.assertEqual(len(prorate_seats(_sub(), _plan(1000), _at())), 2)

    def test_approver(self):
        self.assertEqual(APPROVER_LOW, "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o")
        self.assertEqual(APPROVER_HIGH, "Ram\u00f3n Etxeberria-Go\u00f1i")
        lo = prorate_seats(_sub(seat_price_cents=50000, billable_seats=1), _plan(50000), _at(30))
        self.assertEqual(lo[0]["amount_cents"], 50000)
        self.assertEqual(lo[0]["approved_by"], "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o")
        hi = prorate_seats(_sub(seat_price_cents=50001, billable_seats=1), _plan(50001), _at(30))
        self.assertEqual(hi[0]["approved_by"], "Ram\u00f3n Etxeberria-Go\u00f1i")

    def test_days_clamping(self):
        self.assertEqual(prorate_seats(_sub(), _plan(), _at(90))[0]["amount_cents"], 5000)
        self.assertEqual(prorate_seats(_sub(), _plan(), _END + timedelta(days=3)), [])
        self.assertEqual(prorate_seats(_sub(), _plan(), _END + timedelta(hours=1)), [])
        res = prorate_seats(_sub(), _plan(), _END - timedelta(days=14, hours=23))
        self.assertEqual(res[0]["amount_cents"], -(-(1000 * 5 * 14) // 30))

    def test_order(self):
        self.assertEqual([r["kind"] for r in prorate_seats(_sub(), _plan(), _at())],
                         ["credit", "charge"])

    def test_naive_datetime(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(), datetime(2025, 6, 15))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(period_end=datetime(2025, 6, 30)), _plan(), _at())

    def test_type_validation(self):
        with self.assertRaises(TypeError):
            prorate_seats(_sub(seat_price_cents=10.0), _plan(), _at())
        with self.assertRaises(TypeError):
            prorate_seats(_sub(), _plan(2000.5), _at())
        with self.assertRaises(TypeError):
            prorate_seats(_sub(billable_seats=True), _plan(), _at())
        with self.assertRaises(ValueError):
            prorate_seats(_sub(billable_seats=-1), _plan(), _at())
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(-5), _at())

    def test_billable_and_legacy(self):
        base = prorate_seats(_sub(), _plan(), _at())
        self.assertEqual(base, prorate_seats(_sub(seats=100), _plan(), _at()))
        self.assertEqual(base, prorate_seats(_sub(legacy_discount=50), _plan(), _at()))

    def test_types_and_id(self):
        for r in prorate_seats(_sub(), _plan(), _at()):
            self.assertIs(type(r["amount_cents"]), int)
            self.assertIs(type(r["vat_cents"]), int)
            self.assertEqual(r["subscription_id"], "sub_1")

    def test_descriptions(self):
        for r in prorate_seats(_sub(plan_name="x" * 200), _plan(name="\u00e9" * 200), _at()):
            self.assertLessEqual(len(r["description"]), 80)
            self.assertIn("2025-06-30", r["description"])
        self.assertEqual(prorate_seats(_sub(), _plan(), _at())[0]["description"],
                         "Credit unused Basic seats until 2025-06-30")

    def test_build_description_boundaries(self):
        d = "2025-06-30"
        s = build_description("Credit", "a" * 43, d)
        self.assertEqual(len(s), 80)
        self.assertNotIn("...", s)
        s = build_description("Credit", "a" * 44, d)
        self.assertEqual(len(s), 80)
        self.assertIn("a" * 40 + "...", s)
        s = build_description("Charge", "\u1ec5" * 500, d)
        self.assertEqual(len(s), 80)
        self.assertTrue(s.endswith(f" seats until {d}"))
        long_date = "D" * 70
        s = build_description("Credit", "plan", long_date)
        self.assertIn(long_date, s)
        self.assertTrue(s.startswith("Credit unused  seats"))


if __name__ == "__main__":
    unittest.main()