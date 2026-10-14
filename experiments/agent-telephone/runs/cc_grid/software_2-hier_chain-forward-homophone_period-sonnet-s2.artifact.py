"""Seat-upgrade proration for Fernhollow Studios.

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list of line dicts
with keys subscription_id, kind, amount_cents, vat_cents, description, approved_by.
Integer arithmetic only.

Decisions (including points the brief leaves open):
- PERIOD_DAYS = 13. days_left = (period_end date - changed_at date).days, with
  changed_at converted to period_end's timezone; the dates are compared, partial
  days are ignored. Naive datetimes raise ValueError.
- days_left <= 0 -> []. days_left > 13 is CLAMPED to 13 (alternative: reject). OPEN QUESTION.
- status "trialing" -> []. All other statuses are processed normally; the brief does
  not say what to do for e.g. "cancelled" (arguably []). OPEN QUESTION.
- Seats come from billable_seats, never from seats. Missing, None, negative, bool or
  non-int values raise ValueError. 0 seats gives [] (all lines fall below the minimum).
  The same seat count is used for the old and the new plan, so the net of the two lines
  equals (new - old) * seats * days / 13 only up to rounding.
- Downgrade (new price < old price) -> []. Equal price is not a downgrade: both a credit
  and a charge are produced (odd, possibly [] is better). OPEN QUESTION.
- credit = ceil(old_price * seats * days_left / 13), via -(-a // b).
  charge = floor(new_price * seats * days_left / 13), via //.
- Minimum: each line is judged independently on its rounded amount; amount < 50 is
  skipped (exactly 50 is kept). One line may be kept while the other is skipped.
- Approver: credit amount strictly greater than 50000 cents (EUR 500) ->
  Ramon Etxeberria-Goni, otherwise Nguyen Thi Phuong Thao (with their original Unicode
  spelling). Charges have approved_by None.
- VAT: charges only. 0 if vat_id is truthy (reverse charge), else 21% of the rounded
  charge, rounded DOWN (charge * 21 // 100). The brief does not specify VAT rounding
  direction; down mirrors the charge rule. The house default (half-up) was overridden
  on the architect's instruction. OPEN QUESTION. Credits always have vat_cents 0 (the
  brief says credits never carry VAT; this overrides the generic "VAT on every line").
- Order: credit first, then charge. legacy_discount is ignored.
- Description: "Credit unused <old plan> seats until YYYY-MM-DD" and
  "Charge <new plan> seats until YYYY-MM-DD", at most 80 code points. Only the plan name
  is shortened, with a single "…" appended. If not even an empty name leaves room for
  the ellipsis, the name is empty. If the fixed text alone exceeds 80, fall back to
  "<Credit|Charge> YYYY-MM-DD". The date is always kept. The date is period_end's own
  date in its own timezone.
- Inputs are never mutated.
"""

PERIOD_DAYS = 13
MIN_LINE_CENTS = 50
BIG_CREDIT_CENTS = 50000
VAT_PERCENT = 21
MAX_DESC = 80
APPROVER = "Nguyễn Thị Phương Thảo"
BIG_APPROVER = "Ramón Etxeberria-Goñi"


def _aware(dt, label):
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _description(kind_word, template, name, date_str):
    full = template.format(name=name, date=date_str)
    if len(full) <= MAX_DESC:
        return full
    fixed = len(template.format(name="", date=date_str))
    if fixed > MAX_DESC:
        return f"{kind_word} {date_str}"
    avail = MAX_DESC - fixed
    short = name[: avail - 1] + "…" if avail >= 1 else ""
    return template.format(name=short, date=date_str)


def _seats(subscription):
    seats = subscription.get("billable_seats")
    if seats is None or isinstance(seats, bool) or not isinstance(seats, int):
        raise ValueError("billable_seats must be a non-negative int")
    if seats < 0:
        raise ValueError("billable_seats must be a non-negative int")
    return seats


def prorate_seats(subscription, new_plan, changed_at):
    period_end = subscription["period_end"]
    _aware(period_end, "period_end")
    _aware(changed_at, "changed_at")

    if subscription.get("status") == "trialing":
        return []

    days_left = (period_end.date() - changed_at.astimezone(period_end.tzinfo).date()).days
    if days_left <= 0:
        return []
    days_left = min(days_left, PERIOD_DAYS)

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    seats = _seats(subscription)
    date_str = period_end.date().isoformat()
    sub_id = subscription["id"]
    lines = []

    credit = -(-(old_price * seats * days_left) // PERIOD_DAYS)
    if credit >= MIN_LINE_CENTS:
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,
            "description": _description(
                "Credit", "Credit unused {name} seats until {date}",
                subscription["plan_name"], date_str),
            "approved_by": BIG_APPROVER if credit > BIG_CREDIT_CENTS else APPROVER,
        })

    charge = (new_price * seats * days_left) // PERIOD_DAYS
    if charge >= MIN_LINE_CENTS:
        vat = 0 if subscription.get("vat_id") else charge * VAT_PERCENT // 100
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat,
            "description": _description(
                "Charge", "Charge {name} seats until {date}",
                new_plan["name"], date_str),
            "approved_by": None,
        })

    return lines