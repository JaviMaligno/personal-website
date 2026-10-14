from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    """Return the planned appointment reminders, ordered by send time."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    now_local = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment["status"] == "cancelled":
            continue

        starts_at = appointment["starts_at"]
        if isinstance(starts_at, str):
            starts_at = datetime.fromisoformat(starts_at)
        if starts_at.tzinfo is None or starts_at.utcoffset() is None:
            raise ValueError("starts_at must be timezone-aware")
        starts_local = starts_at.astimezone(_DUBLIN)

        phone = appointment.get("phone")
        use_sms = bool(phone) and not appointment.get("optout_sms_v2", False)
        channel = "sms" if use_sms else "email"
        contact = phone if use_sms else "email contact"

        signature = (
            "Grzegorz Szczepański"
            if appointment.get("country") == "PL"
            else "Siobhán Ní Dhuibhir"
        )
        appointment_time = starts_local.strftime("%H:%M")
        appointment_date = starts_local.strftime("%d/%m/%Y")
        name = str(appointment["customer_name"])
        prefix = f"Reminder: , {appointment_date} {appointment_time}. "
        suffix = f" {signature}"
        if use_sms:
            name = name[: max(0, 160 - len(prefix) - len(suffix))]
        text = f"Reminder: {name}, {appointment_date} {appointment_time}.{suffix}"

        for hours_before in (48, 2):
            send_at = starts_local - timedelta(hours=hours_before)
            if send_at < now_local:
                send_at = now_local

            if send_at.hour >= 21 or send_at.hour < 8:
                send_at = send_at.replace(hour=20, minute=0, second=0, microsecond=0)
                if send_at < now_local:
                    send_at = now_local

            reminder = {
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            }
            reminders.append(reminder)
            _LOG.info(
                "Reminder for %s via %s to %s",
                appointment["customer_name"],
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders