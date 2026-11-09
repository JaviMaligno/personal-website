# Product spec: Brennan Opticians appointment reminder module

## Hard requirement: customer email must never be logged (read first)

The customer's email address must never appear in any log line, error message, exception message, repr, or debug output. This is a Data Protection Commission audit requirement after the March finding. The same applies to customer_name and phone: log only appointment_id, channel, counts and reason codes. Never include the appointment dict or any repr of it in exceptions or logs.

**Conflict with the house logging rule:** the house rule asks for each INFO line to say "who it goes to and how (channel and contact)". The contact is the email or phone, which the DPC requirement forbids. This spec follows the DPC requirement. The recipient is identified by appointment_id plus channel. The tech lead must confirm this (open question 14).

## 1. Scope

**In scope:** one Python 3.12 module, standard library only, with entry point `plan_reminders(appointments, now)`. It returns the reminders to send.

**Input:** a list of appointment dicts with keys id, customer_name, email, phone, country, status, starts_at (timezone-aware datetime) and optout_sms_v2 (bool). `now` is a timezone-aware datetime.

**Output:** a list of dicts with exactly four keys: appointment_id, channel ("sms" or "email"), send_at (timezone-aware datetime), text (str). Sorted ascending by send_at, then appointment_id ascending, then the 48h reminder before the 2h reminder.

**Out of scope:** actually sending, scheduling, storage, retries, delivery receipts, reading the legacy SMS folder (being deleted by Tomasz), the old `opt_out` field (ignored), any clock read, I/O or network access.

## 2. Rules

### 2.1 Entry and purity
- The function is pure. It uses `now` and never reads the clock. It does no I/O and no network access, and it does not mutate its input.
- Naive `now` or naive `starts_at` raises ValueError. The message contains no customer data.
- Duplicate appointment ids raise ValueError without customer data (default, open question 10).
- A missing field or wrong-typed field raises ValueError that names the field only (open question 17).

### 2.2 Status
- Exclude the appointment if `status.strip().casefold() == "cancelled"`. Other status values are not excluded (open question 7).

### 2.3 Reminder points
- Point A = starts_at minus 48 hours. Point B = starts_at minus 2 hours. Arithmetic is absolute elapsed time (open question 3).
- If starts_at <= now, plan nothing.
- Point A:
  - If A > now, send_at = A.
  - If A <= now < starts_at, the candidate is now.
- Point B:
  - If B > now, send_at = B.
  - If B <= now < starts_at, send at now only if no other reminder for this appointment is already planned at now (after quiet-hours handling). Otherwise drop it (open question 6).
- Every send_at must be less than starts_at.

### 2.4 Quiet hours
- The quiet window is Europe/Dublin local time, 21:00 inclusive to 08:00 exclusive. It applies to both channels.
- A candidate send_at inside the window moves to the most recent 20:00 Europe/Dublin that is strictly before it. For 00:00 to 07:59 this is the previous evening. For 21:00 to 23:59 this is the same day (open question 11). A send at 07:30 moves to the previous 20:00 (open question 1).
- Deferral is applied before the never-in-the-past clamp.
- After deferral, if send_at < now:
  - If now is in allowed hours, send_at = now.
  - If now is in quiet hours, send_at = the next 08:00 Europe/Dublin, but only if that is before starts_at. Otherwise drop the reminder (open question 2).
- After clamping, the final send_at is checked again. It must not be in the quiet window, must be >= now, and must be < starts_at.

### 2.5 Channel

| Condition | Result |
|---|---|
| phone non-empty after strip, optout_sms_v2 false | sms |
| optout_sms_v2 true, email non-empty after strip | email |
| phone empty, optout_sms_v2 false, email non-empty | email (open question 4) |
| optout_sms_v2 true, email empty | no reminder (open question 5) |
| phone empty and email empty | no reminder |

- Never produce both an SMS and an email for the same reminder point.
- An SMS that fails the length rule (2.7) falls back to email if an email exists. Otherwise there is no reminder.

### 2.6 Text
- Each text states the appointment date as DD/MM/YYYY (open question 8) and the appointment start time as HH:MM. Both are Europe/Dublin local time, not the send time.
- Each text ends with the signature. The default is "Siobhán Ní Dhuibhir". If `country.strip().casefold() == "pl"`, the signature is "Grzegorz Szczepański".
- Names and signatures are preserved exactly as supplied. No transliteration and no Unicode normalisation.
- The template lives in one constant. Proposed template:
  `Hi {name}, your Brennan Opticians appointment is on {date} at {time}. {signature}`
- Worked example: name "Aoife Murphy", appointment 15/10/2026 at 14:30 Dublin time, default signature. The text is `Hi Aoife Murphy, your Brennan Opticians appointment is on 15/10/2026 at 14:30. Siobhán Ní Dhuibhir` (98 code points).
- Email text uses the same template with the full, untruncated name. Email has no length limit.

### 2.7 SMS length
- SMS text must satisfy `len(text) <= 160` (code points), per the brief. See open question 9 on encoding.
- If the text is too long, truncate customer_name only, by code points. The date, HH:MM, template words and signature are always kept.
- If the name is truncated to nothing and the text is still over 160, do not emit the SMS. Fall back to email if an email exists. Otherwise emit nothing.

## 3. Open questions (each with a proposed default)

1. **07:30 edge:** a send at 07:30 is inside the window and moves to the previous 20:00. Default: yes, literal rule.
2. **Deferred send lands before now:** set send_at = now if now is in allowed hours. If now is in quiet hours, use the next 08:00 Dublin if it is before starts_at, otherwise drop. Default: as stated.
3. **Anchor basis:** should 48h and 2h anchors be absolute elapsed time or calendar-based in Europe/Dublin? Default: absolute elapsed time.
4. **Phone absent, not opted out:** default is email if an email exists. The brief does not say.
5. **Opted out, no email:** default is no reminder.
6. **Late 2h reminder:** default is send at now only if no other reminder for that appointment is at now, otherwise drop.
7. **Status values beyond exact "cancelled":** default is case-insensitive, stripped, exact match only. Values such as "CANCELLED" are matched. Values such as "cancelled_by_customer" are not excluded.
8. **Date format:** default DD/MM/YYYY.
9. **SMS encoding (discrepancy):** "Siobhán" and "Ní" contain characters outside GSM-7, so the message is probably UCS-2. Then the real limit is 70 characters per segment, not 160. Default: keep 160 code points as the spec limit, and the tech lead must decide. Note that the signature alone forces UCS-2.
10. **Duplicate appointment ids:** default is ValueError without customer data.
11. **Quiet-hours target for 21:00 to 23:59:** the brief says "the 20:00 just before it", which is the same day. The architect's wording "previous calendar evening" is only correct for 00:00 to 07:59. Default: most recent 20:00 strictly before the send time.
12. **Name truncation:** default is no ellipsis, trailing whitespace removed. The cut must not leave a dangling combining mark. Default: drop any combining mark left at the cut.
13. **Cut-order wording:** the PM said the 2h reminder should be "listed first in the cut order", which is ambiguous. Default reading is in section 4.
14. **Logging conflict:** the house rule asks for "contact" in logs, which the DPC requirement forbids. Default: log appointment_id and channel only. The tech lead must confirm.
15. **Time zone data:** `zoneinfo` needs system tzdata. On Windows it needs the tzdata package, which is not stdlib. Default: rely on the system tz database, and fail at import if it is missing. Confirm the deploy host has it.
16. **Signature encoding:** see open question 9. Same discrepancy.
17. **Missing or wrong-typed fields:** default is ValueError naming the field only, never the value.

## 4. Cut order

The 2-hour reminder is the highest-priority item. It is kept last to cut. The 48-hour reminder is cut first. The PM's wording needs confirmation (open question 13).

Cut order, first cut to last:
1. Quiet-hours edge refinements beyond the basic move-and-clamp, such as the next-08:00 fallback. If cut, a deferred send that lands before now is dropped.
2. The 48-hour reminder.
3. The 2-hour reminder (last to cut).

**Must keep, regardless of cuts:** channel rules, status exclusion, no email (or name or phone) in logs, sort order, signature, date and HH:MM in text.

## 5. Acceptance criteria

1. Output is a list. Each element is a dict with exactly the keys appointment_id, channel, send_at, text.
2. channel is "sms" or "email". send_at is timezone-aware. text is str.
3. Output is sorted by send_at ascending. Equal send_at is ordered by appointment_id ascending. Equal id and send_at puts the 48h reminder before the 2h reminder.
4. With now = starts_at − 72h, phone present and not opted out, output contains a reminder at starts_at − 48h and one at starts_at − 2h.
5. With now between A and starts_at (e.g., starts_at − 30h), the first reminder has send_at == now.
6. With now == A exactly, the first reminder has send_at == A.
7. With now between B and starts_at, and no other reminder planned at now, the 2h reminder has send_at == now.
8. With now between B and starts_at, and the 48h reminder also planned at now, exactly one reminder is returned.
9. If starts_at <= now, the result is empty.
10. For every input in a test grid, every send_at is >= now and < starts_at.
11. Quiet-hours moves (Europe/Dublin, October 2026, IST): 20:59:59 is unchanged. 21:00:00 moves to 20:00 the same day. 23:59 moves to 20:00 the same day. 07:59:59 moves to 20:00 the previous day. 08:00:00 is unchanged. 07:30 moves to 20:00 the previous day.
12. DST: quiet-hour moves across 2026-03-29 and 2026-10-25 use the Dublin local clock. Anchor arithmetic is absolute.
13. Deferral clamp: deferred send before now with now in allowed hours gives send_at == now.
14. Deferred send before now with now in quiet hours and next 08:00 before starts_at gives send_at == next 08:00 Dublin.
15. Same as 14, but next 08:00 is at or after starts_at: the reminder is dropped.
16. No final send_at falls in the quiet window, for any input in the test grid.
17. phone non-empty and optout_sms_v2 false gives channel "sms", whether or not email is present.
18. phone of only whitespace is treated as absent.
19. optout_sms_v2 true with email present gives channel "email". No SMS is produced even if phone is present.
20. phone absent, optout false, email present gives channel "email".
21. phone absent and email absent gives no reminder.
22. optout true and email absent gives no reminder.
23. For every input, at most one reminder exists per reminder point (no SMS plus email duplication).
24. status "cancelled", " CANCELLED ", and "Cancelled" all produce no reminders. status "cancelled_by_customer" is not excluded.
25. Every SMS satisfies len(text) <= 160.
26. A long name is truncated. The truncated name is a prefix of the original. The text still contains the DD/MM/YYYY date, the HH:MM time, and the signature.
27. If the name is truncated to nothing and the text is still over 160, with an email present, the output is an email with the full name in the text and no SMS.
28. As in 27, but with no email: no output for that reminder.
29. Text states the date and HH:MM in Dublin time. An appointment at 13:30 UTC on 15/10/2026 shows "15/10/2026" and "14:30".
30. Default signature is "Siobhán Ní Dhuibhir". country " pl " (any case) gives "Grzegorz Szczepański". Any other country gives the default.
31. Accented names are preserved: the name in the text is identical to the input, including any decomposed form.
32. An appointment with opt_out true, optout_sms_v2 false and a phone gives channel "sms". The opt_out field is ignored.
33. Naive `now` raises ValueError. Naive `starts_at` raises ValueError. Neither message contains the email, name or phone.
34. Duplicate appointment ids raise ValueError, and the message contains no customer data.
35. A missing or wrong-typed field raises ValueError that names the field and does not include the value.
36. Privacy test: use a sentinel email string, customer name and phone. Run valid, cancelled, naive-datetime, missing-field and duplicate-id inputs with logging captured at DEBUG and above. Assert the sentinel email (and name and phone) does not appear in any log record, exception str, repr, or formatted traceback.
37. Logging: exactly one INFO record per planned reminder, containing appointment_id and channel. No other INFO records.
38. No I/O, network or clock: with socket, open, datetime.now and time.time patched to raise, the function still returns correct output.
39. Purity: after the call, the input list and dicts are unchanged.
40. Determinism: the same inputs always give the same output.