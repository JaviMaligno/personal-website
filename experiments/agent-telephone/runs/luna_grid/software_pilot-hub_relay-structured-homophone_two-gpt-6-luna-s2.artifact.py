from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging


_DUBLIN = ZoneInfo("Europe/Dublin")
_SIGNATURE_DEFAULT = "Siobhán Ní Dhuibhir"
_SIGNATURE_PL = "Grzegorz Szczepański"


def _quiet_hours_adjust(send_at):
    local = send_at.astimezone(_DUBLIN)
    if local.time() >= time(21) or local.time() < time(8):
        day = local.date() if local.time() >= time(21) else local.date() - timedelta(days=1)
        return datetime.combine(day, time(20), tzinfo=_DUBLIN)
    return local


def plan_reminders(appointments, now):
    now = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment["status"] == "cancelled":
            continue

        starts_at = appointment["starts_at"].astimezone(_DUBLIN)
        channel = "sms" if appointment["phone"] and not appointment["optout_sms_v2"] else "email"
        contact = appointment["phone"] if channel == "sms" else "[email withheld]"
        signature = _SIGNATURE_PL if appointment["country"] == "PL" else _SIGNATURE_DEFAULT
        date_text = starts_at.strftime("%Y-%m-%d")
        time_text = starts_at.strftime("%H:%M")

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            send_at = starts_at - offset
            if offset == timedelta(hours=48) and send_at < now:
                send_at = now
            send_at = _quiet_hours_adjust(send_at)

            if send_at < now:
                continue

            name = str(appointment["customer_name"])
            text = f"Hi {name}, your appointment is on {date_text} at {time_text}. {signature}"
            if channel == "sms" and len(text) > 160:
                fixed = f"Hi , your appointment is on {date_text} at {time_text}. {signature}"
                name_limit = max(0, 160 - len(fixed))
                text = f"Hi {name[:name_limit]}, your appointment is on {date_text} at {time_text}. {signature}"

            reminders.append({
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            logging.info(
                "Reminder planned for %s via %s to %s",
                name,
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders