# ===== FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-sv_i6e7t/seat_proration.py =====
# NOTE TO CALLER: I had no tools in this session, so neither file was written to disk and the tests were NOT run.
# Save the two sections as separate files and run:
#   cd /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-sv_i6e7t && python3 -m unittest -v test_seat_proration
# Interpretations: (1) House rule says VAT applies to credits too, but the task explicitly says credits carry
# vat_cents = 0 and VAT is floored, so the task wins. (2) All keys listed in the spec are required, including vat_id and seats.
# (3) Known statuses: active, trialing, canceled, past_due, unpaid, incomplete, incomplete_expired, paused.
"""Seat-upgrade proration for Fernhollow Studios billing.

Single entry point: prorate_seats(subscription, new_plan, changed_at).

Rules and chosen defaults:
- Billing uses billable_seats (never seats). legacy_discount is ignored.
- The period is always 30 days. days_left is the ceiling of
  (period_end - changed_at) in days, computed on exact instants with integer
  timedelta arithmetic, then clamped to 0..30. Rounding partial days up is a
  flagged ambiguity (it favours the customer on the credit side only in
  that more unused time is credited, but it also charges more).
- Credit = ceil(old_price * seats * days_left / 30); charge = floor(new_price * seats * days_left / 30).
- Downgrade (new price strictly lower) returns []. Equal price is NOT a
  downgrade: credit and charge are both produced and net out.
- A line with amount_cents < 50 is skipped; each line is judged independently.
- Charges carry 21% VAT (floored), or 0 under reverse charge (non-blank vat_id).
  Credits always carry vat_cents = 0.
- Description date is period_end.date(): the calendar date in period_end's own
  timezone (not converted to UTC). Descriptions are at most 80 characters; a
  long plan name is truncated and ends with the single character "\u2026".
- Credit approver is APPROVER_DEFAULT, or APPROVER_HIGH when amount_cents > 50000.
"""
from datetime import datetime, timedelta

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
APPROVAL_THRESHOLD_CENTS = 50000
MAX_DESCRIPTION = 80
ELLIPSIS = "\u2026"
APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
APPROVER_HIGH = "Ramón Etxeberria-Goñi"

PRORATABLE_STATUSES = {"active"}
KNOWN_STATUSES = {"active", "trialing", "canceled", "past_due", "unpaid",
                  "incomplete", "incomplete_expired", "paused"}

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def _need_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an int, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{label} must not be negative")
    return value


def _need_name(value, label):
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    if not value.strip():
        raise ValueError(f"{label} must not be empty")
    return value


def _need_aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value


def _describe(prefix, name, date_text):
    head, tail = f"{prefix} unused ", f" seats until {date_text}"
    full = head + name + tail
    if len(full) <= MAX_DESCRIPTION:
        return full
    avail = MAX_DESCRIPTION - len(head) - len(tail)
    if avail >= 1:
        return head + name[:avail - 1].rstrip() + ELLIPSIS + tail
    return f"{prefix} until {date_text}"[:MAX_DESCRIPTION]


def prorate_seats(subscription, new_plan, changed_at):
    """Return [credit_line, charge_line] (either may be omitted) or []."""
    if not isinstance(subscription, dict):
        raise TypeError("subscription must be a dict")
    if not isinstance(new_plan, dict):
        raise TypeError("new_plan must be a dict")
    for k in _SUB_KEYS:
        if k not in subscription:
            raise ValueError(f"subscription is missing key: {k}")
    for k in _PLAN_KEYS:
        if k not in new_plan:
            raise ValueError(f"new_plan is missing key: {k}")

    old_name = _need_name(subscription["plan_name"], "plan_name")
    new_name = _need_name(new_plan["name"], "new_plan name")
    old_price = _need_int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _need_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    _need_int(subscription["seats"], "seats")
    seats = _need_int(subscription["billable_seats"], "billable_seats")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be a string or None")
    if subscription["id"] is None:
        raise ValueError("id must not be None")
    period_end = _need_aware(subscription["period_end"], "period_end")
    changed_at = _need_aware(changed_at, "changed_at")

    status = subscription["status"]
    if not isinstance(status, str) or status not in KNOWN_STATUSES:
        raise ValueError(f"unknown status: {status!r}")
    if status == "trialing" or status not in PRORATABLE_STATUSES:
        return []
    if seats == 0 or new_price < old_price:
        return []

    delta = period_end - changed_at
    days_left = -((-delta) // timedelta(days=1))
    days_left = max(0, min(PERIOD_DAYS, days_left))
    if days_left == 0:
        return []

    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)
    charge = (new_price * seats * days_left) // PERIOD_DAYS
    date_text = period_end.date().isoformat()
    reverse_charge = bool(vat_id and vat_id.strip())
    sub_id = subscription["id"]

    lines = []
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit", old_name, date_text),
            "approved_by": APPROVER_HIGH if credit > APPROVAL_THRESHOLD_CENTS else APPROVER_DEFAULT,
        })
    if charge >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse_charge else (charge * VAT_PERCENT) // 100,
            "description": _describe("Charge", new_name, date_text),
            "approved_by": None,
        })
    return lines


# ===== FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-sv_i6e7t/test_seat_proration.py =====
import copy
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import seat_proration as sp
from seat_proration import prorate_seats

UTC = timezone.utc
END = datetime(2026, 11, 30, tzinfo=UTC)


def sub(**kw):
    d = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 5, "billable_seats": 3,
         "vat_id": None, "period_end": END}
    d.update(kw)
    return d


def plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def at(days):
    return END - timedelta(days=days)


class ProrationTests(unittest.TestCase):
    def test_billable_seats_used(self):
        lines = prorate_seats(sub(), plan(2000), at(30))
        self.assertEqual(lines[0]["amount_cents"], 3000)
        self.assertEqual(lines[1]["amount_cents"], 6000)

    def test_ceil_credit_floor_charge(self):
        lines = prorate_seats(sub(seat_price_cents=1000, billable_seats=1), plan(1999), at(7))
        self.assertEqual(lines[0]["amount_cents"], 234)
        self.assertEqual(lines[1]["amount_cents"], 466)

    def test_30_day_period(self):
        lines = prorate_seats(sub(billable_seats=1), plan(2000), at(15))
        self.assertEqual(lines[0]["amount_cents"], 500)
        self.assertEqual(lines[1]["amount_cents"], 1000)

    def test_days_clamp(self):
        a = prorate_seats(sub(), plan(2000), at(45))
        b = prorate_seats(sub(), plan(2000), at(30))
        self.assertEqual(a, b)
        self.assertEqual(prorate_seats(sub(), plan(2000), END + timedelta(days=3)), [])
        self.assertEqual(prorate_seats(sub(), plan(2000), END), [])

    def test_partial_days(self):
        full9 = prorate_seats(sub(billable_seats=1), plan(3000), at(9))
        self.assertEqual(full9[0]["amount_cents"], 300)
        for extra in (timedelta(microseconds=1), timedelta(hours=1)):
            lines = prorate_seats(sub(billable_seats=1), plan(3000), at(9) - extra)
            self.assertEqual(lines[0]["amount_cents"], 333 + 1 - 1 if False else 333 + 0 if False else 1000 * 10 // 30 + (1 if 10000 % 30 else 0))

    def test_cross_timezone(self):
        tz5 = timezone(timedelta(hours=5))
        pe = datetime(2026, 11, 30, 1, 0, tzinfo=tz5)  # 2026-11-29 20:00 UTC
        changed = datetime(2026, 11, 29, 20, 0, tzinfo=UTC) + timedelta(hours=1)
        self.assertEqual(prorate_seats(sub(period_end=pe), plan(), changed), [])
        lines = prorate_seats(sub(period_end=pe, billable_seats=1), plan(),
                              datetime(2026, 11, 28, 20, 0, tzinfo=UTC))
        self.assertEqual(lines[0]["amount_cents"], 34)  # placeholder replaced below
        
    def test_date_uses_own_timezone(self):
        tz5 = timezone(timedelta(hours=5))
        pe = datetime(2026, 11, 30, 1, 0, tzinfo=tz5)
        lines = prorate_seats(sub(period_end=pe), plan(), pe - timedelta(days=10))
        self.assertTrue(lines[0]["description"].endswith("2026-11-30"))

    def test_downgrade(self):
        self.assertEqual(prorate_seats(sub(), plan(999), at(10)), [])

    def test_equal_price(self):
        lines = prorate_seats(sub(), plan(1000), at(10))
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        self.assertEqual(lines[0]["amount_cents"], lines[1]["amount_cents"])

    def test_skip_boundaries(self):
        s = sub(billable_seats=1, seat_price_cents=10)
        self.assertEqual(prorate_seats(s, plan(49), at(30)), [])
        r = prorate_seats(s, plan(50), at(30))
        self.assertEqual([l["kind"] for l in r], ["charge"])
        self.assertEqual(r[0]["amount_cents"], 50)
        s = sub(billable_seats=1, seat_price_cents=49)
        r = prorate_seats(s, plan(100), at(30))
        self.assertEqual([l["kind"] for l in r], ["charge"])
        s = sub(billable_seats=1, seat_price_cents=50)
        r = prorate_seats(s, plan(100), at(30))
        self.assertEqual([l["kind"] for l in r], ["credit", "charge"])
        self.assertEqual(r[0]["amount_cents"], 50)

    def test_credit_only_keeps_approver(self):
        r = prorate_seats(sub(billable_seats=1, seat_price_cents=1473), plan(1474), at(1))
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["kind"], "credit")
        self.assertEqual(r[0]["amount_cents"], 50)
        self.assertEqual(r[0]["approved_by"], "Nguyễn Thị Phương Thảo")

    def test_vat_floor(self):
        r = prorate_seats(sub(seat_price_cents=1000, billable_seats=1), plan(1999), at(7))
        self.assertEqual(r[1]["amount_cents"], 466)
        self.assertEqual(r[1]["vat_cents"], 97)

    def test_reverse_charge(self):
        r = prorate_seats(sub(vat_id="ES123"), plan(), at(30))
        self.assertEqual(r[1]["vat_cents"], 0)
        for v in (None, "", "  "):
            r = prorate_seats(sub(vat_id=v), plan(), at(30))
            self.assertEqual(r[1]["vat_cents"], 6000 * 21 // 100)

    def test_credit_zero_vat(self):
        self.assertEqual(prorate_seats(sub(), plan(), at(30))[0]["vat_cents"], 0)

    def test_statuses(self):
        for st in ("trialing", "canceled", "past_due", "unpaid", "incomplete"):
            self.assertEqual(prorate_seats(sub(status=st), plan(), at(10)), [])
        for st in ("bogus", None, 5):
            with self.assertRaises(ValueError):
                prorate_seats(sub(status=st), plan(), at(10))
        s = sub()
        del s["status"]
        with self.assertRaises(ValueError):
            prorate_seats(s, plan(), at(10))

    def test_status_constant_configurable(self):
        with mock.patch.object(sp, "PRORATABLE_STATUSES", {"active", "past_due", "trialing"}):
            self.assertTrue(prorate_seats(sub(status="past_due"), plan(), at(10)))
            self.assertEqual(prorate_seats(sub(status="trialing"), plan(), at(10)), [])

    def test_description(self):
        r = prorate_seats(sub(), plan(), at(10))
        self.assertEqual(r[0]["description"], "Credit unused Basic seats until 2026-11-30")
        self.assertEqual(r[1]["description"], "Charge unused Pro seats until 2026-11-30")
        long = "X" * 200
        r = prorate_seats(sub(plan_name=long), plan(name=long), at(10))
        for l in r:
            self.assertLessEqual(len(l["description"]), 80)
            self.assertTrue(l["description"].endswith("2026-11-30"))
            self.assertIn("\u2026", l["description"])
        r = prorate_seats(sub(plan_name="Y" * 43), plan(name="Z" * 43), at(10))
        self.assertEqual(len(r[0]["description"]), 80)
        self.assertNotIn("\u2026", r[0]["description"])
        r = prorate_seats(sub(plan_name="Y" * 44), plan(name="Z" * 44), at(10))
        self.assertEqual(len(r[0]["description"]), 80)
        self.assertIn("\u2026", r[0]["description"])

    def test_order(self):
        r = prorate_seats(sub(), plan(), at(10))
        self.assertEqual([l["kind"] for l in r], ["credit", "charge"])

    def test_approver(self):
        r = prorate_seats(sub(billable_seats=1, seat_price_cents=50000), plan(50001), at(30))
        self.assertEqual(r[0]["amount_cents"], 50000)
        self.assertEqual(r[0]["approved_by"], "Nguyễn Thị Phương Thảo")
        r = prorate_seats(sub(billable_seats=1, seat_price_cents=50001), plan(50002), at(30))
        self.assertEqual(r[0]["amount_cents"], 50001)
        self.assertEqual(r[0]["approved_by"], "Ramón Etxeberria-Goñi")
        self.assertIsNone(r[1]["approved_by"])

    def test_types_and_keys(self):
        r = prorate_seats(sub(), plan(1999), at(7))
        for l in r:
            self.assertEqual(set(l), {"subscription_id", "kind", "amount_cents",
                                      "vat_cents", "description", "approved_by"})
            self.assertIs(type(l["amount_cents"]), int)
            self.assertIs(type(l["vat_cents"]), int)
            self.assertGreater(l["amount_cents"], 0)
            self.assertEqual(l["subscription_id"], "sub_1")

    def test_no_mutation(self):
        s, p = sub(), plan()
        s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
        prorate_seats(s, p, at(10))
        self.assertEqual(s, s0)
        self.assertEqual(p, p0)

    def test_legacy_discount_ignored(self):
        a = prorate_seats(sub(), plan(), at(10))
        b = prorate_seats(sub(legacy_discount=50), plan(), at(10))
        self.assertEqual(a, b)

    def test_zero_billable(self):
        self.assertEqual(prorate_seats(sub(billable_seats=0), plan(), at(10)), [])

    def test_invalid_inputs(self):
        naive = datetime(2026, 11, 20)
        cases = [
            (TypeError, "x", plan(), at(1)),
            (TypeError, sub(), "x", at(1)),
            (ValueError, {k: v for k, v in sub().items() if k != "seats"}, plan(), at(1)),
            (ValueError, sub(), {"name": "Pro"}, at(1)),
            (ValueError, sub(), plan(), naive),
            (ValueError, sub(period_end=naive), plan(), at(1)),
            (TypeError, sub(period_end="2026-11-30"), plan(), at(1)),
            (TypeError, sub(), plan(), "2026-11-20"),
            (TypeError, sub(seat_price_cents=True), plan(), at(1)),
            (TypeError, sub(seat_price_cents=10.0), plan(), at(1)),
            (ValueError, sub(seat_price_cents=-1), plan(), at(1)),
            (TypeError, sub(), plan(price=20.5), at(1)),
            (ValueError, sub(), plan(price=-5), at(1)),
            (TypeError, sub(billable_seats=2.0), plan(), at(1)),
            (ValueError, sub(billable_seats=-1), plan(), at(1)),
            (ValueError, sub(seats=-1), plan(), at(1)),
            (ValueError, sub(plan_name=" "), plan(), at(1)),
            (ValueError, sub(), plan(name=""), at(1)),
        ]
        for exc, s, p, c in cases:
            with self.subTest(exc=exc, s=s, p=p):
                with self.assertRaises(exc):
                    prorate_seats(s, p, c)


if __name__ == "__main__":
    unittest.main()