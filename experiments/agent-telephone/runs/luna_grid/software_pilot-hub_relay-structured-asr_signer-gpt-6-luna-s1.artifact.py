from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging


DUBLIN = ZoneInfo("Europe/Dublin")
SIGNATURE = "Chevonne Nee Divver"
POLISH_SIGNATURE = "Grzegorz Szczepański"
logger = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    now_local = now.astimezone(DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment["status"] == "cancelled":
            continue

        channel = (
            "sms"
            if appointment.get("phone") and not appointment["optout_sms_v2"]
            else "email"
        )
        contact = appointment.get("phone") if channel == "sms" else None
        signature = (
            POLISH_SIGNATURE if appointment["country"] == "PL" else SIGNATURE
        )
        starts_at = appointment["starts_at"].astimezone(DUBLIN)
        date_text = starts_at.strftime("%d %B %Y")
        time_text = starts_at.strftime("%H:%M")

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            send_at = starts_at - lead
            if lead == timedelta(hours=48) and send_at < now_local:
                send_at = now_local
            elif send_at < now_local:
                continue

            if send_at.time() < time(8) or send_at.time() >= time(21):
                send_at = send_at.replace(
                    hour=20, minute=0, second=0, microsecond=0
                )
                if send_at.time() >= time(21):
                    send_at -= timedelta(days=1)
                if send_at < now_local:
                    continue

            name = appointment["customer_name"]
            text = (
                f"Hi {name}, your appointment is on {date_text} at "
                f"{time_text}. {signature}"
            )
            if channel == "sms" and len(text) > 160:
                fixed = (
                    f"Hi , your appointment is on {date_text} at "
                    f"{time_text}. {signature}"
                )
                name = name[: max(0, 160 - len(fixed))]
                text = (
                    f"Hi {name}, your appointment is on {date_text} at "
                    f"{time_text}. {signature}"
                )

            reminders.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                    "_name": appointment["customer_name"],
                    "_contact": contact,
                }
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    for reminder in reminders:
        contact = reminder.pop("_contact")
        name = reminder.pop("_name")
        if reminder["channel"] == "sms":
            digits = "".join(char for char in str(contact) if char.isdigit())
            masked_contact = f"***{digits[-2:]}" if digits else "number withheld"
        else:
            masked_contact = "address withheld"
        logger.info(
            "Reminder to %s via %s (%s)",
            name,
            reminder["channel"],
            masked_contact,
        )

    return reminders