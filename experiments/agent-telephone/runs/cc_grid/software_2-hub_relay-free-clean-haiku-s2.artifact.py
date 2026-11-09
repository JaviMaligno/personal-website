"""Seat-upgrade proration for Fernhollow Studios.

Public entry point: prorate_seats(subscription, new_plan, changed_at).

Decisions and open questions for the client (Ingrid, Fernhollow):
1. Rounding direction: the credit is rounded up (ceiling) and the charge and VAT are rounded down (floor). This overrides the house half-up rule. Confirm whether the rounding instruction is meant from the client's side or ours.
2. Days: whole-day counting (floor) is used for days between changed_at and period_end. Fractional-day counting is an open question.
3. Equal prices return no lines. This is a tech lead decision, not yet confirmed by the client.
4. VAT rounding: charge VAT is floored at 21 percent. Confirm the VAT rounding mode.
5. Credit VAT is always 0 because finance reverses it separately. This overrides the house rule that VAT applies to credits too, as instructed by the tech lead.
6. Only status "trialing" is excluded. Whether "canceled" or "past_due" should also be excluded is open.

Tests in this module were written but not executed in this environment.
"""

from datetime import datetime, timedelta

_MIN_LINE_CENTS = 50
_LARGE_CREDIT_CENTS = 50000
_CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
_LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
_MAX_DESCRIPTION = 80
_VAT_PERCENT = 21
_BILLING_PERIOD_DAYS = 30

_CREDIT_PREFIX = "Credit for unused "
_CHARGE_PREFIX = "Prorated "
_SUFFIX_TEMPLATE = " seats, period ends {}"


def _require_int(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label} must be an integer, got {type(value).__name__}")


def _require_aware(label, value):
    if not isinstance(value, datetime):
        raise ValueError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _format_date(dt):
    # Uses the datetime's own timezone, as specified.
    return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"


def _fit_description(prefix, plan_name, suffix):
    full = prefix + plan_name + suffix
    if len(full) <= _MAX_DESCRIPTION:
        return full
    # Only the plan name is shortened; template text and date are kept intact.
    allowed = _MAX_DESCRIPTION - len(prefix) - len(suffix)
    return prefix + plan_name[:allowed - 3] + "..." + suffix


def prorate_seats(subscription, new_plan, changed_at):
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    billable = subscription["billable_seats"]
    period_end = subscription["period_end"]

    _require_int("seat_price_cents", old_price)
    _require_int("new plan seat_price_cents", new_price)
    _require_int("billable_seats", billable)
    _require_aware("changed_at", changed_at)
    _require_aware("period_end", period_end)

    if subscription["status"] == "trialing":
        return []

    if new_price < old_price:
        # Downgrade: applies at renewal, so no proration lines.
        return []

    if new_price == old_price:
        # Tech lead decision: equal prices produce no lines.
        return []

    if changed_at >= period_end:
        return []

    # Whole days, floored. Decision still to be confirmed with the client.
    days = (period_end - changed_at) // timedelta(days=1)

    # Credit is rounded UP to the next cent (integer ceiling).
    credit_numerator = billable * old_price * days
    credit_amount = -((-credit_numerator) // _BILLING_PERIOD_DAYS)

    # Charge is rounded DOWN to the cent (integer floor).
    charge_numerator = billable * new_price * days
    charge_amount = charge_numerator // _BILLING_PERIOD_DAYS

    date_text = _format_date(period_end)
    suffix = _SUFFIX_TEMPLATE.format(date_text)
    subscription_id = subscription["id"]
    lines = []

    if credit_amount >= _MIN_LINE_CENTS:
        approver = (
            _LARGE_CREDIT_APPROVER
            if credit_amount > _LARGE_CREDIT_CENTS
            else _CREDIT_APPROVER
        )
        lines.append({
            "subscription_id": subscription_id,
            "kind": "credit",
            "amount_cents": credit_amount,
            # Credits never carry VAT; finance reverses it separately.
            "vat_cents": 0,
            "description": _fit_description(
                _CREDIT_PREFIX, subscription["plan_name"], suffix
            ),
            "approved_by": approver,
        })

    if charge_amount >= _MIN_LINE_CENTS:
        # Reverse charge applies when vat_id is set to any non-empty value.
        if subscription["vat_id"]:
            charge_vat = 0
        else:
            charge_vat = charge_amount * _VAT_PERCENT // 100
        lines.append({
            "subscription_id": subscription_id,
            "kind": "charge",
            "amount_cents": charge_amount,
            "vat_cents": charge_vat,
            "description": _fit_description(
                _CHARGE_PREFIX, new_plan["name"], suffix
            ),
            "approved_by": None,
        })

    return lines


# ---------------------------------------------------------------------------
# Tests (standard library unittest). Run with: python3 -I <this file>
# ---------------------------------------------------------------------------

import unittest
from datetime import timezone

_UTC = timezone.utc
_START = datetime(2026, 10, 13, tzinfo=_UTC)
_PERIOD_END = datetime(2026, 11, 12, tzinfo=_UTC)  # exactly 30 days after _START
_PLAN = {"name": "Pro", "seat_price_cents": 2000}


def _sub(**overrides):
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Starter",
        "seat_price_cents": 1000,
        "seats": 10,
        "billable_seats": 10,
        "vat_id": "",
        "period_end": _PERIOD_END,
        "legacy_discount": 99,  # must be ignored entirely
    }
    base.update(overrides)
    return base


class ProratSeatsTests(unittest.TestCase):

    def test_normal_upgrade(self):
        lines = prorate_seats(_sub(), _PLAN, _START)
        self.assertEqual(lines, [
            {
                "subscription_id": "sub_1",
                "kind": "credit",
                "amount_cents": 10000,
                "vat_cents": 0,
                "description": "Credit for unused Starter seats, period ends 2026-11-12",
                "approved_by": "Nguyễn Thị Phương Thảo",
            },
            {
                "subscription_id": "sub_1",
                "kind": "charge",
                "amount_cents": 20000,
                "vat_cents": 4200,
                "description": "Prorated Pro seats, period ends 2026-11-12",
                "approved_by": None,
            },
        ])

    def test_trialing_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _PLAN, _START), [])

    def test_downgrade_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(seat_price_cents=3000), _PLAN, _START), [])

    def test_equal_price_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(seat_price_cents=2000), _PLAN, _START), [])

    def test_reverse_charge_has_zero_charge_vat(self):
        lines = prorate_seats(_sub(vat_id="DE123456789"), _PLAN, _START)
        charge = [l for l in lines if l["kind"] == "charge"][0]
        self.assertEqual(charge["amount_cents"], 20000)
        self.assertEqual(charge["vat_cents"], 0)

    def test_credit_over_500_euro_goes_to_ramon(self):
        lines = prorate_seats(_sub(billable_seats=100), _PLAN, _START)
        credit = lines[0]
        self.assertEqual(credit["kind"], "credit")
        self.assertEqual(credit["amount_cents"], 100000)
        self.assertEqual(credit["approved_by"], "Ramón Etxeberria-Goñi")

    def test_credit_exactly_500_euro_stays_with_default_approver(self):
        lines = prorate_seats(_sub(billable_seats=50), _PLAN, _START)
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], "Nguyễn Thị Phương Thảo")

    def test_line_under_50_cents_is_dropped(self):
        # Credit = 1 * 40 * 30 / 30 = 40 cents, dropped. Charge stays.
        lines = prorate_seats(
            _sub(billable_seats=1, seat_price_cents=40), _PLAN, _START
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 2000)

    def test_both_lines_under_50_cents_returns_empty(self):
        lines = prorate_seats(
            _sub(billable_seats=1, seat_price_cents=0),
            {"name": "Pro", "seat_price_cents": 1},
            _START,
        )
        self.assertEqual(lines, [])

    def test_rounding_up_on_credit_and_down_on_charge(self):
        # 2 whole days remain. Credit = 1000*2/30 = 66.67 -> 67 (up).
        # Charge = 2000*2/30 = 133.33 -> 133 (down). VAT = 133*21//100 = 27.
        start = _PERIOD_END - timedelta(days=2)
        lines = prorate_seats(_sub(billable_seats=1), _PLAN, start)
        self.assertEqual(lines[0]["amount_cents"], 67)
        self.assertEqual(lines[0]["vat_cents"], 0)
        self.assertEqual(lines[1]["amount_cents"], 133)
        self.assertEqual(lines[1]["vat_cents"], 27)

    def test_partial_day_counts_whole_days_floored(self):
        # 29 days 12 hours remain, so days = 29.
        # Credit = 10*1000*29/30 = 9666.67 -> 9667.
        # Charge = 10*2000*29/30 = 19333.33 -> 19333. VAT = 4059.
        start = datetime(2026, 10, 13, 12, tzinfo=_UTC)
        lines = prorate_seats(_sub(), _PLAN, start)
        self.assertEqual(lines[0]["amount_cents"], 9667)
        self.assertEqual(lines[1]["amount_cents"], 19333)
        self.assertEqual(lines[1]["vat_cents"], 4059)

    def test_long_credit_plan_name_is_truncated(self):
        lines = prorate_seats(_sub(plan_name="A" * 60), _PLAN, _START)
        desc = lines[0]["description"]
        self.assertEqual(
            desc,
            "Credit for unused " + "A" * 29 + "..." + " seats, period ends 2026-11-12",
        )
        self.assertEqual(len(desc), 80)

    def test_long_charge_plan_name_is_truncated(self):
        plan = {"name": "B" * 60, "seat_price_cents": 2000}
        lines = prorate_seats(_sub(), plan, _START)
        desc = lines[1]["description"]
        self.assertEqual(
            desc,
            "Prorated " + "B" * 38 + "..." + " seats, period ends 2026-11-12",
        )
        self.assertEqual(len(desc), 80)

    def test_period_already_ended_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(), _PLAN, _PERIOD_END), [])
        after = _PERIOD_END + timedelta(days=1)
        self.assertEqual(prorate_seats(_sub(), _PLAN, after), [])

    def test_date_uses_period_end_own_timezone(self):
        tz = timezone(timedelta(hours=-5))
        end = datetime(2026, 11, 12, 23, 30, tzinfo=tz)  # 2026-11-13 in UTC
        lines = prorate_seats(_sub(period_end=end), _PLAN, _START)
        self.assertTrue(lines[0]["description"].endswith("period ends 2026-11-12"))

    def test_naive_datetime_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _PLAN, datetime(2026, 10, 13))

    def test_non_integer_amount_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(seat_price_cents=10.5), _PLAN, _START)
        with self.assertRaises(ValueError):
            prorate_seats(_sub(billable_seats="10"), _PLAN, _START)


if __name__ == "__main__":
    unittest.main()