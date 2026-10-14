# Appointment Reminders: Design for `plan_reminders(appointments, now)`

This is a design only. No code or report files were written. The design is blocked on the items in section 5, mainly the R7/O3 channel rule and the R12 logging conflict. Until those are resolved, the module should not go to production.

## 1. Requirement breakdown

| ID | Requirement (short) | Design element | Conflict or open point |
|---|---|---|---|
| R1 | Entry point returns dicts with exactly four keys | `plan_reminders`; output dict has only `appointment_id`, `channel`, `send_at`, `text` | Reminder "kind" (48h or 2h) is not a key, so ties rely on generation order (see R15). Do not add keys without dashboard sign-off. |
| R2 | Use `optout_sms_v2` only | `choose_channel` reads only this flag | Flag false with a phone is unresolved (O3). Name suggests true means opted out, which makes the literal R7 inverted (see R7). Missing or None flag is treated as unresolved. |
| R3 | Text states date and HH:MM | `render_sms` and `render_email` format the Dublin-local start time | Date format not specified. Proposed: `26 Oct 2026` (unambiguous). Client to confirm. |
| R4 | First reminder at starts_at minus 48h; second at minus 2h | `planned_send_times` | Conflicts with O1 when the 2h point has passed. O1 sends at `now`; literal R4 would drop it. |
| R5 | If the 48h point has passed, send first reminder at `now` | Clamp nominal send to `now` before quiet hours | Ordering dependency: clamp must run before quiet-hour adjustment. |
| R6 | No send_at before `now` | Final guard in `plan_reminders`; also checked after quiet-hour adjustment | Moving back to 20:00 can land before `now` (O5). Resolved by the O5 rule. |
| R7 | Phone and opt-out true means SMS, do not send email | `choose_channel`, isolated and rule-switchable | Literal reading sends SMS to customers who opted out, likely inverted. The O3 proposal sends email instead, which contradicts the literal "do not send an email instead". BLOCKING. |
| R8 | Never both SMS and email for one reminder | `choose_channel` returns exactly one channel or none | None. |
| R9 | SMS at most 160 characters; shorten name, keep date and time | `render_sms` with name-shortening ladder | Conflicts with carrier reality. The non-GSM-7 characters force UCS-2 (70 per single segment). See O2. |
| R10 | No sends 21:00 to 08:00 Dublin; move to 20:00 | `apply_quiet_hours` | "Same day" fits only 21:00 to 23:59. For 00:00 to 08:00, the target is 20:00 the previous day (O5). |
| R11 | Exclude status "cancelled" | `is_active` | "canceled" spelling and case variants are not covered (O4). |
| R12 | Never log email, including in exceptions and reprs | Logs carry only `appointment_id`, channel, masked contact; exceptions name fields, not values | Conflicts with the house rule to log "contact". For email, the contact is the email address, which R12 forbids. BLOCKING for logging design. |
| R13 | Signature on every message; PL gets Grzegorz Szczepański | `signature_for(country)`; signature never shortened | Country normalization (strip and uppercase) is assumed. Missing country defaults to the Irish signature (pending). Signature length adds to the SMS budget. |
| R14 | Dublin time for appointments and quiet hours; aware datetimes returned | `to_dublin`; all arithmetic on aware UTC; returned values in UTC | Naive `now` or `starts_at` raises ValueError. stdlib `zoneinfo` needs the tz database (see section 3). |
| R15 | Sort by send_at, appointment_id, channel | Stable sort at end of `plan_reminders` | Two reminders for the same appointment can tie fully (duplicate case). The stable sort keeps generation order: 48h before 2h. |
| R16 | If scope is cut, keep the 2h reminder | Build the 2h path first; 48h path is additive | None. |
| R17 | Ignore legacy SMS code | Module imports only stdlib; no reference to the legacy folder | None. Verified by test J1. |

Cross-cutting conflicts to resolve with the client:
- R7 against O3 (blocking). The literal reading sends SMS to opted-out customers. The proposed reading sends email, which R7 explicitly forbids.
- R12 against the house logging rule (blocking).
- R9 against carrier segmentation (O2).

## 2. Design decisions for O1 to O5

### O1: 2h reminder when its time has passed

Chosen rule (PM default):
- If `starts_at <= now`, send nothing for the appointment.
- If the 48h point has passed (and `starts_at > now`), the first reminder is sent at `now`.
- If the 2h point has passed (and `starts_at > now`), the second reminder is sent at `now`.
- Both reminders are sent even if they land together.

Reason: this satisfies R6 and R5 and gives the customer a reminder for short-notice bookings.

Duplicate-looking pairs (flagged): when `starts_at - now < 4h`, the two send times fall within 2h of each other. When `starts_at - now <= 2h`, both are sent at `now` with identical text. That is two identical SMS at the same instant. Two alternatives for the client to decide: send only the 2h reminder when both would land at `now`, or accept the duplicate. The PM default is kept, not silently changed.

Confirmation: needed. The client must confirm the duplicate behavior.

### O2: SMS 160-character limit

Chosen rule (PM default, with additions):
- Measure the full SMS body in characters after NFC normalization. This includes greeting, date, time, and signature.
- The limit is 160 code points, as the client stated.
- Shortening order applies to the greeting name only:
  1. Full name.
  2. First initial plus remainder of name. Proposed: everything after the first token, so "Siobhán Ní Dhuibhir" becomes "S. Ní Dhuibhir". This is a known limitation for surnames with multiple parts; confirm.
  3. No name ("Hi,").
- Date, time, and signature are never truncated. If the message is still over 160 characters, no SMS is returned. A fault is logged with `appointment_id` only. There is no automatic email fallback, because that would change the channel silently and conflicts with the PM's rule.
- Email has no length limit and always uses the full name.

Carrier risk (flagged): "á", "í", "ń", and "ś" are outside GSM-7. The text is therefore sent as UCS-2, where a single segment carries 70 characters and concatenated segments carry 67 each. The 160 figure is a GSM-7 single-segment number. Most real messages in this design will be two segments. The default signature alone already forces UCS-2. The client must decide whether the 160 limit is a character budget (the default) or a single-segment guarantee. A 70-character guarantee would make most texts impossible without dropping the signature, which R13 forbids.

Confirmation: needed.

### O3: Channel rule

Chosen rule: channel selection is in one isolated function with a rule parameter, `literal` or `proposed`. The default is `proposed`, marked provisional.

| Case | Literal reading | Proposed reading (default, provisional) |
|---|---|---|
| Phone present, flag true, email present | SMS only | Email only |
| Phone present, flag true, no email | SMS | No reminder |
| Phone present, flag false | UNRESOLVED: no reminder, WARNING | UNRESOLVED: no reminder, WARNING |
| Phone present, flag missing or None | UNRESOLVED | UNRESOLVED |
| No phone, email present | Email | Email |
| No phone, no email | No reminder | No reminder |

Reason: the literal reading likely contacts opted-out customers by SMS. The proposed reading matches the intent implied by the flag name but contradicts R7's literal wording. Neither should be final without client sign-off. Flag-false cases fail closed (no message, warning) until the client decides.

Confirmation: needed, blocking.

### O4: Other status values

Chosen rule (PM default, with additions):
- Compare status after strip and casefold. Only "cancelled" is excluded.
- Recommendation (needs confirmation): also exclude "canceled". Treating a cancelled appointment as active sends a reminder for an appointment that no longer exists. Excluding it is the safer error.
- Other values are active. A WARNING is logged. The status is logged only if it is on a short known list. Otherwise the log says "unrecognised", so no free text leaks into logs.

Confirmation: needed. The full list of real status values is blocking for sign-off.

### O5: Quiet hours and the 20:00 move

Chosen rule (PM default, with clarifications):
- Window is [21:00, 08:00) Dublin local. 08:00 itself is allowed. 21:00 is in the window.
- Target time for a send in the window: 20:00 on the date on which the window opened. For 21:00 to 23:59 on day D, that is 20:00 on D. For 00:00 to 07:59 on day D, that is 20:00 on D-1. The "same day" wording only fits the first case, so the second case follows "just before the window".
- If the target is at or after `now`, use it.
- If the target is before `now` and `now` is inside the window, defer to the next 08:00 Dublin, but only if that is before `starts_at`. Otherwise drop the reminder.
- If the target is before `now` and `now` is outside the window, send at `now`.

Flagged problem: the deferral can give a 2h reminder that is less than 2h before the appointment. Example: `now` is 22:00 on 13 Oct, `starts_at` is 09:00 on 14 Oct. The 2h reminder is deferred to 08:00, which is 1h before. Both reminders then land at 08:00 as a duplicate pair. The rule is kept as specified, but the client should decide whether a deferred 2h reminder must still meet a maximum lead time, or be dropped.

Confirmation: needed. The deferral rule departs from the literal R10 wording.

## 3. Implementation plan

Module layout: one module, `reminders.py`, standard library only. Imports: `datetime`, `logging`, `unicodedata`, `zoneinfo`.

Tz database note: `zoneinfo` uses the system tz database on Linux and macOS, and so needs no extra package. On Windows, or on a minimal container without `/usr/share/zoneinfo`, the third-party `tzdata` package is required. This breaks the stdlib-only constraint, so confirm the target server image has the system database. The server runs in UTC, which suggests a Linux container; verify it.

Constants: `DUBLIN` (ZoneInfo), `FIRST_LEAD` (48h), `SECOND_LEAD` (2h), `WINDOW_START` (21:00), `WINDOW_END` (08:00), `SMS_LIMIT` (160), `DUPLICATE_THRESHOLD` (4h, for the flag), `ACTIVE_STATUS_EXCLUDED` ({"cancelled"} pending O4).

Functions, in build order:
1. `require_aware(value, field_name) -> None`. Raises ValueError naming the field only.
2. `is_active(appt) -> bool`. Status rule (R11, O4). Logs a WARNING for unknown values without personal data.
3. `choose_channel(appt, rule) -> "sms" | "email" | None | UNRESOLVED`. Channel rule (R7, R8, O3). Isolated and testable for both readings.
4. `signature_for(country) -> str`. R13.
5. `to_dublin(dt) -> datetime`. Conversion for display and quiet-hour checks.
6. `planned_send_times(starts_at, now) -> list[(slot, datetime)]`. Returns the 2h slot first, then the 48h slot. Applies the R5 clamp to `now`. Build this first to support R16.
7. `apply_quiet_hours(send_at, starts_at, now) -> datetime | None`. R10 and O5. Builds the target from the window-opening date, with `zoneinfo` handling the offset for that date.
8. `render_sms(name, starts_at, signature) -> str | None`. R3, R9, O2 ladder. Returns None when the message cannot fit.
9. `render_email(name, starts_at, signature) -> str`. Full name, no limit.
10. `contact_for_log(appt) -> str`. Masked contact for logs (see section 5, blocking item 3).
11. `reminders_for(appt, now, rule) -> list[dict]`. Per-appointment pipeline.
12. `plan_reminders(appointments, now) -> list[dict]`. Validates `now`, loops, sorts, logs one INFO line per returned reminder.

Per-appointment pipeline in `reminders_for`:
1. If not `is_active`, return nothing.
2. `require_aware(starts_at)`.
3. If `starts_at <= now`, return nothing.
4. `choose_channel`. If None, return nothing. If UNRESOLVED, WARNING with `appointment_id` only, then return nothing.
5. For each slot in `planned_send_times` (2h first, then 48h): apply quiet hours. Check `now <= send_at < starts_at`. Render text. If the SMS does not fit, log a fault with `appointment_id` and skip that reminder.
6. Return the reminders.

Processing order in `plan_reminders` (after `now` validation): gather reminders, sort by `(send_at, appointment_id, channel)` using a stable sort, log INFO per reminder, return.

Logging rules: never log email, text bodies, or input dicts. Exceptions name fields, not values.

## 4. Acceptance tests

Fixed reference: `NOW` = 2026-10-13 10:00 Europe/Dublin (IST, UTC+1), which is 09:00 UTC. Unless stated, the proposed O3 reading is used.

### A. Timing (R4, R5, R6, O1)

- A1 (R4). Given `starts_at` = NOW + 72h (2026-10-16 10:00 Dublin). When planned. Then the 48h reminder is 2026-10-14 09:00 UTC, and the 2h reminder is 2026-10-16 07:00 UTC.
- A2 (R5). Given `starts_at` = NOW + 30h. When planned. Then the 48h reminder is at exactly NOW. The 2h reminder is at NOW + 28h.
- A3 (R5 boundary). Given `starts_at` = NOW + 48h. When planned. Then the 48h reminder is at exactly NOW, and it is not in the past.
- A4 (R6, property). Given random `starts_at` values in [NOW - 1h, NOW + 10d]. When planned. Then every `send_at` is at or after NOW, and before `starts_at`.
- A5 (O1 skip). Given `starts_at` = NOW - 1 minute, or exactly NOW. When planned. Then no reminders are returned.
- A6 (O1, duplicate). Given `starts_at` = NOW + 90 minutes. When planned. Then two reminders are returned, both at NOW, with identical text. The duplicate is flagged.
- A7 (O1, near-duplicate). Given `starts_at` = NOW + 3h. When planned. Then the first is at NOW and the second is at NOW + 1h. The near-duplicate is flagged.

### B. Channel (R2, R7, R8, O3)

- B1 (R7). Given phone present, flag true, and email present. Under the literal reading, expect one SMS and no email. Under the proposed reading, expect one email and no SMS. Mark as conflicting with R7 under the proposed reading.
- B2. Given no phone and an email. Under both readings, expect one email.
- B3. Given no phone and no email. Under both readings, expect no reminder.
- B4 (O3). Given phone present and flag false. Under both readings, expect no reminder and one WARNING with no personal data.
- B5 (R8). Given phone present, flag true, and email present. Under any reading, expect at most one channel per reminder.
- B6 (R2). Given a record with `opt_out` true and `optout_sms_v2` false, plus a phone. Expect the same result as B4. Flipping `opt_out` must not change the result.
- B7. Given phone present and the flag missing. Expect UNRESOLVED handling, the same as B4.

### C. Status (R11, O4)

- C1 (R11). Given status "cancelled". When planned. Then no reminders.
- C2. Given status " Cancelled ". Expect no reminders (strip and casefold).
- C3 (recommendation, pending). Given status "canceled". Expect no reminders if the recommendation is accepted.
- C4 (O4). Given status "rescheduled". Expect the appointment to be treated as active, with a WARNING that contains no personal data.

### D. SMS length (R3, R9, O2)

- D1. Given a short name. Expect the SMS to be at most 160 characters and to contain the date, the HH:MM time, and the signature.
- D2 (O2 step 2). Given a long name that pushes the message over 160 characters. Expect the greeting to use the first initial plus the rest of the name, with date, time, and signature intact.
- D3 (O2 step 3). Given a name that still exceeds 160 characters at step 2. Expect the greeting to be "Hi," with date, time, and signature intact.
- D4 (O2 fault). Given a test-only template that exceeds 160 characters even with no name. Expect no SMS, a fault logged with `appointment_id` only, and no email substitute.
- D5. Given a name in decomposed (NFD) form. Expect the length to be measured after NFC normalization.
- D6. Given a long name and email as the channel. Expect the full name and no length limit.
- D7 (R13 length). Given country "PL" and a long name. Expect the Polish signature intact and the length rule applied as in D2 to D4.

### E. Quiet hours (R10, O5)

- E1. Given a send at 21:30 local on 13 Oct. Expect 20:00 on 13 Oct.
- E2. Given a send at 23:30 local on 13 Oct. Expect 20:00 on 13 Oct.
- E3. Given a send at 03:00 local on 14 Oct. Expect 20:00 on 13 Oct (previous day).
- E4. Given a send at 07:59 local on 14 Oct. Expect 20:00 on 13 Oct.
- E5. Given a send at 08:00 local on 14 Oct. Expect no change.
- E6. Given a send at 20:59 local on 13 Oct. Expect no change.
- E7 (O5 defer, flagged). Given `now` = 22:00 on 13 Oct and `starts_at` = 09:00 on 14 Oct. Then the 48h reminder is deferred to 08:00 on 14 Oct. The 2h reminder (nominal 07:00) is also deferred to 08:00. Both land at 08:00 as a duplicate, and the 2h reminder is only 1h before. This is flagged and is the PM default; the client must decide.
- E8 (O5 drop). Given `now` = 22:00 on 13 Oct and `starts_at` = 07:30 on 14 Oct. Then the 08:00 deferral is not before `starts_at`, so both reminders are dropped.
- E9 (O5 send at now). Given `now` = 20:30 on 13 Oct and `starts_at` = 06:00 on 14 Oct. The 2h point (04:00) is in the window, and its target (20:00) is before `now`. `now` is outside the window, so the reminder is sent at `now`. The 48h reminder is also at `now` (duplicate, flagged).

### F. DST and Dublin time (R14)

- F1 (October, clocks back). Given `starts_at` = 2026-10-26 09:00 Dublin (GMT, 09:00 UTC). Then the 2h point is 07:00 UTC on 26 Oct, which is in the window. The target is 20:00 on 25 Oct, which is already GMT, so expect 2026-10-25 20:00 UTC. A naive implementation that uses the offset at the send time would give 19:00 UTC and must fail.
- F2 (October, ambiguous hour). Given `starts_at` = 2026-10-25 02:30 UTC. The 2h point is 00:30 UTC, which is 01:30 local IST (first pass). Expect the target 20:00 on 24 Oct IST, which is 2026-10-24 19:00 UTC. Repeat with `starts_at` = 2026-10-25 03:30 UTC (second pass, 01:30 GMT). Expect the same target, 2026-10-24 19:00 UTC.
- F3 (March, clocks forward). Given `starts_at` = 2026-03-29 08:00 UTC (09:00 IST). The 2h point is 06:00 UTC, which is 07:00 IST after the change. The target is 20:00 on 28 Mar, which is still GMT, so expect 2026-03-28 20:00 UTC. A naive implementation that uses the offset at the send time would give 19:00 UTC and must fail.
- F4 (both changes). Property test over 2026-03-27 to 03-31 and 2026-10-23 to 10-27 at 15-minute steps. Expect every returned `send_at` to be aware and to convert to UTC without error.

### G. Signature (R13)

- G1. Given country "IE". Expect the text to end with "Siobhán Ní Dhuibhir".
- G2. Given country "PL". Expect the text to end with "Grzegorz Szczepański" and not the Irish signature.
- G3 (pending). Given country missing or None. Expect the Irish signature. Mark as pending confirmation.
- G4. Given country " pl ". Expect the Polish signature.

### H. Privacy and logging (R12, house rule)

- H1 (R12). Given an appointment with email "test-only@example.invalid" and an email channel. When planned. Then capture all log records at every level and all exception messages. The address must not appear anywhere.
- H2 (R12). Given a naive `starts_at`. Then ValueError is raised, and its message contains neither the email nor the repr of the input dict.
- H3. Given an appointment missing a required field. Then the error names the field only, not its value.
- H4 (house rule, conflicting). For each returned reminder, one INFO line with `appointment_id`, channel, and a masked contact. The email address is never logged. Expect this to change if the house rule is amended.
- H5. Text bodies are not logged.

### I. Ordering (R15)

- I1. Given reminders with equal `send_at`, different `appointment_id` values, and different channels. Expect the sort by `send_at`, then `appointment_id`, then `channel`.
- I2. Given the same input in a shuffled order. Expect identical output on every run.
- I3. Given a duplicate pair for one appointment with the same `send_at`. Expect the 48h reminder to appear before the 2h reminder, because of generation order.

### J. Legacy code (R17)

- J1. Given the module source. Expect only standard-library imports and no reference to the legacy folder. Then rename or remove the legacy folder and run all tests. They must still pass.
- J2. Expect no call to any function from the legacy SMS code.

### K. Input validation (R14, R1)

- K1. Given a naive `now`. Expect ValueError and no output.
- K2. Given a naive `starts_at`. Expect ValueError.
- K3. Given any valid input. Expect every returned reminder to have exactly the keys `appointment_id`, `channel`, `send_at`, `text`, and a timezone-aware `send_at`.

## 5. Blocking questions for the client

1. R7 and O3 (blocking). Customers with a phone and `optout_sms_v2` true: should they receive an SMS (literal R7), or no SMS and an email if they have an address (proposed)? The proposed reading contradicts R7's "do not send an email instead". Please confirm, and confirm that the flag's meaning is "opted out".
2. O3 (blocking for those customers). Customers with a phone and `optout_sms_v2` false: should they receive an SMS? Currently they get nothing, with a warning, until the client decides. Also: what should happen when the flag is missing?
3. R12 and house logging rule (blocking for logging). The house rule asks for the contact in each log line, but for email that is the address, which R12 forbids. Proposed: log `appointment_id`, channel, and a masked phone (last four digits), never the email. Please approve this, or tell us what the house rule should become.
4. O2 and R9 (blocking for SMS). Should the 160 limit be a character budget (default) or a single-segment guarantee? The second option would drop most texts. Accepting the character budget means most texts are two segments.
5. O2 (affects SMS delivery). If a text still exceeds 160 characters with no name, should we drop it, or fall back to email? The current design drops it and logs a fault.
6. O1 (duplicates). When the appointment is less than about 4 hours away, both reminders are sent at nearly the same time, and at `now` in the worst case. Keep both, send only the 2h reminder, or something else?
7. O5 (deferral). Is the deferral to 08:00 acceptable when it leaves less than 2 hours before the appointment? Should the 2h reminder be dropped instead?
8. O5 and R10 ("same day"). Confirm that a send at 00:00 to 07:59 on day D moves to 20:00 on D-1. Confirm that the window is [21:00, 08:00).
9. O4 and R11 (status values). What are all the real status values? Should "canceled" also be excluded?
10. R3 (date format). Is `26 Oct 2026` acceptable? Should the weekday be included? Email has no subject field in the spec; should one be added?
11. R13 (country). What are the possible `country` values, and what should happen for a missing country?
12. SMS opt-out wording. The spec has no opt-out text in SMS. Does the client need one (for example, a STOP instruction)? Adding it would count against the 160 budget.