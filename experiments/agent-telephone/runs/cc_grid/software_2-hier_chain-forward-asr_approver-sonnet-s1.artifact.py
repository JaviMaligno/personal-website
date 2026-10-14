# Not run: no tools were available, so test_prorate.py was not written and nothing was executed.
# Where the brief and house rules conflict, the brief wins: credits carry no VAT, and
# credits round up while charges round down. Those are the "told otherwise" cases.
"""Seat upgrade proration for Fernhollow Studios.

Decisions:
- Integer arithmetic only. Ceil-div is -(-a // b), floor is a // b.
- Returns [] for trialing subscriptions, for downgrades (new price < old price),
  and for equal prices (no upgrade, so nothing to prorate).
- Seats come from subscription["billable_seats"]; "seats" and "legacy_discount"
  are never read.
- Unused days are whole days, floor((period_end - changed_at) in UTC), clamped to
  0..30. Naive datetimes raise ValueError. 0 unused days returns [].
- credit = ceil(old_price * seats * unused / 30), charge = floor(new_price * seats
  * unused / 30), each computed from the full product with a single division.
- Credit amount_cents is a POSITIVE integer; "kind" says it is a credit.
  Credits carry vat_cents 0 (finance reverses VAT separately).
- Each line is skipped independently if amount_cents < 50 (exactly 50 is kept).
- Charge VAT: 0 if vat_id is truthy (reverse charge), else floor(amount * 21 / 100)
  on the rounded net charge amount.
- approved_by: None on charges; credits use "Win Tee Fung Tao", or
  "Ramon Etxeberria-Goni" with accents (see APPROVER_BIG) when amount_cents > 50000.
- Description: "<Credit|Charge> unused <plan> until YYYY-MM-DD", where the date is
  period_end's own calendar date as given (no UTC conversion). Max 80 code points.
  If too long the stripped plan name is truncated (with "..." when room) and the
  date is never cut. An empty name is omitted entirely.
- Order: credit first, then charge.
"""
from datetime import timezone

APPROVER = "Win Tee Fung Tao"
APPROVER_BIG = "Ram\u00f3n Etxeberria-Go\u00f1i"
MAX_DESC = 80
BIG_CREDIT_CENTS = 50000
MIN_LINE_CENTS = 50
PERIOD_DAYS = 30


def _check_aware(dt, label):
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _description(verb, plan_name, period_end):
    prefix = f"{verb} unused "
    suffix = f"until {period_end.strftime('%Y-%m-%d')}"
    name = str(plan_name or "").strip()
    # Room for the name plus its trailing space separator.
    avail = MAX_DESC - len(prefix) - len(suffix) - 1
    if len(name) > avail:
        if avail > 3:
            name = name[: avail - 3].rstrip() + "..."
        else:
            name = name[: max(avail, 0)].rstrip()
    if not name:
        return f"{prefix}{suffix}"
    return f"{prefix}{name} {suffix}"


def prorate_seats(subscription, new_plan, changed_at):
    """Return invoice lines (credit first, then charge) for a seat upgrade."""
    if subscription["status"] == "trialing":
        return []
    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price <= old_price:  # downgrade or equal price: nothing to prorate now
        return []

    period_end = subscription["period_end"]
    _check_aware(changed_at, "changed_at")
    _check_aware(period_end, "period_end")

    delta = period_end.astimezone(timezone.utc) - changed_at.astimezone(timezone.utc)
    total_seconds = delta.days * 86400 + delta.seconds  # integer, floors microseconds
    unused = max(0, min(PERIOD_DAYS, total_seconds // 86400))
    if unused == 0:
        return []

    seats = subscription["billable_seats"]
    sub_id = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * unused) // PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description("Credit", subscription["plan_name"], period_end),
            "approved_by": APPROVER_BIG if credit > BIG_CREDIT_CENTS else APPROVER,
        })

    charge = (new_price * seats * unused) // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        vat = 0 if subscription.get("vat_id") else (charge * 21) // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description("Charge", new_plan["name"], period_end),
            "approved_by": None,
        })

    return lines