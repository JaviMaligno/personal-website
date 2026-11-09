# Appointment Reminders: Design

This document covers design only. It contains no implementation. The module and test file will be written from this spec.

## 1. Scope and build order

- Build and test the 2-hour path first (AC10). The 48-hour path is added second, using the same scheduling function.
- Standard library only: `datetime`, `zoneinfo`, `logging`, `re`, `typing`, `unittest`.
- Dublin conversions use `ZoneInfo("Europe/Dublin")`. The server runs in UTC.

## 2. Module layout

- Module: `/private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-jtcp4lrr/appointment_reminders.py`
- Tests: `/private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-jtcp4lrr/test_appointment_reminders.py` (unittest, with `assertLogs` for logging tests)
- Constants at module top: `SMS_LIMIT = 160`, `QUIET_START = time(21, 0)`, `QUIET_END = time(8, 0)`, `SHIFT_TO = time(20, 0)`, `EMAIL_ON_OPTOUT = True`, `SIG_DEFAULT = "Chevonne Nee Divver"`, `SIG_PL = "Grzegorz Szczepański"`, `DUBLIN = ZoneInfo("Europe/Dublin")`, `UTC = timezone.utc`.

## 3. Public API and data shapes

```
plan_reminders(appointments: Sequence[Mapping[str, Any]], now: datetime) -> list[dict]
```

Input appointment fields: `id`, `customer_name`, `email`, `phone`, `country`, `status`, `starts_at`, `optout_sms_v2`. The old `opt_out` field is never read.

Output: a list of dicts with exactly the keys `appointment_id`, `channel`, `send_at`, `text`. `send_at` is a UTC-aware datetime (see decision list).

### Validation rules (per record)

| Field | Rule | On failure |
|---|---|---|
| `id` | non-empty `str` after strip | skip record, WARNING with index only |
| `status` | `str` | skip, WARNING with id |
| `starts_at` | `datetime` with non-None utcoffset | skip, WARNING with id |
| `optout_sms_v2` | `bool`, or `None`/missing (treated as `True`) | other types: skip, WARNING with id |
| `customer_name` | `str` or `None` (`None` becomes `""`), stripped | non-str: skip, WARNING with id |
| `email` | stripped; `""` or `None` means absent; must contain `@` and no whitespace | invalid: treated as absent, WARNING with id, value not logged |
| `phone` | spaces removed; optional leading `+` then 7 to 15 digits; `""` or `None` means absent | invalid: treated as absent, WARNING with id |
| `country` | `str` or `None` | non-str: treated as `None` |

Duplicate ids: the first occurrence is kept, later ones are skipped with a WARNING carrying the id.

## 4. Function breakdown

- `plan_reminders(appointments, now)`: validates `now`, parses records, plans reminders, sorts, logs summary and per-reminder INFO lines, returns the list.
- `_check_now(now) -> None`: raises `ValueError("now must be timezone-aware")` when `now.utcoffset()` is None. The message contains no record data.
- `_parse_record(index, raw) -> _Appt | None`: applies section 3 rules. Returns a `NamedTuple` with `id, name, email, phone, country, cancelled, starts_utc, optout`, or `None` on skip.
- `_choose_channel(appt) -> str | None`: section 8.
- `_schedule(starts_utc, now_utc) -> list[tuple[str, datetime]]`: returns `(kind, instant)` pairs using the rules in section 5. Kind is `"48h"` or `"2h"`.
- `_quiet_shift(instant_utc) -> datetime`: section 6. Returns the instant unchanged when it is not in quiet hours.
- `_local_text(instant_utc) -> str`: converts to Dublin local and formats as `"14 Oct 2026 14:30"` using a fixed English month table (not `strftime`, to avoid locale dependence).
- `_signature(country) -> str`: returns `SIG_PL` when `country.strip().upper() == "PL"`, else `SIG_DEFAULT`.
- `_template(name, when_text, sig) -> str`: the single source of wording: `f"Hi {name}, reminder: your Brennan Opticians appointment is on {when_text}. {sig}"`. An empty name is rendered as `"Hello,"` in place of `"Hi {name},"`.
- `_sms_text(name, when_text, sig) -> str`: applies the SMS truncation in section 9.
- `_email_text(name, when_text, sig) -> str`: `_template` with the full name, no limit.

## 5. Scheduling rules (per appointment, all arithmetic on UTC instants)

```
starts = starts_at.astimezone(UTC)
if cancelled or starts <= now: return []          # started or at now: no reminders
channel = _choose_channel(appt); if None: return []
r48 = starts - 48h ; r2 = starts - 2h
if now >= r2:            pts = [("2h", now)]       # 2h point passed, not started
elif now >= r48:         pts = [("48h", now), ("2h", r2)]
else:                    pts = [("48h", r48), ("2h", r2)]
for kind, t in pts:
    s = _quiet_shift(t)
    if s < now: drop (no reminder)                 # never return past sends
    else: emit {appointment_id, channel, send_at: s, text}
```

Points at exactly `now` are kept (`send_at == now` is allowed). Only `send_at < now` is dropped.

## 6. Quiet-hours shift

```
local = instant.astimezone(DUBLIN)
t = local.time()
if time(8,0) <= t < time(21,0): return instant          # allowed
day = local.date() if t >= time(21,0) else local.date() - timedelta(days=1)
return datetime.combine(day, time(20,0), tzinfo=DUBLIN).astimezone(UTC)
```

- 21:00:00 exactly is in the window and shifts to 20:00 the same day.
- 08:00:00 exactly is allowed and does not shift.
- 20:00 is never ambiguous or nonexistent in Dublin, so `fold` does not matter for the target.
- The window check uses the Dublin local time from `astimezone`, so DST is handled. A time such as 01:00 GMT on 25 October (the repeated hour) is in the window and shifts to the previous evening.

## 7. DST-aware Dublin conversion

- Stored and compared values are UTC instants. `starts - timedelta(hours=48)` is 48 real hours. Subtracting wall-clock values on a shared `ZoneInfo` tzinfo is never used.
- Display and quiet-hours checks use `instant.astimezone(DUBLIN)`.
- 2026 transitions relevant to tests: 29 March (01:00 UTC, clocks forward) and 25 October (01:00 UTC, clocks back).

## 8. Channel and opt-out

```
optout = True if rec.optout is None else rec.optout
if phone and not optout:            return "sms"
if email and (not optout or EMAIL_ON_OPTOUT): return "email"
return None
```

- Each appointment uses one channel for all its reminders. SMS and email are never both sent for the same reminder.
- No phone and an email present gives email.
- `None` or missing `optout_sms_v2` is treated as opted out.

## 9. SMS length and truncation

Counting unit: Python code points, `len(text) <= 160`.

Algorithm:
1. Build `full = _template(name, when_text, sig)`.
2. If `len(full) <= 160`, use it.
3. Otherwise compute `budget = 160 - len(_template("", when_text, sig))`. For the fixed wording this is 66 for the default signature and 65 for the PL signature.
4. If `len(name) <= budget`, the name fits (this case cannot occur after step 2 unless the name was trimmed, so it is a safety check only).
5. If `budget >= 4`: `short = name[:budget-3].rstrip() + "..."`. Use ASCII dots only. Do not use the ellipsis character, because it is non-GSM and would change encoding.
6. If `budget < 4`: use the name-free greeting `"Hello,"`.
7. Always rebuild with `_template`. The date and HH:MM are never touched. If the result is still over 160, raise an internal `ValueError` with a constant message. With the fixed signatures this cannot happen, so the guard is a tripwire.

Worked example (default signature): `when_text = "14 Oct 2026 14:30"`, name = `"Abcdefghij" * 10` (100 chars). Fixed part is 94, so budget is 66. Result is `"Hi " + ("Abcdefghij"*6) + "Abc..." + ", reminder: your Brennan Opticians appointment is on 14 Oct 2026 14:30. Chevonne Nee Divver"`, length 160.

Email: uses the full name, no truncation, same wording.

## 10. Sorting and tie-breaking

Sort key: `(send_at_utc, appointment_id, channel)`, ascending. Because `send_at` is UTC, instant comparison is exact. Example: two appointments with the same start and ids `"b-2"` and `"a-1"` at the same time order as `"a-1"` then `"b-2"`. Email sorts before sms on a tie, but the same appointment cannot have both channels.

## 11. Logging and errors

- One INFO line per planned reminder: `planned reminder appointment_id=%s channel=%s send_at=%s`. No contact, name, or text. This is the subject of decision D1.
- One INFO summary per call: `plan_reminders appointments=%d planned=%d skipped=%d`.
- WARNING for skipped or invalid records: `skipped appointment id=%s reason=%s` (or `index=%d` when the id is missing or invalid). Reasons are constant strings. Values are never logged.
- Never log email, phone, name, or message text.
- Exception messages are constant strings naming fields only. They never include the appointment dict or any value from it.

## 12. Test plan (maps to acceptance criteria)

Notation: `now` in UTC, times given as Z or IST/GMT. Dublin is IST (UTC+1) until 25 Oct 2026 and GMT after it. Every expected value is a UTC instant. Unless noted, phone is `"+353871234567"`, email is `"c@example.ie"`, status is `"booked"`, optout is `False`, country is `None`.

| # | AC | Test | Input | Expected |
|---|---|---|---|---|
| T1 | 1 | normal two reminders | starts 2026-10-20T12:00Z, now 2026-10-01T00:00Z | `[2026-10-18T12:00Z sms, 2026-10-20T10:00Z sms]` |
| T2 | 1 | 48h passed, 2h future | starts 2026-10-15T11:00Z, now 2026-10-13T14:00Z | `[2026-10-13T14:00Z sms, 2026-10-15T09:00Z sms]` |
| T3 | 1 | 2h passed, not started | starts 2026-10-13T17:00Z, now 2026-10-13T16:30Z | `[2026-10-13T16:30Z sms]` (text shows 18:00 appointment time) |
| T4 | 1 | already started | starts 2026-10-13T16:00Z, now 2026-10-13T16:30Z | `[]` |
| T5 | 1 | starts equals now | starts = now | `[]` |
| T6 | 1 | 2h point equals now | starts 2026-10-15T11:00Z, now 2026-10-15T09:00Z | `[2026-10-15T09:00Z sms]` |
| T7 | 1, 8 | Oct DST, 48h across change | starts 2026-10-26T10:00Z, now 2026-10-20T00:00Z | `[2026-10-24T10:00Z, 2026-10-26T08:00Z]`; the naive value 09:00Z must not appear |
| T8 | 1, 8 | Mar DST, 48h across change | starts 2026-03-29T10:00Z, now 2026-03-20T00:00Z | `[2026-03-27T10:00Z, 2026-03-29T08:00Z]`; naive 11:00Z must not appear |
| T9 | 1, 4, 8 | 2h shift across Oct change | starts 2026-10-25T03:00Z, now 2026-10-20T00:00Z | `[2026-10-23T03:00Z, 2026-10-24T19:00Z]` (01:00 GMT shifts to 20:00 IST Oct 24) |
| T10 | 1, 4, 8 | quiet shifts across Mar change | starts 2026-03-29T04:00Z, now 2026-03-20T00:00Z | `[2026-03-26T20:00Z, 2026-03-28T20:00Z]` |
| T11 | 4 | 03:00 local shifts to 20:00 previous evening | starts 2026-10-14T04:00Z, now 2026-10-11T12:00Z | `[2026-10-12T04:00Z, 2026-10-13T19:00Z]` |
| T12 | 4 | exactly 21:00 shifts to 20:00 same day | starts 2026-10-14T22:00Z, now 2026-10-11T12:00Z | `[2026-10-12T19:00Z, 2026-10-14T19:00Z]` |
| T13 | 4 | exactly 08:00 allowed | starts 2026-10-14T09:00Z, now 2026-10-11T12:00Z | `[2026-10-12T09:00Z, 2026-10-14T07:00Z]` |
| T14 | 4 | immediate send in quiet hours, shift is before now, dropped | starts 2026-10-14T07:30Z, now 2026-10-14T05:30Z | `[]` (19:00Z Oct 13 is before now; no forward move) |
| T15 | 4 | 48h-at-now quiet, dropped; 2h kept | starts 2026-10-14T09:00Z, now 2026-10-13T22:00Z | `[2026-10-14T07:00Z]` |
| T16 | 2 | SMS by default | phone set, optout False | both reminders channel `sms` |
| T17 | 2 | optout true with email | optout True | both channel `email`; no sms |
| T18 | 2 | optout true, no email | optout True, email None | `[]` |
| T19 | 2 | no phone, email present | phone None | channel `email` |
| T20 | 2 | no phone, no email | phone None, email None | `[]`; INFO summary shows skipped |
| T21 | 2 | optout None treated as true | optout None, email set | channel `email` |
| T22 | 3 | long name truncated | name 100 chars, sms | text length 160, ends with `Chevonne Nee Divver`, contains `14 Oct 2026 14:30`, name `Abcdefghij`*6 + `Abc...` |
| T23 | 3 | short name unchanged | name "Ann" | full template, length under 160 |
| T24 | 3 | budget under 4 uses name-free greeting | direct call `_truncate` with budget 3 | greeting `Hello,`, date and signature intact |
| T25 | 5 | cancelled | status `"cancelled"` and `" Cancelled "` | `[]` for both |
| T26 | 6 | logs have no PII | email `private@example.ie`, name `Siobhan Test`, phone set | captured log lines contain none of these; one INFO per reminder; text not logged |
| T27 | 6 | exception messages have no PII | naive `now`, record containing email | `ValueError` message lacks the email and name |
| T28 | 7 | default signature | country `"IE"` | text ends with `Chevonne Nee Divver` |
| T29 | 7 | PL signature, case-insensitive | country `" pl "`, name `"Anna Nowak"` | text ends with `Grzegorz Szczepański`, length check applies |
| T30 | 7 | Poland not matched (documents current choice) | country `"Poland"` | ends with `Chevonne Nee Divver` (see D6) |
| T31 | 8 | Dublin time shown | starts 2026-10-14T09:00Z | text contains `14 Oct 2026 10:00` |
| T32 | 8 | Dublin time shown after clock change | starts 2026-10-26T10:00Z | text contains `26 Oct 2026 10:00` |
| T33 | 9 | sort with ties | A `"b-2"` starts 2026-10-20T12:00Z; B `"a-1"` same; C `"c-3"` starts 2026-10-19T12:00Z; now 2026-10-01T00:00Z | order: c-3 Oct17 48h; a-1 Oct18 12:00 48h; b-2 Oct18 12:00 48h; c-3 Oct19 10:00 2h; a-1 Oct20 10:00 2h; b-2 Oct20 10:00 2h |
| T34 | 10 | 2h path works alone | only 2h point future (48h passed, now after r2 minus margin) | 2h reminder present |
| T35 | misc | naive `now` | naive datetime | `ValueError` |
| T36 | misc | naive `starts_at` skipped | starts without tzinfo | `[]` plus WARNING with id only |
| T37 | misc | duplicate ids | two records with id `"x"` | first kept, second skipped with WARNING |
| T38 | misc | empty input | `[]` | `[]` |

## 13. Decisions and ambiguities

Contradictions for the PM to take to the client:

- D1. Logging conflict. The house rule asks for who and how (channel and contact) on each INFO line. AC6 forbids logging email and discourages names and phones. Proposal: log `appointment_id` and `channel` only. Support can trace a delivery through the appointment id in the CRM. If contact tracing is needed, it belongs in a restricted audit store, not app logs. Needs DPO or client sign-off.
- D2. Quiet-hours drops. An immediate send that falls in quiet hours and shifts to a past 20:00 is dropped. Example: now 06:30 Dublin for an appointment at 08:30 gives no reminder. Proposal: keep the drop, as the hard rule states. Alternative for client: send at 08:00 for morning-of cases, which changes the rule.
- D3. SMS length. Counting is by code points against 160, as the AC says. Real billing differs. `ń` in "Szczepański" (and `ł`, `ś`, `ą`, and similar in customer names) makes the whole SMS UCS-2, where one segment holds 70 code units and concatenated parts hold 67 each. A 160-code-point PL message is three segments. Options: accept, or transliterate names only. The signature must stay exact per the client, so transliteration applies to the name only.
- D4. Opt-out email. Sending email when SMS is opted out may need consent review under PECR and GDPR, because SMS opt-out does not imply email consent. Implemented as specified, behind `EMAIL_ON_OPTOUT = True`. Legal review before go-live. The switch can be set to `False` quickly.
- D5. Email subject. The output dict has exactly four keys, so no subject can be carried. Proposal: sender uses the constant `"Your Brennan Opticians appointment reminder"`. Alternatively, add a fifth key, which breaks the stated contract.

Proposed defaults to confirm:

- D6. Country: match ISO code `PL` case-insensitively after strip. `"Poland"` falls back to the default signature. Confirm the CRM stores ISO-2 codes, since a wrong signature is a visible error.
- D7. 2h point passed, not started: send one reminder at now (quiet rules apply), which supersedes the 48h reminder. Otherwise the customer would receive two reminders at once.
- D8. Started appointments (`starts <= now`) get nothing. Confirmed by the spec's wording; please verify.
- D9. Name shortening: the name-free fallback fits, so the signature and date always remain. The conflict the PM raised cannot occur with the fixed signatures and date width. The guard stays as a tripwire.
- D10. Date format in text: `"14 Oct 2026 14:30"`, Dublin local, fixed English month names.
- D11. Status: compare `strip().casefold()`, exclude `"cancelled"` and `"canceled"`. Other statuses such as `completed` or `no_show` are not excluded, since they only apply to appointments that have started, which are already excluded.
- D12. Missing phone and email: no reminder, logged by id. Confirm.
- D13. Optout `None` or missing is treated as opted out. Confirm this conservative default.
- D14. `send_at` is returned in UTC. Aware datetime equality compares instants, so tests are unaffected by display zone.
- D15. Tie-break: `(send_at, appointment_id, channel)`.
- D16. Naive `now` raises `ValueError`. Naive `starts_at` skips the record with a WARNING, so one bad record cannot block the batch. Malformed records and duplicate ids are skipped with WARNING logs carrying only the id or index.
- D17. Quiet window: 21:00 inclusive, 08:00 exclusive. Confirm.
- D18. The "Nee" in the signature is kept verbatim as the client's literal string. Confirm.