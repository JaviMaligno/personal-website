import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

_DUBLIN = ZoneInfo("Europe/Dublin")
_UTC = timezone.utc
_LOG = logging.getLogger(__name__)
_SIGNATURE_DEFAULT = "Chevonne Nee Divver"
_SIGNATURE_PL = "Grzegorz Szczepański"


def _message(name, local_start, signature):
    date = local_start.strftime("%Y-%m-%d")
    clock = local_start.strftime("%H:%M")
    prefix = f"Hi {name}, " if name else ""
    fixed = f"your appointment is on {date} at {clock}. {signature}"
    return prefix + fixed


def _sms_text(name, local_start, signature):
    text = _message(name, local_start, signature)
    if len(text) <= 160:
        return text
    fixed = _message("", local_start, signature)
    available = max(0, 160 - len(fixed))
    shortened = name[:available]
    return _message(shortened, local_start, signature)


def plan_reminders(appointments, now):
    now_utc = now.astimezone(_UTC)
    reminders = []

    for appointment in appointments:
        if str(appointment.get("status", "")).strip().lower() == "cancelled":
            continue

        phone = appointment.get("phone")
        phone = phone.strip() if isinstance(phone, str) else ""
        sms = bool(phone) and not appointment.get("optout_sms_v2", False)
        channel = "sms" if sms else "email"
        contact = phone if sms else "redacted"
        name = str(appointment.get("customer_name") or "")
        signature = (
            _SIGNATURE_PL
            if str(appointment.get("country", "")).upper() == "PL"
            else _SIGNATURE_DEFAULT
        )
        starts_at = appointment["starts_at"].astimezone(_UTC)
        local_start = starts_at.astimezone(_DUBLIN)

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            send_at = starts_at - lead
            if lead == timedelta(hours=48) and send_at < now_utc:
                send_at = now_utc
            if send_at < now_utc:
                continue

            local_send = send_at.astimezone(_DUBLIN)
            if local_send.hour >= 21 or local_send.hour < 8:
                quiet_end = datetime.combine(
                    local_send.date() - timedelta(days=1),
                    time(20, 0),
                    tzinfo=_DUBLIN,
                )
                send_at = quiet_end.astimezone(_UTC)
            if send_at < now_utc:
                send_at = now_utc

            text = (
                _sms_text(name, local_start, signature)
                if sms
                else _message(name, local_start, signature)
            )
            reminder = {
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at.astimezone(_UTC),
                "text": text,
            }
            reminders.append(reminder)
            _LOG.info(
                "Planned reminder for %s via %s to contact %s",
                name,
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders