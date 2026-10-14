"""Seat-upgrade proration for Fernhollow Studios.

Entry point: prorate_seats(subscription, new_plan, changed_at).
Integer arithmetic only. Standard library only.

NOTE: the tests at the bottom were written but NOT executed (no execution
tool was available). Run: python -m unittest prorate.py

Decisions (each one is also an OPEN QUESTION for the client):
1. Order of checks: (a) status == "trialing" -> []. (b) new price < old price
   (strictly) -> []. Equal price is NOT a downgrade: it yields a credit and a
   charge that net to about zero. (c) days <= 0 -> []. (d) each line is
   rounded, then dropped on its own if amount < 50 cents (before VAT; exactly
   50 is kept). The double skip can leave a one-sided invoice.
2. Days: whole days = floor((period_end - changed_at) / 1 day), computed on
   aware datetimes (no conversion to dates), clamped to 30. Description date
   is period_end.date() in period_end's own timezone. Naive datetimes raise
   ValueError.
3. Amounts: credit = ceil(old*billable_seats*days/30); charge =
   floor(new*billable_seats*days/30). VAT = charge*21//100, rounded DOWN (the
   brief does not say how to round VAT; the house half-up rule was overridden
   by the architect). VAT is 0 if vat_id is truthy after str strip (None, ""
   or whitespace means no vat_id). Credits always have vat_cents 0 (the brief
   says so; the house rule "VAT on credits" was overridden by the brief).
4. Approver: credit > 50000 cents strictly -> Ramon Etxeberria-Goni, else
   Nguyen Thi Phuong Thao (with full diacritics). Exactly 500.00 goes to Thao.
   Charges: approved_by None.
5. Description: "<Credit|Charge> <plan> until YYYY-MM-DD", max 80 code points.
   Only the plan name is shortened, with a single-char ellipsis; if no room,
   the name is dropped. Credit uses the old plan name, charge the new one.
6. Output: list, credit first, then charge. Keys: subscription_id, kind,
   amount_cents, vat_cents, description, approved_by.
7. Validation: negative or bool/float prices or seats are rejected
   (TypeError for wrong type, ValueError for negative). billable_seats == 0
   -> no lines. An upgrade shows a credit for the old plan and a charge for
   the new plan; the customer sees both, not just the net.
"""
import unittest
from datetime import datetime, timedelta, timezone

THAO = "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"
RAMON = "Ram\u00f3n Etxeberria-Go\u00f1i"
MAX_DESC = 80
_DAY = timedelta(days=1)


def _int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _describe(label, name, end_date):
    prefix = f"{label} "
    suffix = f" until {end_date}"
    budget = MAX_DESC - len(prefix) - len(suffix)
    if len(name) > budget:
        name = name[:budget - 1] + "\u2026" if budget >= 2 else ""
    text = f"{prefix}{name}{suffix}" if name else f"{label}{suffix}"
    if len(text) > MAX_DESC:
        raise ValueError("description too long")
    return text


def prorate_seats(subscription, new_plan, changed_at):
    if subscription["status"] == "trialing":
        return []
    old_price = _int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _int(new_plan["seat_price_cents"], "new seat_price_cents")
    seats = _int(subscription["billable_seats"], "billable_seats")
    period_end = _aware(subscription["period_end"], "period_end")
    changed_at = _aware(changed_at, "changed_at")
    if new_price < old_price:
        return []
    days = min((period_end - changed_at) // _DAY, 30)
    if days <= 0:
        return []

    end_date = period_end.date().isoformat()
    sid = subscription["id"]
    credit = -(-(old_price * seats * days) // 30)
    charge = (new_price * seats * days) // 30
    vat_id = subscription.get("vat_id")
    has_vat_id = bool(vat_id is not None and str(vat_id).strip())

    lines = []
    if credit >= 50:
        lines.append({
            "subscription_id": sid,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit", str(subscription["plan_name"]), end_date),
            "approved_by": RAMON if credit > 50000 else THAO,
        })
    if charge >= 50:
        lines.append({
            "subscription_id": sid,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if has_vat_id else charge * 21 // 100,
            "description": _describe("Charge", str(new_plan["name"]), end_date),
            "approved_by": None,
        })
    return lines


# ---------------------------------------------------------------- tests
UTC = timezone.utc
END = datetime(2026, 1, 31, tzinfo=UTC)


def _sub(**kw):
    s = {"id": "s1", "status": "active", "plan_name": "Old", "seat_price_cents": 1000,
         "seats": 99, "billable_seats": 1, "vat_id": None, "period_end": END}
    s.update(kw)
    return s


def _new(price=2000, name="New"):
    return {"name": name, "seat_price_cents": price}


def _at(d):
    return END - timedelta(days=d)


class ProrateTests(unittest.TestCase):
    def test_trialing(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _new(), _at(30)), [])

    def test_downgrade(self):
        self.assertEqual(prorate_seats(_sub(), _new(999), _at(30)), [])

    def test_equal_price_nets_out(self):
        r = prorate_seats(_sub(seat_price_cents=1001), _new(1001), _at(2))
        self.assertEqual([l["amount_cents"] for l in r], [67, 66])

    def test_basic_upgrade_order_keys_types(self):
        r = prorate_seats(_sub(), _new(2000), _at(30))
        self.assertEqual([l["kind"] for l in r], ["credit", "charge"])
        self.assertEqual([l["amount_cents"] for l in r], [1000, 2000])
        self.assertEqual(r[1]["vat_cents"], 420)
        self.assertEqual(r[0]["vat_cents"], 0)
        self.assertIsNone(r[1]["approved_by"])
        for l in r:
            self.assertEqual(set(l), {"subscription_id", "kind", "amount_cents",
                                      "vat_cents", "description", "approved_by"})
            self.assertIs(type(l["amount_cents"]), int)
            self.assertIs(type(l["vat_cents"]), int)
        self.assertEqual(r[0]["description"], "Credit Old until 2026-01-31")
        self.assertEqual(r[1]["description"], "Charge New until 2026-01-31")

    def test_skip_credit_keep_charge_boundary(self):
        r = prorate_seats(_sub(seat_price_cents=49), _new(50), _at(30))
        self.assertEqual([(l["kind"], l["amount_cents"]) for l in r], [("charge", 50)])
        self.assertEqual(r[0]["vat_cents"], 10)

    def test_skip_charge_keep_credit(self):
        r = prorate_seats(_sub(seat_price_cents=745), _new(745), _at(2))
        self.assertEqual([(l["kind"], l["amount_cents"]) for l in r], [("credit", 50)])

    def test_both_skipped(self):
        self.assertEqual(prorate_seats(_sub(seat_price_cents=10), _new(20), _at(30)), [])

    def test_approver_boundary(self):
        r = prorate_seats(_sub(seat_price_cents=50000), _new(60000), _at(30))
        self.assertEqual(r[0]["approved_by"], THAO)
        r = prorate_seats(_sub(seat_price_cents=50001), _new(60000), _at(30))
        self.assertEqual(r[0]["approved_by"], RAMON)

    def test_vat_id_variants(self):
        for v, expected in (("PT123", 0), ("", 420), ("  ", 420), (None, 420)):
            r = prorate_seats(_sub(vat_id=v), _new(2000), _at(30))
            self.assertEqual(r[1]["vat_cents"], expected, v)

    def test_vat_rounds_down(self):
        r = prorate_seats(_sub(seat_price_cents=50), _new(55), _at(30))
        self.assertEqual(r[1]["vat_cents"], 11)

    def test_long_names(self):
        for ch in ("\u00e9", "\U0001F600", "\u6f22"):
            r = prorate_seats(_sub(plan_name=ch * 200), _new(2000, ch * 200), _at(30))
            for l in r:
                self.assertLessEqual(len(l["description"]), 80)
                self.assertTrue(l["description"].endswith("until 2026-01-31"))
                self.assertIn("\u2026", l["description"])

    def test_days_edges(self):
        self.assertEqual(prorate_seats(_sub(), _new(), END), [])
        self.assertEqual(prorate_seats(_sub(), _new(), END + timedelta(days=3)), [])
        self.assertEqual(prorate_seats(_sub(), _new(), END - timedelta(hours=23)), [])
        self.assertEqual(prorate_seats(_sub(), _new(), _at(45)),
                         prorate_seats(_sub(), _new(), _at(30)))

    def test_tz_aware(self):
        tz = timezone(timedelta(hours=14))
        end = datetime(2026, 1, 31, 0, 0, tzinfo=tz)
        ch = end.astimezone(UTC) - timedelta(days=10)
        r = prorate_seats(_sub(period_end=end), _new(), ch)
        self.assertEqual(r[0]["amount_cents"], 334)
        self.assertTrue(r[0]["description"].endswith("2026-01-31"))

    def test_naive_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _new(), datetime(2026, 1, 1))

    def test_billable_seats_used(self):
        r = prorate_seats(_sub(seats=99, billable_seats=3), _new(2000), _at(30))
        self.assertEqual(r[0]["amount_cents"], 3000)

    def test_zero_seats(self):
        self.assertEqual(prorate_seats(_sub(billable_seats=0), _new(), _at(30)), [])

    def test_validation(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(billable_seats=-1), _new(), _at(30))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(seat_price_cents=-1), _new(), _at(30))
        with self.assertRaises(TypeError):
            prorate_seats(_sub(billable_seats=1.0), _new(), _at(30))
        with self.assertRaises(TypeError):
            prorate_seats(_sub(billable_seats=True), _new(), _at(30))
        with self.assertRaises(TypeError):
            prorate_seats(_sub(), _new(20.5), _at(30))


if __name__ == "__main__":
    unittest.main()