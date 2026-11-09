"""Seat-upgrade proration.

prorate_seats(subscription, new_plan, changed_at) -> list of invoice-line dicts.

Design decisions and assumptions:
- Integer math only; no floats anywhere. Bool and float inputs are rejected.
- Seats billed = billable_seats. seats and legacy_discount are ignored.
- trialing -> []. Downgrade (new price < old) -> []. Equal price -> [].
- billable_seats == 0 -> [].
- Validation (ValueError): changed_at and period_end must be tz-aware; prices and
  billable_seats must be non-negative ints (not bool, not float). Validation runs
  before the early-return rules.
- Days left = period_end - changed_at. If <= 0 -> []. Partial days are rounded UP
  (customer-favourable for the credit), computed from timedelta with integers,
  then clamped to 0..30. A period is always 30 days.
- Credit = ceil(old_price*seats*days/30); charge = floor(new_price*seats*days/30).
- A line whose rounded amount is < 50 cents is skipped; each line is judged on its own.
- VAT: 21% of the charge, rounded down; 0 if vat_id is truthy. Credits carry 0 VAT.
  (The generic house rule "VAT on every line" is overridden by the brief.)
  Rounding is credit-up / charge-down per the brief, not half-up.
- approved_by: None for charges; credits "Nguyen Thi Phuong Thao" (with diacritics)
  unless the rounded credit is strictly > 50000 cents, then "Ramon Etxeberria-Goni"
  (with diacritics).
- Description: "Credit: <plan> unused seats until YYYY-MM-DD" / "Charge: ...",
  date in period_end's own tz. Max 80 characters; only the plan name is truncated,
  with a trailing "…". Empty name -> "(unnamed plan)". Credit uses the subscription's
  plan_name, charge uses new_plan["name"].
- Output order: credit, then charge. Keys: subscription_id, kind, amount_cents,
  vat_cents, description, approved_by.
- Tests are embedded below (unittest); run: python -I prorate.py
"""
from datetime import datetime, timedelta, timezone
import unittest

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
APPROVAL_LIMIT_CENTS = 50000
APPROVER = "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"
BIG_APPROVER = "Ram\u00f3n Etxeberria-Go\u00f1i"
MAX_DESC = 80
PLACEHOLDER = "(unnamed plan)"


def _int(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative int")
    return value


def _aware(value, label):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value


def _describe(prefix, name, period_end):
    name = name if isinstance(name, str) and name else PLACEHOLDER
    suffix = f" unused seats until {period_end.strftime('%Y-%m-%d')}"
    room = MAX_DESC - len(prefix) - len(suffix) - 1  # 1 for the space after prefix
    if len(name) > room:
        name = name[: max(room - 1, 0)] + "\u2026"
    return f"{prefix} {name}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    period_end = _aware(subscription["period_end"], "period_end")
    _aware(changed_at, "changed_at")
    old_price = _int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _int(new_plan["seat_price_cents"], "new seat_price_cents")
    seats = _int(subscription["billable_seats"], "billable_seats")

    if subscription["status"] == "trialing" or seats == 0 or new_price <= old_price:
        return []

    delta = period_end - changed_at
    micros = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
    if micros <= 0:
        return []
    days = max(0, min(PERIOD_DAYS, -(-micros // (86400 * 1_000_000))))

    sid = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * days) // PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sid,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit:", subscription.get("plan_name"), period_end),
            "approved_by": BIG_APPROVER if credit > APPROVAL_LIMIT_CENTS else APPROVER,
        })

    charge = (new_price * seats * days) // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        vat = 0 if subscription.get("vat_id") else (charge * VAT_PERCENT) // 100
        lines.append({
            "subscription_id": sid,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe("Charge:", new_plan.get("name"), period_end),
            "approved_by": None,
        })
    return lines


# ---------------------------------------------------------------- tests
UTC = timezone.utc
END = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def _sub(**kw):
    s = {"id": "s1", "status": "active", "plan_name": "Basic", "seat_price_cents": 1000,
         "seats": 9, "billable_seats": 3, "vat_id": None, "period_end": END,
         "legacy_discount": 50}
    s.update(kw)
    return s


def _run(sub=None, new_price=2000, name="Pro", days=15, at=None):
    sub = sub or _sub()
    at = at or sub["period_end"] - timedelta(days=days)
    return prorate_seats(sub, {"name": name, "seat_price_cents": new_price}, at)


class ProrateTests(unittest.TestCase):
    def test_basic_upgrade_order_and_keys(self):
        c, ch = _run()
        self.assertEqual((c["kind"], c["amount_cents"], c["vat_cents"]), ("credit", 1500, 0))
        self.assertEqual((ch["kind"], ch["amount_cents"], ch["vat_cents"]), ("charge", 3000, 630))
        self.assertEqual(set(c), {"subscription_id", "kind", "amount_cents", "vat_cents",
                                  "description", "approved_by"})
        self.assertEqual(c["approved_by"], APPROVER)
        self.assertIsNone(ch["approved_by"])
        self.assertEqual(c["description"], "Credit: Basic unused seats until 2026-11-01")
        self.assertEqual(ch["description"], "Charge: Pro unused seats until 2026-11-01")

    def test_uses_billable_not_seats(self):
        self.assertEqual(_run(_sub(billable_seats=1))[0]["amount_cents"], 500)

    def test_rounding_directions(self):
        c, ch = _run(_sub(seat_price_cents=1010, billable_seats=1), 1111, days=7)
        self.assertEqual(c["amount_cents"], 236)   # 235.67 up
        self.assertEqual(ch["amount_cents"], 259)  # 259.23 down
        self.assertEqual(ch["vat_cents"], 54)      # 54.39 down

    def test_threshold_after_rounding(self):
        # credit 46.67 -> 47 skipped; charge 93 kept
        r = _run(_sub(seat_price_cents=100, billable_seats=1), 200, days=14)
        self.assertEqual([x["kind"] for x in r], ["charge"])
        # credit 49.93 -> 50 kept; charge 49.93 -> 49 skipped
        r = _run(_sub(seat_price_cents=107, billable_seats=1), 107 + 1, days=14)
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
        r = _run(_sub(seat_price_cents=106, billable_seats=1), 107, days=14)
        self.assertEqual([(x["kind"], x["amount_cents"]) for x in r], [("credit", 50)])

    def test_approver_boundary(self):
        r = _run(_sub(seat_price_cents=50000, billable_seats=1), 60000, days=30)[0]
        self.assertEqual((r["amount_cents"], r["approved_by"]), (50000, APPROVER))
        r = _run(_sub(seat_price_cents=50001, billable_seats=1), 60000, days=30)[0]
        self.assertEqual((r["amount_cents"], r["approved_by"]), (50001, BIG_APPROVER))

    def test_vat_id(self):
        self.assertEqual(_run(_sub(vat_id="PT123"))[1]["vat_cents"], 0)

    def test_no_lines_cases(self):
        self.assertEqual(_run(_sub(status="trialing")), [])
        self.assertEqual(_run(new_price=500), [])
        self.assertEqual(_run(new_price=1000), [])
        self.assertEqual(_run(_sub(billable_seats=0)), [])

    def test_changed_at_not_before_end(self):
        self.assertEqual(_run(at=END), [])
        self.assertEqual(_run(at=END + timedelta(days=1)), [])

    def test_partial_day_ceil(self):
        at = END - timedelta(days=14, hours=1)
        self.assertEqual(_run(at=at)[0]["amount_cents"], 1500)
        self.assertEqual(_run(at=END - timedelta(microseconds=1))[0]["amount_cents"], 100)

    def test_clamp_30(self):
        self.assertEqual(_run(days=45)[0]["amount_cents"], 3000)

    def test_different_tz(self):
        tz2 = timezone(timedelta(hours=2))
        end = datetime(2026, 11, 1, 0, 30, tzinfo=tz2)  # 2026-10-31 in UTC
        at = datetime(2026, 10, 16, 22, 30, tzinfo=UTC)  # exactly 15 days before
        r = _run(_sub(period_end=end), at=at)
        self.assertEqual(r[0]["amount_cents"], 1500)
        self.assertTrue(r[0]["description"].endswith("2026-11-01"))

    def test_naive_rejected(self):
        with self.assertRaises(ValueError):
            _run(at=datetime(2026, 10, 1))
        with self.assertRaises(ValueError):
            _run(_sub(period_end=datetime(2026, 11, 1)))

    def test_bad_numbers_rejected(self):
        for kw in ({"seat_price_cents": -1}, {"billable_seats": -1},
                   {"billable_seats": True}, {"seat_price_cents": 10.0}):
            with self.assertRaises(ValueError):
                _run(_sub(**kw))
        with self.assertRaises(ValueError):
            _run(new_price=-5)
        with self.assertRaises(ValueError):
            _run(new_price=2000.0)

    def test_long_name_truncated(self):
        r = _run(_sub(plan_name="A" * 200), name="B" * 200)
        for x in r:
            self.assertLessEqual(len(x["description"]), MAX_DESC)
            self.assertTrue(x["description"].endswith("until 2026-11-01"))
            self.assertIn("\u2026", x["description"])

    def test_empty_name(self):
        r = _run(_sub(plan_name=""), name="")
        self.assertIn(PLACEHOLDER, r[0]["description"])
        self.assertIn(PLACEHOLDER, r[1]["description"])

    def test_non_ascii(self):
        r = _run(_sub(plan_name="Pl\u00e1n \u00c1gil \u2603"), name="\u30d7\u30ed")
        self.assertIn("Pl\u00e1n \u00c1gil \u2603", r[0]["description"])
        self.assertIn("\u30d7\u30ed", r[1]["description"])
        self.assertEqual(APPROVER, "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o")

    def test_ints_only(self):
        for x in _run():
            self.assertIs(type(x["amount_cents"]), int)
            self.assertIs(type(x["vat_cents"]), int)


if __name__ == "__main__":
    unittest.main()