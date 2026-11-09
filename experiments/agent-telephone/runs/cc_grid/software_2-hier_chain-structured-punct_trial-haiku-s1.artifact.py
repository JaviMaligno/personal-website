# -*- coding: utf-8 -*-
# Target path: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-grdxybvt/seat_proration.py
# STATUS: NOT WRITTEN TO DISK AND NOT RUN. This agent has no file or shell tools.
# The content below must be saved to the path above by a tool-enabled agent.
# No test file was written and no test results exist.
"""Seat upgrade proration for Fernhollow Studios (client contact: Ingrid).

Entry point: prorate_seats(subscription, new_plan, changed_at) -> list of dict.

REPORT TO ARCHITECT
(a) Files: this module only (path in header). No test file written, no tests run.
(b) Design: exact Fraction arithmetic, no floats, no Decimal. Unused fraction of the
    30-day period -> credit (ceil to cent) and charge (floor to cent) in integer cents.
    Rounding uses exact integer arithmetic on Fraction numerator/denominator rather than
    Decimal.quantize, because the 30-day period in microseconds has factor 3 and so no
    decimal context represents the exact value; quantize at default precision could
    round across a cent boundary. Results equal ROUND_CEILING and ROUND_FLOOR.
(c) Assumptions (each isolated and tagged "# OPEN O#" or "# C#" in code):
    O1  Fractional days: exact microseconds / 30-day microseconds, no truncation.
    O2  changed_at >= period_end -> [].
    O3  R10 threshold applied to pre-VAT amount.
    O4  VAT on charges = floor(charge * 21 / 100), integer cents. UNRESOLVED.
    O5  Equal price is not a downgrade; prorate normally.
    O6  Only status "trialing" is skipped; all other statuses prorate.
    O7  All amounts are EUR cents; no currency field in output.
    O8  Description "{Credit|Charge}: {plan} seats, period end {YYYY-MM-DD}"; if over 80
        chars, plan name truncated with "..." and full date kept. Date taken in
        period_end's own timezone.
    C1  Unused fraction clamped to [0, 1].
    C2  Ramon approver only if credit is strictly greater than 50000 cents; exactly
        50000 gets the Thao approver.
    C3  A line dropped by R10 is simply omitted; survivor keeps R12 order.
    C4  If even an empty plan name cannot fit, the description is returned over 80
        chars (flagged).
(d) Other ambiguities: R1 types assumed datetime (not strings) for period_end and
    changed_at. "Has a vat_id" treated as truthy check (None or empty = no VAT id).
    Credit approver is decided on the credit amount, which is net because credits carry
    no VAT. R10 applies to charges as well, so a credit can survive while the charge is
    dropped or the reverse (C3). Downgrade is strictly less-than new price (O5).
(e) Tests: none run.
"""

from datetime import timedelta
from fractions import Fraction

PERIOD_DAYS = 30  # R4: a billing period always counts as 30 days.
_PERIOD_MICROS = PERIOD_DAYS * 24 * 60 * 60 * 10**6

VAT_PERCENT = 21  # R11
MIN_LINE_CENTS = 50  # R10: lines under 50 cents dropped; 50 kept. Applied per O3.
LARGE_CREDIT_CENTS = 50000  # R15 / C2: strictly greater than this.
APPROVER_DEFAULT = "Nguyễn Thị Phương Thảo"  # R15 finance controller
APPROVER_LARGE = "Ramón Etxeberria-Goñi"  # R15 large credit approver
DESCRIPTION_MAX = 80  # R14
ELLIPSIS = "..."  # O8


def unused_fraction(changed_at, period_end):
    """R4, R5, O1, C1: unused part of the 30-day period, exact Fraction in [0, 1]."""
    # O1: exact fractional days, whole microseconds, no truncation to days.
    micros = (period_end - changed_at) // timedelta(microseconds=1)
    fraction = Fraction(micros, _PERIOD_MICROS)
    # C1: clamp so a changed_at before the period start cannot credit more than one period.
    return min(max(fraction, Fraction(0)), Fraction(1))


def _ceil_cents(amount):
    """R6 helper: exact round-up to whole cents, returns int."""
    return -((-amount.numerator) // amount.denominator)


def _floor_cents(amount):
    """R7 helper: exact round-down to whole cents, returns int."""
    return amount.numerator // amount.denominator


def credit_amount_cents(old_price_cents, billable_seats, fraction):
    """R6, R3: credit for unused old plan, rounded up. Uses billable_seats only."""
    return _ceil_cents(Fraction(old_price_cents * billable_seats) * fraction)


def charge_amount_cents(new_price_cents, billable_seats, fraction):
    """R7, R3: charge for unused new plan, rounded down. Uses billable_seats only."""
    return _floor_cents(Fraction(new_price_cents * billable_seats) * fraction)


def vat_cents_for_charge(charge_cents, vat_id):
    """R11, O4: VAT on a charge. Reverse charge (vat_id set) gives 0.
    O4: floor(charge * 21 / 100) as integer cents. UNRESOLVED."""
    if vat_id:
        return 0
    return charge_cents * VAT_PERCENT // 100


def describe_line(kind, plan_name, period_end):
    """R14, O8, C4: '{kind}: {plan} seats, period end YYYY-MM-DD', at most 80 chars."""
    prefix = f"{kind}: "
    suffix = f" seats, period end {period_end.date().isoformat()}"
    room = DESCRIPTION_MAX - len(prefix) - len(suffix)  # chars left for the plan name
    name = plan_name
    if len(name) > room:
        if room >= len(ELLIPSIS):
            name = name[: room - len(ELLIPSIS)] + ELLIPSIS
        elif room >= 0:
            name = ELLIPSIS[:room]
        else:
            # C4: even an empty name does not fit with the date. Flagged; over-long result.
            name = ""
    return prefix + name + suffix


def approver_for_credit(amount_cents):
    """R15, C2: approver for a credit line. Charges have no approver (handled by caller)."""
    if amount_cents > LARGE_CREDIT_CENTS:
        return APPROVER_LARGE
    return APPROVER_DEFAULT


def prorate_seats(subscription, new_plan, changed_at):
    """Return invoice lines for a seat upgrade: credit line first, then charge line."""
    # R9, O6: trialing is not prorated. Other statuses prorate normally.
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]

    # R8, O5: strictly lower new price is a downgrade, applied at renewal. Equal prorates.
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]

    # O2: changed_at at or after period_end gives no lines.
    if changed_at >= period_end:
        return []

    fraction = unused_fraction(changed_at, period_end)  # R4, R5
    seats = subscription["billable_seats"]  # R3: never read `seats`
    sub_id = subscription["id"]
    lines = []

    credit = credit_amount_cents(old_price, seats, fraction)  # R6
    if credit >= MIN_LINE_CENTS:  # R10, O3 (pre-VAT; credits carry no VAT)
        lines.append({
            "subscription_id": sub_id,
            "kind": "credit",
            "amount_cents": credit,
            "vat_cents": 0,  # R11: credits never carry VAT
            "description": describe_line("Credit", subscription["plan_name"], period_end),
            "approved_by": approver_for_credit(credit),  # R15
        })

    charge = charge_amount_cents(new_price, seats, fraction)  # R7
    if charge >= MIN_LINE_CENTS:  # R10, O3 (pre-VAT net amount)
        lines.append({
            "subscription_id": sub_id,
            "kind": "charge",
            "amount_cents": charge,
            "vat_cents": vat_cents_for_charge(charge, subscription["vat_id"]),  # R11, O4
            "description": describe_line("Charge", new_plan["name"], period_end),
            "approved_by": None,  # R15: charges have no approver
        })

    return lines