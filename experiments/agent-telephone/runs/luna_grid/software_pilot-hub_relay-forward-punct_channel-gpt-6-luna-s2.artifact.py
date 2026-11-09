from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    """Return eligible appointment reminders, scheduled in Europe/Dublin time."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    now_dublin = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment.get("status", "").lower() == "cancelled":
            continue

        opted_out = bool(appointment.get("optout_sms_v2", False))
        phone = appointment.get("phone")
        email = appointment.get("email")

        if opted_out:
            continue
        if phone:
            channel, contact = "sms", phone
        elif email:
            channel, contact = "email", "email address on file"
        else:
            continue

        starts_at = appointment["starts_at"]
        if starts_at.tzinfo is None or starts_at.utcoffset() is None:
            raise ValueError("appointment starts_at values must be timezone-aware")

        local_start = starts_at.astimezone(_DUBLIN)
        signature = (
            "Grzegorz Szczepański"
            if appointment.get("country") == "PL"
            else "Siobhán Ní Dhuibhir"
        )
        date_text = local_start.strftime("%Y-%m-%d")
        time_text = local_start.strftime("%H:%M")
        name = str(appointment.get("customer_name") or "")
        message = f"Reminder: {name}, your appointment is on {date_text} at {time_text}. {signature}"

        if channel == "sms" and len(message) > 160:
            fixed = f"Reminder: , your appointment is on {date_text} at {time_text}. {signature}"
            available = max(0, 160 - len(fixed))
            message = f"Reminder: {name[:available]}, your appointment is on {date_text} at {time_text}. {signature}"

        for offset, is_first in ((timedelta(hours=48), True), (timedelta(hours=2), False)):
            send_at = local_start - offset
            if send_at <= now_dublin:
                if not is_first:
                    continue
                send_at = now_dublin

            local_time = send_at.timetz().replace(tzinfo=None)
            if local_time >= time(21, 0):
                send_at = send_at.replace(hour=20, minute=0, second=0, microsecond=0)
            elif local_time < time(8, 0):
                send_at = (send_at - timedelta(days=1)).replace(
                    hour=20, minute=0, second=0, microsecond=0
                )

            if send_at < now_dublin:
                continue

            reminders.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": message,
                }
            )
            _LOG.info(
                "Reminder for %s via %s to %s",
                name,
                channel,
                contact if channel == "sms" else "email address on file",
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders