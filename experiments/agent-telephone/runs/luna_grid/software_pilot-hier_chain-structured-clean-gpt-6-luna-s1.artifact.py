from datetime import datetime, time, timedelta, timezone
import logging
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def _quiet_adjust(send_at: datetime, now: datetime) -> datetime:
    local = send_at.astimezone(_DUBLIN)
    if local.hour >= 21 or local.hour < 8:
        previous_day = local.date() - timedelta(days=1)
        adjusted = datetime.combine(previous_day, time(20, 0), _DUBLIN)
        if adjusted < now.astimezone(_DUBLIN):
            adjusted = datetime.combine(local.date(), time(20, 0), _DUBLIN)
        return adjusted
    return local


def _message(name: str, appointment_time: datetime, country: str, sms: bool) -> str:
    local = appointment_time.astimezone(_DUBLIN)
    date_text = local.strftime("%d %B %Y")
    time_text = local.strftime("%H:%M")
    signature = "Grzegorz Szczepański" if country == "PL" else "Siobhán Ní Dhuibhir"
    prefix = f"Hi {name}, your appointment is on {date_text} at {time_text}. "
    suffix = signature
    if sms:
        name_limit = max(0, 160 - len(prefix) - len(suffix))
        if len(name) > name_limit:
            prefix = f"Hi {name[:name_limit]}, your appointment is on {date_text} at {time_text}. "
        if len(prefix) + len(suffix) > 160:
            prefix = f"Appointment: {date_text} at {time_text}. "
        return prefix + suffix
    return prefix + suffix


def plan_reminders(appointments, now):
    now_utc = now.astimezone(timezone.utc)
    reminders = []

    for appointment in appointments:
        if appointment["status"] == "cancelled":
            continue

        starts_at = appointment["starts_at"]
        starts_utc = starts_at.astimezone(timezone.utc)
        channel = (
            "sms"
            if appointment["phone"] and not appointment["optout_sms_v2"]
            else "email"
        )
        contact = appointment["phone"] if channel == "sms" else "[redacted]"
        text = _message(
            appointment["customer_name"],
            starts_at,
            appointment["country"],
            channel == "sms",
        )

        for lead_time in (timedelta(hours=48), timedelta(hours=2)):
            send_utc = starts_utc - lead_time
            if send_utc < now_utc and lead_time == timedelta(hours=48):
                send_utc = now_utc
            if send_utc < now_utc:
                continue

            send_at = _quiet_adjust(send_utc, now_utc)
            if send_at.astimezone(timezone.utc) < now_utc:
                send_at = now_utc.astimezone(_DUBLIN)
            reminders.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }
            )
            _LOG.info(
                "Reminder planned for %s via %s to %s",
                appointment["customer_name"],
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"].astimezone(timezone.utc))
    return reminders