"""Fernhollow Studios seat proration.

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list[dict]

Assumptions:
- seat_price_cents is per seat per 30-day period; a period is always 30 days.
- Currency is EUR.
- The 50-cent threshold applies to the net amount (before VAT), per line.
- VAT (21%) rounds down and is computed on the final amount_cents.
- days_left uses UTC calendar dates of changed_at and period_end, capped at 30.
- Equal price prorates normally; statuses other than "trialing" prorate normally.
- Credits always have vat_cents 0. This explicit rule overrides the house rule
  "VAT applies to every invoice line, credits included".
- A vat_id that is None, empty or whitespace-only counts as absent.
- No floats are used; all arithmetic is integer.

Points to flag to the client:
- The 50-cent skip rule also drops small credits, which favours the company and
  is in tension with the never-round-in-our-favour principle.
- The VAT rounding, days_left timezone, cap at 30, equal-price and
  other-status behaviours are our assumptions, not confirmed requirements.

Run tests with: python seat_proration.py
"""
from datetime import datetime, timezone, timedelta
import unittest

__all__ = ["prorate_seats"]

_PERIOD_DAYS = 30
_MIN_CENTS = 50
_VAT_PERCENT = 21
_DESC_MAX = 80
_APPROVER = "Win Tee Fung Tao"
_SENIOR_APPROVER = "Ramón Etxeberria-Goñi"
_SENIOR_THRESHOLD = 50000


def _int(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an int, got {value!r}")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    return value


def _aware(value, name):
    if not isinstance(value, datetime) or value.tzinfo is None \
            or value.tzinfo.utcoffset(value) is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _description(prefix, name, date_str):
    suffix = f" until {date_str}"
    available = _DESC_MAX - len(prefix) - len(suffix)
    if available < 1:
        raise ValueError("description template too long")
    if len(name) > available:
        name = name[:available - 1] + "\u2026" if available > 1 else "\u2026"
    return f"{prefix}{name}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    """Return proration lines (credit first, then charge) for a plan change."""
    for key in ("id", "status", "plan_name", "seat_price_cents", "seats",
                "billable_seats", "vat_id", "period_end"):
        if key not in subscription:
            raise KeyError(f"subscription missing key: {key}")
    for key in ("name", "seat_price_cents"):
        if key not in new_plan:
            raise KeyError(f"new_plan missing key: {key}")

    old_price = _int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    _int(subscription["seats"], "seats")
    seats = _int(subscription["billable_seats"], "billable_seats")
    changed_utc = _aware(changed_at, "changed_at")
    end_utc = _aware(subscription["period_end"], "period_end")

    if subscription["status"] == "trialing":
        return []
    if new_price < old_price:
        return []

    days_left = min((end_utc.date() - changed_utc.date()).days, _PERIOD_DAYS)
    if days_left <= 0:
        return []

    credit = -(-(old_price * seats * days_left) // _PERIOD_DAYS)
    charge = (new_price * seats * days_left) // _PERIOD_DAYS

    date_str = end_utc.date().isoformat()
    sub_id = subscription["id"]
    vat_id = subscription["vat_id"]
    has_vat_id = bool(vat_id.strip()) if isinstance(vat_id, str) else bool(vat_id)

    lines = []
    if credit >= _MIN_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(
                "Credit: unused ", str(subscription["plan_name"]), date_str),
            "approved_by": _SENIOR_APPROVER if credit > _SENIOR_THRESHOLD
            else _APPROVER,
        })
    if charge >= _MIN_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if has_vat_id else charge * _VAT_PERCENT // 100,
            "description": _description(
                "Charge: ", str(new_plan["name"]), date_str),
            "approved_by": None,
        })
    return lines


# ----------------------------------------------------------------- tests
_NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 1, "billable_seats": 1,
         "vat_id": None, "period_end": _NOW + timedelta(days=7)}
    s.update(kw)
    return s


def _plan(price, name="Pro"):
    return {"name": name, "seat_price_cents": price}


class ProrateTests(unittest.TestCase):
    def test_1_rounding_and_order(self):
        r = prorate_seats(_sub(), _plan(1001), _NOW)
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
        self.assertEqual([x["amount_cents"] for x in r], [234, 233])

    def test_2_vat_and_approval(self):
        s = _sub(billable_seats=3, period_end=_NOW + timedelta(days=15))
        c, h = prorate_seats(s, _plan(2000), _NOW)
        self.assertEqual((c["amount_cents"], c["vat_cents"], c["approved_by"]),
                         (1500, 0, "Win Tee Fung Tao"))
        self.assertEqual((h["amount_cents"], h["vat_cents"], h["approved_by"]),
                         (3000, 630, None))

    def test_3_vat_id(self):
        s = _sub(billable_seats=3, vat_id="DE123",
                 period_end=_NOW + timedelta(days=15))
        self.assertEqual(prorate_seats(s, _plan(2000), _NOW)[1]["vat_cents"], 0)

    def test_4_billable_seats(self):
        s = _sub(seats=10, billable_seats=4, period_end=_NOW + timedelta(days=30))
        self.assertEqual(prorate_seats(s, _plan(1000), _NOW)[0]["amount_cents"],
                         4000)

    def test_5_approval_threshold(self):
        e = _NOW + timedelta(days=30)
        a = prorate_seats(_sub(seat_price_cents=50000, period_end=e),
                          _plan(100000), _NOW)[0]
        b = prorate_seats(_sub(seat_price_cents=50001, period_end=e),
                          _plan(100000), _NOW)[0]
        self.assertEqual(a["approved_by"], "Win Tee Fung Tao")
        self.assertEqual(b["approved_by"], "Ramón Etxeberria-Goñi")

    def test_6_threshold(self):
        e = _NOW + timedelta(days=30)
        self.assertEqual(prorate_seats(_sub(seat_price_cents=49, period_end=e),
                                       _plan(49), _NOW), [])
        r = prorate_seats(_sub(seat_price_cents=50, period_end=e),
                          _plan(50), _NOW)
        self.assertEqual(len(r), 2)
        r = prorate_seats(_sub(seat_price_cents=49, period_end=e),
                          _plan(1000), _NOW)
        self.assertEqual([x["kind"] for x in r], ["charge"])

    def test_7_downgrade_trialing(self):
        self.assertEqual(prorate_seats(_sub(), _plan(999), _NOW), [])
        self.assertEqual(prorate_seats(_sub(status="trialing"), _plan(2000), _NOW),
                         [])

    def test_8_long_names(self):
        s = _sub(plan_name="A" * 200)
        for x in prorate_seats(s, _plan(2000, "B" * 200), _NOW):
            self.assertLessEqual(len(x["description"]), 80)
            self.assertTrue(x["description"].endswith("2026-01-08"))
            self.assertIn("\u2026", x["description"])

    def test_9_ints_and_legacy_discount(self):
        base = prorate_seats(_sub(), _plan(2000), _NOW)
        other = prorate_seats(_sub(legacy_discount=50), _plan(2000), _NOW)
        self.assertEqual(base, other)
        for x in base:
            for k in ("amount_cents", "vat_cents"):
                self.assertIs(type(x[k]), int)

    def test_cap_and_nonpositive(self):
        a = prorate_seats(_sub(period_end=_NOW + timedelta(days=45)),
                          _plan(2000), _NOW)
        b = prorate_seats(_sub(period_end=_NOW + timedelta(days=30)),
                          _plan(2000), _NOW)
        self.assertEqual([x["amount_cents"] for x in a],
                         [x["amount_cents"] for x in b])
        self.assertEqual(prorate_seats(_sub(period_end=_NOW), _plan(2000), _NOW), [])
        self.assertEqual(prorate_seats(
            _sub(period_end=_NOW - timedelta(days=1)), _plan(2000), _NOW), [])

    def test_utc_dates(self):
        tz = timezone(timedelta(hours=-5))
        ch = datetime(2026, 1, 1, 23, 0, tzinfo=tz)  # Jan 2 04:00 UTC
        s = _sub(seat_price_cents=3000,
                 period_end=datetime(2026, 1, 31, tzinfo=timezone.utc))
        self.assertEqual(prorate_seats(s, _plan(3000), ch)[0]["amount_cents"], 2900)

    def test_invalid_and_no_mutation(self):
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(2000), datetime(2026, 1, 1))
        with self.assertRaises(ValueError):
            prorate_seats(_sub(seat_price_cents=-1), _plan(2000), _NOW)
        with self.assertRaises(ValueError):
            prorate_seats(_sub(), _plan(-5), _NOW)
        s = _sub()
        del s["vat_id"]
        with self.assertRaises(KeyError):
            prorate_seats(s, _plan(2000), _NOW)
        s = _sub()
        snap = dict(s)
        prorate_seats(s, _plan(2000), _NOW)
        self.assertEqual(s, snap)


if __name__ == "__main__":
    unittest.main()