"""Seat upgrade proration for Fernhollow Studios billing.

Entry point: prorate_seats(subscription, new_plan, changed_at).

Notes for the client / open questions:
  1. Equal per-seat price (plan change, not cheaper): prorated normally, credit and charge. Confirm.
  2. Statuses other than "active" (past_due, canceled, paused...): return no lines.
     "trialing" is explicitly no proration. Confirm the others.
  3. VAT rounding: charge VAT = floor(amount * 21 / 100), i.e. never in our favour.
     Confirm floor is wanted rather than half-up.
  4. Description wording ("Credit unused {plan} until YYYY-MM-DD",
     "Charge {plan} until YYYY-MM-DD") was chosen by us. Confirm. Plan names that
     are too long are cut and end with an ellipsis; the date is never cut.
  Also: the house rule "VAT on every line, credits included" conflicts with the
  brief ("credits never carry VAT"). The brief wins: credits have vat_cents 0.
  The tests below were written without being executed in this environment.
"""
from datetime import datetime

_PERIOD_DAYS = 30
_MIN_LINE_CENTS = 50
_VAT_PERCENT = 21
_MAX_DESC = 80
_BIG_CREDIT_CENTS = 50000
_APPROVER = "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"
_APPROVER_BIG = "Ram\u00f3n Etxeberria-Go\u00f1i"


def _need(d, key, what):
    if not isinstance(d, dict) or key not in d:
        raise ValueError(f"missing key {key!r} in {what}")
    return d[key]


def _cents(v, name, allow_zero=True):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0 or (v == 0 and not allow_zero):
        raise ValueError(f"invalid {name}: {v!r}")
    return v


def _aware(v, name):
    if not isinstance(v, datetime) or v.tzinfo is None or v.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return v


def _description(prefix, plan, date_str):
    suffix = f" until {date_str}"
    text = f"{prefix}{plan}{suffix}"
    if len(text) <= _MAX_DESC:
        return text
    room = _MAX_DESC - len(prefix) - len(suffix)
    return f"{prefix}{plan[:room - 1]}\u2026{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    sub_id = _need(subscription, "id", "subscription")
    status = _need(subscription, "status", "subscription")
    old_name = _need(subscription, "plan_name", "subscription")
    old_price = _cents(_need(subscription, "seat_price_cents", "subscription"), "seat_price_cents")
    seats = _cents(_need(subscription, "billable_seats", "subscription"), "billable_seats")
    vat_id = _need(subscription, "vat_id", "subscription")
    period_end = _aware(_need(subscription, "period_end", "subscription"), "period_end")
    new_name = _need(new_plan, "name", "new_plan")
    new_price = _cents(_need(new_plan, "seat_price_cents", "new_plan"), "new_plan seat_price_cents")
    _aware(changed_at, "changed_at")
    if not isinstance(old_name, str) or not isinstance(new_name, str):
        raise ValueError("plan names must be strings")

    if status != "active" or seats == 0 or new_price < old_price:
        return []

    local_change = changed_at.astimezone(period_end.tzinfo)
    days = (period_end.date() - local_change.date()).days
    days = max(0, min(_PERIOD_DAYS, days))
    if days <= 0:
        return []

    date_str = period_end.date().isoformat()
    credit = -(-(old_price * seats * days) // _PERIOD_DAYS)
    charge = (new_price * seats * days) // _PERIOD_DAYS
    reverse_charge = vat_id.strip() != "" if isinstance(vat_id, str) else bool(vat_id)

    lines = []
    if credit >= _MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit unused ", old_name, date_str),
            "approved_by": _APPROVER_BIG if credit > _BIG_CREDIT_CENTS else _APPROVER,
        })
    if charge >= _MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if reverse_charge else charge * _VAT_PERCENT // 100,
            "description": _description("Charge ", new_name, date_str),
            "approved_by": None,
        })
    return lines


# ---------------------------------------------------------------- tests
import copy
import unittest
from datetime import timedelta, timezone

UTC = timezone.utc


def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic", "seat_price_cents": 1000,
         "seats": 5, "billable_seats": 3, "vat_id": "", "period_end": datetime(2026, 11, 11, tzinfo=UTC)}
    s.update(kw)
    return s


def _run(days=10, sub=None, new_price=1500, new_name="Pro"):
    end = datetime(2026, 11, 11, tzinfo=UTC)
    return prorate_seats(sub or _sub(), {"name": new_name, "seat_price_cents": new_price},
                         end - timedelta(days=days))


class ProrateTests(unittest.TestCase):
    def test_worked_example(self):
        lines = _run()
        self.assertEqual([l["kind"] for l in lines], ["credit", "charge"])
        c, ch = lines
        self.assertEqual((c["amount_cents"], c["vat_cents"], c["approved_by"]), (1000, 0, _APPROVER))
        self.assertEqual((ch["amount_cents"], ch["vat_cents"], ch["approved_by"]), (1500, 315, None))
        self.assertEqual(c["description"], "Credit unused Basic until 2026-11-11")
        self.assertEqual(ch["description"], "Charge Pro until 2026-11-11")
        self.assertEqual(set(c), {"subscription_id", "kind", "amount_cents", "vat_cents",
                                  "description", "approved_by"})
        for l in lines:
            self.assertIs(type(l["amount_cents"]), int)
            self.assertIs(type(l["vat_cents"]), int)
            self.assertEqual(l["subscription_id"], "sub_1")

    def test_rounding(self):
        lines = _run(days=7, sub=_sub(billable_seats=1), new_price=1999)
        self.assertEqual(lines[0]["amount_cents"], 234)
        self.assertEqual(lines[1]["amount_cents"], 466)
        self.assertEqual(lines[1]["vat_cents"], 97)

    def test_threshold(self):
        s = _sub(seat_price_cents=100, billable_seats=1)
        self.assertEqual(_run(14, s, 100), [])
        lines = _run(15, s, 100)
        self.assertEqual([l["amount_cents"] for l in lines], [50, 50])

    def test_one_line_survives(self):
        lines = _run(14, _sub(seat_price_cents=100, billable_seats=1), 200)
        self.assertEqual([(l["kind"], l["amount_cents"]) for l in lines], [("charge", 93)])

    def test_approver_boundary(self):
        s = _sub(seat_price_cents=5000, billable_seats=10)
        self.assertEqual(_run(30, s, 6000)[0]["amount_cents"], 50000)
        self.assertEqual(_run(30, s, 6000)[0]["approved_by"], _APPROVER)
        s = _sub(seat_price_cents=5001, billable_seats=10)
        l = _run(30, s, 6000)[0]
        self.assertEqual((l["amount_cents"], l["approved_by"]), (50010, _APPROVER_BIG))

    def test_approver_exact_text(self):
        self.assertEqual(_APPROVER, "Nguyễn Thị Phương Thảo")
        self.assertEqual(_APPROVER_BIG, "Ramón Etxeberria-Goñi")

    def test_vat_id_reverse_charge(self):
        self.assertEqual(_run(sub=_sub(vat_id="PT123"))[1]["vat_cents"], 0)
        self.assertEqual(_run(sub=_sub(vat_id="   "))[1]["vat_cents"], 315)
        self.assertEqual(_run(sub=_sub(vat_id=None))[1]["vat_cents"], 315)

    def test_no_lines_cases(self):
        self.assertEqual(_run(new_price=900), [])
        self.assertEqual(_run(sub=_sub(status="trialing")), [])
        self.assertEqual(_run(sub=_sub(status="canceled")), [])
        self.assertEqual(_run(sub=_sub(billable_seats=0)), [])
        self.assertEqual(_run(days=0), [])
        self.assertEqual(_run(days=-3), [])

    def test_equal_price_prorated(self):
        self.assertEqual(len(_run(new_price=1000)), 2)

    def test_uses_billable_not_seats(self):
        self.assertEqual(_run(sub=_sub(seats=100))[0]["amount_cents"], 1000)

    def test_clamp_to_30(self):
        s = _sub(seat_price_cents=3000, billable_seats=1)
        self.assertEqual(_run(60, s, 3000)[0]["amount_cents"], 3000)

    def test_timezone_uses_period_end_tz(self):
        tz = timezone(timedelta(hours=-5))
        s = _sub(seat_price_cents=3000, billable_seats=1, period_end=datetime(2026, 11, 10, 23, tzinfo=tz))
        lines = prorate_seats(s, {"name": "Pro", "seat_price_cents": 3000},
                              datetime(2026, 11, 1, 3, tzinfo=UTC))
        self.assertEqual(lines[0]["amount_cents"], 1000)  # 10 days (Oct 31 local)
        self.assertTrue(lines[0]["description"].endswith("2026-11-10"))

    def test_long_name_truncated_keeps_date(self):
        lines = _run(sub=_sub(plan_name="X" * 200), new_name="Y" * 200)
        for l in lines:
            self.assertEqual(len(l["description"]), 80)
            self.assertTrue(l["description"].endswith("\u2026 until 2026-11-11"))
        self.assertTrue(lines[0]["description"].startswith("Credit unused XXX"))

    def test_non_ascii_names(self):
        name = "Ünïcödé계획" * 15
        lines = _run(sub=_sub(plan_name=name), new_name="Équipe Ω")
        self.assertEqual(len(lines[0]["description"]), 80)
        self.assertIn("Ünïcödé계획", lines[0]["description"])
        self.assertEqual(lines[1]["description"], "Charge Équipe Ω until 2026-11-11")

    def test_exact_80_not_truncated(self):
        room = 80 - len("Charge ") - len(" until 2026-11-11")
        d = _run(new_name="N" * room)[1]["description"]
        self.assertEqual(len(d), 80)
        self.assertNotIn("\u2026", d)

    def test_validation(self):
        end = datetime(2026, 11, 11, tzinfo=UTC)
        np = {"name": "Pro", "seat_price_cents": 1500}
        at = end - timedelta(days=5)
        bad = [
            (_sub(period_end=datetime(2026, 11, 11)), np, at),
            (_sub(), np, datetime(2026, 11, 6)),
            (_sub(seat_price_cents=10.5), np, at),
            (_sub(seat_price_cents=-1), np, at),
            (_sub(seat_price_cents=True), np, at),
            (_sub(billable_seats=-1), np, at),
            (_sub(billable_seats=2.0), np, at),
            (_sub(), {"name": "Pro", "seat_price_cents": 1.5}, at),
            (_sub(), {"seat_price_cents": 1500}, at),
            (_sub(), {"name": "Pro"}, at),
        ]
        for k in ("id", "status", "plan_name", "seat_price_cents", "billable_seats", "vat_id", "period_end"):
            s = _sub()
            del s[k]
            bad.append((s, np, at))
        for s, n, a in bad:
            with self.assertRaises(ValueError):
                prorate_seats(s, n, a)

    def test_inputs_not_mutated(self):
        s, n = _sub(), {"name": "Pro", "seat_price_cents": 1500}
        s0, n0 = copy.deepcopy(s), copy.deepcopy(n)
        prorate_seats(s, n, datetime(2026, 11, 1, tzinfo=UTC))
        self.assertEqual((s, n), (s0, n0))


if __name__ == "__main__":
    unittest.main()