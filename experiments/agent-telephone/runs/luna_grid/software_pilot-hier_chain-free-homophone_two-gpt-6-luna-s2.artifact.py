"""Plan appointment reminders.

Expected appointment fields:
- appointment_id: required, non-empty identifier.
- starts_at: required datetime or ISO-8601 string. Naive values are treated as
  Europe/Dublin local time; aware values are converted to that timezone.
- cancelled: optional truthy flag; cancelled appointments are skipped.
- phone, optout_sms_v2, email, country, name: optional delivery and message
  details. SMS requires a non-empty phone and optout_sms_v2 is exactly False;
  otherwise email is selected.

Invalid appointments are skipped. A naive `now` raises ValueError. Quiet-hour
adjustments use Europe/Dublin local dates: times from 21:00 through 07:59:59
move to 20:00 on the preceding local date. Adjusted times earlier than `now`
are clamped to `now`. SMS names are shortened as needed; the final fallback
omits the name while retaining the appointment date, time, and signature.
"""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def _parse_start(value):
    if isinstance(value, datetime):
        start = value
    elif isinstance(value, str):
        try:
            start = datetime.fromisoformat(value)
        except ValueError:
            return None
    else:
        return None

    if start.tzinfo is None or start.utcoffset() is None:
        return start.replace(tzinfo=_DUBLIN)
    return start.astimezone(_DUBLIN)


def _has_value(value):
    return value is not None and bool(str(value).strip())


def _message(name, start, country, sms):
    signature = (
        "Grzegorz Szczepański" if country == "PL" else "Siobhán Ní Dhuibhir"
    )
    date = start.strftime("%d/%m/%Y")
    clock = start.strftime("%H:%M")
    prefix = f"Appointment on {date} at {clock}"
    if not sms:
        return f"Reminder for {name}: {prefix}. {signature}" if name else (
            f"Reminder: {prefix}. {signature}"
        )

    if name:
        for length in range(len(name), 0, -1):
            candidate = f"Reminder for {name[:length]}: {prefix}. {signature}"
            if len(candidate) <= 160:
                return candidate
    return f"Reminder: {prefix}. {signature}"


def plan_reminders(appointments, now):
    """Return sorted reminder dictionaries for valid, non-cancelled appointments."""
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_dublin = now.astimezone(_DUBLIN)
    reminders = []

    try:
        iterator = iter(appointments)
    except TypeError:
        return reminders

    for appointment in iterator:
        if not isinstance(appointment, dict) or appointment.get("cancelled"):
            continue

        appointment_id = appointment.get("appointment_id")
        start = _parse_start(appointment.get("starts_at"))
        if not _has_value(appointment_id) or start is None:
            continue

        phone = appointment.get("phone")
        sms = _has_value(phone) and appointment.get("optout_sms_v2") is False
        channel = "sms" if sms else "email"
        contact = str(phone).strip() if sms else (
            "email contact configured" if _has_value(appointment.get("email"))
            else "email contact unavailable"
        )
        name_value = appointment.get("name")
        name = str(name_value).strip() if _has_value(name_value) else ""
        text = _message(name, start, appointment.get("country"), sms)

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            proposed = start - offset
            if offset == timedelta(hours=2) and proposed <= now_dublin:
                continue
            if offset == timedelta(hours=48) and proposed < now_dublin:
                proposed = now_dublin

            if time(21, 0) <= proposed.timetz().replace(tzinfo=None) or (
                proposed.timetz().replace(tzinfo=None) < time(8, 0)
            ):
                preceding_date = proposed.date() - timedelta(days=1)
                proposed = datetime.combine(
                    preceding_date, time(20, 0), tzinfo=_DUBLIN
                )

            if proposed < now_dublin:
                proposed = now_dublin

            reminders.append({
                "appointment_id": appointment_id,
                "channel": channel,
                "send_at": proposed,
                "text": text,
            })
            _LOG.info(
                "Planned reminder for %s via %s to %s",
                name or str(appointment_id),
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders