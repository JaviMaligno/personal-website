# SPEC: `prorate_seats` (Python module)

Status: draft for review. Items marked ASSUMPTION go beyond the brief and need client or tech lead confirmation before build.

## 1. Interface

**Signature:** `prorate_seats(subscription, new_plan, changed_at) -> list[dict]`

**Input `subscription` (dict):**
- `id`: value copied to `subscription_id`
- `status`: str; only `"trialing"` has special meaning
- `plan_name`: str, the old plan's name (used on credit lines)
- `seat_price_cents`: int, old price per seat per period
- `billable_seats`: int, the only seat count used for billing
- `vat_id`: str or None; presence disables charge VAT
- `period_end`: timezone-aware datetime
- `seats`, `legacy_discount`: present but ignored

**Input `new_plan` (dict):**
- `name`: str, used on charge lines
- `seat_price_cents`: int, new price per seat per period

**Input `changed_at`:** timezone-aware datetime.

**Output:** list of 0 to 2 line dicts, in this order: credit (if any), then charge (if any). Each dict has keys:
- `subscription_id`: from `subscription["id"]`
- `kind`: `"credit"` or `"charge"`
- `amount_cents`: int, pre-VAT amount, non-negative (ASSUMPTION, see open questions)
- `vat_cents`: int; always 0 on credits
- `description`: str, at most 80 code points
- `approved_by`: str on credits; None on charges

All money values are Python ints. No floats anywhere, including intermediates.

## 2. Rules and acceptance criteria

**R1. Trialing gate (checked first).** If `status == "trialing"`, return `[]` before any other check or computation.
- AC: status "trialing" with any prices and dates returns `[]`.

**R2. Billable seats only.** Use `billable_seats` for all amounts. Ignore `seats`.
- AC: with `seats=10, billable_seats=3`, amounts are computed with 3.

**R3. Downgrade gate.** If `new_plan.seat_price_cents < subscription.seat_price_cents`, return `[]`.
- AC: old 1500, new 1000 returns `[]`.

**R4. Days left.** ASSUMPTION: `days_left = floor((period_end - changed_at) / 1 day)`, clamped to the range 0 to 13. Computed with integer arithmetic on the timedelta (for example `(period_end - changed_at) // timedelta(days=1)`), then clamped.
- AC: period_end is exactly 6 days after changed_at gives 6.
- AC: period_end is 6 days and 23 hours after changed_at gives 6.
- AC: period_end is 20 days after changed_at gives 13.

**R5. Credit amount.** `credit_gross = old_price * billable_seats * days_left / 13`, rounded UP to the next cent. Integer form: `-((-(old_price * billable_seats * days_left)) // 13)`.
- Credit uses `subscription.plan_name` in its description.

**R6. Charge amount.** `charge_gross = new_price * billable_seats * days_left / 13`, rounded DOWN. Integer form: `(new_price * billable_seats * days_left) // 13`.
- Charge uses `new_plan.name` in its description.

**R7. Minimum line amount.** ASSUMPTION: a line is dropped if its pre-VAT `amount_cents` is less than 50. An amount of exactly 50 is kept.
- Drop decisions are per line and independent.

**R8. Charge VAT.** ASSUMPTION: VAT is computed from the already-rounded-down charge amount.
- If `vat_id` is truthy (non-empty string), `vat_cents = 0`.
- Otherwise `vat_cents = (amount_cents * 21) // 100` (floor).
- Credits always have `vat_cents = 0`.

**R9. Credit approver.** `approved_by` on a credit is a name string (not an object).
- If `amount_cents > 50000`: ASSUMPTION, currency is EUR, so this is "over €500" and the approver is "Ramón Etxeberria-Goñi".
- Otherwise (including exactly 50000): "Nguyễn Thị Phương Thảo".
- Charges have `approved_by = None`.

**R10. Ordering.** Credit line first, then charge line.

**R11. Descriptions.** See section 4.

**R12. Ignored fields.** `legacy_discount` and `seats` have no effect.

## 3. Worked examples (integer cents)

**E1 (brief example, no vat_id).** old 1000, new 1500, billable_seats 3, days_left 6.
- Credit: ceil(3000 * 6 / 13) = ceil(1384.615...) = 1385. Approver: Nguyễn Thị Phương Thảo.
- Charge: floor(4500 * 6 / 13) = floor(2076.923...) = 2076. VAT: floor(2076 * 21 / 100) = floor(435.96) = 435. approved_by None.
- Output: credit (1385, vat 0), then charge (2076, vat 435).

**E2 (same as E1 with vat_id "DE123").** Charge VAT is 0. Credit unchanged (1385, vat 0).

**E3 (credit over threshold).** old 20000, new 25000, billable_seats 3, days_left 13.
- Credit: 60000 * 13 / 13 = 60000. Over 50000, approver: Ramón Etxeberria-Goñi.
- Charge: 75000. VAT: floor(75000 * 21 / 100) = 15750.

**E4 (credit exactly at threshold).** old 50000, new 60000, billable_seats 1, days_left 13.
- Credit: 50000. Not over 50000, approver: Nguyễn Thị Phương Thảo.
- Charge: 60000, VAT 12600.

**E5 (both lines skipped).** old 100, new 110, billable_seats 1, days_left 1.
- Credit: ceil(100 / 13) = 8, skipped. Charge: floor(110 / 13) = 8, skipped.
- Output: `[]`.

**E6 (only charge kept).** old 100, new 1000, billable_seats 1, days_left 1.
- Credit: 8, skipped. Charge: floor(1000 / 13) = 76, kept. VAT: floor(76 * 21 / 100) = 15.
- Output: one charge line only (76, vat 15).

**E7 (only credit kept).** old 1000, new 100, billable_seats 1, days_left 1 would be a downgrade, so use new 1000 and old 100 is also a downgrade check. Instead: old 1000, new 1000 is the same-price case (see section 5). For a true credit-only case, the new price must be at least the old price while the charge is under 50. This is not reachable with equal per-seat prices and the same days and seats, because floor and ceil differ by at most 1 cent. Credit-only cases occur only when the new price is at least the old price and the charge is under 50 while the credit is 50 or more, which requires a charge that is at least 1 cent less than the credit. Test with old 3900, new 3900, billable_seats 1, days_left 13 is not valid either. Treat credit-only as a boundary case to confirm with the tech lead (see open questions).

**E8 (threshold boundary for charge).** old 10, new 50, billable_seats 1, days_left 13.
- Credit: 10, skipped. Charge: 50, kept. VAT: floor(50 * 21 / 100) = 10.
- Output: one charge line (50, vat 10).

**E9 (downgrade).** old 1500, new 1000, any seats and days. Output: `[]`.

**E10 (trialing).** status "trialing", any values. Output: `[]`.

**E11 (ordering).** For E1, output[0].kind == "credit" and output[1].kind == "charge".

## 4. Description rules

**Templates (ASSUMPTION, for client confirmation):**
- Credit: `Credit for unused {plan} until {YYYY-MM-DD}`
- Charge: `Charge for unused {plan} until {YYYY-MM-DD}`

Fixed text around the name is 35 code points (including the 10-character date). The name allowance is therefore 45 code points.

**Length.** Length is Python `len()` on the `str`, which counts code points, not bytes. No Unicode normalization or grapheme handling is applied (ASSUMPTION).

**Date.** `{YYYY-MM-DD}` is `period_end` formatted in its own timezone. No conversion to UTC or any other zone (ASSUMPTION). The date is never dropped or shortened.

**Truncation.** If the full description is at most 80 code points, use it as is. Otherwise, shorten only the plan name:
- Keep the name if it fits in 45 code points.
- Otherwise use the first 42 code points of the name, then `...` (three ASCII dots, ASSUMPTION), for 45 total.

**Example D1.** A plan name of 60 characters with the credit template gives `Credit for unused ` + 42 chars + `...` + ` until 2026-10-20`. Total length 80.

**Empty or unusable name.** The fixed text is 35 code points, so an empty name always fits. The case where even the minimal text exceeds 80 cannot occur with these templates. If templates change, see open questions.

## 5. Edge cases

- **Both lines under 50 cents:** return `[]`. **One line under 50 cents:** return only the other line.
- **changed_at at or after period_end:** ASSUMPTION, days_left is 0, both amounts are 0, both lines are dropped, output is `[]`. Needs explicit confirmation.
- **New price equal to old price:** the brief says "cheaper" for downgrades, so equal price is not a downgrade. ASSUMPTION: normal processing. Credit is ceil(x) and charge is floor(x) for the same x, so the two lines can be equal or differ by 1 cent, and both are emitted if at least 50. This produces an offsetting pair with no economic effect. Open question, alternative is `[]`.
- **Naive datetimes (either input naive, or mixed awareness):** ASSUMPTION, raise `ValueError`. The brief states all datetimes are aware, so this is defensive. Needs confirmation.
- **Zero billable_seats:** days_left and seats give amount 0 for both lines, output `[]`. ASSUMPTION; flagged for confirmation.
- **Trialing check:** occurs before any other check, including datetime validation (ASSUMPTION on ordering with R7 naive-datetime check; the trialing gate is first in the rule order).
- **Non-trialing statuses (for example canceled, past_due):** brief is silent. ASSUMPTION: processed normally. Open question.
- **Negative inputs (seat counts or prices):** not specified. ASSUMPTION: out of scope; behaviour undefined. Open question.
- **vat_id:** present means a non-empty string. Whitespace-only strings: open question.

## 6. Explicit answers to known gaps

- **Currency for the €500 threshold:** the brief has no currency field. ASSUMPTION: EUR. Compared on credit `amount_cents` in cents, strictly greater than 50000. Exactly 50000 goes to the standard approver.
- **Both or one skipped:** section 5. Per-line drop, independent.
- **Days left counting:** ASSUMPTION, whole days, floored, from the exact timedelta, clamped to 0 to 13. Fractional-day proration is not used. Open question.
- **Rounding method:** the period fraction is applied to the whole product (old or new price times seats times days, divided by 13), rounded once at the end. Credit rounds up, charge rounds down.
- **VAT from rounded charge:** ASSUMPTION, yes. VAT is floored from the already-floored charge amount.
- **changed_at at or after period_end:** section 5, output `[]`, needs confirmation.
- **Same-price change:** section 5, normal processing, needs confirmation.
- **50-cent threshold before or after VAT:** ASSUMPTION, before VAT (on pre-VAT `amount_cents`).
- **80-char limit scope:** ASSUMPTION, it covers the full description string. Shortening rule in section 4.
- **approved_by on credits:** a name string.

## 7. Open questions

For Ingrid (client):
1. Is the currency EUR? Should the €500 threshold be exactly "amount_cents > 50000"?
2. Is the 50-cent minimum applied before or after VAT? (Spec assumes before.)
3. Is whole-day counting (floor) correct, or should partial days be prorated by the second? Whole days reduce both credit and charge, which is customer-favourable.
4. Is it correct that a change at or after period_end produces no lines?
5. For a same-price change, should we return `[]` instead of an offsetting credit and charge?
6. Are the description templates acceptable? Is the name truncation with `...` acceptable?
7. Should `amount_cents` on a credit be positive (with `kind` giving direction) or negative? Spec assumes positive.
8. Should non-trialing statuses such as canceled or past_due be prorated?

For the tech lead:
9. Naive datetimes: raise `ValueError` (spec) or something else?
10. Input validation: should non-int prices or seat counts, negative values, or a non-empty whitespace-only `vat_id` be rejected, and how?
11. Confirm the order of checks: trialing first, then downgrade, then the date and seat logic.
12. The credit-only boundary case (section 3, E7) is not constructed; confirm whether it can occur and whether a test case is needed.
13. If description templates change, what is the required fallback when even the minimal text exceeds 80 code points?