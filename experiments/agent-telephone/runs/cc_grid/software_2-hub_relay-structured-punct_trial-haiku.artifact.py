"""Seat proration for Fernhollow Studios.

Defaults applied, for Ingrid to confirm:
- [DEFAULT] R4: naive datetimes raise ValueError.
- [DEFAULT] R6: credit lines name the old plan, charge lines name the new plan.
- [DEFAULT] R10: an equal price returns no lines, the same as a cheaper plan.
- [DEFAULT] R12: the 50-cent skip is measured on the net amount before VAT.
- [DEFAULT] R13: an empty-string vat_id is treated as absent, so 21% VAT applies.
- [OPEN] R13: VAT rounding direction is not specified. Implemented as round-up.
- [DEFAULT] R14: only status "active" is prorated.
- [DEFAULT] R15: credit text "Unused {old} seats, period end {date}", charge text "Prorated {new} seats, period end {date}", date in period_end's own timezone.
- [DEFAULT] R16: currency EUR. Threshold 50,000 cents, compared strictly against the net credit amount.
- [DEFAULT] Day count: floor of whole days from changed_at to period_end in UTC. remaining_days <= 0 returns []. remaining_days > 30 raises ValueError.
- [DEFAULT] Invalid input (missing keys, naive datetimes, remaining_days > 30, description cannot fit in 80 characters) raises ValueError.

R11 follows the client's rule (credits round up, charges round down), not the PM's proposed reversal.

R13 says credits carry no VAT. This differs from the house rule that VAT applies to credits too. The client's R13 is implemented as written.

Test results: not executed in this session.
"""

import unittest
from datetime import datetime, timedelta, timezone

_CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
_LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
_LARGE_CREDIT_CENTS = 50_000
_MIN_LINE_CENTS = 50
_VAT_PERCENT = 21
_MAX_DESCRIPTION = 80
_PERIOD_DAYS = 30
_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _ceil_div(numerator, denominator):
    return -((-numerator) // denominator)


def _require_aware(value, label):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")


def _description(prefix, plan_name, date_text):
    head = f"{prefix} "
    tail = f" seats, period end {date_text}"
    full = head + plan_name + tail
    if len(full) <= _MAX_DESCRIPTION:
        return full
    room = _MAX_DESCRIPTION - len(head) - len(tail)
    if room < 3:
        raise ValueError("description cannot fit within 80 characters")
    return head + plan_name[:room - 3] + "..." + tail


def prorate_seats(subscription, new_plan, changed_at):
    for key in _SUB_KEYS:
        if key not in subscription:
            raise ValueError(f"subscription is missing '{key}'")
    for key in _PLAN_KEYS:
        if key not in new_plan:
            raise ValueError(f"new_plan is missing '{key}'")
    _require_aware(changed_at, "changed_at")
    period_end = subscription["period_end"]
    _require_aware(period_end, "period_end")

    if subscription["status"] != "active":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    billable = subscription["billable_seats"]
    if not (_is_int(old_price) and _is_int(new_price) and _is_int(billable)):
        raise ValueError("prices and billable_seats must be integers")
    if billable < 0:
        raise ValueError("billable_seats must not be negative")

    remaining = (period_end - changed_at) // timedelta(days=1)
    if remaining <= 0:
        return []
    if remaining > _PERIOD_DAYS:
        raise ValueError("remaining_days cannot exceed 30")

    if new_price <= old_price:
        return []

    sub_id = subscription["id"]
    date_text = period_end.date().isoformat()
    lines = []

    credit = _ceil_div(old_price * billable * remaining, _PERIOD_DAYS)
    if credit >= _MIN_LINE_CENTS:
        approver = _LARGE_CREDIT_APPROVER if credit > _LARGE_CREDIT_CENTS else _CREDIT_APPROVER
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Unused", subscription["plan_name"], date_text),
            "approved_by": approver,
        })

    charge = (new_price * billable * remaining) // _PERIOD_DAYS
    if charge >= _MIN_LINE_CENTS:
        if subscription["vat_id"]:
            vat = 0
        else:
            vat = _ceil_div(charge * _VAT_PERCENT, 100)
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description("Prorated", new_plan["name"], date_text),
            "approved_by": None,
        })

    return lines


class _ProrateTests(unittest.TestCase):
    UTC = timezone.utc

    def _sub(self, **overrides):
        base = dict(
            id="sub_1",
            status="active",
            plan_name="Studio",
            seat_price_cents=1000,
            seats=10,
            billable_seats=10,
            vat_id=None,
            period_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
        )
        base.update(overrides)
        return base

    def _plan(self, price, name="Pro"):
        return {"name": name, "seat_price_cents": price}

    def _changed(self):
        return datetime(2026, 3, 16, tzinfo=timezone.utc)

    def test_upgrade_credit_then_charge(self):
        lines = prorate_seats(self._sub(), self._plan(2000), self._changed())
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        self.assertEqual([l["amount_cents"] for l in lines], [5000, 10000])
        self.assertEqual([l["vat_cents"] for l in lines], [0, 2100])
        self.assertEqual([l["approved_by"] for l in lines], [_CREDIT_APPROVER, None])
        self.assertEqual(lines[0]["subscription_id"], "sub_1")

    def test_downgrade_returns_empty(self):
        self.assertEqual(prorate_seats(self._sub(), self._plan(500), self._changed()), [])

    def test_equal_price_returns_empty(self):
        self.assertEqual(prorate_seats(self._sub(), self._plan(1000), self._changed()), [])

    def test_trialing_returns_empty(self):
        sub = self._sub(status="trialing")
        self.assertEqual(prorate_seats(sub, self._plan(2000), self._changed()), [])

    def test_billable_seats_used_not_seats(self):
        sub = self._sub(seats=99, billable_seats=5)
        lines = prorate_seats(sub, self._plan(2000), self._changed())
        self.assertEqual(lines[0]["amount_cents"], 2500)
        self.assertEqual(lines[1]["amount_cents"], 5000)

    def test_thirty_day_rule_across_months(self):
        sub = self._sub(billable_seats=1,
                        period_end=datetime(2026, 3, 2, tzinfo=timezone.utc))
        changed = datetime(2026, 1, 31, tzinfo=timezone.utc)
        lines = prorate_seats(sub, self._plan(2000), changed)
        self.assertEqual(lines[0]["amount_cents"], 1000)
        self.assertEqual(lines[1]["amount_cents"], 2000)

    def test_fifty_cent_skip_keeps_other_line(self):
        sub = self._sub(seat_price_cents=100, billable_seats=1,
                        period_end=datetime(2026, 3, 26, tzinfo=timezone.utc))
        changed = datetime(2026, 3, 16, tzinfo=timezone.utc)
        lines = prorate_seats(sub, self._plan(200), changed)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "charge")
        self.assertEqual(lines[0]["amount_cents"], 66)
        self.assertEqual(lines[0]["vat_cents"], 14)

    def test_vat_21_percent_and_reverse_charge(self):
        sub = self._sub(seat_price_cents=100, billable_seats=1,
                        period_end=datetime(2026, 3, 26, tzinfo=timezone.utc))
        changed = datetime(2026, 3, 16, tzinfo=timezone.utc)
        standard = prorate_seats(sub, self._plan(200), changed)[0]
        self.assertEqual(standard["vat_cents"], 14)
        reverse = prorate_seats(dict(sub, vat_id="GB123456789"), self._plan(200), changed)[0]
        self.assertEqual(reverse["vat_cents"], 0)
        empty = prorate_seats(dict(sub, vat_id=""), self._plan(200), changed)[0]
        self.assertEqual(empty["vat_cents"], 14)

    def test_credit_rounds_up_and_charge_rounds_down(self):
        sub = self._sub(billable_seats=1,
                        period_end=datetime(2026, 3, 26, tzinfo=timezone.utc))
        changed = datetime(2026, 3, 16, tzinfo=timezone.utc)
        lines = prorate_seats(sub, self._plan(2000), changed)
        self.assertEqual(lines[0]["amount_cents"], 334)
        self.assertEqual(lines[1]["amount_cents"], 666)
        self.assertEqual(lines[1]["vat_cents"], 140)

    def test_approver_at_exactly_50000_is_thao(self):
        sub = self._sub(seat_price_cents=50000, billable_seats=1,
                        period_end=datetime(2026, 3, 31, tzinfo=timezone.utc))
        changed = datetime(2026, 3, 1, tzinfo=timezone.utc)
        lines = prorate_seats(sub, self._plan(60000), changed)
        self.assertEqual(lines[0]["amount_cents"], 50000)
        self.assertEqual(lines[0]["approved_by"], _CREDIT_APPROVER)

    def test_approver_at_50001_is_ramon(self):
        sub = self._sub(seat_price_cents=50001, billable_seats=1,
                        period_end=datetime(2026, 3, 31, tzinfo=timezone.utc))
        changed = datetime(2026, 3, 1, tzinfo=timezone.utc)
        lines = prorate_seats(sub, self._plan(60000), changed)
        self.assertEqual(lines[0]["amount_cents"], 50001)
        self.assertEqual(lines[0]["approved_by"], _LARGE_CREDIT_APPROVER)

    def test_description_length_and_date_preserved(self):
        long_name = "X" * 120
        tz = timezone(timedelta(hours=2))
        sub = self._sub(plan_name=long_name,
                        period_end=datetime(2026, 3, 31, 0, 30, tzinfo=tz))
        lines = prorate_seats(sub, self._plan(2000, name=long_name), self._changed())
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertLessEqual(len(line["description"]), 80)
            self.assertIn("period end 2026-03-31", line["description"])
            self.assertIn("...", line["description"])

    def test_naive_datetime_raises(self):
        with self.assertRaises(ValueError):
            prorate_seats(self._sub(), self._plan(2000), datetime(2026, 3, 16))


if __name__ == "__main__":
    unittest.main()