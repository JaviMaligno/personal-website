SPEC: Brennan Opticians appointment reminders
Module: plan_reminders(appointments, now)
Status: draft for client review. Items marked [OPEN Q#] depend on an unresolved question and must not be implemented by assumption.

1. PURPOSE
Given a list of appointment records and the current time, return the reminder messages to send. The function sends nothing itself and has no side effects other than logging (see section 9).

2. ENTRY POINT AND RETURN SHAPE
- Signature: plan_reminders(appointments, now). Both arguments are required.
- Returns a list of dicts. Each dict has exactly these keys: appointment_id, channel, send_at, text.
- channel is one of "sms" or "email".
- send_at is a timezone-aware datetime. Whether it is expressed in UTC or Europe/Dublin is [OPEN Q15].
- text is a string.
- The list is sorted ascending by send_at (see section 10 for ties).
- An empty input, or input where no reminders apply, returns an empty list.
- Implementation constraints: Python 3.12, standard library only. Use zoneinfo for Europe/Dublin. Ignore the legacy folder entirely.

3. INPUT SHAPE
Each appointment is a dict with these fields:
- id
- customer_name
- email
- phone (may be missing or empty)
- country
- status
- starts_at (timezone-aware datetime)
- optout_sms_v2 (boolean)
The field optout_sms_v2 is the only opt-out flag. The legacy opt_out field must not be read.
All datetimes, including now and starts_at, are timezone-aware. Behaviour for naive datetimes or other invalid input is [OPEN Q10].

4. SCHEDULING RULES
4.1 Reminder points. For each eligible appointment, the first reminder is due at starts_at minus 48 hours, and the second at starts_at minus 2 hours.
4.2 Late first reminder. If the 48-hour point is before now, the first reminder is sent at now instead.
4.3 Late second reminder. If the 2-hour point is before now, the behaviour is [OPEN Q3]. Options: (a) drop the reminder, (b) send it at now.
4.4 Never in the past. No returned send_at may be earlier than now. How this interacts with the quiet-window shift is [OPEN Q4].
4.5 Reminder count. An eligible appointment produces up to two reminders, one per reminder point. Zero reminders are produced if both points have passed and the late-second-reminder rule (4.3) drops it.
Acceptance criteria:
- AC 4.1a: starts_at = 2026-10-20 10:00 Dublin, now = 2026-10-01 12:00 UTC. Reminder 1 send_at = 2026-10-18 10:00 Dublin (in quiet window rules, see section 6, if applicable). Reminder 2 send_at = 2026-10-20 08:00 Dublin.
- AC 4.2a: starts_at is 30 hours after now. Reminder 1 send_at equals now.
- AC 4.4a: For every returned reminder, send_at >= now.

5. CHANNEL RULES
5.1 One channel per reminder. Each reminder has exactly one channel. An SMS and an email must never both be produced for the same reminder point.
5.2 SMS eligibility. A reminder goes by SMS only if the customer has a phone number and the opt-out condition is met. The direction of the optout_sms_v2 condition is [OPEN Q1]. Options:
   (a) optout_sms_v2 true means the customer has opted out of SMS, so no SMS is sent.
   (b) optout_sms_v2 true means the customer has opted in, so SMS is sent.
5.3 Email fallback. When there is no phone number, whether an email is sent or no reminder is sent is [OPEN Q2]. The brief says "Don't email them instead", which is not clear enough to implement.
5.4 Email when SMS is not used. Whether email is ever used when SMS is ineligible for a reason other than a missing phone number is [OPEN Q2] and [OPEN Q1].
Acceptance criteria:
- AC 5.1a: For any input, no two returned dicts share both appointment_id and send_at.
- AC 5.2a: [PENDING Q1] Output for each combination of phone present or absent and optout_sms_v2 true or false is verified against the chosen option.
- AC 5.3a: [PENDING Q2] Output for a phone-less appointment matches the chosen option.

6. QUIET WINDOW
6.1 No send_at may fall between 21:00 and 08:00 Europe/Dublin.
6.2 A time in that window is moved back to 20:00 of the previous evening (Europe/Dublin).
6.3 Applies to both the 48-hour and 2-hour reminders. The brief describes the rule for "anything", and the client has not yet confirmed it for both reminder types [OPEN Q5].
6.4 Whether the 08:00 boundary itself is inside or outside the window is not stated [OPEN Q10].
6.5 If a shifted time falls before now, the outcome is [OPEN Q4].
Acceptance criteria:
- AC 6.2a: A reminder computed for 23:30 Dublin on a given day returns send_at 20:00 Dublin on that same day.
- AC 6.2b: A reminder computed for 07:15 Dublin returns send_at 20:00 Dublin on the previous day.
- AC 6.1a: No returned send_at has a Dublin local time in the window 21:00 to 08:00, subject to the 08:00 boundary in [OPEN Q10].
- AC 6.5a: [PENDING Q4] A shifted time earlier than now is handled as the client decides.

7. CANCELLED AND OTHER STATUSES
7.1 Appointments with status "cancelled" produce no reminders.
7.2 Whether other statuses (for example completed or no-show) produce reminders is [OPEN Q7]. Until decided, only the cancelled exclusion is specified.
Acceptance criteria:
- AC 7.1a: An appointment with status "cancelled" produces zero returned reminders regardless of other fields.

8. SMS TEXT AND LENGTH
8.1 Every text includes the appointment date and the appointment time as HH:MM, in Europe/Dublin local time. The exact date format is [OPEN Q11].
8.2 Every text ends with a signature (section 8.5).
8.3 An SMS must be at most 160 characters.
8.4 If an SMS is too long, the customer's name is shortened. The date and time are never removed or shortened.
8.5 Signature: "Siobhán Ní Dhuibhir" by default. If country is PL, the signature is "Grzegorz Szczepański" instead. The country code format and whether any other country uses Siobhán's signature is [OPEN Q8].
8.6 Whether the 160-character limit includes the signature is [OPEN Q6]. If the message is still too long after the name is shortened to nothing, the behaviour is also [OPEN Q6].
8.7 Email text and subject are not specified [OPEN Q9]. Whether the same text and signature apply to email is also [OPEN Q9].
Acceptance criteria:
- AC 8.1a: Each returned text contains the appointment date and the appointment time as HH:MM Dublin local time.
- AC 8.3a: Each SMS text has length <= 160, subject to [OPEN Q6].
- AC 8.4a: For a long customer name, the truncated text still contains the full date and HH:MM.
- AC 8.5a: Country PL yields the Grzegorz Szczepański signature. Other countries yield Siobhán Ní Dhuibhir, subject to [OPEN Q8].

9. LOGGING AND PRIVACY
9.1 Log exactly one INFO line per planned reminder, using the logging module. Each line states the recipient and the channel, so support can trace deliveries.
9.2 Customer email addresses must never appear in any log line, print output, return value other than the email text (if email text is not applicable, see section 8.7), or error message.
9.3 For email-channel reminders the log line must still identify the recipient without the email address. The identifier to log (for example the appointment id or a masked form) is [OPEN Q12]. The house rule (log the contact) and the tech lead rule (never log emails) conflict for this channel and must be resolved by the client and tech lead.
9.4 For SMS-channel reminders the contact may be the phone number. Whether phone numbers may be logged in full is [OPEN Q12].
Acceptance criteria:
- AC 9.2a: Running the function with an email address in the input produces no log record or printed output containing that address.
- AC 9.1a: The number of INFO records equals the number of returned reminders.

10. SORTING, TIES AND INVALID INPUT
10.1 Results are sorted ascending by send_at.
10.2 The order of reminders with identical send_at is [OPEN Q10].
10.3 Invalid or missing input (naive datetimes, missing fields, duplicate ids, appointments already started, non-boolean optout_sms_v2) is handled as [OPEN Q10] specifies. No default behaviour is set.
Acceptance criteria:
- AC 10.1a: For any output, send_at values are non-decreasing.
- AC 10.2a: [PENDING Q10] Tie ordering matches the chosen rule.

11. PRIORITY
The brief states that if scope must be cut, the 2-hour reminder matters more than the 48-hour reminder. Section 4 must be implemented so that the 2-hour reminder is preserved if anything is cut.

12. OPEN QUESTIONS FOR CLIENT
Q1. The brief says "Text them if they have a phone number, if optout_sms_v2 is true." Does optout_sms_v2 true mean the customer has opted out (suppress texts) or has opted in (allow texts)? The field name suggests one reading and the sentence suggests the other. Options: (a) true means opted out, (b) true means opted in.
Q2. When there is no phone number, is an email sent, or is no reminder sent at all? "Don't email them instead" is ambiguous.
Q3. If the 2-hour point has already passed at run time, is that reminder dropped, or sent at now? Options: (a) drop, (b) send at now.
Q4. If the 48-hour point has passed and the first reminder goes at now, what happens if the quiet-window shift moves a send before now? Options: (a) drop, (b) send at now, (c) other.
Q5. Confirm that the quiet-window shift (21:00-08:00 moved to 20:00 of the previous evening) applies to both the 48-hour and 2-hour reminders.
Q6. Does the 160-character SMS limit include the signature? If the message is still too long after the name is shortened to nothing, what happens? Options: (a) truncate the signature, (b) send anyway, (c) do not send, (d) other.
Q7. Which status values exist besides "cancelled", and do other statuses (for example completed or no-show) receive reminders?
Q8. Country code format: "PL", "pl", or "Poland"? Is any country other than PL signed by Siobhán, or is the default signature for all non-PL countries?
Q9. Email subject and text are not specified. Does the same text apply to email? Is the signature the same?
Q10. Invalid or missing input handling (naive datetimes, missing fields, duplicate ids, appointments already started, non-boolean optout_sms_v2). Also the order of reminders with identical send_at, and whether the 08:00 boundary is inside or outside the quiet window.
Q11. Exact date format in the text (for example DD/MM/YYYY or a spelled-out month) and the time format (HH:MM, Dublin local).
Q12. Logging identifiers: what may be logged for email-channel reminders given the ban on logging customer emails (appointment id, masked address, or other)? May phone numbers be logged in full for SMS-channel reminders?
Q13. Are the returned send_at values to be expressed in UTC or Europe/Dublin?
Q14. (Reserved for further client input.)
Q15. Confirm whether the returned send_at timezone is UTC or Europe/Dublin (see Q13 and section 2).