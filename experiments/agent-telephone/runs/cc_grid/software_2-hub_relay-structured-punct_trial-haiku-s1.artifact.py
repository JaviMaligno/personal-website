"""Seat upgrade proration for Fernhollow Studios.

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list of invoice lines.

Run tests with: python3 -m unittest <path-to-this-file>

Open items for client confirmation (not resolved silently):
(a) days is whole floored days (R21 default). Client said only "number of days".
(b) VAT on charges is floor(amount_cents * 21 / 100) per R26. This rounds in the
    client's favour, which conflicts with the general R9 house rule. Confirm.
(c) Only "trialing" is excluded (R12/R29). Other statuses such as past_due or
    canceled are prorated. Confirm.
(d) The R25 description wording is a proposed template and may need client wording.
"""

import unittest
from datetime import datetime, timedelta, timezone

# ---- Constants (change here) ----
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
LARGE_CREDIT_THRESHOLD_CENTS = 50000
PERIOD_DAYS = 30
DESCRIPTION_MAX_CHARS = 80
APPROVER_STANDARD = "Nguyễn Thị Phương Thảo"
APPROVER_LARGE = "Ramón Etxeberria-Goñi"
CREDIT_PREFIX = "Credit unused "
CHARGE_PREFIX = "Charge unused "
SEATS_TO = " seats to "
ELLIPSIS = "..."

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def _require_keys(mapping, keys, label):
    if not isinstance(mapping, dict):
        raise ValueError(f"{label} must be a dict")
    for key in keys:
        if key not in mapping:
            raise ValueError(f"{label} is missing key: {key}")


def _count(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    if value < 0:
        raise ValueError(f"{label} must not be negative")
    return value


def _aware(value, label):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")
    return value


def _text(value, label):
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    return value


def _date_text(value):
    return f"{value.year:04d}-{value.month:02d}-{value.day:02d}"


def _describe(prefix, name, date_text):
    suffix = SEATS_TO + date_text
    room = DESCRIPTION_MAX_CHARS - len(prefix) - len(suffix)
    if len(name) > room:
        name = name[: room - len(ELLIPSIS)] + ELLIPSIS
    return prefix + name + suffix


def prorate_seats(subscription, new_plan, changed_at):
    _require_keys(subscription, _SUB_KEYS, "subscription")
    _require_keys(new_plan, _PLAN_KEYS, "new_plan")

    old_price = _count(subscription["seat_price_cents"], "seat_price_cents")
    seats = _count(subscription["seats"], "seats")
    billable = _count(subscription["billable_seats"], "billable_seats")
    new_price = _count(new_plan["seat_price_cents"], "new_plan.seat_price_cents")
    period_end = _aware(subscription["period_end"], "period_end")
    changed = _aware(changed_at, "changed_at")
    status = _text(subscription["status"], "status")
    plan_name = _text(subscription["plan_name"], "plan_name")
    new_name = _text(new_plan["name"], "new_plan.name")

    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise ValueError("vat_id must be a string or None")
    has_vat_id = vat_id is not None and vat_id.strip() != ""

    # seats is validated above but billing uses billable_seats only (R5).
    if status == "trialing":
        return []
    if billable == 0 or new_price <= old_price:
        return []

    days = (period_end - changed) // timedelta(days=1)
    if days <= 0:
        return []

    credit_cents = -((-(old_price * billable * days)) // PERIOD_DAYS)  # ceil
    charge_cents = (new_price * billable * days) // PERIOD_DAYS        # floor

    date_text = _date_text(period_end)
    sub_id = subscription["id"]
    lines = []

    if credit_cents >= MIN_LINE_CENTS:
        approver = (APPROVER_LARGE if credit_cents > LARGE_CREDIT_THRESHOLD_CENTS
                    else APPROVER_STANDARD)
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit_cents,
            "vat_cents": 0,
            "description": _describe(CREDIT_PREFIX, plan_name, date_text),
            "approved_by": approver,
        })

    if charge_cents >= MIN_LINE_CENTS:
        vat_cents = 0 if has_vat_id else (charge_cents * VAT_PERCENT) // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge_cents,
            "vat_cents": vat_cents,
            "description": _describe(CHARGE_PREFIX, new_name, date_text),
            "approved_by": None,
        })

    return lines


# ---- Tests ----

UTC = timezone.utc
T0 = datetime(2026, 1, 1, tzinfo=UTC)
T_END = datetime(2026, 1, 31, tzinfo=UTC)


def _sub(**overrides):
    sub = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Pro",
        "seat_price_cents": 1000,
        "seats": 10,
        "billable_seats": 10,
        "vat_id": None,
        "period_end": T_END,
        "legacy_discount": 99,
    }
    sub.update(overrides)
    return sub


def _plan(price=1500, name="Business"):
    return {"name": name, "seat_price_cents": price}


def _run(sub=None, plan=None, changed=T0):
    return prorate_seats(sub if sub is not None else _sub(),
                         plan if plan is not None else _plan(),
                         changed)


class ProrateTests(unittest.TestCase):

    def test_basic_upgrade_credit_then_charge(self):
        lines = _run()
        self.assertEqual(len(lines), 2)
        credit, charge = lines
        self.assertEqual(credit["kind"], "credit")
        self.assertEqual(credit["amount_cents"], 10000)
        self.assertEqual(credit["vat_cents"], 0)
        self.assertEqual(credit["approved_by"], APPROVER_STANDARD)
        self.assertEqual(credit["description"], "Credit unused Pro seats to 2026-01-31")
        self.assertEqual(credit["subscription_id"], "sub_1")
        self.assertEqual(set(credit), {"subscription_id", "kind", "amount_cents",
                                       "vat_cents", "description", "approved_by"})
        self.assertEqual(charge["kind"], "charge")
        self.assertEqual(charge["amount_cents"], 15000)
        self.assertEqual(charge["vat_cents"], 3150)
        self.assertIsNone(charge["approved_by"])
        self.assertEqual(charge["description"], "Charge unused Business seats to 2026-01-31")

    def test_amounts_are_plain_ints(self):
        for line in _run():
            self.assertIs(type(line["amount_cents"]), int)
            self.assertIs(type(line["vat_cents"]), int)

    def test_bills_on_billable_seats_not_seats(self):
        lines = _run(sub=_sub(seats=20, billable_seats=10))
        self.assertEqual(lines[0]["amount_cents"], 10000)
        self.assertEqual(lines[1]["amount_cents"], 15000)

    def test_legacy_discount_ignored(self):
        with_discount = _run(sub=_sub(legacy_discount=50))
        without = _sub()
        del without["legacy_discount"]
        self.assertEqual(with_discount, _run(sub=without))

    def test_credit_rounds_up_and_charge_rounds_down(self):
        # days = 10; credit = ceil(1001*10/30) = 334; charge = floor(1502*10/30) = 500
        lines = _run(sub=_sub(seat_price_cents=1001, seats=1, billable_seats=1,
                              period_end=datetime(2026, 1, 11, tzinfo=UTC)),
                     plan=_plan(price=1502))
        self.assertEqual(lines[0]["amount_cents"], 334)
        self.assertEqual(lines[1]["amount_cents"], 500)
        self.assertEqual(lines[1]["vat_cents"], 105)

    def test_charge_vat_is_floored(self):
        # charge 333 -> VAT floor(333*21/100) = floor(69.93) = 69
        lines = _run(sub=_sub(seat_price_cents=200, seats=1, billable_seats=1),
                     plan=_plan(price=333))
        self.assertEqual(lines[1]["amount_cents"], 333)
        self.assertEqual(lines[1]["vat_cents"], 69)

    def test_credit_under_50_skipped(self):
        lines = _run(sub=_sub(seat_price_cents=49, seats=1, billable_seats=1),
                     plan=_plan(price=100))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 100)
        self.assertEqual(lines[0]["vat_cents"], 21)

    def test_charge_under_50_skipped_credit_kept(self):
        # days = 10; credit = ceil(1480/30) = 50 (kept); charge = floor(1490/30) = 49 (skipped)
        lines = _run(sub=_sub(seat_price_cents=148, seats=1, billable_seats=1,
                              period_end=datetime(2026, 1, 11, tzinfo=UTC)),
                     plan=_plan(price=149))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "credit")
        self.assertEqual(lines[0]["amount_cents"], 50)
        self.assertEqual(lines[0]["approved_by"], APPROVER_STANDARD)

    def test_both_under_50_returns_empty(self):
        lines = _run(sub=_sub(seat_price_cents=10, seats=1, billable_seats=1),
                     plan=_plan(price=20))
        self.assertEqual(lines, [])

    def test_threshold_exactly_50000_goes_to_thao(self):
        lines = _run(sub=_sub(seat_price_cents=50000, seats=1, billable_seats=1),
                     plan=_plan(price=50100))
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], "Nguyễn Thị Phương Thảo")

    def test_threshold_above_50000_goes_to_ramon(self):
        lines = _run(sub=_sub(seat_price_cents=50001, seats=1, billable_seats=1),
                     plan=_plan(price=50002))
        self.assertEqual(lines[0]["amount_cents"], 50001)
        self.assertEqual(lines[0]["approved_by"], "Ramón Etxeberria-Goñi")

    def test_vat_reverse_charge_with_vat_id(self):
        lines = _run(sub=_sub(vat_id="DE123456789"))
        self.assertEqual(lines[0]["vat_cents"], 0)
        self.assertEqual(lines[1]["vat_cents"], 0)
        self.assertEqual(lines[1]["amount_cents"], 15000)

    def test_blank_vat_id_still_charges_vat(self):
        for blank in ("", "   ", "\t\n"):
            with self.subTest(vat_id=blank):
                lines = _run(sub=_sub(vat_id=blank))
                self.assertEqual(lines[1]["vat_cents"], 3150)

    def test_trialing_returns_empty(self):
        self.assertEqual(_run(sub=_sub(status="trialing")), [])

    def test_other_statuses_are_prorated(self):
        lines = _run(sub=_sub(status="past_due"))
        self.assertEqual(len(lines), 2)

    def test_downgrade_returns_empty(self):
        self.assertEqual(_run(plan=_plan(price=900)), [])

    def test_equal_price_returns_empty(self):
        self.assertEqual(_run(plan=_plan(price=1000)), [])

    def test_zero_billable_returns_empty(self):
        self.assertEqual(_run(sub=_sub(billable_seats=0)), [])

    def test_zero_days_returns_empty(self):
        self.assertEqual(_run(changed=T_END), [])

    def test_period_end_before_changed_at_returns_empty(self):
        self.assertEqual(_run(changed=datetime(2026, 2, 1, tzinfo=UTC)), [])

    def test_partial_day_is_floored(self):
        # 30.5 days elapsed -> days = 30
        sub = _sub(seat_price_cents=3000, seats=1, billable_seats=1,
                   period_end=datetime(2026, 1, 31, 12, 0, tzinfo=UTC))
        lines = _run(sub=sub, plan=_plan(price=4500))
        self.assertEqual(lines[0]["amount_cents"], 3000)
        self.assertEqual(lines[1]["amount_cents"], 4500)

    def test_description_date_uses_supplied_timezone(self):
        # period_end is 2026-01-31 00:30 at +02:00 (2026-01-30 22:30 UTC).
        # days = 29; credit = 2900; charge = 4350.
        tz2 = timezone(timedelta(hours=2))
        sub = _sub(seat_price_cents=3000, seats=1, billable_seats=1,
                   period_end=datetime(2026, 1, 31, 0, 30, tzinfo=tz2))
        lines = _run(sub=sub, plan=_plan(price=4500))
        self.assertEqual(lines[0]["amount_cents"], 2900)
        self.assertEqual(lines[1]["amount_cents"], 4350)
        self.assertTrue(lines[0]["description"].endswith("2026-01-31"))
        self.assertTrue(lines[1]["description"].endswith("2026-01-31"))

    def test_description_truncates_plan_name_with_ellipsis(self):
        # fixed text plus date is 34 chars, so the name gets 46 chars: 43 + "..."
        lines = _run(sub=_sub(plan_name="A" * 100), plan=_plan(name="B" * 100))
        self.assertEqual(lines[0]["description"],
                         "Credit unused " + "A" * 43 + "..." + " seats to 2026-01-31")
        self.assertEqual(lines[1]["description"],
                         "Charge unused " + "B" * 43 + "..." + " seats to 2026-01-31")
        self.assertEqual(len(lines[0]["description"]), 80)
        self.assertEqual(len(lines[1]["description"]), 80)

    def test_description_exactly_80_code_points_not_truncated(self):
        lines = _run(sub=_sub(plan_name="é" * 46))
        self.assertEqual(lines[0]["description"],
                         "Credit unused " + "é" * 46 + " seats to 2026-01-31")
        self.assertEqual(len(lines[0]["description"]), 80)

    def test_output_is_deterministic(self):
        self.assertEqual(_run(), _run())

    def test_subscription_id_on_every_line(self):
        for line in _run(sub=_sub(id="sub_42")):
            self.assertEqual(line["subscription_id"], "sub_42")

    def test_missing_subscription_key_raises(self):
        for key in ("id", "status", "plan_name", "seat_price_cents", "seats",
                    "billable_seats", "vat_id", "period_end"):
            with self.subTest(key=key):
                sub = _sub()
                del sub[key]
                with self.assertRaises(ValueError):
                    _run(sub=sub)

    def test_missing_new_plan_key_raises(self):
        for key in ("name", "seat_price_cents"):
            with self.subTest(key=key):
                plan = _plan()
                del plan[key]
                with self.assertRaises(ValueError):
                    _run(plan=plan)

    def test_non_integer_prices_and_counts_raise(self):
        cases = [
            _sub(seat_price_cents=1000.0),
            _sub(seats=10.0),
            _sub(billable_seats="10"),
        ]
        for sub in cases:
            with self.subTest(sub=sub):
                with self.assertRaises(ValueError):
                    _run(sub=sub)
        with self.assertRaises(ValueError):
            _run(plan=_plan(price=1500.0))

    def test_bool_counts_raise(self):
        with self.assertRaises(ValueError):
            _run(sub=_sub(seats=True))
        with self.assertRaises(ValueError):
            _run(sub=_sub(billable_seats=False))
        with self.assertRaises(ValueError):
            _run(plan=_plan(price=True))

    def test_negative_values_raise(self):
        with self.assertRaises(ValueError):
            _run(sub=_sub(seats=-1))
        with self.assertRaises(ValueError):
            _run(sub=_sub(billable_seats=-1))
        with self.assertRaises(ValueError):
            _run(sub=_sub(seat_price_cents=-5))
        with self.assertRaises(ValueError):
            _run(plan=_plan(price=-5))

    def test_naive_datetimes_raise(self):
        with self.assertRaises(ValueError):
            _run(changed=datetime(2026, 1, 1))
        with self.assertRaises(ValueError):
            _run(sub=_sub(period_end=datetime(2026, 1, 31)))


if __name__ == "__main__":
    unittest.main()