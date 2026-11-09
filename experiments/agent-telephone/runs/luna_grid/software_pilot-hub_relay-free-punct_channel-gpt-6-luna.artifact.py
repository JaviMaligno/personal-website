from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def _as_dublin(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime):
        raise TypeError("appointment times and now must be datetimes or ISO strings")
    if value.tzinfo is None:
        return value.replace(tzinfo=_DUBLIN)
    return value.astimezone(_DUBLIN)


def _quiet_hours_adjust(send_at):
    if send_at.hour >= 21:
        day = send_at.date()
    elif send_at.hour < 8:
        day = send_at.date() - timedelta(days=1)
    else:
        return send_at
    return datetime.combine(day, time(20), _DUBLIN)


def plan_reminders(appointments, now):
    now = _as_dublin(now)
    reminders = []

    for appointment in appointments:
        if appointment.get("cancelled") or str(appointment.get("status", "")).lower() == "cancelled":
            continue

        starts_at = _as_dublin(appointment["starts_at"])
        phone = appointment.get("phone")
        sms_opted_out = bool(appointment.get("optout_sms_v2", False))

        if phone and not sms_opted_out:
            channel = "sms"
            contact = str(phone)
        elif not sms_opted_out and appointment.get("email"):
            channel = "email"
            contact = "address withheld"
        else:
            continue

        name = str(appointment.get("customer_name", "")).strip()
        signature = (
            "Grzegorz Szczepański"
            if str(appointment.get("country", "")).upper() == "PL"
            else "Siobhán Ní Dhuibhir"
        )
        appointment_time = starts_at.strftime("%Y-%m-%d %H:%M")

        for hours_before in (48, 2):
            send_at = starts_at - timedelta(hours=hours_before)
            if hours_before == 48 and send_at < now:
                send_at = now
            send_at = _quiet_hours_adjust(send_at)
            if send_at < now:
                send_at = now

            prefix = "Reminder: "
            suffix = f", your appointment is on {appointment_time}. {signature}"
            available = 160 - len(prefix) - len(suffix)
            reminder_name = name[:max(0, available)] if channel == "sms" else name
            text = f"{prefix}{reminder_name}{suffix}"

            reminders.append({
                "appointment_id": appointment["appointment_id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            _LOG.info(
                "Reminder for %s via %s to %s",
                name or appointment["appointment_id"],
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders