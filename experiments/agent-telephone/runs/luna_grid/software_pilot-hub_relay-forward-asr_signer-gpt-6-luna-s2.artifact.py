from datetime import datetime, time, timedelta, timezone
import logging
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)
_SIGNATURE_DEFAULT = "Chevonne Nee Divver"
_SIGNATURE_PL = "Grzegorz Szczepański"


def _quiet_hour_adjust(send_at: datetime) -> datetime:
    local = send_at.astimezone(_DUBLIN)
    if local.time() >= time(21) or local.time() < time(8):
        day = local.date() if local.time() >= time(21) else local.date() - timedelta(days=1)
        return datetime.combine(day, time(20), _DUBLIN)
    return local


def _message(name: str, starts_at: datetime, signature: str, sms: bool) -> str:
    local_start = starts_at.astimezone(_DUBLIN)
    date_time = f"{local_start:%Y-%m-%d} at {local_start:%H:%M}"
    prefix = f"Hi {name}, " if name else ""
    suffix = f" Your appointment is {date_time}. {signature}"
    if not sms:
        return prefix + suffix.lstrip()
    available = 160 - len(suffix) - len(prefix)
    if available < 0:
        prefix = ""
        available = 160 - len(suffix)
    return prefix + name[:max(0, available)] + suffix if name and prefix else prefix + suffix.lstrip()


def plan_reminders(appointments, now):
    now_utc = now.astimezone(timezone.utc)
    planned = []

    for appointment in appointments:
        if str(appointment.get("status", "")).lower() == "cancelled":
            continue

        starts_at = appointment["starts_at"].astimezone(timezone.utc)
        if starts_at <= now_utc:
            continue

        sms = bool(appointment.get("phone")) and not appointment.get("optout_sms_v2", False)
        channel = "sms" if sms else "email"
        signature = _SIGNATURE_PL if appointment.get("country") == "PL" else _SIGNATURE_DEFAULT
        name = str(appointment.get("customer_name") or "")
        for offset in (timedelta(hours=48), timedelta(hours=2)):
            due = starts_at - offset
            candidate = max(due, now_utc)
            send_at = _quiet_hour_adjust(candidate.astimezone(_DUBLIN))
            if send_at.astimezone(timezone.utc) < now_utc:
                continue
            planned.append({
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": _message(name, starts_at, signature, sms),
            })
            _LOG.info(
                "Reminder recipient appointment_id=%s channel=%s contact_type=%s",
                appointment["id"],
                channel,
                "phone" if sms else "email",
            )

    return sorted(planned, key=lambda reminder: reminder["send_at"])