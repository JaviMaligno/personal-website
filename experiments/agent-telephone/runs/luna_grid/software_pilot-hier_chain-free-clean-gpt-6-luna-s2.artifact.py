from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def _as_dublin(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime):
        raise TypeError("appointment times and now must be datetimes or ISO-formatted strings")
    if value.tzinfo is None:
        return value.replace(tzinfo=_DUBLIN)
    return value.astimezone(_DUBLIN)


def _present(value):
    return value is not None and bool(str(value).strip())


def plan_reminders(appointments, now):
    """Plan appointment reminders; naive datetimes are treated as Dublin local time."""
    now = _as_dublin(now)
    planned = []

    for appointment in appointments:
        if appointment.get("cancelled", False):
            continue

        starts_at = _as_dublin(appointment["starts_at"])
        phone = appointment.get("phone")
        use_sms = _present(phone) and not appointment.get("optout_sms_v2", False)
        channel = "sms" if use_sms else "email"
        contact = str(phone).strip() if use_sms else "email on file"
        name = str(appointment.get("customer_name") or appointment.get("name") or "Customer").strip()
        signoff = (
            "Grzegorz Szczepański"
            if str(appointment.get("country") or "").upper() == "PL"
            else "Siobhán Ní Dhuibhir"
        )
        appointment_time = starts_at.strftime("%Y-%m-%d %H:%M")
        prefix = f"Reminder for {appointment_time}. "
        suffix = f" {signoff}"
        available_name_length = max(0, 160 - len(prefix) - len(suffix))
        short_name = name[:available_name_length]
        text = f"{prefix}{short_name}{suffix}"
        if len(text) > 160:
            text = f"{prefix}{suffix.strip()}"

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            send_at = starts_at - offset
            if send_at < now:
                send_at = now

            local_time = send_at.timetz().replace(tzinfo=None)
            if local_time >= time(21, 0) or local_time < time(8, 0):
                quiet_start = send_at.replace(hour=21, minute=0, second=0, microsecond=0)
                send_at = quiet_start - timedelta(hours=1)

            reminder = {
                "appointment_id": appointment.get("appointment_id", appointment.get("id")),
                "channel": channel,
                "send_at": send_at,
                "text": text,
            }
            planned.append((send_at, 0 if offset == timedelta(hours=2) else 1, reminder))
            _LOG.info(
                "Reminder for %s via %s to %s",
                name,
                channel,
                contact,
            )

    planned.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in planned]