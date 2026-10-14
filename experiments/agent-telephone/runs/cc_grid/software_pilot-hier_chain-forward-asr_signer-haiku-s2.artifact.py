## Verdict

The design is implementable as a single stdlib module, but four points conflict with the brief or with each other and need a decision before code is written:

- **Logging conflict:** the house logging rule asks for the contact (channel and contact) on every planned-reminder log line. The brief and the design forbid logging any email or phone.
- **SMS length conflict:** the brief's 160-character limit does not hold for Polish or Irish text, which is sent as UCS-2 with a 70-character single-segment limit. The Polish signature alone forces UCS-2.
- **Immediate-send conflict:** "send now" for an overdue 48-hour reminder conflicts with the quiet window when `now` falls between 21:00 and 08:00.
- **Quiet-fallback conflict:** when the 20:00 anchor is already past, the design falls back to the next 08:00, which can land after the appointment or in a different day than the brief describes.

## 1. Scoped plan

**Deliverables**
- `reminders.py`: one public function, `plan_reminders(appointments, now) -> list[dict]`, plus private helpers.
- `tests/test_reminders.py`: unit tests with a fixed `now`.

**Module layout (single file, stdlib only)**
- Constants: `TZ = ZoneInfo("Europe/Dublin")`, quiet window bounds, SMS limits, signatures, cancelled set, and reason codes.
- `_require_aware(dt, name)`: raises `ValueError` naming the field only, never the appointment.
- `_normalise(appt)`: strips strings, maps blank phone or email to `None`, upper-cases and strips country, casefolds and strips status, and coerces `id` to a comparable key for sorting.
- `_is_cancelled`, `_is_opted_out` (True only for bool `True`; anything else is treated as opted out and logged as `optout_nonbool`).
- `_choose_channel(appt)`: returns `("sms", phone)`, `("email", email)`, or `None`. Decided once per appointment.
- `_candidates(starts_at)`: the 48h and 2h points.
- `_quiet_adjust(t_utc)`: converts to Dublin local, and if the time is in [21:00, 08:00) moves it to the most recent 20:00 at or before it, then converts back to UTC.
- `_schedule(appt, now)`: returns 0 to 2 `(kind, send_at_utc)` pairs using the design's steps.
- `_render(appt, channel, send_at)`: builds text with the Dublin date and 24-hour time, and the signature.
- `_fit_sms(text)`: applies the name-shortening ladder, then skips with `sms_too_long` if the name-free text still does not fit.

**Data flow**
1. Validate `now` (aware, else `ValueError`).
2. Build a count of `id` values to detect duplicates.
3. For each appointment: normalise, then apply skips in a fixed order (duplicate id, cancelled, naive `starts_at`, no contact). Each skip logs one reason code.
4. Choose the channel once.
5. Schedule reminders, dropping any with `send_at >= starts_at` or `send_at < now`.
6. Render, and for SMS apply the fit rule.
7. Sort by `(send_at_utc, str(id), kind order 48h before 2h)`.
8. Log one line per planned reminder, then return the list.

**Test approach**
- Fixed `now` values in each case, with no network. Optionally patch `socket` to prove purity.
- Quiet boundaries: 20:59:59 allowed, 21:00 quiet, 07:59 quiet, 08:00 allowed.
- DST: appointments whose 48h or 2h points fall near 2026-03-29 and 2026-10-25, checked in Dublin local time.
- Dublin date differs from UTC date (for example, an appointment at 00:30 Dublin time).
- 48h point already passed: immediate send at `now` (or quiet-adjusted), and the 2h reminder still emitted when valid.
- 2h point passed: that reminder skipped, 48h kept when valid.
- Started, or starting in under 2h: no reminders, or only valid ones.
- Cancelled with case and whitespace variants.
- Channel matrix: opted-out with email, opted-out with no email, not opted-out with phone, no phone with email, neither.
- SMS length: exactly 160 passes, 161 is shortened, and the name ladder order is correct.
- Country "PL" in lower case and with whitespace.
- Sort order with equal `send_at` values and mixed id types.
- `caplog` over full output: no email or phone substring anywhere in logs or exception text.
- Duplicate ids, unknown status values, naive `starts_at`, non-bool `optout_sms_v2`.

**Scope cut:** if time runs short, keep the 2h reminder and the channel logic first, then the 48h reminder.

## 2. Conflicts to resolve

- **Logging (blocking):** the house rule requires contact details in each log line. The brief and the DPC audit requirement forbid it. The plan logs `appointment_id` and `channel` only.
- **SMS encoding (blocking):** "Grzegorz Szczepański" contains ś and ń, so the PL SMS is UCS-2 with a 70-character single-segment limit. Date, time and signature together likely exceed 70 characters. Irish fadas (á, í, ó, ú) also break GSM-7. Counting code points cannot match real segment limits.
- **Immediate 48h send vs quiet window:** the brief says "immediately" and "nothing between 21:00 and 08:00". The design lets quiet win.
- **Quiet fallback:** the design's "next 08:00" fallback conflicts with the brief's "move back to the 20:00 just before it" when that 20:00 is past. It can also push the send past `starts_at`.
- **Design step 6** ("fix it if needed") is undefined.
- **Name shortening:** the design says "shorten the name", but the signature is also a name. The text template is not specified, so it is unclear where `customer_name` appears.
- **zoneinfo:** on Windows, `zoneinfo` needs the third-party `tzdata` package, which breaks stdlib-only. The server is UTC Linux, so this is likely fine, but it should be confirmed.
- **Python version:** the design says 3.9+, the house target is 3.12. No real conflict.

## 3. Open questions with recommended defaults

1. **Quiet rule past 20:00:** if the 20:00 anchor is before `now` and `now` is outside the window, send at `now`. If `now` is inside the window, send at the next 08:00 Dublin only if that is before `starts_at`, otherwise drop with `skipped_started`. Default: this design, with the 08:00-after-start case dropped.
2. **Overdue 48h send during quiet hours:** default is quiet wins (defer to 08:00), logged as `quiet_shifted`. Needs PM sign-off since it contradicts "immediately".
3. **Overdue 2h reminder:** default skip with `missed_2h`. Do not send late at `now`.
4. **Opted out, no email:** default no reminder, log `skipped_no_contact`.
5. **Neither phone nor email:** default no reminder, log `skipped_no_contact`.
6. **Non-bool `optout_sms_v2` (missing or string):** default treat as opted out, log `optout_nonbool`. Note this means a customer with a phone and no flag gets email, which differs from the literal brief. Confirm.
7. **Cancelled definition:** default cancelled after normalisation if the value is "cancelled" or "canceled". Other statuses are treated as active. Confirm the full list of CRM status values.
8. **SMS over 160:** default shorten the name by the ladder, and if still too long, skip with `sms_too_long`. Never truncate date, time or signature.
9. **GSM-7 vs UCS-2:** default measure by encoding (GSM-7 limit 160, UCS-2 limit 70 in UTF-16 units). For PL or accented signatures this will skip SMS. PM must decide between skipping, sending multipart, or falling back to email. Recommend not silently falling back.
10. **Already-started appointments:** default skip, `skipped_started`.
11. **Short-notice bookings (under 2h):** default send the 48h reminder at `now` if it is valid, and skip 2h. Confirm.
12. **Tie-breaking:** default `(send_at, str(id), kind)`, 48h before 2h.
13. **Date format:** default DD/MM/YYYY. Confirm, since ISO is unambiguous.
14. **Time format:** default HH:MM 24-hour, Dublin local.
15. **Output `send_at` timezone:** default timezone-aware UTC.
16. **Channel consistency:** default one channel per appointment, decided once, so both reminders match.
17. **Naive datetimes:** `now` naive raises `ValueError`. Naive `starts_at` skips the appointment with `naive_datetime`.
18. **Duplicate appointment ids:** default skip every appointment sharing the duplicated id, log `duplicate_id`. Raising would block the whole batch.
19. **08:00 fallback after start:** default drop with `skipped_started`.
20. **Logging contact (house rule conflict):** default log only `appointment_id`, `channel` and reason codes. Support can map ids to contacts in the CRM. Waiving the house rule needs PM and DPC sign-off.
21. **Message template wording:** not specified. Needed before tests can assert lengths. Also confirm where `customer_name` appears.
22. **Email subject and body:** the brief does not define them. Default: subject "Appointment reminder", body the same as the SMS template with the full name.
23. **Country codes:** default accept only "PL" for the Polish signature, after normalisation. Confirm whether other variants occur.
24. **zoneinfo on Windows:** default assume a Linux server with the system tz database. Confirm.
25. **Test framework:** default pytest for tests (not part of the module). unittest would keep zero dependencies if preferred.