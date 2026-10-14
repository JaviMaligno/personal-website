from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)
_SIGNATURES = {
    "PL": "Grzegorz Szczepański",
}
_DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"


def _aware(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("now and starts_at must be timezone-aware datetimes")
    return value


def _masked_email(address):
    if not address or "@" not in address:
        return "[email]"
    local, domain = address.rsplit("@", 1)
    return f"{local[:1]}***@{domain}"


def _quiet_time(value, now):
    local = value.astimezone(_DUBLIN)
    if local.hour >= 21 or local.hour < 8:
        send_at = datetime.combine(local.date(), time(20), _DUBLIN)
        if send_at < now.astimezone(_DUBLIN):
            send_at = datetime.combine(
                now.astimezone(_DUBLIN).date() + timedelta(days=1),
                time(20),
                _DUBLIN,
            )
        return send_at
    return local


def _sms_text(name, starts_at, signature):
    stamp = starts_at.astimezone(_DUBLIN).strftime("%Y-%m-%d %H:%M")
    prefix = f"Reminder: {stamp}. "
    suffix = f" {signature}"
    text = f"{prefix}{name}{suffix}"
    if len(text) <= 160:
        return text

    available = 160 - len(prefix) - len(suffix)
    if available <= 0:
        return (prefix + suffix)[:160]
    short_name = name.strip()
    if len(short_name) > available:
        short_name = short_name.split()[0] if short_name.split() else ""
    if len(short_name) > available:
        short_name = short_name[:available]
    return f"{prefix}{short_name}{suffix}"[:160]


def plan_reminders(appointments, now):
    """Return planned appointment reminders, ordered by their delivery time."""
    now = _aware(now)
    reminders = []

    for appointment in appointments:
        if appointment.get("cancelled", False):
            continue

        starts_at = _aware(appointment["starts_at"])
        phone = appointment.get("phone")
        opted_out = appointment.get("optout_sms_v2", False)
        channel = "sms" if phone and not opted_out else "email"
        contact = phone if channel == "sms" else _masked_email(appointment.get("email"))
        name = str(appointment.get("customer_name", appointment.get("name", "Customer")))
        signature = _SIGNATURES.get(
            str(appointment.get("country", "")).upper(),
            _DEFAULT_SIGNATURE,
        )

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            candidate = starts_at - lead
            if candidate < now:
                candidate = now
            send_at = _quiet_time(candidate, now)
            text = _sms_text(name, starts_at, signature)
            reminders.append(
                {
                    "appointment_id": appointment["appointment_id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }
            )
            _LOG.info(
                "Planned reminder for %s via %s to %s",
                name,
                channel,
                contact or "[missing contact]",
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders