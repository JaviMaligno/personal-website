from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

__all__ = ["plan_reminders"]

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    """Return scheduled appointment reminders, ordered by send time."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment["status"].lower() == "cancelled":
            continue

        start = appointment["starts_at"]
        if isinstance(start, str):
            start = datetime.fromisoformat(start)
        if start.tzinfo is None or start.utcoffset() is None:
            raise ValueError("starts_at must be timezone-aware")
        start = start.astimezone(_DUBLIN)

        use_sms = bool(appointment.get("phone")) and not appointment.get("optout_sms_v2", False)
        channel = "sms" if use_sms else "email"
        contact = appointment["phone"] if use_sms else "email (address redacted)"
        recipient = appointment.get("customer_name", "")
        signature = "Grzegorz Szczepański" if appointment.get("country") == "PL" else "Chevonne Nee Divver"
        appointment_time = start.strftime("%Y-%m-%d %H:%M")
        name = recipient.strip()

        for hours in (48, 2):
            scheduled = start - timedelta(hours=hours)
            if scheduled < now:
                scheduled = now
            elif time(0, 0) <= scheduled.timetz().replace(tzinfo=None) < time(8, 0):
                scheduled = datetime.combine(scheduled.date() - timedelta(days=1), time(20), _DUBLIN)
            elif scheduled.timetz().replace(tzinfo=None) >= time(21, 0):
                scheduled = datetime.combine(scheduled.date(), time(20), _DUBLIN)

            text = f"Hi {name}, your appointment is {appointment_time}. {signature}"
            if channel == "sms" and len(text) > 160:
                fixed = f"Hi , your appointment is {appointment_time}. {signature}"
                name = name[:max(0, 160 - len(fixed))]
                text = f"Hi {name}, your appointment is {appointment_time}. {signature}"

            reminders.append({
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": scheduled,
                "text": text,
            })
            _LOG.info("Reminder for %s via %s to %s", recipient, channel, contact)

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders