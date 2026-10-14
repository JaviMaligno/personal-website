"""Prorated seat billing for Fernhollow Studios.

Public entry point: prorate_seats(subscription, new_plan, changed_at).

Status: this file was written without execution. No tool was available in this session, so the tests have NOT been run. Verify with: python -m unittest prorate -v

Assumptions and deviations (for the product manager and Ingrid):
1. Cents are euro cents, so the 50,000-cent approver threshold means EUR 500.
2. The threshold compares the credit amount, which carries no VAT.
3. The change day counts as used: remaining_days = calendar days from the change date to the period_end date.
4. Calendar dates use each datetime's own timezone: changed_at.date() in changed_at's zone, period_end.date() in period_end's zone. The description date is period_end's own-zone date. The early exit "changed_at >= period_end" compares instants. If the calendar-day result is zero or negative (possible only when the zones differ), the function returns [] as a guard.
5. An equal per-seat price is not a downgrade. It is prorated and produces a credit and a charge.
6. Only status "trialing" is excluded. Other statuses are prorated normally.
7. The 50-cent minimum applies to each line's net amount before VAT, independently.
8. VAT on charges is floor(charge * 21 / 100), or 0 when vat_id is truthy (reverse charge).
9. The description wording is the proposal from the brief. Plan names are shortened with an ellipsis when needed. The date is never shortened. Length is checked in code.
10. Negative seats, billable_seats, or prices raise ValueError. Non-integer numeric values and bools raise TypeError. Missing required keys raise KeyError naming the missing keys. Naive or non-datetime values raise ValueError or TypeError.
Deviations from the house rules, as the brief directs: credits carry vat_cents 0 (the house rule puts VAT on credits too), and rounding is ceiling for credits and floor for charges, not half-up.
"""

import unittest
from datetime import datetime, timedelta, timezone

__all__ = ["prorate_seats"]

BILLING_PERIOD_DAYS = 30
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
APPROVAL_THRESHOLD_CENTS = 50_000
DEFAULT_APPROVER = "Win Tee Fung Tao"
THRESHOLD_APPROVER = "Ramón Etxeberria-Goñi"
MAX_DESCRIPTION_LEN = 80
ELLIPSIS = "\u2026"

_SUB_REQUIRED = (
    "id", "status", "plan_name", "seat_price_cents",
    "seats", "billable_seats", "vat_id", "period_end",
)
_PLAN_REQUIRED = ("name", "seat_price_cents")


def _require_keys(mapping, keys, label):
    missing = [k for k in keys if k not in mapping]
    if missing:
        raise KeyError(f"{label} is missing required key(s): {', '.join(missing)}")


def _require_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must not be negative, got {value}")
    return value


def _require_str(value, name):
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string, got {type(value).__name__}")
    return value


def _require_aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime, got {type(value).__name__}")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _describe(head, plan_name, tail):
    room = MAX_DESCRIPTION_LEN - len(head) - len(tail)
    if len(plan_name) > room:
        if room < 1:
            raise ValueError("description template leaves no room for the plan name")
        plan_name = plan_name[: room - 1] + ELLIPSIS
    text = head + plan_name + tail
    if len(text) > MAX_DESCRIPTION_LEN:
        raise ValueError(f"description is {len(text)} characters, limit is {MAX_DESCRIPTION_LEN}")
    return text


def prorate_seats(subscription, new_plan, changed_at):
    _require_keys(subscription, _SUB_REQUIRED, "subscription")
    _require_keys(new_plan, _PLAN_REQUIRED, "new_plan")

    changed_at = _require_aware(changed_at, "changed_at")
    period_end = _require_aware(subscription["period_end"], "period_end")
    subscription_id = subscription["id"]
    old_plan_name = _require_str(subscription["plan_name"], "plan_name")
    new_plan_name = _require_str(new_plan["name"], "new_plan name")
    old_price = _require_int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _require_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    _require_int(subscription["seats"], "seats")
    billable = _require_int(subscription["billable_seats"], "billable_seats")

    if subscription["status"] == "trialing":
        return []
    if new_price < old_price:
        return []
    if changed_at >= period_end:
        return []

    remaining_days = (period_end.date() - changed_at.date()).days
    if remaining_days <= 0:
        return []

    old_total = old_price * billable
    new_total = new_price * billable
    credit_amount = -((-(old_total * remaining_days)) // BILLING_PERIOD_DAYS)
    charge_amount = (new_total * remaining_days) // BILLING_PERIOD_DAYS

    date_text = period_end.date().isoformat()
    lines = []

    if credit_amount >= MIN_LINE_CENTS:
        approver = (
            THRESHOLD_APPROVER
            if credit_amount > APPROVAL_THRESHOLD_CENTS
            else DEFAULT_APPROVER
        )
        lines.append({
            "subscription_id": subscription_id,
            "kind": "credit",
            "amount_cents": credit_amount,
            "vat_cents": 0,
            "description": _describe(
                "Unused ", old_plan_name, f" seats credit, period ends {date_text}"
            ),
            "approved_by": approver,
        })

    if charge_amount >= MIN_LINE_CENTS:
        if subscription["vat_id"]:
            vat_cents = 0
        else:
            vat_cents = charge_amount * VAT_PERCENT // 100
        lines.append({
            "subscription_id": subscription_id,
            "kind": "charge",
            "amount_cents": charge_amount,
            "vat_cents": vat_cents,
            "description": _describe(
                "Prorated ", new_plan_name, f" seats, period ends {date_text}"
            ),
            "approved_by": None,
        })

    return lines


def _sub(**overrides):
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Studio",
        "seat_price_cents": 1001,
        "seats": 3,
        "billable_seats": 3,
        "vat_id": None,
        "period_end": datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc),
    }
    base.update(overrides)
    return base


def _plan(price=1501, name="Studio Pro"):
    return {"name": name, "seat_price_cents": price}


UTC = timezone.utc
CHANGED = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)  # 7 remaining days to 2026-10-20


class ProrateSeatsTests(unittest.TestCase):

    def test_worked_example(self):
        lines = prorate_seats(_sub(), _plan(), CHANGED)
        self.assertEqual(len(lines), 2)
        credit, charge = lines
        self.assertEqual(credit["kind"], "credit")
        self.assertEqual(credit["amount_cents"], 701)
        self.assertEqual(credit["vat_cents"], 0)
        self.assertEqual(credit["approved_by"], "Win Tee Fung Tao")
        self.assertEqual(charge["kind"], "charge")
        self.assertEqual(charge["amount_cents"], 1050)
        self.assertEqual(charge["vat_cents"], 220)
        self.assertIsNone(charge["approved_by"])
        self.assertEqual(credit["subscription_id"], "sub_1")

    def test_rounding_credit_up_and_charge_down_on_fractional_cents(self):
        # credit 3003*7/30 = 700.7 rounds up to 701; charge 4503*7/30 = 1050.7 rounds down to 1050
        credit, charge = prorate_seats(_sub(), _plan(), CHANGED)
        self.assertEqual(credit["amount_cents"], 701)
        self.assertEqual(charge["amount_cents"], 1050)

    def test_rounding_on_larger_fractional_cent_remainders(self):
        # credit 10010/30 = 333.67 -> 334 ; charge 15010/30 = 500.33 -> 500
        sub = _sub(billable_seats=10)
        credit, charge = prorate_seats(sub, _plan(), datetime(2026, 10, 19, 12, 0, tzinfo=UTC))
        self.assertEqual(credit["amount_cents"], 334)
        self.assertEqual(charge["amount_cents"], 500)
        self.assertEqual(charge["vat_cents"], 105)

    def test_exact_division_has_no_rounding(self):
        # old 3000*1*3/30 = 300 exactly; new 3000*1*3/30 = 300 exactly (equal price, not a downgrade)
        sub = _sub(seat_price_cents=3000, billable_seats=1)
        lines = prorate_seats(sub, _plan(price=3000), datetime(2026, 10, 17, 12, 0, tzinfo=UTC))
        self.assertEqual(lines[0]["amount_cents"], 300)
        self.assertEqual(lines[1]["amount_cents"], 300)

    def test_credit_below_50_cents_is_omitted(self):
        # credit 1001/30 = 33.37 -> 34 (<50, omitted); charge 1501/30 = 50.03 -> 50 (kept)
        sub = _sub(billable_seats=1)
        lines = prorate_seats(sub, _plan(), datetime(2026, 10, 19, 12, 0, tzinfo=UTC))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 50)
        self.assertEqual(lines[0]["vat_cents"], 10)

    def test_fifty_cents_exactly_is_kept(self):
        sub = _sub(seat_price_cents=1500, billable_seats=1)
        lines = prorate_seats(sub, _plan(price=1501), datetime(2026, 10, 19, 12, 0, tzinfo=UTC))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        self.assertEqual(lines[0]["amount_cents"], 50)

    def test_charge_below_50_cents_is_omitted_and_empty_result(self):
        # credit 34 (omitted); charge 1470/30 = 49.0 -> 49 (omitted)
        sub = _sub(billable_seats=1)
        self.assertEqual(
            prorate_seats(sub, _plan(price=1470), datetime(2026, 10, 19, 12, 0, tzinfo=UTC)),
            [],
        )

    def test_vat_applied_without_vat_id(self):
        charge = prorate_seats(_sub(vat_id=""), _plan(), CHANGED)[1]
        self.assertEqual(charge["vat_cents"], 220)

    def test_vat_zero_with_vat_id_reverse_charge(self):
        charge = prorate_seats(_sub(vat_id="DE123456789"), _plan(), CHANGED)[1]
        self.assertEqual(charge["amount_cents"], 1050)
        self.assertEqual(charge["vat_cents"], 0)

    def test_vat_rounds_down(self):
        # charge 1050 -> 1050*21/100 = 220.5 -> 220
        charge = prorate_seats(_sub(), _plan(), CHANGED)[1]
        self.assertEqual(charge["vat_cents"], 220)

    def test_credits_have_zero_vat_even_without_vat_id(self):
        credit = prorate_seats(_sub(), _plan(), CHANGED)[0]
        self.assertEqual(credit["vat_cents"], 0)

    def test_approver_at_exactly_50000_is_default(self):
        sub = _sub(seat_price_cents=50000, billable_seats=1,
                   period_end=datetime(2026, 10, 20, 12, 0, tzinfo=UTC))
        credit = prorate_seats(sub, _plan(price=60000),
                               datetime(2026, 9, 20, 12, 0, tzinfo=UTC))[0]
        self.assertEqual(credit["amount_cents"], 50000)
        self.assertEqual(credit["approved_by"], "Win Tee Fung Tao")

    def test_approver_at_50001_is_threshold_approver(self):
        sub = _sub(seat_price_cents=50001, billable_seats=1,
                   period_end=datetime(2026, 10, 20, 12, 0, tzinfo=UTC))
        credit = prorate_seats(sub, _plan(price=60000),
                               datetime(2026, 9, 20, 12, 0, tzinfo=UTC))[0]
        self.assertEqual(credit["amount_cents"], 50001)
        self.assertEqual(credit["approved_by"], "Ramón Etxeberria-Goñi")
        self.assertEqual(credit["approved_by"].encode("utf-8").decode("utf-8"),
                         "Ramón Etxeberria-Goñi")

    def test_trialing_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(), CHANGED), [])

    def test_non_trialing_statuses_are_prorated(self):
        for status in ("past_due", "canceled", "active"):
            with self.subTest(status=status):
                self.assertEqual(len(prorate_seats(_sub(status=status), _plan(), CHANGED)), 2)

    def test_downgrade_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(), _plan(price=900), CHANGED), [])

    def test_equal_price_is_prorated_not_downgrade(self):
        lines = prorate_seats(_sub(), _plan(price=1001), CHANGED)
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        self.assertEqual(lines[0]["amount_cents"], 701)
        self.assertEqual(lines[1]["amount_cents"], 700)  # 3003*7/30 = 700.7 floored

    def test_changed_at_equal_to_period_end_returns_empty(self):
        self.assertEqual(
            prorate_seats(_sub(), _plan(), datetime(2026, 10, 20, 12, 0, tzinfo=UTC)), [])

    def test_changed_at_after_period_end_returns_empty(self):
        self.assertEqual(
            prorate_seats(_sub(), _plan(), datetime(2026, 10, 21, 12, 0, tzinfo=UTC)), [])

    def test_description_length_and_date_preserved(self):
        for lines in (prorate_seats(_sub(), _plan(), CHANGED),):
            for line in lines:
                self.assertLessEqual(len(line["description"]), 80)
                self.assertIn("2026-10-20", line["description"])
        credit, charge = prorate_seats(_sub(), _plan(), CHANGED)
        self.assertIn("Studio", credit["description"])
        self.assertIn("Studio Pro", charge["description"])

    def test_long_plan_name_is_shortened_but_date_kept(self):
        long_name = "Z" * 300
        credit, charge = prorate_seats(
            _sub(plan_name=long_name), _plan(name=long_name), CHANGED)
        for line in (credit, charge):
            self.assertLessEqual(len(line["description"]), 80)
            self.assertIn("2026-10-20", line["description"])
            self.assertIn(ELLIPSIS, line["description"])

    def test_naive_changed_at_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(), datetime(2026, 10, 13, 12, 0))

    def test_naive_period_end_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(period_end=datetime(2026, 10, 20, 12, 0)), _plan(), CHANGED)

    def test_missing_subscription_key_raises_clear_error(self):
        sub = _sub()
        del sub["vat_id"]
        with self.assertRaises(KeyError) as ctx:
            prorate_seats(sub, _plan(), CHANGED)
        self.assertIn("vat_id", str(ctx.exception))

    def test_missing_plan_key_raises_clear_error(self):
        with self.assertRaises(KeyError) as ctx:
            prorate_seats(_sub(), {"name": "Studio Pro"}, CHANGED)
        self.assertIn("seat_price_cents", str(ctx.exception))

    def test_uses_billable_seats_not_seats(self):
        lines_a = prorate_seats(_sub(seats=3, billable_seats=3), _plan(), CHANGED)
        lines_b = prorate_seats(_sub(seats=50, billable_seats=3), _plan(), CHANGED)
        self.assertEqual(lines_a, lines_b)

    def test_negative_seats_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(billable_seats=-1), _plan(), CHANGED)

    def test_negative_price_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(price=-5), CHANGED)

    def test_float_price_rejected(self):
        with self.assertRaises(TypeError):
            prorate_seats(_sub(seat_price_cents=1001.0), _plan(), CHANGED)

    def test_remaining_days_uses_each_datetimes_own_timezone(self):
        plus5 = timezone(timedelta(hours=5))
        changed = datetime(2026, 10, 13, 0, 30, tzinfo=plus5)  # calendar date 2026-10-13
        credit = prorate_seats(_sub(), _plan(), changed)[0]
        self.assertEqual(credit["amount_cents"], 701)


if __name__ == "__main__":
    unittest.main()