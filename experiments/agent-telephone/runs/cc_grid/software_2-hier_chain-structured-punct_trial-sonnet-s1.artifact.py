# ===== /prorate.py (current working directory) =====
# Assumptions:
# - R10 (credit VAT always 0) overrides the house rule "VAT on every line", as the client stated it explicitly.
# - R8 explicit rounding (credit up, charge down) overrides the house half-up rule.
# - Description format: "Credit unused {plan} until {date}" / "Charge unused {plan} until {date}".
# - Tests were NOT executed by me (no tools available); run: python3 -I -m pytest test_prorate.py

APPROVER = "Nguyễn Thị Phương Thảo"
SENIOR_APPROVER = "Ramón Etxeberria-Goñi"
PERIOD_DAYS = 30
MAX_DESC = 80
MIN_LINE_CENTS = 50
SENIOR_THRESHOLD = 50000
VAT_PERCENT = 21


def _describe(verb, plan, date):
    # R12: shorten plan name only; date always intact at the end.
    prefix = f"{verb} unused "
    suffix = f" until {date}"
    budget = MAX_DESC - len(prefix) - len(suffix)
    if len(plan) > budget:
        plan = plan[: budget - 1] + "…"
    return prefix + plan + suffix


def prorate_seats(subscription, new_plan, changed_at):  # R1
    # R11: trialing first.
    if subscription.get("status") == "trialing":
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    # R7: downgrade only (equal is not a downgrade).
    if new_price < old_price:
        return []

    seats = subscription.get("billable_seats") or 0  # R5
    period_end = subscription["period_end"]
    days_left = max(0, min(PERIOD_DAYS, (period_end - changed_at).days))  # R6
    date = period_end.strftime("%Y-%m-%d")  # R4
    sub_id = subscription["id"]

    lines = []
    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)  # R8 round up
    if credit >= MIN_LINE_CENTS:  # R9
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,  # R10
            "description": _describe("Credit", subscription["plan_name"], date),
            "approved_by": SENIOR_APPROVER if credit > SENIOR_THRESHOLD else APPROVER,  # R13
        })
    charge = (new_price * seats * days_left) // PERIOD_DAYS  # R8 round down
    if charge >= MIN_LINE_CENTS:
        vat = 0 if subscription.get("vat_id") else charge * VAT_PERCENT // 100  # R10
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe("Charge", new_plan["name"], date),
            "approved_by": None,
        })
    return lines  # R15: credit first


# ===== /test_prorate.py (current working directory) =====
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone

from prorate import prorate_seats

END = datetime(2026, 11, 1, tzinfo=timezone.utc)
NOW = END - timedelta(days=30)


def sub(**kw):
    s = dict(id="s1", status="active", plan_name="Basic", seat_price_cents=1000,
             seats=99, billable_seats=10, vat_id=None, period_end=END)
    s.update(kw)
    return s


def plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def test_basic_credit_then_charge_r3_r6_r15_r16():
    out = prorate_seats(sub(), plan(), NOW)
    assert [l["kind"] for l in out] == ["credit", "charge"]
    c, ch = out
    assert set(c) == {"subscription_id", "kind", "amount_cents", "vat_cents",
                      "description", "approved_by"}
    assert c["amount_cents"] == 10000 and c["vat_cents"] == 0
    assert ch["amount_cents"] == 20000 and ch["vat_cents"] == 4200
    assert ch["approved_by"] is None
    assert c["description"] == "Credit unused Basic until 2026-11-01"
    assert ch["description"] == "Charge unused Pro until 2026-11-01"
    for l in out:
        assert type(l["amount_cents"]) is int and type(l["vat_cents"]) is int


def test_uses_billable_seats_r5():
    out = prorate_seats(sub(billable_seats=1, seats=500), plan(), NOW)
    assert out[0]["amount_cents"] == 1000


def test_downgrade_and_trialing_r7_r11():
    assert prorate_seats(sub(), plan(999), NOW) == []
    assert prorate_seats(sub(status="trialing"), plan(), NOW) == []


def test_days_left_zero_and_clamp_r6():
    assert prorate_seats(sub(), plan(), END) == []
    assert prorate_seats(sub(), plan(), END + timedelta(days=5)) == []
    out = prorate_seats(sub(), plan(), END - timedelta(days=90))
    assert out[0]["amount_cents"] == 10000  # clamped to 30 days
    out = prorate_seats(sub(), plan(), END - timedelta(days=15, hours=5))
    assert out[0]["amount_cents"] == 5000  # floor to 15 days


def test_vat_id_r10():
    for v in ("", None):
        assert prorate_seats(sub(vat_id=v), plan(), NOW)[1]["vat_cents"] == 4200
    s = sub(); del s["vat_id"]
    assert prorate_seats(s, plan(), NOW)[1]["vat_cents"] == 4200
    out = prorate_seats(sub(vat_id="DE123"), plan(), NOW)
    assert out[1]["vat_cents"] == 0 and out[0]["vat_cents"] == 0


def test_vat_floor_r10():
    out = prorate_seats(sub(billable_seats=1), plan(1050), NOW)
    assert out[1]["amount_cents"] == 1050 and out[1]["vat_cents"] == 220


def test_zero_billable_seats():
    assert prorate_seats(sub(billable_seats=0), plan(), NOW) == []


def test_rounding_and_skip_r8_r9():
    # equal price: credit ceil = 50 kept, charge floor = 49 skipped
    out = prorate_seats(sub(seat_price_cents=1, billable_seats=1471), plan(1),
                        END - timedelta(days=1))
    assert [l["kind"] for l in out] == ["credit"]
    assert out[0]["amount_cents"] == 50


def test_charge_without_credit():
    out = prorate_seats(sub(seat_price_cents=1, billable_seats=1), plan(100), NOW)
    assert [l["kind"] for l in out] == ["charge"]


def test_same_price_change():
    out = prorate_seats(sub(), plan(1000, "Basic2"), NOW)
    assert [l["amount_cents"] for l in out] == [10000, 10000]


def test_approver_boundaries_r13():
    at = prorate_seats(sub(seat_price_cents=5000), plan(6000), NOW)[0]
    assert at["amount_cents"] == 50000
    assert at["approved_by"] == "Nguyễn Thị Phương Thảo"
    over = prorate_seats(sub(seat_price_cents=50001, billable_seats=1), plan(60000), NOW)[0]
    assert over["amount_cents"] == 50001
    assert over["approved_by"] == "Ramón Etxeberria-Goñi"


def test_long_plan_name_r12():
    for name in ("A" * 300, "Ünïcödé–日本語 " * 20):
        out = prorate_seats(sub(plan_name=name), plan(name=name), NOW)
        for l in out:
            assert len(l["description"]) <= 80
            assert l["description"].endswith(" until 2026-11-01")
            assert "…" in l["description"]
    assert out[0]["description"].startswith("Credit unused Ünïcödé")


def test_name_exactly_fits_r12():
    name = "B" * 49
    d = prorate_seats(sub(plan_name=name), plan(name=name), NOW)[0]["description"]
    assert len(d) == 80 and "…" not in d
</br>