"""Appointment reminders for Brennan Opticians.

Public entry point: plan_reminders(appointments, now).

Decisions and interpretations:
- FIRST_REMINDER_OFFSET is 48h of absolute elapsed time (UTC arithmetic).
- SECOND_REMINDER_OFFSET = 2h is an INTERPRETATION of garbled client wording
  ("the second one too, hours before" / "the 2-hour reminder").
- First reminder whose 48h point is past is sent at `now`. The second one is
  never pulled forward; if its time is past it is dropped.
- Quiet hours 21:00-08:00 Europe/Dublin: a time in [21:00, 08:00) moves back
  to the preceding 20:00 local (built from wall time, not by subtracting
  hours). If the result is before `now` the reminder is dropped (never pushed
  into the morning). Reminders are independent of each other.
- Dedupe: identical send_at for both reminders -> only the 2-hour one is kept
  (the 2-hour reminder has priority when only one is possible).
- Never emit send_at < now or send_at >= starts_at. Starts <= now yield nothing.
- Channel: SMS if phone has >= 7 digits and optout_sms_v2 is not truthy, else
  email. Only optout_sms_v2 is read (legacy opt_out is ignored). Truthy means
  True, 1, or the strings "true"/"1" (case-insensitive, stripped); missing
  means not opted out. No usable channel -> one id-only warning, skipped.
- Malformed appointments (not a dict, missing id/starts_at, naive or non-datetime
  starts_at) are skipped with a warning.
- Date format in texts is DD/MM/YYYY, time HH:MM, Europe/Dublin local time.
- SMS limited to 160 characters. Risk: non-GSM characters (a-acute, n-acute,
  o-acute in signatures) force UCS-2 where a segment is 70 characters, so real
  messages may be split into several segments and cost more.
- Logging / privacy: the house rule asks for one INFO line per planned
  reminder saying who and how. The task's hard privacy rule forbids logging
  email, phone or names, so the INFO line carries the appointment id (the
  recipient reference), channel and send time only, never the contact value.
  All log lines contain ids only.
- Requires tzdata for zoneinfo on systems without a system tz database.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

FIRST_REMINDER_OFFSET = timedelta(hours=48)
SECOND_REMINDER_OFFSET = timedelta(hours=2)
LOCAL_TZ = ZoneInfo("Europe/Dublin")
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
QUIET_FALLBACK = time(20, 0)
SMS_MAX_LEN = 160
MIN_PHONE_DIGITS = 7
SIGNATURE_DEFAULT = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")
_OFFSETS = (FIRST_REMINDER_OFFSET, SECOND_REMINDER_OFFSET)


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _opted_out(value) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1")
    if isinstance(value, int) and not isinstance(value, bool):
        return value == 1
    return False


def _usable_phone(phone) -> bool:
    if not isinstance(phone, str) or not phone.strip():
        return False
    return sum(c.isdigit() for c in phone) >= MIN_PHONE_DIGITS


def _usable_email(email) -> bool:
    return isinstance(email, str) and bool(_EMAIL_RE.match(email.strip()))


def _choose_channel(appt: dict):
    if _usable_phone(appt.get("phone")) and not _opted_out(appt.get("optout_sms_v2")):
        return "sms"
    if _usable_email(appt.get("email")):
        return "email"
    return None


def _clean_name(name) -> str:
    if not isinstance(name, str):
        return ""
    name = _nfc(name)
    name = "".join(" " if c.isspace() else c
                   for c in name if c.isspace() or unicodedata.category(c)[0] != "C")
    return _nfc(" ".join(name.split()))


def _signature(country) -> str:
    if isinstance(country, str) and country.strip().upper() == "PL":
        return _nfc(SIGNATURE_PL)
    return _nfc(SIGNATURE_DEFAULT)


def _trim_tail(s: str) -> str:
    while s and (s[-1].isspace() or unicodedata.combining(s[-1])):
        s = s[:-1]
    return s


def _truncate(name: str, limit: int) -> str:
    """Truncate to at most `limit` chars incl. ellipsis, not splitting sequences."""
    if len(name) <= limit:
        return name
    if limit < 2:
        return ""
    n = limit - 1
    while n > 0 and unicodedata.combining(name[n]):
        n -= 1
    head = _trim_tail(name[:n])
    return _nfc(head + "\u2026") if head else ""


def _sms_text(name: str, date: str, hhmm: str, sig: str) -> str:
    tail = f", reminder: your Brennan Opticians appointment is on {date} at {hhmm}. {sig}"
    if name:
        full = f"Hi {name}{tail}"
        if len(full) <= SMS_MAX_LEN:
            return full
        room = SMS_MAX_LEN - len(f"Hi {tail}")
        short = _truncate(name, room)
        if short:
            return f"Hi {short}{tail}"
    generic = f"Hi, your Brennan Opticians appointment is on {date} at {hhmm}. {sig}"
    if len(generic) <= SMS_MAX_LEN:
        return generic
    return f"{date} {hhmm} {sig}"[:SMS_MAX_LEN]


def _email_text(name: str, date: str, hhmm: str, sig: str) -> str:
    greeting = f"Hi {name}," if name else "Hello,"
    return (f"{greeting}\n\nThis is a reminder that your Brennan Opticians "
            f"appointment is on {date} at {hhmm}.\n\nKind regards,\n{sig}")


def _build_text(channel: str, appt: dict, start: datetime) -> str:
    local = start.astimezone(LOCAL_TZ)
    date, hhmm = local.strftime("%d/%m/%Y"), local.strftime("%H:%M")
    name, sig = _clean_name(appt.get("customer_name")), _signature(appt.get("country"))
    if channel == "sms":
        return _nfc(_sms_text(name, date, hhmm, sig))
    return _nfc(_email_text(name, date, hhmm, sig))


def _apply_quiet_hours(t: datetime) -> datetime:
    """Move a quiet-hours time back to the preceding 20:00 Dublin local time."""
    local = t.astimezone(LOCAL_TZ)
    lt = local.time()
    if QUIET_END <= lt < QUIET_START:
        return t
    day = local.date()
    if lt < QUIET_END:
        day = day - timedelta(days=1)
    wall = datetime.combine(day, QUIET_FALLBACK).replace(tzinfo=LOCAL_TZ, fold=0)
    return wall.astimezone(timezone.utc)


def _plan_one(appt: dict, now: datetime) -> list[tuple]:
    if not isinstance(appt, dict):
        logger.warning("malformed appointment, skipping")
        return []
    appt_id = appt.get("id")
    start = appt.get("starts_at")
    if appt_id is None or not isinstance(start, datetime) or start.tzinfo is None \
            or start.utcoffset() is None:
        if appt_id is None:
            logger.warning("malformed appointment (no id), skipping")
        else:
            logger.warning("appointment %s: malformed, skipping", appt_id)
        return []
    status = appt.get("status")
    if isinstance(status, str) and status.strip().lower() == "cancelled":
        logger.debug("appointment %s: cancelled, no reminders", appt_id)
        return []
    start_utc = start.astimezone(timezone.utc)
    now_utc = now.astimezone(timezone.utc)
    if start_utc <= now_utc:
        logger.debug("appointment %s: already started, no reminders", appt_id)
        return []
    channel = _choose_channel(appt)
    if channel is None:
        logger.warning("appointment %s: no usable contact channel, skipping", appt_id)
        return []

    times: list[datetime | None] = []
    for idx, offset in enumerate(_OFFSETS):
        t = start_utc - offset
        if t < now_utc:
            if idx == 0:
                t = now_utc
            else:
                logger.debug("appointment %s: reminder %d dropped (past)", appt_id, idx + 1)
                times.append(None)
                continue
        t = _apply_quiet_hours(t)
        if t < now_utc or t >= start_utc:
            logger.debug("appointment %s: reminder %d dropped (quiet hours)", appt_id, idx + 1)
            t = None
        times.append(t)

    if times[0] is not None and times[0] == times[1]:
        logger.debug("appointment %s: duplicate time, keeping 2-hour reminder", appt_id)
        times[0] = None

    text = _build_text(channel, appt, start_utc)
    out = []
    for idx, t in enumerate(times):
        if t is None:
            continue
        logger.info("appointment %s: reminder planned via %s at %s",
                    appt_id, channel, t.isoformat())
        out.append((t, str(appt_id), idx, {
            "appointment_id": appt_id, "channel": channel,
            "send_at": t, "text": text}))
    return out


def plan_reminders(appointments, now: datetime) -> list[dict]:
    """Return reminders sorted by (send_at, str(appointment_id), offset order).

    Does not mutate its input.
    """
    planned: list[tuple] = []
    for appt in appointments or []:
        try:
            planned.extend(_plan_one(appt, now))
        except Exception as exc:  # never log message/repr: may contain PII
            appt_id = appt.get("id") if isinstance(appt, dict) else None
            logger.warning("appointment %s: unexpected error (%s), skipping",
                           appt_id, type(exc).__name__)
    planned.sort(key=lambda p: (p[0], p[1], p[2]))
    return [p[3] for p in planned]