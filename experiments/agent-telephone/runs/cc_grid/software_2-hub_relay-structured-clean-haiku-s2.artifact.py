"""Seat proration for Fernhollow Studios.

Public entry point: prorate_seats(subscription, new_plan, changed_at).

[CONFIRM] items implemented as written. Each is isolated in a named constant or function:
- DAYS_PER_PERIOD = 30 (R7).
- All cents are treated as EUR because the input has no currency field (N2).
- Unused days are exact elapsed time divided by 86400 seconds, not truncated (N3).
- changed_at earlier than period_end - 30 days raises ValueError, not clamped (N4).
- Each line is checked against the 50-cent rule independently, so one-sided invoices are returned (N5).
- Charge VAT = floor(charge_cents * 21 / 100) on the rounded-down amount, or 0 when vat_id is set (N6).
- Only status "trialing" suppresses proration. Other statuses are processed normally (N7).
- Downgrade check is new price <= old price returns [] (N8).
- Malformed input (missing keys, wrong types, negative prices or counts) raises ValueError (out-of-scope validation).
- Description templates and the ellipsis character are to be confirmed with Ingrid (N12).

Spec gaps and choices made:
- vat_id counts as set only when it is a non-blank string. Whitespace-only and empty values are treated as unset. Non-string, non-None vat_id raises ValueError.
- Input validation runs before the trialing check, so malformed input raises even for trialing subscriptions.
- The 50-cent and 50000-cent thresholds are compared against the pre-VAT amount.
- R8 and N8 both mean an upgrade (new price strictly greater than old price) is the only case that produces lines.
- legacy_discount is never read.
"""

from datetime import datetime, timedelta, timezone
from fractions import Fraction
import math
import unittest

DAYS_PER_PERIOD = 30  # R7, [CONFIRM]
VAT_RATE_PERCENT = 21  # R11
MIN_LINE_CENTS = 50  # R10, compared before VAT (N2)
SENIOR_APPROVAL_THRESHOLD_CENTS = 50000  # R15, EUR 500.00 (N2)
CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
SENIOR_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
MAX_DESCRIPTION_LENGTH = 80  # R14
ELLIPSIS = "…"  # [CONFIRM] character
TRIAL_STATUS = "trialing"  # R13
MICROSECONDS_PER_DAY = 86_400 * 1_000_000

SUBSCRIPTION_KEYS = (
    "id", "status", "plan_name", "seat_price_cents",
    "seats", "billable_seats", "vat_id", "period_end",
)
NEW_PLAN_KEYS = ("name", "seat_price_cents")


def _check_non_negative_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer, got {value!r}")


def _check_aware(value, label):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")


def _validate(subscription, new_plan, changed_at):
    for key in SUBSCRIPTION_KEYS:
        if key not in subscription:
            raise ValueError(f"subscription is missing key {key!r}")
    for key in NEW_PLAN_KEYS:
        if key not in new_plan:
            raise ValueError(f"new_plan is missing key {key!r}")
    _check_non_negative_int(subscription["seat_price_cents"], "subscription seat_price_cents")
    _check_non_negative_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    _check_non_negative_int(subscription["seats"], "subscription seats")
    _check_non_negative_int(subscription["billable_seats"], "subscription billable_seats")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise ValueError("subscription vat_id must be a string or None")
    _check_aware(subscription["period_end"], "subscription period_end")
    _check_aware(changed_at, "changed_at")


def _is_vat_exempt(vat_id):
    # Reverse charge applies only when vat_id is a non-blank string.
    return vat_id is not None and vat_id.strip() != ""


def _unused_days(period_end, changed_at):
    # Exact elapsed time as a fraction of a day, no truncation (N3).
    micros = (period_end - changed_at) // timedelta(microseconds=1)
    return Fraction(micros, MICROSECONDS_PER_DAY)


def _describe(prefix, name, suffix):
    full = f"{prefix}{name}{suffix}"
    if len(full) <= MAX_DESCRIPTION_LENGTH:
        return full
    room = MAX_DESCRIPTION_LENGTH - len(prefix) - len(suffix) - len(ELLIPSIS)
    return f"{prefix}{name[:max(room, 0)]}{ELLIPSIS}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    _validate(subscription, new_plan, changed_at)

    period_end = subscription["period_end"]
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]

    # N9 evaluation order.
    if subscription["status"] == TRIAL_STATUS:
        return []
    if new_price <= old_price:
        return []
    unused = _unused_days(period_end, changed_at)
    if unused <= 0:
        return []
    if changed_at < period_end - timedelta(days=DAYS_PER_PERIOD):
        raise ValueError("changed_at is earlier than the start of the billing period")

    seats = subscription["billable_seats"]  # R5
    credit_cents = math.ceil(Fraction(old_price * seats) * unused / DAYS_PER_PERIOD)  # R9
    charge_cents = math.floor(Fraction(new_price * seats) * unused / DAYS_PER_PERIOD)  # R9

    date_text = period_end.date().isoformat()  # R4, in the supplied timezone
    lines = []

    if credit_cents >= MIN_LINE_CENTS:
        approver = (
            SENIOR_CREDIT_APPROVER
            if credit_cents > SENIOR_APPROVAL_THRESHOLD_CENTS
            else CREDIT_APPROVER
        )
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,  # R12
            "description": _describe(
                "Credit: unused ", subscription["plan_name"],
                f" seats to {date_text}",
            ),
            "approved_by": approver,
        })

    if charge_cents >= MIN_LINE_CENTS:
        if _is_vat_exempt(subscription["vat_id"]):
            vat_cents = 0
        else:
            vat_cents = charge_cents * VAT_RATE_PERCENT // 100  # floor, N6
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _describe(
                "Charge: new ", new_plan["name"],
                f" seats to {date_text}",
            ),
            "approved_by": None,
        })

    return lines


UTC = timezone.utc
PERIOD_END = datetime(2026, 3, 31, 12, 0, tzinfo=UTC)


def _sub(**overrides):
    base = {
        "id": "sub_1", "status": "active", "plan_name": "Pro",
        "seat_price_cents": 1000, "seats": 5, "billable_seats": 1,
        "vat_id": None, "period_end": PERIOD_END,
    }
    base.update(overrides)
    return base


def _plan(price_cents, name="Business"):
    return {"name": name, "seat_price_cents": price_cents}


def _ago(days):
    return PERIOD_END - timedelta(days=days)


class ProrateSeatsTests(unittest.TestCase):
    def test_credit_rounds_up_and_charge_rounds_down(self):
        lines = prorate_seats(_sub(seat_price_cents=1000), _plan(1600), _ago(10))
        self.assertEqual(lines[0]["amount_cents"], 334)  # 333.33 -> 334
        self.assertEqual(lines[1]["amount_cents"], 533)  # 533.33 -> 533

    def test_credit_below_50_is_skipped(self):
        lines = prorate_seats(_sub(seat_price_cents=147), _plan(300), _ago(10))
        self.assertEqual([l["kind"] for l in lines], ["charge"])

    def test_credit_of_exactly_50_is_kept(self):
        lines = prorate_seats(_sub(seat_price_cents=150), _plan(300), _ago(10))
        self.assertEqual(lines[0]["kind"], "credit")
        self.assertEqual(lines[0]["amount_cents"], 50)

    def test_charge_below_50_is_skipped(self):
        lines = prorate_seats(_sub(seat_price_cents=100), _plan(147), _ago(10))
        self.assertEqual([l["kind"] for l in lines], ["credit"])

    def test_charge_of_exactly_50_is_kept(self):
        lines = prorate_seats(_sub(seat_price_cents=100), _plan(150), _ago(10))
        self.assertEqual(lines[1]["kind"], "charge")
        self.assertEqual(lines[1]["amount_cents"], 50)

    def test_vat_21_percent_on_charge(self):
        lines = prorate_seats(_sub(seat_price_cents=1000), _plan(1600), _ago(10))
        self.assertEqual(lines[1]["vat_cents"], 111)  # floor(533 * 21 / 100)

    def test_reverse_charge_when_vat_id_set(self):
        lines = prorate_seats(_sub(seat_price_cents=1000, vat_id="DE123"), _plan(1600), _ago(10))
        self.assertEqual(lines[1]["vat_cents"], 0)

    def test_empty_vat_id_still_charges_vat(self):
        lines = prorate_seats(_sub(seat_price_cents=1000, vat_id=""), _plan(1600), _ago(10))
        self.assertEqual(lines[1]["vat_cents"], 111)

    def test_credit_has_no_vat(self):
        lines = prorate_seats(_sub(seat_price_cents=1000), _plan(1600), _ago(10))
        self.assertEqual(lines[0]["vat_cents"], 0)

    def test_approval_boundary_at_50000_and_50001(self):
        lines = prorate_seats(_sub(seat_price_cents=50000), _plan(50100), _ago(30))
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], "Nguyễn Thị Phương Thảo")
        lines = prorate_seats(_sub(seat_price_cents=50001), _plan(50100), _ago(30))
        self.assertEqual(lines[0]["amount_cents"], 50001)
        self.assertEqual(lines[0]["approved_by"], "Ramón Etxeberria-Goñi")

    def test_charge_approved_by_is_none(self):
        lines = prorate_seats(_sub(seat_price_cents=1000), _plan(1600), _ago(10))
        self.assertIsNone(lines[1]["approved_by"])

    def test_downgrade_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(seat_price_cents=1000), _plan(500), _ago(10)), [])

    def test_equal_price_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(seat_price_cents=1000), _plan(1000), _ago(10)), [])

    def test_trialing_returns_empty(self):
        sub = _sub(status="trialing", seat_price_cents=1000)
        self.assertEqual(prorate_seats(sub, _plan(1600), _ago(10)), [])

    def test_line_order_credit_then_charge(self):
        lines = prorate_seats(_sub(seat_price_cents=1000), _plan(1600), _ago(10))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])

    def test_description_names_plan_and_date(self):
        lines = prorate_seats(_sub(seat_price_cents=1000), _plan(1600), _ago(10))
        self.assertEqual(lines[0]["description"], "Credit: unused Pro seats to 2026-03-31")
        self.assertEqual(lines[1]["description"], "Charge: new Business seats to 2026-03-31")

    def test_long_description_truncated_keeps_date(self):
        lines = prorate_seats(_sub(plan_name="X" * 200, seat_price_cents=1000), _plan(1600), _ago(10))
        desc = lines[0]["description"]
        self.assertLessEqual(len(desc), 80)
        self.assertIn(ELLIPSIS, desc)
        self.assertTrue(desc.endswith(" seats to 2026-03-31"))

    def test_leap_year_period_uses_30_day_rule(self):
        period_end = datetime(2024, 3, 1, 12, 0, tzinfo=UTC)
        sub = _sub(period_end=period_end, seat_price_cents=1000)
        lines = prorate_seats(sub, _plan(2000), period_end - timedelta(days=15))
        self.assertEqual(lines[0]["amount_cents"], 500)
        self.assertEqual(lines[1]["amount_cents"], 1000)

    def test_non_leap_year_period_uses_30_day_rule(self):
        period_end = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
        sub = _sub(period_end=period_end, seat_price_cents=1000)
        lines = prorate_seats(sub, _plan(2000), period_end - timedelta(days=15))
        self.assertEqual(lines[0]["amount_cents"], 500)
        self.assertEqual(lines[1]["amount_cents"], 1000)

    def test_changed_at_before_period_start_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(seat_price_cents=1000), _plan(1600), _ago(31))

    def test_naive_changed_at_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(1600), datetime(2026, 3, 20, 12, 0))

    def test_naive_period_end_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(period_end=datetime(2026, 3, 31, 12, 0)), _plan(1600), _ago(10))

    def test_missing_key_rejected(self):
        sub = _sub()
        del sub["vat_id"]
        with self.assertRaises(ValueError):
            prorate_seats(sub, _plan(1600), _ago(10))


if __name__ == "__main__":
    unittest.main()