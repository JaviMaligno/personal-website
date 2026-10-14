# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-sonvo0j1/prorate_seats.py
"""prorate_seats: seat-upgrade proration for Fernhollow Studios.

STATUS: Not saved to disk and not executed. This session had no file or shell
access, so the test results are unknown. Save this module to the path above,
save the tests as test_prorate_seats.py in the same directory, and run
`python3 -I -m unittest` from that directory.

PENDING items, implemented with provisional defaults for client confirmation:
- LARGE_CREDIT_THRESHOLD_CENTS = 50000, currency assumed EUR (param large_threshold_cents)
- threshold_inclusive=False (strictly over the threshold for APPROVER_LARGE)
- EXCLUDED_STATUSES = frozenset({"trialing"}) (param excluded_statuses)
- allow_fractional_days=True (False floors days_left to whole days)
- on_days_over_period="raise" (or "clamp")
- on_nonpositive_days="no_lines" (or "raise")
- vat_rounding=_round_half_up (half-up on exact Fraction, applied to rounded charge_cents)
- minimum_applies_to="net" (only "net" is implemented)
- equal_price_is_downgrade=False
- description_shortener=None (default truncates plan name and appends "...")
- date_timezone="UTC"
- CREDIT_TEMPLATE and CHARGE_TEMPLATE wording
- Invalid input: naive datetimes raise ValueError, non-int prices or seats raise TypeError, empty vat_id counts as absent

Deviations from the design:
- Input validation runs before the trialing check, so a trialing subscription with invalid input still raises.
- Credit lines carry no VAT, as the brief requires. This overrides the house rule that VAT applies to every line.
- The sub-minimum and threshold rules follow the design exactly. APPROVER_LARGE applies only to lines that survive the minimum.
"""

import math
from datetime import datetime
from fractions import Fraction
from zoneinfo import ZoneInfo

PERIOD_DAYS = 13
VAT_RATE = Fraction(21, 100)
MIN_LINE_CENTS = 50
APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
APPROVER_LARGE = "Ramón Etxeberria-Goñi"
LARGE_CREDIT_THRESHOLD_CENTS = 50000
MAX_DESCRIPTION_LEN = 80
EXCLUDED_STATUSES = frozenset({"trialing"})
CREDIT_TEMPLATE = "Credit unused {plan}, period ends {date}"
CHARGE_TEMPLATE = "Prorated {plan}, period ends {date}"
_ELLIPSIS = "..."
_MICROS_PER_DAY = 86_400_000_000


def _round_half_up(x):
    """Round a Fraction to int, halves away from zero."""
    if x >= 0:
        return math.floor(x + Fraction(1, 2))
    return -math.floor(-x + Fraction(1, 2))


def _check_aware(dt, name):
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _check_int(value, name):
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be int, got {type(value).__name__}")
    return value


def _describe(template, plan_name, date_str, shortener):
    if not isinstance(plan_name, str):
        raise TypeError("plan name must be str")
    overhead = len(template.format(plan="", date=date_str))
    if overhead > MAX_DESCRIPTION_LEN:
        raise ValueError("description template too long even without plan name")
    room = MAX_DESCRIPTION_LEN - overhead
    if len(plan_name) <= room:
        plan = plan_name
    elif shortener is not None:
        plan = shortener(plan_name, room)
    else:
        if room < len(_ELLIPSIS) + 1:
            raise ValueError("plan name too long to fit with date and template")
        plan = plan_name[: room - len(_ELLIPSIS)] + _ELLIPSIS
    text = template.format(plan=plan, date=date_str)
    if len(text) > MAX_DESCRIPTION_LEN:
        raise ValueError("description exceeds MAX_DESCRIPTION_LEN after shortening")
    return text


def prorate_seats(
    subscription,
    new_plan,
    changed_at,
    *,
    excluded_statuses=EXCLUDED_STATUSES,
    large_threshold_cents=LARGE_CREDIT_THRESHOLD_CENTS,
    threshold_inclusive=False,
    allow_fractional_days=True,
    on_days_over_period="raise",
    on_nonpositive_days="no_lines",
    vat_rounding=_round_half_up,
    minimum_applies_to="net",
    equal_price_is_downgrade=False,
    description_shortener=None,
    date_timezone="UTC",
):
    """Return credit and charge invoice lines for a seat upgrade.

    description_shortener, if given, is called as f(plan_name, max_len) and must
    return a string no longer than max_len.
    """
    if minimum_applies_to != "net":
        raise ValueError("only minimum_applies_to='net' is implemented")
    if on_days_over_period not in ("raise", "clamp"):
        raise ValueError("on_days_over_period must be 'raise' or 'clamp'")
    if on_nonpositive_days not in ("no_lines", "raise"):
        raise ValueError("on_nonpositive_days must be 'no_lines' or 'raise'")

    sub_id = subscription["id"]
    old_plan_name = subscription["plan_name"]
    old = _check_int(subscription["seat_price_cents"], "seat_price_cents")
    new = _check_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    seats = _check_int(subscription["billable_seats"], "billable_seats")
    vat_id = subscription["vat_id"]
    new_plan_name = new_plan["name"]
    period_end = subscription["period_end"]
    _check_aware(period_end, "period_end")
    _check_aware(changed_at, "changed_at")

    if subscription["status"] in excluded_statuses:
        return []
    if new < old or (new == old and equal_price_is_downgrade):
        return []

    delta = period_end - changed_at
    micros = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
    days_left = Fraction(micros, _MICROS_PER_DAY)
    if not allow_fractional_days:
        days_left = Fraction(math.floor(days_left))

    if days_left <= 0:
        if on_nonpositive_days == "raise":
            raise ValueError("changed_at is at or after period_end")
        return []
    if days_left > PERIOD_DAYS:
        if on_days_over_period == "raise":
            raise ValueError(f"days_left {days_left} exceeds period of {PERIOD_DAYS} days")
        days_left = Fraction(PERIOD_DAYS)

    fraction = days_left / PERIOD_DAYS
    credit_cents = math.ceil(seats * old * fraction)
    charge_cents = math.floor(seats * new * fraction)

    date_str = period_end.astimezone(ZoneInfo(date_timezone)).strftime("%Y-%m-%d")
    lines = []

    if credit_cents >= MIN_LINE_CENTS:
        if threshold_inclusive:
            large = credit_cents >= large_threshold_cents
        else:
            large = credit_cents > large_threshold_cents
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe(CREDIT_TEMPLATE, old_plan_name, date_str, description_shortener),
            "approved_by": APPROVER_LARGE if large else APPROVER_DEFAULT,
        })

    if charge_cents >= MIN_LINE_CENTS:
        vat_cents = 0 if vat_id else vat_rounding(charge_cents * VAT_RATE)
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _describe(CHARGE_TEMPLATE, new_plan_name, date_str, description_shortener),
            "approved_by": None,
        })

    return lines

# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-sonvo0j1/test_prorate_seats.py
"""Unit tests for prorate_seats. Run with: python3 -I -m unittest (from this directory).

Not executed in this session. Results are unknown until run.
"""

import os
import sys
import unicodedata
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prorate_seats as ps  # noqa: E402

UTC = timezone.utc
END = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def sub(**kw):
    d = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Studio",
        "seat_price_cents": 1000,
        "seats": 99,
        "billable_seats": 3,
        "vat_id": None,
        "period_end": END,
    }
    d.update(kw)
    return d


def plan(price, name="Studio Pro"):
    return {"name": name, "seat_price_cents": price}


def at(days, end=END):
    return end - timedelta(days=days)


class ProrateTests(unittest.TestCase):

    def test_trialing_returns_empty(self):
        self.assertEqual(ps.prorate_seats(sub(status="trialing"), plan(100000), at(6.5)), [])

    def test_downgrade_returns_empty(self):
        self.assertEqual(ps.prorate_seats(sub(seat_price_cents=2000), plan(1000), at(6.5)), [])

    def test_equal_price_prorated_by_default(self):
        lines = ps.prorate_seats(sub(billable_seats=1), plan(1000), at(6.5))
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["amount_cents"], 500)
        self.assertEqual(lines[1]["amount_cents"], 500)
        self.assertEqual(lines[1]["vat_cents"], 105)

    def test_equal_price_downgrade_flag_returns_empty(self):
        self.assertEqual(
            ps.prorate_seats(sub(billable_seats=1), plan(1000), at(6.5),
                             equal_price_is_downgrade=True),
            [],
        )

    def test_basic_upgrade_exact_values(self):
        # 3 seats * 1000 * (6.5/13) = 1500 credit; 3 * 2000 * (1/2) = 3000 charge; VAT 630
        lines = ps.prorate_seats(sub(), plan(2000), at(6.5))
        self.assertEqual(lines[0]["amount_cents"], 1500)
        self.assertEqual(lines[1]["amount_cents"], 3000)
        self.assertEqual(lines[1]["vat_cents"], 630)

    def test_uses_billable_seats_not_seats(self):
        lines = ps.prorate_seats(sub(seats=99, billable_seats=3), plan(2000), at(6.5))
        self.assertEqual(lines[0]["amount_cents"], 1500)
        self.assertEqual(lines[1]["amount_cents"], 3000)

    def test_ignores_legacy_discount(self):
        with_field = ps.prorate_seats(sub(legacy_discount=50), plan(2000), at(6.5))
        without = ps.prorate_seats(sub(), plan(2000), at(6.5))
        self.assertEqual(with_field, without)

    def test_credit_rounds_up_charge_rounds_down(self):
        # credit 1000/13 = 76.92 -> 77; charge 2000/13 = 153.85 -> 153; VAT 153*0.21 = 32.13 -> 32
        lines = ps.prorate_seats(sub(billable_seats=1), plan(2000), at(1))
        self.assertEqual(lines[0]["amount_cents"], 77)
        self.assertEqual(lines[1]["amount_cents"], 153)
        self.assertEqual(lines[1]["vat_cents"], 32)

    def test_exact_integer_no_rounding_change(self):
        lines = ps.prorate_seats(sub(billable_seats=1), plan(2000), at(6.5))
        self.assertEqual(lines[0]["amount_cents"], 500)
        self.assertEqual(lines[1]["amount_cents"], 1000)
        self.assertEqual(lines[1]["vat_cents"], 210)

    def test_minimum_credit_dropped_charge_kept(self):
        # credit ceil(100/13) = 8 (dropped); charge floor(2000/13) = 153 (kept)
        lines = ps.prorate_seats(sub(billable_seats=1, seat_price_cents=100), plan(2000), at(1))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 153)

    def test_minimum_charge_dropped_credit_kept(self):
        # equal price 640: credit ceil(640/13) = 50 (kept); charge floor(640/13) = 49 (dropped)
        lines = ps.prorate_seats(sub(billable_seats=1, seat_price_cents=640), plan(640), at(1))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "credit")
        self.assertEqual(lines[0]["amount_cents"], 50)

    def test_both_dropped_returns_empty(self):
        # credit 8, charge 7, both under 50
        self.assertEqual(
            ps.prorate_seats(sub(billable_seats=1, seat_price_cents=100), plan(100), at(1)),
            [],
        )

    def test_minimum_boundary_50_kept(self):
        # 650/13 = 50 exactly for both lines
        lines = ps.prorate_seats(sub(billable_seats=1, seat_price_cents=650), plan(650), at(1))
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["amount_cents"], 50)
        self.assertEqual(lines[1]["amount_cents"], 50)
        self.assertEqual(lines[1]["vat_cents"], 11)  # 10.5 rounds half-up to 11

    def test_minimum_boundary_49_dropped(self):
        # 637/13 = 49 exactly for both lines; both under 50
        self.assertEqual(
            ps.prorate_seats(sub(billable_seats=1, seat_price_cents=637), plan(637), at(1)),
            [],
        )

    def test_vat_on_rounded_charge_credit_zero(self):
        lines = ps.prorate_seats(sub(billable_seats=1), plan(2000), at(1))
        self.assertEqual(lines[0]["vat_cents"], 0)
        self.assertEqual(lines[1]["vat_cents"], 32)

    def test_reverse_charge_with_vat_id(self):
        lines = ps.prorate_seats(sub(billable_seats=1, vat_id="NL123"), plan(2000), at(1))
        self.assertEqual(lines[1]["vat_cents"], 0)

    def test_empty_string_vat_id_treated_as_absent(self):
        lines = ps.prorate_seats(sub(billable_seats=1, vat_id=""), plan(2000), at(1))
        self.assertEqual(lines[1]["vat_cents"], 32)

    def test_approver_default_at_50000(self):
        lines = ps.prorate_seats(sub(billable_seats=1, seat_price_cents=50000), plan(50000), at(13))
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], ps.APPROVER_DEFAULT)

    def test_approver_large_above_50000(self):
        lines = ps.prorate_seats(sub(billable_seats=1, seat_price_cents=50001), plan(50001), at(13))
        self.assertEqual(lines[0]["approved_by"], ps.APPROVER_LARGE)

    def test_approver_large_at_50000_when_inclusive(self):
        lines = ps.prorate_seats(sub(billable_seats=1, seat_price_cents=50000), plan(50000), at(13),
                                 threshold_inclusive=True)
        self.assertEqual(lines[0]["approved_by"], ps.APPROVER_LARGE)

    def test_charge_approved_by_none(self):
        lines = ps.prorate_seats(sub(billable_seats=1), plan(2000), at(6.5))
        self.assertIsNone(lines[1]["approved_by"])

    def test_approver_strings_exact(self):
        self.assertEqual(ps.APPROVER_DEFAULT, "Nguyễn Thị Phương Thảo")
        self.assertEqual(ps.APPROVER_LARGE, "Ramón Etxeberria-Goñi")
        self.assertEqual(unicodedata.normalize("NFC", ps.APPROVER_DEFAULT), ps.APPROVER_DEFAULT)
        self.assertEqual(unicodedata.normalize("NFC", ps.APPROVER_LARGE), ps.APPROVER_LARGE)

    def test_order_credit_then_charge(self):
        lines = ps.prorate_seats(sub(billable_seats=1), plan(2000), at(6.5))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])

    def test_zero_days_returns_empty(self):
        self.assertEqual(ps.prorate_seats(sub(), plan(2000), at(0)), [])

    def test_negative_days_returns_empty(self):
        self.assertEqual(ps.prorate_seats(sub(), plan(2000), at(-1)), [])

    def test_nonpositive_days_raise_when_configured(self):
        with self.assertRaises(ValueError):
            ps.prorate_seats(sub(), plan(2000), at(0), on_nonpositive_days="raise")

    def test_days_over_period_raises_by_default(self):
        with self.assertRaises(ValueError):
            ps.prorate_seats(sub(), plan(2000), at(14))

    def test_days_over_period_clamped(self):
        lines = ps.prorate_seats(sub(billable_seats=1), plan(2000), at(14),
                                 on_days_over_period="clamp")
        self.assertEqual(lines[0]["amount_cents"], 1000)
        self.assertEqual(lines[1]["amount_cents"], 2000)
        self.assertEqual(lines[1]["vat_cents"], 420)

    def test_whole_days_when_fractional_disabled(self):
        # 6.5 days floors to 6: credit 1300*6/13 = 600; charge 2600*6/13 = 1200; VAT 252
        lines = ps.prorate_seats(sub(billable_seats=1, seat_price_cents=1300), plan(2600), at(6.5),
                                 allow_fractional_days=False)
        self.assertEqual(lines[0]["amount_cents"], 600)
        self.assertEqual(lines[1]["amount_cents"], 1200)
        self.assertEqual(lines[1]["vat_cents"], 252)

    def test_fractional_days_default(self):
        lines = ps.prorate_seats(sub(billable_seats=1, seat_price_cents=1300), plan(2600), at(6.5))
        self.assertEqual(lines[0]["amount_cents"], 650)

    def test_description_contains_plan_and_utc_date(self):
        end2 = datetime(2026, 3, 1, 0, 30, tzinfo=timezone(timedelta(hours=2)))
        lines = ps.prorate_seats(sub(billable_seats=1, period_end=end2), plan(2000, "Studio Pro"),
                                 at(1, end2))
        self.assertIn("Studio", lines[0]["description"])
        self.assertIn("2026-02-28", lines[0]["description"])
        self.assertIn("Studio Pro", lines[1]["description"])
        self.assertIn("2026-02-28", lines[1]["description"])
        for line in lines:
            self.assertLessEqual(len(line["description"]), 80)

    def test_long_plan_name_shortened_date_intact(self):
        lines = ps.prorate_seats(sub(billable_seats=1), plan(2000, "A" * 200), at(1))
        desc = lines[1]["description"]
        self.assertLessEqual(len(desc), 80)
        self.assertIn("...", desc)
        self.assertTrue(desc.endswith("period ends 2026-03-01"))

    def test_shortener_result_too_long_raises(self):
        with self.assertRaises(ValueError):
            ps.prorate_seats(sub(billable_seats=1), plan(2000, "A" * 200), at(1),
                             description_shortener=lambda n, m: "x" * 200)

    def test_room_too_small_raises(self):
        template = "x" * 65 + " {plan} {date}"
        with mock.patch.object(ps, "CHARGE_TEMPLATE", template):
            with self.assertRaises(ValueError):
                ps.prorate_seats(sub(billable_seats=1), plan(2000, "A" * 200), at(1))

    def test_naive_changed_at_raises(self):
        with self.assertRaises(ValueError):
            ps.prorate_seats(sub(), plan(2000), datetime(2026, 2, 27, 12))

    def test_naive_period_end_raises(self):
        with self.assertRaises(ValueError):
            ps.prorate_seats(sub(period_end=datetime(2026, 3, 1, 12)), plan(2000), at(6.5))

    def test_float_subscription_price_raises(self):
        with self.assertRaises(TypeError):
            ps.prorate_seats(sub(seat_price_cents=10.0), plan(2000), at(6.5))

    def test_float_new_plan_price_raises(self):
        with self.assertRaises(TypeError):
            ps.prorate_seats(sub(), plan(2000.0), at(6.5))

    def test_bool_seats_raises(self):
        with self.assertRaises(TypeError):
            ps.prorate_seats(sub(billable_seats=True), plan(2000), at(6.5))

    def test_amounts_are_int(self):
        lines = ps.prorate_seats(sub(billable_seats=1), plan(2000), at(1))
        for line in lines:
            self.assertIs(type(line["amount_cents"]), int)
            self.assertIs(type(line["vat_cents"]), int)

    def test_month_independence(self):
        feb = datetime(2026, 2, 28, 12, tzinfo=UTC)
        jul = datetime(2026, 7, 31, 12, tzinfo=UTC)
        a = ps.prorate_seats(sub(), plan(2000), at(6.5, feb))
        b = ps.prorate_seats(sub(period_end=jul), plan(2000), at(6.5, jul))
        self.assertEqual([l["amount_cents"] for l in a], [l["amount_cents"] for l in b])
        self.assertEqual([l["vat_cents"] for l in a], [l["vat_cents"] for l in b])


if __name__ == "__main__":
    unittest.main()