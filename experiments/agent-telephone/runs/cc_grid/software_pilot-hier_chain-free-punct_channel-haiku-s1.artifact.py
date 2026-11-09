I could not run the zoneinfo or length checks in this session, so the figures below are worked by hand. Confirm them with a short `python3 -I` script outside the project directory before relying on them.

**(a) Feasibility problems**

- Literal rule 3 would text customers who have opted out. The fail-closed reading is the only safe one, but it is still an interpretation.
- The house rule to log "contact" conflicts with rule 7 and with ordinary personal-data care. Logging phone numbers in plain text is avoidable.
- Using len() for the 160 check is wrong for these signatures, because they are not GSM-7 and the message goes out as UCS-2.
- Subtracting 48 hours from a ZoneInfo-aware datetime uses wall-clock time, not elapsed time. Example: a start of Monday 29 March 2027 10:00 IST has a true 48-hour point of Saturday 27 March 09:00 GMT. Naive subtraction gives 10:00 GMT, which is 47 real hours. Compute all offsets from UTC.
- The "first reminder" rule must key on the 48-hour offset, not on tuple index. Otherwise stage 1, with offsets (2,), would apply the immediate-send rule to the 2-hour reminder.
- Sorting on appointment_id raises TypeError if ids mix int and str.
- ZoneInfo needs a tz database on the server. Since the module is stdlib-only, confirm the server image has one.

**(b) Figures**

- "Siobhán Ní Dhuibhir" is 19 characters. "Grzegorz Szczepański" is 20. Both contain characters outside GSM-7 (á, í, ń), so the message is UCS-2. A single UCS-2 SMS holds 70 UTF-16 code units, and concatenated segments hold 67 each. A 160-unit message therefore takes three segments.
- Sample template: "Hi {name}, your Brennan Opticians appointment is on {date} at {time}. " with DD/MM/YYYY dates is 64 characters before the name. With the Irish signature the fixed part is 83, leaving 77 for the name. With the Polish signature it is 84.
- Under a strict single-segment rule of 70 units, the fixed parts alone exceed the limit, so no SMS could ever be sent. The fixed-parts-too-long case cannot occur with this template unless the fixed text grows past 160.
- 2026-10-25 is the last Sunday of October. Clocks go back at 01:00 UTC, so local 01:00 to 01:59 occurs twice. 2027-03-28 is the last Sunday of March. Clocks go forward at 01:00 UTC, so local 01:00 to 01:59 does not exist. 20:00 is neither ambiguous nor in a gap on either date. Build quiet-window instants from UTC, not from local wall-clock constructors. The previous-day 20:00 targets on 24 October and 27 March are unambiguous.

**(c) Recommendations, ranked by impact**

1. Rule 3. Implement opt-out meaning no SMS. Fail closed when the flag is missing or not a boolean. Get written client confirmation before go-live. Do not implement the literal inverse.
2. Contact logging. Log appointment_id, channel, and the last four digits of the phone. Never log the email. The house-rule owner should confirm this.
3. Encoding. Count UTF-16 code units, keep 160 as the client's cap, and tell the client this means up to three segments. Ask whether they want a 134-unit cap (two segments) or an ASCII-folded signature, which conflicts with "exact".
4. Quiet versus immediate. The proposal is defensible but I would change it. When the 20:00 target has passed and now is within 08:00 to 21:00, sending at now is late-evening for a morning appointment. I recommend deferring to the 08:00 that ends the quiet window, or to now if that is later. Drop any reminder whose send time is at or after starts_at. Client should choose between the two.
5. Email channel. Keep it unreachable. Enabling it requires its own consent field, because optout_sms_v2 is SMS-specific.
6. Immediate send in stage 1. Key it to the 48-hour offset so it stays dormant.
7. Quiet-hour timezone. Dublin local, as proposed. Low risk.
8. Fixed-parts-too-long. Return None, log sms_too_long, and never fall back to email.
9. Two-hour point already past. Omit and log the reason. Confirm with client.

**(d) Ambiguities I missed**

- Template wording and date format were not supplied.
- Missing customer_name, and how the first name is derived for hyphenated or particle names.
- Status matching should be case- and whitespace-tolerant. Consider an allow-list for sending rather than skipping only "cancelled".
- Naive starts_at should be rejected explicitly.
- Confirm whether 21:00 is quiet and 08:00 is allowed, as the proposal assumes.
- Country normalisation (strip and case-fold) deviates from the exact match the design lists. Confirm.
- Some regimes may require an opt-out keyword in the text. Confirm.
- Phone validation is only a non-empty check. Consider format validation.

**(e) Stage 1 cut**

Confirm 2-hour only, and confirm the consequences. Appointments starting between 08:00 and 10:00 get their reminder at 20:00 the previous evening. Appointments less than two hours ahead get nothing. The 48-hour rule is dormant.