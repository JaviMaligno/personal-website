from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    """Plan eligible appointment reminders in Europe/Dublin local time."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now_local = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        starts_at = appointment["starts_at"]
        if starts_at.tzinfo is None or starts_at.utcoffset() is None:
            raise ValueError("starts_at must be timezone-aware")
        if appointment.get("cancelled", False):
            continue
        if appointment.get("optout_sms_v2", False):
            continue

        start_local = starts_at.astimezone(_DUBLIN)
        channel = appointment.get("channel", "sms")
        if channel not in ("sms", "email"):
            continue
        contact = appointment.get("phone" if channel == "sms" else "email")
        if not contact:
            continue

        customer = str(appointment.get("customer_name", ""))
        date_text = start_local.strftime("%Y-%m-%d")
        time_text = start_local.strftime("%H:%M")
        signature = (
            "Grzegorz Szczepański"
            if appointment.get("country") == "PL"
            else "Siobhán Ní Dhuibhir"
        )

        for offset in (timedelta(hours=2), timedelta(hours=48)):
            candidate = start_local - offset
            if offset == timedelta(hours=48) and candidate < now_local:
                candidate = now_local
            if candidate.timetz().replace(tzinfo=None) >= time(21) or candidate.hour < 8:
                candidate = datetime.combine(
                    candidate.date() - timedelta(days=1), time(20), _DUBLIN
                )
            if candidate < now_local:
                continue

            text = f"Hello {customer}, your appointment is {date_text} at {time_text}. {signature}"
            if channel == "sms" and len(text) > 160:
                fixed = f"Hello , your appointment is {date_text} at {time_text}. {signature}"
                available = max(0, 160 - len(fixed))
                text = f"Hello {customer[:available]}, your appointment is {date_text} at {time_text}. {signature}"

            reminders.append({
                "appointment_id": appointment["appointment_id"],
                "channel": channel,
                "send_at": candidate,
                "text": text,
            })
            _LOG.info(
                "Reminder planned for %s via %s to %s",
                customer or appointment["appointment_id"],
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders