# prorate.py
# Assumptions:
# - days_left counts calendar dates in period_end's timezone.
# - VAT is floored: amount*21//100.
# - An equal price is not a downgrade.
# - R7 (credit rounded up, charge rounded down) overrides the house half-up rule.
# - R10 (credits carry no VAT) overrides the house "VAT on every line" rule.
# - Tests are embedded below so the single file is self-contained.
# - Run them with: pytest -q prorate.py
# - I had no tool access, so the tests have NOT been run.

PERIOD_DAYS = 13
MAX_DESC = 80
MIN_AMOUNT = 50
VAT_PERCENT = 21
APPROVER_DEFAULT = "Nguyen\u0302\u0303".replace("Nguyen\u0302\u0303", "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o")  # NFC
APPROVER_HIGH = "Ram\u00f3n Etxeberria-Go\u00f1i"  # NFC
HIGH_CREDIT_THRESHOLD = 50000


def _has_vat_id(vat_id):
    return isinstance(vat_id, str) and bool(vat_id.strip())


def _describe(kind_word, plan, date_str):
    prefix = f"{kind_word} unused " if kind_word == "Credit" else f"{kind_word} "
    suffix = f" seats, period ends {date_str}"
    budget = MAX_DESC - len(prefix) - len(suffix)
    if len(plan) > budget:
        keep = budget - 3
        plan = plan[:keep] + "..." if keep > 0 else "..."
    return f"{prefix}{plan}{suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    if subscription.get("status") == "trialing":
        return []
    seats = subscription["billable_seats"]
    if seats <= 0:
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []
    period_end = subscription["period_end"]
    local_change = changed_at.astimezone(period_end.tzinfo)
    days_left = min((period_end.date() - local_change.date()).days, PERIOD_DAYS)
    if days_left <= 0:
        return []

    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)
    if credit >= MIN_AMOUNT:
        approver = APPROVER_HIGH if credit > HIGH_CREDIT_THRESHOLD else APPROVER_DEFAULT
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _describe("Credit", subscription["plan_name"], date_str),
            "approved_by": approver,
        })

    charge = (new_price * seats * days_left) // PERIOD_DAYS
    if charge >= MIN_AMOUNT:
        vat = 0 if _has_vat_id(subscription.get("vat_id")) else charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _describe("Charge", new_plan["name"], date_str),
            "approved_by": None,
        })
    return lines


# ---------------------------- tests ----------------------------
import copy
import unicodedata
from datetime import datetime, timedelta, timezone

UTC = timezone.utc


def _sub(**kw):
    s = {"id": "sub_1", "status": "active", "plan_name": "Basic",
         "seat_price_cents": 1000, "billable_seats": 1, "vat_id": None,
         "period_end": datetime(2025, 1, 14, tzinfo=UTC)}
    s.update(kw)
    return s


def _plan(price=2000, name="Pro"):
    return {"name": name, "seat_price_cents": price}


def _at(day=1, hour=12):
    return datetime(2025, 1, day, hour, tzinfo=UTC)


def test_r1_r2_r3_r15_basic():
    out = prorate_seats(_sub(billable_seats=10), _plan(), _at(1))
    assert [l["kind"] for l in out] == ["credit", "charge"]
    assert all(set(l) == {"subscription_id", "kind", "amount_cents", "vat_cents",
                          "description", "approved_by"} for l in out)
    assert out[0]["amount_cents"] == 10000 and out[1]["amount_cents"] == 20000
    assert out[0]["description"] == "Credit unused Basic seats, period ends 2025-01-14"
    assert out[1]["description"] == "Charge Pro seats, period ends 2025-01-14"
    assert out[1]["approved_by"] is None


def test_r4_uses_billable_not_seats_and_r17_ignores_discount():
    s = _sub(billable_seats=2, legacy_discount=50)
    s["seats"] = 999
    out = prorate_seats(s, _plan(), _at(1))
    assert out[0]["amount_cents"] == 2000


def test_r5_days_clamp_and_timezone():
    assert prorate_seats(_sub(), _plan(), _at(14)) == []
    assert prorate_seats(_sub(), _plan(), _at(20)) == []
    early = datetime(2024, 12, 1, tzinfo=UTC)
    assert prorate_seats(_sub(), _plan(), early)[0]["amount_cents"] == 1000
    tz = timezone(timedelta(hours=10))
    s = _sub(period_end=datetime(2025, 1, 14, tzinfo=tz))
    ch = datetime(2025, 1, 8, 20, tzinfo=UTC)  # Jan 9 in +10 -> 5 days
    out = prorate_seats(s, _plan(1000), ch)
    assert out[0]["amount_cents"] == -(-5000 // 13)


def test_r6_downgrade_and_equal():
    assert prorate_seats(_sub(), _plan(500), _at(1)) == []
    assert len(prorate_seats(_sub(), _plan(1000), _at(1))) == 2


def test_r7_rounding_and_r9_vat_floor():
    out = prorate_seats(_sub(), _plan(1000), _at(9))  # 5 days
    assert out[0]["amount_cents"] == 385
    assert out[1]["amount_cents"] == 384
    assert out[1]["vat_cents"] == 384 * 21 // 100 == 80


def test_r8_independent_skip():
    out = prorate_seats(_sub(seat_price_cents=40), _plan(1000), _at(1))
    assert [l["kind"] for l in out] == ["charge"]
    out = prorate_seats(_sub(seat_price_cents=1000), _plan(1000), _at(13))  # 1 day
    assert [l["amount_cents"] for l in out] == [77, 76]
    assert prorate_seats(_sub(seat_price_cents=100), _plan(100), _at(13)) == []


def test_r9_r10_vat_id():
    out = prorate_seats(_sub(vat_id="DE123"), _plan(), _at(1))
    assert out[1]["vat_cents"] == 0 and out[0]["vat_cents"] == 0
    out = prorate_seats(_sub(vat_id="   "), _plan(), _at(1))
    assert out[1]["vat_cents"] == 2100 * 21 // 21 * 1 // 1 * 0 + out[1]["amount_cents"] * 21 // 100
    assert out[0]["vat_cents"] == 0


def test_r11_trial_and_no_seats():
    assert prorate_seats(_sub(status="trialing"), _plan(), _at(1)) == []
    assert prorate_seats(_sub(billable_seats=0), _plan(), _at(1)) == []


def test_r12_long_and_non_ascii_names():
    for name in ("A" * 200, "\u00e9\u4e2d" * 80):
        out = prorate_seats(_sub(plan_name=name), _plan(name=name), _at(1))
        for l in out:
            assert len(l["description"]) <= 80
            assert l["description"].endswith("period ends 2025-01-14")
            assert "..." in l["description"]
    assert _describe("Credit", "", "2025-01-14") == "Credit unused  seats, period ends 2025-01-14"


def test_r12_budget_exhausted():
    assert "unused ... seats" in _describe("Credit", "x" * 500, "2025-01-14")


def test_r13_approvers():
    assert unicodedata.is_normalized("NFC", APPROVER_DEFAULT)
    assert unicodedata.is_normalized("NFC", APPROVER_HIGH)
    assert APPROVER_DEFAULT == "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"
    low = prorate_seats(_sub(seat_price_cents=3846, billable_seats=1), _plan(4000), _at(1))
    assert low[0]["amount_cents"] == 3846 and low[0]["approved_by"] == APPROVER_DEFAULT
    edge = prorate_seats(_sub(seat_price_cents=50000), _plan(50000), _at(1))
    assert edge[0]["amount_cents"] == 50000 and edge[0]["approved_by"] == APPROVER_DEFAULT
    high = prorate_seats(_sub(seat_price_cents=6000, billable_seats=10), _plan(7000), _at(1))
    assert high[0]["amount_cents"] == 60000 and high[0]["approved_by"] == APPROVER_HIGH


def test_no_mutation_and_int_types():
    s, p, c = _sub(billable_seats=3), _plan(), _at(2)
    s0, p0 = copy.deepcopy(s), copy.deepcopy(p)
    out = prorate_seats(s, p, c)
    assert s == s0 and p == p0
    assert all(type(l["amount_cents"]) is int and type(l["vat_cents"]) is int for l in out)