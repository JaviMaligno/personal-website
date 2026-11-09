from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOGGER = logging.getLogger(__name__)
_IRISH_SIGNATURE = "Siobhán Ní Dhuibhir"
_POLISH_SIGNATURE = "Grzegorz Szczepański"


def plan_reminders(appointments, now):
    """Return appointment reminders scheduled at or after the aware datetime `now`."""
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")

    now_local = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if str(appointment.get("status", "")).casefold() == "cancelled":
            continue

        starts_at = appointment["starts_at"]
        if (
            not isinstance(starts_at, datetime)
            or starts_at.tzinfo is None
            or starts_at.utcoffset() is None
        ):
            raise ValueError("starts_at must be a timezone-aware datetime")

        phone = appointment.get("phone")
        opted_out = bool(appointment.get("optout_sms_v2", False))
        if phone and opted_out:
            continue
        channel = "sms" if phone else "email"
        contact = phone if channel == "sms" else appointment.get("email")
        if channel == "email" and not contact:
            continue

        starts_local = starts_at.astimezone(_DUBLIN)
        signature = (
            _POLISH_SIGNATURE
            if str(appointment.get("country", "")).upper() == "PL"
            else _IRISH_SIGNATURE
        )
        date_text = starts_local.strftime("%d/%m/%Y")
        time_text = starts_local.strftime("%H:%M")
        name = str(appointment.get("customer_name") or "").strip()

        if channel == "sms":
            suffix = f" {signature}"
            prefix = f"Appointment {date_text} at {time_text}."
            available = 160 - len(prefix) - len(suffix)
            name_part = f" {name}" if name and available > 1 else ""
            text = prefix + name_part[: max(0, available)] + suffix
        else:
            greeting = f" {name}," if name else ""
            text = f"Appointment{greeting} {date_text} at {time_text}. {signature}"

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            scheduled = starts_at - lead
            if scheduled < now:
                scheduled = now
            local_send = scheduled.astimezone(_DUBLIN)

            if local_send.hour >= 21:
                local_send = local_send.replace(
                    hour=20, minute=0, second=0, microsecond=0
                )
            elif local_send.hour < 8:
                local_send = (local_send - timedelta(days=1)).replace(
                    hour=20, minute=0, second=0, microsecond=0
                )

            if local_send < now_local:
                local_send = now_local.replace(
                    hour=8, minute=0, second=0, microsecond=0
                )
                if local_send < now_local:
                    local_send += timedelta(days=1)

            reminders.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": local_send,
                    "text": text,
                }
            )
            log_contact = contact if channel == "sms" else "[redacted]"
            _LOGGER.info(
                "Planned %s reminder for appointment %s via %s to %s",
                lead,
                appointment["id"],
                channel,
                log_contact,
            )

    reminders.sort(
        key=lambda reminder: (
            reminder["send_at"].astimezone(ZoneInfo("UTC")),
            str(reminder["appointment_id"]),
            reminder["channel"],
        )
    )
    return reminders