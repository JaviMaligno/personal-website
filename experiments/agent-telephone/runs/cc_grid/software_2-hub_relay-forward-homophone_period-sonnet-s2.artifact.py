"""Seat upgrade proration for Fernhollow Studios.

Entry point: prorate_seats(subscription, new_plan, changed_at).

Assumptions (to be confirmed with the client):
- Integer math only. Credit = ceil(old_price * billable_seats * days_left / 13);
  charge = floor(new_price * billable_seats * days_left / 13). The
  billable_seats field is used, never seats. legacy_discount is ignored.
- Returns [] if status is "trialing", if new price < old price (downgrade),
  if prices are equal, or if days_left <= 0. days_left is clamped to 13.
- days_left = whole calendar days from changed_at to period_end, both
  expressed in period_end's timezone. Naive datetimes raise ValueError.
  Missing keys or negative/non-int values raise ValueError. The key "seats"
  is not required, since it is never used.
- Each line is skipped independently if its pre-VAT amount_cents < 50.
  Credit amount_cents is a positive magnitude.
- Charge VAT = floor(21% of the charge amount); 0 if vat_id is non-blank
  after stripping. Credits always have vat_cents 0. This deliberately
  overrides the house rule "VAT on every line" and the half-up rounding
  rule, as the brief explicitly says credits carry no VAT and amounts
  round in the customer's favour.
- Credit approved_by is "Nguyễn Thị Phương Thảo", or "Ramón Etxeberria-Goñi"
  if the credit amount_cents > 50000 (strictly over EUR 500). Charges: None.
- Credit line first, then charge line.
- Descriptions: "Credit unused {old_plan} until YYYY-MM-DD" and
  "Charge {new_plan} until YYYY-MM-DD", max 80 characters. Only the plan
  name is shortened (ending in an ellipsis); the date is always kept.
- Worked example: old 1000, new 1500, 3 billable seats, 5 days left ->
  credit 1154, charge 1730 with VAT 363.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

PERIOD_DAYS = 13
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
MAX_DESC = 80
APPROVER = "Nguyễn Thị Phương Thảo"
BIG_APPROVER = "Ramón Etxeberria-Goñi"
BIG_CREDIT_CENTS = 50000


def _int(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative int")
    return value


def _aware(value, name):
    if not isinstance(value, datetime) or value.tzinfo is None \
            or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value


def _get(d, key, what):
    if not isinstance(d, dict) or key not in d:
        raise ValueError(f"missing key {key!r} in {what}")
    return d[key]


def _describe(prefix, plan, date_str):
    suffix = f" until {date_str}"
    avail = MAX_DESC - len(prefix) - len(suffix)
    if len(plan) > avail:
        plan = plan[:max(avail - 1, 0)] + "…" if avail >= 1 else ""
    return f"{prefix}{plan}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    sub_id = _get(subscription, "id", "subscription")
    status = _get(subscription, "status", "subscription")
    old_name = _get(subscription, "plan_name", "subscription")
    old_price = _int(_get(subscription, "seat_price_cents", "subscription"),
                     "seat_price_cents")
    seats = _int(_get(subscription, "billable_seats", "subscription"),
                 "billable_seats")
    vat_id = _get(subscription, "vat_id", "subscription")
    period_end = _aware(_get(subscription, "period_end", "subscription"),
                        "period_end")
    new_name = _get(new_plan, "name", "new_plan")
    new_price = _int(_get(new_plan, "seat_price_cents", "new_plan"),
                     "new_plan seat_price_cents")
    _aware(changed_at, "changed_at")

    if status == "trialing" or new_price <= old_price:
        return []

    tz = period_end.tzinfo
    days_left = (period_end.date()
                 - changed_at.astimezone(tz).date()).days
    if days_left <= 0:
        return []
    days_left = min(days_left, PERIOD_DAYS)

    date_str = period_end.date().isoformat()
    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)
    charge = (new_price * seats * days_left) // PERIOD_DAYS

    lines = []
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit unused ", str(old_name),
                                     date_str),
            "approved_by": BIG_APPROVER if credit > BIG_CREDIT_CENTS
            else APPROVER,
        })
    if charge >= MIN_LINE_CENTS:
        reverse = isinstance(vat_id, str) and bool(vat_id.strip())
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * VAT_PERCENT // 100,
            "description": _describe("Charge ", str(new_name), date_str),
            "approved_by": None,
        })
    return lines


class ProrateTests(unittest.TestCase):
    def sub(self, **kw):
        s = {"id": "s1", "status": "active", "plan_name": "Basic",
             "seat_price_cents": 1000, "seats": 9, "billable_seats": 3,
             "vat_id": None,
             "period_end": datetime(2026, 10, 18, 12, tzinfo=timezone.utc)}
        s.update(kw)
        return s

    NEW = {"name": "Pro", "seat_price_cents": 1500}
    AT = datetime(2026, 10, 13, 9, tzinfo=timezone.utc)

    def test_worked_example(self):
        c, ch = prorate_seats(self.sub(), self.NEW, self.AT)
        self.assertEqual((c["kind"], c["amount_cents"], c["vat_cents"]),
                         ("credit", 1154, 0))
        self.assertEqual((ch["kind"], ch["amount_cents"], ch["vat_cents"]),
                         ("charge", 1730, 363))
        self.assertEqual(c["approved_by"], APPROVER)
        self.assertIsNone(ch["approved_by"])
        self.assertEqual(c["description"], "Credit unused Basic until 2026-10-18")

    def test_reverse_charge(self):
        lines = prorate_seats(self.sub(vat_id=" NL123 "), self.NEW, self.AT)
        self.assertEqual(lines[1]["vat_cents"], 0)
        lines = prorate_seats(self.sub(vat_id="  "), self.NEW, self.AT)
        self.assertEqual(lines[1]["vat_cents"], 363)

    def test_no_lines(self):
        self.assertEqual(prorate_seats(self.sub(status="trialing"),
                                       self.NEW, self.AT), [])
        self.assertEqual(prorate_seats(
            self.sub(), {"name": "x", "seat_price_cents": 900}, self.AT), [])
        self.assertEqual(prorate_seats(
            self.sub(), {"name": "x", "seat_price_cents": 1000}, self.AT), [])
        self.assertEqual(prorate_seats(
            self.sub(), self.NEW, datetime(2026, 10, 18, 1, tzinfo=timezone.utc)), [])

    def test_clamp_and_big_credit(self):
        at = self.AT - timedelta(days=30)
        c, ch = prorate_seats(self.sub(billable_seats=50), self.NEW, at)
        self.assertEqual(c["amount_cents"], 50000)
        self.assertEqual(c["approved_by"], APPROVER)
        c, _ = prorate_seats(self.sub(billable_seats=51), self.NEW, at)
        self.assertEqual(c["approved_by"], BIG_APPROVER)

    def test_small_lines_skipped_independently(self):
        s = self.sub(seat_price_cents=1, billable_seats=1)
        lines = prorate_seats(s, {"name": "P", "seat_price_cents": 130},
                              self.AT)
        self.assertEqual([l["kind"] for l in lines], ["charge"])

    def test_timezone(self):
        tz = timezone(timedelta(hours=10))
        s = self.sub(period_end=datetime(2026, 10, 18, 12, tzinfo=tz))
        at = datetime(2026, 10, 12, 20, tzinfo=timezone.utc)  # 13th local
        c, _ = prorate_seats(s, self.NEW, at)
        self.assertEqual(c["amount_cents"], 1154)

    def test_description_truncation(self):
        long = "Ä" * 100
        c, ch = prorate_seats(self.sub(plan_name=long),
                              {"name": long, "seat_price_cents": 1500},
                              self.AT)
        for l in (c, ch):
            self.assertEqual(len(l["description"]), 80)
            self.assertTrue(l["description"].endswith(" until 2026-10-18"))
            self.assertIn("…", l["description"])

    def test_validation(self):
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), self.NEW, datetime(2026, 10, 13))
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(period_end=datetime(2026, 10, 18)),
                          self.NEW, self.AT)
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(billable_seats=-1), self.NEW, self.AT)
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(billable_seats=2.0), self.NEW, self.AT)
        s = self.sub()
        del s["plan_name"]
        with self.assertRaises(ValueError):
            prorate_seats(s, self.NEW, self.AT)
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), {"name": "x"}, self.AT)


if __name__ == "__main__":
    unittest.main()