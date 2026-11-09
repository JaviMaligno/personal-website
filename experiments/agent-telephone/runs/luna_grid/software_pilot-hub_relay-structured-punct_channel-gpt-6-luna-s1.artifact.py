from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)
_IRISH_SIGNATURE = "Siobhán Ní Dhuibhir"
_POLISH_SIGNATURE = "Grzegorz Szczepański"


def plan_reminders(appointments, now):
    """Plan appointment reminders, returning them in send-time order."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment.get("status", "").casefold() == "cancelled":
            continue

        starts_at = appointment["starts_at"]
        if starts_at.tzinfo is None or starts_at.utcoffset() is None:
            raise ValueError("starts_at must be timezone-aware")
        local_start = starts_at.astimezone(_DUBLIN)

        phone = appointment.get("phone")
        if phone and appointment.get("optout_sms_v2") is True:
            channel, contact = "sms", phone
        elif appointment.get("email"):
            channel, contact = "email", "[redacted]"
        else:
            continue

        signature = (
            _POLISH_SIGNATURE
            if appointment.get("country") == "PL"
            else _IRISH_SIGNATURE
        )
        date_time = local_start.strftime("%Y-%m-%d %H:%M")
        name = str(appointment.get("customer_name", ""))
        message = f"Hello {name}, your appointment is on {date_time}. {signature}"

        if channel == "sms" and len(message) > 160:
            suffix = f", your appointment is on {date_time}. {signature}"
            name_budget = max(0, 160 - len("Hello " + suffix))
            shortened_name = name[:name_budget]
            message = f"Hello {shortened_name}{suffix}"

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            send_at = local_start - offset
            if send_at < now:
                if offset == timedelta(hours=48):
                    send_at = now
                else:
                    continue

            if send_at.time() >= time(21) or send_at.time() < time(8):
                send_at = datetime.combine(
                    send_at.date() - (timedelta(days=1) if send_at.time() < time(8) else timedelta()),
                    time(20),
                    tzinfo=_DUBLIN,
                )
                if send_at < now:
                    send_at = datetime.combine(
                        now.date() + timedelta(days=1), time(20), tzinfo=_DUBLIN
                    )

            reminder = {
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": message,
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