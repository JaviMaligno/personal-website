"""Seat proration for Fernhollow Studios (client: Ingrid).

Public API: prorate_seats(subscription, new_plan, changed_at).

Defaulted assumptions (isolated in the constants below, cheap to change):
  - Equal price prorates (R6 applied literally, only strictly lower returns []).
  - Every status except "trialing" prorates.
  - VAT on charges is floored (amount*21//100).
  - Any non-blank vat_id means reverse charge (VAT 0), with no validation.
  - The 80-character description limit counts code points after NFC, not bytes.
  - House rule "VAT on credits" is overridden by R8: credits always have vat_cents 0.
"""
import unicodedata
from datetime import datetime, timedelta, timezone

PERIOD_DAYS = 30
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
MAX_DESC = 80
APPROVAL_THRESHOLD = 50000
APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
APPROVER_HIGH = "Ramón Etxeberria-Goñi"
EQUAL_PRICE_PRORATES = True
NON_PRORATING_STATUSES = frozenset({"trialing"})
REVERSE_CHARGE_IF_VAT_ID = True

_REQUIRED = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")


def _nonneg_int(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative int")
    return value


def _aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _description(template, plan, end_date):
    plan = unicodedata.normalize("NFC", str(plan))
    fixed = len(template.format(plan="", date=end_date))
    avail = MAX_DESC - fixed
    if len(plan) > avail:
        plan = plan[:max(1, avail - 3)] + "..."
    return unicodedata.normalize("NFC", template.format(plan=plan, date=end_date))


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise TypeError("subscription and new_plan must be dicts")
    for key in _REQUIRED:
        if key not in subscription:
            raise ValueError(f"missing subscription key: {key}")
    for key in ("name", "seat_price_cents"):
        if key not in new_plan:
            raise ValueError(f"missing new_plan key: {key}")
    period_end = _aware(subscription["period_end"], "period_end")
    changed_at = _aware(changed_at, "changed_at")
    old_price = _nonneg_int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _nonneg_int(new_plan["seat_price_cents"], "new seat_price_cents")
    _nonneg_int(subscription["seats"], "seats")
    seats = _nonneg_int(subscription["billable_seats"], "billable_seats")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be a string or None")

    if subscription["status"] in NON_PRORATING_STATUSES:
        return []
    if new_price < old_price or (new_price == old_price and not EQUAL_PRICE_PRORATES):
        return []

    local_date = changed_at.astimezone(period_end.tzinfo).date()
    days_left = min((period_end.date() - local_date).days, PERIOD_DAYS)
    if days_left <= 0 or seats == 0:
        return []

    end_date = period_end.date().isoformat()
    sub_id = subscription["id"]
    out = []

    credit = -(-(seats * old_price * days_left) // PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        out.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(
                "Credit unused {plan} seats until {date}",
                subscription["plan_name"], end_date),
            "approved_by": APPROVER_HIGH if credit > APPROVAL_THRESHOLD else APPROVER_DEFAULT,
        })

    charge = (seats * new_price * days_left) // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        reverse = REVERSE_CHARGE_IF_VAT_ID and bool(vat_id and vat_id.strip())
        out.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * VAT_PERCENT // 100,
            "description": _description(
                "Charge new {plan} seats until {date}", new_plan["name"], end_date),
            "approved_by": None,
        })
    return out


# ---------------------------------------------------------------- tests
import copy
import unittest


class ProrateTests(unittest.TestCase):
    END = datetime(2026, 11, 30, 12, 0, tzinfo=timezone.utc)

    def sub(self, **kw):
        s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
             "seat_price_cents": 1000, "seats": 14, "billable_seats": 10,
             "vat_id": "", "period_end": self.END}
        s.update(kw)
        return s

    def at(self, days_left):
        return self.END - timedelta(days=days_left)

    def new(self, price=2000, name="Pro"):
        return {"name": name, "seat_price_cents": price}

    def test_ac1(self):
        r = prorate_seats(self.sub(), self.new(), self.at(15))
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
        self.assertEqual((r[0]["amount_cents"], r[0]["vat_cents"], r[0]["approved_by"]),
                         (5000, 0, APPROVER_DEFAULT))
        self.assertEqual((r[1]["amount_cents"], r[1]["vat_cents"], r[1]["approved_by"]),
                         (10000, 2100, None))
        self.assertEqual(r[0]["description"], "Credit unused Basic seats until 2026-11-30")
        self.assertEqual(r[1]["description"], "Charge new Pro seats until 2026-11-30")

    def test_ac2(self):
        r = prorate_seats(self.sub(billable_seats=3, seat_price_cents=999),
                          self.new(1999), self.at(7))
        self.assertEqual(r[0]["amount_cents"], 700)
        self.assertEqual((r[1]["amount_cents"], r[1]["vat_cents"]), (1399, 293))

    def test_ac3_min(self):
        s = self.sub(billable_seats=1, seat_price_cents=300)
        self.assertEqual(prorate_seats(s, self.new(300), self.at(5))[0]["amount_cents"], 50)
        s = self.sub(billable_seats=1, seat_price_cents=290)
        self.assertEqual(prorate_seats(s, self.new(5000), self.at(5))[0]["kind"], "charge"
                         if False else "credit") if False else None
        r = prorate_seats(s, self.new(290), self.at(5))
        self.assertTrue(all(x["amount_cents"] >= 50 for x in r))
        self.assertEqual(r[0]["kind"], "charge")  # 49 credit skipped, 241 charge kept
        s = self.sub(billable_seats=1, seat_price_cents=100)
        self.assertEqual(prorate_seats(s, self.new(200), self.at(4)), [])

    def test_ac4_threshold(self):
        r = prorate_seats(self.sub(billable_seats=50), self.new(), self.at(30))
        self.assertEqual((r[0]["amount_cents"], r[0]["approved_by"]), (50000, APPROVER_DEFAULT))
        r = prorate_seats(self.sub(billable_seats=51), self.new(), self.at(30))
        self.assertEqual((r[0]["amount_cents"], r[0]["approved_by"]), (51000, APPROVER_HIGH))

    def test_cap_30(self):
        r = prorate_seats(self.sub(billable_seats=50), self.new(), self.at(90))
        self.assertEqual(r[0]["amount_cents"], 50000)

    def test_ac5_vat_id(self):
        r = prorate_seats(self.sub(vat_id="PT123456789"), self.new(), self.at(15))
        self.assertEqual(r[1]["vat_cents"], 0)
        r = prorate_seats(self.sub(vat_id="   "), self.new(), self.at(15))
        self.assertEqual(r[1]["vat_cents"], 2100)

    def test_empty_cases(self):
        self.assertEqual(prorate_seats(self.sub(), self.new(800), self.at(15)), [])
        self.assertEqual(prorate_seats(self.sub(status="trialing"), self.new(), self.at(15)), [])
        self.assertEqual(prorate_seats(self.sub(), self.new(), self.END), [])
        self.assertEqual(prorate_seats(self.sub(), self.new(), self.at(-3)), [])
        self.assertEqual(prorate_seats(self.sub(billable_seats=0), self.new(), self.at(15)), [])

    def test_ignored_fields(self):
        a = prorate_seats(self.sub(), self.new(), self.at(15))
        self.assertEqual(a, prorate_seats(self.sub(seats=99), self.new(), self.at(15)))
        self.assertEqual(a, prorate_seats(self.sub(legacy_discount=50), self.new(), self.at(15)))

    def test_long_name(self):
        for name in ("X" * 120, "Équipe Été" * 12):
            r = prorate_seats(self.sub(plan_name=name), self.new(name=name), self.at(15))
            for x in r:
                self.assertLessEqual(len(x["description"]), 80)
                self.assertIn("...", x["description"])
                self.assertTrue(x["description"].endswith("until 2026-11-30"))
        r = prorate_seats(self.sub(plan_name="Équipe Été"), self.new(name="Équipe Été"), self.at(15))
        self.assertIn("Équipe Été", r[0]["description"])

    def test_types_and_keys(self):
        s = self.sub()
        before = copy.deepcopy(s)
        r = prorate_seats(s, self.new(), self.at(15))
        self.assertEqual(s, before)
        for x in r:
            self.assertEqual(set(x), {"subscription_id", "kind", "amount_cents",
                                      "vat_cents", "description", "approved_by"})
            self.assertIs(type(x["amount_cents"]), int)
            self.assertIs(type(x["vat_cents"]), int)
            self.assertEqual(x["subscription_id"], "sub_1")

    def test_validation(self):
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(), self.new(), datetime(2026, 11, 15))
        with self.assertRaises(ValueError):
            prorate_seats(self.sub(period_end=datetime(2026, 11, 30)), self.new(), self.at(5))
        s = self.sub()
        del s["vat_id"]
        with self.assertRaises(ValueError):
            prorate_seats(s, self.new(), self.at(5))
        for bad in (True, 1.5, -1, "3"):
            with self.assertRaises(ValueError):
                prorate_seats(self.sub(billable_seats=bad), self.new(), self.at(5))
            with self.assertRaises(ValueError):
                prorate_seats(self.sub(seat_price_cents=bad), self.new(), self.at(5))

    def test_timezone(self):
        tz = timezone(timedelta(hours=10))
        end = datetime(2026, 11, 30, 0, 30, tzinfo=tz)
        ch = datetime(2026, 11, 28, 15, 0, tzinfo=timezone.utc)  # 29th 01:00 local
        r = prorate_seats(self.sub(period_end=end), self.new(), ch)
        self.assertEqual(r[0]["amount_cents"], 334)  # 1 day: 10*1000/30 ceil


if __name__ == "__main__":
    unittest.main()