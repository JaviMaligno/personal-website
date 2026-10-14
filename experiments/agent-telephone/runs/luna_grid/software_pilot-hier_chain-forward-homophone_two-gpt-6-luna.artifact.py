from datetime import datetime, timedelta
from logging import getLogger
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = getLogger(__name__)
_SIGNATURE = "Siobhán Ní Dhuibhir"
_POLISH_SIGNATURE = "Grzegorz Szczepański"


def _aware_datetime(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    if not isinstance(value, datetime) or value.tzinfo is None:
        return None
    try:
        if value.utcoffset() is None:
            return None
        return value.astimezone(_DUBLIN)
    except (OverflowError, ValueError):
        return None


def _message(name, starts_at, signature, sms):
    date = starts_at.strftime("%Y-%m-%d")
    time = starts_at.strftime("%H:%M")
    prefix = f"Hi {name}, " if name else ""
    body = f"{prefix}reminder: your appointment is on {date} at {time}. {signature}"
    if sms and len(body) > 160:
        fixed = f"Hi , reminder: your appointment is on {date} at {time}. {signature}"
        available = max(0, 160 - len(fixed))
        body = f"Hi {name[:available]}, reminder: your appointment is on {date} at {time}. {signature}"
    return body


def plan_reminders(appointments, now):
    """Return appointment reminders scheduled in Europe/Dublin time."""
    current = _aware_datetime(now)
    if current is None:
        return []

    try:
        entries = iter(appointments)
    except TypeError:
        return []

    reminders = []
    for appointment in entries:
        if not isinstance(appointment, dict):
            continue
        starts_at = _aware_datetime(appointment.get("starts_at"))
        if starts_at is None:
            continue
        if str(appointment.get("status", "")).strip().lower() == "cancelled":
            continue

        phone = appointment.get("phone")
        has_phone = isinstance(phone, str) and bool(phone.strip())
        sms = has_phone and appointment.get("optout_sms_v2") is not True
        channel = "sms" if sms else "email"
        signature = (
            _POLISH_SIGNATURE
            if str(appointment.get("country", "")).strip().upper() == "PL"
            else _SIGNATURE
        )
        raw_name = appointment.get("customer_name")
        name = raw_name.strip() if isinstance(raw_name, str) else ""
        appointment_id = appointment.get("id")

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            try:
                scheduled = starts_at - lead
            except OverflowError:
                continue
            if lead == timedelta(hours=48) and scheduled < current:
                scheduled = current
            if scheduled.hour >= 21 or scheduled.hour < 8:
                try:
                    scheduled = scheduled.replace(hour=20, minute=0, second=0, microsecond=0)
                except (OverflowError, ValueError):
                    continue
            if scheduled < current:
                continue

            reminders.append({
                "appointment_id": appointment_id,
                "channel": channel,
                "send_at": scheduled,
                "text": _message(name, starts_at, signature, channel == "sms"),
            })
            recipient = str(appointment_id).replace("\n", " ") if appointment_id is not None else "unknown"
            contact = "phone on file" if channel == "sms" else "email on file"
            _LOG.info("Reminder planned for appointment %s via %s to %s", recipient, channel, contact)

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders