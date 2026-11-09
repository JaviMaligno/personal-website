"""prorate_seats.py

Seat-upgrade proration for Fernhollow Studios billing.

Assumptions:
- Tests (test_prorate_seats.py) were not written or run: no tools were available in this session.
- Credits carry vat_cents 0 as the client's brief and the architect specify. This overrides the house rule "VAT applies to every invoice line".
- The period is 13 days. unused = timedelta.days of (period_end - changed_at), clamped to 0..13.
- Credit = ceil, charge = floor, both in integer arithmetic. Lines under 50 cents are skipped, and exactly 50 is kept.
- VAT = charge * 21 // 100, or 0 if vat_id is truthy.
- Description is "<name> - seat proration until YYYY-MM-DD", at most 80 characters. Only the plan name is truncated, with an ellipsis. The date comes from period_end as given, with no timezone conversion.
- Credits are approved by Nguyễn Thị Phương Thảo, or by Ramón Etxeberria-Goñi if amount_cents > 50000.
- billable_seats is used, and legacy_discount is ignored.
- Trialing status or a lower new price returns []. An equal price is not a downgrade.
"""

PERIOD_DAYS = 13
MAX_DESC = 80
MIN_LINE_CENTS = 50
VAT_PERCENT = 21
APPROVER = "Nguy\u1ec5n Th\u1ecb Ph\u01b0\u01a1ng Th\u1ea3o"
BIG_APPROVER = "Ram\u00f3n Etxeberria-Go\u00f1i"
BIG_THRESHOLD_CENTS = 50000


def _description(name: str, period_end) -> str:
    date = period_end.date().isoformat()
    suffix = f" - seat proration until {date}"
    name = str(name)
    avail = MAX_DESC - len(suffix)
    if len(name) <= avail:
        return name + suffix
    if avail >= 2:
        return name[: avail - 1] + "\u2026" + suffix
    if avail == 1:
        return "\u2026" + suffix
    # Pathological: no room for any name; keep the date, cap the length.
    return f"until {date}"[-MAX_DESC:]


def prorate_seats(subscription, new_plan, changed_at):
    if subscription.get("status") == "trialing":
        return []
    old_price = int(subscription["seat_price_cents"])
    new_price = int(new_plan["seat_price_cents"])
    if new_price < old_price:
        return []

    seats = int(subscription["billable_seats"])
    period_end = subscription["period_end"]
    unused = (period_end - changed_at).days
    unused = max(0, min(PERIOD_DAYS, unused))

    sub_id = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * unused) // PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(subscription["plan_name"], period_end),
            "approved_by": BIG_APPROVER if credit > BIG_THRESHOLD_CENTS else APPROVER,
        })

    charge = (new_price * seats * unused) // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        vat = 0 if subscription.get("vat_id") else charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description(new_plan["name"], period_end),
            "approved_by": None,
        })

    return lines