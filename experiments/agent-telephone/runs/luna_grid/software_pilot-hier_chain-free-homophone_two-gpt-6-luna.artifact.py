from datetime import datetime, time, timedelta, timezone
import logging
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOGGER = logging.getLogger(__name__)


def _require_aware(value, field):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")


def _quiet_hours(send_at, now_utc):
    local_time = send_at.timetz().replace(tzinfo=None)
    if local_time >= time(21):
        send_at = datetime.combine(send_at.date(), time(20), _DUBLIN)
    elif local_time < time(8):
        send_at = datetime.combine(
            send_at.date() - timedelta(days=1), time(20), _DUBLIN
        )
    if send_at.astimezone(timezone.utc) < now_utc:
        return now_utc.astimezone(_DUBLIN)
    return send_at


def _message(name, date, local_time, signature, sms):
    if name:
        prefix = f"Appointment reminder for {name}: "
    else:
        prefix = "Appointment reminder: "
    suffix = f"{date} at {local_time}. {signature}"
    if sms:
        name_length = max(0, 160 - len(prefix) - len(suffix))
        if name:
            prefix = f"Appointment reminder for {name[:name_length]}: "
        return prefix + suffix
    return prefix + suffix


def plan_reminders(appointments, now):
    """Return scheduled appointment reminders in Europe/Dublin local time."""
    _require_aware(now, "now")
    now_utc = now.astimezone(timezone.utc)
    results = []

    for appointment in appointments:
        if appointment.get("status", "").casefold() == "cancelled":
            continue

        appointment_at = appointment["appointment_at"]
        _require_aware(appointment_at, "appointment_at")
        appointment_utc = appointment_at.astimezone(timezone.utc)
        appointment_local = appointment_utc.astimezone(_DUBLIN)
        date = appointment_local.strftime("%d/%m/%Y")
        local_time = appointment_local.strftime("%H:%M")
        signature = (
            "Grzegorz Szczepański"
            if appointment.get("country") == "PL"
            else "Siobhán Ní Dhuibhir"
        )

        phone = appointment.get("phone", "")
        email = appointment.get("email", "")
        sms = bool(phone) and not appointment.get("optout_sms_v2", False)
        if not sms and not email:
            continue
        channel = "sms" if sms else "email"
        name = appointment.get("customer_name") or ""

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            target_utc = appointment_utc - lead
            if lead == timedelta(hours=2) and target_utc < now_utc:
                continue
            if lead == timedelta(hours=48) and target_utc < now_utc:
                target_utc = now_utc

            send_at = _quiet_hours(target_utc.astimezone(_DUBLIN), now_utc)
            results.append(
                {
                    "appointment_id": appointment.get("appointment_id"),
                    "channel": channel,
                    "send_at": send_at,
                    "text": _message(name, date, local_time, signature, sms),
                }
            )
            _LOGGER.info(
                "Reminder planned for appointment_id=%r via %s to %s",
                appointment.get("appointment_id"),
                channel,
                "phone" if sms else "email",
            )

    results.sort(key=lambda item: item["send_at"].astimezone(timezone.utc))
    return results