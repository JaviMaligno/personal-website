"""Seat-upgrade proration for Fernhollow Studios.

Public entry point: prorate_seats(subscription, new_plan, changed_at).

Chosen defaults (to be confirmed with the client):
  * days_left is the whole-day floor of (period_end - changed_at), clamped to
    0..30. A period is always 30 days.
  * Credit is rounded up (ceiling) and charge rounded down (floor), in integer
    arithmetic only. Charge VAT (21%) is rounded down.
  * amount_cents is always a positive net figure for both kinds.
  * Credits always carry vat_cents 0 (the explicit spec overrides the generic
    house rule that VAT applies to credit lines).
  * Statuses other than "trialing" are prorated.
  * Equal price still prorates; a strictly cheaper new plan returns [].
  * The 50 cent minimum is applied to each line independently (50 is kept).
  * The legacy_discount field and the seats field are ignored.
  * A non-empty (after strip) vat_id means reverse charge, so VAT is 0.
  * Long plan names are shortened with a trailing "..." so descriptions stay
    within 80 characters; the date is never shortened.

Run the tests with: python proration.py
"""
import unicodedata
from datetime import datetime, timedelta

_PERIOD_DAYS = 30
_MIN_LINE_CENTS = 50
_APPROVAL_LIMIT_CENTS = 50000
_VAT_PERCENT = 21
_MAX_DESC = 80
_APPROVER = unicodedata.normalize("NFC", "Nguyễn Thị Phương Thảo")
_APPROVER_HIGH = unicodedata.normalize("NFC", "Ramón Etxeberria-Goñi")

_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents",
             "billable_seats", "vat_id", "period_end")
_PLAN_KEYS = ("name", "seat_price_cents")


def _count(value, label):
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative int")
    return value


def _aware(value, label):
    if (not isinstance(value, datetime) or value.tzinfo is None
            or value.utcoffset() is None):
        raise ValueError(f"{label} must be a timezone-aware datetime")
    return value


def _description(template, plan, date_text):
    full = template.format(plan=plan, date=date_text)
    if len(full) <= _MAX_DESC:
        return full
    room = _MAX_DESC - len(template.format(plan="", date=date_text))
    keep = max(room - 3, 0)
    return template.format(plan=plan[:keep] + "...", date=date_text)


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise ValueError("subscription and new_plan must be dicts")
    for key in _SUB_KEYS:
        if key not in subscription:
            raise ValueError(f"subscription missing key: {key}")
    for key in _PLAN_KEYS:
        if key not in new_plan:
            raise ValueError(f"new_plan missing key: {key}")
    old_price = _count(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _count(new_plan["seat_price_cents"], "new seat_price_cents")
    seats = _count(subscription["billable_seats"], "billable_seats")
    if "seats" in subscription and subscription["seats"] is not None:
        _count(subscription["seats"], "seats")
    _aware(changed_at, "changed_at")
    period_end = _aware(subscription["period_end"], "period_end")
    old_name = subscription["plan_name"]
    new_name = new_plan["name"]
    if not isinstance(old_name, str) or not isinstance(new_name, str):
        raise ValueError("plan names must be strings")
    if not isinstance(subscription["status"], str):
        raise ValueError("status must be a string")

    if new_price < old_price:
        return []
    if subscription["status"] == "trialing":
        return []
    if seats == 0:
        return []
    delta = period_end - changed_at
    if delta <= timedelta(0):
        return []
    days_left = min(delta // timedelta(days=1), _PERIOD_DAYS)
    if days_left <= 0:
        return []

    credit = -(-(old_price * seats * days_left) // _PERIOD_DAYS)
    charge = (new_price * seats * days_left) // _PERIOD_DAYS

    date_text = period_end.date().isoformat()
    vat_id = subscription["vat_id"]
    reverse_charge = vat_id is not None and str(vat_id).strip() != ""
    sub_id = subscription["id"]
    lines = []
    if credit >= _MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(
                "Unused time credit - {plan} - period ends {date}",
                old_name, date_text),
            "approved_by": (_APPROVER_HIGH if credit > _APPROVAL_LIMIT_CENTS
                            else _APPROVER),
        })
    if charge >= _MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse_charge else charge * _VAT_PERCENT // 100,
            "description": _description(
                "Prorated seat charge - {plan} - period ends {date}",
                new_name, date_text),
            "approved_by": None,
        })
    return lines


# ---------------------------------------------------------------- tests
import copy
import unittest
from datetime import timezone


class ProrationTests(unittest.TestCase):
    NOW = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)

    def sub(self, price=1000, billable=1, days=30, **kw):
        s = {"id": "sub_1", "status": "active", "plan_name": "Studio",
             "seat_price_cents": price, "seats": billable,
             "billable_seats": billable, "vat_id": "",
             "period_end": self.NOW + timedelta(days=days)}
        s.update(kw)
        return s

    def plan(self, price=1500, name="Studio Plus"):
        return {"name": name, "seat_price_cents": price}

    def test_basic_example(self):
        r = prorate_seats(self.sub(999, 3, 7), self.plan(1499), self.NOW)
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
        self.assertEqual(r[0]["amount_cents"], 700)
        self.assertEqual(r[0]["vat_cents"], 0)
        self.assertEqual(r[0]["approved_by"], _APPROVER)
        self.assertEqual(r[1]["amount_cents"], 1049)
        self.assertEqual(r[1]["vat_cents"], 220)
        self.assertIsNone(r[1]["approved_by"])

    def test_reverse_charge(self):
        s = self.sub(1000, 10, 15, vat_id=" NL123 ")
        r = prorate_seats(s, self.plan(1500), self.NOW)
        self.assertEqual(r[0]["amount_cents"], 5000)
        self.assertEqual(r[1]["amount_cents"], 7500)
        self.assertEqual(r[1]["vat_cents"], 0)

    def test_whitespace_vat_id_is_absent(self):
        r = prorate_seats(self.sub(1000, 1, 30, vat_id="  "),
                          self.plan(1500), self.NOW)
        self.assertEqual(r[1]["vat_cents"], 315)

    def test_uses_billable_seats(self):
        s = self.sub(1000, 8, 30, seats=12)
        r = prorate_seats(s, self.plan(1000), self.NOW)
        self.assertEqual(r[0]["amount_cents"], 8000)

    def test_empty_cases(self):
        self.assertEqual(prorate_seats(self.sub(1000), self.plan(999), self.NOW), [])
        self.assertEqual(prorate_seats(self.sub(status="trialing"), self.plan(), self.NOW), [])
        self.assertEqual(prorate_seats(self.sub(days=0), self.plan(), self.NOW), [])
        self.assertEqual(prorate_seats(self.sub(billable=0), self.plan(), self.NOW), [])
        s = self.sub()
        s["period_end"] = self.NOW + timedelta(hours=23)
        self.assertEqual(prorate_seats(s, self.plan(), self.NOW), [])
        s["period_end"] = self.NOW - timedelta(days=3)
        self.assertEqual(prorate_seats(s, self.plan(), self.NOW), [])

    def test_other_status_prorates_and_clamp(self):
        r = prorate_seats(self.sub(1000, 1, 90, status="past_due"),
                          self.plan(1000), self.NOW)
        self.assertEqual(r[0]["amount_cents"], 1000)

    def test_minimum_line(self):
        r = prorate_seats(self.sub(49), self.plan(100), self.NOW)
        self.assertEqual([x["kind"] for x in r], ["charge"])
        r = prorate_seats(self.sub(50), self.plan(100), self.NOW)
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
        self.assertEqual(r[0]["amount_cents"], 50)

    def test_approver_threshold(self):
        r = prorate_seats(self.sub(50000), self.plan(50000), self.NOW)
        self.assertEqual(r[0]["approved_by"], _APPROVER)
        r = prorate_seats(self.sub(50001), self.plan(50001), self.NOW)
        self.assertEqual(r[0]["approved_by"], _APPROVER_HIGH)
        self.assertEqual(r[0]["approved_by"],
                         unicodedata.normalize("NFC", r[0]["approved_by"]))

    def test_long_names(self):
        s = self.sub(plan_name="A" * 200)
        r = prorate_seats(s, self.plan(name="B" * 200), self.NOW)
        for line in r:
            self.assertLessEqual(len(line["description"]), 80)
            self.assertIn("2026-11-24", line["description"])
            self.assertIn("...", line["description"])

    def test_short_description(self):
        r = prorate_seats(self.sub(), self.plan(), self.NOW)
        self.assertEqual(r[0]["description"],
                         "Unused time credit - Studio - period ends 2026-11-24")

    def test_ints_keys_no_mutation_legacy(self):
        s = self.sub(999, 3, 7)
        p = self.plan(1499)
        before = copy.deepcopy((s, p))
        base = prorate_seats(s, p, self.NOW)
        self.assertEqual((s, p), before)
        s2 = dict(s, legacy_discount=50)
        self.assertEqual(prorate_seats(s2, p, self.NOW), base)
        for line in base:
            self.assertEqual(set(line), {"subscription_id", "kind", "amount_cents",
                                         "vat_cents", "description", "approved_by"})
            self.assertIs(type(line["amount_cents"]), int)
            self.assertIs(type(line["vat_cents"]), int)

    def test_validation(self):
        naive = datetime(2026, 10, 25)
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), self.plan(), naive)
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(period_end=naive), self.plan(), self.NOW)
        s = self.sub()
        del s["vat_id"]
        with self.assertRaises(ValueError):
            prorate_seats(s, self.plan(), self.NOW)
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), {"name": "x"}, self.NOW)
        for bad in (True, 1.5, -1, "3"):
            with self.assertRaises(ValueError):
                prorate_seats(self.sub(billable_seats=bad), self.plan(), self.NOW)
            with self.assertRaises(ValueError):
                prorate_seats(self.sub(seat_price_cents=bad), self.plan(), self.NOW)
            with self.assertRaises(ValueError):
                prorate_seats(self.sub(), self.plan(bad), self.NOW)


if __name__ == "__main__":
    unittest.main()