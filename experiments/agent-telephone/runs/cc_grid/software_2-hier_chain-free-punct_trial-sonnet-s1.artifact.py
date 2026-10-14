# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-npw_akm1/prorate.py =====
"""Seat upgrade proration for Fernhollow Studios billing.

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list[dict]

Behaviour
- Bills on billable_seats (not seats). legacy_discount is ignored.
- Period is always 30 days. days_left = floor(period_end - changed_at) in whole
  days, clamped to 30. Returns [] if the delta is <= 0 or days_left is 0.
- Only a strictly higher per-seat price produces lines. Trialing -> [].
- Credit = ceil(old_price * seats * days / 30) at the OLD price.
  Charge = floor(new_price * seats * days / 30) at the NEW price.
- A line under 50 cents (pre-VAT, strict) is skipped independently.
- Charge VAT = floor(amount * 21 / 100), or 0 when vat_id is a non-blank string.
  Credits always have vat_cents 0.
- Credits need approval: APPROVER, or SENIOR_APPROVER when amount > 50000.

Flagged assumptions
- Partial days are dropped (floor). The unused remainder is therefore not
  credited or charged.
- days_left is clamped to 30; a period_end more than 30 days away is treated
  as 30 days.
- The description date is period_end's own local date (not converted to UTC).
- Departure from house rules: the house default is half-up rounding and VAT on
  credits. The design decisions given for this task override both (ceil/floor
  rounding, no VAT on credits).
"""
from datetime import datetime

APPROVER = "Nguyễn Thị Phương Thảo"
SENIOR_APPROVER = "Ramón Etxeberria-Goñi"
PERIOD_DAYS = 30
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
SENIOR_THRESHOLD_CENTS = 50000
MAX_DESC = 80


def _int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    return value


def _aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _desc(prefix, plan, date_str):
    suffix = f" to {date_str}"
    budget = MAX_DESC - len(prefix) - len(suffix)
    if len(plan) > budget:
        plan = plan[: max(budget - 1, 0)] + "…"
    return f"{prefix}{plan}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    old_price = _int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _int(new_plan["seat_price_cents"], "new_plan.seat_price_cents")
    seats = _int(subscription["billable_seats"], "billable_seats")
    period_end = subscription["period_end"]
    _aware(period_end, "period_end")
    _aware(changed_at, "changed_at")

    if subscription.get("status") == "trialing" or seats <= 0:
        return []
    if new_price <= old_price:
        return []

    delta = period_end - changed_at
    if delta.total_seconds() <= 0:
        return []
    days_left = min(delta.days, PERIOD_DAYS)
    if days_left <= 0:
        return []

    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _desc("Credit unused ", str(subscription["plan_name"]), date_str),
            "approved_by": SENIOR_APPROVER if credit > SENIOR_THRESHOLD_CENTS else APPROVER,
        })

    charge = (new_price * seats * days_left) // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        vat_id = subscription.get("vat_id")
        reverse = isinstance(vat_id, str) and bool(vat_id.strip())
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * VAT_PERCENT // 100,
            "description": _desc("Charge ", str(new_plan["name"]), date_str),
            "approved_by": None,
        })
    return lines


# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-npw_akm1/test_prorate.py =====
import unittest
from datetime import datetime, timedelta, timezone

from prorate import prorate_seats, APPROVER, SENIOR_APPROVER

UTC = timezone.utc
END = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def sub(**kw):
    d = dict(id="s1", status="active", plan_name="Basic", seat_price_cents=1000,
             seats=5, billable_seats=4, vat_id="", period_end=END)
    d.update(kw)
    return d


def plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def at(days=10, **kw):
    return END - timedelta(days=days, **kw)


class ProrateTests(unittest.TestCase):
    def test_happy_path_exact(self):
        lines = prorate_seats(sub(), plan(), at(10))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        c, ch = lines
        self.assertEqual(c["amount_cents"], 1334)
        self.assertEqual(c["vat_cents"], 0)
        self.assertEqual(c["approved_by"], APPROVER)
        self.assertEqual(c["subscription_id"], "s1")
        self.assertEqual(ch["amount_cents"], 2666)
        self.assertEqual(ch["vat_cents"], 559)
        self.assertIsNone(ch["approved_by"])
        self.assertEqual(c["description"], "Credit unused Basic to 2026-11-01")
        self.assertEqual(ch["description"], "Charge Pro to 2026-11-01")

    def test_ceil_vs_floor(self):
        c, ch = prorate_seats(sub(seat_price_cents=1010, billable_seats=1),
                              plan(1510), at(7))
        self.assertEqual(c["amount_cents"], 236)
        self.assertEqual(ch["amount_cents"], 352)

    def test_billable_not_seats(self):
        a = prorate_seats(sub(seats=100, billable_seats=4), plan(), at(10))
        b = prorate_seats(sub(seats=1, billable_seats=4), plan(), at(10))
        self.assertEqual(a, b)
        self.assertEqual(a[0]["amount_cents"], 1334)

    def test_no_lines_cases(self):
        self.assertEqual(prorate_seats(sub(), plan(500), at()), [])
        self.assertEqual(prorate_seats(sub(), plan(1000), at()), [])
        self.assertEqual(prorate_seats(sub(status="trialing"), plan(), at()), [])
        self.assertEqual(prorate_seats(sub(billable_seats=0), plan(), at()), [])
        self.assertEqual(prorate_seats(sub(billable_seats=-1), plan(), at()), [])

    def test_period_end_edges(self):
        self.assertEqual(prorate_seats(sub(), plan(), END), [])
        self.assertEqual(prorate_seats(sub(), plan(), END + timedelta(days=1)), [])
        self.assertEqual(prorate_seats(sub(), plan(), END - timedelta(hours=23)), [])

    def test_clamp_and_partial_day(self):
        full = prorate_seats(sub(), plan(), at(30))
        self.assertEqual(prorate_seats(sub(), plan(), at(45)), full)
        self.assertEqual(full[0]["amount_cents"], 4000)
        self.assertEqual(prorate_seats(sub(), plan(), at(10, hours=23)),
                         prorate_seats(sub(), plan(), at(10)))

    def test_boundaries_and_independent_skip(self):
        s = sub(seat_price_cents=10, billable_seats=1)
        self.assertEqual(prorate_seats(s, plan(49), at(30)), [])
        r = prorate_seats(s, plan(50), at(30))
        self.assertEqual([l["kind"] for l in r], ["charge"])
        self.assertEqual(r[0]["amount_cents"], 50)
        s = sub(seat_price_cents=49, billable_seats=1)
        r = prorate_seats(s, plan(100), at(30))
        self.assertEqual([l["kind"] for l in r], ["charge"])
        r = prorate_seats(sub(seat_price_cents=50, billable_seats=1), plan(100), at(30))
        self.assertEqual([l["kind"] for l in r], ["credit", "charge"])

    def test_vat(self):
        r = prorate_seats(sub(seat_price_cents=10, billable_seats=1), plan(100), at(30))
        self.assertEqual(r[0]["vat_cents"], 21)
        for vid in ("NL123", " x "):
            r = prorate_seats(sub(vat_id=vid), plan(), at(10))
            self.assertEqual(r[1]["vat_cents"], 0)
        r = prorate_seats(sub(vat_id="   "), plan(), at(10))
        self.assertEqual(r[1]["vat_cents"], 559)
        r = prorate_seats(sub(vat_id=None), plan(), at(10))
        self.assertEqual(r[1]["vat_cents"], 559)
        self.assertEqual(r[0]["vat_cents"], 0)

    def test_approval_boundary(self):
        base = dict(billable_seats=1)
        r = prorate_seats(sub(seat_price_cents=50000, **base), plan(60000), at(30))
        self.assertEqual(r[0]["amount_cents"], 50000)
        self.assertEqual(r[0]["approved_by"], "Nguyễn Thị Phương Thảo")
        r = prorate_seats(sub(seat_price_cents=50001, **base), plan(60000), at(30))
        self.assertEqual(r[0]["amount_cents"], 50001)
        self.assertEqual(r[0]["approved_by"], "Ramón Etxeberria-Goñi")
        self.assertEqual(SENIOR_APPROVER, "Ramón Etxeberria-Goñi")

    def test_non_ascii_names(self):
        r = prorate_seats(sub(plan_name="Ünïcödé Ñ"), plan(name="プロ"), at(10))
        self.assertEqual(r[0]["description"], "Credit unused Ünïcödé Ñ to 2026-11-01")
        self.assertEqual(r[1]["description"], "Charge プロ to 2026-11-01")

    def test_description_length(self):
        for name in ("x" * 500, "é" * 500, "日" * 81):
            r = prorate_seats(sub(plan_name=name), plan(name=name), at(10))
            for l in r:
                self.assertLessEqual(len(l["description"]), 80)
                self.assertTrue(l["description"].endswith(" to 2026-11-01"))
                self.assertIn("…", l["description"])

    def test_date_in_own_timezone(self):
        tz = timezone(timedelta(hours=14))
        end = datetime(2026, 11, 2, 1, 0, tzinfo=tz)  # 2026-11-01 in UTC
        r = prorate_seats(sub(period_end=end), plan(), end - timedelta(days=10))
        self.assertTrue(r[0]["description"].endswith("2026-11-02"))

    def test_validation(self):
        with self.assertRaises(ValueError):
            prorate_seats(sub(), plan(), datetime(2026, 10, 20))
        with self.assertRaises(ValueError):
            prorate_seats(sub(period_end=datetime(2026, 11, 1)), plan(), at())
        for bad in (10.0, True, "10"):
            with self.assertRaises((TypeError, ValueError)):
                prorate_seats(sub(seat_price_cents=bad), plan(), at())
            with self.assertRaises((TypeError, ValueError)):
                prorate_seats(sub(), plan(bad), at())
            with self.assertRaises((TypeError, ValueError)):
                prorate_seats(sub(billable_seats=bad), plan(), at())

    def test_ints_only(self):
        for l in prorate_seats(sub(), plan(), at(10)):
            self.assertIs(type(l["amount_cents"]), int)
            self.assertIs(type(l["vat_cents"]), int)


if __name__ == "__main__":
    unittest.main()