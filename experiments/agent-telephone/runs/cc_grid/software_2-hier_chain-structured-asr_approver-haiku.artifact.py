PART (a): SPEC (restated, with corrections)

Requirements (IDs unchanged)
- R1. Single entry point prorate_seats(subscription, new_plan, changed_at).
- R2. subscription keys: id, status, plan_name, seat_price_cents, seats, billable_seats, vat_id, period_end.
- R3. new_plan keys: name, seat_price_cents.
- R4. All datetimes are timezone-aware.
- R5. Returns a list of invoice lines with keys: subscription_id, kind ("credit" or "charge"), amount_cents, vat_cents, description, approved_by (None on charges).
- R6. Each description names the plan and gives period_end as YYYY-MM-DD.
- R7. Bill on billable_seats, not seats.
- R8. Credit the unused old plan; charge the unused new plan.
- R9. A billing period counts as 30 days. Unused days = changed_at to period_end.
- R10. Downgrade (new cheaper than old): no lines now.
- R11. Credits round up to the next cent; charges round down. (Explicit override of the house half-up rule for these lines.)
- R12. Skip any line under 50 cents.
- R13. Charges carry 21% VAT unless the customer has a vat_id, then reverse charge, VAT zero.
- R14. Credits never carry VAT. (Explicit override of the house "VAT on credits" rule.)
- R15. Trialing subscriptions: no lines.
- R16. Descriptions at most 80 characters; shorten the plan name, keep the date in full.
- R17. Credits approved by Win Tee Fung Tao; over EUR 500 approved by Ramon Etxeberria-Goñi.
- R18. Credit line before charge line.
- R19. All amounts are integer cents.
- R20. Ignore legacy_discount.
- R21. If scope is cut, the credit calculation (R8-R11, R17) takes priority over VAT (R13-R14).

Open points (PM assumptions, IDs unchanged)
- O1. R17 threshold = 50000 cents on the net credit (credits carry no VAT, so net equals gross).
- O2. R12 minimum = 50 cents on the net amount excluding VAT, for both line types.
- O3. Fractional days: exact elapsed time divided by 24h. Unused fraction = days_remaining / 30. Exact arithmetic, then R11 rounding.
- O4. Charge VAT rounds down.
- O5. Equal price returns no lines.
- O6. changed_at at or after period_end, or status other than active or trialing, returns no lines.
- O7. Current billable_seats used for both lines. Credit = old price x billable_seats x (days/30). Charge = new price x billable_seats x (days/30).

Architect design (S-IDs)
- S1. Pure function, no I/O, returns a list of dicts.
- S2. Validation, raising ValueError before any output. All 8 subscription keys present. new_plan has name and seat_price_cents. changed_at and period_end are datetime instances with utcoffset() not None. seat_price_cents (both plans) and billable_seats are int, not bool, not float, and >= 0. Plan names are non-empty after strip. vat_id: None, empty, or whitespace-only means no VAT ID; any other non-empty string means reverse charge. seats is never read. legacy_discount is ignored if present.
- S3. After validation: if status != "active", return [].
- S4. If changed_at >= period_end, return [].
- S5. If new price <= old price, return [].
- S6. E = period_end - changed_at in integer microseconds. If E > 2592000000000 (30 days), raise ValueError. E equal to 30 days is allowed.
- S7. D = 2592000000000. Credit net = ceiling(old x billable_seats x E / D), computed as -((-n) // D). Charge net = floor(new x billable_seats x E / D).
- S8. Skip any line with net < 50, evaluated after rounding. Net exactly 50 is kept.
- S9. Credit VAT = 0. Charge VAT = 0 if reverse charge, else (charge_net x 21) // 100, on the rounded net. Only for a charge that was not skipped.
- S10. Credits: approved_by = "Ramon Etxeberria-Goñi" if credit_net > 50000, else "Win Tee Fung Tao". Charges: None.
- S11. Credit description: "Credit {old plan_name} seats, period end {YYYY-MM-DD}". Charge description: "Charge {new name} seats, period end {YYYY-MM-DD}". Date is the calendar date of period_end in its own offset. Fixed text is 36 characters, leaving 44 for the plan name. If the plan name is at most 44 code points, use it unchanged. Otherwise use its first 41 code points followed by "...". If the room is below 4 characters, raise ValueError with no partial output.
- S12. Order: credit then charge. A skipped line is omitted. Both skipped gives [].
- S13. subscription_id = subscription id. Credit vat_cents = 0. approved_by is a string on credits, None on charges.
- S14. billable_seats = 0 gives both nets 0, both skipped, return [].

CORRECTIONS
- CORRECTED (S2): "values may be None where allowed" is ambiguous. Only vat_id may be None. All other values must be present and of the types stated. Reason: the spec names no other nullable field, so a developer cannot tell which others are allowed.
- CORRECTED (S2, type gap): id, status, plan_name, and both plan names must be str. seats is not type-checked because it is never read. All type failures raise ValueError, not TypeError. Reason: the architect did not state the types for these fields.
- CORRECTED (S11, plan name whitespace): the description uses the plan name exactly as stored (no strip). The strip is used only for the non-empty check in S2. Reason: the spec does not say whether to strip, and a developer would have to guess.

Clarifications, not corrections
- The house half-up rounding rule is overridden by R11 on these lines. This must be recorded as a deliberate override.
- The house rule "VAT on every line, credits included" is overridden by R14. This must be recorded as a deliberate override.
- The S11 truncation counts code points, so it may split a base character from a combining mark. Accepted as specified.

PART (b): VERDICTS

O1. CONFIRM. Threshold applied to the net credit, which equals gross.
O2. CONFIRM. Applied to net excluding VAT, on both line types.
O3. CONFIRM. Fractional days are required for exact arithmetic (see F2).
O4. CONFIRM. Rounds down. This overrides the house half-up rule.
O5. CONFIRM.
O6. CONFIRM, subject to F6 and F7.
O7. CONFIRM, subject to F8.

F1. AGREE WITH IMPLEMENTATION, CLIENT MUST CONFIRM. The company reading (Fernhollow Studios as "client") matches the engagement and the spec implements it. The customer reading would reverse the direction on both lines. Hold the spec as written until the client confirms.
F2. AGREE. A whole-day count cannot satisfy R11 in both directions, so fractional days are needed. R9's wording "number of days" should be read as "days, possibly fractional" and this should be stated in the requirement.
F3. AGREE, CLIENT MUST CONFIRM. No currency field exists. R17's "EUR 500" supports EUR cents as the unit for R12 and R17.
F4. AGREE WITH RAISE, CLIENT MUST CHOOSE. Raising stops a batch on one bad subscription. Clamping would silently under-bill or over-bill. Client decision required. Ex10 at exactly 30 days is allowed.
F5. AGREE, CLIENT MUST CONFIRM the "..." marker. Truncation can split combining characters (see clarifications).
F6. AGREE. Only status "active" proceeds. R15 and O6 are reconciled this way. Trialing is excluded.
F7. CLIENT DECISION REQUIRED. As written there is no signal. The module must stay pure, so any notice would have to come from the caller. Client must say whether a log or error is wanted.
F8. CLIENT MUST CONFIRM. The credit uses current billable_seats, which may differ from what was invoiced at period start.
F9. AGREE. The date comes from period_end's own offset. Example: period_end 2026-11-11T00:30:00+02:00 is still dated 2026-11-11 here, while its UTC date is 2026-11-10. This is intended but should be tested (Ex21 below).
F10. AGREE. Thresholds apply to the rounded values, which is what gets emitted.
F11. AGREE. Naive datetimes raise ValueError (Ex11).
F12. AGREE. Strictly greater than 50000. Ex2 does not test the boundary, so boundary examples are added below (Ex13, Ex14).
F13. AGREE, CLIENT MUST CONFIRM. The rate is fixed at 21%. Reverse charge is driven by any non-empty vat_id, regardless of country, so a non-EU customer with a vat_id also gets zero VAT. Client must confirm.

Missing cases added by me (all verified in part (c)): credit exactly 50 kept, credit exactly 50000 (Win Tee), credit 50001 (Ramon), window exceeded, whitespace vat_id, zero billable seats, past_due status, bool and float rejection, and the date-offset case.

PART (c): ACCEPTANCE EXAMPLES (each verified independently)

Denominator D = 2592000000000 microseconds (30 days). Day counts below are calendar days between the two timestamps.

Ex1. Oct 22 to Nov 11 = 20 days, f = 20/30 = 2/3.
Credit: 1000 x 5 x 2/3 = 3333.33, ceiling 3334. Approver: Win Tee (3334 is not over 50000).
Charge: 2000 x 5 x 2/3 = 6666.67, floor 6666. VAT: 6666 x 21 = 139986, // 100 = 1399.
Lines:
(sub_A1, 3334, 0, "Credit Studio Basic seats, period end 2026-11-11", "Win Tee Fung Tao")
(sub_A1, 6666, 1399, "Charge Studio Pro seats, period end 2026-11-11", None)
Result: matches expected. PASS.

Ex2. Oct 27 to Nov 11 = 15 days, f = 1/2.
Credit: 5000 x 30 x 1/2 = 75000 exact. Over 50000, approver Ramon.
Charge: 6000 x 30 x 1/2 = 90000 exact. VAT: 90000 x 21 = 1890000, // 100 = 18900.
Lines:
(sub_B2, 75000, 0, "Credit Team Plus seats, period end 2026-11-11", "Ramon Etxeberria-Goñi")
(sub_B2, 90000, 18900, "Charge Team Max seats, period end 2026-11-11", None)
Result: matches expected. PASS.

Ex3. Oct 30 to Nov 10 = 11 days, f = 11/30.
Credit: 999 x 7 = 6993; x 11 = 76923; / 30 = 2564.10, ceiling 2565.
Charge: 1001 x 7 = 7007; x 11 = 77077; / 30 = 2569.23, floor 2569. VAT: 2569 x 21 = 53949, // 100 = 539.
Lines:
(sub_C3, 2565, 0, "Credit Desk Lite seats, period end 2026-11-10", "Win Tee Fung Tao")
(sub_C3, 2569, 539, "Charge Desk Plus seats, period end 2026-11-10", None)
Result: matches expected. PASS.

Ex4. Nov 10 to Nov 11 = 1 day, f = 1/30.
Credit: 100 x 1 / 30 = 3.33, ceiling 4. Under 50, skipped.
Charge: 2000 x 1 / 30 = 66.67, floor 66. VAT: 66 x 21 = 1386, // 100 = 13. Not under 50, kept.
Lines:
(sub_D4, 66, 13, "Charge Solo Plus seats, period end 2026-11-11", None)
Result: matches expected. PASS.

Ex5. Same as Ex1, vat_id "PT509999999" (reverse charge).
Credit: 3334, VAT 0, Win Tee.
Charge: 6666, VAT 0.
Lines:
(sub_A1, 3334, 0, "Credit Studio Basic seats, period end 2026-11-11", "Win Tee Fung Tao")
(sub_A1, 6666, 0, "Charge Studio Pro seats, period end 2026-11-11", None)
Result: matches expected. PASS.

Ex6. Old 2000, new 1000. New is cheaper, so downgrade.
Result: []. PASS.

Ex7. Ex1 with status "trialing". S3 returns [].
Result: []. PASS.

Ex8. changed_at = period_end = 2026-11-11T00:00:00+00:00. S4 returns [].
Result: []. PASS.

Ex9. Ex1 with new price 1000 (equal). S5 returns [].
Result: []. PASS.

Ex10. Oct 12 to Nov 11 = 30 days, E = D exactly (allowed), f = 1.
Credit: 1000 x 1 x 1 = 1000 exact. Approver Win Tee.
Charge: 2000 exact. VAT: 2000 x 21 = 42000, // 100 = 420.
Descriptions. Credit plan name "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrs" has 26 + 19 = 45 characters, which exceeds 44, so use first 41 ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmno", 26 + 15) plus "...". Total 36 + 44 = 80. Charge plan name has 26 + 18 = 44 characters, used unchanged. Total 80.
Lines:
(sub_J10, 1000, 0, "Credit ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmno... seats, period end 2026-11-11", "Win Tee Fung Tao")
(sub_J10, 2000, 420, "Charge ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqr seats, period end 2026-11-11", None)
Result: matches expected, both descriptions 80 characters. PASS.

Ex11. Ex1 with naive changed_at "2026-10-22T00:00:00". S2 raises ValueError.
Result: ValueError. PASS.

Added examples

Ex12 (credit exactly 50 is kept). Plans "Studio Basic" (1000) to "Studio Pro" (2000), billable_seats 1, changed_at 2026-11-09T12:00:00+00:00, period_end 2026-11-11T00:00:00+00:00, vat_id None. E = 36 hours = 129600000000 microseconds, f = 0.05.
Credit: 1000 x 1 x 129600000000 / 2592000000000 = 50 exact. Kept.
Charge: 2000 x 0.05 = 100 exact. VAT: 100 x 21 // 100 = 21.
Lines:
(sub_E12, 50, 0, "Credit Studio Basic seats, period end 2026-11-11", "Win Tee Fung Tao")
(sub_E12, 100, 21, "Charge Studio Pro seats, period end 2026-11-11", None)
PASS.

Ex13 (credit exactly 50000, Win Tee). Plans "Team Plus" (50000) to "Team Max" (50001), billable_seats 1, changed_at 2026-10-12T00:00:00+00:00, period_end 2026-11-11T00:00:00+00:00, vat_id None. f = 1.
Credit: 50000 exact. Not over 50000, so Win Tee.
Charge: 50001 exact. VAT: 50001 x 21 = 1050021, // 100 = 10500.
Lines:
(sub_F13, 50000, 0, "Credit Team Plus seats, period end 2026-11-11", "Win Tee Fung Tao")
(sub_F13, 50001, 10500, "Charge Team Max seats, period end 2026-11-11", None)
PASS.

Ex14 (credit 50001, Ramon). Plans "Team Plus" (50001) to "Team Max" (50002), same dates and billable_seats 1.
Credit: 50001 exact. Over 50000, so Ramon.
Charge: 50002 exact. VAT: 50002 x 21 = 1050042, // 100 = 10500.
Lines:
(sub_G14, 50001, 0, "Credit Team Plus seats, period end 2026-11-11", "Ramon Etxeberria-Goñi")
(sub_G14, 50002, 10500, "Charge Team Max seats, period end 2026-11-11", None)
PASS.

Ex15 (window exceeded). Ex1 with changed_at 2026-10-11T00:00:00+00:00. E = 31 days > D. S6 raises ValueError.
Result: ValueError. PASS.

Ex16 (whitespace-only vat_id means no VAT ID). Ex1 with vat_id "   ". S2 treats it as no VAT ID.
Lines: (sub_A1, 3334, 0, credit, Win Tee), (sub_A1, 6666, 1399, charge, None). Same as Ex1. PASS.

Ex17 (zero billable seats). Ex1 with billable_seats 0. Both nets 0, both skipped.
Result: []. PASS.

Ex18 (past_due). Ex1 with status "past_due". S3 returns [].
Result: []. PASS.

Ex19 (bool rejected). Ex1 with seat_price_cents True. S2 raises ValueError.
Result: ValueError. PASS.

Ex20 (float rejected). Ex1 with billable_seats 5.0. S2 raises ValueError.
Result: ValueError. PASS.

Ex21 (date uses own offset). changed_at 2026-10-23T00:00:00+02:00 (= Oct 22 22:00 UTC), period_end 2026-11-11T00:00:00+02:00 (= Nov 10 22:00 UTC). Plans and seats as Ex1, vat_id None. E = 19 days exactly, f = 19/30.
Credit: 5000 x 19 = 95000; / 30 = 3166.67, ceiling 3167. Approver Win Tee.
Charge: 10000 x 19 = 190000; / 30 = 6333.33, floor 6333. VAT: 6333 x 21 = 132993, // 100 = 1329.
Date in description is the date in period_end's own offset: 2026-11-11 (not 2026-11-10).
Lines:
(sub_A1, 3167, 0, "Credit Studio Basic seats, period end 2026-11-11", "Win Tee Fung Tao")
(sub_A1, 6333, 1329, "Charge Studio Pro seats, period end 2026-11-11", None)
PASS.

Summary: The architect's arithmetic is correct in all eleven given examples. No mismatches. The design is implementable once the three CORRECTED points above are adopted and the client confirms F1, F3, F4, F7, F8, F13. The added examples Ex12 to Ex21 close the boundary, validation, and date-offset gaps.