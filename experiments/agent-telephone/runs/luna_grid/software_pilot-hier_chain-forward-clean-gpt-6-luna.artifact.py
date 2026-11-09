from datetime import datetime, timedelta, timezone
import logging
from zoneinfo import ZoneInfo

_LOGGER = logging.getLogger(__name__)
_DUBLIN = ZoneInfo("Europe/Dublin")
_UTC = timezone.utc
_SIGNATURE = "Siobhán Ní Dhuibhir"
_POLISH_SIGNATURE = "Grzegorz Szczepański"


def plan_reminders(appointments, now):
    """Return appointment reminders sorted by their local Dublin send time."""
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")

    now_local = now.astimezone(_DUBLIN)
    now_utc = now.astimezone(_UTC)
    reminders = []

    for appointment in appointments:
        if not isinstance(appointment, dict) or appointment.get("status") == "cancelled":
            continue

        starts_at = appointment.get("starts_at")
        if (
            not isinstance(starts_at, datetime)
            or starts_at.tzinfo is None
            or starts_at.utcoffset() is None
            or appointment.get("id") is None
        ):
            continue

        starts_utc = starts_at.astimezone(_UTC)
        starts_local = starts_utc.astimezone(_DUBLIN)
        phone = appointment.get("phone")
        phone = phone.strip() if isinstance(phone, str) else ""
        use_sms = bool(phone) and appointment.get("optout_sms_v2", False) is not True
        channel = "sms" if use_sms else "email"
        contact = phone if use_sms else "[redacted]"
        name = appointment.get("customer_name")
        name = name.strip() if isinstance(name, str) and name.strip() else "there"
        signature = (
            _POLISH_SIGNATURE
            if appointment.get("country") == "PL"
            else _SIGNATURE
        )
        date_text = starts_local.strftime("%d %B %Y")
        time_text = starts_local.strftime("%H:%M")
        base_text = f"Your appointment is on {date_text} at {time_text}. {signature}"

        for hours_before in (48, 2):
            candidate_utc = starts_utc - timedelta(hours=hours_before)
            if hours_before == 48 and candidate_utc < now_utc:
                candidate_utc = now_utc
            if candidate_utc < now_utc:
                continue

            send_at = candidate_utc.astimezone(_DUBLIN)
            if send_at.hour >= 21 or send_at.hour < 8:
                send_at = (send_at - timedelta(days=1)).replace(
                    hour=20, minute=0, second=0, microsecond=0
                )
            if send_at < now_local:
                continue

            text = f"Hi {name}, {base_text}"
            if use_sms and len(text) > 160:
                prefix = "Hi "
                suffix = f", {base_text}"
                available = max(0, 160 - len(prefix) - len(suffix))
                shortened = name[:available].rstrip()
                text = f"{prefix}{shortened}{suffix}"
                if len(text) > 160:
                    text = text[:160]

            reminders.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }
            )
            _LOGGER.info(
                "Planned reminder for %s via %s (contact: %s)",
                name,
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders