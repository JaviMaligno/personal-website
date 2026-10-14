1. SPECIFICATION

1.1 Interface

prorate_seats(subscription: dict, new_plan: dict, changed_at: datetime) -> list[dict]

Input:
- subscription: id, status, plan_name, seat_price_cents, seats (ignored), billable_seats, vat_id (may be absent or None), period_end (tz-aware datetime).
- new_plan: name, seat_price_cents.
- changed_at: tz-aware datetime.

Output: list of dicts with keys subscription_id, kind ("credit" or "charge"), amount_cents (int), vat_cents (int), description (str, at most 80 characters), approved_by (str for credits, None for charges). Order is always credit first, then charge. The list is empty when no lines apply.

Module constraints: standard library only, Python 3.12, one public function. Use integer arithmetic only (no float anywhere), for example fractions.Fraction or integer numerator and denominator with explicit ceil and floor helpers.

1.2 Data rules

- seat_price_cents, billable_seats and new_plan seat_price_cents must be int, not bool, and not negative. Anything else raises ValueError (proposed; see Q9).
- seats is never read. It is not validated and not used.
- legacy_discount is never read.
- period_end and changed_at must be tz-aware. Naive datetimes raise ValueError (proposed). All comparisons and arithmetic are done on aware instants, so differing offsets must not change the result.
- The period length is a fixed 30 days (2,592,000 seconds), regardless of calendar month.
- The period start is not in the input. It is implied as period_end minus 30 days (proposed; see Q5).

1.3 Calculation steps

1. If status == "trialing", return [].
2. If new_plan seat_price_cents < old seat_price_cents, this is a downgrade: return []. (Equal price handling is open, see Q4.)
3. unused_us = period_end - changed_at in microseconds. If unused_us <= 0 (changed_at on or after period_end), return [] (proposed; see Q6).
4. Exact (unrounded) amounts, as rationals:
   credit_exact = old_price * billable_seats * unused_us / (30 * 86400 * 10**6)
   charge_exact = new_price * billable_seats * unused_us / (30 * 86400 * 10**6)
   The product is taken once, then divided once. There is no intermediate rounding of per-day or per-seat values (proposed; see Q7).
5. credit_cents = ceil(credit_exact). Rounding up means the customer receives at least the exact credit.
   charge_cents = floor(charge_exact). Rounding down means the customer pays at most the exact charge.
   Both directions favour the customer, which matches the "never round in our favour" rule.
6. Minimum line value: a line with amount_cents < 50 is omitted entirely, including its VAT. The test is on the net amount before VAT (proposed; see Q3). Each line is tested independently.
7. Credit line (if not skipped): vat_cents = 0 (brief: credits never carry VAT). approved_by = "Win Tee Fung Tao" if amount_cents <= 50000, otherwise "Ramon Etxeberria-Goñi" (threshold proposed; see Q2).
8. Charge line (if not skipped): if vat_id is present (not None and not empty), vat_cents = 0 (reverse charge). Otherwise vat_cents = 21% of charge_cents, rounding mode to be confirmed (see Q8). approved_by = None.
9. Descriptions (proposed template, see Q10):
   Credit: "Unused {old_plan_name} seats to {YYYY-MM-DD}"
   Charge: "Unused {new_plan_name} seats to {YYYY-MM-DD}"
   The date is period_end rendered as YYYY-MM-DD in period_end's own offset (see Q11). If the full string exceeds 80 characters, shorten the plan name first. The date is never shortened. With the proposed template the fixed overhead is 27 characters, leaving 53 for the plan name. If the name cannot fit in the remaining space, raise an error instead of truncating the date (proposed).
10. Return credit line (if present) followed by charge line (if present).

1.4 Acceptance criteria and worked examples

A1. Trialing subscription (status "trialing") with any valid inputs returns [].

A2. Downgrade: old price 1500, new price 1000, any valid changed_at inside the period. Returns [].

A3. Standard upgrade, no vat_id. Old price 1000, new price 1500, billable_seats 10, changed_at exactly 15 days before period_end (at midnight, so whole days and fractional-day interpretations agree).
   Credit: 1000 * 10 * 15 / 30 = 5000 exactly. amount 5000, vat 0, approved_by "Win Tee Fung Tao".
   Charge: 1500 * 10 * 15 / 30 = 7500 exactly. amount 7500, vat 1575 (21% of 7500).
   Output order: credit, then charge.

A4. Rounding asymmetry. Old price 999, new price 1001, billable_seats 3, 7 unused days (changed_at 7 days before period_end, at midnight).
   Credit exact: 999 * 3 * 7 / 30 = 699.3, so credit is 700 (rounded up).
   Charge exact: 1001 * 3 * 7 / 30 = 700.7, so charge is 700 (rounded down).
   Charge VAT: 21% of 700 = 147 (if the VAT rounding mode in Q8 gives an exact result here, which it does).
   Credit vat 0.

A5. Skip rule. Old price 10, new price 20, billable_seats 1, 1 unused day.
   Credit exact: 10/30, ceil gives 1, under 50, skipped.
   Charge exact: 20/30, floor gives 0, skipped.
   Returns [].

A6. Approval threshold (proposed, pending Q2). Credit of exactly 50000 cents goes to Win Tee Fung Tao. Credit of 50001 cents goes to Ramon Etxeberria-Goñi.

A7. vat_id present (for example "DE123456789") on an upgrade: charge vat_cents is 0, credit vat_cents is 0. Presence check only. Validity is not checked (see Q12).

A8. Description length. Any generated description is at most 80 characters, and always contains the YYYY-MM-DD period end date unchanged.

A9. Invalid types (float price, bool billable_seats, naive datetime) raise ValueError. No float value appears in any output.

A10. Changes to seats, or the presence of legacy_discount, do not change any output.

1.5 Priorities if scope is cut

Keep the credit calculation correct first (steps 3 to 5, 7, 10). Then the skip rule and approval. VAT (step 8) is the lowest priority, behind the credit.

2. AMBIGUITIES IN THE BRIEF

- Unused days: whole days or fractional days? Inclusive or exclusive of the change date? How are timezone offsets and the period_end date boundary handled (is period_end an exclusive instant or the end of its calendar day)?
- Same price: brief says downgrade is cheaper; equal price is not addressed. Credit and charge would be equal and offset.
- changed_at on or after period_end, or before the period start: not addressed. The period start is not in the input.
- 30-day period: anchored to period_end, or to a period start? No period_start field exists.
- Calculation order: per-seat price times billable seats times unused fraction is stated, but there is no rule for where rounding happens.
- seats: the brief says bill on billable_seats, but does not say whether seats must be ignored everywhere or validated.
- billable_seats zero or missing: no behaviour stated.
- status: only "trialing" is named. Other values (active, past_due, cancelled, unknown strings) are not addressed.
- vat_id present but invalid: no validation rule is given.
- VAT rounding: whether VAT on a charge is computed on the rounded amount, and what rounding mode applies (house default is half-up, which would round the customer's payment up, against the customer-favour rule).
- Minimum 50 cents: whether tested before or after VAT.
- Credits and VAT: the brief says credits carry no VAT. The house default says VAT applies to every line including credits. The brief overrides the house default, so this spec follows the brief, but it should be confirmed with the client.
- Approval: "over EUR 500" is stated in the brief, but the currency of prices is not stated, and no cents conversion is given. The brief literally implies exactly 500 goes to the controller, but PM notes ask for confirmation.
- Approval comparison: gross or net? Credits carry no VAT, so for credit lines gross equals net, but finance reverses VAT separately, which may mean the reversal amount is what counts.
- Approver name: the brief writes Ramón, PM notes write Ramon. The identifier used in approved_by must be confirmed.
- Description wording: the brief gives no template. Which plan name goes in the credit line (old plan) and the charge line (new plan) is an assumption. The date timezone is not specified.
- Minimal plan name length and ellipsis character are not specified.
- Rounding direction: the brief says credits round up and charges round down. This is consistent with the customer-favour intent and is followed as written.
- Ignoring legacy_discount: confirmed by the brief and PM note.

3. OPEN QUESTIONS FOR THE CLIENT

1. Currency: what currency are seat prices in? Is the approval threshold EUR 500, which we propose as 50000 cents?
2. Approval threshold: is exactly EUR 500 (50000 cents) approved by the controller (Win Tee Fung Tao), with Ramón Etxeberria-Goñi only for credits strictly over that amount? Is the comparison on the gross or net amount, and is the spelling "Ramón" or "Ramon" for the approver record?
3. Minimum line value: is the 50-cent threshold tested before or after VAT? Is it applied per line, and are skipped lines dropped together with their VAT?
4. Same price: if the new plan costs exactly the same as the old plan, should no lines be returned, or should a credit and charge of equal amount be issued?
5. Period definition: is each billing period exactly 30 days ending at period_end (so the period starts 30 days earlier), or is there a period start we should use? If a period start exists, please add it to the subscription record.
6. Out-of-range change dates: what should happen if changed_at is on or after period_end, or earlier than the period start? Should we return no lines, raise an error, or clamp the dates?
7. Days and rounding: should unused time be counted in whole days or fractional days? Is the change date counted as used or unused? Should the calculation be a single multiplication and division with one rounding step, as proposed?
8. VAT on charges: should VAT be computed on the rounded charge amount? What rounding applies to the VAT itself: half-up, down, or up? Confirm it should not round in the company's favour.
9. Invalid or missing billable_seats: should zero or missing billable_seats return no lines, or raise an error? Should non-integer or negative values raise an error?
10. Description wording: please provide the exact template for credit and charge descriptions. Should the credit line name the old plan and the charge line name the new plan? What is the date timezone? What is the minimal acceptable plan name length, and which character should be used for shortening (for example an ellipsis)?
11. Status values: which status values besides "trialing" exist? Should active subscriptions be prorated, and how should unknown or other statuses (such as past_due or cancelled) be handled?
12. vat_id: should a present but invalid vat_id be treated as reverse charge, or should it be validated and handled differently?
13. Credits and VAT: the brief says credits never carry VAT, which differs from the house default of VAT on every line. Please confirm that credit lines must always show vat_cents of 0 and that finance handles the reversal separately.
14. Seats field: should the old seats field be ignored entirely, or should billable_seats be checked against it for consistency?
15. Rounding direction: please confirm that credits round up and charges round down on the final amount, and that no intermediate rounding is applied to per-seat or per-day values.