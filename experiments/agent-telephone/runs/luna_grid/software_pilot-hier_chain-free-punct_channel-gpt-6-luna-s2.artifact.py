"""Plan appointment reminders.

Quiet-hours policy: Dublin-local sends from 21:00 through 07:59 move to
20:00 immediately before quiet hours. If that would put a send before `now`,
send at `now` instead, even during quiet hours. This also resolves overdue
48-hour reminders: they are sent at `now`, with the same quiet-hours exception.
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)
_ENDINGS = {
    "PL": "Grzegorz Szczepański",
    "DEFAULT": "Siobhán Ní Dhuibhir",
}


def plan_reminders(appointments, now):
    """Return sorted reminder dictionaries for eligible appointments."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    reminders = []
    for appointment in appointments:
        if appointment.get("cancelled"):
            continue

        starts_at = appointment["starts_at"]
        if starts_at.tzinfo is None or starts_at.utcoffset() is None:
            raise ValueError("starts_at must be timezone-aware")

        phone = str(appointment.get("phone") or "").strip()
        email = str(appointment.get("email") or "").strip()
        if phone:
            channel, contact = (
                ("sms", phone)
                if not appointment.get("optout_sms_v2", False)
                else (None, None)
            )
        elif email:
            channel, contact = "email", email
        else:
            channel, contact = None, None
        if channel is None:
            continue

        local_start = starts_at.astimezone(_DUBLIN)
        for offset in (timedelta(hours=48), timedelta(hours=2)):
            send_at = starts_at - offset
            if send_at < now:
                send_at = now
            local_send = send_at.astimezone(_DUBLIN)
            if local_send.hour >= 21 or local_send.hour < 8:
                quiet_end = local_send.replace(
                    hour=20, minute=0, second=0, microsecond=0
                )
                if local_send.hour < 8:
                    quiet_end -= timedelta(days=1)
                send_at = quiet_end.astimezone(now.tzinfo)
                if send_at < now:
                    send_at = now

            ending = _ENDINGS.get(appointment.get("country"), _ENDINGS["DEFAULT"])
            date = local_start.strftime("%d %B %Y")
            time = local_start.strftime("%H:%M")
            if channel == "sms":
                name = str(appointment.get("customer_name") or "").strip()
                prefix = f"Reminder: {name}, your appointment is on {date} at {time}. — "
                text = prefix + ending
                if len(text) > 160:
                    available = max(0, 160 - len(f"Reminder: , your appointment is on {date} at {time}. — {ending}"))
                    name = name[:available]
                    text = f"Reminder: {name}, your appointment is on {date} at {time}. — {ending}"
            else:
                text = (
                    f"Appointment reminder: your appointment is on "
                    f"{date} at {time}. — {ending}"
                )

            reminders.append(
                {
                    "appointment_id": appointment["appointment_id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }
            )
            recipient = str(appointment.get("customer_name") or "customer").strip()
            logged_contact = contact if channel == "sms" else "[email address redacted]"
            _LOG.info("Reminder recipient=%s channel=%s contact=%s", recipient, channel, logged_contact)

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders