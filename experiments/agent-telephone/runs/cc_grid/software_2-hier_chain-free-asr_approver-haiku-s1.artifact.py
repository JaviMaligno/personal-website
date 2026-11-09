"""Seat upgrade proration for Fernhollow Studios billing.

Not executed in the authoring environment. Run with: python -m unittest <this file>

Design flags for the client (also noted in the implementation summary):
(a) Amounts are assumed to be EUR cents; the 50000 approval threshold must be confirmed.
(b) The approval threshold is applied to net amount_cents, which equals gross for credits.
(c) Unused time is exact fractional days via integer microseconds, clamped to [0, 30 days]. Client to confirm both the fractional choice and the clamp.
(d) Equal prices are not a downgrade, so they produce a credit and a charge of similar size, not no lines.
(e) ROUNDING CONFLICT: credits round up and charges round down. Both directions favour the client, which contradicts the stated principle that rounding must never favour the client. Implemented as written; must be confirmed.
(f) VAT CONFLICT: the house rule says VAT applies to every invoice line including credits, but the spec sets credit vat_cents to 0. Implemented per the explicit spec; must be confirmed.
(g) The house rule of half-up rounding to the cent is not used; the explicit floor and ceiling rules are implemented instead.
(h) CONTRADICTION: the edge case says a new plan price of 0 with a positive old price yields a credit and no charge, but the downgrade check (new < old) returns an empty list first. The explicit check order is implemented, so this returns []. Product manager to confirm.
(i) billable_seats is not checked against seats.
(j) Inputs are validated before the trialing check, so malformed input raises even for trialing subscriptions.
"""

from datetime import datetime, timedelta, timezone
import unittest

__all__ = ["prorate_seats"]

_PERIOD_US = 30 * 24 * 60 * 60 * 10**6
_ONE_US = timedelta(microseconds=1)
_MIN_LINE_CENTS = 50
_VAT_PERCENT = 21
_LARGE_CREDIT_CENTS = 50000
_APPROVER_DEFAULT = "Win Tee Fung Tao"
_APPROVER_LARGE = "Ramón Etxeberria-Goñi"
_MAX_DESC = 80


def _money(value, name):
    if type(value) is not int:
        raise TypeError(f"{name} must be an int in cents, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _text(value, name):
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _description(plan_name, label, period_end):
    date = period_end.strftime("%Y-%m-%d")
    suffix = f" {label}, period ends {date}"
    text = plan_name + suffix
    if len(text) <= _MAX_DESC:
        return text
    room = _MAX_DESC - len(suffix)
    if room >= 3:
        short = plan_name[:room - 3] + "..."
    else:
        short = "..."[:max(room, 0)]
    return short + suffix


def prorate_seats(subscription, new_plan, changed_at):
    seats = _money(subscription["seats"], "seats")
    billable = _money(subscription["billable_seats"], "billable_seats")
    old = _money(subscription["seat_price_cents"], "seat_price_cents")
    new = _money(new_plan["seat_price_cents"], "new seat_price_cents")
    plan_name = _text(subscription["plan_name"], "plan_name")
    new_name = _text(new_plan["name"], "name")
    period_end = _aware(subscription["period_end"], "period_end")
    changed_at = _aware(changed_at, "changed_at")

    if subscription["status"] == "trialing":
        return []
    if new < old:
        return []

    elapsed = (period_end - changed_at) // _ONE_US
    unused = min(max(elapsed, 0), _PERIOD_US)

    # Credits round up (ceiling), charges round down (floor), per the explicit rule.
    credit = -((-(billable * old * unused)) // _PERIOD_US)
    charge = (billable * new * unused) // _PERIOD_US

    sub_id = subscription["id"]
    lines = []

    if credit >= _MIN_LINE_CENTS:
        approver = _APPROVER_LARGE if credit > _LARGE_CREDIT_CENTS else _APPROVER_DEFAULT
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(plan_name, "credit", period_end),
            "approved_by": approver,
        })

    if charge >= _MIN_LINE_CENTS:
        if subscription.get("vat_id"):
            vat = 0
        else:
            vat = charge * _VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description(new_name, "charge", period_end),
            "approved_by": None,
        })

    return lines


class _ProrateTests(unittest.TestCase):
    PE = datetime(2026, 11, 1, tzinfo=timezone.utc)
    FULL = PE - timedelta(days=30)
    HALF = PE - timedelta(days=15)

    @staticmethod
    def _sub(**over):
        base = {
            "id": "sub_1",
            "status": "active",
            "plan_name": "Studio",
            "seat_price_cents": 1000,
            "seats": 5,
            "billable_seats": 5,
            "vat_id": None,
            "period_end": _ProrateTests.PE,
        }
        base.update(over)
        return base

    @staticmethod
    def _plan(price, name="Studio Plus"):
        return {"name": name, "seat_price_cents": price}

    def test_trialing_returns_empty(self):
        self.assertEqual(
            prorate_seats(self._sub(status="trialing"), self._plan(2000), self.FULL), [])

    def test_downgrade_returns_empty(self):
        self.assertEqual(
            prorate_seats(self._sub(seat_price_cents=2000), self._plan(1000), self.FULL), [])

    def test_zero_new_price_is_downgrade(self):
        self.assertEqual(
            prorate_seats(self._sub(seat_price_cents=1000), self._plan(0), self.FULL), [])

    def test_vat_id_gives_zero_vat_on_charge(self):
        out = prorate_seats(
            self._sub(vat_id="NL123", billable_seats=1, seats=1), self._plan(2000), self.FULL)
        self.assertEqual(out[1]["kind"], "charge")
        self.assertEqual(out[1]["amount_cents"], 2000)
        self.assertEqual(out[1]["vat_cents"], 0)

    def test_charge_vat_without_vat_id(self):
        out = prorate_seats(
            self._sub(billable_seats=1, seats=1), self._plan(2000), self.FULL)
        self.assertEqual(out[1]["vat_cents"], 420)
        self.assertIsNone(out[1]["approved_by"])

    def test_credit_approval_threshold(self):
        cases = [
            (50000, "Win Tee Fung Tao"),
            (50001, "Ramón Etxeberria-Goñi"),
            (49999, "Win Tee Fung Tao"),
        ]
        for amount, approver in cases:
            with self.subTest(amount=amount):
                out = prorate_seats(
                    self._sub(seat_price_cents=amount, billable_seats=1, seats=1),
                    self._plan(amount), self.FULL)
                self.assertEqual(out[0]["kind"], "credit")
                self.assertEqual(out[0]["amount_cents"], amount)
                self.assertEqual(out[0]["vat_cents"], 0)
                self.assertEqual(out[0]["approved_by"], approver)

    def test_line_under_50_cents_dropped(self):
        self.assertEqual(
            prorate_seats(self._sub(seat_price_cents=0, billable_seats=1, seats=1),
                          self._plan(49), self.FULL), [])
        out = prorate_seats(self._sub(seat_price_cents=0, billable_seats=1, seats=1),
                            self._plan(50), self.FULL)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["kind"], "charge")
        self.assertEqual(out[0]["amount_cents"], 50)

    def test_long_plan_name_description_shortened(self):
        long_name = "P" * 200
        pe = self.PE
        with self.subTest("credit uses subscription plan name"):
            out = prorate_seats(self._sub(plan_name=long_name, billable_seats=1, seats=1),
                                self._plan(1000), self.FULL)
            desc = out[0]["description"]
            self.assertLessEqual(len(desc), 80)
            self.assertTrue(desc.endswith("credit, period ends 2026-11-01"))
            self.assertIn("...", desc)
        with self.subTest("charge uses new plan name"):
            out = prorate_seats(self._sub(seat_price_cents=0, billable_seats=1, seats=1),
                                self._plan(1000, name="X" * 200), self.FULL)
            desc = out[0]["description"]
            self.assertLessEqual(len(desc), 80)
            self.assertTrue(desc.endswith("charge, period ends 2026-11-01"))
            self.assertTrue(desc.startswith("X"))
            self.assertIn("...", desc)

    def test_rounding_credit_up_charge_down(self):
        # Half a period on 99 cents: credit 49.5 rounds up to 50, charge 49.5 rounds down to 49.
        out = prorate_seats(self._sub(seat_price_cents=99, billable_seats=1, seats=1),
                            self._plan(99), self.HALF)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["kind"], "credit")
        self.assertEqual(out[0]["amount_cents"], 50)

    def test_rounding_charge_floor_with_vat(self):
        # 199 cents over half a period: credit ceil(99.5)=100, charge floor(99.5)=99, VAT floor(20.79)=20.
        out = prorate_seats(self._sub(seat_price_cents=199, billable_seats=1, seats=1),
                            self._plan(199), self.HALF)
        self.assertEqual(out[0]["amount_cents"], 100)
        self.assertEqual(out[1]["amount_cents"], 99)
        self.assertEqual(out[1]["vat_cents"], 20)

    def test_billable_seats_used_not_seats(self):
        out = prorate_seats(
            self._sub(seats=10, billable_seats=2, seat_price_cents=1000),
            self._plan(1000), self.FULL)
        self.assertEqual(out[0]["amount_cents"], 2000)
        self.assertEqual(out[1]["amount_cents"], 2000)

    def test_legacy_discount_ignored(self):
        base = self._sub(billable_seats=1, seats=1)
        with_key = dict(base, legacy_discount=-999999)
        self.assertEqual(
            prorate_seats(with_key, self._plan(2000), self.FULL),
            prorate_seats(base, self._plan(2000), self.FULL))

    def test_changed_at_at_or_after_period_end_empty(self):
        self.assertEqual(prorate_seats(self._sub(), self._plan(2000), self.PE), [])
        self.assertEqual(
            prorate_seats(self._sub(), self._plan(2000), self.PE + timedelta(days=1)), [])

    def test_floats_and_bools_raise_typeerror(self):
        bad_cases = [
            self._sub(seat_price_cents=1000.0),
            self._sub(billable_seats=2.0),
            self._sub(billable_seats=True),
            self._sub(seats=1.5),
        ]
        for sub in bad_cases:
            with self.subTest(sub=sub):
                with self.assertRaises(TypeError):
                    prorate_seats(sub, self._plan(2000), self.FULL)
        with self.subTest("new plan price float"):
            with self.assertRaises(TypeError):
                prorate_seats(self._sub(), self._plan(1500.0), self.FULL)

    def test_negative_values_raise_valueerror(self):
        with self.assertRaises(ValueError):
            prorate_seats(self._sub(billable_seats=-1), self._plan(2000), self.FULL)
        with self.assertRaises(ValueError):
            prorate_seats(self._sub(), self._plan(-5), self.FULL)

    def test_zero_billable_seats_empty(self):
        self.assertEqual(
            prorate_seats(self._sub(billable_seats=0), self._plan(2000), self.FULL), [])

    def test_both_prices_zero_empty(self):
        self.assertEqual(
            prorate_seats(self._sub(seat_price_cents=0), self._plan(0), self.FULL), [])

    def test_old_zero_gives_charge_only(self):
        out = prorate_seats(self._sub(seat_price_cents=0, billable_seats=1, seats=1),
                            self._plan(1000), self.FULL)
        self.assertEqual([line["kind"] for line in out], ["charge"])

    def test_output_key_order(self):
        out = prorate_seats(self._sub(billable_seats=1, seats=1), self._plan(2000), self.FULL)
        expected = ["subscription_id", "kind", "amount_cents", "vat_cents",
                    "description", "approved_by"]
        for line in out:
            self.assertEqual(list(line.keys()), expected)

    def test_period_end_date_not_converted_to_utc(self):
        tz = timezone(timedelta(hours=-5))
        pe = datetime(2026, 11, 1, 0, 30, tzinfo=tz)
        out = prorate_seats(self._sub(period_end=pe, billable_seats=1, seats=1),
                            self._plan(1000), pe - timedelta(days=30))
        self.assertTrue(out[0]["description"].endswith("2026-11-01"))


if __name__ == "__main__":
    unittest.main()