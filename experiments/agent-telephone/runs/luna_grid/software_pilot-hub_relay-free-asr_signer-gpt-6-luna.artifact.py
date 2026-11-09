from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    now_local = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment["status"] == "cancelled":
            continue

        starts_at = appointment["starts_at"].astimezone(_DUBLIN)
        for hours in (48, 2):
            send_at = max(starts_at - timedelta(hours=hours), now_local)

            if send_at.time() >= time(21) or send_at.time() < time(8):
                send_at = send_at.replace(hour=20, minute=0, second=0, microsecond=0)
                if send_at < now_local:
                    send_at += timedelta(days=1)

            channel = (
                "sms"
                if appointment["phone"] and not appointment["optout_sms_v2"]
                else "email"
            )
            date_time = starts_at.strftime("%d %B %Y at %H:%M")
            signature = (
                "Grzegorz Szczepański"
                if appointment["country"] == "PL"
                else "Chevonne Nee Divver"
            )
            name = appointment["customer_name"]

            if channel == "sms":
                prefix = f"Hi {name}, your appointment is on {date_time}. "
                suffix = f" {signature}"
                available = max(0, 160 - len(prefix) - len(suffix))
                text = f"Hi {name[:available]}, your appointment is on {date_time}.{suffix}"
                contact = appointment["phone"]
            else:
                text = f"Hi {name}, your appointment is on {date_time}. {signature}"
                contact = "email address withheld"

            reminder = {
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            }
            reminders.append(reminder)
            _LOG.info(
                "Planned reminder for %s via %s to %s",
                name,
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders