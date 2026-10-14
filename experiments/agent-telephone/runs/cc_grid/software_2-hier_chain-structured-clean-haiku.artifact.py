# Plan: `prorate_seats` (seat upgrades in billing)

No production code has been written. The design below is provisional until the blocking questions in section (c) are answered.

## (a) Module design and plan steps

**Module:** a single file, `seat_proration.py`, standard library only (`datetime`, `fractions`, `typing`). Keep internal helpers private (leading underscore). The only public name is `prorate_seats`.

**Functions:**

1. `prorate_seats(subscription, new_plan, changed_at) -> list[dict]`: the entry point. It orchestrates the steps below and does no arithmetic itself.
2. `_validate(subscription, new_plan, changed_at)`: checks required keys, that every amount is an `int` (reject `float` and `bool`), that `changed_at` and `period_end` are timezone-aware, and that `status` is recognised. Raises `TypeError` or `ValueError`. It never mutates its inputs.
3. `_unused_days(changed_at, period_end) -> Fraction`: exact arithmetic. Compute `delta = period_end - changed_at`, then take `Fraction(delta // timedelta(microseconds=1), 86_400_000_000)`. Clamp negative values to 0 (Q3). Do not use `total_seconds()` or `/` on timedeltas, because both produce floats (R13).
4. `_exact_amount(price_cents, seats, unused_days) -> Fraction`: `Fraction(price_cents * seats) * unused_days / 30` (R4). The 30-day period is a named constant.
5. `_ceil_cents(x: Fraction) -> int` and `_floor_cents(x: Fraction) -> int`: `-(-x.numerator // x.denominator)` and `x.numerator // x.denominator`. These implement the R6 directions. Keep them as the only rounding points.
6. `_approver(credit_cents) -> str`: returns the Ramón name if `credit_cents > 50000`, otherwise the Thảo name (R11). Use the exact strings from the spec and keep them as module constants.
7. `_charge_vat(net_cents, vat_id) -> int`: returns 0 if `vat_id` is truthy (reverse charge). Otherwise returns `floor(net_cents * 21 / 100)` using integer arithmetic (`net_cents * 21 // 100`). The rounding direction is provisional (Q4).
8. `_description(name, period_end, budget_fn) -> str`: builds the text and shortens only the plan name (R10). The date is formatted as `f"{period_end:%Y-%m-%d}"`, which uses the datetime's own tzinfo with no conversion (Q9). The name is truncated to fit 80 characters, with no ellipsis (Q8). If no room remains for the name, raise `ValueError` and emit no line.
9. `_build_line(subscription_id, kind, amount_cents, vat_cents, description, approved_by) -> dict`: a constructor for the output dictionary that enforces the R2 key set.

**Entry-point flow:**

1. Validate inputs.
2. If `status == "trialing"`, return `[]` (R9).
3. If `status` is not `"active"` and not `"trialing"`, raise `ValueError` (Q3 default, pending confirmation).
4. If `new_plan["seat_price_cents"] < subscription["seat_price_cents"]`, return `[]` (R5).
5. Compute `days = _unused_days(...)`, the exact credit `Fraction` for the old price, and the exact charge `Fraction` for the new price, both using `billable_seats` and not `seats` (R3, R4).
6. Round the credit up and the charge down (R6), producing integer cents.
7. Drop any line whose rounded net amount is under 50 cents (R7, Q5). Apply the threshold to the rounded net amount, before VAT.
8. Build the credit line first (`kind="credit"`, `vat_cents=0`, `approved_by` from `_approver`), then the charge line (`kind="charge"`, `vat_cents` from `_charge_vat`, `approved_by=None`) (R8, R11, R12).
9. Descriptions: the credit names `subscription["plan_name"]` and the charge names `new_plan["name"]`. Each is shortened independently.
10. Return the list. Never read `legacy_discount` (R14). Never read `seats` (R3).

**Design points for easy change:**

- Constants at the top of the module: `PERIOD_DAYS = 30`, `VAT_BP = 2100` (basis points), `MIN_LINE_CENTS = 50`, `APPROVAL_THRESHOLD_CENTS = 50000`, `APPROVER_DEFAULT`, `APPROVER_LARGE`, `DESC_MAX = 80`, `DATE_FMT`, `ALLOWED_STATUSES`. Each provisional default can then be changed in one place.
- Rounding and VAT are isolated in the helpers listed in steps 5 and 7, so the R6 direction and the Q4 VAT rule can be flipped without touching the flow.
- Keep the `_description` truncation budget as a separate pure function so the 80-character rule is tested in isolation.

## (b) Test matrix

Worked values are given where the expected output can be checked by hand.

**R1 (inputs)**
- Missing key in `subscription` or `new_plan` raises `ValueError`.
- A float `seat_price_cents` or `billable_seats` raises `TypeError`.
- A `bool` amount raises `TypeError`.
- A naive `changed_at` or naive `period_end` raises `ValueError`.

**R2 (output shape)**
- Each returned line has exactly the keys `subscription_id`, `kind`, `amount_cents`, `vat_cents`, `description`, `approved_by`.
- `kind` is only `"credit"` or `"charge"`.

**R3 (seat basis)**
- `seats=10`, `billable_seats=3`, old 1000, new 2000, 10 unused days. Expected credit 1000, charge 2000, so the result is based on 3 seats.

**R4 (proration)**
- Old 1000, new 2000, billable 3, 10 unused days: credit = 1000 × 3 × 10 / 30 = 1000; charge = 2000 × 3 × 10 / 30 = 2000.
- A 31-day calendar month still uses the 30-day divisor. The test must not depend on the month of `changed_at`.

**R5 (downgrade)**
- New price 900, old 1000: returns `[]`.

**R6 (rounding direction)**
- Credit rounds up: old 1000, 1 seat, 1 day gives 33.33, so the credit is 34.
- Charge rounds down: new 1001, 1 seat, 1 day gives 33.37, so the charge is 33.
- Combined with R7: old 1485, 1 seat, 1 day gives 49.5, which rounds up to a 50-cent credit and is kept. New 1497, 1 seat, 1 day gives 49.9, which rounds down to a 49-cent charge and is dropped.
- Verify that no test relies on half-up rounding.

**R7 (minimum line)**
- Line at exactly 50 cents is kept. Line at 49 cents is dropped.
- A dropped credit does not suppress the charge, and the reverse.

**R8 (VAT)**
- Charge with no `vat_id`: new 2000 net gives `vat_cents = 420`.
- Charge with `vat_id` set: `vat_cents = 0`.
- Credit: `vat_cents = 0` in every case, including the reverse-charge and non-reverse-charge paths.
- Rounding check for Q4: a net charge of 51 cents gives VAT floor(10.71) = 10.

**R9 (trialing)**
- `status="trialing"` returns `[]`, with no validation of the price difference.

**R10 (descriptions)**
- Each description contains the plan name and `YYYY-MM-DD`.
- Length is at most 80 characters.
- A 120-character plan name is truncated, and the full date remains intact at the end.
- A date with a `+05:30` tzinfo whose UTC date differs is formatted in its own zone (Q9).
- A plan name that cannot fit even at zero characters raises `ValueError` and emits no line.

**R11 (credit approval)**
- Credit of exactly 50000 cents gives the Thảo name.
- Credit of 50001 cents gives the Ramón name.
- Charges always have `approved_by=None`.
- Confirm that the Unicode names survive round-tripping unchanged.

**R12 (ordering)**
- When both lines are emitted, the credit is index 0 and the charge is index 1.

**R13 (money types)**
- Every `amount_cents` and `vat_cents` is an `int`, with `type(x) is int`.
- No `float` appears anywhere in the output.
- The implementation never calls `total_seconds()` or uses `/` on a timedelta.

**R14 (legacy_discount)**
- Adding `legacy_discount` with arbitrary values does not change any output.

**R15 (scope priority)**
- If VAT must be cut, the credit tests for R4, R6 and R11 remain in the suite and must pass.

**Q2 (partial days)**
- `changed_at` at 12:00 and `period_end` at midnight gives 0.5 unused days. Old 1000, 1 seat: credit = 500 × 0.5... more precisely 1000 × 0.5 / 30 = 16.67, rounded up to 17.
- No float appears in the computation.

**Q3 (edge cases)**
- `changed_at` equal to `period_end` gives unused days 0 and no lines.
- `changed_at` after `period_end` clamps to 0 and no lines.
- Equal prices: the default proposes both lines. This test is blocked until the conflict with Q10 is resolved (see section c).
- `status="canceled"` or `"past_due"` raises (provisional).
- `status="active"` prorates.

**Q4 (VAT rounding)**
- Charge net 51 gives VAT 10, not 11.

**Q5 (50-cent threshold applies to net)**
- A charge with net 50 and VAT 10 is kept (net 50 is at the threshold). A charge with net 49 is dropped even though its gross would be 59.

**Q6 (threshold on net)**
- Credits carry no VAT, so the test confirms that the 50000 boundary is on the net, which is the only amount.

**Q7 (rounding direction)**
- Test the R6 directions as written. A failure is expected to change once Q7 is answered.

**Q8 (description truncation)**
- Plan name is truncated to fit with no ellipsis, and the full date is kept.
- If the name cannot fit, raise.

**Q9 (timezone of date)**
- Date uses the datetime's own tzinfo, with no UTC conversion. Covered in R10.

**Q10 (zero output cases)**
- `billable_seats=0` gives `[]`.
- Zero price difference gives `[]` under Q10. This conflicts with Q3 and is blocked.

## (c) Blocking questions for the client

These must be answered before implementation, because each one changes computed amounts, the branch logic, or the ledger contract.

1. **R6 direction (Q7).** As written, credits rounding up and charges rounding down both favour the end customer. The stated background (a fine for rounding in the company's own favour) makes sense only if the protected party is the customer. Confirm that "client" in R6 means the customer. If "client" means Fernhollow, the rule is inverted and every rounding call flips.
2. **Half-up house rule vs R6.** The house rule says half-up rounding. R6 overrides it for credits and charges. Confirm that R6 replaces half-up entirely for these lines.
3. **VAT on credits: house rule vs R8.** The house rule says VAT applies to every invoice line, credits included. R8 says credits never carry VAT. The design follows R8 (the explicit requirement). Confirm with finance.
4. **Equal prices (Q3) vs zero difference (Q10).** Q3 proposes that equal prices emit both lines. Q10 proposes that a zero price difference emits no lines. These contradict each other. Decide which applies to equal seat prices.
5. **Unknown statuses (Q3).** Confirm that only `"active"` prorates and that `"canceled"`, `"past_due"` and other statuses raise. Raising will block the upgrade flow for those subscriptions. Confirm that raising is preferred over returning `[]`.
6. **Ledger contract (R2, R13).** Confirm the sign convention. The design assumes `amount_cents` is a positive magnitude and `kind` gives the direction. Also confirm that `amount_cents` for charges is the net amount, with VAT in `vat_cents` and not added to it.
7. **VAT rounding (Q4).** Rounding VAT down underpays tax. Confirm that finance accepts this, or specify a different rule for tax.
8. **Currency (Q1).** The 50000-cent threshold is only meaningful if amounts are EUR. Confirm.
9. **Partial days (Q2).** Confirm exact fractional days, with rounding applied only to the final amount.
10. **Description truncation failure (Q8).** Confirm that raising is acceptable when a description cannot fit, since that fails the whole upgrade.

## Non-blocking assumptions

- **R7 applied after rounding.** The 50-cent test uses the rounded net amount, so a 49.5-cent credit (rounded to 50) is kept.
- **Description wording.** Template is provisional, for example `"Seat change to {name}, period end {date}"`. The date format is fixed by R10.
- **Line naming.** The credit names the old plan and the charge names the new plan.
- **Changed_at before period start.** The spec gives no period start, so this case is not handled. It is out of scope unless the client adds a `period_start` field.
- **Error types.** `TypeError` for wrong types, `ValueError` for bad values and unknown statuses.
- **No logging, no I/O.** The module is pure.
- **Zero-amount lines.** Zero-value lines are dropped by R7 and never emitted.
- **Input immutability.** Inputs are not modified.