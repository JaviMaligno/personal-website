"""Seat-upgrade proration for billing (client: Fernhollow Studios / Ingrid).

Requirement IDs R1 to R16 are implemented as specified. The following are proposed defaults, not client-confirmed (UNCONFIRMED):

O1  Currency is EUR (CURRENCY, documentation only). The R13 threshold is 50000 cents.
O2  R13 compares the computed credit amount_cents (credits carry no VAT). Strictly greater than 50000 goes to the large-credit approver. Exactly 50000 goes to the standard approver.
O3  Exact fractional days: remaining = microseconds(period_end - changed_at) / (30 * 86400 * 10**6). No flooring to whole days.
O4  changed_at >= period_end returns []. changed_at before the period start clamps remaining to 1 and logs a WARNING (still prorated).
O5  The R9 50-cent test applies to the final rounded pre-VAT amount_cents of each line. A credit rounding up to exactly 50 is kept.
O6  Charge vat_cents = (amount_cents * 21) // 100. VAT is 0 under reverse charge.
O7  Downgrade means new seat price < old seat price. Equal prices are not a downgrade: both lines are emitted.

Additional assumptions (architect design items, implemented as proposed):
- billable_seats > seats raises ValueError (UNCONFIRMED).
- vat_id: None, empty, or whitespace-only means no VAT id (reverse charge does not apply). Any other non-empty string means reverse charge.
- Ellipsis style is "..." counted inside the 80-character budget. Plan names are stripped. The period end date is never truncated.
- id, status, plan_name, and new_plan name must be non-empty after strip.
- Credit VAT is 0 per R10. This overrides the general house rule that VAT applies to credits too.
- Clamp warnings are emitted via logging.getLogger(__name__) at WARNING level.
- Rounding follows R8 (credits ceil, charges floor). This overrides the house half-up rule.

The unit tests are in this same module and run with: python -m unittest seat_proration (or python seat_proration.py).
"""

import logging
import math
from datetime import datetime, timedelta
from fractions import Fraction

logger = logging.getLogger(__name__)

PERIOD_DAYS = 30
VAT_RATE_PERCENT = 21
MIN_LINE_CENTS = 50
CURRENCY = "EUR"  # documentation only (O1)
APPROVAL_THRESHOLD_CENTS = 50000  # EUR 500.00 (O1, O2)
DESCRIPTION_MAX_LEN = 80
CREDIT_APPROVER = "Win Tee Fung Tao"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"

_PERIOD_US = PERIOD_DAYS * 86400 * 10**6
_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")
_CREDIT_TEMPLATE = "Unused {plan} seats, period ends {date}"
_CHARGE_TEMPLATE = "Prorated {plan} seats, period ends {date}"
_ELLIPSIS = "..."
_MIN_PLAN_BUDGET = len(_ELLIPSIS) + 1


def _require_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an int (cents), got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")


def _require_str(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_aware(name, value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _validate_inputs(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict):
        raise ValueError("subscription must be a dict")
    missing = [k for k in _SUB_KEYS if k not in subscription]
    if missing:
        raise ValueError(f"subscription missing keys: {', '.join(missing)}")
    if not isinstance(new_plan, dict):
        raise ValueError("new_plan must be a dict")
    missing = [k for k in _PLAN_KEYS if k not in new_plan]
    if missing:
        raise ValueError(f"new_plan missing keys: {', '.join(missing)}")

    for key in ("id", "status", "plan_name"):
        _require_str(f"subscription.{key}", subscription[key])
    _require_int("subscription.seat_price_cents", subscription["seat_price_cents"])
    _require_int("subscription.seats", subscription["seats"])
    _require_int("subscription.billable_seats", subscription["billable_seats"])
    if subscription["billable_seats"] > subscription["seats"]:
        raise ValueError("subscription.billable_seats must be <= subscription.seats")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise ValueError("subscription.vat_id must be None or str")
    _require_aware("subscription.period_end", subscription["period_end"])

    _require_str("new_plan.name", new_plan["name"])
    _require_int("new_plan.seat_price_cents", new_plan["seat_price_cents"])
    _require_aware("changed_at", changed_at)


def _remaining_fraction(changed_at, period_end):
    delta_us = (period_end - changed_at) // timedelta(microseconds=1)
    remaining = Fraction(delta_us, _PERIOD_US)
    if remaining > 1:
        logger.warning("changed_at %s is before period start; clamping remaining fraction to 1",
                       changed_at.isoformat())
        remaining = Fraction(1)
    return remaining


def _truncate_plan_name(plan, fixed_len):
    budget = DESCRIPTION_MAX_LEN - fixed_len
    if budget < _MIN_PLAN_BUDGET:
        raise RuntimeError("description template leaves no room for plan name")
    if len(plan) <= budget:
        return plan
    return plan[: budget - len(_ELLIPSIS)].rstrip() + _ELLIPSIS


def _build_description(template, plan, period_end):
    date = period_end.strftime("%Y-%m-%d")
    plan = plan.strip()
    fixed_len = len(template.format(plan="", date=date))
    plan = _truncate_plan_name(plan, fixed_len)
    description = template.format(plan=plan, date=date)
    if len(description) > DESCRIPTION_MAX_LEN or date not in description:
        raise RuntimeError("description invariant violated")
    return description


def _build_credit(subscription, amount_cents, period_end):
    approver = (LARGE_CREDIT_APPROVER if amount_cents > APPROVAL_THRESHOLD_CENTS
                else CREDIT_APPROVER)
    return {
        "subscription_id": subscription["id"],
        "kind": "credit",
        "amount_cents": amount_cents,
        "vat_cents": 0,
        "description": _build_description(_CREDIT_TEMPLATE, subscription["plan_name"], period_end),
        "approved_by": approver,
    }


def _charge_vat_cents(amount_cents, vat_id):
    if vat_id is not None and vat_id.strip():
        return 0
    return (amount_cents * VAT_RATE_PERCENT) // 100


def _build_charge(subscription, new_plan, amount_cents, period_end):
    return {
        "subscription_id": subscription["id"],
        "kind": "charge",
        "amount_cents": amount_cents,
        "vat_cents": _charge_vat_cents(amount_cents, subscription["vat_id"]),
        "description": _build_description(_CHARGE_TEMPLATE, new_plan["name"], period_end),
        "approved_by": None,
    }


def prorate_seats(subscription, new_plan, changed_at):
    _validate_inputs(subscription, new_plan, changed_at)
    if subscription["status"] == "trialing":
        return []

    period_end = subscription["period_end"]
    if changed_at >= period_end:
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    billable = subscription["billable_seats"]
    if billable == 0:
        return []

    remaining = _remaining_fraction(changed_at, period_end)
    credit_cents = math.ceil(Fraction(old_price * billable) * remaining)
    charge_cents = math.floor(Fraction(new_price * billable) * remaining)

    lines = []
    if credit_cents >= MIN_LINE_CENTS:
        lines.append(_build_credit(subscription, credit_cents, period_end))
    if charge_cents >= MIN_LINE_CENTS:
        lines.append(_build_charge(subscription, new_plan, charge_cents, period_end))
    return lines


if __name__ == "__main__":
    import unittest
    from datetime import timezone

    UTC = timezone.utc
    PE = datetime(2026, 11, 1, tzinfo=UTC)
    HALF = PE - timedelta(days=15)
    FULL = PE - timedelta(days=30)

    def _sub(**over):
        sub = {"id": "sub_1", "status": "active", "plan_name": "Studio",
               "seat_price_cents": 1000, "seats": 10, "billable_seats": 10,
               "vat_id": None, "period_end": PE}
        sub.update(over)
        return sub

    def _plan(price=1500, name="Studio Pro"):
        return {"name": name, "seat_price_cents": price}

    class ProrateSeatsTests(unittest.TestCase):

        def test_upgrade_credit_and_charge(self):
            lines = prorate_seats(_sub(), _plan(), HALF)
            self.assertEqual(len(lines), 2)
            credit, charge = lines
            self.assertEqual(credit["kind"], "credit")
            self.assertEqual(credit["amount_cents"], 5000)
            self.assertEqual(credit["vat_cents"], 0)
            self.assertEqual(credit["approved_by"], CREDIT_APPROVER)
            self.assertEqual(credit["description"], "Unused Studio seats, period ends 2026-11-01")
            self.assertEqual(charge["kind"], "charge")
            self.assertEqual(charge["amount_cents"], 7500)
            self.assertEqual(charge["vat_cents"], 1575)
            self.assertIsNone(charge["approved_by"])
            self.assertEqual(charge["description"],
                             "Prorated Studio Pro seats, period ends 2026-11-01")
            for line in lines:
                self.assertEqual(set(line), {"subscription_id", "kind", "amount_cents",
                                             "vat_cents", "description", "approved_by"})

        def test_downgrade_returns_empty(self):
            self.assertEqual(prorate_seats(_sub(), _plan(price=500), HALF), [])

        def test_trialing_returns_empty(self):
            self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(), HALF), [])

        def test_reverse_charge_zero_vat(self):
            lines = prorate_seats(_sub(vat_id="DE123"), _plan(), HALF)
            self.assertEqual(lines[1]["vat_cents"], 0)

        def test_whitespace_vat_id_is_not_reverse_charge(self):
            lines = prorate_seats(_sub(vat_id="   "), _plan(), HALF)
            self.assertEqual(lines[1]["vat_cents"], 1575)

        def test_threshold_exactly_50000_goes_to_standard_approver(self):
            lines = prorate_seats(_sub(seat_price_cents=5000), _plan(price=5000), FULL)
            self.assertEqual(lines[0]["amount_cents"], 50000)
            self.assertEqual(lines[0]["approved_by"], CREDIT_APPROVER)

        def test_threshold_50001_goes_to_large_approver(self):
            lines = prorate_seats(_sub(seat_price_cents=1, seats=50001, billable_seats=50001),
                                  _plan(price=1), FULL)
            self.assertEqual(lines[0]["amount_cents"], 50001)
            self.assertEqual(lines[0]["approved_by"], LARGE_CREDIT_APPROVER)

        def test_credit_ceils_and_small_charge_dropped(self):
            # credit 99/2 = 49.5 -> 50 (kept); charge 99/2 = 49.5 -> 49 (dropped)
            lines = prorate_seats(_sub(seat_price_cents=99, seats=1, billable_seats=1),
                                  _plan(price=99), HALF)
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0]["kind"], "credit")
            self.assertEqual(lines[0]["amount_cents"], 50)

        def test_zero_credit_and_charge_below_50_dropped(self):
            lines = prorate_seats(_sub(seat_price_cents=0, seats=49, billable_seats=49),
                                  _plan(price=1), FULL)
            self.assertEqual(lines, [])

        def test_exact_fraction_not_float(self):
            changed = PE - timedelta(days=15, microseconds=1)
            lines = prorate_seats(_sub(seat_price_cents=1000, seats=1, billable_seats=1),
                                  _plan(price=1000), changed)
            self.assertEqual(lines[0]["amount_cents"], 501)
            self.assertEqual(lines[1]["amount_cents"], 500)
            self.assertEqual(lines[1]["vat_cents"], 105)

        def test_description_exactly_80_chars(self):
            lines = prorate_seats(_sub(plan_name="A" * 43), _plan(name="B" * 41), HALF)
            self.assertEqual(len(lines[0]["description"]), 80)
            self.assertEqual(len(lines[1]["description"]), 80)
            self.assertIn("2026-11-01", lines[0]["description"])
            self.assertIn("2026-11-01", lines[1]["description"])

        def test_long_plan_name_truncated_date_kept(self):
            lines = prorate_seats(_sub(plan_name="X" * 200), _plan(name="Y" * 200), HALF)
            for line in lines:
                self.assertLessEqual(len(line["description"]), 80)
                self.assertIn("2026-11-01", line["description"])
                self.assertIn("...", line["description"])
            self.assertEqual(len(lines[0]["description"]), 80)

        def test_changed_at_equal_period_end_returns_empty(self):
            self.assertEqual(prorate_seats(_sub(), _plan(), PE), [])

        def test_changed_at_after_period_end_returns_empty(self):
            self.assertEqual(prorate_seats(_sub(), _plan(), PE + timedelta(days=1)), [])

        def test_changed_at_before_period_start_clamps_and_warns(self):
            changed = PE - timedelta(days=40)
            with self.assertLogs(level="WARNING"):
                lines = prorate_seats(_sub(seat_price_cents=100, seats=1, billable_seats=1),
                                      _plan(price=200), changed)
            self.assertEqual(lines[0]["amount_cents"], 100)
            self.assertEqual(lines[1]["amount_cents"], 200)

        def test_equal_prices_emit_both_lines(self):
            lines = prorate_seats(_sub(), _plan(price=1000), HALF)
            self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])

        def test_billable_seats_used_not_seats(self):
            lines = prorate_seats(_sub(seats=20, billable_seats=10), _plan(), HALF)
            self.assertEqual(lines[0]["amount_cents"], 5000)
            self.assertEqual(lines[1]["amount_cents"], 7500)

        def test_legacy_discount_ignored(self):
            base = prorate_seats(_sub(), _plan(), HALF)
            for value in ("x", 0.5, None, {"a": 1}, True, -7):
                self.assertEqual(prorate_seats(_sub(legacy_discount=value), _plan(), HALF), base)

        def test_output_types_are_int_and_no_floats(self):
            lines = prorate_seats(_sub(), _plan(), HALF)
            for line in lines:
                self.assertIs(type(line["amount_cents"]), int)
                self.assertIs(type(line["vat_cents"]), int)
                for value in line.values():
                    self.assertNotIsInstance(value, float)

        def test_zero_billable_returns_empty(self):
            self.assertEqual(prorate_seats(_sub(billable_seats=0, seats=5), _plan(), HALF), [])

        def test_missing_key_raises(self):
            sub = _sub()
            del sub["vat_id"]
            with self.assertRaises(ValueError) as cm:
                prorate_seats(sub, _plan(), HALF)
            self.assertIn("vat_id", str(cm.exception))

        def test_float_price_raises(self):
            with self.assertRaises(ValueError) as cm:
                prorate_seats(_sub(seat_price_cents=1000.0), _plan(), HALF)
            self.assertIn("seat_price_cents", str(cm.exception))

        def test_new_plan_float_price_raises(self):
            with self.assertRaises(ValueError) as cm:
                prorate_seats(_sub(), _plan(price=1.5), HALF)
            self.assertIn("new_plan.seat_price_cents", str(cm.exception))

        def test_bool_price_raises(self):
            with self.assertRaises(ValueError) as cm:
                prorate_seats(_sub(seat_price_cents=True), _plan(), HALF)
            self.assertIn("seat_price_cents", str(cm.exception))

        def test_negative_value_raises(self):
            with self.assertRaises(ValueError) as cm:
                prorate_seats(_sub(seats=-1), _plan(), HALF)
            self.assertIn("seats", str(cm.exception))

        def test_naive_datetime_raises(self):
            with self.assertRaises(ValueError) as cm:
                prorate_seats(_sub(), _plan(), datetime(2026, 10, 16))
            self.assertIn("changed_at", str(cm.exception))

        def test_billable_greater_than_seats_raises(self):
            with self.assertRaises(ValueError) as cm:
                prorate_seats(_sub(billable_seats=11), _plan(), HALF)
            self.assertIn("billable_seats", str(cm.exception))

    unittest.main()
```