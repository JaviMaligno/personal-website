"""Seat upgrade proration for Fernhollow Studios.

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list[dict].

Assumptions (also covered by the tests at the bottom):
- Overrides the house defaults: credits round UP, charges round DOWN, VAT is
  rounded DOWN (amount*21//100) and credits carry no VAT.
- Integer math only. Seats = billable_seats; seats and legacy_discount are ignored.
- A period is 13 days. days = whole UTC days from changed_at to period_end,
  floored (partial days do not count), clamped to 0..13.
- Naive datetimes (changed_at or period_end) raise ValueError. This is checked
  before the status check, so a naive datetime is rejected even when trialing.
- Checks: status == "trialing" -> []; new price < old price -> [].
  Equal price is not a downgrade.
- Each line is rounded first, then dropped if < 50 cents (exactly 50 is kept).
  Lines are skipped independently. amount_cents is positive for credits too.
- vat_id: None, or empty/whitespace-only string, means no vat_id (VAT applies).
- approved_by: charge None; credit "Nguyễn Thị Phương Thảo", or
  "Ramón Etxeberria-Goñi" if credit amount_cents > 50000.
- Description: "Credit unused <plan> until YYYY-MM-DD" / "Charge <plan> until
  YYYY-MM-DD". The date is the UTC date of period_end. Max 80 characters. If
  too long, the plan name is cut and ends with a single "…". If the name budget
  is < 1 char or the name is empty, the name is omitted. The date is always kept.
- Output order: credit, then charge.
"""
from datetime import datetime, timedelta, timezone
import unittest

UTC = timezone.utc
PERIOD_DAYS = 13
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
BIG_CREDIT_CENTS = 50000
MAX_DESC = 80
APPROVER = "Nguyễn Thị Phương Thảo"
BIG_APPROVER = "Ramón Etxeberria-Goñi"


def _check_aware(dt, label):
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")


def _description(prefix, name, end_date):
    tail = f" until {end_date}"
    budget = MAX_DESC - len(prefix) - len(tail)
    name = name or ""
    if not name or budget < 1:
        return f"{prefix.rstrip()}{tail}"
    if len(name) > budget:
        name = name[: budget - 1] + "…"
    return f"{prefix}{name}{tail}"


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription["period_end"]
    _check_aware(changed_at, "changed_at")
    _check_aware(period_end, "period_end")

    if subscription["status"] == "trialing":
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    end_utc = period_end.astimezone(UTC)
    days = (end_utc - changed_at.astimezone(UTC)) // timedelta(days=1)
    days = max(0, min(PERIOD_DAYS, days))
    seats = subscription["billable_seats"]
    end_date = end_utc.strftime("%Y-%m-%d")
    sub_id = subscription["id"]

    lines = []
    credit = -(-(old_price * seats * days) // PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit unused ", subscription["plan_name"], end_date),
            "approved_by": BIG_APPROVER if credit > BIG_CREDIT_CENTS else APPROVER,
        })

    charge = (new_price * seats * days) // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        vat_id = subscription.get("vat_id")
        has_vat_id = vat_id is not None and bool(str(vat_id).strip())
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if has_vat_id else charge * VAT_PERCENT // 100,
            "description": _description("Charge ", new_plan["name"], end_date),
            "approved_by": None,
        })
    return lines


# ---------------------------------------------------------------- tests
def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 99, "billable_seats": 1,
         "vat_id": None, "period_end": datetime(2026, 1, 14, tzinfo=UTC)}
    s.update(kw)
    return s


def _plan(price=1000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


AT = datetime(2026, 1, 13, tzinfo=UTC)  # 1 day before period end
START = datetime(2026, 1, 1, tzinfo=UTC)  # 13 days


class ProrateTests(unittest.TestCase):
    def test_rounding_direction(self):
        credit, charge = prorate_seats(_sub(), _plan(), AT)
        self.assertEqual(credit["amount_cents"], 77)  # 76.9 up
        self.assertEqual(charge["amount_cents"], 76)  # 76.9 down
        self.assertEqual(charge["vat_cents"], 15)  # 15.96 down
        self.assertEqual(credit["vat_cents"], 0)

    def test_skip_and_exactly_50(self):
        lines = prorate_seats(_sub(seat_price_cents=650), _plan(650), AT)
        self.assertEqual([l["amount_cents"] for l in lines], [50, 50])
        self.assertEqual(lines[1]["vat_cents"], 10)
        lines = prorate_seats(_sub(seat_price_cents=637), _plan(650), AT)
        self.assertEqual([l["kind"] for l in lines], ["charge"])
        lines = prorate_seats(_sub(seat_price_cents=100), _plan(100), AT)
        self.assertEqual(lines, [])

    def test_threshold(self):
        l = prorate_seats(_sub(seat_price_cents=50000), _plan(50000), START)
        self.assertEqual(l[0]["amount_cents"], 50000)
        self.assertEqual(l[0]["approved_by"], APPROVER)
        l = prorate_seats(_sub(seat_price_cents=50001), _plan(50001), START)
        self.assertEqual(l[0]["approved_by"], BIG_APPROVER)
        self.assertIsNone(l[1]["approved_by"])

    def test_trialing_and_downgrade(self):
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(), AT), [])
        self.assertEqual(prorate_seats(_sub(), _plan(999), AT), [])

    def test_equal_price_proceeds(self):
        self.assertEqual(len(prorate_seats(_sub(), _plan(1000), START)), 2)

    def test_reverse_charge(self):
        for v in ("NL123", ):
            l = prorate_seats(_sub(vat_id=v), _plan(), AT)
            self.assertEqual(l[1]["vat_cents"], 0)
        for v in ("", "   ", None):
            l = prorate_seats(_sub(vat_id=v), _plan(), AT)
            self.assertEqual(l[1]["vat_cents"], 15)

    def test_order(self):
        self.assertEqual([l["kind"] for l in prorate_seats(_sub(), _plan(), AT)],
                         ["credit", "charge"])

    def test_long_names_keep_date(self):
        for name in ("x" * 100, "Ñandú-é" * 30):
            for l in prorate_seats(_sub(plan_name=name), _plan(name=name), AT):
                self.assertEqual(len(l["description"]), 80)
                self.assertTrue(l["description"].endswith("until 2026-01-14"))
                self.assertEqual(l["description"].count("…"), 1)
        l = prorate_seats(_sub(), _plan(name="Pro"), AT)
        self.assertEqual(l[0]["description"], "Credit unused Basic until 2026-01-14")
        self.assertEqual(l[1]["description"], "Charge Pro until 2026-01-14")

    def test_billable_seats(self):
        l = prorate_seats(_sub(billable_seats=3), _plan(), START)
        self.assertEqual(l[0]["amount_cents"], 3000)

    def test_partial_day_timezone_clamp(self):
        end = datetime(2026, 1, 14, tzinfo=UTC)
        at = end - timedelta(days=12, hours=-1)  # 11d23h -> 11 days
        l = prorate_seats(_sub(), _plan(), at)
        self.assertEqual(l[0]["amount_cents"], -(-1000 * 11 // 13))
        # same instant expressed in +02:00; description date is UTC
        tz = timezone(timedelta(hours=2))
        pe = datetime(2026, 1, 14, 1, 0, tzinfo=tz)  # 2026-01-13 23:00 UTC
        l = prorate_seats(_sub(period_end=pe), _plan(), pe - timedelta(days=2, hours=1))
        self.assertEqual(l[0]["amount_cents"], -(-1000 * 2 // 13))
        self.assertTrue(l[0]["description"].endswith("2026-01-13"))
        # clamping
        early = datetime(2025, 6, 1, tzinfo=UTC)
        self.assertEqual(prorate_seats(_sub(), _plan(), early)[0]["amount_cents"], 1000)
        self.assertEqual(prorate_seats(_sub(), _plan(), end + timedelta(days=1)), [])

    def test_naive_rejected(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(), datetime(2026, 1, 13))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(period_end=datetime(2026, 1, 14)), _plan(), AT)

    def test_types(self):
        for l in prorate_seats(_sub(), _plan(), AT):
            self.assertIs(type(l["amount_cents"]), int)
            self.assertIs(type(l["vat_cents"]), int)


if __name__ == "__main__":
    unittest.main()