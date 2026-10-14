from datetime import datetime, timedelta
from logging import getLogger
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = getLogger(__name__)


def _local(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("appointment and current datetimes must be timezone-aware")
    return value.astimezone(_DUBLIN)


def _quiet_adjust(value):
    if value.hour >= 21:
        return value.replace(hour=20, minute=0, second=0, microsecond=0)
    if value.hour < 8:
        return (value - timedelta(days=1)).replace(
            hour=20, minute=0, second=0, microsecond=0
        )
    return value


def _message(name, starts_at, signature, limit=None):
    appointment_time = f"{starts_at:%Y-%m-%d} at {starts_at:%H:%M}"
    ending = f" Your appointment is {appointment_time}. {signature}"
    prefix = f"Hi {name},"
    if limit is not None:
        available = limit - len(prefix) - len(ending)
        if available < 0:
            prefix = ""
            available = limit - len(ending)
        if available < 0:
            raise ValueError("appointment details and signature exceed SMS limit")
        prefix = prefix[: available + len(prefix)] if len(prefix) <= available else (
            prefix[: max(0, available - 1)] + ("…" if available else "")
        )
    return f"{prefix}{ending}"


def plan_reminders(appointments, now):
    """Return non-cancelled appointment reminders, ordered by local send time."""
    local_now = _local(now)
    reminders = []

    for appointment in appointments:
        if str(appointment["status"]).lower() == "cancelled":
            continue

        opted_out = bool(appointment.get("optout_sms_v2", False))
        phone = appointment.get("phone")
        if phone and not opted_out:
            channel = "sms"
            contact = phone
        elif opted_out:
            channel = "email"
            contact = appointment.get("email")
        else:
            continue

        starts_at = _local(appointment["starts_at"])
        signature = (
            "Grzegorz Szczepański"
            if str(appointment.get("country", "")).upper() == "PL"
            else "Chevonne Nee Divver"
        )
        text = _message(
            str(appointment.get("customer_name", "")),
            starts_at,
            signature,
            160 if channel == "sms" else None,
        )

        for offset in (timedelta(hours=2), timedelta(hours=48)):
            send_at = starts_at - offset
            if offset == timedelta(hours=48) and send_at < local_now:
                send_at = local_now
            send_at = _quiet_adjust(send_at)
            if send_at < local_now:
                send_at = local_now

            reminders.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }
            )
            log_contact = str(contact) if channel == "sms" else "[email address redacted]"
            _LOG.info(
                "Planned %s reminder for %s via %s to %s",
                "2-hour" if offset == timedelta(hours=2) else "48-hour",
                appointment.get("customer_name", ""),
                channel,
                log_contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders