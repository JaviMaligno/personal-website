import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    """Return reminders for each non-cancelled appointment."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    reminders = []

    for appointment in appointments:
        get = appointment.get if hasattr(appointment, "get") else lambda key, default=None: getattr(appointment, key, default)

        if get("cancelled", False):
            continue

        starts_at = get("starts_at")
        if starts_at.tzinfo is None or starts_at.utcoffset() is None:
            raise ValueError("starts_at must be timezone-aware")

        phone = get("phone_number") or get("phone")
        channel = "sms" if phone and not get("optout_sms_v2", False) else "email"
        contact = phone if channel == "sms" else (get("email") or "no email")
        name = str(get("customer_name") or get("name") or "there")
        signature = (
            "Grzegorz Szczepański"
            if get("country") == "PL"
            else "Siobhán Ní Dhuibhir"
        )
        appointment_id = get("appointment_id", get("id"))
        date_text = starts_at.strftime("%Y-%m-%d")
        time_text = starts_at.strftime("%H:%M")

        for hours in (48, 2):
            send_at = starts_at - timedelta(hours=hours)
            if send_at < now:
                send_at = now

            local_send = send_at.astimezone(_DUBLIN)
            if local_send.time() >= time(21) or local_send.time() < time(8):
                quiet_end = local_send.replace(
                    hour=20, minute=0, second=0, microsecond=0
                )
                if local_send.time() < time(8):
                    quiet_end -= timedelta(days=1)
                send_at = quiet_end.astimezone(send_at.tzinfo)
                if send_at < now:
                    send_at = now

            if channel == "sms":
                prefix = f"Reminder: {name}, appointment {date_text} {time_text}. "
                suffix = f" {signature}"
                available = 160 - len(prefix) - len(suffix)
                text = f"Reminder: {name[:max(0, available)]}, appointment {date_text} {time_text}.{suffix}"
                if len(text) > 160:
                    text = f"Appt {date_text} {time_text}.{suffix}"
            else:
                text = f"Reminder: {name}, your appointment is on {date_text} at {time_text}. {signature}"

            reminder = {
                "appointment_id": appointment_id,
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

    return sorted(reminders, key=lambda reminder: reminder["send_at"])
