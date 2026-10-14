# /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-s704ratn/fernhollow_proration/proration.py
"""Seat-upgrade proration for Fernhollow Studios (client contact: Ingrid).

Open points, implemented as defaults and pending client confirmation:
1. Concrete rounding rules are followed, not the "never round in the client's favour" wording.
2. changed_at earlier than period_end minus 30 days raises ValueError.
3. Description templates are invented; the client supplied none.
4. All amounts are assumed to be EUR.
5. Every non-trialing status is prorated.
6. Equal seat prices proceed through proration (only a strictly lower new price exits).
"""

import math
from datetime import datetime, timedelta
from fractions import Fraction

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
LARGE_CREDIT_CENTS = 50000
VAT_PERCENT = 21
DESCRIPTION_MAX = 80
APPROVER_LARGE = "Ramón Etxeberria-Goñi"
APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
_MICROSECOND = timedelta(microseconds=1)
_MICROS_PER_DAY = 86400 * 10**6


def _check_aware(name, value):
    if not isinstance(value, datetime):
        raise ValueError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _check_int_nonneg(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must not be negative")


def _vat_absent(vat_id):
    return vat_id is None or str(vat_id).strip() == ""


def _ymd(dt):
    return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"


def _describe(prefix, name, date_text):
    suffix = f" seats, period ends {date_text}"
    budget = DESCRIPTION_MAX - len(prefix) - len(suffix)
    if len(name) > budget:
        name = name[:budget - 3] + "..."
    return f"{prefix}{name}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    _check_aware("changed_at", changed_at)
    period_end = subscription["period_end"]
    _check_aware("period_end", period_end)

    _check_int_nonneg("seats", subscription["seats"])
    _check_int_nonneg("billable_seats", subscription["billable_seats"])
    _check_int_nonneg("seat_price_cents", subscription["seat_price_cents"])
    _check_int_nonneg("new plan seat_price_cents", new_plan["seat_price_cents"])

    if changed_at < period_end - timedelta(days=PERIOD_DAYS):
        raise ValueError("changed_at is earlier than period_end minus 30 days")

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]

    if subscription["status"] == "trialing":
        return []
    if new_price < old_price:
        return []
    if changed_at >= period_end:
        return []

    billable = subscription["billable_seats"]
    unused_micros = (period_end - changed_at) // _MICROSECOND
    unused_days = Fraction(unused_micros, _MICROS_PER_DAY)
    fraction = unused_days / PERIOD_DAYS

    credit_gross = Fraction(old_price * billable) * fraction
    charge_gross = Fraction(new_price * billable) * fraction
    credit_cents = math.ceil(credit_gross)
    charge_cents = math.floor(charge_gross)

    date_text = _ymd(period_end)
    subscription_id = subscription["id"]
    lines = []

    if credit_cents >= MIN_LINE_CENTS:
        approved = APPROVER_LARGE if credit_cents > LARGE_CREDIT_CENTS else APPROVER_DEFAULT
        lines.append({
            "subscription_id": subscription_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe("Credit: unused ", subscription["plan_name"], date_text),
            "approved_by": approved,
        })

    if charge_cents >= MIN_LINE_CENTS:
        if _vat_absent(subscription.get("vat_id")):
            vat = charge_cents * VAT_PERCENT // 100
        else:
            vat = 0
        lines.append({
            "subscription_id": subscription_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat,
            "description": _describe("Charge: prorated ", new_plan["name"], date_text),
            "approved_by": None,
        })

    return lines


# /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-s704ratn/fernhollow_proration_tests/test_proration.py
# NOT EXECUTED: this session had no interpreter access, so these tests have not been run.
# Run with: python3 -I -m unittest discover -s <this directory> -v

import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-s704ratn/fernhollow_proration")
from proration import prorate_seats  # noqa: E402

UTC = timezone.utc
PERIOD_END = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_APPROVER = "Ramón Etxeberria-Goñi"


def sub(**overrides):
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Team",
        "seat_price_cents": 1000,
        "seats": 10,
        "billable_seats": 10,
        "vat_id": None,
        "period_end": PERIOD_END,
    }
    base.update(overrides)
    return base


def plan(price=1500, name="Business"):
    return {"name": name, "seat_price_cents": price}


class ProrationTests(unittest.TestCase):

    def test_worked_example(self):
        changed = PERIOD_END - timedelta(days=10, hours=6)
        credit, charge = prorate_seats(sub(), plan(), changed)
        self.assertEqual(credit, {
            "subscription_id": "sub_1",
            "kind": "credit",
            "amount_cents": 3417,
            "vat_cents": 0,
            "description": "Credit: unused Team seats, period ends 2026-11-01",
            "approved_by": CREDIT_APPROVER,
        })
        self.assertEqual(charge, {
            "subscription_id": "sub_1",
            "kind": "charge",
            "amount_cents": 5125,
            "vat_cents": 1076,
            "description": "Charge: prorated Business seats, period ends 2026-11-01",
            "approved_by": None,
        })

    def test_trialing_exits_empty(self):
        changed = PERIOD_END - timedelta(days=10, hours=6)
        self.assertEqual(prorate_seats(sub(status="trialing"), plan(), changed), [])

    def test_downgrade_exits_empty(self):
        changed = PERIOD_END - timedelta(days=10, hours=6)
        self.assertEqual(prorate_seats(sub(), plan(price=900), changed), [])

    def test_equal_price_proceeds(self):
        changed = PERIOD_END - timedelta(days=10, hours=6)
        lines = prorate_seats(sub(), plan(price=1000), changed)
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])

    def test_one_line_dropped_other_kept(self):
        # Half a period left: credit 99 * 1/2 = 49.5 ceils to 50 (kept);
        # charge 99 * 1/2 = 49.5 floors to 49 (dropped).
        changed = PERIOD_END - timedelta(days=15)
        lines = prorate_seats(sub(seat_price_cents=99, billable_seats=1), plan(price=99), changed)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "credit")
        self.assertEqual(lines[0]["amount_cents"], 50)
        self.assertEqual(lines[0]["approved_by"], CREDIT_APPROVER)

    def test_both_lines_dropped_returns_empty(self):
        changed = PERIOD_END - timedelta(hours=1)
        self.assertEqual(prorate_seats(sub(), plan(), changed), [])

    def test_approval_boundary_50000_is_default_approver(self):
        changed = PERIOD_END - timedelta(days=30)
        credit, charge = prorate_seats(
            sub(seat_price_cents=50000, billable_seats=1), plan(price=50000), changed)
        self.assertEqual(credit["amount_cents"], 50000)
        self.assertEqual(credit["approved_by"], CREDIT_APPROVER)

    def test_approval_boundary_50001_is_large_approver(self):
        changed = PERIOD_END - timedelta(days=30)
        credit, charge = prorate_seats(
            sub(seat_price_cents=50001, billable_seats=1), plan(price=50001), changed)
        self.assertEqual(credit["amount_cents"], 50001)
        self.assertEqual(credit["approved_by"], LARGE_APPROVER)

    def test_reverse_charge_with_vat_id(self):
        changed = PERIOD_END - timedelta(days=10, hours=6)
        credit, charge = prorate_seats(sub(vat_id="DE123456789"), plan(), changed)
        self.assertEqual(charge["amount_cents"], 5125)
        self.assertEqual(charge["vat_cents"], 0)
        self.assertEqual(credit["vat_cents"], 0)

    def test_whitespace_vat_id_treated_as_absent(self):
        changed = PERIOD_END - timedelta(days=10, hours=6)
        credit, charge = prorate_seats(sub(vat_id="   "), plan(), changed)
        self.assertEqual(charge["vat_cents"], 1076)

    def test_long_description_truncates_name_keeps_date(self):
        changed = PERIOD_END - timedelta(days=10, hours=6)
        credit, charge = prorate_seats(sub(plan_name="X" * 100), plan(), changed)
        desc = credit["description"]
        self.assertEqual(len(desc), 80)
        self.assertTrue(desc.startswith("Credit: unused "))
        self.assertTrue(desc.endswith(" seats, period ends 2026-11-01"))
        self.assertIn("...", desc)

    def test_naive_changed_at_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(sub(), plan(), datetime(2026, 10, 22, 6, 0))

    def test_naive_period_end_raises(self):
        naive_end = datetime(2026, 11, 1, 12, 0)
        with self.assertRaises(ValueError):
            prorate_seats(sub(period_end=naive_end), plan(),
                          datetime(2026, 10, 22, 6, 0, tzinfo=UTC))

    def test_negative_seats_raises(self):
        changed = PERIOD_END - timedelta(days=10)
        with self.assertRaises(ValueError):
            prorate_seats(sub(billable_seats=-1), plan(), changed)

    def test_changed_earlier_than_30_days_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(sub(), plan(), PERIOD_END - timedelta(days=31))

    def test_zero_billable_seats_gives_empty(self):
        changed = PERIOD_END - timedelta(days=10, hours=6)
        self.assertEqual(prorate_seats(sub(billable_seats=0), plan(), changed), [])


if __name__ == "__main__":
    unittest.main()