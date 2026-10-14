"""prorate_seats: prorate a seat-price change on a subscription.

Money is integer cents. Credit lines round up and charge lines round down,
computed exactly with fractions.Fraction. Only billable_seats is billed.

Rules implemented (Requirements from the architect):
- status == "trialing" returns [].
- A strictly cheaper new plan is a downgrade and returns [].
- Credit = ceil(billable * old_price * unused / 13); charge = floor(billable * new_price * unused / 13).
- Lines with amount_cents under 50 (before VAT) are dropped independently.
- VAT 21% on charge lines only; vat_id truthy means reverse charge (vat 0).
- Credits carry vat_cents = 0 (architect requirement; this differs from the general house rule that VAT applies to credits too, so it is flagged here).
- Credit approved_by is "Nguyễn Thị Phương Thảo". Charges have approved_by None.
- Descriptions are at most 80 code points and always keep the period end date as YYYY-MM-DD.
- legacy_discount is ignored. Inputs are never mutated.

Assumptions implemented (flagged):
- Lines under 50 cents are judged before VAT.
- status matching is exact and case-sensitive.
- Equal prices are not a downgrade; they yield offsetting equal lines.
- changed_at >= period_end returns [] (unused_days <= 0).
- seat_price_cents is used as given, per seat per 13-day period. No unit conversion.
- VAT rounding is floor (open question on the rule).
- Seat count is assumed unchanged at the change date.
- Naive datetimes raise ValueError.

Open questions, left unresolved in code:
- Approver threshold: the input has no currency or FX rate. Any credit line requires the caller to pass both currency and fx_rate_to_eur. Without both, prorate_seats raises ApproverThresholdUnresolved and returns nothing (fail-closed). The strict "> EUR 500" comparison is an assumption.
- changed_at == period_end and changed_at >= period_end: returns [] rather than raising.
- unused_days > 13 (no period_start available): raises ValueError.
- Whether equal prices should produce no lines at all.
- Unit of seat_price_cents (per month, per year, or per 13-day period).
- VAT rounding rule (floor used).

Not verified: this module has not been executed. The self-test below is unrun.
"""

import math
from datetime import datetime, timedelta
from fractions import Fraction

PERIOD_DAYS = 13
VAT_PERCENT = 21
MIN_LINE_CENTS = 50
MAX_DESCRIPTION_LEN = 80
CREDIT_APPROVER = "Nguyễn Thị Phương Thảo"
LARGE_CREDIT_APPROVER = "Ramón Etxeberria-Goñi"
LARGE_CREDIT_THRESHOLD_EUR_CENTS = 50_000
_MICROS_PER_DAY = 86_400_000_000


class ApproverThresholdUnresolved(Exception):
    """A credit line needs the EUR 500 approver check, but no currency/FX override was given."""


def _to_fraction(value):
    if isinstance(value, (float, bool)):
        raise TypeError("fx_rate_to_eur must be an int, str or Fraction, not float")
    fx = Fraction(value)
    if fx <= 0:
        raise ValueError("fx_rate_to_eur must be positive")
    return fx


def _credit_approver(amount_cents, currency, fx_rate_to_eur):
    if currency is None or fx_rate_to_eur is None:
        raise ApproverThresholdUnresolved(
            "credit line needs the EUR threshold check; pass currency and fx_rate_to_eur"
        )
    if not isinstance(currency, str) or not currency.strip():
        raise ApproverThresholdUnresolved("currency must be a non-empty string")
    eur_cents = Fraction(amount_cents) * _to_fraction(fx_rate_to_eur)
    if eur_cents > LARGE_CREDIT_THRESHOLD_EUR_CENTS:
        return LARGE_CREDIT_APPROVER
    return CREDIT_APPROVER


def _check_aware(name, dt):
    if not isinstance(dt, datetime) or dt.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _description(prefix, plan, period_end):
    head = f"{prefix} "
    suffix = f" unused to {period_end.date().isoformat()}"
    room = MAX_DESCRIPTION_LEN - len(head) - len(suffix)
    name = str(plan)
    if len(name) > room:
        name = name[:room - 3] + "..."
    return f"{head}{name}{suffix}"


def _line(sub_id, kind, amount, vat, desc, approved_by):
    return {
        "subscription_id": sub_id,
        "kind": kind,
        "amount_cents": amount,
        "vat_cents": vat,
        "description": desc,
        "approved_by": approved_by,
    }


def prorate_seats(subscription, new_plan, changed_at, *, currency=None, fx_rate_to_eur=None):
    period_end = subscription["period_end"]
    _check_aware("changed_at", changed_at)
    _check_aware("period_end", period_end)

    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    micros = (period_end - changed_at) // timedelta(microseconds=1)
    if micros <= 0:
        return []
    unused = Fraction(micros, _MICROS_PER_DAY)
    if unused > PERIOD_DAYS:
        raise ValueError("unused days exceed the 13-day period; changed_at is outside the period")

    seats = subscription["billable_seats"]
    credit_cents = math.ceil(Fraction(seats * old_price) * unused / PERIOD_DAYS)
    charge_cents = math.floor(Fraction(seats * new_price) * unused / PERIOD_DAYS)

    sub_id = subscription["id"]
    reverse_charge = bool(subscription.get("vat_id"))
    lines = []

    if credit_cents >= MIN_LINE_CENTS:
        approver = _credit_approver(credit_cents, currency, fx_rate_to_eur)
        lines.append(_line(
            sub_id, "credit", credit_cents, 0,
            _description("Credit", subscription["plan_name"], period_end),
            approver,
        ))

    if charge_cents >= MIN_LINE_CENTS:
        vat = 0 if reverse_charge else charge_cents * VAT_PERCENT // 100
        lines.append(_line(
            sub_id, "charge", charge_cents, vat,
            _description("Charge", new_plan["name"], period_end),
            None,
        ))

    return lines


def _self_test():
    from datetime import timezone
    import copy

    utc = timezone.utc
    end = datetime(2026, 10, 20, 12, 0, tzinfo=utc)
    changed = end - timedelta(days=5)
    sub = {
        "id": "sub_1", "status": "active", "plan_name": "Basic",
        "seat_price_cents": 1000, "seats": 99, "billable_seats": 3,
        "vat_id": None, "period_end": end, "legacy_discount": 50,
    }
    plan = {"name": "Pro", "seat_price_cents": 1500}

    # Hand-check: credit 1154, charge 1730, VAT 363.
    snapshot = copy.deepcopy(sub)
    lines = prorate_seats(sub, plan, changed, currency="EUR", fx_rate_to_eur=1)
    assert [l["amount_cents"] for l in lines] == [1154, 1730]
    assert lines[1]["vat_cents"] == 363 and lines[0]["vat_cents"] == 0
    assert lines[0]["approved_by"] == CREDIT_APPROVER and lines[1]["approved_by"] is None
    assert lines[0]["description"] == "Credit Basic unused to 2026-10-20"
    assert lines[1]["description"] == "Charge Pro unused to 2026-10-20"
    assert sub == snapshot

    # Fail-closed when no override is given.
    try:
        prorate_seats(sub, plan, changed)
        raise AssertionError("expected ApproverThresholdUnresolved")
    except ApproverThresholdUnresolved:
        pass

    # Threshold: strict greater-than EUR 500.
    assert _credit_approver(50_000, "EUR", 1) == CREDIT_APPROVER
    assert _credit_approver(50_001, "EUR", 1) == LARGE_CREDIT_APPROVER
    big = dict(sub, billable_seats=1000)
    lines = prorate_seats(big, plan, changed, currency="EUR", fx_rate_to_eur="1")
    assert lines[0]["approved_by"] == LARGE_CREDIT_APPROVER

    # Under-50 lines dropped.
    small = dict(sub, billable_seats=1, seat_price_cents=10)
    assert prorate_seats(small, {"name": "Pro", "seat_price_cents": 20}, changed,
                         currency="EUR", fx_rate_to_eur=1) == []

    # Trialing and downgrade.
    assert prorate_seats(dict(sub, status="trialing"), plan, changed) == []
    assert prorate_seats(sub, {"name": "Lite", "seat_price_cents": 500}, changed) == []

    # Reverse charge.
    rc = prorate_seats(dict(sub, vat_id="DE123"), plan, changed,
                       currency="EUR", fx_rate_to_eur=1)
    assert rc[0]["vat_cents"] == 0 and rc[1]["vat_cents"] == 0

    # Truncation keeps the date and the 80-char limit.
    d = prorate_seats(dict(sub, plan_name="P" * 120), plan, changed,
                      currency="EUR", fx_rate_to_eur=1)[0]["description"]
    assert len(d) == 80 and d.endswith("unused to 2026-10-20")

    # Naive datetime and more than 13 unused days.
    try:
        prorate_seats(sub, plan, datetime(2026, 10, 15))
        raise AssertionError("expected ValueError for naive datetime")
    except ValueError:
        pass
    try:
        prorate_seats(sub, plan, end - timedelta(days=14), currency="EUR", fx_rate_to_eur=1)
        raise AssertionError("expected ValueError for >13 unused days")
    except ValueError:
        pass


if __name__ == "__main__":
    _self_test()
    print("ok")