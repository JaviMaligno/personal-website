from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

DUBLIN = ZoneInfo("Europe/Dublin")
SIGNATURE = "Grzegorz Szczepański"
DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"


def plan_reminders(appointments, now):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    current = now.astimezone(DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment.get("status") == "cancelled":
            continue

        starts_at = appointment["starts_at"]
        if starts_at.tzinfo is None or starts_at.utcoffset() is None:
            raise ValueError("appointment starts_at must be timezone-aware")

        start_local = starts_at.astimezone(DUBLIN)
        if start_local <= current:
            continue

        phone = appointment.get("phone")
        use_sms = bool(phone) and not appointment.get("optout_sms_v2", False)
        channel = "sms" if use_sms else "email"

        name = str(appointment.get("customer_name") or "")
        signature = (
            SIGNATURE
            if appointment.get("country") == "PL"
            else DEFAULT_SIGNATURE
        )
        date_text = start_local.strftime("%Y-%m-%d")
        time_text = start_local.strftime("%H:%M")
        message_tail = f"Your appointment is on {date_text} at {time_text}. {signature}"
        if name:
            message_tail = f"Hello {name}, your appointment is on {date_text} at {time_text}. {signature}"

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            target = starts_at - lead
            if target.astimezone(DUBLIN) < current:
                target = current

            send_local = target.astimezone(DUBLIN)
            if send_local.hour >= 21 or send_local.hour < 8:
                previous_evening = send_local.replace(
                    hour=20, minute=0, second=0, microsecond=0
                )
                send_local = (
                    previous_evening
                    if previous_evening >= current
                    else current.replace(hour=8, minute=0, second=0, microsecond=0)
                )
                if send_local < current:
                    send_local = current

            text = message_tail
            if use_sms and len(text) > 160:
                prefix = f"Hello "
                suffix = f", your appointment is on {date_text} at {time_text}. {signature}"
                available = max(0, 160 - len(prefix) - len(suffix))
                short_name = name[:available]
                text = f"{prefix}{short_name}{suffix}" if short_name else (
                    f"Appointment on {date_text} at {time_text}. {signature}"
                )

            reminders.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": send_local,
                    "text": text,
                }
            )
            logging.info("Planned reminder via %s using contact on file", channel)

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders