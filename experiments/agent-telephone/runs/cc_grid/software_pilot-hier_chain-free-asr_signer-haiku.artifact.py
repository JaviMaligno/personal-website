## Verdict

The design is sound on the core timing rules: absolute UTC arithmetic, the quiet-hour shift, the single-reminder rule when 2 hours has passed, and the DST examples all check out. I verified the DST dates (2026-03-29 and 2026-10-25 are the last Sundays) and the 20:00 GMT example. It needs corrections in four areas: the logging rule conflicts with the privacy rule, the output has no recipient, duplicate send times can occur, and the length budget figure is wrong.

## Corrections

1. **Logging conflict (must resolve before implementation).** The house rule requires one INFO line per planned reminder saying who it goes to and how (channel and contact). Client rule 7 forbids logging the email address, and the design also bans logging phone numbers and names. Recommended resolution: INFO per reminder logs appointment_id, channel, and UTC send_at, plus a masked contact. For SMS, log only the last 4 digits of the phone. For email, log "contact=withheld" and do not log the address or its domain. Escalate to the PM to confirm this, because the house rule and client rule 7 cannot both be satisfied literally for email. The design's DEBUG-only per-reminder line must move to INFO.

2. **No recipient in output.** The output keys are fixed to appointment_id, channel, send_at, and text, so the caller cannot find the SMS number or email address. The design must state that the caller resolves contact details from appointment_id, or the client must approve an extra field. Do not add the address to the output without that approval.

3. **Duplicate reminders.** Two candidates can resolve to the same (channel, send_at). Example: the 48-hour point has passed, so candidates are now and t2. If t2 is quiet and shifts to a time before now, which then clamps to now, both candidates become now. The same happens when both resolve to the next 08:00. Add a rule: deduplicate on (appointment_id, channel, send_at) before returning.

4. **Length budget.** Counting the template with "Hello," and the 19-character signature "Grzegorz Szczepański" gives 89 characters, not "about 91". The test should assert the computed value is at most 160 and should not hard-code 91.

5. **Arithmetic pitfall.** Subtracting a timedelta from a datetime that carries a ZoneInfo tzinfo does wall-clock arithmetic and breaks the absolute-duration rule. All t48 and t2 math must be done in UTC. The 20:00 and 08:00 local targets should be built by combining the local date with a time and tzinfo, with fold=0, then converted to UTC.

6. **"Passed" boundary.** The design does not say whether a candidate exactly equal to now counts as passed. Define: a candidate is in the future only if it is strictly greater than now. Equal to now counts as passed and is replaced by now.

7. **Invalid-record definition.** The design says to validate fields but does not define invalid. Define it: non-dict, missing or empty id, non-string or unknown status, naive starts_at, and non-datetime starts_at are invalid and skipped with a WARNING. Only a naive now raises ValueError. Fields that are None for name, email, phone, or country are treated as empty, not invalid.

8. **Product consequence to surface.** For starts between about 06:00 and 10:00 local, the 2-hour reminder falls in quiet hours and moves to the previous evening, about 12 or more hours early. This is what rule 5 requires, but the PM should know the 2-hour reminder will not be a true 2-hour reminder for early appointments.

9. **Wording of rule 5.** "Moves back to 20:00 the same evening" fits 21:00 to 23:59 only. The design's previous-evening reading for 00:00 to 07:59 is the only workable one, so it should be stated as an interpretation for client confirmation (open question a).

10. **Name fallback.** The final fallback drops the name entirely and changes the greeting to "Hello,". This satisfies "shorten the name" but should be stated explicitly.

11. **Test file location.** Not specified. Suggest tests/test_appointment_reminders.py alongside the module.

## Final ordered plan with acceptance criteria

1. **Skeleton, now validation, public signature.** Criteria: plan_reminders(appointments, now) exists; a naive now raises ValueError with a message containing no field values; an empty list returns an empty list; the module logger is "brennan.reminders".

2. **Validation, eligibility, channel choice.** Criteria: cancelled and canceled (after strip and lowercase) are skipped with reason cancelled; started appointments are skipped; no-contact records are skipped; optout_sms_v2 exactly False with a phone yields SMS; opt-out with email yields email; opt-out with no email yields nothing; missing phone with email yields email; a missing or non-boolean optout flag yields a WARNING and is treated as opted out; the opt_out field is never read.

3. **Candidate timing and single-reminder rule.** Criteria: both future yields t48 and t2; t48 passed with t2 future yields now and t2; t2 passed yields exactly one reminder at now; the 2-hour candidate is correct in all cases; the DST example gives 11:00 IST on 2026-10-23 for a 10:00 UTC start on 2026-10-25.

4. **Quiet-hour resolution, past clamp, start cutoff, DST.** Criteria: boundary tests at 20:59 (not quiet), 21:00 (quiet), 07:59 (quiet), and 08:00 (not quiet); early-morning shift goes to the previous 20:00; 02:30 on 2026-10-26 gives 20:00 UTC on 2026-10-25; 01:30 on 2026-10-25 with fold 0 and fold 1 both give 20:00 IST on 2026-10-24; now in quiet hours clamps to next 08:00; results at or after starts_at are dropped; an internal assertion checks no result is quiet or before now.

5. **Text building and signature selection.** Criteria: date is "D Mon YYYY" with no leading zero using an English abbreviation table; time is 24-hour HH:MM from starts_at in Dublin local; the greeting is "Hello," when the name is empty; PL is selected for "pl" and " PL " after strip and uppercase; the text ends with the signature with no trailing punctuation.

6. **SMS fitting.** Criteria: texts of 160 characters or fewer are unchanged; each fallback step (full name, first token, initial with period, no name) is tested at its boundary; the no-name fallback is at most 160 characters for both signatures; the date and time are never dropped; email has no length limit.

7. **Dedupe, sorting, assembly.** Criteria: duplicate (appointment_id, channel, send_at) entries are removed; output is sorted by (UTC send_at, str(appointment_id), channel); send_at is UTC; only the four keys are present.

8. **Logging and privacy.** Criteria: one INFO line per planned reminder with id, channel, UTC send time, and the masked contact per correction 1; one INFO summary with input count, output count, and skip counts by reason code; DEBUG per-reminder detail; WARNING for invalid records and missing opt-out flags with id and reason code only; a caplog test confirms a distinctive email string appears in no record at any level and in no exception text; exceptions are logged by class name only.

9. **Full pass and review.** Criteria: all tests pass with pytest and an injected now; no pytz and no fixed offsets; no reference to the legacy code; no locale-dependent formatting; the code is reviewed against all ten client rules.

## Open questions

- (a) Early-morning quiet shift. Assumed: previous evening's 20:00. Client must confirm, because the "same evening" wording only fits 21:00 to 23:59.
- (b) Quiet versus past. Assumed: fallback is now if now is not quiet, otherwise next 08:00. Client should confirm.
- (c) Both reminders past. Assumed: one reminder at now. Client should confirm, since it is inferred from rule 2 and the no-gap intent.
- (d) Reminder that resolves at or after start. Assumed: dropped. Client must confirm, because the appointment then goes unannounced.
- (e) Date format "27 Oct 2026". Assumed as stated. Low risk; confirm.
- (f) 48 and 2 hours as absolute durations. Assumed absolute. Client should confirm.
- (g) 160 limit. Assumed to count Python characters. Client must confirm. With UCS-2, because of ń and ś, the 70-character segment limit applies. Even the 89-character fixed part exceeds 70, so every PL SMS would be two segments.
- (h) No phone and no email produces no reminder. Client should confirm.
- (i) Opt-out with no email produces no reminder and does not fall back to email. Client should confirm.
- (j) Statuses other than cancelled and canceled are sent. Assumed. Client should confirm, for example for no_show or completed.
- (k) Missing or non-boolean optout_sms_v2 is treated as opted out for SMS, with email fallback. Client should confirm.
- (l) send_at returned in UTC. Assumed. Low risk; confirm.
- (m) Already-started appointments produce nothing. Inferred from rule 2 and the start cutoff; confirm.
- (n) Email subject line and phone E.164 validation. Assumed neither is required by the module. Client must confirm.
- (o) Duplicate appointment ids are not deduplicated at input. Assumed. Confirm; the caller is responsible for unique ids.
- (p) Recipient resolution. Assumed the caller joins on appointment_id because output has no contact field. Client must confirm.
- (q) House-rule INFO contact versus client rule 7. Assumed masked SMS phone and withheld email contact. The PM must confirm.