# ==== FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-3jb2b22f/seat_proration.py ====
# NOTE: I had no tools in this session, so neither file was saved and the
# tests were NOT run. Save each section as UTF-8 and run:
#   python3 -I -m pytest /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-3jb2b22f
# Assumptions: EUR cents; "..." (3 ASCII chars) is the truncation marker;
# plan names are truncated by code points (NFC assumed); seats must be > 0 and
# billable_seats >= 0; validation runs before any early return (including
# trialing); billable_seats > seats is not rejected; unknown status values
# are prorated.
"""Seat-upgrade proration for Fernhollow Studios billing (EUR cents)."""
from datetime import datetime, timedelta

APPROVER_STANDARD = "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"
APPROVER_SENIOR = "Ram\u00f3n Etxeberria-Go\u00f1i"
APPROVAL_THRESHOLD_CENTS = 50000
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
MAX_DESC = 80
ELLIPSIS = "..."
PERIOD_DAYS = 13


def _us(td: timedelta) -> int:
    return (td.days * 86400 + td.seconds) * 1_000_000 + td.microseconds


_PERIOD_US = _us(timedelta(days=PERIOD_DAYS))


def _int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    return value


def _aware(value, name):
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _describe(verb, plan, date_str):
    template = f"{verb} unused {{}} until {date_str}"
    room = MAX_DESC - len(template.format(""))
    if len(plan) > room:
        if room >= len(ELLIPSIS):
            plan = plan[: room - len(ELLIPSIS)] + ELLIPSIS
        else:
            plan = ELLIPSIS[: max(room, 0)]
    return template.format(plan)


def prorate_seats(subscription, new_plan, changed_at):
    """Return proration lines (credit first, then charge) for a seat upgrade.

    Subscriptions with status == "trialing" yield []. All other statuses are
    prorated. Also [] for: billable_seats == 0, a downgrade (new price below
    old), or changed_at >= period_end. The legacy_discount field is ignored.
    Inputs are not mutated.
    """
    old_price = _int(subscription["seat_price_cents"], "seat_price_cents")
    new_price = _int(new_plan["seat_price_cents"], "new seat_price_cents")
    seats = _int(subscription["seats"], "seats")
    billable = _int(subscription["billable_seats"], "billable_seats")
    if old_price < 0 or new_price < 0:
        raise ValueError("prices must not be negative")
    if seats <= 0:
        raise ValueError("seats must be positive")
    if billable < 0:
        raise ValueError("billable_seats must not be negative")
    period_end = subscription["period_end"]
    _aware(changed_at, "changed_at")
    _aware(period_end, "period_end")

    if subscription["status"] == "trialing" or billable == 0:
        return []
    if new_price < old_price:
        return []
    if changed_at >= period_end:
        return []

    remaining = min(max(_us(period_end - changed_at), 0), _PERIOD_US)
    credit_num = old_price * billable * remaining
    charge_num = new_price * billable * remaining
    credit = -(-credit_num // _PERIOD_US)  # ceiling
    charge = charge_num // _PERIOD_US  # floor

    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit", subscription["plan_name"], date_str),
            "approved_by": (APPROVER_SENIOR if credit > APPROVAL_THRESHOLD_CENTS
                            else APPROVER_STANDARD),
        })
    if charge >= MIN_LINE_CENTS:
        vat_id = subscription.get("vat_id")
        has_vat_id = isinstance(vat_id, str) and bool(vat_id.strip())
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": 0 if has_vat_id else charge * VAT_PERCENT // 100,
            "description": _describe("Charge", new_plan["name"], date_str),
            "approved_by": None,
        })
    return lines


# ==== FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-3jb2b22f/test_seat_proration.py ====
import ast
import copy
import unicodedata
from datetime import datetime, timedelta, timezone

import pytest

import seat_proration as sp
from seat_proration import prorate_seats

UTC = timezone.utc
END = datetime(2025, 1, 14, 0, 0, tzinfo=UTC)


def sub(**kw):
    d = dict(id="sub_1", status="active", plan_name="Basic", seat_price_cents=1000,
             seats=5, billable_seats=1, vat_id=None, period_end=END)
    d.update(kw)
    return d


def plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def run(s=None, p=None, before=timedelta(days=13)):
    return prorate_seats(s or sub(), p or plan(), END - before)


def test_R1_naive_datetime_raises():
    with pytest.raises(ValueError):
        prorate_seats(sub(), plan(), datetime(2025, 1, 10))
    with pytest.raises(ValueError):
        prorate_seats(sub(period_end=datetime(2025, 1, 14)), plan(), END - timedelta(days=1))


def test_R2_keys_and_descriptions():
    credit, charge = run()
    keys = {"subscription_id", "kind", "amount_cents", "vat_cents", "description", "approved_by"}
    assert set(credit) == keys and set(charge) == keys
    assert credit["kind"] == "credit" and charge["kind"] == "charge"
    assert credit["description"] == "Credit unused Basic until 2025-01-14"
    assert charge["description"] == "Charge unused Pro until 2025-01-14"
    assert credit["subscription_id"] == "sub_1"


def test_R2_date_in_period_end_own_tz():
    tz = timezone(timedelta(hours=5))
    end = datetime(2025, 1, 14, 1, 0, tzinfo=tz)  # 2025-01-13 in UTC
    out = prorate_seats(sub(period_end=end), plan(), end - timedelta(days=1))
    assert all("2025-01-14" in l["description"] for l in out)


def test_R3_uses_billable_not_seats():
    out = run(sub(seats=50, billable_seats=2))
    assert out[0]["amount_cents"] == 2000 and out[1]["amount_cents"] == 4000
    assert out == run(sub(seats=3, billable_seats=2))


def test_R4_half_period_and_clamp_and_end():
    out = run(before=timedelta(days=6, hours=12))
    assert [l["amount_cents"] for l in out] == [500, 1000]
    far = run(before=timedelta(days=30))
    assert [l["amount_cents"] for l in far] == [1000, 2000]
    assert prorate_seats(sub(), plan(), END) == []
    assert prorate_seats(sub(), plan(), END + timedelta(seconds=1)) == []


def test_R4_ceil_vs_floor_same_fraction():
    s = sub(billable_seats=100)
    out = prorate_seats(s, plan(1000), END - timedelta(days=1))  # equal prices
    assert out[0]["amount_cents"] == 7693 and out[1]["amount_cents"] == 7692


def test_R4_half_day_and_subday():
    out = prorate_seats(sub(seat_price_cents=1301), plan(1301), END - timedelta(hours=12))
    assert out[0]["amount_cents"] == 51 and out[1]["amount_cents"] == 50
    s = sub(billable_seats=100000)
    out = prorate_seats(s, plan(1000), END - timedelta(seconds=1))
    assert out[0]["amount_cents"] == -(-(1000 * 100000) // 1123200)
    assert out[1]["amount_cents"] == 1000 * 100000 // 1123200


def test_R4_different_timezone_compares_instants():
    tz = timezone(timedelta(hours=-8))
    changed = (END - timedelta(days=1)).astimezone(tz)
    out = prorate_seats(sub(billable_seats=100), plan(1000), changed)
    assert out[0]["amount_cents"] == 7693
    assert prorate_seats(sub(), plan(), END.astimezone(tz)) == []


def test_R5_downgrade_and_equal():
    assert run(p=plan(999)) == []
    out = run(p=plan(1000))
    assert [l["kind"] for l in out] == ["credit", "charge"]


def test_R6_rounding_directions():
    out = prorate_seats(sub(seat_price_cents=1301), plan(1301), END - timedelta(hours=12))
    assert out[0]["amount_cents"] > out[1]["amount_cents"]


@pytest.mark.parametrize("old,new,kinds", [
    (49, 49, []),
    (50, 50, ["credit", "charge"]),
    (51, 51, ["credit", "charge"]),
    (49, 60, ["charge"]),
    (49, 50, ["charge"]),
    (40, 49, []),
])
def test_R7_boundary_independent(old, new, kinds):
    out = prorate_seats(sub(seat_price_cents=old), plan(new), END - timedelta(days=13))
    assert [l["kind"] for l in out] == kinds


def test_R7_credit_dropped_after_rounding():
    # raw credit just above 49 but ceiling gives 50 -> kept
    out = prorate_seats(sub(seat_price_cents=1301), plan(1301), END - timedelta(hours=12))
    assert out[0]["amount_cents"] == 51


def test_R8_vat_floor_and_vat_id():
    out = run(sub(billable_seats=100), plan(1000), ) if False else prorate_seats(
        sub(billable_seats=100), plan(1000), END - timedelta(days=1))
    assert out[1]["amount_cents"] == 7692 and out[1]["vat_cents"] == 7692 * 21 // 100
    for vid in ("NL123", " x "):
        assert run(sub(vat_id=vid))[1]["vat_cents"] == 0
    for vid in (None, "", "   "):
        assert run(sub(vat_id=vid))[1]["vat_cents"] == 2000 * 21 // 100


def test_R9_credit_vat_zero():
    assert run()[0]["vat_cents"] == 0
    assert run(sub(vat_id="NL1"))[0]["vat_cents"] == 0


def test_R10_trialing_and_other_statuses():
    assert run(sub(status="trialing")) == []
    for st in ("active", "past_due", "canceled"):
        assert len(run(sub(status=st))) == 2


def test_R11_long_plan_name():
    long = "A" * 200
    out = prorate_seats(sub(plan_name=long), plan(name=long), END - timedelta(days=13))
    for l in out:
        assert len(l["description"]) <= 80
        assert l["description"].endswith("until 2025-01-14")
        assert "..." in l["description"]


def test_R11_non_ascii_plan_name():
    name = "\u00c9quipe \u65e5\u672c\u8a9e " * 10
    out = prorate_seats(sub(plan_name=name), plan(name=name), END - timedelta(days=13))
    for l in out:
        assert len(l["description"]) <= 80
        assert l["description"].endswith("2025-01-14")
    short = prorate_seats(sub(plan_name="\u65e5\u672c"), plan(name="\u00c9quipe"), END - timedelta(days=13))
    assert "\u65e5\u672c" in short[0]["description"] and "\u00c9quipe" in short[1]["description"]


def test_R11_exact_80_not_truncated():
    room = 80 - len("Credit unused  until 2025-01-14")
    out = prorate_seats(sub(plan_name="B" * room), plan(), END - timedelta(days=13))
    assert len(out[0]["description"]) == 80 and "..." not in out[0]["description"]


def test_R12_approvers_exact_and_nfc():
    assert sp.APPROVER_STANDARD == "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"
    assert sp.APPROVER_SENIOR == "Ram\u00f3n Etxeberria-Go\u00f1i"
    for n in (sp.APPROVER_STANDARD, sp.APPROVER_SENIOR):
        assert unicodedata.normalize("NFC", n) == n
    s = sub(seat_price_cents=50000)
    out = prorate_seats(s, plan(50000), END - timedelta(days=13))
    assert out[0]["approved_by"] == sp.APPROVER_STANDARD
    assert out[1]["approved_by"] is None
    s = sub(seat_price_cents=50001)
    out = prorate_seats(s, plan(50001), END - timedelta(days=13))
    assert out[0]["approved_by"] == sp.APPROVER_SENIOR
    assert out[1]["approved_by"] is None


def test_R13_credit_and_vat_both_present():
    credit, charge = run()
    assert credit["amount_cents"] == 1000 and charge["vat_cents"] == 420


def test_R14_order_and_single_line():
    assert [l["kind"] for l in run()] == ["credit", "charge"]
    out = prorate_seats(sub(seat_price_cents=49), plan(60), END - timedelta(days=13))
    assert [l["kind"] for l in out] == ["charge"]


def test_R15_int_types():
    for l in run():
        assert type(l["amount_cents"]) is int and type(l["vat_cents"]) is int


def test_R15_source_scan():
    with open(sp.__file__, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.Div)
        if isinstance(node, ast.Constant):
            assert not isinstance(node.value, float)


def test_R15_bad_inputs():
    with pytest.raises(TypeError):
        run(sub(seat_price_cents=10.5))
    with pytest.raises(TypeError):
        run(sub(seat_price_cents=True))
    with pytest.raises(TypeError):
        run(p=plan(20.0))
    with pytest.raises(TypeError):
        run(sub(billable_seats=True))
    with pytest.raises(TypeError):
        run(sub(seats=2.0))
    with pytest.raises(ValueError):
        run(sub(seat_price_cents=-1))
    with pytest.raises(ValueError):
        run(p=plan(-5))
    with pytest.raises(ValueError):
        run(sub(seats=0))
    with pytest.raises(ValueError):
        run(sub(billable_seats=-1))


def test_R15_billable_zero_returns_empty():
    assert run(sub(billable_seats=0)) == []


def test_R16_legacy_discount_ignored():
    assert run(sub(legacy_discount=50)) == run()
    assert run(sub(legacy_discount=0.9)) == run()


def test_inputs_not_mutated():
    s, p = sub(legacy_discount=3), plan()
    s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
    prorate_seats(s, p, END - timedelta(days=3))
    assert s == s0 and p == p0