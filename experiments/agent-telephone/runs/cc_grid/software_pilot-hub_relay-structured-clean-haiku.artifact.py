"""Appointment reminder planner for Brennan Opticians.

Public entry point: plan_reminders(appointments, now).

Deviations and open points for the client (open spec questions resolved with the R19-R28 defaults):
- R19: each send time is first clamped to now, then moved by the quiet-hours rule. If the moved time is still before now, it goes forward to the next 08:00 Europe/Dublin. With now at 22:00 Dublin, the 48h reminder therefore goes to 08:00 the next day, not to now as R6 literally reads.
- R20: the 2h reminder is dropped if its point is at or before now. Appointments starting at or before now produce nothing.
- Not specified and not handled: a reminder moved forward by R19 can be scheduled after starts_at (for example, an appointment in one hour, planned at 22:00). These are not dropped. Client to decide.
- R23: an SMS still over 160 characters after the name is dropped is emitted anyway and logged at WARNING with the appointment id only.
- Characters such as a-acute and i-acute in the signature are outside GSM-7. A gateway may split such SMS into shorter segments even when the text is within 160 characters.
- R4 has no recipient field, so the sender cannot address a message from this output. Client to decide how recipients are linked.
- The house rule to log the contact for each reminder conflicts with R13 (no email, phone or name in logs). Logs carry appointment_id and channel only.
- Appointment ids must be non-empty strings so that R16 and R26 sorting is well defined.
- The test file is not part of this output and has not been run.
"""

import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
_SMS_MAX = 160
_REQUIRED = (
    "id", "customer_name", "email", "phone",
    "country", "status", "starts_at", "optout_sms_v2",
)
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _is_aware(dt):
    return isinstance(dt, datetime) and dt.utcoffset() is not None


def _validate(appointments, now):
    if not _is_aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    if not isinstance(appointments, (list, tuple)):
        raise ValueError("appointments must be a list")
    seen = set()
    for i, a in enumerate(appointments):
        where = f"appointments[{i}]"
        if not isinstance(a, dict):
            raise ValueError(f"{where}: not a dict")
        for key in _REQUIRED:
            if key not in a:
                raise ValueError(f"{where}: missing key {key!r}")
        aid = a["id"]
        if not isinstance(aid, str) or not aid:
            raise ValueError(f"{where}: id must be a non-empty string")
        if aid in seen:
            raise ValueError(f"{where}: duplicate id")
        seen.add(aid)
        for key in ("customer_name", "email", "phone", "country"):
            if a[key] is not None and not isinstance(a[key], str):
                raise ValueError(f"{where}: {key} must be a string or None")
        if not isinstance(a["status"], str):
            raise ValueError(f"{where}: status must be a string")
        if not _is_aware(a["starts_at"]):
            raise ValueError(f"{where}: starts_at must be a timezone-aware datetime")
        if not isinstance(a["optout_sms_v2"], bool):
            raise ValueError(f"{where}: optout_sms_v2 must be a bool")


def _quiet_adjust(t):
    """Apply R11 to a UTC-aware time. Returns UTC-aware time."""
    loc = t.astimezone(DUBLIN)
    tm = loc.time()
    if time(0, 0) <= tm < time(8, 0):
        day = loc.date() - timedelta(days=1)
    elif tm >= time(21, 0):
        day = loc.date()
    else:
        return t
    return datetime.combine(day, time(20, 0), tzinfo=DUBLIN).astimezone(UTC)


def _next_0800(now):
    """First 08:00 Europe/Dublin strictly after now, as UTC."""
    loc = now.astimezone(DUBLIN)
    day = loc.date() if loc.time() < time(8, 0) else loc.date() + timedelta(days=1)
    return datetime.combine(day, time(8, 0), tzinfo=DUBLIN).astimezone(UTC)


def _send_time(candidate, now):
    """R6/R7 clamp, then R11 quiet hours, then R19 forward move."""
    t = _quiet_adjust(max(candidate, now))
    if t < now:
        t = _next_0800(now)
    return t


def _fmt_date(d):
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"


def _sms_text(name, date_s, time_s, sig):
    """Returns (text, still_too_long). Only the name is shortened (R9, R23)."""
    prefixes = []
    if name:
        prefixes.append(f"Hi {name}, ")
        first = name.split()[0]
        if first != name:
            prefixes.append(f"Hi {first}, ")
    prefixes.append("")
    text = ""
    for p in prefixes:
        text = f"{p}Brennan Opticians reminder: appointment on {date_s} at {time_s}. {sig}"
        if len(text) <= _SMS_MAX:
            return text, False
    return text, True


def _email_text(name, date_s, time_s, sig):
    greet = f"Hello {name}," if name else "Hello,"
    return (
        f"{greet}\n\n"
        f"This is a reminder of your appointment at Brennan Opticians "
        f"on {date_s} at {time_s} (Dublin time).\n\n"
        f"Kind regards,\n{sig}"
    )


def plan_reminders(appointments, now):
    _validate(appointments, now)
    now = now.astimezone(UTC)

    rows = []
    flagged = []
    for i, a in enumerate(appointments):
        if a["status"] == "cancelled":
            continue
        starts = a["starts_at"].astimezone(UTC)
        if starts <= now:
            continue

        aid = a["id"]
        phone = (a["phone"] or "").strip()
        email = (a["email"] or "").strip()
        channel = "sms" if phone and not a["optout_sms_v2"] else "email"
        if channel == "email" and not email:
            raise ValueError(f"appointments[{i}]: no email address for email reminder")

        local = starts.astimezone(DUBLIN)
        date_s = _fmt_date(local.date())
        time_s = f"{local.hour:02d}:{local.minute:02d}"
        name = (a["customer_name"] or "").strip()
        sig = SIG_PL if a["country"] == "PL" else SIG_DEFAULT

        if channel == "sms":
            text, too_long = _sms_text(name, date_s, time_s, sig)
            if too_long:
                flagged.append(aid)
        else:
            text = _email_text(name, date_s, time_s, sig)

        points = [starts - timedelta(hours=48)]
        two_hour = starts - timedelta(hours=2)
        if two_hour > now:
            points.append(two_hour)

        for point in points:
            rows.append({
                "appointment_id": aid,
                "channel": channel,
                "send_at": _send_time(point, now),
                "text": text,
            })

    rows.sort(key=lambda r: (
        r["send_at"],
        r["appointment_id"],
        0 if r["channel"] == "email" else 1,
    ))

    for aid in flagged:
        logger.warning("sms for appointment_id=%s still exceeds %d characters after shortening",
                       aid, _SMS_MAX)
    for r in rows:
        logger.info("planned reminder: appointment_id=%s channel=%s send_at=%s",
                    r["appointment_id"], r["channel"], r["send_at"].isoformat())

    return rows