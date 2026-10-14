from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Any, Mapping
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now) -> list[dict]:
    """Plan 48-hour and 2-hour reminders for usable appointments.

    Accepts mappings or objects with common appointment field names. Naive
    datetimes are interpreted as Dublin local time; ISO datetime strings are
    accepted. Missing or invalid required IDs or scheduled times are skipped.
    SMS length uses UTF-16 code units, as with JavaScript string length.
    """
    def field(obj: Any, *names: str, default: Any = None) -> Any:
        for name in names:
            if isinstance(obj, Mapping):
                if name in obj:
                    return obj[name]
            elif hasattr(obj, name):
                return getattr(obj, name)
        return default

    def local_datetime(value: Any) -> datetime | None:
        try:
            if isinstance(value, str):
                value = datetime.fromisoformat(value)
            if not isinstance(value, datetime):
                return None
            if value.tzinfo is None:
                return value.replace(tzinfo=_DUBLIN)
            return value.astimezone(_DUBLIN)
        except (TypeError, ValueError, OverflowError):
            return None

    def sms_length(value: str) -> int:
        return len(value.encode("utf-16-le")) // 2

    current = local_datetime(now)
    if current is None:
        return []

    plans: list[dict] = []
    for appointment in appointments or ():
        appointment_id = field(appointment, "appointment_id", "id")
        scheduled = local_datetime(
            field(appointment, "scheduled_at", "scheduled_time", "appointment_time", "start_time")
        )
        if appointment_id is None or scheduled is None:
            continue

        status = str(field(appointment, "status", default="")).strip().lower()
        if field(appointment, "cancelled", "is_cancelled", default=False) is True or status == "cancelled":
            continue

        customer = field(appointment, "customer", default=appointment)
        name = str(field(customer, "name", "customer_name", default="")).strip()
        phone = field(customer, "phone_number", "phone", "mobile")
        has_phone = isinstance(phone, str) and bool(phone.strip())
        sms_optout = field(customer, "optout_sms_v2", default=None)
        channel = "sms" if has_phone and sms_optout is False else "email"
        country = str(field(customer, "country", default="")).strip().upper()
        signature = "Grzegorz Szczepański." if country == "PL" else "Chevonne Nee Divver,"
        date_text = scheduled.strftime("%d/%m/%Y")
        time_text = scheduled.strftime("%H:%M")
        prefix = f"Hi {name}, your appointment is on {date_text} at {time_text}. "
        suffix = f" {signature}"
        message = prefix + suffix
        if channel == "sms" and sms_length(message) > 160:
            fixed = f"Hi , your appointment is on {date_text} at {time_text}.{suffix}"
            available = max(0, 160 - sms_length(fixed))
            shortened = ""
            for char in name:
                if sms_length(shortened + char) > available:
                    break
                shortened += char
            message = f"Hi {shortened}, your appointment is on {date_text} at {time_text}.{suffix}"

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            send_at = scheduled - lead
            if lead == timedelta(hours=48) and send_at < current:
                send_at = current
            local_time = send_at.timetz().replace(tzinfo=None)
            if local_time >= time(21, 0) or local_time < time(8, 0):
                quiet_end = (send_at - timedelta(days=1) if local_time < time(8, 0) else send_at).replace(
                    hour=20, minute=0, second=0, microsecond=0
                )
                send_at = max(quiet_end, current)
            send_at = max(send_at, current)
            plans.append({
                "appointment_id": appointment_id,
                "channel": channel,
                "send_at": send_at,
                "text": message,
            })
            contact = phone.strip() if channel == "sms" else "[redacted]"
            _LOG.info("Reminder for %s via %s to %s", name or "customer", channel, contact)

    plans.sort(key=lambda reminder: reminder["send_at"])
    return plans