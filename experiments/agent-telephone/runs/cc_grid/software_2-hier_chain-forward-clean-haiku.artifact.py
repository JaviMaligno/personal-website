# Design: prorate_seats (Fernhollow Studios seat upgrades)

## (a) Design

**1. Entry point and output.** `prorate_seats(subscription, new_plan, changed_at)` returns a list of dicts with exactly these keys: `subscription_id`, `kind` ("credit" or "charge"), `amount_cents` (int), `vat_cents` (int), `description` (str), `approved_by` (str or None, None on charges). The credit line comes first and the charge line second.

**2. Period and days left.** The period is always 30 days. `period_start` is derived as `period_end - 30 days`, because the brief has no `period_start` field. Days left is the whole number of days from `changed_at` to `period_end`, computed as floor of the timedelta divided by one day. Days left is clamped to the range [0, 30]. (Open questions Q1 to Q3.)

**3. Arithmetic.** All money is integer cents. No floats and no Decimal. Multiply all integer factors first and divide once at the end.
- Credit: `credit_cents = ceil(old_seat_price_cents * billable_seats * days_left / 30)`, using integer ceiling division.
- Charge: `charge_cents = floor(new_seat_price_cents * billable_seats * days_left / 30)`, using integer floor division.
- Worked example: old price 1001, billable_seats 1, days_left 10 gives a credit of 334 (333.67 rounded up).

**4. Seat count and legacy field.** Only `billable_seats` is used. `seats` is never read. `legacy_discount` is never read, so its presence or absence has no effect.

**5. Skip rule.** A line whose pre-VAT `amount_cents` is strictly less than 50 is omitted from the output. Each line is evaluated independently. A skipped credit does not suppress the charge, and a skipped charge does not suppress the credit. (Q4.)

**6. Downgrade.** A downgrade is `new_plan.seat_price_cents < subscription.seat_price_cents`, strictly. A downgrade returns `[]`. Equal price is not a downgrade under this rule, so both lines are computed and may be equal in amount. (Q5.)

**7. VAT.**
- Credits always have `vat_cents = 0`. This is fixed by the brief.
- Charges with a `vat_id` that is a non-empty string (after no trimming) have `vat_cents = 0` (reverse charge).
- Charges with no `vat_id`, or with a `vat_id` that is an empty or whitespace-only string, have VAT at 21%. The rounding mode is open (Q6 and Q7). The architect's draft uses floor. The house rule is half-up, which is the default unless the brief says otherwise. The brief's "never round in our favour" does not clearly cover VAT. My recommendation is half-up, with floor as the alternative.

**8. Status.** A status of "trialing" returns `[]`. This is fixed by the brief. Other statuses are not addressed by the brief. The default is to prorate normally. (Q8.)

**9. Approval.**
- Credit: `approved_by` is "Nguyễn Thị Phương Thảo". It becomes "Ramón Etxeberria-Goñi" only if `amount_cents` is strictly greater than 50000.
- Charge: `approved_by` is None.
- The threshold assumes amounts are EUR cents. No exchange rate is applied. (Q9.)

**10. Description.**
- Credit: `"Credit: {subscription.plan_name} until {YYYY-MM-DD}"`.
- Charge: `"Charge: {new_plan.name} until {YYYY-MM-DD}"`.
- The date is the calendar date of `period_end` in its own timezone. (Q10.)
- Text is NFC-normalised before measuring, and length is counted in Unicode code points.
- Maximum length is 80 code points. If the full text fits, use it.
- Otherwise truncate only the plan name so the result fits. Strip trailing whitespace from the truncated name, then append a single U+2026 ellipsis. The date is never truncated.
- If the template itself cannot fit, raise ValueError. This is unreachable in practice, because the fixed overhead is about 25 code points. (Q11.)

**11. Timezones.** Every datetime argument must be timezone-aware. A naive datetime raises ValueError. Aware datetimes are compared and subtracted directly, with no conversion.

**12. Edge cases and validation.**
- `changed_at >= period_end` returns `[]`.
- `billable_seats == 0` returns `[]`.
- `days_left == 0` returns `[]`. Both amounts round to zero and are skipped.
- A bool or float for any price, seat count, or amount raises TypeError.
- Negative prices or seat counts raise ValueError. (Q12.)

**13. Ordering and composition.** Credit before charge. If one line is skipped or absent, the output contains only the other. If both are absent, the output is `[]`.

## (b) Open questions

Each default is UNCONFIRMED.

- **Q1. Period start.** The brief has no `period_start` field. Options: (a) derive it as `period_end - 30 days` (UNCONFIRMED default); (b) require the field from the caller.
- **Q2. Partial days.** Options: (a) whole days, floor (UNCONFIRMED default); (b) fractional days, which would change the arithmetic.
- **Q3. changed_at before period_start.** Options: (a) clamp days_left to 30 (UNCONFIRMED default); (b) raise ValueError.
- **Q4. Skip threshold basis.** Options: (a) test pre-VAT amount, strictly under 50 (UNCONFIRMED default); (b) test the amount including VAT. The brief says "line under 50 cents" without specifying.
- **Q5. Equal price.** Options: (a) compute both lines (UNCONFIRMED default, follows the strict reading of "cheaper"); (b) return `[]` for equal price. The client should decide.
- **Q6. Charge VAT rounding.** The brief says "never round in our favour" but does not say how VAT rounds. Options: (a) round half-up, the house rule (UNCONFIRMED recommended default); (b) floor, the customer-favourable reading (architect's draft); (c) ceil. Note that the architect's floor default departs from the house half-up rule. The client should confirm which applies.
- **Q7. VAT on blank vat_id.** Options: (a) treat empty and whitespace-only as absent, so VAT applies (UNCONFIRMED default); (b) treat any non-None value as present, so reverse charge applies. The brief says only "unless the customer has a vat_id".
- **Q8. Statuses other than trialing.** The brief is silent. Options: (a) prorate normally (UNCONFIRMED default); (b) return `[]`; (c) raise for unknown statuses.
- **Q9. Currency and threshold.** The threshold of EUR 500 is taken as 50000 cents, which assumes all amounts are EUR. The subscription has no currency field. Client question: what currency are amounts in, and is there a per-customer currency field? Default is EUR cents, threshold 50000, strict greater-than (UNCONFIRMED). No exchange rate is to be invented.
- **Q10. Date timezone.** Options: (a) `period_end`'s own timezone (UNCONFIRMED default); (b) Europe/Lisbon; (c) UTC.
- **Q11. Template overflow.** Options: (a) raise ValueError if the template cannot fit (UNCONFIRMED default); (b) truncate the date. The brief says the date must never be truncated, so (b) is ruled out.
- **Q12. Negative inputs.** Options: (a) raise ValueError (UNCONFIRMED default); (b) return `[]`.
- **Q13. billable_seats above seats.** The brief does not say whether this is an error. Default: no check is made (UNCONFIRMED). Tech lead to confirm.
- **Q14. Scope priority.** The brief says that if scope is cut, the credit calculation matters more than VAT. This is recorded as a priority, not a question, and should guide any trade-offs.

## (c) Acceptance criteria

1. Credit example: old price 1001, billable_seats 1, days_left 10 (changed_at is exactly 10 days before period_end) gives a credit line with `amount_cents` 334.
2. Charge example: new price 1001, billable_seats 1, days_left 10 gives a charge line with `amount_cents` 333.
3. Exact division: old price 300, billable_seats 1, days_left 10 gives a credit of exactly 100, not 101.
4. A credit of exactly 50 cents is kept.
5. A credit of 49 cents is dropped.
6. A charge of exactly 50 cents is kept, and one of 49 cents is dropped.
7. A dropped credit does not remove a kept charge, and a dropped charge does not remove a kept credit.
8. A credit of exactly 50000 cents has `approved_by` "Nguyễn Thị Phương Thảo".
9. A credit of 50001 cents has `approved_by` "Ramón Etxeberria-Goñi".
10. Every charge line has `approved_by` None.
11. Every credit line has `vat_cents` 0.
12. A charge with `vat_id` None has VAT applied at 21% using the rounding mode chosen in Q6.
13. A charge with `vat_id` "" is treated as absent, so VAT applies.
14. A charge with `vat_id` "   " is treated as absent, pending Q7.
15. A charge with `vat_id` "DE123456789" has `vat_cents` 0.
16. A subscription with new price lower than old price returns `[]`.
17. Equal prices follow the choice made in Q5.
18. A subscription with status "trialing" returns `[]`.
19. `changed_at` equal to or after `period_end` returns `[]`.
20. `billable_seats` 0 returns `[]`.
21. Days_left 0 returns `[]`.
22. The result uses `billable_seats` and ignores `seats`. Changing `seats` alone does not change any amount.
23. The result is the same whether or not `legacy_discount` is present.
24. A naive datetime for `changed_at` or `period_end` raises ValueError.
25. A bool or float amount or seat count raises TypeError.
26. A negative price or seat count raises ValueError, pending Q12.
27. Output lists credit before charge.
28. If both lines are skipped, the output is `[]`.
29. Every output dict has exactly the keys `subscription_id`, `kind`, `amount_cents`, `vat_cents`, `description`, `approved_by`.
30. Every `amount_cents` and `vat_cents` value is an int.
31. Every description is at most 80 code points and contains the date in YYYY-MM-DD form.
32. When truncation is needed, only the plan name is shortened, the text ends with U+2026, and there are no trailing spaces before the ellipsis.
33. A plan name in decomposed Unicode form and the same name in composed form produce descriptions of the same length.
34. The description date equals the calendar date of `period_end` in the timezone chosen in Q10.