# Fernhollow Studios seat-upgrade proration: design and build plan

## (a) Scoped spec

**Interface**

`prorate_seats(subscription, new_plan, changed_at) -> list[dict]`

- Each line has keys `subscription_id`, `kind` ("credit" or "charge"), `amount_cents` (int), `vat_cents` (int), `description` (str), `approved_by` (str or None).
- Lines are ordered credit first, then charge. Either line may be omitted.
- Subscription keys used: `id`, `status`, `plan_name`, `seat_price_cents`, `billable_seats`, `vat_id`, `period_end`. The `seats` and `legacy_discount` fields are ignored.
- `new_plan` keys used: `name`, `seat_price_cents`.

**Rules and acceptance criteria**

1. **Status.** Only "active" prorates. "trialing" returns []. Any other status raises ValueError. (Status rule is ASSUMPTION for "active", BLOCKER for the other statuses.)
   - AC: active prorates; trialing returns []; past_due, canceled and unknown raise ValueError.
2. **Downgrade and equal price.** If new price is less than or equal to old price, return [].
   - AC: cheaper plan returns []; equal price returns []; upgrade proceeds.
3. **Time basis.** Period is 30 days. unused = period_end - changed_at in integer seconds. Clamp unused to [0, 30 days]. If changed_at >= period_end, return [].
   - AC: exact fractional-day arithmetic with no floats; changed_at before period start clamps to 30 days; changed_at at or after period_end returns [].
4. **Amount.** amount = price_cents * billable_seats * unused_seconds / (30 * 86400), computed with Fraction. Round once at the end: credit uses ceiling, charge uses floor (see decision 1).
   - AC: no float appears anywhere in the calculation.
5. **Minimum.** Skip a line when its rounded amount_cents (before VAT) is less than 50. Skipped lines are omitted, not returned as zero. Credit and charge are evaluated independently.
   - AC: 49 is skipped, 50 and 51 are kept.
6. **VAT.** Charges: vat = (amount_cents * 21 + 50) // 100 when vat_id is absent, else 0. Credits: vat_cents is always 0. "vat_id present" means it is a string whose strip() is non-empty.
   - AC: 21% rounding is correct at both ends; None, "" and whitespace-only vat_id count as absent.
7. **Description.** Format a fixed template containing the plan name and "period ends YYYY-MM-DD". The date comes from period_end's own tzinfo with no conversion. Each line names only its own plan. Maximum 80 characters. If too long, truncate the plan name with "..." and keep the date. If still too long after the name is reduced to the minimum, raise ValueError.
   - AC: exactly 80 characters passes; 81 triggers shortening; the date is always present; unfixable length raises ValueError.
8. **Approval.** Credit: "Nguyễn Thị Phương Thảo". If credit amount_cents is strictly greater than 50000, use "Ramón Etxeberria-Goñi". Charge: None.
   - AC: 50000 gives Thao; 50001 gives Ramón; charges are None.
9. **Types.** All amounts are int cents. Naive datetimes raise ValueError.
   - AC: naive changed_at or period_end raises ValueError; outputs are int.
10. **Seats.** billable_seats drives both lines; seats has no effect.
    - AC: changing seats does not change output.

## (b) Numbered build plan and test cases

1. Write the rounding helpers, one for credit (ceiling) and one for charge (floor), so the direction can be flipped in one place.
2. Write the time-basis and amount calculation using Fraction. Test cases:
   - Full 30 days, one seat, price 1000: credit 1000 exactly.
   - Half a day left: exact half of the full amount.
   - Fractional cents at each end: credit rounds up (for example 100.01 gives 101); charge rounds down (for example 100.99 gives 100).
   - Exact integers stay unchanged in both directions.
   - changed_at at period_end returns [].
   - changed_at before period start clamps to 30 days.
3. Write status and downgrade gating. Test cases:
   - trialing returns [].
   - past_due, canceled and an unknown status raise ValueError.
   - Downgrade returns [].
   - Equal price returns [].
4. Write the minimum-50 filter. Test cases: 49 skipped, 50 kept, 51 kept, and credit and charge filtered independently.
5. Write VAT. Test cases:
   - 21% on charge (for example 1000 gives 210).
   - Half-up at the boundary (for example 3 gives 1, computed as (3*21+50)//100).
   - vat_id "VAT123" gives zero charge VAT.
   - vat_id None, "", and "   " each give 21% VAT.
   - Credit VAT is always 0.
6. Write descriptions. Test cases:
   - Exactly 80 characters passes unchanged.
   - 81 characters triggers plan-name shortening with the date kept.
   - Date always present and formatted YYYY-MM-DD.
   - Unfixable length raises ValueError.
7. Write approval. Test cases:
   - Credit 50000 gives Thao.
   - Credit 50001 gives Ramón.
   - Charge gives None.
8. Write type and ordering checks. Test cases:
   - Naive datetime raises ValueError.
   - Output amounts are int.
   - Credit appears before charge.
   - seats field change has no effect.
9. Run the full suite and confirm all acceptance criteria are met. Apply any changed decisions from part (c) before finalising.

## (c) Decisions needed from Ingrid

Each item is either a BLOCKER (must be confirmed before build) or an ASSUMPTION (we proceed with the default and flag it for confirmation).

1. **Rounding conflict.** BLOCKER. The brief says "never round in our favour", but also says credits round up and charges round down. Both of those favour the customer, so the principle and the literal rules contradict each other. Default: implement the literal rules (credit ceiling, charge floor), isolated in named helpers.
2. **Currency and conversion.** BLOCKER. The brief uses € for the threshold, so EUR is the likely currency. Still confirm whether subscriptions are all EUR and whether any conversion applies. Default: EUR, no conversion, threshold 50000 cents.
3. **Threshold comparison basis.** BLOCKER. Default: net credit amount (credits carry no VAT, so net equals gross), strictly greater than 50000 cents. Confirm this rather than credit including VAT or total of all lines.
4. **Partial days.** BLOCKER. The brief says "days left". Default: exact fractional days. Confirm whether partial days count.
5. **period_end timezone for the date.** ASSUMPTION. Default: use the tzinfo of period_end as supplied, with no conversion. Confirm.
6. **Trialing and other statuses.** BLOCKER for other statuses. Default: trialing returns []; active prorates; any other status raises ValueError. Confirm the caller can handle the exception.
7. **Equal-price behaviour.** ASSUMPTION. Default: equal price returns [] (no-op). Confirm.
8. **Minimum 50 cents, before or after VAT.** ASSUMPTION. Default: measured on amount_cents before VAT, applied to credits and charges alike. Confirm.
9. **VAT rounding mode.** ASSUMPTION. Default: round half up on the charge amount, using (amount*21+50)//100. Confirm half-up.
10. **Description content and overflow.** ASSUMPTION. Default: each line names only its own plan; overflow truncates the plan name with "..." and keeps the date; unfixable overflow raises ValueError. Confirm all three.
11. **Approver spelling.** BLOCKER. Default: use the brief's spelling with diacritics, "Nguyễn Thị Phương Thảo" and "Ramón Etxeberria-Goñi". The PM note dropped the diacritics, so confirm the legal spelling.
12. **Naive datetime handling.** ASSUMPTION. Default: raise ValueError. Confirm.