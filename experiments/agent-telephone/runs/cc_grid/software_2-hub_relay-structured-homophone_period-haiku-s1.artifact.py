#!/usr/bin/env python3
"""Seat-upgrade proration for Fernhollow Studios.

Module: fernhollow_seat_proration.py
Entry point: prorate_seats(subscription, new_plan, changed_at) -> list[dict]
Standard library only. Run the bundled tests with: python3 -I fernhollow_seat_proration.py

Assumptions from the product spec. Items marked CONFIRM need client or finance sign-off.
A1  CONFIRM (client): seat prices are EUR cents, with no conversion.
A2  CONFIRM (client): the EUR 500 approver threshold is compared against the credit amount_cents. Credits carry no VAT.
A3  changed_at at or after period_end returns []. This is not an error.
A4  billable_seats == 0 returns []. Negative billable_seats raises ValueError.
A5  The 50-cent minimum applies per line, on the pre-VAT amount_cents.
A6  CONFIRM (client, said "days left"): the unused fraction is exact elapsed microseconds from changed_at to period_end divided by PERIOD_DAYS * 86400 seconds. Credit = old seat price * billable_seats * fraction, rounded up. Charge = new seat price * billable_seats * fraction, rounded down. Integer arithmetic only.
A7  amount_cents is always a positive int. kind carries the direction.
A8  CONFIRM (finance): charge vat_cents = 21% of amount_cents, rounded down.
A9  Description templates: "Unused {plan} seats until {YYYY-MM-DD}". If too long, the plan name is truncated and "..." is appended. Length is counted in code points.
A10 The credit names subscription["plan_name"]. The charge names new_plan["name"].
A11 CONFIRM (client): only "trialing" is no-proration. All other statuses prorate.
A12 If the new seat_price_cents equals the old one, return []. Comparison uses seat_price_cents only.
A13 CONTROL GAP: approved_by values are recorded as specified. This module does not verify approvals. Approval enforcement must happen upstream.
A14 CONFIRM (client): PERIOD_DAYS = 13 is a single named constant.
A15 Invalid inputs (missing keys, naive datetimes, negative amounts, wrong types) raise ValueError.

Additional assumptions beyond the spec (CONFIRM):
X1  An unused span longer than PERIOD_DAYS raises ValueError, to avoid billing more than one period.
X2  vat_id of None or "" both mean no VAT ID, so VAT applies.
X3  The legacy_discount field is never read (R21).
"""

from datetime import datetime, timedelta, timezone

PERIOD_DAYS = 13
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
LARGE_CREDIT_CENTS = 50000
MAX_DESCRIPTION_LEN = 80
ELLIPSIS = "..."
TRIALING = "trialing"
STANDARD_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"

_PERIOD_US = PERIOD_DAYS * 86400 * 10**6
_SUBSCRIPTION_KEYS = ("id", "status", "plan_name", "seat_price_cents",
                      "seats", "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def _check_int(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    if value < minimum:
        raise ValueError(f"{label} must be >= {minimum}")


def _check_str(value, label):
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")


def _check_aware(value, label):
    if not isinstance(value, datetime):
        raise ValueError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _validate(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict):
        raise ValueError("subscription must be a dict")
    if not isinstance(new_plan, dict):
        raise ValueError("new_plan must be a dict")
    for key in _SUBSCRIPTION_KEYS:
        if key not in subscription:
            raise ValueError(f"subscription is missing key {key!r}")
    for key in _PLAN_KEYS:
        if key not in new_plan:
            raise ValueError(f"new_plan is missing key {key!r}")
    _check_str(subscription["id"], "subscription id")
    _check_str(subscription["status"], "subscription status")
    _check_str(subscription["plan_name"], "subscription plan_name")
    _check_str(new_plan["name"], "new_plan name")
    if subscription["vat_id"] is not None:
        _check_str(subscription["vat_id"], "vat_id")
    _check_int(subscription["seat_price_cents"], "seat_price_cents")
    _check_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    _check_int(subscription["seats"], "seats")
    _check_int(subscription["billable_seats"], "billable_seats")
    _check_aware(subscription["period_end"], "period_end")
    _check_aware(changed_at, "changed_at")


def _ceil_div(numerator, denominator):
    return -((-numerator) // denominator)


def _describe(plan_name, date_str):
    prefix = "Unused "
    suffix = f" seats until {date_str}"
    full = f"{prefix}{plan_name}{suffix}"
    if len(full) <= MAX_DESCRIPTION_LEN:
        return full
    fixed = len(prefix) + len(suffix)
    if fixed + len(ELLIPSIS) > MAX_DESCRIPTION_LEN:
        raise ValueError("description template and date exceed 80 characters")
    keep = MAX_DESCRIPTION_LEN - fixed - len(ELLIPSIS)
    return f"{prefix}{plan_name[:keep]}{ELLIPSIS}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    """Return invoice lines for a seat upgrade: credit first, then charge."""
    _validate(subscription, new_plan, changed_at)

    if subscription["status"] == TRIALING:
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    billable = subscription["billable_seats"]
    if billable == 0 or new_price <= old_price:
        return []

    period_end = subscription["period_end"]
    elapsed_us = (period_end - changed_at) // timedelta(microseconds=1)
    if elapsed_us <= 0:
        return []
    if elapsed_us > _PERIOD_US:
        raise ValueError("unused span exceeds the billing period")

    credit_cents = _ceil_div(old_price * billable * elapsed_us, _PERIOD_US)
    charge_cents = (new_price * billable * elapsed_us) // _PERIOD_US
    date_str = period_end.date().isoformat()

    lines = []
    if credit_cents >= MIN_LINE_CENTS:
        approver = (LARGE_CREDIT_APPROVER if credit_cents > LARGE_CREDIT_CENTS
                    else STANDARD_APPROVER)
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe(subscription["plan_name"], date_str),
            "approved_by": approver,
        })
    if charge_cents >= MIN_LINE_CENTS:
        if subscription["vat_id"]:
            vat_cents = 0
        else:
            vat_cents = charge_cents * VAT_PERCENT // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _describe(new_plan["name"], date_str),
            "approved_by": None,
        })
    return lines


if __name__ == "__main__":
    import unittest

    UTC = timezone.utc
    PE = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    HALF = PE - timedelta(days=6, hours=12)
    QUARTER = PE - timedelta(days=3, hours=6)
    FULL = PE - timedelta(days=13)
    STD = STANDARD_APPROVER
    LARGE = LARGE_CREDIT_APPROVER

    def _sub(**over):
        base = {"id": "sub_1", "status": "active", "plan_name": "Team",
                "seat_price_cents": 1000, "seats": 10, "billable_seats": 10,
                "vat_id": None, "period_end": PE,
                "legacy_discount": "not-read"}
        base.update(over)
        return base

    def _plan(**over):
        base = {"name": "Business", "seat_price_cents": 2000}
        base.update(over)
        return base

    def _walk_floats(value):
        if isinstance(value, float):
            return True
        if isinstance(value, dict):
            return any(_walk_floats(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return any(_walk_floats(v) for v in value)
        return False

    class ProrateTests(unittest.TestCase):

        def test_constants(self):
            self.assertEqual(PERIOD_DAYS, 13)
            self.assertEqual(VAT_PERCENT, 21)

        def test_basic_upgrade_lines(self):
            lines = prorate_seats(_sub(), _plan(), HALF)
            self.assertEqual(len(lines), 2)
            credit, charge = lines
            self.assertEqual(credit["kind"], "credit")
            self.assertEqual(credit["amount_cents"], 5000)
            self.assertEqual(credit["vat_cents"], 0)
            self.assertEqual(credit["approved_by"], STD)
            self.assertEqual(credit["subscription_id"], "sub_1")
            self.assertEqual(credit["description"],
                             "Unused Team seats until 2026-11-01")
            self.assertEqual(charge["kind"], "charge")
            self.assertEqual(charge["amount_cents"], 10000)
            self.assertEqual(charge["vat_cents"], 2100)
            self.assertIsNone(charge["approved_by"])
            self.assertEqual(charge["description"],
                             "Unused Business seats until 2026-11-01")

        def test_bills_on_billable_not_seats(self):
            a = prorate_seats(_sub(seats=20, billable_seats=10), _plan(), HALF)
            b = prorate_seats(_sub(seats=3, billable_seats=10), _plan(), HALF)
            self.assertEqual(a[0]["amount_cents"], 5000)
            self.assertEqual(a, b)

        def test_downgrade_returns_empty(self):
            self.assertEqual(prorate_seats(_sub(), _plan(seat_price_cents=500),
                                           HALF), [])

        def test_equal_price_returns_empty(self):
            self.assertEqual(prorate_seats(_sub(), _plan(seat_price_cents=1000),
                                           HALF), [])

        def test_trialing_returns_empty(self):
            self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(),
                                           HALF), [])

        def test_other_statuses_prorate(self):
            self.assertEqual(len(prorate_seats(_sub(status="past_due"),
                                               _plan(), HALF)), 2)

        def test_changed_at_on_or_after_period_end_returns_empty(self):
            self.assertEqual(prorate_seats(_sub(), _plan(), PE), [])
            self.assertEqual(prorate_seats(_sub(), _plan(),
                                           PE + timedelta(hours=1)), [])

        def test_zero_billable_returns_empty(self):
            self.assertEqual(prorate_seats(_sub(billable_seats=0), _plan(),
                                           HALF), [])

        def test_negative_billable_raises(self):
            with self.assertRaises(ValueError):
                prorate_seats(_sub(billable_seats=-1), _plan(), HALF)

        def test_vat_id_reverse_charge(self):
            lines = prorate_seats(_sub(vat_id="DE123456789"), _plan(), HALF)
            self.assertEqual([l["vat_cents"] for l in lines], [0, 0])

        def test_empty_vat_id_still_charges_vat(self):
            lines = prorate_seats(_sub(vat_id=""), _plan(), HALF)
            self.assertEqual(lines[1]["vat_cents"], 2100)

        def test_credit_rounds_up(self):
            lines = prorate_seats(_sub(seat_price_cents=1001, billable_seats=1),
                                  _plan(seat_price_cents=2001), HALF)
            self.assertEqual(lines[0]["amount_cents"], 501)

        def test_charge_rounds_down(self):
            lines = prorate_seats(_sub(seat_price_cents=1001, billable_seats=1),
                                  _plan(seat_price_cents=2001), HALF)
            self.assertEqual(lines[1]["amount_cents"], 1000)
            self.assertEqual(lines[1]["vat_cents"], 210)

        def test_fifty_cent_drop_per_line(self):
            lines = prorate_seats(_sub(seat_price_cents=100, billable_seats=1),
                                  _plan(seat_price_cents=2000), QUARTER)
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0]["kind"], "charge")
            self.assertEqual(lines[0]["amount_cents"], 500)

        def test_minimum_applies_to_pre_vat_amount(self):
            lines = prorate_seats(_sub(seat_price_cents=100, billable_seats=1),
                                  _plan(seat_price_cents=200), QUARTER)
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0]["amount_cents"], 50)
            self.assertEqual(lines[0]["vat_cents"], 10)

        def test_both_lines_dropped_returns_empty(self):
            self.assertEqual(prorate_seats(_sub(seat_price_cents=10,
                                                billable_seats=1),
                                           _plan(seat_price_cents=20), QUARTER),
                             [])

        def test_threshold_exactly_50000_is_standard(self):
            lines = prorate_seats(_sub(seat_price_cents=50000, billable_seats=1),
                                  _plan(seat_price_cents=60000), FULL)
            self.assertEqual(lines[0]["amount_cents"], 50000)
            self.assertEqual(lines[0]["approved_by"], STD)

        def test_threshold_50001_is_large(self):
            lines = prorate_seats(_sub(seat_price_cents=50001, billable_seats=1),
                                  _plan(seat_price_cents=60000), FULL)
            self.assertEqual(lines[0]["amount_cents"], 50001)
            self.assertEqual(lines[0]["approved_by"], LARGE)

        def test_ordering_credit_then_charge(self):
            lines = prorate_seats(_sub(), _plan(), HALF)
            self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])

        def test_description_truncated_to_80(self):
            lines = prorate_seats(_sub(plan_name="A" * 60), _plan(), HALF)
            expected = "Unused " + "A" * 47 + "..." + " seats until 2026-11-01"
            self.assertEqual(lines[0]["description"], expected)
            self.assertEqual(len(lines[0]["description"]), 80)

        def test_truncation_counts_code_points(self):
            lines = prorate_seats(_sub(plan_name="Ñ" * 60), _plan(), HALF)
            self.assertEqual(lines[0]["description"],
                             "Unused " + "Ñ" * 47 + "..."
                             + " seats until 2026-11-01")

        def test_short_name_not_truncated(self):
            lines = prorate_seats(_sub(plan_name="B" * 10), _plan(), HALF)
            self.assertNotIn("...", lines[0]["description"])

        def test_span_longer_than_period_raises(self):
            with self.assertRaises(ValueError):
                prorate_seats(_sub(), _plan(),
                              PE - timedelta(days=14))

        def test_naive_datetimes_raise(self):
            naive = datetime(2026, 10, 1, 12)
            with self.assertRaises(ValueError):
                prorate_seats(_sub(), _plan(), naive)
            with self.assertRaises(ValueError):
                prorate_seats(_sub(period_end=naive), _plan(), HALF)

        def test_missing_key_raises(self):
            sub = _sub()
            del sub["vat_id"]
            with self.assertRaises(ValueError):
                prorate_seats(sub, _plan(), HALF)
            with self.assertRaises(ValueError):
                prorate_seats(_sub(), {"name": "X"}, HALF)

        def test_wrong_types_raise(self):
            with self.assertRaises(ValueError):
                prorate_seats(_sub(seat_price_cents=10.5), _plan(), HALF)
            with self.assertRaises(ValueError):
                prorate_seats(_sub(), _plan(seat_price_cents=2000.0), HALF)
            with self.assertRaises(ValueError):
                prorate_seats(_sub(billable_seats=True), _plan(), HALF)

        def test_legacy_discount_ignored(self):
            with_field = prorate_seats(_sub(legacy_discount=object()),
                                       _plan(), HALF)
            without = prorate_seats(
                {k: v for k, v in _sub().items() if k != "legacy_discount"},
                _plan(), HALF)
            self.assertEqual(with_field, without)

        def test_no_floats_anywhere(self):
            lines = prorate_seats(_sub(seat_price_cents=1001, billable_seats=3),
                                  _plan(seat_price_cents=2001), HALF)
            self.assertFalse(_walk_floats(lines))
            for line in lines:
                self.assertIs(type(line["amount_cents"]), int)
                self.assertIs(type(line["vat_cents"]), int)
                self.assertGreater(line["amount_cents"], 0)

        def test_credit_has_no_vat_and_charge_has_approver_none(self):
            credit, charge = prorate_seats(_sub(), _plan(), HALF)
            self.assertEqual(credit["vat_cents"], 0)
            self.assertIsNone(charge["approved_by"])

    unittest.main()