## Design

**Entry point:** `plan_reminders(appointments, now)`. Reject a naive `now` with a ValueError whose text contains no contact data. All scheduling arithmetic uses UTC instants. Europe/Dublin conversion (zoneinfo) is used only for quiet-hours checks and for the text.

**Private helpers:**
- `_dublin(dt)`: converts to Europe/Dublin.
- `_channel(appt)`: returns SMS if phone is non-blank and `optout_sms_v2` is not true, else email if present, else nothing. Never both.
- `_slots(starts_at, now)`: the 48h and 2h instants, with past points clamped to `now` (see decision 2).
- `_quiet(send_at, now)`: applies the quiet-hours rule (decision 1).
- `_signature(country)`: PL rule (decision 6).
- `_sms_text` and `_email_text`: name shortening and length check (decision 3).
- `_log_planned` and `_log_skipped`: ID-only logging (see logging below).

**Data flow:**
1. Drop cancelled appointments.
2. Choose channel. If none, log an ID-only skip and continue.
3. If `starts_at` is at or before `now`, skip.
4. Compute the 48h and 2h slots, clamp, apply quiet hours, and drop any result at or after `starts_at`.
5. If both slots resolve to the same `send_at`, keep only the 2h one.
6. Build text and log one INFO line per reminder.
7. Sort by `(send_at, str(appointment_id))`.

**Edge cases:**
- The 48h subtraction must be done on UTC instants. Subtracting on Dublin wall-clock time gives an hour's error across DST. Example: 02:30 GMT on 26 Oct 2026 minus 48h is 03:30 IST on 24 Oct.
- Text date and time come from `starts_at` converted to Dublin. A 00:30 appointment on 25 Oct 2026 shows 25/10/2026 00:30.
- Aware inputs never hit the spring gap on 29 Mar 2026. The quiet-hours check on local hour remains correct.
- Ties: identical `send_at` values across different appointments are allowed and ordered by ID. A single appointment never yields two reminders at the same instant.

## Decisions (recommended defaults)

1. **Quiet hours.** The window is [21:00, 08:00) Dublin local. A slot at 21:00 to 23:59 moves to 20:00 the same date. A slot at 00:00 to 07:59 moves to 20:00 the previous date. If the moved time is before `now`, use 08:00 local the next morning instead. Keep the result only if it is before `starts_at`, otherwise skip. If `now` is inside quiet hours, the first permitted instant is 08:00 next morning, which this rule produces. **Flag:** 08:00 is the one place the literal "20:00 before" rule is overridden.

2. **2h point passed, `starts_at` still future.** Send at `now` (subject to quiet hours), because the 2h reminder matters more. **Flag:** this departs from a strict skip. If 48h also resolves to `now`, the two collapse into one 2h reminder. Two identical-time texts would be spam. PM may override.

3. **Name shortening, in order:** full name, then first given name, then first initial plus surname, then no name. Shorten only at word boundaries. Date, time and signature are never removed or shortened. The signature is never dropped. The minimum SMS is the no-name template, about 80 characters. If that still exceeds 160 (only possible with an absurd signature), skip and log the ID.

4. **No usable contact.** If there is no email and either opt-out is set or there is no phone, produce nothing and log one ID-only skip line with a reason code.

5. **Status and past dates.** Exclude only a status that normalises (strip, lower) to "cancelled". Any other value, including missing, is treated as active. **Flag:** PM to confirm whether completed or no-show should be excluded. `starts_at` at or before `now` is skipped.

6. **Signature.** The same text is used for SMS and email. PL rule: `country.strip().upper() == "PL"`, which gives Grzegorz Szczepański. Otherwise Siobhán Ní Dhuibhir. Use the normalised match because CRM values vary in case and whitespace.

7. **Date and wording.** Date is DD/MM/YYYY and time is HH:MM, both Dublin local.
   - SMS: `Brennan Opticians: appointment for {name} on {date} at {time}. {sig}`. With no name: `Brennan Opticians: appointment on {date} at {time}. {sig}`.
   - Email: `Dear {name}, this is a reminder of your appointment at Brennan Opticians on {date} at {time}. Kind regards, {sig}`. With no name, use "Dear customer".

8. **Length and encoding.** Count `len(text)` against 160, as briefed. **Flag:** the signature itself contains á and í (Siobhán, Ní), and the PL signature adds ń and ś. None of these are in GSM-7, so every SMS is UCS-2. Under UCS-2 a segment carries 70 characters, so a "160-character" text is really two or three billable segments. Keep the 160 rule as briefed. Raise with the PM an ASCII-transliterated signature option ("Siobhan Ni Dhuibhir"). Do not transliterate silently.

9. **Output fields.** None beyond the four keys. Pádraig's dashboard depends on that contract. Extra fields such as name or reason would push personal data into dashboards and risk breakage. Skip reasons stay in logs, keyed by ID.

**Logging.** The house rule asks for recipient and contact in each line. The tech lead says log IDs only and never an email. I recommend logging `appointment_id`, channel and `send_at` only, with no phone or email fragment. **Flag for PM and DPO sign-off.**

## Test cases (descriptions and expected results)

1. Both slots future, daytime: two reminders, sorted, correct text.
2. Status "Cancelled" with whitespace: no reminders.
3. 48h passed, 2h future: 48h reminder at `now`, plus the 2h one.
4. 2h passed, start future: one reminder at `now`.
5. `starts_at` in the past: none.
6. optout true with email: email only.
7. optout true, no email: none, ID-only log.
8. Phone and email, optout false: SMS only.
9. No phone, email present: email.
10. Country " pl ": Polish signature.
11. Slot at 02:00 local: send_at 20:00 previous evening.
12. Slot at 21:30 local: send_at 20:00 same evening.
13. `now` 22:00, 2h slot 23:00: 08:00 next morning if before start, else none.
14. Slot exactly 08:00: allowed. Slot exactly 21:00: shifted.
15. DST fall-back: start 02:30 GMT 26 Oct 2026 gives 48h send at 03:30 IST 24 Oct.
16. DST spring: start 14:00 IST 29 Mar 2026 gives 48h send at 13:00 GMT 27 Mar.
17. Both slots clamp to `now`: exactly one reminder.
18. Long name: full name fits, then shortened in order, date, time and signature always present.
19. Captured log output contains no "@" and no email address.
20. Naive `now`: ValueError.
21. Every output dict has exactly four keys.
22. Two appointments with the same `send_at`: ordered by ID.

## Open risks

- SMS encoding and cost (decision 8). This is the largest risk.
- Logging contact conflict (above).
- zoneinfo needs system tzdata. Minimal server images may lack it, so verify before go-live.
- Phone numbers are not validated here. A malformed number fails downstream, not in this module.
- Unknown status vocabulary (decision 5).
- The 08:00 override and the collapse rule both depart from literal wording and need PM sign-off.