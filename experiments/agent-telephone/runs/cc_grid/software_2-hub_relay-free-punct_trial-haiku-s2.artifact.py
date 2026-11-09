# Fernhollow Studios seat-upgrade proration.
#
# Assumptions and open points for review:
# - All amounts are assumed to be EUR. There is no currency field.
# - Charge VAT is floor(amount * 21 / 100), following the client's round-down rule.
#   The PM's draft specified round-up. Confirm with finance.
# - Same price (new == old) returns [], the same as a downgrade.
# - The description truncation marker is "..." after the shortened plan name.
#   If there is no room for the marker after the date, ValueError is raised.
# - changed_at at or after period_end returns [] (no lines).
# - legacy_discount and seats are never read.
# - The tests at the bottom were written but have NOT been executed in this environment.

import unittest
from datetime import datetime, timedelta, timezone

_PERIOD_US = 30 * 86400 * 10**6
_MIN_LINE_CENTS = 50
_VAT_PERCENT = 21
_HIGH_APPROVER = "Ramón Etxeberria-Goñi"
_LOW_APPROVER = "Nguyễn Thị Phương Thảo"
_HIGH_THRESHOLD_CENTS = 50000
_MAX_DESC = 80
_CREDIT_PREFIX = "Credit: unused "
_CHARGE_PREFIX = "Charge: unused "
_TAIL = " until "
_ELLIPSIS = "..."


def _cents(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer number of cents")
    if value < 0:
        raise ValueError(f"{label} must not be negative")
    return value


def _aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value


def _date_text(dt):
    return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"


def _description(prefix, plan_name, period_end):
    if not isinstance(plan_name, str):
        raise TypeError("plan name must be a string")
    tail = _TAIL + _date_text(period_end)
    fixed = len(prefix) + len(tail)
    if fixed > _MAX_DESC:
        raise ValueError("period end date does not fit in description")
    full = prefix + plan_name + tail
    if len(full) <= _MAX_DESC:
        return full
    room = _MAX_DESC - fixed - len(_ELLIPSIS)
    if room < 0:
        raise ValueError("no room for truncated plan name and marker")
    return prefix + plan_name[:room] + _ELLIPSIS + tail


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise TypeError("subscription and new_plan must be dicts")
    _aware(changed_at, "changed_at")
    period_end = _aware(subscription["period_end"], "period_end")
    p_old = _cents(subscription["seat_price_cents"], "seat_price_cents")
    p_new = _cents(new_plan["seat_price_cents"], "new plan seat_price_cents")
    billable = _cents(subscription["billable_seats"], "billable_seats")
    vat_id = subscription.get("vat_id")
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be a string or None")

    if subscription["status"] == "trialing":
        return []
    if p_new <= p_old:
        return []
    if changed_at >= period_end:
        return []
    if billable == 0:
        return []

    remaining = period_end - changed_at
    r_us = (remaining.days * 86400 + remaining.seconds) * 10**6 + remaining.microseconds
    if r_us == 0:
        return []
    if r_us > _PERIOD_US:
        raise ValueError("remaining time exceeds one 30-day billing period")

    credit_cents = -((-(billable * p_old * r_us)) // _PERIOD_US)
    charge_cents = (billable * p_new * r_us) // _PERIOD_US

    lines = []
    if credit_cents >= _MIN_LINE_CENTS:
        approver = _HIGH_APPROVER if credit_cents > _HIGH_THRESHOLD_CENTS else _LOW_APPROVER
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _description(_CREDIT_PREFIX, subscription["plan_name"], period_end),
            "approved_by": approver,
        })
    if charge_cents >= _MIN_LINE_CENTS:
        if vat_id is None or vat_id.strip() == "":
            vat = charge_cents * _VAT_PERCENT // 100
        else:
            vat = 0
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat,
            "description": _description(_CHARGE_PREFIX, new_plan["name"], period_end),
            "approved_by": None,
        })
    return lines


class _ProrateTests(unittest.TestCase):
    PE = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)

    def sub(self, **overrides):
        s = {
            "id": "sub_1",
            "status": "active",
            "plan_name": "Studio",
            "seat_price_cents": 1000,
            "seats": 99,
            "billable_seats": 10,
            "vat_id": None,
            "period_end": self.PE,
        }
        s.update(overrides)
        return s

    def plan(self, price=1500, name="Studio Pro"):
        return {"name": name, "seat_price_cents": price}

    def at(self, days):
        return self.PE - timedelta(days=days)

    def test_example_1_worked_numbers(self):
        lines = prorate_seats(self.sub(), self.plan(), self.at(15))
        self.assertEqual(len(lines), 2)
        credit, charge = lines
        self.assertEqual(credit["kind"], "credit")
        self.assertEqual(credit["amount_cents"], 5000)
        self.assertEqual(credit["vat_cents"], 0)
        self.assertEqual(credit["approved_by"], _LOW_APPROVER)
        self.assertEqual(charge["kind"], "charge")
        self.assertEqual(charge["amount_cents"], 7500)
        self.assertEqual(charge["vat_cents"], 1575)
        self.assertIsNone(charge["approved_by"])

    def test_example_2_credit_dropped_charge_kept(self):
        lines = prorate_seats(self.sub(billable_seats=1), self.plan(1600), self.at(1))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 53)
        self.assertEqual(lines[0]["vat_cents"], 11)

    def test_example_3_reverse_charge_vat_zero(self):
        lines = prorate_seats(self.sub(vat_id="DE123456789"), self.plan(), self.at(15))
        charge = lines[1]
        self.assertEqual(charge["amount_cents"], 7500)
        self.assertEqual(charge["vat_cents"], 0)

    def test_blank_vat_id_still_charges_vat(self):
        lines = prorate_seats(self.sub(vat_id="   "), self.plan(), self.at(15))
        self.assertEqual(lines[1]["vat_cents"], 1575)

    def test_example_4_trialing_returns_empty(self):
        self.assertEqual(prorate_seats(self.sub(status="trialing"), self.plan(), self.at(15)), [])

    def test_example_5_approval_threshold(self):
        high = prorate_seats(self.sub(seat_price_cents=50001, billable_seats=1),
                             self.plan(50002), self.at(30))
        self.assertEqual(high[0]["amount_cents"], 50001)
        self.assertEqual(high[0]["approved_by"], _HIGH_APPROVER)

        exact = prorate_seats(self.sub(seat_price_cents=50000, billable_seats=1),
                              self.plan(50001), self.at(30))
        self.assertEqual(exact[0]["amount_cents"], 50000)
        self.assertEqual(exact[0]["approved_by"], _LOW_APPROVER)

    def test_example_6_zero_seats_or_zero_remaining(self):
        self.assertEqual(prorate_seats(self.sub(billable_seats=0), self.plan(), self.at(15)), [])
        self.assertEqual(prorate_seats(self.sub(), self.plan(), self.at(0)), [])

    def test_example_7_long_plan_name_truncated(self):
        name = "X" * 200
        lines = prorate_seats(self.sub(), self.plan(name=name), self.at(15))
        desc = lines[1]["description"]
        self.assertEqual(len(desc), 80)
        self.assertEqual(desc, _CHARGE_PREFIX + "X" * 45 + "..." + " until 2026-11-01")

    def test_credit_always_before_charge(self):
        lines = prorate_seats(self.sub(), self.plan(), self.at(15))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])

    def test_naive_datetime_raises(self):
        naive = datetime(2026, 10, 17, 12, 0)
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), self.plan(), naive)

    def test_float_cents_rejected(self):
        with self.assertRaises(TypeError):
            prorate_seats(self.sub(seat_price_cents=1000.0), self.plan(), self.at(15))

    def test_remaining_over_one_period_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), self.plan(), self.at(31))

    def test_changed_after_period_end_returns_empty(self):
        self.assertEqual(prorate_seats(self.sub(), self.plan(), self.PE + timedelta(days=1)), [])


if __name__ == "__main__":
    unittest.main()