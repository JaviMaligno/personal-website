(a) FUNCTIONAL SPEC

Verdict on the proposed algorithm: confirmed, with the corrections below.

Corrections found:
1. Case G is wrong. 09:00 IST on 30 Mar is 08:00Z, not 07:00Z. Slot 1 nominal is 28 Mar 08:00Z, which is 08:00 GMT (not quiet), so slot 1 is 2026-03-28 08:00Z, not 27 Mar 20:00Z. Slot 2 2026-03-29 19:00Z is correct.
2. Length budget: the PL signature is one code point longer than the Siobhan signature, so the full-name budget is 64 code points for the Siobhan signature and 63 for the PL signature, not "about 64" for both.
3. Logging conflict: the house rule asks for one INFO line per planned reminder naming the contact, but the privacy rule forbids logging any contact. This must be resolved before implementation (see open question 12).
4. Under a 70-code-point UCS-2 limit, the no-name form (91 or 92 code points) does not fit. Changing the constant alone is not enough; the template or a multipart policy must change too.
5. Missing-key handling was not specified; it is defined in (b).
6. starts_at equal to now means "started" (no reminders), while a reminder whose send_at equals now is allowed ("not passed"). These are different rules and both are kept.

Constants: SLOT1_OFFSET = 48 hours, SLOT2_OFFSET = 2 hours, DUBLIN = ZoneInfo("Europe/Dublin"), SMS_MAX_CHARS = 160. All instants are converted to UTC (datetime.timezone.utc) for arithmetic. Output send_at values are UTC-aware.

Quiet test: take the instant, convert with astimezone(DUBLIN), and read the wall-clock time. Quiet means wall time >= 21:00 or wall time < 08:00. Exactly 21:00:00 is quiet; exactly 08:00:00 is not.

quiet_move(t):
    local = t.astimezone(DUBLIN)
    if local.time() >= 21:00: return 20:00 on local.date(), converted to UTC
    if local.time() < 08:00: return 20:00 on (local.date() minus 1 day), converted to UTC
    return t

earliest_permitted(now):
    local = now.astimezone(DUBLIN)
    if local.time() >= 21:00: return 08:00 on (local.date() plus 1 day), converted to UTC
    if local.time() < 08:00: return 08:00 on local.date(), converted to UTC
    return now

Both 20:00 and 08:00 targets are built as wall-clock times in DUBLIN with fold=0. They never fall in a DST gap or overlap, so this is safe. Duplicate wall times on 25 Oct (01:00 to 01:59 occurs twice) are both in the quiet window, and because all instants are stored as UTC the choice of occurrence does not affect the result.

Algorithm (per validated appointment, in input order):

    start = starts_at in UTC
    if normalized status == "cancelled": drop all, reason CANCELLED; continue
    if start <= now: drop all, reason STARTED; continue
    channel = choose_channel(a)          # SMS, EMAIL, or none
    if channel is none: drop all, reason NO_CHANNEL; continue

    # slot 1
    t1 = start - 48h
    if t1 < now: t1 = now
    t1 = quiet_move(t1)
    if t1 < now: t1 = earliest_permitted(now)
    s1 = t1

    # slot 2
    t2 = start - 2h
    s2 = none
    if t2 < now: reason SLOT2_PAST
    else:
        t2 = quiet_move(t2)
        if t2 < now: reason SLOT2_PAST (no clamp)
        else: s2 = t2

    if s1 >= start: drop slot 1, reason SLOT1_AFTER_START
    if s2 is set and s2 >= start: drop slot 2, reason SLOT2_AFTER_START (cannot occur, kept as a guard)
    if s1 and s2 both survive and s1 >= s2: drop slot 1, reason SLOT1_COLLIDES_SLOT2

Channel rule: if the stripped phone is a non-empty string and optout_sms_v2 is False (identity check), use SMS. Otherwise, if the stripped email is a non-empty string, use EMAIL. Otherwise, no reminders (reason NO_CHANNEL). Missing or None optout is treated as opted out for SMS. The old opt_out field is never read.

Cancelled rule: status None counts as not cancelled. Otherwise status.strip().casefold() == "cancelled". The spelling "canceled" does not match (open question 6).

Output: one entry per surviving slot. Sort by (send_at in UTC, str(appointment_id), channel, slot index). Slot index is 1 or 2. Channel strings compare "email" before "sms".

Precedence: cancelled, then started, then channel, then slot 1 (with clamp), then slot 2 (no clamp), then the after-start guards, then the tiebreak.

Logging (see section (b) and open question 12): use logging.getLogger(__name__).
- One INFO summary per call: appointments received, reminders produced, and counts of drops per reason code.
- DEBUG per appointment: the appointment id and reason code only.
- Never log or include the email, phone, customer name, country, or message text.

Runtime: target Python 3.12; the code also works on 3.9 or newer. Only datetime, zoneinfo, unicodedata, and logging are listed. Validation also needs collections.abc.Mapping, which is standard library but not on the list; this should be noted for sign-off.

tzdata: zoneinfo reads the system IANA database. Windows has none, and minimal Linux containers may lack it. The PyPI package tzdata would be an extra dependency and needs client approval. Do not assume it is present. If it is missing, ZoneInfo raises ZoneInfoNotFoundError, which should surface as a clear startup failure, not a silent wrong time.

(b) DATA CONTRACT

Input: plan_reminders(appointments, now).
- appointments must be a list (tuples are rejected). Each element must be a Mapping.
- id: non-empty string after stripping, or int that is not bool. Duplicates are rejected using str(id) as the key, so that the sort is unambiguous. The original value is preserved in output.
- customer_name: string, non-empty after stripping. Required even if no reminder is sent.
- email, phone, country: None or string. A missing key is treated as None. None or blank after stripping counts as absent for email and phone.
- status: None or string. Missing is treated as None.
- optout_sms_v2: missing, None, True, or False. Any other type is an error (so 0 and 1 are rejected).
- starts_at: instance of datetime.datetime (a date is rejected), with utcoffset() not None.
- now: datetime.datetime with utcoffset() not None.
- Missing id, customer_name, or starts_at is an error.
- Phone and email are presence checks only, with no format validation (open question 9).

Validation runs for the whole input before any reminder is computed or logged. The first error raises immediately.

Exception: ReminderInputError(ValueError). It carries only the message string, no extra attributes, and is raised with "from None" so that no chained context leaks values.

Message formats (index and field name only):
- "appointments: must be a list"
- "appointments[{i}]: must be a mapping"
- "appointments[{i}]: missing field '{field}'"
- "appointments[{i}]: field '{field}' has an invalid type"
- "appointments[{i}]: field '{field}' must be timezone-aware"
- "appointments[{i}]: duplicate 'id'"
- "now: must be timezone-aware" (no index)
- "appointments[{i}]: field 'starts_at' must be timezone-aware"
- "appointments[{i}]: field 'starts_at' must be a datetime, not a date"

Output: list of dicts with keys:
- appointment_id: the original id value
- channel: "sms" or "email"
- send_at: timezone-aware datetime in UTC, never earlier than now
- text: the message string

Sorted as in (a). Output contains no logging side effects beyond the logging rules.

(c) MESSAGE TEMPLATE AND LENGTH

Full form: "Hi {name}, reminder of your Brennan Opticians appointment on {date} at {time}. {sig}"
No-name form: "Reminder of your Brennan Opticians appointment on {date} at {time}. {sig}"

Date: f"{day:02d} {MON[month-1]} {year}" with MON = ("Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"). Day and time are Dublin local, derived from starts_at. Example: "27 Oct 2026".
Time: HH:MM, 24-hour, Dublin local of starts_at.
Signature: "Siobh\u00e1n N\u00ed Dhuibhir", or "Grzegorz Szczepa\u0144ski" when country is not None and country.strip().casefold() == "pl". Use \u escapes in the source so the bytes are fixed and NFC.

Normalization: name = unicodedata.normalize("NFC", customer_name.strip()), and any internal whitespace run is collapsed to one space (open question 14). Signatures are NFC as well.

Fixed lengths: the full form without the name is 96 code points (Siobhan) or 97 (PL). So the full-name budget is 64 (Siobhan) or 63 (PL).

SMS shortening order, first that fits wins:
1. Full name.
2. First token of the name (first whitespace-separated token).
3. First code point of the first token followed by a period, for example "S.".
4. No-name form.

Email: full form, no shortening, no length limit.

sms_fits(text): return len(text) <= SMS_MAX_CHARS, with SMS_MAX_CHARS = 160 in one module constant. Only this function and this constant know the limit.

Flag: 160 counts Python code points, not GSM-7 septets or UCS-2 units. Names and the signature containing "\u00e1", "\u00ed", and "\u0144" are not in the GSM-7 basic set, so on a real carrier the message is UCS-2. A 160-code-point UCS-2 message is multiple segments (about 67 code units per concatenated segment), not one. Accepting that multipart cost, changing the signature to ASCII (for example "Siobhan Ni Dhuibhir"), or moving to a 70-unit limit with a new template are client decisions.

(d) EDGE CASES (SMS-eligible unless noted; reminder times are UTC)

1. Case A: now 2026-10-13 22:00 IST (21:00Z), starts 2026-10-15 10:00 IST (09:00Z). Slot 1 at 2026-10-14 07:00Z; slot 2 at 2026-10-15 07:00Z. Confirmed.
2. Case B: starts 2026-10-14 09:00 IST (08:00Z), same now. Only slot 1 at 2026-10-14 07:00Z. Slot 2 nominal 06:00Z is 07:00 IST, quiet, moves to 19:00Z on 13 Oct (before now), dropped. Confirmed.
3. Case C: starts 2026-10-14 10:00 IST (09:00Z), same now. Slot 1 would be 07:00Z; slot 2 is 07:00Z; tie drops slot 1. Only slot 2 at 2026-10-14 07:00Z. Confirmed.
4. Case D: now 2026-10-13 03:00 IST (02:00Z), starts 2026-10-13 15:00 IST (14:00Z). Slot 1 at 2026-10-13 07:00Z (clamp, then earliest permitted); slot 2 at 2026-10-13 12:00Z. Confirmed.
5. Case E: same now, starts 2026-10-13 07:30 IST (06:30Z). Slot 1 at 07:00Z is after starts, dropped. Slot 2 moves to 19:00Z on 12 Oct, dropped. No reminders. Confirmed.
6. Case F (fall-back): now 2026-10-01 12:00 IST (11:00Z), starts 2026-10-26 08:00 GMT (08:00Z). Slot 1 at 2026-10-24 08:00Z (09:00 IST). Slot 2 nominal 2026-10-26 06:00Z is 06:00 GMT, quiet, moves to 20:00 GMT on 25 Oct, i.e. 2026-10-25 20:00Z. Confirmed.
7. Case G (spring-forward, corrected): now 2026-03-01 00:00Z, starts 2026-03-30 09:00 IST (08:00Z). Slot 1 at 2026-03-28 08:00Z (08:00 GMT, not quiet). Slot 2 nominal 06:00Z is 07:00 IST, quiet, moves to 19:00Z on 29 Mar (IST). Slot 2 at 2026-03-29 19:00Z.
8. Case H (boundaries): nominal exactly 21:00:00 is quiet and moves to 20:00 the same day. Nominal 20:59:59.999999 is not quiet. Nominal exactly 08:00:00 is not quiet. Nominal exactly 00:00:00 is quiet and moves to 20:00 the previous day. A nominal equal to now is not passed and is kept as is.
9. Spring-forward gap: wall times 02:00 to 02:59 on 29 Mar do not exist. Work is in UTC, so no reminder is built on a missing time.
10. Fall-back overlap: 01:00 to 01:59 on 25 Oct occurs twice. Both occurrences are quiet, so the result is the same.
11. Cancelled: status "  CANCELLED " gives no reminders. status "canceled" is not matched and is treated as active (pending open question 6).
12. Started: starts_at equal to now gives no reminders. starts_at one second after now is handled by the normal rules, and slot 1 is dropped if its send time is at or after starts_at.
13. Past-due 48h: now is 08:30 IST on 13 Oct, starts 13 Oct 12:00 IST. Slot 1 clamps to now (08:30 IST), slot 2 at 10:00 IST. Both are sent.
14. Past-due 2h after quiet move: slot 2 nominal is quiet and moves to a time before now. Dropped, no clamp.
15. PL signature: country " pl " or "PL" gives the Grzegorz signature. country None or "de" gives Siobhan.
16. Missing phone: phone None or "   " with an email gives EMAIL. Both phone and email missing gives no reminders.
17. Optout: optout missing or None gives EMAIL (if email exists). optout True gives EMAIL. optout False with phone gives SMS.
18. Blank phone with optout False and an email gives EMAIL.
19. 80-character name: SMS uses the first name (or initial) and keeps date, time, and signature. Email uses the full name.
20. Name of exactly 64 code points with the Siobhan signature: full form fits at 160. Name of 65 falls to the first-name form.
21. NFD: "a\u0301" (decomposed) normalizes to "\u00e1" and counts as 1 code point, equal to the precomposed form.
22. Slot 1 send equal to starts_at: dropped (at or after starts_at).

(e) ACCEPTANCE CRITERIA

1. plan_reminders with a tuple, a dict, or a non-Mapping element raises ReminderInputError with the index and field only.
2. A naive now raises ReminderInputError whose message names "now" but contains no datetime value.
3. A naive starts_at raises ReminderInputError whose message names "starts_at" and the index.
4. A date (not datetime) for starts_at raises ReminderInputError.
5. optout_sms_v2 equal to 0, 1, or "yes" raises ReminderInputError.
6. Duplicate id (by str) raises ReminderInputError naming the second index and "id".
7. No ReminderInputError message, repr, or args contains any email, phone, name, or text value.
8. Validation completes before any log line or output is produced for an invalid batch.
9. Every returned send_at is timezone-aware and in UTC, and is never earlier than now.
10. Every returned send_at is strictly before starts_at.
11. No returned send_at falls in the quiet window (Dublin wall time 21:00 to 07:59), except when it equals now and now itself is quiet, which never happens because earliest_permitted returns 08:00 in that case.
12. Cases A through H produce the results in section (d), with Case G corrected.
13. For one appointment, both slots never have the same send_at (tiebreak).
14. Output is sorted by (send_at UTC, str(id), channel, slot index).
15. Results are identical when the same inputs are given with Dublin-offset datetimes instead of UTC datetimes.
16. SMS texts pass sms_fits when the name is at most 64 code points (63 for PL) after NFC; the full-name form is used.
17. A name of 80 code points produces a shortened SMS containing the date, time, and signature unchanged.
18. The NFD and NFC forms of the same name produce identical text.
19. Country " pl " produces the Grzegorz signature; "PL" likewise.
20. The phone-with-optout-missing case produces an EMAIL reminder only.
21. The optout-True case produces EMAIL only; optout-False with a phone produces SMS.
22. A blank phone with an email produces EMAIL only; no phone and no email produces an empty list.
23. The module only imports from the standard library (plus collections.abc).
24. Logging: exactly one INFO summary per call; DEBUG lines contain the id and a reason code only.
25. Changing SMS_MAX_CHARS is the only change needed to alter the length check.

(f) OPEN QUESTIONS (with recommended default)

1. Switch to UCS-2 with a 70-unit limit? Default: no switch now; keep 160 code points. Note that 70 also breaks the no-name template (91 code points), so a template or multipart decision is needed.
2. Drop the 48h reminder when it collides with the 2h reminder? Default: yes, as specified (keep the 2h reminder).
3. Drop a 2h reminder pushed before now by quiet hours? Default: yes, no clamp.
4. Should missing optout count as opted out, and should email still be sent in that case? Default: yes for both.
5. Should email use the same text without the SMS limit? Default: yes, full-name form, no limit.
6. Should "canceled" count as cancelled? Default: yes, treat both spellings as cancelled, to avoid unwanted reminders.
7. Does starts_at equal to now count as started? Default: yes.
8. Is DD Mon YYYY the agreed date format? Default: yes; confirm with the client.
9. Should phone and email get format validation? Default: no, presence checks only.
10. Should duplicate ids fail the whole batch? Default: yes.
11. May the tzdata package be added as a dependency? Default: no. Needs client approval if the target container lacks the system tz database.
12. The house rule asks for an INFO line per reminder naming the contact, but the privacy rule forbids logging contact data. Default: one INFO line per planned reminder containing the appointment id, slot, and channel only, with no email, phone, or name. The client must sign off on any contact reference, which would still be personal data.
13. Should a 48h reminder already past due be sent immediately at now (clamp, as specified) or dropped? Default: clamp, as specified.
14. How should customer names with internal runs of whitespace or control characters be handled? Default: collapse whitespace runs to one space and strip control characters before counting.
15. Keep the accented signature (non-GSM-7, so UCS-2 on carriers) or switch to an ASCII form? Default: keep the accented signature as specified; the cost and segment impact must be accepted by the client.