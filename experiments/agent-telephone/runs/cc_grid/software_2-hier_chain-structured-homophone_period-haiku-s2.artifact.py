# Written spec: prorate_seats (Fernhollow Studios, seat upgrades in billing)

Date: 2026-10-13. Entry point: `prorate_seats(subscription, new_plan, changed_at)`. Standard library only, Python 3.12.

## (a) Requirements R1 to R15 (restated unchanged)

R1. Inputs. `subscription` is a dict with keys `id`, `status`, `plan_name`, `seat_price_cents`, `seats`, `billable_seats`, `vat_id`, `period_end`. `new_plan` is a dict with `name` and `seat_price_cents`. `changed_at` and `period_end` are timezone-aware datetimes.

R2. Output. The entry point returns a list of invoice line dicts, each with keys `subscription_id`, `kind` ("credit" or "charge"), `amount_cents`, `vat_cents`, `description`, `approved_by` (None on charges).

R3. Seat count. Bill on `billable_seats`. Do NOT use `seats`, which still counts deactivated users since the June SSO migration.

R4. Proration method. A billing period always counts as 13 days regardless of calendar month. The unused fraction is the number of days from `changed_at` to `period_end` divided by 13.

R5. Credit and charge. Credit the unused part of the old plan (old `seat_price_cents` x `billable_seats` x unused fraction). Charge the unused part of the new plan (new `seat_price_cents` x `billable_seats` x unused fraction).

R6. Downgrade. If the new plan's seat price is lower than the old one, do not prorate. Return an empty list. The change applies at renewal.

R7. Rounding, never in the client's favour. Credit amounts round UP to the next cent. Charge amounts round DOWN. All amounts are integer cents. No floats anywhere, since the ledger import rejects decimals.

R8. Minimum line. Skip any line whose amount is under 50 cents. It is not emitted at all.

R9. VAT on charges. VAT is 21% of the charge amount, unless the subscription has a `vat_id`, in which case reverse charge applies and VAT is 0. Credits never carry VAT (`vat_cents` = 0), because finance reverses VAT separately.

R10. Trialing. If `status` is "trialing", no proration: return an empty list.

R11. Descriptions. Each description names the plan and includes the period end date formatted YYYY-MM-DD. Maximum 80 characters. If too long, shorten the plan name only. The date must always be kept in full.

R12. Approvals. Every credit line has `approved_by` = "Nguyễn Thị Phương Thảo" (finance controller). If a credit is over €500 (50000 cents), `approved_by` = "Ramón Etxeberria-Goñi" instead. Charges have `approved_by` = None.

R13. Ordering. The credit line comes before the charge line in the returned list. The PDF template depends on this order.

R14. Ignore the legacy field `legacy_discount`. Do not read it. It is being removed by Wojciech.

R15. Scope priority. If scope must be cut, correctness of the credit (R4, R5, R7, R12) takes priority over VAT (R9).

## (b) R16 to R25: confirmed or corrected

**R7 title conflict (read this first).** The body of R7 and R19 round credits UP and charges DOWN, and VAT DOWN. Every rounding rule therefore resolves in the subscriber's favour, not Fernhollow's. The title "never in the client's favour" only matches the body if "client" means Fernhollow Studios, our client. Read that way, the title and body agree: rounding never favours Fernhollow. The reading is ambiguous, so I implement the explicit body and R19 rules. The title should be reworded to "Rounding always resolves in the subscriber's favour (credits up, charges and VAT down)". Ingrid should confirm this business position in writing.

**R16. Confirmed as a working assumption, pending client.** All amounts are EUR. There is no currency input and no currency field in the output. Ingrid must confirm that every subscription is EUR (see risk 14).

**R17. Confirmed.** The 50-cent test (R8) uses the pre-VAT `amount_cents`. A charge of 50 cents pre-VAT is emitted with VAT of 10 cents. A credit has no VAT, so its pre-VAT amount is its full amount.

**R18. Confirmed, with the following detail.**
- Compute unused days as `(period_end.astimezone(UTC) - changed_at.astimezone(UTC)) // timedelta(days=1)`. The `//` floors toward negative infinity and returns an int.
- If the result is 0 or negative, unused days = 0, so no lines are emitted.
- If the result is above 13, clamp it to 13.
- If either datetime is naive (`tzinfo is None` or `utcoffset()` is None), raise ValueError. Also raise if either value is not a datetime.

**R19. Confirmed. Integer formulas:**
- Credit: `ceil(old_price * billable_seats * days / 13)`, computed as `-((-old_price * billable_seats * days) // 13)`.
- Charge: `floor(new_price * billable_seats * days / 13)`, computed as `(new_price * billable_seats * days) // 13`.
- VAT: `(charge * 21) // 100` when there is no VAT ID, otherwise 0.

These match the spec for all valid inputs. Negative values are rejected before the formulas run, so the floor and ceiling behaviour is well defined. Zero seats or zero days give 0, which is then skipped by R8. `days` is already clamped to 13 before the formulas are used.

**R20. Confirmed, with a flag.** An equal seat price is prorated. The credit and charge round in opposite directions, so the two can differ by at most 1 cent. For a same-price change such as a rename, the customer receives a credit and a charge with VAT on the charge. That VAT is not offset by a VAT credit (see risk 6).

**R21. Corrected. Do not use a denylist.** Use an explicit allowlist, with unknown values raising:
- "active": prorate normally.
- "trialing": return [] (R10).
- "canceled": return []. An upgrade on a canceled subscription indicates an upstream error, so log it.
- "past_due", "unpaid", "paused", "incomplete", "incomplete_expired": return [] pending review (see risk 10).
- Any other value: raise ValueError.

Prorating only "active" is the safe default. The original R21 wording ("prorate normally") is unsafe for unpaid or canceled accounts.

**R22. Confirmed.** The rounded credit is compared with 50000. Strictly greater than 50000 gives Ramón Etxeberria-Goñi. Exactly 50000 or less gives Nguyễn Thị Phương Thảo. Charges have `approved_by` = None.

**R23. Confirmed.** Each line is evaluated independently. A skipped credit does not suppress the charge, and the reverse also holds. If both are skipped, return []. The resulting invoice may not reconcile to the prices, which is acceptable (risk 20).

**R24. Confirmed, with the exact algorithm:**
- Credit description: `f"{subscription['plan_name']} until {date}"`. Charge description: `f"{new_plan['name']} until {date}"`.
- `date` is `period_end.strftime("%Y-%m-%d")`, using `period_end`'s own tzinfo as given (see risk 19).
- Suffix = `f" until {date}"`, which is 17 characters. Budget for the name = 80 - len(suffix) = 63 code points.
- If `len(name) > budget`, set `name = name[:budget - 1] + "…"` (U+2026, one code point). The total length is then exactly 80.
- Names are NFC-normalised before measuring.
- Empty names are rejected during validation, so "emptied" cannot happen. If a future template makes the budget 0 or less, raise ValueError rather than emit an over-length string.

**R25. Confirmed.** The module takes no seat delta. `billable_seats` is used as given for both the old and new plan. Callers must not pass a changed seat count.

## (c) Additional risks and open questions

1. **The 13-day period (R4) is probably wrong for monthly or annual billing.** The inputs contain no period start, so the real period length cannot be derived. If periods are 30 days, a change with 20 days left is clamped to a full credit and a full charge, which is badly wrong. Default: block the build until Ingrid confirms 13 is intentional, or supply the period length as an input.

2. **The clamp at 13 (R18) gives a full credit and charge for any change more than 13 days before period end**, including backdated changes. Default: keep the clamp as specified and confirm it explicitly.

3. **Whole-day truncation is material.** At 13 days, one day is about 7.7% of the seat price. Default: keep R18 truncation as specified and confirm that the customer-facing rule is acceptable.

4. **The R7 title conflict** is covered in (b). Default: implement the body and R19, reword the title, and get Ingrid's written position.

5. **The house rules are overridden.** R9 (credits carry no VAT) overrides the default that VAT applies to credits too. R7 and R19 (directed rounding) override the default half-up rounding. Default: treat the explicit rules as overrides and obtain written sign-off from finance.

6. **Credits carry no VAT (R9).** The customer's net invoice then contains 21% VAT on the charge with no matching VAT credit. Default: follow R9, and confirm that finance reverses VAT off-module and that the PDF presentation is acceptable.

7. **The VAT rate and place of supply are unknown.** The 21% rate is applied to everyone, and there is no country input. Non-EU customers and EU consumers may be subject to other rules, including OSS. Default: keep 21% as specified, and add a customer country input before launch.

8. **vat_id handling.** Default: strip whitespace; treat None, "", and whitespace-only as no VAT ID, which charges 21%. Any non-blank value counts as a valid ID with reverse charge. The module does not validate the format or check VIES. An invalid ID would leave VAT uncollected, so this should be confirmed with finance.

9. **The reverse-charge invoice note.** Reverse charge normally requires a legal note on the invoice. Default: finance supplies the wording, and the PDF template prints it when VAT is 0 on a charge.

10. **Status decisions (R21).** "past_due" and "unpaid" accounts may have debts, so creating credits or charges could be inappropriate. Default: return [] for these pending a business decision, as in (b).

11. **legacy_discount (R14).** Ignoring it overbills any live subscription that still depends on an effective discount. Default: confirm with Wojciech that no active subscription relies on it before removal.

12. **Validation policy.** The cases needing a policy are negative or non-int seats and prices, bool values (Python treats True as 1), missing keys, empty plan names, `billable_seats` greater than `seats`, and unknown statuses. Default: raise ValueError for all of them. Silent skipping is not safe for billing.

13. **billable_seats completeness.** After the SSO migration, every subscription needs a correct `billable_seats`. Default: raise if it is missing, and require 0 <= billable_seats <= seats.

14. **Currency.** The output has no currency field, and R16 is unconfirmed. Default: the caller asserts that all subscriptions are EUR. Adding a currency field would change R2, so it needs the tech lead's approval.

15. **Approval names.** The approval strings are hardcoded attestations, not authorisations. The module does not enforce approval. Names must match the finance system exactly, including NFC normalisation. The ledger must accept non-ASCII UTF-8. Default: store the names as NFC constants, confirm the ledger encoding, and have finance verify the names.

16. **Downgrades (R6) are not recorded.** The module returns [] and schedules nothing, so the change at renewal could be lost or applied without a record. Default: the caller must schedule the renewal change and log it.

17. **Downgrade means a lower seat price only.** A cheaper seat price with more features still counts as a downgrade, and features are not considered. Default: keep as specified.

18. **Idempotency.** The function is pure, but a caller that repeats a call will double-bill. Default: the caller keys on subscription id, changed_at, and new plan name.

19. **Timezone of the description date.** Using `period_end`'s own tzinfo can give a different date from UTC, for example 2026-11-01T00:30+02:00 renders as 2026-11-01 but is 2026-10-31 in UTC. Default: use the tzinfo as given, and confirm which timezone customers see on their invoices.

20. **Reconciliation.** Skipped sub-50-cent lines and the independence in R23 mean totals will not always match the price arithmetic. Default: finance accepts this, and the skipped amounts are logged.

21. **Scope priority (R15).** If time is short, ship credit correctness first. VAT can be deferred only if finance confirms a separate VAT process. Default: Ingrid confirms.

22. **Description wording.** "until <date>" versus "through <date>" is unconfirmed. Default: "until", as in R24.

23. **Golden test vectors.** Boundary cases need to be signed off by Ingrid before implementation. These include a credit of exactly 50000 and 50001 cents, lines of 49 and 50 cents, 0, 1, 13, and 14 days, equal prices, a DST boundary, and a naive datetime. Default: the tests are written in the implementation phase, using Ingrid's expected values where available.