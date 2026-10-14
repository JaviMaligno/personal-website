# ===== FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-g1c_mjhb/seat_billing.py =====
# NOTE: this reply was produced without tool access. Neither file was written to
# disk and the tests were NOT run. Run them yourself, for example:
#   python3 -I -m unittest discover -s <dir> -p 'test_*.py'
"""Seat-upgrade billing for Fernhollow Studios.

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list of dicts.

Documented assumptions:
 A. The minimum-line threshold applies to the net amount (before VAT), to each
    line independently. Credit and charge are never netted. If only one
    survives, only that one is returned (credit first if both survive).
 B. Time left is computed exactly in integer microseconds. remaining =
    period_end - changed_at. remaining <= 0 gives []. More than 30 days is
    clamped to 30 days. Amount = price * billable_seats * remaining_us /
    (30 days in us), rounded once at the end (credits up, charges down).
    WHOLE_DAYS_ONLY=True floors the remaining time to whole days first.
 C. "Over EUR 500" means strictly greater than 50000 cents.
 D. Equal price is not a downgrade and prorates (EQUAL_PRICE_PRORATES).
 E. Charge VAT = floor(net_charge_cents * 21 / 100) on the rounded net charge.
 F. status "trialing" gives []; "active" and "past_due" prorate; any other
    status raises ValueError.
 G. The description date is period_end.date() in period_end's own timezone.
 H. Validation: every validation failure (missing keys, wrong types, bad
    values, naive datetimes, non-mapping inputs) raises ValueError, consistently.
    Validation runs before the trialing/downgrade shortcuts. vat_id may be
    None, a string or absent; blank/whitespace counts as no VAT id.
    billable_seats == 0 gives []. Inputs are never mutated.
 Ignored fields: legacy_discount and seats (only billable_seats is used).
"""
from datetime import datetime, timedelta
from collections.abc import Mapping

# --- Tunable assumptions -----------------------------------------------------
MIN_LINE_CENTS = 50                 # lines with net amount below this are dropped
VAT_RATE_PERCENT = 21               # VAT on charges, whole percent
DAYS_IN_PERIOD = 30                 # a billing period is always this many days
APPROVAL_THRESHOLD_CENTS = 50000    # credits strictly above this need the senior approver
APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"
APPROVER_SENIOR = "Ramón Etxeberria-Goñi"
MAX_DESCRIPTION_LEN = 80            # max characters in a description
WHOLE_DAYS_ONLY = False             # True: floor remaining time to whole days
EQUAL_PRICE_PRORATES = True         # False: equal price is treated like a downgrade
ALLOWED_STATUSES = ("active", "past_due")   # statuses that prorate
TRIAL_STATUS = "trialing"                   # status that returns []

_US = timedelta(microseconds=1)
_DAY_US = 86400 * 10**6
_PERIOD_US = DAYS_IN_PERIOD * _DAY_US


def _fail(msg):
    raise ValueError(msg)


def _need(mapping, name, keys):
    if not isinstance(mapping, Mapping):
        _fail(f"{name} must be a mapping")
    for k in keys:
        if k not in mapping:
            _fail(f"{name} is missing required key {k!r}")


def _nonempty_str(v, what):
    if not isinstance(v, str) or not v.strip():
        _fail(f"{what} must be a non-empty string")


def _nonneg_int(v, what):
    if type(v) is not int or v < 0:
        _fail(f"{what} must be a non-negative int")


def _aware(v, what):
    if not isinstance(v, datetime) or v.tzinfo is None or v.utcoffset() is None:
        _fail(f"{what} must be a timezone-aware datetime")


def _vat_cents(net_cents, vat_id):
    """VAT for a charge line (isolated from the credit path)."""
    if isinstance(vat_id, str) and vat_id.strip():
        return 0  # reverse charge
    return net_cents * VAT_RATE_PERCENT // 100


def _description(template, plan, date_str):
    text = template.format(plan=plan, date=date_str)
    if len(text) <= MAX_DESCRIPTION_LEN:
        return text
    room = MAX_DESCRIPTION_LEN - len(template.format(plan="", date=date_str))
    short = plan[: max(room - 3, 0)] + "..."
    return template.format(plan=short, date=date_str)


def prorate_seats(subscription, new_plan, changed_at):
    _need(subscription, "subscription",
          ("id", "status", "plan_name", "seat_price_cents", "billable_seats", "period_end"))
    _need(new_plan, "new_plan", ("name", "seat_price_cents"))
    _nonempty_str(subscription["id"], "subscription id")
    _nonempty_str(subscription["status"], "status")
    _nonempty_str(subscription["plan_name"], "plan_name")
    _nonempty_str(new_plan["name"], "new_plan name")
    _nonneg_int(subscription["seat_price_cents"], "seat_price_cents")
    _nonneg_int(subscription["billable_seats"], "billable_seats")
    _nonneg_int(new_plan["seat_price_cents"], "new_plan seat_price_cents")
    _aware(changed_at, "changed_at")
    _aware(subscription["period_end"], "period_end")
    vat_id = subscription.get("vat_id")
    if vat_id is not None and not isinstance(vat_id, str):
        _fail("vat_id must be None or a string")

    status = subscription["status"]
    if status != TRIAL_STATUS and status not in ALLOWED_STATUSES:
        _fail(f"unsupported status {status!r}")
    if status == TRIAL_STATUS:
        return []

    seats = subscription["billable_seats"]
    if seats == 0:
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []
    if new_price == old_price and not EQUAL_PRICE_PRORATES:
        return []

    period_end = subscription["period_end"]
    remaining = (period_end - changed_at) // _US
    if remaining <= 0:
        return []
    remaining = min(remaining, _PERIOD_US)
    if WHOLE_DAYS_ONLY:
        remaining = remaining // _DAY_US * _DAY_US

    credit = -(-(old_price * seats * remaining) // _PERIOD_US)  # ceil
    charge = (new_price * seats * remaining) // _PERIOD_US      # floor

    date_str = period_end.date().isoformat()
    sid = subscription["id"]
    lines = []
    if credit >= MIN_LINE_CENTS:
        approver = (APPROVER_SENIOR if credit > APPROVAL_THRESHOLD_CENTS
                    else APPROVER_DEFAULT)
        lines.append({
            "subscription_id": sid,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit unused {plan} seats until {date}",
                                        subscription["plan_name"], date_str),
            "approved_by": approver,
        })
    if charge >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sid,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": _vat_cents(charge, vat_id),
            "description": _description("Charge {plan} seats until {date}",
                                        new_plan["name"], date_str),
            "approved_by": None,
        })
    return lines


# ===== FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-g1c_mjhb/test_seat_billing.py =====
import copy
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import seat_billing as sb

UTC = timezone.utc
PE = datetime(2025, 6, 30, tzinfo=UTC)
THAO = "Nguyễn Thị Phương Thảo"
RAMON = "Ramón Etxeberria-Goñi"


def sub(**over):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "seats": 10, "billable_seats": 10,
         "vat_id": None, "period_end": PE, "legacy_discount": 0}
    s.update(over)
    return s


def plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def at(delta, end=PE):
    return end - delta


class TestProration(unittest.TestCase):
    def test_exact_15_days(self):  # rules 1, 2
        r = sb.prorate_seats(sub(), plan(), at(timedelta(days=15)))
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
        self.assertEqual(r[0]["amount_cents"], 5000)    # 1000*10/2
        self.assertEqual(r[1]["amount_cents"], 10000)   # 2000*10/2
        self.assertEqual(r[1]["vat_cents"], 2100)
        self.assertEqual(r[0]["vat_cents"], 0)

    def test_billable_seats_not_seats(self):  # rule 1
        r = sb.prorate_seats(sub(seats=99, billable_seats=3), plan(),
                             at(timedelta(days=15)))
        self.assertEqual(r[0]["amount_cents"], 1500)
        self.assertEqual(r[1]["amount_cents"], 3000)

    def test_zero_seats(self):
        self.assertEqual(sb.prorate_seats(sub(billable_seats=0), plan(),
                                          at(timedelta(days=15))), [])

    def test_ceil_vs_floor(self):  # rule 4, 3 days left of 30
        r = sb.prorate_seats(sub(seat_price_cents=1001, billable_seats=1),
                             plan(1009), at(timedelta(days=3)))
        self.assertEqual(r[0]["amount_cents"], 101)   # 100.1 up
        self.assertEqual(r[1]["amount_cents"], 100)   # 100.9 down

    def test_30_day_period_always(self):  # rule 2
        a = sb.prorate_seats(sub(period_end=datetime(2025, 3, 1, tzinfo=UTC)),
                             plan(), datetime(2025, 3, 1, tzinfo=UTC) - timedelta(days=15))
        b = sb.prorate_seats(sub(period_end=datetime(2025, 8, 1, tzinfo=UTC)),
                             plan(), datetime(2025, 8, 1, tzinfo=UTC) - timedelta(days=15))
        self.assertEqual([x["amount_cents"] for x in a], [5000, 10000])
        self.assertEqual([x["amount_cents"] for x in b], [5000, 10000])

    def test_downgrade(self):  # rule 3
        self.assertEqual(sb.prorate_seats(sub(), plan(999), at(timedelta(days=15))), [])

    def test_equal_price(self):  # assumption D
        r = sb.prorate_seats(sub(), plan(1000), at(timedelta(days=15)))
        self.assertEqual([x["amount_cents"] for x in r], [5000, 5000])
        with mock.patch.object(sb, "EQUAL_PRICE_PRORATES", False):
            self.assertEqual(sb.prorate_seats(sub(), plan(1000), at(timedelta(days=15))), [])

    def test_trialing(self):  # rule 7
        self.assertEqual(sb.prorate_seats(sub(status="trialing"), plan(),
                                          at(timedelta(days=15))), [])

    def test_statuses(self):  # assumption F
        for st in ("active", "past_due"):
            r = sb.prorate_seats(sub(status=st), plan(), at(timedelta(days=15)))
            self.assertEqual(len(r), 2, st)
        with self.assertRaises(ValueError):
            sb.prorate_seats(sub(status="canceled"), plan(), at(timedelta(days=15)))

    def test_min_line_boundaries(self):  # rule 5, 30 days left, 1 seat
        d = timedelta(days=30)
        r = sb.prorate_seats(sub(seat_price_cents=49, billable_seats=1), plan(50), at(d))
        self.assertEqual([(x["kind"], x["amount_cents"]) for x in r], [("charge", 50)])
        r = sb.prorate_seats(sub(seat_price_cents=0, billable_seats=1), plan(49), at(d))
        self.assertEqual(r, [])
        r = sb.prorate_seats(sub(seat_price_cents=0, billable_seats=1), plan(50), at(d))
        self.assertEqual([(x["kind"], x["amount_cents"]) for x in r], [("charge", 50)])
        # 15 days left: credit 99/2=49.5 -> 50 kept; charge 49.5 -> 49 dropped
        r = sb.prorate_seats(sub(seat_price_cents=99, billable_seats=1), plan(99),
                             at(timedelta(days=15)))
        self.assertEqual([(x["kind"], x["amount_cents"]) for x in r], [("credit", 50)])
        # credit 97/2=48.5 -> 49 dropped
        r = sb.prorate_seats(sub(seat_price_cents=97, billable_seats=1), plan(97),
                             at(timedelta(days=15)))
        self.assertEqual(r, [])

    def test_vat_floor(self):  # rule 6
        r = sb.prorate_seats(sub(seat_price_cents=1000, billable_seats=1), plan(1050),
                             at(timedelta(days=3)))
        self.assertEqual(r[0]["amount_cents"], 100)
        self.assertEqual(r[1]["amount_cents"], 105)
        self.assertEqual(r[1]["vat_cents"], 22)  # 22.05 floored

    def test_reverse_charge_and_blank_vat(self):
        d = at(timedelta(days=15))
        self.assertEqual(sb.prorate_seats(sub(vat_id="NL123"), plan(), d)[1]["vat_cents"], 0)
        for blank in ("", "   ", None):
            self.assertEqual(sb.prorate_seats(sub(vat_id=blank), plan(), d)[1]["vat_cents"], 2100)
        s = sub()
        del s["vat_id"]
        self.assertEqual(sb.prorate_seats(s, plan(), d)[1]["vat_cents"], 2100)
        self.assertEqual(sb.prorate_seats(sub(vat_id="NL123"), plan(), d)[0]["vat_cents"], 0)

    def test_descriptions(self):  # rule 8
        r = sb.prorate_seats(sub(), plan(), at(timedelta(days=15)))
        self.assertEqual(r[0]["description"], "Credit unused Basic seats until 2025-06-30")
        self.assertEqual(r[1]["description"], "Charge Pro seats until 2025-06-30")
        long = "X" * 100
        r = sb.prorate_seats(sub(plan_name=long), plan(name=long), at(timedelta(days=15)))
        for line, prefix in zip(r, ("Credit unused XXX", "Charge XXX")):
            self.assertEqual(len(line["description"]), 80)
            self.assertIn("2025-06-30", line["description"])
            self.assertTrue(line["description"].startswith(prefix))
            self.assertIn("...", line["description"])

    def test_description_chars_not_bytes(self):
        name = "Ñ" * 100
        r = sb.prorate_seats(sub(plan_name=name), plan(name=name), at(timedelta(days=15)))
        for line in r:
            self.assertLessEqual(len(line["description"]), 80)
            self.assertIn("2025-06-30", line["description"])

    def test_approval(self):  # rule 9
        d = at(timedelta(days=30))
        r = sb.prorate_seats(sub(seat_price_cents=50000, billable_seats=1), plan(60000), d)
        self.assertEqual(r[0]["amount_cents"], 50000)
        self.assertEqual(r[0]["approved_by"], THAO)
        r = sb.prorate_seats(sub(seat_price_cents=50001, billable_seats=1), plan(60000), d)
        self.assertEqual(r[0]["amount_cents"], 50001)
        self.assertEqual(r[0]["approved_by"], RAMON)
        r = sb.prorate_seats(sub(seat_price_cents=100, billable_seats=1), plan(200), d)
        self.assertEqual(r[0]["approved_by"], THAO)
        self.assertIsNone(r[1]["approved_by"])  # charge
        self.assertEqual(r[1]["vat_cents"], 42)

    def test_order_keys_types(self):  # rules 10, 11
        r = sb.prorate_seats(sub(), plan(), at(timedelta(days=15)))
        self.assertEqual([x["kind"] for x in r], ["credit", "charge"])
        for x in r:
            self.assertEqual(set(x), {"subscription_id", "kind", "amount_cents",
                                      "vat_cents", "description", "approved_by"})
            self.assertEqual(x["subscription_id"], "sub_1")
            self.assertIs(type(x["amount_cents"]), int)
            self.assertIs(type(x["vat_cents"]), int)
            self.assertGreaterEqual(x["amount_cents"], 0)

    def test_no_mutation_and_legacy_ignored(self):
        s, p = sub(legacy_discount=50), plan()
        s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
        a = sb.prorate_seats(s, p, at(timedelta(days=15)))
        self.assertEqual((s, p), (s0, p0))
        b = sb.prorate_seats(sub(legacy_discount=0), plan(), at(timedelta(days=15)))
        self.assertEqual(a, b)

    def test_time_edges(self):
        self.assertEqual(sb.prorate_seats(sub(), plan(), PE), [])
        self.assertEqual(sb.prorate_seats(sub(), plan(), PE + timedelta(days=1)), [])
        r = sb.prorate_seats(sub(), plan(), at(timedelta(days=45)))
        self.assertEqual([x["amount_cents"] for x in r], [10000, 20000])

    def test_fractional_remaining(self):
        r = sb.prorate_seats(sub(seat_price_cents=6001, billable_seats=1), plan(6059),
                             at(timedelta(hours=12)))
        self.assertEqual(r[0]["amount_cents"], 101)  # 6001/60 = 100.02 up
        self.assertEqual(r[1]["amount_cents"], 100)  # 6059/60 = 100.98 down

    def test_whole_days_only(self):
        s, p, d = sub(seat_price_cents=3000, billable_seats=1), plan(3000), at(timedelta(hours=36))
        self.assertEqual([x["amount_cents"] for x in sb.prorate_seats(s, p, d)], [150, 150])
        with mock.patch.object(sb, "WHOLE_DAYS_ONLY", True):
            self.assertEqual([x["amount_cents"] for x in sb.prorate_seats(s, p, d)], [100, 100])

    def test_timezones(self):
        plus5 = timezone(timedelta(hours=5))
        ch = datetime(2025, 6, 15, 5, 0, tzinfo=plus5)  # 2025-06-15 00:00 UTC
        r = sb.prorate_seats(sub(), plan(), ch)
        self.assertEqual([x["amount_cents"] for x in r], [5000, 10000])
        minus5 = timezone(timedelta(hours=-5))
        pe = datetime(2025, 6, 30, 22, 0, tzinfo=minus5)  # 2025-07-01 03:00 UTC
        r = sb.prorate_seats(sub(period_end=pe), plan(), pe - timedelta(days=15))
        self.assertEqual([x["amount_cents"] for x in r], [5000, 10000])
        self.assertIn("2025-06-30", r[0]["description"])
        self.assertNotIn("2025-07-01", r[0]["description"])

    def test_validation(self):
        d = at(timedelta(days=15))
        naive = datetime(2025, 6, 15)
        bad = [
            (sub(), plan(), naive),
            (sub(period_end=datetime(2025, 6, 30)), plan(), d),
            (sub(seat_price_cents=10.0), plan(), d),
            (sub(seat_price_cents=True), plan(), d),
            (sub(seat_price_cents=-1), plan(), d),
            (sub(billable_seats=2.0), plan(), d),
            (sub(billable_seats=True), plan(), d),
            (sub(billable_seats=-1), plan(), d),
            (sub(id=""), plan(), d),
            (sub(plan_name="  "), plan(), d),
            (sub(), plan(name=""), d),
            (sub(), plan(price=1.5), d),
            (sub(), plan(price=-5), d),
            (sub(), {"name": "Pro"}, d),
            (sub(), {"seat_price_cents": 5}, d),
            # validation runs before shortcuts
            (sub(status="trialing", period_end=datetime(2025, 6, 30)), plan(), d),
            (sub(), plan(price=1.5), PE + timedelta(days=1)),
            (sub(seat_price_cents=2000), plan(price=-1), d),
        ]
        for i, (s, p, c) in enumerate(bad):
            with self.subTest(i=i), self.assertRaises(ValueError):
                sb.prorate_seats(s, p, c)
        for key in ("id", "status", "plan_name", "seat_price_cents",
                    "billable_seats", "period_end"):
            s = sub()
            del s[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                sb.prorate_seats(s, plan(), d)


if __name__ == "__main__":
    unittest.main()