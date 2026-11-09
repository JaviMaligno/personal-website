from datetime import datetime, time, timedelta
import logging
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_SIGNATURE_DEFAULT = "Chevonne Nee Divver"
_SIGNATURE_PL = "Grzegorz Szczepański"
_LOG = logging.getLogger(__name__)


def _aware_datetime(value):
    if not isinstance(value, datetime):
        raise ValueError("Appointment datetime is missing or invalid")
    try:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError
    except Exception:
        raise ValueError("Appointment datetime must be timezone-aware") from None
    return value


def _message(name, date_text, time_text, signature, sms):
    def build(customer):
        greeting = f"Hi {customer}, " if customer else ""
        return f"{greeting}your appointment is on {date_text} at {time_text}. {signature}"

    text = build(name)
    if sms and len(text) > 160:
        text = build("")
    if sms and len(text) > 160:
        raise ValueError("SMS reminder text exceeds 160 characters")
    return text


def plan_reminders(appointments, now):
    """Return chronologically ordered reminders for valid, non-cancelled appointments."""
    now = _aware_datetime(now)
    reminders = []

    for appointment in appointments:
        if not isinstance(appointment, dict):
            raise ValueError("Appointment record is invalid")
        if appointment.get("status") == "cancelled":
            continue

        try:
            starts_at = _aware_datetime(appointment["starts_at"])
            appointment_id = appointment["id"]
            name = appointment.get("customer_name") or ""
            phone = appointment.get("phone")
            email = appointment.get("email")
            opted_out = appointment["optout_sms_v2"]
            country = appointment.get("country")
        except (KeyError, TypeError):
            raise ValueError("Appointment record is missing required data") from None

        if not isinstance(opted_out, bool):
            raise ValueError("SMS preference must be a boolean")

        use_sms = bool(phone) and not opted_out
        if not use_sms and not email:
            raise ValueError("Appointment has no usable contact details")

        channel = "sms" if use_sms else "email"
        contact = str(phone) if use_sms else "[redacted]"
        signature = _SIGNATURE_PL if country == "PL" else _SIGNATURE_DEFAULT
        local_start = starts_at.astimezone(_DUBLIN)
        date_text = local_start.strftime("%Y-%m-%d")
        time_text = local_start.strftime("%H:%M")

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            target = starts_at - offset
            if offset == timedelta(hours=48) and target < now:
                target = now
            elif target < now:
                continue

            local_target = target.astimezone(_DUBLIN)
            if local_target.time() >= time(21, 0) or local_target.time() < time(8, 0):
                local_target = datetime.combine(
                    local_target.date() - timedelta(days=1),
                    time(20, 0),
                    tzinfo=_DUBLIN,
                )
                target = local_target

            if target < now:
                continue

            text = _message(name, date_text, time_text, signature, use_sms)
            reminders.append(
                {
                    "appointment_id": appointment_id,
                    "channel": channel,
                    "send_at": target,
                    "text": text,
                }
            )
            _LOG.info(
                "Planned reminder for %s via %s contact=%s",
                name or "[unnamed customer]",
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders