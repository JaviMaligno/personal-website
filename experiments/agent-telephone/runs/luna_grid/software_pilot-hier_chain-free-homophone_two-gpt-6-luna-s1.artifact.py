from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

__all__ = ["plan_reminders"]

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)
_OFFSETS = (("48h", timedelta(hours=48)), ("2h", timedelta(hours=2)))


def plan_reminders(appointments, now):
    """Plan reminders for appointment dictionaries.

    Expected fields: appointment_id, start (aware datetime), cancelled,
    customer_name, phone, email, optout_sms_v2, and country. Malformed
    appointments and cancelled appointments are skipped. Missing optional
    values use empty strings/False; appointments without an ID or valid start
    are skipped. `now` must be timezone-aware or ValueError is raised.
    """
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")

    now_local = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if not isinstance(appointment, dict) or appointment.get("cancelled"):
            continue

        appointment_id = appointment.get("appointment_id")
        start = appointment.get("start")
        if not appointment_id or not isinstance(start, datetime) or start.utcoffset() is None:
            continue

        local_start = start.astimezone(_DUBLIN)
        name = str(appointment.get("customer_name") or "").strip()
        country = str(appointment.get("country") or "").upper()
        signoff = "Grzegorz Szczepański" if country == "PL" else "Siobhán Ní Dhuibhir"
        phone = str(appointment.get("phone") or "").strip()
        use_sms = bool(phone) and not appointment.get("optout_sms_v2")
        channel = "sms" if use_sms else "email"
        contact = phone if use_sms else ("configured email contact" if appointment.get("email") else "email contact")

        for label, offset in _OFFSETS:
            candidate = local_start - offset
            if label == "48h" and candidate < now_local:
                candidate = now_local

            if candidate.hour >= 21 or candidate.hour < 8:
                candidate = candidate.replace(hour=20, minute=0, second=0, microsecond=0)
                if local_start.hour < 8 and candidate.date() == local_start.date():
                    candidate -= timedelta(days=1)

            if candidate.astimezone(ZoneInfo("UTC")) < now.astimezone(ZoneInfo("UTC")):
                continue

            when = local_start.strftime("%Y-%m-%d")
            time = local_start.strftime("%H:%M")
            prefix = f"Hi {name}, " if name else ""
            text = f"{prefix}your appointment is {when} at {time}. {signoff}"
            if use_sms and len(text) > 160:
                fixed = f"Your appointment is {when} at {time}. {signoff}"
                if len(fixed) > 160:
                    text = fixed[:160]
                else:
                    available = 160 - len(fixed) - 5
                    short_name = name[:max(0, available)].rstrip()
                    text = f"Hi {short_name}, {fixed}" if short_name else fixed

            reminders.append({
                "appointment_id": appointment_id,
                "channel": channel,
                "send_at": candidate,
                "text": text,
            })
            _LOG.info(
                "Planned %s reminder for %s via %s to %s",
                label, name or str(appointment_id), channel, contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"].astimezone(ZoneInfo("UTC")))
    return reminders