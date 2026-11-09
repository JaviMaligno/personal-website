from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

__all__ = ["plan_reminders"]

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)
_SIGNATURE_IE = "Siobhán Ní Dhuibhir"
_SIGNATURE_PL = "Grzegorz Szczepański"


def _localize(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetimes must be timezone-aware")
    return value.astimezone(_DUBLIN)


def _message(name, appointment, signature, sms):
    date = appointment.strftime("%Y-%m-%d")
    clock = appointment.strftime("%H:%M")
    prefix = f"Reminder: {name}, your appointment is on " if name else "Reminder: Your appointment is on "
    required = f"{date} at {clock}. {signature}"
    message = prefix + required

    if sms and len(message) > 160:
        available = 160 - len("Reminder: , your appointment is on ") - len(required)
        if available >= 0:
            shortened = name[:available].rstrip()
            message = (f"Reminder: {shortened}, your appointment is on " if shortened
                       else "Reminder: Your appointment is on ") + required
        if len(message) > 160:
            message = required
    return message


def plan_reminders(appointments, now):
    """Return chronologically ordered appointment reminder dictionaries."""
    now = _localize(now)
    reminders = []

    for appointment in appointments:
        if appointment.get("status") == "cancelled":
            continue

        starts_at = _localize(appointment["starts_at"])
        phone = appointment.get("phone")
        sms = bool(phone) and not appointment.get("optout_sms_v2", False)
        channel = "sms" if sms else "email"
        signature = _SIGNATURE_PL if appointment.get("country") == "PL" else _SIGNATURE_IE
        name = str(appointment.get("customer_name", ""))

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            point = starts_at - offset
            if offset == timedelta(hours=2) and point < now:
                continue
            send_at = now if offset == timedelta(hours=48) and point < now else point

            if send_at.time() >= time(21) or send_at.time() < time(8):
                send_at = (send_at - timedelta(days=1)).replace(
                    hour=20, minute=0, second=0, microsecond=0
                )
            if send_at < now:
                continue

            text = _message(name, starts_at, signature, sms)
            reminders.append({
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })

            recipient = name or "customer"
            contact = f"phone {phone}" if sms else "email contact withheld"
            _LOG.info("Reminder recipient=%s channel=%s contact=%s", recipient, channel, contact)

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders