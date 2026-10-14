from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)
_SIGNATURE = {
    "PL": "Grzegorz Szczepański",
}


def _as_dublin(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=_DUBLIN)
    return value.astimezone(_DUBLIN)


def _quiet_hours(send_at):
    if time(21) <= send_at.timetz().replace(tzinfo=None) or send_at.hour < 8:
        previous_day = send_at.date() - timedelta(days=1)
        return datetime.combine(previous_day, time(20), _DUBLIN)
    return send_at


def plan_reminders(appointments, now):
    now = _as_dublin(now)
    reminders = []

    for appointment in appointments:
        if appointment.get("status") == "cancelled":
            continue

        starts_at = _as_dublin(appointment["starts_at"])
        phone = appointment.get("phone")
        use_sms = bool(phone) and not appointment.get("optout_sms_v2", False)
        channel = "sms" if use_sms else "email"
        contact = phone if use_sms else appointment.get("email", appointment.get("customer_email", ""))
        name = str(appointment.get("customer_name", appointment.get("name", "")))
        signature = _SIGNATURE.get(appointment.get("country"), "Chevonne Nee Divver")
        appointment_time = starts_at.strftime("%Y-%m-%d %H:%M")
        appointment_id = appointment.get("appointment_id", appointment.get("id"))

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            send_at = starts_at - offset
            if send_at < now:
                send_at = now
            send_at = _quiet_hours(send_at)
            if send_at < now:
                send_at = now

            text = f"Reminder for {name}: appointment {appointment_time}. {signature}"
            if use_sms and len(text) > 160:
                fixed = f"Reminder for : appointment {appointment_time}. {signature}"
                available = max(0, 160 - len(fixed))
                text = f"Reminder for {name[:available]}: appointment {appointment_time}. {signature}"

            reminders.append({
                "appointment_id": appointment_id,
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            _LOG.info(
                "Planned reminder for %s via %s to %s",
                name or "customer",
                channel,
                contact if use_sms else "email (address redacted)",
            )

    return sorted(reminders, key=lambda reminder: reminder["send_at"])