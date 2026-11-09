# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-32h54t0f/billing.py =====
# -*- coding: utf-8 -*-
"""Seat proration for plan upgrades. Integer arithmetic only.

Assumptions and ambiguities (flagged):
- Equal price and downgrade return [] (nothing to prorate / no refund policy given).
- days_left = floor((period_end - changed_at) / 1 day), clamped to 0..30. Partial days
  are dropped. Period is always 30 days. days_left <= 0 returns [].
- credit = ceil(old_total * days_left / 30); charge = floor(new_total * days_left / 30).
  These follow the spec and replace the house half-up rule. Rounding favours the customer.
- Lines with a net amount under 50 cents are skipped, each line independently.
- VAT: charges only. A non-blank vat_id means reverse charge (0). Otherwise
  charge * 21 // 100 (floored; assumption). Credits always carry vat_cents = 0, as the
  spec says. This departs from the house rule "VAT on every line, credits included";
  the explicit task instruction was followed, so please confirm with the client.
- Currency is assumed to be EUR, amounts in cents. Approver threshold: strictly > 50000.
- Descriptions use period_end.date() in its own timezone (no conversion). Only the plan
  name is truncated (with a single "…"); the date is never cut. Control characters in
  plan names are replaced by spaces and whitespace is collapsed.
- Validation raises ValueError for naive datetimes, missing keys, non-int/bool/float
  money or seat values, and negative values. Validation runs before the trialing check.
- The "seats" and "legacy_discount" fields are ignored. vat_id is optional.
- The tests were written without the ability to execute them in this session; run them
  with: python -m unittest test_billing
"""
from datetime import datetime, timedelta
import unicodedata

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
MAX_DESCRIPTION = 80
APPROVAL_THRESHOLD_CENTS = 50000
DEFAULT_APPROVER = "Win Tee Fung Tao"
SENIOR_APPROVER = "Ramón Etxeberria-Goñi"
ELLIPSIS = "…"

_DAY = timedelta(days=1)


def _ceil_div(n: int, d: int) -> int:
    return -(-n // d)


def _days_left(period_end: datetime, changed_at: datetime) -> int:
    days = (period_end - changed_at) // _DAY  # floor, integer-only
    return max(0, min(PERIOD_DAYS, days))


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _require(d, key, what):
    if not isinstance(d, dict) or key not in d:
        raise ValueError(f"missing key {key!r} in {what}")
    return d[key]


def _validate(subscription, new_plan, changed_at):
    status = _require(subscription, "status", "subscription")
    _require(subscription, "id", "subscription")
    plan_name = _require(subscription, "plan_name", "subscription")
    old_price = _require(subscription, "seat_price_cents", "subscription")
    seats = _require(subscription, "billable_seats", "subscription")
    period_end = _require(subscription, "period_end", "subscription")
    new_name = _require(new_plan, "name", "new_plan")
    new_price = _require(new_plan, "seat_price_cents", "new_plan")
    for label, v in (("old seat_price_cents", old_price),
                     ("new seat_price_cents", new_price),
                     ("billable_seats", seats)):
        if not _is_int(v):
            raise ValueError(f"{label} must be an int")
        if v < 0:
            raise ValueError(f"{label} must not be negative")
    for label, dt in (("period_end", period_end), ("changed_at", changed_at)):
        if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError(f"{label} must be a timezone-aware datetime")
    if not isinstance(plan_name, str) or not isinstance(new_name, str):
        raise ValueError("plan names must be strings")
    return status, plan_name, old_price, seats, period_end, new_name, new_price


def _clean(name: str) -> str:
    chars = [" " if unicodedata.category(c).startswith("C") else c for c in name]
    return " ".join("".join(chars).split())


def _build_description(prefix: str, plan: str, date_str: str) -> str:
    suffix = f" until {date_str}"
    room = MAX_DESCRIPTION - len(prefix) - len(suffix)
    plan = _clean(plan)
    if len(plan) > room:
        plan = plan[:room - 1] + ELLIPSIS if room >= 1 else ""
    return f"{prefix}{plan}{suffix}"


def _approver_for(amount_cents: int) -> str:
    return SENIOR_APPROVER if amount_cents > APPROVAL_THRESHOLD_CENTS else DEFAULT_APPROVER


def prorate_seats(subscription, new_plan, changed_at):
    """Return [credit, charge] invoice lines (either may be absent) for an upgrade."""
    (status, old_name, old_price, seats, period_end,
     new_name, new_price) = _validate(subscription, new_plan, changed_at)

    if status == "trialing" or new_price <= old_price or seats == 0:
        return []
    days = _days_left(period_end, changed_at)
    if days <= 0:
        return []

    sub_id = subscription["id"]
    date_str = period_end.date().isoformat()
    lines = []

    credit = _ceil_div(old_price * seats * days, PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _build_description("Credit unused ", old_name, date_str),
            "approved_by": _approver_for(credit),
        })

    charge = (new_price * seats * days) // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        vat_id = subscription.get("vat_id")
        reverse = isinstance(vat_id, str) and vat_id.strip() != ""
        vat = 0 if reverse else charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _build_description("Charge new ", new_name, date_str),
            "approved_by": None,
        })
    return lines


# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-32h54t0f/test_billing.py =====
# -*- coding: utf-8 -*-
import unittest
from datetime import datetime, timedelta, timezone

from billing import prorate_seats

END = datetime(2026, 11, 1, tzinfo=timezone.utc)


def sub(**kw):
    d = dict(id="s1", status="active", plan_name="Basic", seat_price_cents=1000,
             seats=99, billable_seats=3, vat_id=None, period_end=END)
    d.update(kw)
    return d


def plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def at(days=10, **kw):
    return END - timedelta(days=days, **kw)


class BillingTests(unittest.TestCase):
    def test_upgrade_basic_and_order(self):
        r = prorate_seats(sub(), plan(), at(10))
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
        self.assertEqual(r[0]["amount_cents"], 1000)
        self.assertEqual(r[1]["amount_cents"], 2000)
        self.assertEqual(set(r[0]), {"subscription_id", "kind", "amount_cents",
                                     "vat_cents", "description", "approved_by"})
        self.assertIsNone(r[1]["approved_by"])
        self.assertEqual(r[0]["subscription_id"], "s1")

    def test_no_lines_cases(self):
        self.assertEqual(prorate_seats(sub(), plan(500), at()), [])
        self.assertEqual(prorate_seats(sub(), plan(1000), at()), [])
        self.assertEqual(prorate_seats(sub(status="trialing"), plan(), at()), [])
        self.assertEqual(prorate_seats(sub(billable_seats=0), plan(), at()), [])

    def test_billable_seats_used(self):
        r = prorate_seats(sub(billable_seats=1), plan(), at(30))
        self.assertEqual(r[0]["amount_cents"], 1000)
        self.assertEqual(r[1]["amount_cents"], 2000)

    def test_rounding(self):
        r = prorate_seats(sub(seat_price_cents=101, billable_seats=1), plan(202), at(20))
        self.assertEqual(r[0]["amount_cents"], 68)   # 67.33 up
        self.assertEqual(r[1]["amount_cents"], 134)  # 134.67 down

    def test_independent_skip(self):
        r = prorate_seats(sub(seat_price_cents=10, billable_seats=1), plan(100), at(30))
        self.assertEqual([x["kind"] for x in r], ["charge"])
        r = prorate_seats(sub(seat_price_cents=1000, billable_seats=1), plan(1001), at(1))
        self.assertEqual(r, [])  # both under 50

    def test_threshold_50(self):
        r = prorate_seats(sub(seat_price_cents=50, billable_seats=1), plan(100), at(30))
        self.assertEqual(r[0]["amount_cents"], 50)
        r = prorate_seats(sub(seat_price_cents=49, billable_seats=1), plan(100), at(30))
        self.assertEqual([x["kind"] for x in r], ["charge"])

    def test_vat(self):
        r = prorate_seats(sub(seat_price_cents=100, billable_seats=1), plan(150), at(30))
        self.assertEqual(r[1]["amount_cents"], 150)
        self.assertEqual(r[1]["vat_cents"], 31)  # 31.5 floored
        self.assertEqual(r[0]["vat_cents"], 0)

    def test_vat_id_reverse_charge(self):
        r = prorate_seats(sub(vat_id="ES123"), plan(), at(10))
        self.assertEqual(r[1]["vat_cents"], 0)
        r = prorate_seats(sub(vat_id="   "), plan(), at(10))
        self.assertEqual(r[1]["vat_cents"], 420)

    def test_approver_threshold(self):
        s = dict(billable_seats=1)
        r = prorate_seats(sub(seat_price_cents=50000, **s), plan(60000), at(30))
        self.assertEqual(r[0]["amount_cents"], 50000)
        self.assertEqual(r[0]["approved_by"], "Win Tee Fung Tao")
        r = prorate_seats(sub(seat_price_cents=50001, **s), plan(60000), at(30))
        self.assertEqual(r[0]["approved_by"], "Ramón Etxeberria-Goñi")

    def test_description_length(self):
        long = "X" * 200
        r = prorate_seats(sub(plan_name=long), plan(name=long + "\n"), at(10))
        for line in r:
            self.assertLessEqual(len(line["description"]), 80)
            self.assertTrue(line["description"].endswith("2026-11-01"))
            self.assertNotIn("\n", line["description"])
        short = prorate_seats(sub(), plan(), at(10))
        self.assertEqual(short[1]["description"], "Charge new Pro until 2026-11-01")

    def test_past_period_end(self):
        self.assertEqual(prorate_seats(sub(), plan(), END + timedelta(hours=1)), [])
        self.assertEqual(prorate_seats(sub(), plan(), END), [])

    def test_partial_day_floor(self):
        r = prorate_seats(sub(seat_price_cents=300, billable_seats=1), plan(600),
                          END - timedelta(days=9, hours=23))
        self.assertEqual(r[0]["amount_cents"], 90)   # 9 days
        self.assertEqual(r[1]["amount_cents"], 180)

    def test_clamp_before_period_start(self):
        a = prorate_seats(sub(), plan(), at(45))
        b = prorate_seats(sub(), plan(), at(30))
        self.assertEqual(a, b)

    def test_validation(self):
        naive = datetime(2026, 10, 20)
        with self.assertRaises(ValueError):
            prorate_seats(sub(), plan(), naive)
        with self.assertRaises(ValueError):
            prorate_seats(sub(period_end=naive), plan(), at())
        with self.assertRaises(ValueError):
            prorate_seats(sub(billable_seats=-1), plan(), at())
        with self.assertRaises(ValueError):
            prorate_seats(sub(seat_price_cents=10.0), plan(), at())
        with self.assertRaises(ValueError):
            prorate_seats(sub(billable_seats=True), plan(), at())
        with self.assertRaises(ValueError):
            prorate_seats(sub(), {"name": "x"}, at())

    def test_int_types(self):
        for line in prorate_seats(sub(), plan(), at(10)):
            self.assertIs(type(line["amount_cents"]), int)
            self.assertIs(type(line["vat_cents"]), int)


if __name__ == "__main__":
    unittest.main()

# Note: I had no tool access in this session, so the tests above have NOT been run.
# Run: python -m unittest test_billing   (from the working directory)