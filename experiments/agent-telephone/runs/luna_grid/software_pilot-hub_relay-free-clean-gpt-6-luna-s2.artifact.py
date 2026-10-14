from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    """Return scheduled appointment reminders as dictionaries."""
    if isinstance(now, str):
        now = datetime.fromisoformat(now)
    if now.tzinfo is None:
        now = now.replace(tzinfo=_DUBLIN)
    now = now.astimezone(_DUBLIN)

    reminders = []
    for appointment in appointments:
        if appointment.get("cancelled"):
            continue

        starts_at = appointment["starts_at"]
        if isinstance(starts_at, str):
            starts_at = datetime.fromisoformat(starts_at)
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=_DUBLIN)
        starts_at = starts_at.astimezone(_DUBLIN)

        phone = appointment.get("phone")
        channel = (
            "sms"
            if phone and not appointment.get("optout_sms_v2", False)
            else "email"
        )
        contact = phone if channel == "sms" else "email"
        name = str(appointment.get("customer_name") or "")
        signature = (
            "Grzegorz Szczepański"
            if appointment.get("country") == "PL"
            else "Siobhán Ní Dhuibhir"
        )
        date = starts_at.strftime("%Y-%m-%d")
        time = starts_at.strftime("%H:%M")

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            send_at = starts_at - lead
            if send_at < now:
                send_at = now
            if 21 <= send_at.hour or send_at.hour < 8:
                day = send_at.date()
                if send_at.hour < 8:
                    day -= timedelta(days=1)
                send_at = datetime.combine(day, datetime.min.time(), _DUBLIN).replace(
                    hour=20
                )

            text = f"Reminder: {name}, your appointment is on {date} at {time}. {signature}"
            if channel == "sms" and len(text) > 160:
                fixed = f"Reminder: , your appointment is on {date} at {time}. {signature}"
                name_limit = max(0, 160 - len(fixed))
                text = f"Reminder: {name[:name_limit]}, your appointment is on {date} at {time}. {signature}"

            reminder = {
                "appointment_id": appointment["appointment_id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            }
            reminders.append(reminder)
            _LOG.info(
                "Planned reminder for %s via %s to %s",
                name,
                channel,
                contact if channel == "sms" else "email",
            )

    return sorted(reminders, key=lambda reminder: reminder["send_at"])