from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

DUBLIN = ZoneInfo("Europe/Dublin")
LOGGER = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    now = now.astimezone(DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment.get("status") == "cancelled":
            continue

        starts_at = appointment.get("datetime", appointment.get("appointment_time"))
        if starts_at is None:
            continue
        starts_at = starts_at.astimezone(DUBLIN)

        phone = appointment.get("phone")
        opted_out = appointment.get("optout_sms_v2") is True
        channel = "sms" if phone and not opted_out else "email"
        contact = phone if channel == "sms" else appointment.get("email")
        recipient = appointment.get("customer_name", "")
        signature = (
            "Grzegorz Szczepański"
            if appointment.get("country") == "PL"
            else "Siobhán Ní Dhuibhir"
        )
        appointment_time = starts_at.strftime("%Y-%m-%d %H:%M")

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            send_at = starts_at - lead
            if send_at < now:
                send_at = now

            local_send = send_at.astimezone(DUBLIN)
            if local_send.hour >= 21 or local_send.hour < 8:
                local_send = (local_send - timedelta(days=1)).replace(
                    hour=20, minute=0, second=0, microsecond=0
                )
                send_at = local_send

            if send_at < now:
                continue

            name = recipient
            text = f"Reminder for {name}: your appointment is {appointment_time}. {signature}"
            if channel == "sms" and len(text) > 160:
                fixed = f"Reminder: appointment {appointment_time}. {signature}"
                available = max(0, 160 - len(fixed))
                text = f"Reminder: appointment {appointment_time}. {name[:available]}{'. ' if available else ''}{signature}"
                if len(text) > 160:
                    text = fixed[:160]

            reminder = {
                "appointment_id": appointment.get("appointment_id", appointment.get("id")),
                "channel": channel,
                "send_at": send_at,
                "text": text,
            }
            reminders.append(reminder)

            logged_contact = contact
            if channel == "email" and contact:
                local_part, separator, domain = contact.partition("@")
                logged_contact = f"{local_part[:1]}***@{domain}" if separator else "***"
            LOGGER.info(
                "Reminder planned for %s via %s contact=%s",
                recipient,
                channel,
                logged_contact or "unavailable",
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders