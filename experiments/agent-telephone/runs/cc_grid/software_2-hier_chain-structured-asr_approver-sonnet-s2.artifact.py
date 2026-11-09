# -*- coding: utf-8 -*-
# NOTE: written without tool access; the tests below were NOT executed.
# Run with: python3 -I prorate.py   (runs the embedded unittest suite)
# Spec precedence: R7 (ceil/floor) and R10 (credit VAT = 0) override the house defaults
# of half-up rounding and VAT on credits.
from datetime import datetime, timedelta, timezone

_PERIOD_DAYS = 30
_MIN_LINE_CENTS = 50
_VAT_PCT = 21
_APPROVER = "Win Tee Fung Tao"
_APPROVER_HIGH = "Ramón Etxeberria-Goñi"
_APPROVAL_LIMIT = 50000
_MAX_DESC = 80


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _check_aware(name, dt):
    if not isinstance(dt, datetime):
        raise TypeError(f"{name} must be a datetime")
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _days_left(period_end, changed_at):  # R5
    td = period_end - changed_at
    secs = td.days * 86400 + td.seconds
    return max(0, min(_PERIOD_DAYS, secs // 86400))


def _description(template, name, date):  # R3, R12
    overhead = len(template.format(name="", date=date))
    avail = _MAX_DESC - overhead
    if len(name) > avail:
        avail = max(avail, 0)
        name = name[:avail - 3] + "..." if avail >= 3 else name[:avail]
    return template.format(name=name, date=date)


def prorate_seats(subscription, new_plan, changed_at):  # R1
    _check_aware("changed_at", changed_at)
    period_end = subscription["period_end"]
    _check_aware("period_end", period_end)

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    seats = subscription["billable_seats"]  # R4
    for label, v in (("old seat_price_cents", old_price),
                     ("new seat_price_cents", new_price)):
        if not _is_int(v):
            raise TypeError(f"{label} must be an int, got {type(v).__name__}")
    if not _is_int(seats):
        raise TypeError("billable_seats must be an int")
    if seats < 0:
        raise ValueError("billable_seats must be >= 0")

    if subscription.get("status") == "trialing":  # R11
        return []
    if new_price <= old_price:  # R6
        return []

    days = _days_left(period_end, changed_at)
    date = period_end.date().isoformat()
    result = []

    credit = -(-(old_price * seats * days) // _PERIOD_DAYS)  # R7
    if credit >= _MIN_LINE_CENTS:  # R8
        result.append({
            "subscription_id": subscription["id"],
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,  # R10
            "description": _description(
                "Credit unused {name} seats until {date}",
                str(subscription["plan_name"]), date),
            "approved_by": _APPROVER_HIGH if credit > _APPROVAL_LIMIT else _APPROVER,  # R13
        })

    charge = (new_price * seats * days) // _PERIOD_DAYS  # R7
    if charge >= _MIN_LINE_CENTS:
        vat_id = subscription.get("vat_id")
        has_vat_id = bool(str(vat_id).strip()) if vat_id is not None else False
        result.append({
            "subscription_id": subscription["id"],
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if has_vat_id else (charge * _VAT_PCT) // 100,  # R9
            "description": _description(
                "Charge unused {name} seats until {date}",
                str(new_plan["name"]), date),
            "approved_by": None,
        })
    return result  # R15: credit first


if __name__ == "__main__":
    import copy
    import unittest

    UTC = timezone.utc
    END = datetime(2025, 3, 31, 12, 0, tzinfo=UTC)

    def sub(**kw):
        d = dict(id="s1", status="active", plan_name="Basic", seat_price_cents=1000,
                 seats=99, billable_seats=7, vat_id=None, period_end=END)
        d.update(kw)
        return d

    def plan(price, name="Pro"):
        return {"name": name, "seat_price_cents": price}

    def at(days, extra=timedelta(0)):
        return END - timedelta(days=days) - extra

    class T(unittest.TestCase):
        def test_A(self):  # R4 R5 R9 R10 R13
            r = prorate_seats(sub(), plan(2000), at(15))
            self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
            self.assertEqual((r[0]["amount_cents"], r[0]["vat_cents"], r[0]["approved_by"]),
                             (3500, 0, "Win Tee Fung Tao"))
            self.assertEqual((r[1]["amount_cents"], r[1]["vat_cents"], r[1]["approved_by"]),
                             (7000, 1470, None))
            self.assertEqual(set(r[0]), {"subscription_id", "kind", "amount_cents",
                                         "vat_cents", "description", "approved_by"})
            self.assertEqual(r[0]["description"], "Credit unused Basic seats until 2025-03-31")
            self.assertEqual(r[1]["description"], "Charge unused Pro seats until 2025-03-31")

        def test_B(self):  # R7
            r = prorate_seats(sub(seat_price_cents=1001, billable_seats=1), plan(1002), at(17))
            self.assertEqual((r[0]["amount_cents"], r[1]["amount_cents"], r[1]["vat_cents"]),
                             (568, 567, 119))

        def test_C(self):  # R9
            r = prorate_seats(sub(vat_id="PT123456789"), plan(2000), at(15))
            self.assertEqual(r[1]["vat_cents"], 0)
            for v in (None, "", "   "):
                r = prorate_seats(sub(vat_id=v), plan(2000), at(15))
                self.assertEqual(r[1]["vat_cents"], 1470)

        def test_D(self):  # R6 R11
            self.assertEqual(prorate_seats(sub(), plan(500), at(15)), [])
            self.assertEqual(prorate_seats(sub(), plan(1000), at(15)), [])
            self.assertEqual(prorate_seats(sub(status="trialing"), plan(2000), at(15)), [])
            self.assertTrue(prorate_seats(sub(status="cancelled"), plan(2000), at(15)))

        def test_E(self):  # R13
            r = prorate_seats(sub(seat_price_cents=10000, billable_seats=6), plan(20000), at(30))
            self.assertEqual((r[0]["amount_cents"], r[0]["approved_by"]),
                             (60000, "Ramón Etxeberria-Goñi"))
            r = prorate_seats(sub(seat_price_cents=5000, billable_seats=10), plan(6000), at(30))
            self.assertEqual((r[0]["amount_cents"], r[0]["approved_by"]),
                             (50000, "Win Tee Fung Tao"))
            r = prorate_seats(sub(seat_price_cents=50001, billable_seats=1), plan(60000), at(30))
            self.assertEqual(r[0]["approved_by"], "Ramón Etxeberria-Goñi")

        def test_F(self):  # R8
            # credit raw 49*30 -> 49 skipped; charge 50 kept
            r = prorate_seats(sub(seat_price_cents=49, billable_seats=1), plan(50), at(30))
            self.assertEqual([(x["kind"], x["amount_cents"]) for x in r], [("charge", 50)])
            r = prorate_seats(sub(seat_price_cents=50, billable_seats=1), plan(51), at(30))
            self.assertEqual([x["kind"] for x in r], ["credit", "charge"])

        def test_G(self):  # R5
            r = prorate_seats(sub(), plan(2000), at(30, timedelta(hours=12)))
            self.assertEqual(r[0]["amount_cents"], 7000)
            r = prorate_seats(sub(), plan(2000), at(12, timedelta(hours=23)))
            self.assertEqual(r[0]["amount_cents"], 7000 * 12 // 30)
            self.assertEqual(prorate_seats(sub(), plan(2000), END + timedelta(days=1)), [])
            self.assertEqual(prorate_seats(sub(), plan(2000), END), [])

        def test_H(self):  # R12
            r = prorate_seats(sub(plan_name="x" * 100), plan(2000, "y" * 100), at(15))
            for x in r:
                self.assertLessEqual(len(x["description"]), 80)
                self.assertTrue(x["description"].endswith("until 2025-03-31"))
                self.assertIn("...", x["description"])
            self.assertEqual(r[0]["kind"], "credit")

        def test_I(self):  # R1 R16
            with self.assertRaises(ValueError):
                prorate_seats(sub(), plan(2000), datetime(2025, 3, 1))
            s, p = sub(), plan(2000)
            s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
            r = prorate_seats(s, p, at(15))
            self.assertEqual((s, p), (s0, p0))
            for x in r:
                self.assertIs(type(x["amount_cents"]), int)
                self.assertIs(type(x["vat_cents"]), int)
            with self.assertRaises(TypeError):
                prorate_seats(sub(seat_price_cents=10.0), plan(2000), at(15))
            with self.assertRaises(TypeError):
                prorate_seats(sub(), plan(True), at(15))
            with self.assertRaises(ValueError):
                prorate_seats(sub(billable_seats=-1), plan(2000), at(15))

    unittest.main()