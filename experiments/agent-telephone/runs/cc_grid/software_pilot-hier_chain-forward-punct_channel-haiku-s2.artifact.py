MODULE DESIGN AND DATA FLOW

Entry point: plan_reminders(appointments, now) returns list[dict]. Each dict has exactly the keys appointment_id, channel ("sms" or "email"), send_at (timezone-aware, UTC), and text. The module uses only datetime, zoneinfo, and logging.

Validation: now must be aware, or raise ValueError. Each starts_at must be aware, or raise ValueError naming only the appointment_id and field. A missing id is an error. Missing keys are read as None. Invalid input raises for the whole batch (see open question 9).

Per-appointment flow:
1. Skip if status (str(x or "").strip().lower()) is "cancelled" or "canceled".
2. Skip if starts_at in UTC is at or before now.
3. Choose one channel. If phone is non-empty after strip, the channel is "sms" only when optout_sms_v2 is exactly the bool False; otherwise there are no reminders and no email. Else, if email is usable, the channel is "email". Else there are no reminders. The old opt_out field is ignored.
4. Compute the two raw send times in UTC: starts_utc minus 48h (index 1) and starts_utc minus 2h (index 2). Quiet-window adjustment: if the local Dublin time is 21:00 or later, or before 08:00, move to 20:00 Europe/Dublin on the local date of that window (same date if 21:00 or later, previous date if before 08:00). All subtraction happens in UTC.
   - If t < now: index 1 becomes allowed_at_or_after(now) (now, or the next 08:00 Dublin if now is in the quiet window). Index 2 is omitted.
   - If t >= starts_utc, omit.
   - If index 1 and index 2 resolve to the same send_at, keep only index 2.
5. Build text (see the text rules below).
6. Sort by (send_at UTC, str(appointment_id), index), then drop index.
7. Logging: DEBUG per appointment (id, channel, ISO send_at, skip reason code). One INFO summary count.

Text rules: body is "Hi {name}, your Brennan Opticians appointment is on {date} at {time}. {signature}". Nameless variant drops the name slot. Date is DD/MM/YYYY and time is HH:MM, both in Europe/Dublin. The signature is "Siobhán Ní Dhuibhir", or "Grzegorz Szczepański" when country == "PL" exactly. The name is sanitised (control characters removed, whitespace collapsed, ends stripped). Email has no length limit. For SMS, if the text is 160 code points or fewer, it is kept as is. Otherwise the name is truncated to fit, with no ellipsis. If the name is empty, the nameless variant is used. Date, time, and signature are never shortened. If the nameless variant is still over 160, raise a ValueError at import or in tests.

Technical notes that need a decision:

(a) Logging conflict. The house rule requires one INFO line per planned reminder saying who it goes to and how (channel and contact). The design forbids logging contact details, and the DPC audit explicitly objects to logging customer contact data. Both cannot be met. The recommended resolution is one INFO line per reminder with appointment_id and channel only, with no contact value. This needs sign-off from the client and the team lead before implementation.

(b) The SMS limit is not what the brief assumes. "Siobhán" and "Grzegorz Szczepański" contain characters outside GSM-7, so the message is UCS-2. A single UCS-2 SMS holds 70 characters and a concatenated segment holds 67. A 160-character cap is not a real carrier limit for these messages. Enforcing 160 as written means a 160-character message may be sent as two or three segments.

(c) The SMS budget wording is ambiguous. The template with an empty name slot reads "Hi , your ...", which has a stray space. The budget must be defined precisely as the length of the nameless variant, or the rule should be restated so the output is unambiguous.

(d) The brief says the 00:00 to 07:59 window moves to "the 20:00 just before it". That is the previous evening, which matches the design. The architect's note calls the brief's phrase "same local day" and says it would move forward. That is a misreading, and the design rule is correct as written.

(e) Duplicate appointment ids are processed twice in this design. Both reminders would carry the same appointment_id, so the dashboard may show duplicates. This needs a decision (see question 13).

EDGE CASES WITH CHOSEN BEHAVIOUR

1. The 48h point has passed but the appointment is still ahead. One reminder is sent at now (or the next 08:00 Dublin if now is in the quiet window, provided that is before the start). The 2h reminder is kept if it is still ahead.
2. The 2h point has passed after quiet adjustment. Omit it.
3. Now is inside the quiet window and the first reminder must move to now. Defer to the next 08:00 Dublin if that is before the start; otherwise omit.
4. The 2h point is in the quiet window and its 20:00 anchor is already past. Omit. Do not move it forward.
5. The appointment starts within 2 hours of now. Send one first reminder at now (index 1 clamp). No second reminder.
6. starts_at equals now exactly: no reminders. now equals a reminder time exactly: that reminder is not past and is sent at now.
7. DST: Europe/Dublin is UTC+0 until 2026-03-29 and UTC+1 until 2026-10-25. Test a reminder that spans 2026-10-25 and quiet-window moves on both sides of that date.
8. Times from 00:00 to 07:59 local move to 20:00 of the previous local day.
9. Phone present but opted out: no reminders at all, no email.
10. optout_sms_v2 missing, None, the string "false", or any non-bool: treated as opted out.
11. Duplicate appointment ids: both are processed (open question 13).
12. Empty input list returns [].
13. SMS overflow: the name is shortened; date and time are always kept.

OPEN QUESTIONS FOR THE CLIENT

1. The brief says "text if optout_sms_v2 is true", which contradicts its name. The design uses SMS only when the flag is false. Confirm.
2. Confirm that customers with a phone who have opted out get no email at all.
3. Confirm the 20:00 previous-evening rule for 00:00 to 07:59 send times. The brief supports this.
4. If the first reminder falls in quiet hours and must move to now, defer to 08:00 (design) or drop it?
5. Confirm the date format DD/MM/YYYY.
6. SMS length: enforce 160 code points as written, or move to real segment limits (70 characters per UCS-2 segment)? See technical note (b).
7. Name truncation: mid-word cut, first name only, or initial?
8. Phone validation: non-empty check only, or E.164?
9. Invalid input (naive datetime, missing id): reject the whole batch (design) or skip only that appointment?
10. "PL" matching: case-sensitive and unstripped (design) or case-insensitive?
11. Status: "canceled" is also treated as cancelled. Other statuses such as no-show are not excluded. Confirm.
12. send_at is returned in UTC. Confirm this works for Pádraig's dashboard.
13. Duplicate appointment ids: process both (design) or reject?
14. Confirm that a single catch-up reminder at now, for an appointment already inside its 2h window, is acceptable.
15. Confirm the DPC audit scope for names, phones, and emails in logs, and resolve the logging conflict in technical note (a).

ORDERED IMPLEMENTATION PLAN WITH ACCEPTANCE CRITERIA

Step 1. Input validation and channel selection.
- A naive now raises ValueError.
- A naive starts_at raises ValueError whose message contains the appointment_id and field name, and contains no email, name, or phone value.
- Opted-out customers, and customers whose flag is missing, with a phone get zero reminders.
- A customer with no phone and a usable email gets channel "email".
- No appointment ever gets both channels.

Step 2. Quiet-hour function (zoneinfo).
- 2026-10-20 07:00 local maps to 2026-10-19 20:00 local.
- 21:00 local is in the window and maps to 20:00 local on the same day, which is earlier.
- 08:00 local is allowed unchanged.
- Behaviour is correct on both sides of 2026-10-25 and 2026-03-29.

Step 3. Schedule computation.
- Start 2026-10-20 10:00 local: first reminder 2026-10-18 10:00 local, second 2026-10-20 08:00 local.
- Start 2026-10-20 09:00 local: second reminder moves to 2026-10-19 20:00 local.
- now 2026-10-18 12:00 local with start 2026-10-20 10:00 local: first reminder at now.
- now inside the quiet window: first reminder moves to 08:00 the next morning.
- Every send_at is at or after now and before starts_at.

Step 4. Status and started-appointment filters.
- Cancelled or canceled produces nothing.
- starts_at at or before now produces nothing.

Step 5. Text building and SMS fitting.
- A 60-character name still fits in an SMS.
- A 300-character name is truncated so the message is at most 160 code points and still contains the exact date and HH:MM. (Subject to the decision in technical note (b).)
- country "PL" gives Grzegorz Szczepański.
- Any other country gives Siobhán Ní Dhuibhir.
- Email text contains the full name.

Step 6. Ordering and output shape.
- Each output dict has exactly four keys.
- The list is sorted by send_at ascending, then str(appointment_id), then index.
- send_at is timezone-aware.

Step 7. Logging audit.
- A test captures all records at DEBUG level and asserts that no email address, name, phone number, or body text appears in any log record or exception message.
- The test also checks the INFO line format agreed under technical note (a).