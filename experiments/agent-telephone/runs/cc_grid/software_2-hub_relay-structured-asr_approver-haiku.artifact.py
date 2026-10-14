# seat_proration.py
import unittest
from datetime import datetime, timedelta, timezone

# Not executed in this environment; the unit tests are unverified.

PERIOD_US = 30 * 86400 * 1_000_000
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
APPROVAL_THRESHOLD_CENTS = 50000
APPROVER_DEFAULT = "Win Tee Fung Tao"
APPROVER_LARGE = "Ramón Etxeberria-Goñi"
MAX_DESC = 80
ELLIPSIS = "..."
SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
            "billable_seats", "vat_id", "period_end")
PLAN_KEYS = ("name", "seat_price_cents")


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _require_nonneg_int(value, label):
    if not _is_int(value) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _require_aware(value, label):
    if not isinstance(value, datetime):
        raise ValueError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _validate(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise ValueError("subscription and new_plan must be dicts")
    for key in SUB_KEYS:
        if key not in subscription:
            raise ValueError(f"subscription missing key {key!r}")
    for key in PLAN_KEYS:
        if key not in new_plan:
            raise ValueError(f"new_plan missing key {key!r}")
    if not isinstance(subscription["plan_name"], str):
        raise ValueError("plan_name must be a string")
    if not isinstance(new_plan["name"], str):
        raise ValueError("new_plan name must be a string")
    _require_nonneg_int(subscription["seat_price_cents"], "seat_price_cents")
    _require_nonneg_int(subscription["seats"], "seats")
    _require_nonneg_int(subscription["billable_seats"], "billable_seats")
    _require_nonneg_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    _require_aware(subscription["period_end"], "period_end")
    _require_aware(changed_at, "changed_at")


def _elapsed_microseconds(start, end):
    delta = end - start
    return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds


def _description(name, period_end):
    suffix = " until " + period_end.strftime("%Y-%m-%d")
    desc = name + suffix
    if len(desc) <= MAX_DESC:
        return desc
    room = MAX_DESC - len(suffix)
    if room < len(ELLIPSIS):
        raise ValueError("description cannot fit within 80 characters")
    return name[: room - len(ELLIPSIS)] + ELLIPSIS + suffix


def prorate_seats(subscription, new_plan, changed_at):
    _validate(subscription, new_plan, changed_at)

    period_end = subscription["period_end"]
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    seats = subscription["billable_seats"]

    if subscription["status"] == "trialing":
        return []
    if changed_at >= period_end:
        return []
    if seats == 0:
        return []
    if new_price <= old_price:
        return []

    # Exact integer arithmetic: fraction = elapsed_us / PERIOD_US.
    elapsed_us = _elapsed_microseconds(changed_at, period_end)
    base = seats * elapsed_us
    # Credits round up (ceiling); charges round down (floor).
    credit = -((-(old_price * base)) // PERIOD_US)
    charge = (new_price * base) // PERIOD_US

    lines = []
    if credit >= MIN_LINE_CENTS:
        approver = APPROVER_LARGE if credit > APPROVAL_THRESHOLD_CENTS else APPROVER_DEFAULT
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            # R17 overrides the house rule: credits never carry VAT.
            "vat_cents": 0,
            "description": _description(subscription["plan_name"], period_end),
            "approved_by": approver,
        })
    if charge >= MIN_LINE_CENTS:
        if subscription["vat_id"]:
            vat = 0
        else:
            vat = (charge * VAT_PERCENT) // 100
        lines.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description(new_plan["name"], period_end),
            "approved_by": None,
        })
    return lines


UTC = timezone.utc
CHANGED = datetime(2026, 10, 16, tzinfo=UTC)
ONE_DAY_BEFORE_END = datetime(2026, 10, 30, tzinfo=UTC)
PRO = {"name": "Pro", "seat_price_cents": 2000}


def _sub(**overrides):
    base = {
        "id": "sub_1",
        "status": "active",
        "plan_name": "Starter",
        "seat_price_cents": 1000,
        "seats": 12,
        "billable_seats": 10,
        "vat_id": None,
        "period_end": datetime(2026, 10, 31, tzinfo=UTC),
        "legacy_discount": 99,
    }
    base.update(overrides)
    return base


class TestProrateSeats(unittest.TestCase):

    def test_basic_upgrade_credit_and_charge(self):
        r = prorate_seats(_sub(), PRO, CHANGED)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0], {
            "subscription_id": "sub_1",
            "kind": "credit",
            "amount_cents": 5000,
            "vat_cents": 0,
            "description": "Starter until 2026-10-31",
            "approved_by": "Win Tee Fung Tao",
        })
        self.assertEqual(r[1], {
            "subscription_id": "sub_1",
            "kind": "charge",
            "amount_cents": 10000,
            "vat_cents": 2100,
            "description": "Pro until 2026-10-31",
            "approved_by": None,
        })

    def test_credit_precedes_charge(self):
        r = prorate_seats(_sub(), PRO, CHANGED)
        self.assertEqual([line["kind"] for line in r], ["credit", "charge"])

    def test_billable_seats_used_not_seats(self):
        r = prorate_seats(_sub(seats=50, billable_seats=10), PRO, CHANGED)
        self.assertEqual(r[0]["amount_cents"], 5000)
        self.assertEqual(r[1]["amount_cents"], 10000)

    def test_period_is_30_days_regardless_of_month_length(self):
        # 15 days elapsed across February (28 days) still gives half a period.
        end = datetime(2026, 3, 1, tzinfo=UTC)
        start = datetime(2026, 2, 14, tzinfo=UTC)
        r = prorate_seats(_sub(period_end=end), PRO, start)
        self.assertEqual(r[0]["amount_cents"], 5000)
        self.assertEqual(r[1]["amount_cents"], 10000)

    def test_downgrade_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(), {"name": "Basic", "seat_price_cents": 500}, CHANGED), [])

    def test_trialing_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), PRO, CHANGED), [])

    def test_credit_ceiling_and_charge_floor(self):
        # One day of a 30-day period with 10 seats:
        # credit = 1000*10/30 = 333.33 -> 334; charge = 2000*10/30 = 666.67 -> 666.
        r = prorate_seats(_sub(), PRO, ONE_DAY_BEFORE_END)
        self.assertEqual(r[0]["amount_cents"], 334)
        self.assertEqual(r[1]["amount_cents"], 666)
        self.assertEqual(r[1]["vat_cents"], 139)

    def test_line_under_50_cents_is_dropped(self):
        # One seat, one day: credit = ceil(1000/30) = 34 (dropped); charge = floor(2000/30) = 66 (kept).
        r = prorate_seats(_sub(billable_seats=1), PRO, ONE_DAY_BEFORE_END)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["kind"], "charge")
        self.assertEqual(r[0]["amount_cents"], 66)

    def test_both_lines_under_50_cents_returns_empty(self):
        # Credit = ceil(500/30) = 17; charge = floor(510/30) = 17.
        r = prorate_seats(_sub(seat_price_cents=500, billable_seats=1),
                          {"name": "Pro", "seat_price_cents": 510}, ONE_DAY_BEFORE_END)
        self.assertEqual(r, [])

    def test_exactly_50_cents_is_kept(self):
        r = prorate_seats(_sub(seat_price_cents=100, billable_seats=1),
                          {"name": "Pro", "seat_price_cents": 200}, CHANGED)
        self.assertEqual([line["amount_cents"] for line in r], [50, 100])

    def test_vat_21_percent_on_charge(self):
        r = prorate_seats(_sub(), PRO, CHANGED)
        self.assertEqual(r[1]["vat_cents"], 2100)

    def test_reverse_charge_when_vat_id_set(self):
        r = prorate_seats(_sub(vat_id="DE123456789"), PRO, CHANGED)
        self.assertEqual(r[1]["vat_cents"], 0)
        self.assertEqual(r[1]["amount_cents"], 10000)

    def test_no_vat_on_credits(self):
        r = prorate_seats(_sub(), PRO, CHANGED)
        self.assertEqual(r[0]["vat_cents"], 0)

    def test_approval_threshold_exactly_50000_is_default_approver(self):
        # Credit = 100000 * 1 * 15 / 30 = 50000 exactly.
        r = prorate_seats(_sub(seat_price_cents=100000, billable_seats=1),
                          {"name": "Pro", "seat_price_cents": 100001}, CHANGED)
        self.assertEqual(r[0]["amount_cents"], 50000)
        self.assertEqual(r[0]["approved_by"], "Win Tee Fung Tao")

    def test_approval_threshold_50001_is_large_approver(self):
        # Credit = 100002 * 1 * 15 / 30 = 50001 exactly.
        r = prorate_seats(_sub(seat_price_cents=100002, billable_seats=1),
                          {"name": "Pro", "seat_price_cents": 100003}, CHANGED)
        self.assertEqual(r[0]["amount_cents"], 50001)
        self.assertEqual(r[0]["approved_by"], "Ramón Etxeberria-Goñi")

    def test_description_truncates_plan_name_and_keeps_date(self):
        r = prorate_seats(_sub(plan_name="A" * 100), PRO, CHANGED)
        expected = "A" * 60 + "..." + " until 2026-10-31"
        self.assertEqual(r[0]["description"], expected)
        self.assertEqual(len(r[0]["description"]), 80)
        self.assertTrue(r[0]["description"].endswith("until 2026-10-31"))

    def test_changed_at_equal_to_period_end_returns_empty(self):
        end = datetime(2026, 10, 31, tzinfo=UTC)
        self.assertEqual(prorate_seats(_sub(), PRO, end), [])

    def test_changed_at_after_period_end_returns_empty(self):
        later = datetime(2026, 11, 1, tzinfo=UTC)
        self.assertEqual(prorate_seats(_sub(), PRO, later), [])

    def test_equal_price_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(), {"name": "Same", "seat_price_cents": 1000}, CHANGED), [])

    def test_zero_billable_seats_returns_empty(self):
        self.assertEqual(prorate_seats(_sub(billable_seats=0), PRO, CHANGED), [])

    def test_different_offsets_same_instant(self):
        plus_two = timezone(timedelta(hours=2))
        changed = datetime(2026, 10, 16, 2, 0, tzinfo=plus_two)
        r = prorate_seats(_sub(), PRO, changed)
        self.assertEqual(r[0]["amount_cents"], 5000)
        self.assertEqual(r[1]["amount_cents"], 10000)

    def test_missing_key_raises(self):
        sub = _sub()
        del sub["vat_id"]
        with self.assertRaises(ValueError):
            prorate_seats(sub, PRO, CHANGED)

    def test_negative_price_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(seat_price_cents=-1), PRO, CHANGED)

    def test_float_price_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(seat_price_cents=10.0), PRO, CHANGED)

    def test_bool_seats_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(billable_seats=True), PRO, CHANGED)

    def test_naive_changed_at_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), PRO, datetime(2026, 10, 16))


if __name__ == "__main__":
    unittest.main()