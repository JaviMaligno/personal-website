from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_SIGNATURE = "Siobhán Ní Dhuibhir"


def plan_reminders(appointments, now):
    """Return appointment reminders scheduled at or after now."""
    now_utc = now.astimezone(timezone.utc)
    reminders = []

    for appointment in appointments:
        if str(appointment.get("status", "")).casefold() == "cancelled":
            continue

        opted_out = bool(appointment.get("optout_sms_v2"))
        phone = appointment.get("phone")
        email = appointment.get("email")

        if opted_out:
            continue
        if phone:
            channel, contact = "sms", str(phone)
        elif email:
            channel, contact = "email", "address withheld"
        else:
            continue

        starts_at = appointment["starts_at"].astimezone(_DUBLIN)
        signature = (
            "Grzegorz Szczepański"
            if appointment.get("country") == "PL"
            else _SIGNATURE
        )
        date = starts_at.strftime("%Y-%m-%d")
        time = starts_at.strftime("%H:%M")
        name = str(appointment.get("customer_name") or "")
        text = f"Your appointment is on {date} at {time}. {name}. {signature}"

        if channel == "sms" and len(text) > 160:
            fixed = f"Your appointment is on {date} at {time}. . {signature}"
            name = name[:max(0, 160 - len(fixed))]
            text = f"Your appointment is on {date} at {time}. {name}. {signature}"

        start_utc = starts_at.astimezone(timezone.utc)
        for hours in (48, 2):
            target_utc = start_utc - timedelta(hours=hours)
            if target_utc < now_utc:
                target_utc = now_utc

            send_at = target_utc.astimezone(_DUBLIN)
            if send_at.hour >= 21 or send_at.hour < 8:
                send_at = send_at.replace(
                    hour=20, minute=0, second=0, microsecond=0
                ) - timedelta(days=1)

            if send_at.astimezone(timezone.utc) < now_utc:
                send_at = now.astimezone(_DUBLIN)

            reminder = {
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            }
            reminders.append(reminder)
            logging.info(
                "Planned reminder for %s via %s to %s",
                name or "customer",
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"].astimezone(timezone.utc))
    return reminders