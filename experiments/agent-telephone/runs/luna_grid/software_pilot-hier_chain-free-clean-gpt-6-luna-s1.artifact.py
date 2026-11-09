from datetime import datetime, time, timedelta
import logging
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    now = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment.get("status") == "cancelled":
            continue

        starts_at = appointment["starts_at"].astimezone(_DUBLIN)
        customer = appointment.get("customer") or {}
        name = appointment.get("customer_name", customer.get("name", ""))
        country = appointment.get("country", customer.get("country"))
        signature = "Grzegorz Szczepański" if country == "PL" else "Siobhán Ní Dhuibhir"
        phone = appointment.get("phone", customer.get("phone"))
        channel = "sms" if phone and not appointment.get("optout_sms_v2", False) else "email"
        contact = phone if channel == "sms" else "<redacted>"
        date = starts_at.strftime("%d/%m/%Y")
        clock = starts_at.strftime("%H:%M")

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            send_at = starts_at - lead
            if send_at.time() >= time(21) or send_at.time() < time(8):
                send_at = send_at.replace(hour=20, minute=0, second=0, microsecond=0)
            if send_at < now:
                send_at = now

            text = f"Reminder: {name}, your appointment is {date} at {clock}. {signature}"
            if channel == "sms":
                fixed = f"Reminder: , your appointment is {date} at {clock}. {signature}"
                text = f"Reminder: {name[:max(0, 160 - len(fixed))]}, your appointment is {date} at {clock}. {signature}"
                text = text[:160]

            reminders.append({
                "appointment_id": appointment["appointment_id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            _LOG.info(
                "Reminder for %s via %s to %s",
                name or appointment["appointment_id"],
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders