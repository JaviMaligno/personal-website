from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)
_SIGNATURE = "Grzegorz Szczepański"
_DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"


def plan_reminders(appointments, now):
    """Return due appointment reminders, scheduled in Europe/Dublin."""
    now = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment["status"].lower() == "cancelled":
            continue

        starts_at = appointment["starts_at"].astimezone(_DUBLIN)
        signature = (
            _SIGNATURE if appointment.get("country") == "PL"
            else _DEFAULT_SIGNATURE
        )
        text = (
            f"{appointment['customer_name']}: your appointment is on "
            f"{starts_at:%d %B} at {starts_at:%H:%M}. {signature}"
        )

        channel = (
            "sms"
            if appointment.get("phone") and not appointment.get("optout_sms_v2", False)
            else "email"
        )
        if channel == "sms" and len(text) > 160:
            name = appointment["customer_name"]
            shortened = name[:1] + "." if name else ""
            text = (
                f"{shortened}: your appointment is on {starts_at:%d %B} "
                f"at {starts_at:%H:%M}. {signature}"
            )

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            target = starts_at - offset
            send_at = max(target, now)
            if send_at.hour >= 21 or send_at.hour < 8:
                send_at = send_at.replace(hour=20, minute=0, second=0, microsecond=0)
                if send_at < now:
                    continue

            reminder = {
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            }
            reminders.append(reminder)

            contact = appointment.get("phone") if channel == "sms" else "[redacted]"
            _LOG.info(
                "Reminder planned for %s via %s to %s",
                appointment.get("customer_name", ""),
                channel,
                contact or "[unavailable]",
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders
