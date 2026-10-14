"""Seat-upgrade proration for Fernhollow Studios (client: Ingrid).

Review notes (this module has not been executed):

Implemented: R1-R18. R19 needed no cut, so VAT (R13) is in scope.
Cut: none.

Ambiguities and contradictions:
- House rule says VAT applies to every invoice line, credits included. R13 says credits carry vat_cents = 0. R13 is the explicit task rule, so it is implemented.
- House rule says money rounds half-up. D4 says VAT rounds down (floor). D4 is implemented as written, so VAT is floored.
- R10 only blocks a strictly cheaper new plan. Equal price is treated as proceeding, so a credit and a charge at the same rate are produced. The credit rounds up and the charge rounds down, so they can differ by 1 cent.
- D1(d) returns [] when changed_at >= period_end. This is assumed, not specified.
- Remaining time is not clamped to the 30-day period. Nothing in the spec says to clamp, so a period_end more than 30 days away produces a credit or charge larger than one period's price.
- R15/D5: if the fixed description text leaves no room for any plan name, the name is dropped and the length may still exceed 80. This does not happen with realistic inputs.
- The unit tests are inline under __main__ because only this one file can be returned. They have not been run.
"""

from datetime import datetime, timedelta, timezone

CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
LARGE_CREDIT_CENTS = 50000
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
PERIOD_US = 30 * 86400 * 10**6
MAX_DESC = 80
ONE_US = timedelta(microseconds=1)


def _is_aware(dt):
    return isinstance(dt, datetime) and dt.utcoffset() is not None


def _require_int(name, value):
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer number of cents")
    return value


def _describe(kind, plan_name, period_end):
    head = f"{kind}: unused "
    tail = f" seats to {period_end.strftime('%Y-%m-%d')}"
    room = MAX_DESC - len(head) - len(tail)
    name = plan_name
    if len(name) > room:
        name = name[:room - 3] + "..." if room >= 3 else name[:max(room, 0)]
    return head + name + tail


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription["period_end"]
    if not (_is_aware(changed_at) and _is_aware(period_end)):
        raise ValueError("changed_at and period_end must be timezone-aware datetimes")

    if subscription["status"] == "trialing":
        return []

    old_price = _require_int("seat_price_cents", subscription["seat_price_cents"])
    new_price = _require_int("new_plan seat_price_cents", new_plan["seat_price_cents"])
    if new_price < old_price:
        return []

    remaining_us = (period_end - changed_at) // ONE_US
    if remaining_us <= 0:
        return []

    seats = _require_int("billable_seats", subscription["billable_seats"])
    sub_id = subscription["id"]
    lines = []

    credit_numerator = old_price * seats * remaining_us
    credit = -((-credit_numerator) // PERIOD_US)
    if credit >= MIN_LINE_CENTS:
        approver = LARGE_CREDIT_APPROVER if credit > LARGE_CREDIT_CENTS else CREDIT_APPROVER
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit", subscription["plan_name"], period_end),
            "approved_by": approver,
        })

    charge_numerator = new_price * seats * remaining_us
    charge = charge_numerator // PERIOD_US
    if charge >= MIN_LINE_CENTS:
        vat = 0 if subscription["vat_id"] else charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe("Charge", new_plan["name"], period_end),
            "approved_by": None,
        })

    return lines


if __name__ == "__main__":
    import unittest

    UTC = timezone.utc
    PE = datetime(2026, 11, 1, tzinfo=UTC)
    NEW = {"name": "Studio Plus", "seat_price_cents": 1500}

    def _sub(**over):
        s = {
            "id": "sub_1",
            "status": "active",
            "plan_name": "Studio",
            "seat_price_cents": 1000,
            "seats": 9,
            "billable_seats": 5,
            "vat_id": None,
            "period_end": PE,
            "legacy_discount": 99,
        }
        s.update(over)
        return s

    class ProrationTests(unittest.TestCase):
        def test_trialing_returns_empty(self):
            self.assertEqual(prorate_seats(_sub(status="trialing"), NEW, PE - timedelta(days=1)), [])

        def test_downgrade_returns_empty(self):
            cheaper = {"name": "Lite", "seat_price_cents": 500}
            self.assertEqual(prorate_seats(_sub(), cheaper, PE - timedelta(days=1)), [])

        def test_equal_price_proceeds_with_rounding(self):
            same = {"name": "Studio", "seat_price_cents": 1000}
            lines = prorate_seats(_sub(), same, PE - timedelta(days=1))
            self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
            self.assertEqual(lines[0]["amount_cents"], 167)
            self.assertEqual(lines[1]["amount_cents"], 166)

        def test_naive_datetime_raises(self):
            with self.assertRaises(ValueError):
                prorate_seats(_sub(), NEW, datetime(2026, 10, 31))
            with self.assertRaises(ValueError):
                prorate_seats(_sub(period_end=datetime(2026, 11, 1)), NEW,
                              datetime(2026, 10, 31, tzinfo=UTC))

        def test_30_day_rule_across_31_day_month(self):
            pe = datetime(2026, 10, 31, tzinfo=UTC)
            changed = pe - timedelta(days=15)
            lines = prorate_seats(_sub(period_end=pe), NEW, changed)
            self.assertEqual(lines[0]["amount_cents"], 2500)
            self.assertEqual(lines[1]["amount_cents"], 3750)
            self.assertEqual(lines[1]["vat_cents"], 787)

        def test_credit_rounds_up_and_charge_rounds_down(self):
            same = {"name": "Studio", "seat_price_cents": 1000}
            lines = prorate_seats(_sub(), same, PE - timedelta(days=1))
            self.assertEqual(lines[0]["amount_cents"], 167)
            self.assertEqual(lines[1]["amount_cents"], 166)

        def test_sub_50_cent_lines_skipped(self):
            same = {"name": "Studio", "seat_price_cents": 1000}
            lines = prorate_seats(_sub(billable_seats=1), same, PE - timedelta(days=1))
            self.assertEqual(lines, [])

        def test_reverse_charge_no_vat(self):
            pe = datetime(2026, 10, 31, tzinfo=UTC)
            lines = prorate_seats(_sub(period_end=pe, vat_id="DE123"), NEW, pe - timedelta(days=15))
            self.assertEqual(lines[1]["vat_cents"], 0)

        def test_credit_over_50000_switches_approver(self):
            big = _sub(seat_price_cents=100000, billable_seats=2)
            lines = prorate_seats(big, {"name": "X", "seat_price_cents": 100000}, PE - timedelta(days=30))
            self.assertEqual(lines[0]["amount_cents"], 200000)
            self.assertEqual(lines[0]["approved_by"], LARGE_CREDIT_APPROVER)

        def test_credit_exactly_50000_keeps_default_approver(self):
            edge = _sub(seat_price_cents=50000, billable_seats=1)
            lines = prorate_seats(edge, {"name": "X", "seat_price_cents": 50000}, PE - timedelta(days=30))
            self.assertEqual(lines[0]["amount_cents"], 50000)
            self.assertEqual(lines[0]["approved_by"], CREDIT_APPROVER)
            self.assertIsNone(lines[1]["approved_by"])

        def test_description_length_and_date(self):
            sub = _sub(plan_name="A" * 120)
            new = {"name": "B" * 120, "seat_price_cents": 1500}
            lines = prorate_seats(sub, new, PE - timedelta(days=1))
            for line in lines:
                self.assertLessEqual(len(line["description"]), MAX_DESC)
                self.assertTrue(line["description"].endswith("to 2026-11-01"))

        def test_line_order_credit_then_charge(self):
            lines = prorate_seats(_sub(), NEW, PE - timedelta(days=1))
            self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])

        def test_legacy_discount_ignored(self):
            a = prorate_seats(_sub(), NEW, PE - timedelta(days=1))
            b = prorate_seats(_sub(legacy_discount=None), NEW, PE - timedelta(days=1))
            self.assertEqual(a, b)

    unittest.main()
</br>