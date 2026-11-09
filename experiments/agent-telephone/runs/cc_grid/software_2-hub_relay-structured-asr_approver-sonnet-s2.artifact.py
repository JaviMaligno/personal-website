"""Fernhollow Studios seat proration.

Defaults for the client to confirm:
- Partial days are floored (15d23h -> 15).
- Non-trialing statuses (e.g. canceled) are prorated normally.
- amount_cents is net of VAT; vat_cents is reported separately.
- Description wording follows the R4 templates exactly.
- A skipped credit (<50 cents) does not suppress the charge, and vice versa.

NOTE: the tests below could not be executed in this environment (no tools).
Run them with: python -m unittest prorate
"""
from datetime import datetime, timedelta

_PERIOD_DAYS = 30
_MIN_CENTS = 50
_MAX_DESC = 80
_APPROVER = "Win Tee Fung Tao"
_SENIOR_APPROVER = "Ramón Etxeberria-Goñi"
_SUB_KEYS = ("id", "status", "plan_name", "seat_price_cents", "seats",
             "billable_seats", "vat_id", "period_end")


def _check_int(v, name):
    if type(v) is not int:
        raise TypeError(f"{name} must be int")
    if v < 0:
        raise ValueError(f"{name} must be non-negative")
    return v


def _check_dt(v, name):
    if not isinstance(v, datetime):
        raise TypeError(f"{name} must be datetime")
    if v.tzinfo is None or v.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return v


def _description(template, plan, date_str):
    full = template.format(plan=plan, date=date_str)
    if len(full) <= _MAX_DESC:
        return full
    plan = plan.strip()
    full = template.format(plan=plan, date=date_str)
    if len(full) <= _MAX_DESC:
        return full
    fixed = len(template.format(plan="", date=date_str))
    keep = max(_MAX_DESC - fixed - 3, 0)
    short = plan[:keep].rstrip() + "..."
    return template.format(plan=short, date=date_str)


def prorate_seats(subscription, new_plan, changed_at):
    if not isinstance(subscription, dict) or not isinstance(new_plan, dict):
        raise TypeError("subscription and new_plan must be dicts")
    for k in _SUB_KEYS:
        if k not in subscription:
            raise ValueError(f"missing subscription key: {k}")
    for k in ("name", "seat_price_cents"):
        if k not in new_plan:
            raise ValueError(f"missing new_plan key: {k}")
    old_price = _check_int(subscription["seat_price_cents"], "seat_price_cents")
    _check_int(subscription["seats"], "seats")
    billable = _check_int(subscription["billable_seats"], "billable_seats")
    new_price = _check_int(new_plan["seat_price_cents"], "new seat_price_cents")
    period_end = _check_dt(subscription["period_end"], "period_end")
    _check_dt(changed_at, "changed_at")
    old_name = subscription["plan_name"]
    new_name = new_plan["name"]
    if not isinstance(old_name, str) or not isinstance(new_name, str):
        raise TypeError("plan names must be str")
    vat_id = subscription["vat_id"]
    if vat_id is not None and not isinstance(vat_id, str):
        raise TypeError("vat_id must be str or None")

    if subscription["status"] == "trialing" or billable == 0:
        return []
    if new_price <= old_price:
        return []
    days = (period_end - changed_at) // timedelta(days=1)
    if days <= 0:
        return []
    days = min(days, _PERIOD_DAYS)

    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    out = []

    credit = -(-(old_price * billable * days) // _PERIOD_DAYS)
    if credit >= _MIN_CENTS:
        out.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(
                "Credit unused {plan} plan, period end {date}", old_name, date_str),
            "approved_by": _SENIOR_APPROVER if credit > 50000 else _APPROVER,
        })

    charge = (new_price * billable * days) // _PERIOD_DAYS
    if charge >= _MIN_CENTS:
        reverse = vat_id is not None and vat_id.strip() != ""
        out.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse else charge * 21 // 100,
            "description": _description(
                "Charge {plan} plan, period end {date}", new_name, date_str),
            "approved_by": None,
        })
    return out


# ---------------------------------------------------------------- tests
import unittest
from datetime import timezone


class ProrateTests(unittest.TestCase):
    END = datetime(2026, 1, 31, tzinfo=timezone.utc)

    def sub(self, **kw):
        s = dict(id="s1", status="active", plan_name="Basic",
                 seat_price_cents=1000, seats=5, billable_seats=5,
                 vat_id=None, period_end=self.END)
        s.update(kw)
        return s

    def run_(self, sub=None, price=2000, name="Pro", days=15, extra=timedelta(0)):
        return prorate_seats(sub or self.sub(), {"name": name, "seat_price_cents": price},
                             self.END - timedelta(days=days) - extra)

    def test_worked_example(self):
        r = self.run_()
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
        self.assertEqual((r[0]["amount_cents"], r[1]["amount_cents"]), (2500, 5000))
        self.assertEqual(r[1]["vat_cents"], 1050)
        self.assertEqual(r[0]["description"], "Credit unused Basic plan, period end 2026-01-31")
        self.assertIsNone(r[1]["approved_by"])
        self.assertEqual(r[0]["approved_by"], "Win Tee Fung Tao")

    def test_rounding_example(self):
        r = self.run_(self.sub(seat_price_cents=999, billable_seats=3), 1333, days=7)
        self.assertEqual((r[0]["amount_cents"], r[1]["amount_cents"]), (700, 933))
        self.assertEqual(r[1]["vat_cents"], 195)

    def test_49_50_boundary_credit_skipped_charge_kept(self):
        r = self.run_(self.sub(seat_price_cents=49, billable_seats=1), 100, days=30)
        self.assertEqual([x["kind"] for x in r], ["charge"])
        r = self.run_(self.sub(seat_price_cents=50, billable_seats=1), 100, days=30)
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])

    def test_approval_boundary(self):
        for price, who in ((50000, "Win Tee Fung Tao"), (50001, "Ramón Etxeberria-Goñi")):
            r = self.run_(self.sub(seat_price_cents=price, billable_seats=1), 60000, days=30)
            self.assertEqual(r[0]["amount_cents"], price)
            self.assertEqual(r[0]["approved_by"], who)

    def test_no_proration_cases(self):
        self.assertEqual(self.run_(price=500), [])
        self.assertEqual(self.run_(price=1000, name="Other"), [])
        self.assertEqual(self.run_(self.sub(status="trialing")), [])
        self.assertEqual(self.run_(self.sub(billable_seats=0)), [])
        self.assertEqual(self.run_(days=-1), [])
        self.assertEqual(self.run_(days=0), [])

    def test_canceled_prorated(self):
        self.assertEqual(len(self.run_(self.sub(status="canceled"))), 2)

    def test_reverse_charge(self):
        self.assertEqual(self.run_(self.sub(vat_id="DE123"))[1]["vat_cents"], 0)
        for v in (None, "", "  "):
            self.assertEqual(self.run_(self.sub(vat_id=v))[1]["vat_cents"], 1050)

    def test_partial_day_and_cap(self):
        r = self.run_(days=15, extra=timedelta(hours=-23))  # 15d23h
        self.assertEqual(r[0]["amount_cents"], 2500)
        r = self.run_(days=90)
        self.assertEqual(r[0]["amount_cents"], 5000)

    def test_long_and_cjk_names(self):
        for name in ("X" * 200, "日本語" * 50, "  " + "ab " * 60):
            r = self.run_(self.sub(plan_name=name), name=name)
            for x in r:
                self.assertLessEqual(len(x["description"]), 80)
                self.assertIn("2026-01-31", x["description"])
                self.assertTrue(x["description"].endswith("2026-01-31"))
                self.assertIn("...", x["description"])
                self.assertNotIn(" ...", x["description"])

    def test_types_and_seats(self):
        r = self.run_(self.sub(seats=99))
        self.assertEqual(r[0]["amount_cents"], 2500)
        for x in r:
            self.assertIs(type(x["amount_cents"]), int)
            self.assertIs(type(x["vat_cents"]), int)
            self.assertEqual(set(x), {"subscription_id", "kind", "amount_cents",
                                      "vat_cents", "description", "approved_by"})

    def test_legacy_discount_ignored_and_no_mutation(self):
        s = self.sub(legacy_discount=50)
        before = dict(s)
        self.assertEqual(self.run_(s)[0]["amount_cents"], 2500)
        self.assertEqual(s, before)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            self.run_(self.sub(period_end=datetime(2026, 1, 31)))
        with self.assertRaises((TypeError, ValueError)):
            prorate_seats(self.sub(), {"name": "P", "seat_price_cents": 2000}, datetime(2026, 1, 1))
        with self.assertRaises(TypeError):
            self.run_(self.sub(seat_price_cents=10.0))
        with self.assertRaises(TypeError):
            self.run_(self.sub(seats=True))
        with self.assertRaises(ValueError):
            self.run_(self.sub(billable_seats=-1))
        s = self.sub()
        del s["vat_id"]
        with self.assertRaises(ValueError):
            self.run_(s)


if __name__ == "__main__":
    unittest.main()