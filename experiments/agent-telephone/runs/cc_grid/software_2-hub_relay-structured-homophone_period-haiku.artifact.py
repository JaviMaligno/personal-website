# ===== FILE: seat_proration.py =====
"""Seat-upgrade proration for Fernhollow Studios.

Assumptions beyond the spec:
- R2 requires the key "seats" to be present. Its value is never read (R7).
- Credit template: "Seat credit {plan} to {date}". Charge template: "Seat charge {plan} to {date}".
  A name that is too long is cut and ends with "...". Length is counted in characters.
- With these templates, the room left for the name is always 54 characters, so the
  ValueError guard in _describe is not reachable with the current wording. It is kept as a safeguard.
- Input validation runs before the trialing, downgrade, and zero-day early returns.
- Prices and seat counts must be int. bool and float are rejected.
- vat_id None is treated as absent. Whitespace-only vat_id is treated as absent (R26).
- Equal prices return [] (R25).
- An empty plan name is not rejected.
- billable_seats greater than seats is not rejected. The spec is silent on this.
- Credits carry 0 VAT per R14. The house rule says VAT applies to credits too. R14 is the explicit
  instruction, so it is followed here.
- Unused days = floor((period_end - changed_at) / 24 h). Absolute instants are compared.

Open questions for Ingrid:
1. Confirm that charge VAT rounds down (R23).
2. Confirm that equal prices return [] (R25).
3. Confirm the description template (R27).
4. Confirm that credits carry no VAT (R14), given the house rule.
5. Confirm that the EUR 500 approval threshold is strictly greater than 50000 cents (R17).
6. Should billable_seats greater than seats be rejected?
7. Should an empty plan name be rejected?

The accompanying tests were written but not executed in the authoring environment.
"""

from datetime import datetime, timedelta

PERIOD_DAYS = 13
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
MAX_DESCRIPTION_LEN = 80
LARGE_CREDIT_CENTS = 50000
APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
APPROVER_LARGE = "Ramón Etxeberria-Goñi"
CREDIT_TEMPLATE = "Seat credit {name} to {date}"
CHARGE_TEMPLATE = "Seat charge {name} to {date}"
ELLIPSIS = "..."

SUBSCRIPTION_KEYS = (
    "id", "status", "plan_name", "seat_price_cents",
    "seats", "billable_seats", "vat_id", "period_end",
)
PLAN_KEYS = ("name", "seat_price_cents")


def _require_keys(mapping, keys, label):
    if not isinstance(mapping, dict):
        raise ValueError(f"{label} must be a dict")
    for key in keys:
        if key not in mapping:
            raise ValueError(f"{label} is missing key {key!r}")


def _require_int(value, label):
    if type(value) is not int:
        raise ValueError(f"{label} must be an integer")
    if value < 0:
        raise ValueError(f"{label} must not be negative")
    return value


def _require_aware(value, label):
    if not isinstance(value, datetime):
        raise ValueError(f"{label} must be a datetime")
    if value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value


def _require_text(value, label):
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    return value


def _has_vat_id(vat_id):
    if vat_id is None:
        return False
    _require_text(vat_id, "vat_id")
    return vat_id.strip() != ""


def _describe(template, name, period_end):
    date = period_end.strftime("%Y-%m-%d")
    room = MAX_DESCRIPTION_LEN - len(template.format(name="", date=date))
    if room < 1:
        raise ValueError("description cannot fit within 80 characters")
    if len(name) > room:
        if room > len(ELLIPSIS):
            name = name[: room - len(ELLIPSIS)] + ELLIPSIS
        else:
            name = name[:room]
    return template.format(name=name, date=date)


def prorate_seats(subscription, new_plan, changed_at):
    _require_keys(subscription, SUBSCRIPTION_KEYS, "subscription")
    _require_keys(new_plan, PLAN_KEYS, "new_plan")
    changed_at = _require_aware(changed_at, "changed_at")
    period_end = _require_aware(subscription["period_end"], "period_end")
    old_price = _require_int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _require_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    billable = _require_int(subscription["billable_seats"], "billable_seats")
    old_name = _require_text(subscription["plan_name"], "plan_name")
    new_name = _require_text(new_plan["name"], "new_plan name")
    reverse_charge = _has_vat_id(subscription["vat_id"])

    if subscription["status"] == "trialing":
        return []
    if new_price <= old_price:
        return []

    unused = (period_end - changed_at) // timedelta(days=1)
    if unused <= 0:
        return []
    if unused > PERIOD_DAYS:
        raise ValueError(f"unused days {unused} exceeds the {PERIOD_DAYS}-day period")

    credit_numerator = old_price * billable * unused
    credit = -((-credit_numerator) // PERIOD_DAYS)
    charge = (new_price * billable * unused) // PERIOD_DAYS

    lines = []
    if credit >= MIN_LINE_CENTS:
        approver = APPROVER_LARGE if credit > LARGE_CREDIT_CENTS else APPROVER_DEFAULT
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe(CREDIT_TEMPLATE, old_name, period_end),
            "approved_by": approver,
        })
    if charge >= MIN_LINE_CENTS:
        vat = 0 if reverse_charge else charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe(CHARGE_TEMPLATE, new_name, period_end),
            "approved_by": None,
        })
    return lines

# ===== FILE: test_seat_proration.py =====
import unittest
from datetime import datetime, timedelta, timezone

from seat_proration import prorate_seats

UTC = timezone.utc
PERIOD_END = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
THAO = "Nguyễn Thị Phương Thảo"
RAMON = "Ramón Etxeberria-Goñi"


def make_sub(**overrides):
    sub = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Studio",
        "seat_price_cents": 1000,
        "seats": 10,
        "billable_seats": 4,
        "vat_id": "",
        "period_end": PERIOD_END,
    }
    sub.update(overrides)
    return sub


def make_plan(price=2000, name="Studio Pro"):
    return {"name": name, "seat_price_cents": price}


class ProrateTests(unittest.TestCase):
    def test_normal_upgrade(self):
        changed = PERIOD_END - timedelta(days=5)
        lines = prorate_seats(make_sub(), make_plan(), changed)
        self.assertEqual(lines, [
            {"subscription_id": "sub_1", "kind": "credit", "amount_cents": 1539,
             "vat_cents": 0, "description": "Seat credit Studio to 2026-11-01",
             "approved_by": THAO},
            {"subscription_id": "sub_1", "kind": "charge", "amount_cents": 3076,
             "vat_cents": 645, "description": "Seat charge Studio Pro to 2026-11-01",
             "approved_by": None},
        ])

    def test_line_keys_are_exact(self):
        changed = PERIOD_END - timedelta(days=5)
        lines = prorate_seats(make_sub(), make_plan(), changed)
        expected = {"subscription_id", "kind", "amount_cents", "vat_cents",
                    "description", "approved_by"}
        for line in lines:
            self.assertEqual(set(line.keys()), expected)

    def test_ordering_credit_then_charge(self):
        changed = PERIOD_END - timedelta(days=5)
        lines = prorate_seats(make_sub(), make_plan(), changed)
        self.assertEqual([line["kind"] for line in lines], ["credit", "charge"])

    def test_downgrade_returns_empty(self):
        changed = PERIOD_END - timedelta(days=5)
        self.assertEqual(prorate_seats(make_sub(), make_plan(500), changed), [])

    def test_equal_price_returns_empty(self):
        changed = PERIOD_END - timedelta(days=5)
        self.assertEqual(prorate_seats(make_sub(), make_plan(1000), changed), [])

    def test_trialing_returns_empty(self):
        changed = PERIOD_END - timedelta(days=5)
        self.assertEqual(prorate_seats(make_sub(status="trialing"), make_plan(), changed), [])

    def test_other_statuses_are_prorated(self):
        changed = PERIOD_END - timedelta(days=5)
        lines = prorate_seats(make_sub(status="past_due"), make_plan(), changed)
        self.assertEqual(len(lines), 2)

    def test_reverse_charge_has_no_vat(self):
        changed = PERIOD_END - timedelta(days=5)
        lines = prorate_seats(make_sub(vat_id="DE123456789"), make_plan(), changed)
        self.assertEqual(lines[0]["vat_cents"], 0)
        self.assertEqual(lines[1]["vat_cents"], 0)
        self.assertEqual(lines[1]["amount_cents"], 3076)

    def test_whitespace_vat_id_counts_as_absent(self):
        changed = PERIOD_END - timedelta(days=5)
        lines = prorate_seats(make_sub(vat_id="   "), make_plan(), changed)
        self.assertEqual(lines[1]["vat_cents"], 645)

    def test_credit_over_500_euro_approved_by_ramon(self):
        sub = make_sub(seat_price_cents=10000, billable_seats=10)
        changed = PERIOD_END - timedelta(days=13)
        lines = prorate_seats(sub, make_plan(20000), changed)
        self.assertEqual(lines[0]["amount_cents"], 100000)
        self.assertEqual(lines[0]["approved_by"], RAMON)
        self.assertEqual(lines[1]["amount_cents"], 200000)

    def test_credit_exactly_500_euro_approved_by_thao(self):
        sub = make_sub(seat_price_cents=5000, billable_seats=10)
        changed = PERIOD_END - timedelta(days=13)
        lines = prorate_seats(sub, make_plan(6000), changed)
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], THAO)

    def test_approver_spelling_is_exact(self):
        self.assertEqual(THAO, "Nguyễn Thị Phương Thảo")
        self.assertEqual(RAMON, "Ramón Etxeberria-Goñi")

    def test_line_under_50_cents_is_skipped(self):
        sub = make_sub(seat_price_cents=600, billable_seats=1)
        changed = PERIOD_END - timedelta(days=1)
        lines = prorate_seats(sub, make_plan(700), changed)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 53)
        self.assertEqual(lines[0]["vat_cents"], 11)

    def test_both_lines_under_50_cents_returns_empty(self):
        sub = make_sub(seat_price_cents=100, billable_seats=1)
        changed = PERIOD_END - timedelta(days=1)
        self.assertEqual(prorate_seats(sub, make_plan(101), changed), [])

    def test_rounding_direction_credit_up_charge_down(self):
        sub = make_sub(seat_price_cents=1000, billable_seats=1)
        changed = PERIOD_END - timedelta(days=1)
        lines = prorate_seats(sub, make_plan(1500), changed)
        self.assertEqual(lines[0]["amount_cents"], 77)   # ceil(1000/13)
        self.assertEqual(lines[1]["amount_cents"], 115)  # floor(1500/13)
        self.assertEqual(lines[1]["vat_cents"], 24)      # floor(115 * 0.21)

    def test_long_description_shortens_name_and_keeps_date(self):
        sub = make_sub(plan_name="A" * 70)
        changed = PERIOD_END - timedelta(days=5)
        lines = prorate_seats(sub, make_plan(), changed)
        desc = lines[0]["description"]
        self.assertLessEqual(len(desc), 80)
        self.assertEqual(desc, "Seat credit " + "A" * 51 + "..." + " to 2026-11-01")
        self.assertTrue(desc.endswith("to 2026-11-01"))

    def test_partial_day_is_dropped(self):
        changed = PERIOD_END - timedelta(days=5, hours=3)
        lines = prorate_seats(make_sub(), make_plan(), changed)
        self.assertEqual(lines[0]["amount_cents"], 1539)

    def test_same_instant_in_other_timezone(self):
        changed = (PERIOD_END - timedelta(days=5)).astimezone(timezone(timedelta(hours=2)))
        lines = prorate_seats(make_sub(), make_plan(), changed)
        self.assertEqual(lines[0]["amount_cents"], 1539)

    def test_zero_or_negative_unused_days_returns_empty(self):
        self.assertEqual(prorate_seats(make_sub(), make_plan(), PERIOD_END), [])
        after = PERIOD_END + timedelta(hours=1)
        self.assertEqual(prorate_seats(make_sub(), make_plan(), after), [])

    def test_more_than_13_unused_days_raises(self):
        changed = PERIOD_END - timedelta(days=14)
        with self.assertRaises(ValueError):
            prorate_seats(make_sub(), make_plan(), changed)

    def test_exactly_13_unused_days_is_allowed(self):
        changed = PERIOD_END - timedelta(days=13)
        lines = prorate_seats(make_sub(), make_plan(), changed)
        self.assertEqual(lines[0]["amount_cents"], 4000)
        self.assertEqual(lines[1]["amount_cents"], 8000)

    def test_legacy_discount_is_ignored(self):
        changed = PERIOD_END - timedelta(days=5)
        with_field = prorate_seats(make_sub(legacy_discount=50), make_plan(), changed)
        without = prorate_seats(make_sub(), make_plan(), changed)
        self.assertEqual(with_field, without)

    def test_billable_seats_above_seats_is_not_rejected(self):
        changed = PERIOD_END - timedelta(days=5)
        lines = prorate_seats(make_sub(billable_seats=12, seats=10), make_plan(), changed)
        self.assertEqual(len(lines), 2)

    def test_naive_changed_at_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(make_sub(), make_plan(), datetime(2026, 10, 27, 12, 0))

    def test_naive_period_end_raises(self):
        sub = make_sub(period_end=datetime(2026, 11, 1, 12, 0))
        with self.assertRaises(ValueError):
            prorate_seats(sub, make_plan(), PERIOD_END - timedelta(days=5))

    def test_missing_subscription_key_raises(self):
        sub = make_sub()
        del sub["vat_id"]
        with self.assertRaises(ValueError):
            prorate_seats(sub, make_plan(), PERIOD_END - timedelta(days=5))

    def test_missing_plan_key_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(make_sub(), {"seat_price_cents": 2000},
                          PERIOD_END - timedelta(days=5))

    def test_float_price_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(make_sub(seat_price_cents=10.0), make_plan(),
                          PERIOD_END - timedelta(days=5))

    def test_negative_value_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(make_sub(billable_seats=-1), make_plan(),
                          PERIOD_END - timedelta(days=5))


if __name__ == "__main__":
    unittest.main()