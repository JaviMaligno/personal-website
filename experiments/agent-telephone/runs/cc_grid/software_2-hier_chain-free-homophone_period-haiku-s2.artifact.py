Verdict: the worked examples check out, but the design has one conflict with the house VAT rule and several ambiguities that need a decision before implementation.

**Verified examples (E1 to E9)**

- E1: credit 1500 (ceil of 1500), approved_by Thảo; charge 3000, vat 0 (reverse charge). Correct.
- E2: charge 3000, vat 630. Correct.
- E3: credit 77 (ceil of 76.92), charge 76 (floor of 76.92), charge vat 15 (1596 // 100). Correct.
- E4: credit 77, charge 153 (floor of 153.85). Correct. Charge vat is 32 if vat_id is None, which the design does not state.
- E5: credit raw 48.92 rounds to 49, which is below 50, so it is skipped. Single charge line 153, vat 32 if vat_id is None. Correct.
- E6: credit exactly 50 (650/13 = 50), kept, approved_by Thảo. Charge 50, vat 10. Correct. The sentence about "not valid as a change" is muddled, but the values are right.
- E7: credit 50001 goes to Ramón; credit 50000 goes to Thảo. Correct. Full 13 days is accepted because only spans above 13 days are rejected.
- E8: 2026-02-20 to 2026-03-05 is exactly 13 days (8 + 5), and no DST change falls in that window, so the amounts are identical. Correct.
- E9: 2026-11-01T00:30+02:00 gives "2026-11-01" in its own timezone. Correct.

**Defects and contradictions**

1. Credit VAT conflicts with the house rule. The house rule is that VAT applies to every invoice line, credits included. Section 5 sets credit vat_cents to 0 with no stated reason. Unless the client has told us otherwise, this must be fixed. If credit VAT is added, the rounding direction should be ceil, since rounding in the customer's favour on a refund means a larger refund. The design's floor rule for charge VAT does not carry over to credits.
2. The 13-day billing period is a feasibility risk. Any remaining span above 13 days raises ValueError. If real billing periods are monthly, ordinary mid-month upgrades would fail. The claim "a billing period is 13 days" needs confirming with the client.
3. Downgrades return [] silently. Section 2 rejects silent [] for stale data because it "would drop a real change", yet a downgrade is also a real change that produces no credit for the price difference. This is a business decision that needs confirming.
4. Check order is ambiguous. It is not stated whether the span check runs before the trialing and downgrade early returns. As written, a trialing or downgraded subscription with more than 13 days remaining would raise rather than return [].
5. Currency check placement is unspecified. The design does not say which object holds the currency field, or where the check sits in the order.
6. Truncation is ambiguous. It is not stated whether "..." counts toward the 80-code-point limit, or whether trailing whitespace is stripped before or after "..." is appended. For reference, the credit plan name budget is 48 code points and the charge budget is 57.
7. billable_seats is not checked against seats. Nothing says billable_seats must not exceed seats.
8. Approval routing is hardcoded to two named approvers. This is probably intended, but it should be confirmed as a business rule and not an implementation detail.

**Open questions I cannot settle from this message**

- Does the client want VAT on credit lines? If yes, is it ceil?
- Are billing periods really 13 days?
- Should a downgrade produce any credit?
- Where do the currency field and the span check sit in the validation order?
- Should billable_seats be validated against seats?