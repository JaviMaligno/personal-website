from datetime import datetime, timedelta
from logging import getLogger
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = getLogger(__name__)
_SIGNATURE = "Siobhán Ní Dhuibhir"
_POLISH_SIGNATURE = "Grzegorz Szczepański"


def _quiet_adjust(send_at):
    local = send_at.astimezone(_DUBLIN)
    if local.hour < 8:
        return (local - timedelta(days=1)).replace(
            hour=20, minute=0, second=0, microsecond=0
        )
    if local.hour >= 21:
        return local.replace(hour=20, minute=0, second=0, microsecond=0)
    return local


def _message(appointment, sms):
    starts_at = appointment["starts_at"].astimezone(_DUBLIN)
    date = starts_at.strftime("%d %B %Y")
    time = starts_at.strftime("%H:%M")
    signature = (
        _POLISH_SIGNATURE if appointment.get("country") == "PL" else _SIGNATURE
    )
    name = str(appointment.get("customer_name") or "").strip()
    greeting = f"Dear {name}, " if name else ""
    message = f"{greeting}your appointment is on {date} at {time}. {signature}"

    if sms and len(message) > 160:
        fixed = f"your appointment is on {date} at {time}. {signature}"
        prefix = "Dear "
        suffix = ", " if name else ""
        available = 160 - len(fixed) - len(prefix) - len(suffix)
        shortened = name[:max(0, available)].rstrip()
        greeting = f"Dear {shortened}, " if shortened else ""
        message = f"{greeting}{fixed}"
        if len(message) > 160:
            message = fixed
    return message


def plan_reminders(appointments, now):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        starts_at = appointment["starts_at"]
        if starts_at.tzinfo is None or starts_at.utcoffset() is None:
            raise ValueError("starts_at must be timezone-aware")
        if str(appointment.get("status", "")).lower() == "cancelled":
            continue

        phone = appointment.get("phone")
        email = appointment.get("email")
        if phone and appointment.get("optout_sms_v2") is True:
            channel, contact = "sms", phone
        elif email:
            channel, contact = "email", email
        else:
            continue

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            calculated = starts_at.astimezone(_DUBLIN) - offset
            if offset == timedelta(hours=48) and calculated < now:
                calculated = now
            elif calculated < now:
                continue

            send_at = _quiet_adjust(calculated)
            if send_at < now:
                continue

            reminders.append({
                "appointment_id": appointment.get("id"),
                "channel": channel,
                "send_at": send_at,
                "text": _message(appointment, channel == "sms"),
            })
            recipient = appointment.get("customer_name") or "customer"
            logged_contact = str(contact) if channel == "sms" else "address redacted"
            _LOG.info(
                "Reminder for %s via %s to %s",
                recipient,
                channel,
                logged_contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders