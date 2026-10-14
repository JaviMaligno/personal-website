# File: fernhollow_billing.py
"""Seat proration for Fernhollow Studios billing. All amounts are EUR cents.

Default decisions, each isolated in one place so they are easy to change:
- R23 (default): only "trialing" is skipped. Other statuses are prorated.
  See TRIAL_STATUS and prorate_seats.
- R22 (default): an equal price returns []. See _is_upgrade.
- R25 (default): unused days above 30 raise ValueError. See prorate_seats.
- R24 (default): charge VAT is floor(amount * 21 / 100). See _vat_cents.
- R13 (default): reverse charge applies when vat_id is a non-empty string after strip.
  None or "" means VAT applies. See _is_reverse_charge.
- R16 (default): if the plan name must be shortened and there is no room for "...",
  ValueError is raised. See _describe.
"""

import math
from datetime import datetime, timedelta, timezone
from fractions import Fraction

BILLING_PERIOD_DAYS = 30
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
LARGE_CREDIT_CENTS = 50000
TRIAL_STATUS = "trialing"
APPROVER_LARGE_CREDIT = "Ramón Etxeberria-Goñi"
APPROVER_DEFAULT = "Win Tee Fung Tao"
MAX_DESCRIPTION_LEN = 80
ELLIPSIS = "..."
CREDIT_TEMPLATE = "Credit unused seats on {name}, period ends {date}"
CHARGE_TEMPLATE = "Upgrade seats to {name}, period ends {date}"
_MICROS_PER_DAY = 86_400_000_000

_SUBSCRIPTION_KEYS = (
    "id", "status", "plan_name", "seat_price_cents", "seats",
    "billable_seats", "vat_id", "period_end",
)
_PLAN_KEYS = ("name", "seat_price_cents")


def _require_dict(value, keys, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a dict")
    missing = [k for k in keys if k not in value]
    if missing:
        raise ValueError(f"{label} missing keys: {', '.join(missing)}")


def _require_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative int")
    return value


def _require_aware(value, label):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")
    return value


def _unused_days(changed_at, period_end):
    """Exact fractional days from changed_at to period_end (R9).

    Both instants are converted to UTC first so that same-tzinfo wall-clock
    subtraction (which ignores DST shifts) cannot distort the result.
    """
    delta = period_end.astimezone(timezone.utc) - changed_at.astimezone(timezone.utc)
    micros = delta // timedelta(microseconds=1)
    return Fraction(micros, _MICROS_PER_DAY)


def _is_upgrade(old_cents, new_cents):
    """Equal or lower price is not an upgrade (R10, R22)."""
    return new_cents > old_cents


def _is_reverse_charge(vat_id):
    """A non-empty vat_id means reverse charge (R13). None or "" means VAT applies."""
    return vat_id is not None and str(vat_id).strip() != ""


def _vat_cents(amount_cents, vat_id):
    """Charge VAT, floored to the cent (R24). Reverse charge gives 0 (R13)."""
    if _is_reverse_charge(vat_id):
        return 0
    return amount_cents * VAT_PERCENT // 100


def _describe(template, name, date_text):
    """Fit the description into 80 characters by shortening the plan name (R16).

    The date is never truncated. If even the name-less text cannot leave room
    for the ellipsis, ValueError is raised.
    """
    name = str(name)
    full = template.format(name=name, date=date_text)
    if len(full) <= MAX_DESCRIPTION_LEN:
        return full
    base_len = len(template.format(name="", date=date_text))
    if base_len + len(ELLIPSIS) > MAX_DESCRIPTION_LEN:
        raise ValueError("description cannot fit the period end date")
    keep = MAX_DESCRIPTION_LEN - base_len - len(ELLIPSIS)
    return template.format(name=name[:keep] + ELLIPSIS, date=date_text)


def prorate_seats(subscription, new_plan, changed_at):
    _require_dict(subscription, _SUBSCRIPTION_KEYS, "subscription")
    _require_dict(new_plan, _PLAN_KEYS, "new_plan")
    old_price = _require_int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _require_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    billable = _require_int(subscription["billable_seats"], "billable_seats")
    period_end = _require_aware(subscription["period_end"], "period_end")
    changed_at = _require_aware(changed_at, "changed_at")

    if subscription["status"] == TRIAL_STATUS:
        return []
    if changed_at > period_end:
        raise ValueError("changed_at is after period_end")

    days = _unused_days(changed_at, period_end)
    if days > BILLING_PERIOD_DAYS:
        raise ValueError("unused days exceed the 30-day billing period")
    if days == 0 or not _is_upgrade(old_price, new_price):
        return []

    date_text = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    credit_cents = math.ceil(Fraction(old_price * billable) * days / BILLING_PERIOD_DAYS)
    if credit_cents >= MIN_LINE_CENTS:
        approver = (APPROVER_LARGE_CREDIT if credit_cents > LARGE_CREDIT_CENTS
                    else APPROVER_DEFAULT)
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe(CREDIT_TEMPLATE, subscription["plan_name"], date_text),
            "approved_by": approver,
        })

    charge_cents = math.floor(Fraction(new_price * billable) * days / BILLING_PERIOD_DAYS)
    if charge_cents >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": _vat_cents(charge_cents, subscription["vat_id"]),
            "description": _describe(CHARGE_TEMPLATE, new_plan["name"], date_text),
            "approved_by": None,
        })

    return lines


# File: test_fernhollow_billing.py
# Save this file next to fernhollow_billing.py in a new, empty directory
# that is separate from the repository root.
# Run: python3 -I -m unittest -v test_fernhollow_billing
# Test results: not executed in this session.

import unittest
from datetime import datetime, timedelta, timezone

import fernhollow_billing as fb

UTC = timezone.utc
PERIOD_END = datetime(2026, 11, 1, 0, 0, tzinfo=UTC)
WIN = "Win Tee Fung Tao"
RAMON = "Ramón Etxeberria-Goñi"


def sub(**overrides):
    d = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 10, "billable_seats": 10,
         "vat_id": None, "period_end": PERIOD_END}
    d.update(overrides)
    return d


def plan(**overrides):
    d = {"name": "Pro", "seat_price_cents": 1500}
    d.update(overrides)
    return d


def ago(**kwargs):
    return PERIOD_END - timedelta(**kwargs)


class TestProrateSeats(unittest.TestCase):

    def test_ac1_basic_upgrade(self):
        lines = fb.prorate_seats(sub(), plan(), ago(days=15))
        self.assertEqual(lines, [
            {"subscription_id": "sub_1", "kind": "credit", "amount_cents": 5000,
             "vat_cents": 0,
             "description": "Credit unused seats on Basic, period ends 2026-11-01",
             "approved_by": WIN},
            {"subscription_id": "sub_1", "kind": "charge", "amount_cents": 7500,
             "vat_cents": 1575,
             "description": "Upgrade seats to Pro, period ends 2026-11-01",
             "approved_by": None},
        ])

    def test_ac2_seats_ignored_billable_used(self):
        a = fb.prorate_seats(sub(), plan(), ago(days=15))
        b = fb.prorate_seats(sub(seats=12, billable_seats=10), plan(), ago(days=15))
        self.assertEqual(a, b)

    def test_ac3_trialing_returns_empty(self):
        self.assertEqual(fb.prorate_seats(sub(status="trialing"), plan(), ago(days=15)), [])

    def test_ac4_downgrade_returns_empty(self):
        self.assertEqual(fb.prorate_seats(sub(), plan(seat_price_cents=900), ago(days=15)), [])

    def test_equal_price_returns_empty(self):
        self.assertEqual(fb.prorate_seats(sub(), plan(seat_price_cents=1000), ago(days=15)), [])

    def test_ac5_credit_ceiling_49_5_kept_as_50(self):
        # credit 99 * 15 / 30 = 49.5 -> 50 (kept); charge 100 * 15 / 30 = 50 (kept)
        lines = fb.prorate_seats(sub(seat_price_cents=99), plan(seat_price_cents=100), ago(days=15))
        self.assertEqual([l["amount_cents"] for l in lines], [50, 50])
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])

    def test_ac5_credit_49_skipped(self):
        # credit 98 * 15 / 30 = 49 -> skipped; charge 50 kept
        lines = fb.prorate_seats(sub(seat_price_cents=98), plan(seat_price_cents=100), ago(days=15))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 50)

    def test_ac5_charge_49_9_skipped(self):
        # charge 1497 / 30 = 49.9 -> floor 49 -> skipped; credit 0 skipped
        self.assertEqual(
            fb.prorate_seats(sub(seat_price_cents=0), plan(seat_price_cents=1497), ago(days=1)),
            [])

    def test_ac5_charge_exactly_50_kept(self):
        lines = fb.prorate_seats(sub(seat_price_cents=0), plan(seat_price_cents=1500), ago(days=1))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["amount_cents"], 50)
        self.assertEqual(lines[0]["vat_cents"], 10)

    def test_ac6_descriptions_fit_80_and_contain_date(self):
        lines = fb.prorate_seats(
            sub(plan_name="A" * 200), plan(name="B" * 200), ago(days=15))
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertLessEqual(len(line["description"]), 80)
            self.assertIn("2026-11-01", line["description"])
            self.assertIn("...", line["description"])
        self.assertTrue(lines[0]["description"].startswith("Credit unused seats on AAA"))
        self.assertTrue(lines[1]["description"].startswith("Upgrade seats to BBB"))

    def test_ac7_credit_exactly_50000_win_tee(self):
        lines = fb.prorate_seats(sub(seat_price_cents=50000, billable_seats=1),
                                 plan(seat_price_cents=60000), ago(days=30))
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], WIN)

    def test_ac7_credit_50001_ramon(self):
        lines = fb.prorate_seats(sub(seat_price_cents=50001, billable_seats=1),
                                 plan(seat_price_cents=60000), ago(days=30))
        self.assertEqual(lines[0]["amount_cents"], 50001)
        self.assertEqual(lines[0]["approved_by"], RAMON)

    def test_ac8_reverse_charge_gives_zero_vat(self):
        lines = fb.prorate_seats(sub(vat_id="GB123456789"), plan(), ago(days=15))
        self.assertTrue(all(l["vat_cents"] == 0 for l in lines))

    def test_empty_vat_id_means_vat_applies(self):
        lines = fb.prorate_seats(sub(vat_id=""), plan(), ago(days=15))
        self.assertEqual(lines[1]["vat_cents"], 1575)

    def test_ac9_legacy_discount_ignored(self):
        a = fb.prorate_seats(sub(), plan(), ago(days=15))
        b = fb.prorate_seats(sub(legacy_discount=15), plan(), ago(days=15))
        self.assertEqual(a, b)

    def test_ac10_naive_changed_at_raises(self):
        with self.assertRaises(ValueError):
            fb.prorate_seats(sub(), plan(), datetime(2026, 10, 17, 12))

    def test_ac10_naive_period_end_raises(self):
        with self.assertRaises(ValueError):
            fb.prorate_seats(sub(period_end=datetime(2026, 11, 1)), plan(), ago(days=15))

    def test_ac10_changed_at_after_period_end_raises(self):
        with self.assertRaises(ValueError):
            fb.prorate_seats(sub(), plan(), PERIOD_END + timedelta(seconds=1))

    def test_ac11_all_amounts_are_int(self):
        lines = fb.prorate_seats(sub(), plan(), PERIOD_END - timedelta(hours=12))
        self.assertTrue(lines)
        for line in lines:
            self.assertIs(type(line["amount_cents"]), int)
            self.assertIs(type(line["vat_cents"]), int)

    def test_fractional_days_exact(self):
        # credit 1000*10*(1/2)/30 = 166.67 -> 167; charge 1500*10*(1/2)/30 = 250; vat 52
        lines = fb.prorate_seats(sub(), plan(), ago(hours=12))
        self.assertEqual(lines[0]["amount_cents"], 167)
        self.assertEqual(lines[1]["amount_cents"], 250)
        self.assertEqual(lines[1]["vat_cents"], 52)

    def test_description_date_uses_period_end_own_timezone(self):
        pe = datetime(2026, 11, 1, 0, 30, tzinfo=timezone(timedelta(hours=2)))
        lines = fb.prorate_seats(sub(period_end=pe), plan(), pe - timedelta(days=15))
        self.assertTrue(lines[0]["description"].endswith("2026-11-01"))
        self.assertTrue(lines[1]["description"].endswith("2026-11-01"))

    def test_changed_at_equal_period_end_returns_empty(self):
        self.assertEqual(fb.prorate_seats(sub(), plan(), PERIOD_END), [])

    def test_more_than_30_unused_days_raises(self):
        with self.assertRaises(ValueError):
            fb.prorate_seats(sub(), plan(), ago(days=31))

    def test_canceled_and_past_due_are_prorated(self):
        for status in ("canceled", "past_due"):
            lines = fb.prorate_seats(sub(status=status), plan(), ago(days=15))
            self.assertEqual(len(lines), 2, status)

    def test_credit_first_then_charge_order(self):
        lines = fb.prorate_seats(sub(), plan(), ago(days=15))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])

    def test_missing_subscription_key_raises(self):
        s = sub()
        del s["vat_id"]
        with self.assertRaises(ValueError):
            fb.prorate_seats(s, plan(), ago(days=15))

    def test_missing_plan_key_raises(self):
        p = plan()
        del p["name"]
        with self.assertRaises(ValueError):
            fb.prorate_seats(sub(), p, ago(days=15))

    def test_description_helper_raises_when_date_cannot_fit(self):
        template = "{name}" + "x" * 80 + ", {date}"
        with self.assertRaises(ValueError):
            fb._describe(template, "P", "2026-11-01")


if __name__ == "__main__":
    unittest.main()