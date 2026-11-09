# Fernhollow Studios: Seat Upgrade Proration Module (Design Plan)

## 1. Module layout and function steps

**Layout:** one file, `proration.py`, standard library only (`datetime`, `fractions`, `math`). It contains:

- Named constants: `PERIOD_DAYS = 13`, `VAT_RATE_PERCENT = 21`, `MIN_LINE_CENTS = 50`, `APPROVAL_THRESHOLD_CENTS = 50_000` (ASSUMPTION, see Q4), `CONTROLLER = "Nguyễn Thị Phương Thảo"`, `SENIOR_APPROVER = "Ramón Etxeberria-Goñi"`, `MAX_DESC_LEN = 80`.
- Private helpers: `_validate`, `_unused_ratio`, `_round_half_up_vat`, `_describe`, `_approver`.
- One public function, `prorate_seats(subscription, new_plan, changed_at)`.

**Steps inside `prorate_seats`:**

1. **Validate.** Check required keys. Require `changed_at` and `period_end` to be timezone-aware. Require seat prices and `billable_seats` to be non-negative ints. Never read `seats` or `legacy_discount`.
2. **Status gate.** `trialing` returns `[]`. Other statuses follow Q6.
3. **Price gate.** If `new_plan` price is lower than or equal to the old price, return `[]`.
4. **Period window.** `period_start = period_end - 13 days`. If `changed_at >= period_end`, return `[]`. If `changed_at < period_start`, raise `ValueError` (Q7).
5. **Unused ratio.** Compute `ratio = Fraction(unused_microseconds, 13 * 86400 * 10**6)` from integer microseconds, so no floats are used.
6. **Raw amounts.** `raw_credit = old_price * billable_seats * ratio`, and `raw_charge = new_price * billable_seats * ratio`.
7. **Directional rounding.** `credit_cents = math.ceil(raw_credit)` and `charge_cents = math.floor(raw_charge)`. This happens before the skip check, so a credit of 49.01 cents becomes 50 and is kept.
8. **Skip.** Drop any line whose net amount is under 50 cents (Q5).
9. **VAT.** Credits get `vat_cents = 0`. Charges get `0` if `vat_id` is set (reverse charge), otherwise `(charge_cents * 21 + 50) // 100`, which is half-up integer math (Q2).
10. **Approval.** Credits get the controller's name. If `amount_cents > APPROVAL_THRESHOLD_CENTS`, they get the senior approver's name instead. Charges get `None`.
11. **Descriptions.** Build each description, shortening only the plan name if needed (Q3).
12. **Assemble.** Return `[credit_line?, charge_line?]`, so credits always precede charges.

**Data shape of each line:** `{"subscription_id": str, "kind": "credit"|"charge", "amount_cents": int, "vat_cents": int, "description": str, "approved_by": str|None}`

## 2. Test plan

Test order: credit calculation first, then the other areas.

**A. Credit calculation (first priority)**
- Old price 1200, billable 5, 6 unused days of 13: raw credit is 36000/13 = 2769.23, so expect `2770`.
- Same case, new price 1800: raw charge is 54000/13 = 4153.85, so expect `4153`.
- Exact case: old price 1300, billable 1, unused 13 days (`changed_at = period_start`): expect `1300`, no rounding.
- Ignore `seats`: set `seats` to 99 with `billable_seats` 5, and confirm the result matches the 5-seat case.
- Ignore `legacy_discount`: adding it changes nothing.
- Fractional day with a time component: confirm the result uses exact microseconds (Q1).

**B. Rounding edge cases**
- Credit of 49.01 cents rounds up to 50 and is kept. Charge of 49.99 cents rounds down to 49 and is skipped.
- Half-cent VAT: charge 4153 gives `(4153*21+50)//100 = 872`.
- Zero billable seats: returns `[]`.
- Result is always `int`, never `float`.

**C. Downgrade and equal price**
- New price lower than old: `[]`.
- New price equal to old, name changed: `[]` (Q9).

**D. Trial and other statuses**
- `status="trialing"`: `[]`, even with a valid window and an upgrade.
- `canceled`, `past_due`, and an unknown status: check against the Q6 default.

**E. VAT**
- Charge with no `vat_id`: `vat_cents` equals 21% of the charge (half-up).
- Charge with `vat_id`: `vat_cents == 0`.
- Credit with and without `vat_id`: `vat_cents == 0` in both cases.

**F. Approval threshold**
- Credit exactly 50000 cents: approved by the controller.
- Credit 50001 cents: approved by the senior approver.
- Every charge: `approved_by is None`.

**G. Description length and content**
- Normal names: description is at most 80 characters and contains the date as `YYYY-MM-DD`.
- Very long plan name: shortened, date unchanged, length at most 80.
- Plan name that cannot fit: raises rather than truncating the date.

**H. Ordering**
- Credit and charge both present: credit first.
- Only one line present: correct kind.

**I. 50-cent skip**
- Net amount 49 is skipped. 50 is kept.
- Net amount under 50 whose VAT would push it over 50: still skipped (default, Q5).

**J. Boundaries**
- `changed_at == period_end`: `[]`.
- `changed_at == period_start`: full 13-day credit.
- `changed_at < period_start`: raises `ValueError`.
- Naive datetime: raises.

## 3. Open questions (each with a proposed default)

These must be resolved before implementation. Each default is an ASSUMPTION not yet confirmed by the client.

- **Q1. Fractional days (a).** ASSUMPTION: use exact elapsed time as a fraction of 13 days, not whole days. This avoids biasing the result either way.
- **Q2. VAT rounding on charges (b).** ASSUMPTION: VAT is computed on the net charge after directional rounding, rounded half-up to the cent.
- **Q3. Description wording and shortening (c).** ASSUMPTION: `"Credit {plan} seats to {YYYY-MM-DD}"` and `"Charge {plan} seats to {YYYY-MM-DD}"`. If too long, the plan name is cut and suffixed with `...`. The date is never changed. If the date cannot fit, raise.
- **Q4. Currency and approval threshold.** The data does not state a currency. ASSUMPTION: amounts are EUR, and the €500 rule applies to the pre-VAT credit amount, which equals the credit amount. Strictly over €500 goes to the senior approver. Ingrid must confirm both points. Until then, mark this as an open item.
- **Q5. Under-50-cent skip base.** ASSUMPTION: the test applies to the net amount, before VAT.
- **Q6. Other statuses.** ASSUMPTION: `trialing`, `canceled`, and `past_due` return `[]`. Any unknown status raises `ValueError`.
- **Q7. `changed_at` outside the period.** ASSUMPTION: at or after `period_end` returns `[]`. Before `period_start` raises `ValueError`.
- **Q8. Timezone for the period-end date in descriptions.** ASSUMPTION: format the date in the timezone of `period_end` as provided, with no conversion.
- **Q9. Equal price with a plan-name change.** ASSUMPTION: not an upgrade, so return `[]`.
- **Q10. Rounding direction versus house rule.** The house rule is half-up. The spec overrides it with ceiling for credits and floor for charges. ASSUMPTION: the directional rule applies to credits and charges, and half-up applies only to VAT. Ingrid should confirm.

## 4. Risks

- **Currency is unconfirmed (Q4).** If the amounts are not EUR, approval routing is wrong. This is the most serious open risk.
- **Rounding conflict (Q10).** Directional rounding conflicts with the house rule. Either outcome may be correct, so confirm before building.
- **Credit precision is the top priority.** Use integer or Fraction arithmetic throughout. Any float in the credit path would break the exact-cent requirement.
- **Credit and charge are not reconciled.** Each is rounded separately, so the net of the two may differ by a cent from an exact calculation. Document this for finance.
- **Thirteen-day period is not a calendar.** The fixed 13-day basis may not match what customers expect from calendar-month billing. Confirm the business intent.
- **Reverse-charge invoices.** Zero VAT when `vat_id` is set may require a legal note on the PDF template. Check with finance.
- **Unicode names.** The approver names contain diacritics. Keep the source file as UTF-8 and confirm the PDF template renders them.
- **Silent skips.** The 50-cent rule can drop a line without any signal to the caller. Consider logging skipped lines.