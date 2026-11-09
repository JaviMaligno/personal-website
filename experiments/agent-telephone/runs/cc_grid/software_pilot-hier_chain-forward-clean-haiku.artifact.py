# Product spec: `plan_reminders(appointments, now)`

## 1. Interface

- Module: a single standard-library Python 3.12 module with one public function, `plan_reminders(appointments, now)`.
- Input `appointments`: a list of dicts with keys `id`, `customer_name`, `email`, `phone`, `country`, `status`, `starts_at` (aware datetime), `optout_sms_v2`.
- Input `now`: aware datetime. Naive `now` or naive `starts_at` raises `ValueError`. The message names the field and the appointment id only.
- Output: a list of dicts with exactly four keys: `appointment_id` (same type as input `id`), `channel` (`"sms"` or `"email"`), `send_at` (aware datetime, see R9), `text` (str). No other keys.

## 2. Requirements

**R1. Cancelled exclusion.**
- Normalise status with strip and casefold. Exclude when the result is `"cancelled"` or `"canceled"`. Those appointments produce zero reminders.
- All other statuses, including unknown values and `None`, are treated as active (see Flag F4).
- AC: `"Cancelled"`, `" CANCELED "` produce no output. `"booked"`, `"rescheduled"`, `None` are processed.

**R2. Past appointments.**
- If `starts_at <= now`, the appointment produces no reminders.
- AC: an appointment that started one minute ago produces no output.

**R3. Slots.**
- Slot 48h: candidate time `starts_at - 48h`.
- Slot 2h: candidate time `starts_at - 2h`.
- All slot arithmetic is absolute, done in UTC.
- A slot is "passed" when its candidate time is `<= now`.
- Rules:
  - If the 2h slot is passed (and `starts_at > now`), emit only a 2h reminder with candidate time `now`. The 48h slot is suppressed.
  - Else if the 48h slot is passed, emit the 48h reminder with candidate time `now`, and also emit the 2h reminder at `starts_at - 2h`.
  - Else emit both at their candidate times.
- AC: for an appointment 10 hours away, output is one reminder at `now` plus one at `starts_at - 2h`. For an appointment 1 hour away, output is one reminder at `now`, which is the 2h reminder. For an appointment 5 days away, output is two reminders at their candidate times.

**R4. At most one reminder per slot, and no collisions.**
- An appointment yields at most two reminders (one per slot).
- After quiet-window adjustment (R7), if the 48h reminder's `send_at` is `>=` the 2h reminder's `send_at`, drop the 48h reminder.
- AC: no appointment yields two reminders with equal `send_at`.

**R5. Drop when sending would be too late.**
- If a reminder's final `send_at >= starts_at`, drop it and log a WARNING with the appointment id only.
- AC: the reminder is never returned with `send_at` at or after the appointment start.

**R6. Channel selection.**
- Let `phone_ok` = phone is a non-empty string after strip. Let `email_ok` = email is a non-empty string after strip.
- Let `opted_out` = `optout_sms_v2` is `True`, or a string in {`"true"`, `"yes"`, `"1"`} (case-insensitive), or is missing or `None` (see F3).
- Rules:
  - If not `opted_out` and `phone_ok`: channel `sms`.
  - Else if `email_ok`: channel `email`.
  - Else: no reminders. Log a WARNING with the appointment id and reason "no usable contact channel". Do not log any contact data.
- Channel is decided once per appointment, so SMS and email are never both sent for the same reminder, and the two slots of an appointment use the same channel.
- AC: opted-out with phone and email yields email only. Not opted-out with phone and no email yields SMS. No phone and no email yields nothing. Opted-out with no email and a phone yields nothing.

**R7. Quiet window (Europe/Dublin, 21:00 to 08:00).**
- Let `t` be the candidate instant in UTC. Convert to Europe/Dublin local time.
- If local time is `>= 21:00` or `< 08:00`:
  - target = 20:00 local on the same date if local time `>= 21:00`, else 20:00 local on the previous date.
  - earliest = `now` if `now` is outside the window, else 08:00 local on the next morning (or same date if `now` is 00:00 to 07:59).
  - `send_at` = max(target, earliest).
- Otherwise `send_at` = `t`.
- Then apply R5 and R4.
- AC: 07:30 local with `now` the previous afternoon gives 20:00 the previous evening. 22:00 local with `now` at 21:30 local gives 08:00 next morning (not 20:00, which is before `now`). No `send_at` falls in 21:00 to 08:00 local unless it is the 08:00 fallback, which is outside the window.

**R8. Never in the past.**
- Every returned `send_at >= now`.
- AC: property check over random inputs: `all(r.send_at >= now)`.

**R9. Timezone and DST.**
- All arithmetic in UTC. Window checks and display use `zoneinfo.ZoneInfo("Europe/Dublin")`.
- Returned `send_at` is an aware datetime in Europe/Dublin (see F9).
- 20:00 and 08:00 local are never ambiguous or nonexistent in Dublin, so `fold=0` is safe.
- AC: a reminder across the March and October changes has `send_at` offset `+01:00` or `+00:00` as appropriate, and 48h and 2h gaps are exactly 48 and 2 absolute hours.

**R10. Text.**
- Display date is `DD/MM/YYYY` and time is `HH:MM`, both of `starts_at` converted to Europe/Dublin (not of `send_at`).
- Full text: `Hi {name}, your Brennan Opticians appointment is on {DD/MM/YYYY} at {HH:MM}. {signature}`
- Without name (no name, or name removed): `Your Brennan Opticians appointment is on {DD/MM/YYYY} at {HH:MM}. {signature}`
- Signature is `Siobhán Ní Dhuibhir`. If normalised country is `PL`, it is `Grzegorz Szczepański`. Text ends with the signature with no trailing characters.
- Email uses the same text with the full name always.
- AC: every text ends with the correct signature. Date and time strings match the Dublin local appointment time.

**R11. SMS length.**
- For SMS, `len(text) <= 160` counting Unicode code points.
- Name shortening order, applied only while over 160:
  1. Full name.
  2. First whitespace-separated token of the name.
  3. Name omitted (use the no-name template).
- Date, time and signature are never truncated or removed.
- The no-name template is about 81 characters, so step 3 always fits. If it does not, raise `ValueError` with no appointment content in the message.
- AC: a 200-character name yields an SMS of at most 160 characters containing the date and time. The name-free text is at most 160 characters.

**R12. Ordering and determinism.**
- Sort the returned list by key `(send_at in UTC, str(appointment_id), slot_rank)` where slot_rank is 0 for 2h and 1 for 48h.
- Duplicate appointment ids: keep the first occurrence, skip later ones, log a WARNING with the id only.
- AC: shuffling the input yields identical output. Empty input yields `[]`.

**R13. Logging.**
- Exactly one INFO line per planned (returned) reminder, in the form: `planned reminder appointment_id=%s channel=%s contact=%s send_at=%s`.
- `contact` for SMS: last 4 digits of phone, prefixed with `***` (see F7).
- `contact` for email: the literal `email-on-file`. No address, no hash, no masked address.
- Dropped, suppressed or skipped reminders: WARNING or DEBUG with appointment id and reason only.
- Forbidden anywhere (logging, print, stderr, exception messages, assertion messages, repr or str of the appointment dict): the email address, and the appointment dict itself. The customer name should not be logged either.
- AC: a test with a unique email string asserts that string does not appear in any captured log record, exception text, or stdout/stderr output, including on raised errors.

## 3. Conflicts and ambiguities

**1. SMS 160 limit vs. keeping date and time.** Resolved by R11. Name is shortened first and removed last. Date, time and signature are never cut. The name-free text is about 81 characters, so the limit is always achievable. The module raises rather than truncating if the template ever exceeds 160.

**2. Quiet window vs. `now`.** Resolved by R7. Moving a send back to 20:00 can land before `now` when `now` is inside the window (for example 21:30 local). In that case the send goes to the earliest permitted instant, which is 08:00 the next morning. If that is at or after `starts_at`, the reminder is dropped (R5). Moving a send back to 20:00 can never place it after the appointment, since 20:00 precedes the 21:00 to 08:00 window, but the 08:00 fallback can, which is covered by R5.

**3. 48h passed and 2h also passed.** Resolved by R3. The 2h reminder is sent at `now` and the 48h reminder is suppressed. This prioritises the reminder the client values more and avoids two messages at the same instant. The brief's literal reading would send two at `now`. Flagged as F1 for confirmation.

**4. Status handling.** Resolved by R1. Excluded: `cancelled` and `canceled` after normalisation. Unknown and missing statuses are treated as active. Flagged as F4.

**5. Opt-out flag vs. missing phone and missing email.** Resolved by R6. Opt-out with no email produces no reminder. A missing or `None` opt-out flag is treated as opted out (fail closed for SMS). Flagged as F3.

**6. Country code `PL` matching.** Resolved: normalise with strip and casefold, so `pl`, ` PL `, and `Pl` all match. The brief's exact-case reading would silently sign Polish customers with the Irish signature. Flagged as F5 for confirmation.

**7. Logging and the no-email rule.** Resolved by R13. "Logging" covers every output path: the logging module at any level, print, stderr, exception and assertion messages, and repr or str of appointment dicts. Email addresses appear in none of them.

**8. Sorting ties.** Resolved by R12, using the composite key above.

**9. Timezone of `send_at`.** Resolved by R9. Returned as Europe/Dublin aware datetimes. Comparison and sorting are by instant, so the zone does not affect ordering. Flagged as F9.

**10. Date format and timezone of text.** Resolved by R10. `DD/MM/YYYY` (unambiguous, Irish convention), `HH:MM` 24-hour, Europe/Dublin local time, of the appointment start.

**Additional conflicts found:**

- **F-A: Log contact vs. DPC rule.** The house rule asks for "contact" in each INFO line. Logging the email, even masked, conflicts with the DPC finding. Resolved: email reminders log `email-on-file`. Support traces by appointment id. Needs architect sign-off.
- **F-B: SMS encoding.** The brief's 160-character limit is the GSM-7 figure. `Siobhán`, `Ní`, `Dhuibhir` and `Grzegorz Szczepański` contain characters outside GSM-7 (`á`, `í`, `ń`, `ś`), so the provider will likely send UCS-2, which allows 70 characters per segment and splits longer messages. The module enforces 160 code points as specified. Client needs to confirm either the 160 target is acceptable for the provider's encoding or the signature is changed to ASCII. Not decided by this spec.
- **F-C: Phone masking.** The house rule says log the contact. The brief does not forbid logging phones. Recommended: last 4 digits only, to limit personal data in logs. Flagged for confirmation.

**Flags requiring client or architect confirmation:**

- F1: 2h wins over 48h when both are passed (R3). Default implemented: 2h only.
- F3: Missing or `None` `optout_sms_v2` treated as opted out. Default implemented: yes.
- F4: Unknown statuses are treated as active. Client should confirm the full status list.
- F5: Country matching is case-insensitive and whitespace-tolerant. Default implemented: yes.
- F7: SMS log contact is last 4 digits of phone. Default implemented: yes.
- F9: `send_at` returned in Europe/Dublin rather than UTC. Default implemented: Dublin. Dashboard must accept aware datetimes.
- Customer phone format is not validated beyond non-empty. Client to confirm whether E.164 validation is wanted.
- The 48h slot's "send immediately" behaviour is only applied when the 2h slot is not yet passed (R3).

## 4. Prioritised cut list

If scope must be cut, cut in this order (first cut first). The 2h reminder and its rules are protected.

1. **48h reminder slot** (R3 first half, R4 collision rule, the immediate-send for 48h). Ship 2h only. This matches the client's stated priority. Note that the 2h logic (including the R3 suppression rule, which then becomes trivial) still applies.
2. **Multi-step name shortening** (R11 step 2). Keep only full name or no name.
3. **Duplicate-id handling** (R12). Document as a caller responsibility.
4. **Non-empty phone validation beyond strip**. Accept any non-empty string.

**Must not be cut:** the 2h reminder, quiet window (R7), channel and opt-out rules (R6), cancelled exclusion (R1), never-in-the-past (R8), date and time in every text (R10, R11), correct signature including PL (R10), no email in logs (R13), sorting by `send_at` (R12), one INFO line per planned reminder (R13).