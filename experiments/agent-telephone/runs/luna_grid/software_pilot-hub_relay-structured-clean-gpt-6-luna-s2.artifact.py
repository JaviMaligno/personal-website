from datetime import datetime, time, timedelta
import logging
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
SIGNATURES = {
    "PL": "Grzegorz Szczepański",
}
DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"


def plan_reminders(appointments, now):
    now_local = now.astimezone(DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment["status"] == "cancelled":
            continue

        starts_at = appointment["starts_at"].astimezone(DUBLIN)
        signature = SIGNATURES.get(appointment["country"], DEFAULT_SIGNATURE)
        opted_out = appointment["optout_sms_v2"]
        channel = "sms" if appointment["phone"] and not opted_out else "email"
        contact = appointment["phone"] if channel == "sms" else "[address redacted]"
        name = appointment["customer_name"] or ""
        date_time = starts_at.strftime("%Y-%m-%d at %H:%M")

        text = f"Hi {name}, reminder: your appointment is on {date_time}. {signature}"
        if channel == "sms" and len(text) > 160:
            suffix = f", reminder: your appointment is on {date_time}. {signature}"
            text = f"{name[:max(0, 160 - len(suffix))]}{suffix}"

        for lead_time in (timedelta(hours=48), timedelta(hours=2)):
            send_at = starts_at - lead_time
            if send_at < now_local:
                send_at = now_local

            if time(21, 0) <= send_at.timetz().replace(tzinfo=None) or send_at.time() < time(8, 0):
                send_at = datetime.combine(send_at.date() - timedelta(days=1), time(20, 0), DUBLIN)
                if send_at < now_local:
                    send_at = datetime.combine(now_local.date(), time(20, 0), DUBLIN)
                    if send_at < now_local:
                        send_at += timedelta(days=1)

            reminder = {
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            }
            reminders.append(reminder)
            logging.info(
                "Reminder planned for %s via %s to %s",
                name,
                channel,
                contact,
            )

    return sorted(reminders, key=lambda reminder: reminder["send_at"])