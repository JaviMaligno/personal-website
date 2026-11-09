from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def _as_datetime(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Appointment times and now must be timezone-aware")
    return value.astimezone(_DUBLIN)


def _quiet_adjust(send_at, now):
    if time(21) <= send_at.timetz().replace(tzinfo=None) or send_at.hour < 8:
        evening = datetime.combine(send_at.date(), time(20), _DUBLIN)
        if evening < now:
            evening += timedelta(days=1)
        return evening
    return send_at


def plan_reminders(appointments, now):
    now = _as_datetime(now)
    reminders = []

    for appointment in appointments:
        if appointment.get("cancelled"):
            continue

        starts_at = _as_datetime(appointment["starts_at"])
        channel = (
            "sms"
            if appointment.get("phone_number") and not appointment.get("optout_sms_v2")
            else "email"
        )
        contact = appointment.get("phone_number") if channel == "sms" else "email contact withheld"
        recipient = appointment.get("customer_name") or appointment.get("appointment_id")
        signature = (
            "Grzegorz Szczepański,"
            if appointment.get("country") == "PL"
            else "Siobhán Ní Dhuibhir,"
        )
        date_time = f"{starts_at:%Y-%m-%d} at {starts_at:%H:%M}"
        name = appointment.get("customer_name", "")
        for hours in (48, 2):
            send_at = starts_at - timedelta(hours=hours)
            if hours == 2 and send_at < now:
                continue
            if hours == 48 and send_at < now:
                send_at = now
            send_at = _quiet_adjust(send_at, now)
            prefix = f"Reminder: {name}, your appointment is {date_time}. "
            text = f"{prefix}{signature}"
            if channel == "sms" and len(text) > 160:
                available = 160 - len(f"Reminder: , your appointment is {date_time}. {signature}")
                short_name = name[:max(0, available)]
                text = f"Reminder: {short_name}, your appointment is {date_time}. {signature}"
            reminders.append({
                "appointment_id": appointment["appointment_id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            _LOG.info(
                "Reminder recipient=%s channel=%s contact=%s",
                recipient,
                channel,
                contact,
            )

    return sorted(reminders, key=lambda reminder: reminder["send_at"])