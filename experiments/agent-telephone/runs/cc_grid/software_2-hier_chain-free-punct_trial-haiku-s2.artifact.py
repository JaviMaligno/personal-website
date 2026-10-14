# File: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-761sei0t/seat_proration.py
"""Seat-upgrade proration for Fernhollow Studios billing (client: Ingrid).

Assumptions to confirm with the client:
- All amounts are EUR cents. The inputs carry no currency field.
- Only the status "trialing" is special-cased. Other statuses are not
  specified and are processed like any other status.
- The seats key is never read. Billing uses billable_seats only.
- legacy_discount is never read.
- Plan names are validated (non-empty after strip) on every call, even when
  the call returns [] early.

Open blockers for the tech lead:
- The inputs cannot show whether a non-EUR subscription can occur.
- Dropping a credit under 50 cents costs the client, which conflicts with the
  rule that rounding never favours the provider. Implemented as written.
"""

from datetime import datetime, timedelta, timezone

_PERIOD_US = 30 * 86400 * 10**6
_MIN_LINE_CENTS = 50
_LARGE_CREDIT_CENTS = 50000
_VAT_PERCENT = 21
_DESC_MAX = 80
_DESC_MIN_BUDGET = 4
_APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
_APPROVER_LARGE = "Ramón Etxeberria-Goñi"
_CREDIT_PREFIX = "Credit for unused "
_CHARGE_PREFIX = "Charge for unused "
_DATE_PREFIX = ", period end "
_UTC = timezone.utc
_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def _require_keys(mapping, keys, label):
    if not isinstance(mapping, dict):
        raise TypeError(f"{label} must be a dict")
    for key in keys:
        if key not in mapping:
            raise ValueError(f"{label} is missing key {key!r}")


def _require_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be a plain int")
    if value < 0:
        raise ValueError(f"{label} must be non-negative")
    return value


def _require_aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value


def _plan_name(value, label):
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a str")
    name = value.strip()
    if not name:
        raise ValueError(f"{label} must not be empty")
    return name


def _vat_is_empty(vat_id):
    if vat_id is None:
        return True
    if not isinstance(vat_id, str):
        raise TypeError("vat_id must be a str or None")
    return vat_id.strip() == ""


def _build_description(prefix, plan, date_text):
    tail = _DATE_PREFIX + date_text
    budget = _DESC_MAX - len(prefix) - len(tail)
    if budget < _DESC_MIN_BUDGET:
        raise ValueError("description budget too small for plan name")
    full = prefix + plan + tail
    if len(full) <= _DESC_MAX:
        return full
    short = plan[: budget - 3] + "..."
    return prefix + short + tail


def _line(sub_id, kind, amount, vat, description, approved_by):
    return {
        "subscription_id": sub_id,
        "kind": kind,
        "amount_cents": amount,
        "vat_cents": vat,
        "description": description,
        "approved_by": approved_by,
    }


def prorate_seats(subscription, new_plan, changed_at):
    _require_keys(subscription, _SUB_KEYS, "subscription")
    _require_keys(new_plan, _PLAN_KEYS, "new_plan")
    _require_aware(changed_at, "changed_at")
    period_end = _require_aware(subscription["period_end"], "period_end")
    old_price = _require_int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _require_int(new_plan["seat_price_cents"], "new plan seat_price_cents")
    billable = _require_int(subscription["billable_seats"], "billable_seats")
    old_name = _plan_name(subscription["plan_name"], "plan_name")
    new_name = _plan_name(new_plan["name"], "new plan name")
    vat_empty = _vat_is_empty(subscription["vat_id"])

    if subscription["status"] == "trialing":
        return []
    if new_price <= old_price:
        return []

    unused_us = (period_end.astimezone(_UTC)
                 - changed_at.astimezone(_UTC)) // timedelta(microseconds=1)
    if unused_us <= 0:
        return []

    sub_id = subscription["id"]
    date_text = period_end.date().isoformat()
    lines = []

    credit = -((-(old_price * billable * unused_us)) // _PERIOD_US)
    if credit >= _MIN_LINE_CENTS:
        approver = _APPROVER_LARGE if credit > _LARGE_CREDIT_CENTS else _APPROVER_DEFAULT
        lines.append(_line(sub_id, "credit", credit, 0,
                           _build_description(_CREDIT_PREFIX, old_name, date_text),
                           approver))

    charge = (new_price * billable * unused_us) // _PERIOD_US
    if charge >= _MIN_LINE_CENTS:
        vat = 0 if not vat_empty else charge * _VAT_PERCENT // 100
        lines.append(_line(sub_id, "charge", charge, vat,
                           _build_description(_CHARGE_PREFIX, new_name, date_text),
                           None))

    return lines

# ---- next file: test_seat_proration.py (save at its own absolute path) ----

# File: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-761sei0t/test_seat_proration.py
# Status: not executed. This environment has no execution tools, so these tests
# have not been run. Run with: python3 -I test_seat_proration.py
# The sys.path line below is needed because -I removes the script directory
# from sys.path.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from seat_proration import prorate_seats

UTC = timezone.utc
PE = datetime(2026, 10, 31, 0, 0, tzinfo=UTC)
HALF = PE - timedelta(days=15)
THAO = "Nguyễn Thị Phương Thảo"
RAMON = "Ramón Etxeberria-Goñi"


def _sub(**over):
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Basic",
        "seat_price_cents": 1000,
        "seats": 99,
        "billable_seats": 1,
        "vat_id": None,
        "period_end": PE,
    }
    base.update(over)
    return base


def _plan(price, name="Pro"):
    return {"name": name, "seat_price_cents": price}


class ProrateTests(unittest.TestCase):

    def test_normal_upgrade_both_lines(self):
        lines = prorate_seats(_sub(billable_seats=10), _plan(1500), HALF)
        self.assertEqual(lines, [
            {"subscription_id": "sub_1", "kind": "credit", "amount_cents": 5000,
             "vat_cents": 0,
             "description": "Credit for unused Basic, period end 2026-10-31",
             "approved_by": THAO},
            {"subscription_id": "sub_1", "kind": "charge", "amount_cents": 7500,
             "vat_cents": 1575,
             "description": "Charge for unused Pro, period end 2026-10-31",
             "approved_by": None},
        ])

    def test_credit_before_charge(self):
        lines = prorate_seats(_sub(billable_seats=10), _plan(1500), HALF)
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])

    def test_ceiling_on_credit_and_floor_on_charge(self):
        changed = PE - timedelta(days=1)
        lines = prorate_seats(_sub(billable_seats=10), _plan(1600), changed)
        self.assertEqual(lines[0]["kind"], "credit")
        self.assertEqual(lines[0]["amount_cents"], 334)   # 333.33 ceiled
        self.assertEqual(lines[1]["kind"], "charge")
        self.assertEqual(lines[1]["amount_cents"], 533)   # 533.33 floored
        self.assertEqual(lines[1]["vat_cents"], 111)      # 533 * 21 // 100

    def test_credit_dropped_charge_kept(self):
        lines = prorate_seats(_sub(seat_price_cents=10), _plan(1000), HALF)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 500)
        self.assertEqual(lines[0]["vat_cents"], 105)

    def test_charge_dropped_credit_kept(self):
        # credit = ceil(49.2) = 50 (kept); charge = floor(49.3) = 49 (dropped)
        lines = prorate_seats(_sub(seat_price_cents=492), _plan(493),
                              PE - timedelta(days=3))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "credit")
        self.assertEqual(lines[0]["amount_cents"], 50)
        self.assertEqual(lines[0]["approved_by"], THAO)

    def test_threshold_exactly_50000_keeps_default_approver(self):
        lines = prorate_seats(_sub(seat_price_cents=50000), _plan(50001),
                              PE - timedelta(days=30))
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], THAO)

    def test_threshold_50001_uses_large_approver(self):
        lines = prorate_seats(_sub(seat_price_cents=50001), _plan(50002),
                              PE - timedelta(days=30))
        self.assertEqual(lines[0]["amount_cents"], 50001)
        self.assertEqual(lines[0]["approved_by"], RAMON)

    def test_vat_floor_on_charge(self):
        lines = prorate_seats(_sub(seat_price_cents=0), _plan(1001),
                              PE - timedelta(days=30))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["amount_cents"], 1001)
        self.assertEqual(lines[0]["vat_cents"], 210)  # 21021 // 100

    def test_reverse_charge_when_vat_id_set(self):
        lines = prorate_seats(_sub(billable_seats=10, vat_id="DE123456789"),
                              _plan(1500), HALF)
        self.assertEqual(lines[1]["vat_cents"], 0)
        self.assertEqual(lines[0]["vat_cents"], 0)

    def test_whitespace_vat_id_treated_as_empty(self):
        lines = prorate_seats(_sub(billable_seats=10, vat_id="   "),
                              _plan(1500), HALF)
        self.assertEqual(lines[1]["vat_cents"], 1575)

    def test_trialing_returns_empty(self):
        self.assertEqual(
            prorate_seats(_sub(status="trialing"), _plan(1500), HALF), [])

    def test_downgrade_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(500), HALF), [])

    def test_equal_price_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(1000), HALF), [])

    def test_changed_after_period_end_returns_empty(self):
        self.assertEqual(
            prorate_seats(_sub(), _plan(1500), PE + timedelta(days=1)), [])

    def test_changed_equal_period_end_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(1500), PE), [])

    def test_zero_billable_returns_empty(self):
        self.assertEqual(
            prorate_seats(_sub(billable_seats=0), _plan(1500), HALF), [])

    def test_mixed_timezone_across_dst_matches_utc(self):
        berlin = ZoneInfo("Europe/Berlin")
        changed_local = datetime(2026, 3, 1, 12, 0, tzinfo=berlin)
        end_local = datetime(2026, 3, 29, 12, 0, tzinfo=berlin)
        mixed = prorate_seats(
            _sub(period_end=end_local, billable_seats=1000),
            _plan(2000), changed_local)
        utc_only = prorate_seats(
            _sub(period_end=end_local.astimezone(UTC), billable_seats=1000),
            _plan(2000), changed_local.astimezone(UTC))
        self.assertTrue(mixed)
        self.assertEqual(mixed, utc_only)

    def test_long_plan_names_truncated_and_date_kept(self):
        lines = prorate_seats(_sub(plan_name="A" * 60), _plan(1500, "B" * 60),
                              HALF)
        credit_desc = "Credit for unused " + "A" * 36 + "..." + ", period end 2026-10-31"
        charge_desc = "Charge for unused " + "B" * 36 + "..." + ", period end 2026-10-31"
        self.assertEqual(lines[0]["description"], credit_desc)
        self.assertEqual(lines[1]["description"], charge_desc)
        for line in lines:
            self.assertLessEqual(len(line["description"]), 80)
            self.assertEqual(len(line["description"]), 80)
            self.assertIn("2026-10-31", line["description"])

    def test_output_amounts_are_int(self):
        lines = prorate_seats(_sub(billable_seats=10), _plan(1500), HALF)
        self.assertTrue(lines)
        for line in lines:
            self.assertIs(type(line["amount_cents"]), int)
            self.assertIs(type(line["vat_cents"]), int)
            self.assertEqual(set(line.keys()), {
                "subscription_id", "kind", "amount_cents",
                "vat_cents", "description", "approved_by"})

    def test_legacy_discount_and_seats_ignored(self):
        base = prorate_seats(_sub(billable_seats=10), _plan(1500), HALF)
        other = prorate_seats(
            _sub(billable_seats=10, legacy_discount="garbage", seats="x"),
            _plan(1500), HALF)
        self.assertEqual(base, other)

    def test_naive_changed_at_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(1500), datetime(2026, 10, 15, 12, 0))

    def test_bool_price_rejected(self):
        with self.assertRaises(TypeError):
            prorate_seats(_sub(seat_price_cents=True), _plan(1500), HALF)

    def test_float_price_rejected(self):
        with self.assertRaises(TypeError):
            prorate_seats(_sub(seat_price_cents=1000.0), _plan(1500), HALF)

    def test_float_billable_rejected(self):
        with self.assertRaises(TypeError):
            prorate_seats(_sub(billable_seats=1.0), _plan(1500), HALF)

    def test_bool_new_price_rejected(self):
        with self.assertRaises(TypeError):
            prorate_seats(_sub(), _plan(True), HALF)

    def test_negative_billable_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(billable_seats=-1), _plan(1500), HALF)

    def test_empty_plan_name_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(plan_name="   "), _plan(1500), HALF)


if __name__ == "__main__":
    unittest.main()