"""Brennan Opticians appointment reminders.

Public API: plan_reminders(appointments, now) -> list of dicts with exactly the keys
appointment_id, channel ("sms"|"email"), send_at, text. Pure function: no I/O, no clock.

Assumptions and rules
- Two reminders per appointment: 48h and 2h before the start. The client wording was cut
  off; the second reminder is assumed to be 2 hours before (REMINDER_HOURS_BEFORE).
- Offsets are absolute durations on aware datetimes, so DST changes do not alter elapsed
  time. Only displayed date/time and quiet-hour checks use local time.
- Europe/Dublin is used for ALL customers, including country PL (assumption).
- Candidate send time = max(target, now). Quiet hours are local >= 21:00 or < 08:00
  (20:00 and 08:00 exactly are allowed). A quiet candidate moves back to the preceding
  20:00; if that is before now, it moves forward to the next 08:00, kept only if strictly
  before the start, otherwise that reminder is dropped. Each reminder resolves
  independently. If both resolve to the same send_at only the 2h one is kept.
- Skips: status cancelled/canceled (stripped, casefolded); starts_at <= now; malformed
  records (WARNING, batch continues); no usable channel (WARNING).
- Opt-out semantics: only optout_sms_v2 is consulted. Missing/None/False/0 means not
  opted out; True/1/"true"/"1"/"yes" means opted out; anything else is treated as opted
  out with a WARNING. Opt-out affects SMS only; email is the fallback channel.
- SMS length is len(text) in Python characters (GSM/UCS-2 segmenting is not modelled).
  Name shortening ladder: full, first token, hard-cut first token, initial plus ".",
  no name, then a compact template. Date, time and signature are never cut. Emails are
  not truncated.
- Logging: one INFO line per planned reminder with appointment id, channel and a MASKED
  contact (phone: last two digits only; email: "email on file"). The full address, full
  phone number and customer name are never logged (client requirement R13 takes
  precedence over logging the raw contact).
"""
import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

_log = logging.getLogger("brennan.reminders")
_DUBLIN = ZoneInfo("Europe/Dublin")
REMINDER_HOURS_BEFORE = (48, 2)  # 2h is an ASSUMPTION (client wording cut off)
_SMS_LIMIT = 160
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_SIG_DEFAULT = "Siobhán Ní Dhuibhir"
_SIG_PL = "Grzegorz Szczepański"
_CANCELLED = {"cancelled", "canceled"}
_TRUE_STR = {"true", "1", "yes"}


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _opted_out(value, appt_id):
    if value is None or value is False:
        return False
    if value is True:
        return True
    if isinstance(value, str) and value.strip().casefold() in _TRUE_STR:
        return True
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    _log.warning("unrecognised optout value, treated as opted out: appointment=%s", appt_id)
    return True


def _usable(value):
    return isinstance(value, str) and bool(value.strip())


def _is_quiet(local):
    return local.hour >= 21 or local.hour < 8


def _resolve(candidate, now, starts):
    local = candidate.astimezone(_DUBLIN)
    if not _is_quiet(local):
        return candidate
    day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    back = datetime.combine(day, time(20, 0), tzinfo=_DUBLIN)
    if back >= now:
        return back
    day = local.date() if local.hour < 8 else local.date() + timedelta(days=1)
    fwd = datetime.combine(day, time(8, 0), tzinfo=_DUBLIN)
    return fwd if fwd < starts else None


def _sms_text(name, date_s, time_s, sig, limit=_SMS_LIMIT):
    def build(n):
        hi = f"Hi {n}," if n else "Hi,"
        return f"{hi} reminder: your Brennan Opticians appointment is on {date_s} at {time_s}. {sig}"

    name = " ".join(name.split())
    first = name.split(" ")[0] if name else ""
    options = [name, first]
    options += [first[:n] for n in range(len(first) - 1, 0, -1)]
    if first:
        options.append(first[0] + ".")
    options.append("")
    for n in options:
        text = build(n)
        if len(text) <= limit:
            return text
    return f"Brennan Opticians: appointment {date_s} at {time_s}. {sig}"


def _build_text(channel, name, local, country):
    sig = _SIG_PL if isinstance(country, str) and country.strip().upper() == "PL" else _SIG_DEFAULT
    date_s = f"{local.day} {_MONTHS[local.month - 1]} {local.year}"
    time_s = local.strftime("%H:%M")
    name = name if isinstance(name, str) else ""
    if channel == "sms":
        return _sms_text(name, date_s, time_s, sig)
    name = " ".join(name.split())
    hi = f"Hi {name}," if name else "Hi,"
    return f"{hi} reminder: your Brennan Opticians appointment is on {date_s} at {time_s}. {sig}"


def _mask(channel, phone):
    if channel == "email":
        return "email on file"
    digits = "".join(c for c in phone if c.isdigit())
    return "phone ending " + digits[-2:] if digits else "phone"


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    planned = []
    for appt in appointments:
        if not isinstance(appt, dict):
            _log.warning("skipping malformed appointment record: not a dict")
            continue
        appt_id = appt.get("id")
        starts = appt.get("starts_at")
        if appt_id is None or not _aware(starts):
            _log.warning("skipping malformed appointment: appointment=%s", appt_id)
            continue
        status = appt.get("status")
        if isinstance(status, str) and status.strip().casefold() in _CANCELLED:
            continue
        if starts <= now:
            continue
        phone, email = appt.get("phone"), appt.get("email")
        opted_out = _opted_out(appt.get("optout_sms_v2"), appt_id)
        if _usable(phone) and not opted_out:
            channel = "sms"
        elif _usable(email):
            channel = "email"
        else:
            _log.warning("no usable channel: appointment=%s", appt_id)
            continue
        resolved = {}
        for hours in REMINDER_HOURS_BEFORE:
            target = starts - timedelta(hours=hours)
            send = _resolve(max(target, now), now, starts)
            if send is None:
                _log.info("reminder dropped, no valid slot before start: appointment=%s hours_before=%s",
                          appt_id, hours)
            else:
                resolved[hours] = send
        if len(resolved) == 2 and resolved[48] == resolved[2]:
            del resolved[48]
        local_start = starts.astimezone(_DUBLIN)
        for hours, send in resolved.items():
            text = _build_text(channel, appt.get("customer_name"), local_start, appt.get("country"))
            _log.info("reminder planned: appointment=%s hours_before=%s channel=%s contact=%s send_at=%s",
                      appt_id, hours, channel, _mask(channel, phone if isinstance(phone, str) else ""),
                      send.astimezone(_DUBLIN).isoformat())
            planned.append((send.astimezone(timezone.utc), str(appt_id), -hours, {
                "appointment_id": appt_id,
                "channel": channel,
                "send_at": send.astimezone(_DUBLIN),
                "text": text,
            }))
    planned.sort(key=lambda p: p[:3])
    return [p[3] for p in planned]