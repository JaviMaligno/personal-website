from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import logging


_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    """Return appointment reminders scheduled relative to the aware datetime now."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    now_utc = now.astimezone(timezone.utc)
    reminders = []

    for appointment in appointments:
        if appointment["status"].lower() == "cancelled":
            continue

        starts_at = appointment["starts_at"]
        if starts_at.tzinfo is None or starts_at.utcoffset() is None:
            raise ValueError("appointment datetimes must be timezone-aware")

        local_start = starts_at.astimezone(_DUBLIN)
        when = local_start.strftime("%Y-%m-%d at %H:%M")
        name = str(appointment.get("customer_name") or "")
        signature = (
            "Grzegorz Szczepański"
            if appointment.get("country") == "PL"
            else "Siobhán Ní Dhuibhir"
        )
        phone = appointment.get("phone")
        sms = bool(phone) and not appointment.get("optout_sms_v2", False)
        channel = "sms" if sms else "email"
        contact = str(phone) if sms else "redacted"

        for hours in (48, 2):
            instant = starts_at.astimezone(timezone.utc) - timedelta(hours=hours)
            if hours == 48 and instant < now_utc:
                instant = now_utc

            local_send = instant.astimezone(_DUBLIN)
            if local_send.hour >= 21 or local_send.hour < 8:
                local_send = (local_send - timedelta(days=1)).replace(
                    hour=20, minute=0, second=0, microsecond=0
                )

            send_utc = max(local_send.astimezone(timezone.utc), now_utc)
            send_at = send_utc.astimezone(now.tzinfo)

            if sms:
                prefix = f"Hi {name}, " if name else "Hi, "
                text = f"{prefix}your appointment is {when}. {signature}"
                if len(text) > 160:
                    short_name = name.split()[0] if name.split() else ""
                    prefix = f"Hi {short_name}, " if short_name else "Hi, "
                    text = f"{prefix}your appointment is {when}. {signature}"
                if len(text) > 160:
                    text = f"Appointment: {when}. {signature}"
            else:
                text = f"Hi {name}, your appointment is {when}. {signature}" if name else (
                    f"Your appointment is {when}. {signature}"
                )

            reminders.append({
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            _LOG.info(
                "Planned reminder for %s via %s to %s",
                name or appointment["id"],
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"].astimezone(timezone.utc))
    return reminders