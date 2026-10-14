"""Seat upgrade proration for Fernhollow Studios.

prorate_seats(subscription, new_plan, changed_at) returns invoice lines: credit first, then charge.
Returns [] when no lines apply (Q5).

Open questions, each isolated in the helper or branch named:
Q1  Currency: the brief has no currency field. _approver_for_credit assumes all amounts are EUR.
Q2  changed_at after period_end, or more than 30 days before it: raises UnusedPeriodError. See _unused_ratio.
Q3  Partial days: the fraction is exact to the microsecond, with no day rounding. See _unused_ratio.
Q4  Description still over 80 code points after shortening: raises DescriptionTooLongError. See _describe.
Q5  Return value when no lines apply: [] is assumed, not None. See prorate_seats.
Q6  Same-price plan change: raises SamePricePlanError. See _check_plan_change.
Q7  Skip threshold on net or gross for charges: net is used. See _keep.
Q8  VAT rounding on charges: floor is assumed. See _charge_vat.
Q9  Description wording "Unused {plan} seats to {date}" needs sign-off. See DESCRIPTION_TEMPLATE.

Judgement calls:
- vat_id is treated as absent when it is None or whitespace-only. Any other non-str value raises TypeError.
- "unused" in the money formula is unused days. Dividing by 30 gives the period fraction, so the money math is price * billable * unused_us / PERIOD_US.
- Time is measured in microseconds so sub-second timestamps do not truncate.
- legacy_discount is never read.
"""

from datetime import datetime, timedelta, timezone
import unittest

PERIOD_DAYS = 30
PERIOD_US = PERIOD_DAYS * 86400 * 1_000_000
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
BIG_CREDIT_CENTS = 50000  # EUR 500; currency assumed EUR (Q1)
FINANCE_CONTROLLER = "Nguyễn Thị Phương Thảo"
BIG_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
MAX_DESCRIPTION_LEN = 80
ELLIPSIS = "\u2026"
DESCRIPTION_TEMPLATE = "Unused {plan} seats to {date}"  # wording needs sign-off (Q9)


class ProrationError(Exception):
    """Base class for proration errors."""


class UnusedPeriodError(ProrationError):
    """changed_at is outside the billing period (Q2)."""


class SamePricePlanError(ProrationError):
    """Plan change with an unchanged seat price (Q6)."""


class DescriptionTooLongError(ProrationError):
    """Description cannot fit in 80 code points even after shortening (Q4)."""


def _require_int(name, value):
    if type(value) is not int:
        raise TypeError(f"{name} must be int, got {type(value).__name__}")
    return value


def _require_aware(name, value):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise TypeError(f"{name} must be a timezone-aware datetime")
    return value


def _has_vat_id(vat_id):
    if vat_id is None:
        return False
    if not isinstance(vat_id, str):
        raise TypeError("vat_id must be str or None")
    return vat_id.strip() != ""


def _unused_ratio(changed_at, period_end):
    """Return (numerator, denominator) for unused time over the 30-day period.

    Q2: outside the period raises UnusedPeriodError.
    Q3: partial days count exactly; no day rounding is applied here.
    """
    unused = period_end - changed_at
    if unused < timedelta(0) or unused > timedelta(days=PERIOD_DAYS):
        raise UnusedPeriodError("changed_at is outside the billing period")
    return unused // timedelta(microseconds=1), PERIOD_US


def _credit_cents(old_price, billable, num, den):
    # Round up: integer ceiling of price * seats * fraction.
    return -(-(old_price * billable * num) // den)


def _charge_cents(new_price, billable, num, den):
    # Round down: integer floor of price * seats * fraction.
    return (new_price * billable * num) // den


def _keep(net_cents):
    """Q7: threshold applied to net. Gross for charges is unconfirmed."""
    return net_cents >= MIN_LINE_CENTS


def _charge_vat(net_cents, vat_id):
    """Q8: floor rounding assumed. Any vat_id means reverse charge (0)."""
    if _has_vat_id(vat_id):
        return 0
    return net_cents * VAT_PERCENT // 100


def _approver_for_credit(amount_cents):
    """Q1: amounts assumed EUR. Credits carry no VAT, so net equals gross."""
    if amount_cents > BIG_CREDIT_CENTS:
        return BIG_CREDIT_APPROVER
    return FINANCE_CONTROLLER


def _describe(plan_name, period_end):
    """Q9: wording needs sign-off. Q4: raises if even the shortest form does not fit."""
    if type(plan_name) is not str:
        raise TypeError("plan name must be str")
    date = period_end.strftime("%Y-%m-%d")
    fixed = DESCRIPTION_TEMPLATE.format(plan="", date=date)
    room = MAX_DESCRIPTION_LEN - len(fixed)
    if len(plan_name) <= room:
        return DESCRIPTION_TEMPLATE.format(plan=plan_name, date=date)
    if room < 1:
        raise DescriptionTooLongError("description cannot fit in 80 code points")
    short = plan_name[: room - 1] + ELLIPSIS
    return DESCRIPTION_TEMPLATE.format(plan=short, date=date)


def _check_plan_change(old_price, new_price):
    """Return True for upgrades, False for downgrades (applied at renewal)."""
    if new_price < old_price:
        return False
    if new_price == old_price:
        # Q6: same-price change is undecided; raise rather than guess.
        raise SamePricePlanError("same-price plan change is undecided")
    return True


def prorate_seats(subscription, new_plan, changed_at):
    sub_price = _require_int("seat_price_cents", subscription["seat_price_cents"])
    billable = _require_int("billable_seats", subscription["billable_seats"])
    _require_int("seats", subscription["seats"])
    new_price = _require_int("new_plan seat_price_cents", new_plan["seat_price_cents"])
    _require_aware("changed_at", changed_at)
    period_end = _require_aware("period_end", subscription["period_end"])

    if subscription["status"] == "trialing":
        return []
    if not _check_plan_change(sub_price, new_price):
        return []

    num, den = _unused_ratio(changed_at, period_end)
    sub_id = subscription["id"]
    lines = []

    credit = _credit_cents(sub_price, billable, num, den)
    if _keep(credit):
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe(subscription["plan_name"], period_end),
            "approved_by": _approver_for_credit(credit),
        })

    charge = _charge_cents(new_price, billable, num, den)
    if _keep(charge):
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": _charge_vat(charge, subscription["vat_id"]),
            "description": _describe(new_plan["name"], period_end),
            "approved_by": None,
        })

    return lines


# ---------------------------------------------------------------- tests

PERIOD_END = datetime(2026, 10, 31, tzinfo=timezone.utc)
TEN_DAYS_LEFT = PERIOD_END - timedelta(days=10)
ONE_DAY_LEFT = PERIOD_END - timedelta(days=1)
FULL_PERIOD_LEFT = PERIOD_END - timedelta(days=30)


def _sub(**overrides):
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Studio",
        "seat_price_cents": 1000,
        "seats": 10,
        "billable_seats": 8,
        "vat_id": None,
        "period_end": PERIOD_END,
    }
    base.update(overrides)
    return base


def _plan(price=1400, name="Studio Plus"):
    return {"name": name, "seat_price_cents": price}


class ProrateSeatsTests(unittest.TestCase):

    def test_trialing_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(), TEN_DAYS_LEFT), [])

    def test_downgrade_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(price=900), TEN_DAYS_LEFT), [])

    def test_uses_billable_seats_not_seats(self):
        self.assertEqual(
            prorate_seats(_sub(seats=100), _plan(), TEN_DAYS_LEFT),
            prorate_seats(_sub(), _plan(), TEN_DAYS_LEFT),
        )

    def test_credit_rounds_up(self):
        lines = prorate_seats(_sub(), _plan(), TEN_DAYS_LEFT)
        # 1000 * 8 * (10/30) = 2666.67 -> 2667
        self.assertEqual(lines[0]["amount_cents"], 2667)

    def test_charge_rounds_down(self):
        lines = prorate_seats(_sub(), _plan(), TEN_DAYS_LEFT)
        # 1400 * 8 * (10/30) = 3733.33 -> 3733
        self.assertEqual(lines[1]["amount_cents"], 3733)

    def test_fifty_cent_skip_drops_charge_keeps_credit(self):
        # credit = ceil(1000/30) = 34 (kept); charge = floor(1001/30) = 33 (dropped)
        lines = prorate_seats(_sub(billable_seats=1), _plan(price=1001), ONE_DAY_LEFT)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "credit")
        self.assertEqual(lines[0]["amount_cents"], 34)

    def test_both_lines_under_fifty_returns_empty(self):
        # credit = ceil(1/30) = 1; charge = floor(2/30) = 0
        lines = prorate_seats(_sub(seat_price_cents=1, billable_seats=1), _plan(price=2), ONE_DAY_LEFT)
        self.assertEqual(lines, [])

    def test_exactly_fifty_is_kept(self):
        # charge = floor(1500/30) = 50
        lines = prorate_seats(_sub(billable_seats=1), _plan(price=1500), ONE_DAY_LEFT)
        charge = [l for l in lines if l["kind"] == "charge"]
        self.assertEqual(charge[0]["amount_cents"], 50)

    def test_reverse_charge_vat_zero(self):
        lines = prorate_seats(_sub(vat_id="DE123456789"), _plan(), TEN_DAYS_LEFT)
        self.assertEqual(lines[1]["vat_cents"], 0)

    def test_charge_vat_is_21_percent_without_vat_id(self):
        lines = prorate_seats(_sub(), _plan(), TEN_DAYS_LEFT)
        # 3733 * 21 / 100 = 783.93 -> 783 (floor, Q8)
        self.assertEqual(lines[1]["vat_cents"], 783)

    def test_whitespace_vat_id_treated_as_absent(self):
        lines = prorate_seats(_sub(vat_id="   "), _plan(), TEN_DAYS_LEFT)
        self.assertEqual(lines[1]["vat_cents"], 783)

    def test_credit_vat_always_zero(self):
        lines = prorate_seats(_sub(), _plan(), TEN_DAYS_LEFT)
        self.assertEqual(lines[0]["vat_cents"], 0)

    def test_approval_at_exactly_50000_is_finance(self):
        lines = prorate_seats(_sub(seat_price_cents=50000, billable_seats=1),
                              _plan(price=60000), FULL_PERIOD_LEFT)
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], FINANCE_CONTROLLER)

    def test_approval_at_50001_is_big_approver(self):
        lines = prorate_seats(_sub(seat_price_cents=50001, billable_seats=1),
                              _plan(price=60000), FULL_PERIOD_LEFT)
        self.assertEqual(lines[0]["amount_cents"], 50001)
        self.assertEqual(lines[0]["approved_by"], BIG_CREDIT_APPROVER)

    def test_charge_approved_by_is_none(self):
        lines = prorate_seats(_sub(), _plan(), TEN_DAYS_LEFT)
        self.assertIsNone(lines[1]["approved_by"])

    def test_credit_before_charge(self):
        lines = prorate_seats(_sub(), _plan(), TEN_DAYS_LEFT)
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])

    def test_descriptions_name_plan_and_date(self):
        lines = prorate_seats(_sub(), _plan(), TEN_DAYS_LEFT)
        self.assertIn("Studio", lines[0]["description"])
        self.assertIn("2026-10-31", lines[0]["description"])
        self.assertIn("Studio Plus", lines[1]["description"])
        self.assertIn("2026-10-31", lines[1]["description"])

    def test_long_plan_name_description_fits_80_code_points(self):
        long_name = "Tiếng Việt Português Plan " * 10
        lines = prorate_seats(_sub(plan_name=long_name), _plan(), TEN_DAYS_LEFT)
        desc = lines[0]["description"]
        self.assertLessEqual(len(desc), 80)
        self.assertIn("2026-10-31", desc)

    def test_legacy_discount_ignored(self):
        plain = prorate_seats(_sub(), _plan(), TEN_DAYS_LEFT)
        with_legacy = prorate_seats(_sub(legacy_discount="garbage"), _plan(), TEN_DAYS_LEFT)
        self.assertEqual(plain, with_legacy)

    def test_no_float_values_in_output(self):
        for line in prorate_seats(_sub(), _plan(), TEN_DAYS_LEFT):
            self.assertIs(type(line["amount_cents"]), int)
            self.assertIs(type(line["vat_cents"]), int)

    def test_naive_changed_at_raises_type_error(self):
        with self.assertRaises(TypeError):
            prorate_seats(_sub(), _plan(), datetime(2026, 10, 21))

    def test_float_seats_raise_type_error(self):
        with self.assertRaises(TypeError):
            prorate_seats(_sub(billable_seats=8.0), _plan(), TEN_DAYS_LEFT)

    def test_changed_at_after_period_end_raises(self):
        # Q2: named exception until answered
        with self.assertRaises(UnusedPeriodError):
            prorate_seats(_sub(), _plan(), PERIOD_END + timedelta(days=1))

    def test_changed_at_before_period_start_raises(self):
        # Q2: named exception until answered
        with self.assertRaises(UnusedPeriodError):
            prorate_seats(_sub(), _plan(), PERIOD_END - timedelta(days=31))

    def test_same_price_raises(self):
        # Q6: undecided, named exception until answered
        with self.assertRaises(SamePricePlanError):
            prorate_seats(_sub(), _plan(price=1000), TEN_DAYS_LEFT)

    @unittest.skip("Q1: currency unknown; EUR threshold assumed")
    def test_currency_threshold(self):
        pass

    @unittest.skip("Q3: partial-day counting undecided")
    def test_partial_day_counting(self):
        pass

    @unittest.skip("Q4: shortened description still over 80 code points, undecided")
    def test_description_unshortenable(self):
        pass

    @unittest.skip("Q5: empty list vs None when no lines apply, undecided")
    def test_no_lines_return_shape(self):
        pass

    @unittest.skip("Q7: skip threshold on net or gross for charges, undecided")
    def test_skip_threshold_gross(self):
        pass

    @unittest.skip("Q8: VAT rounding on charges, floor assumed, undecided")
    def test_vat_rounding(self):
        pass

    @unittest.skip("Q9: description wording needs sign-off")
    def test_description_wording(self):
        pass


if __name__ == "__main__":
    unittest.main()