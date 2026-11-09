from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import logging

DUBLIN = ZoneInfo("Europe/Dublin")
SECOND_REMINDER_LEAD = timedelta(hours=2)
SIGNATURE = "Siobhán Ní Dhuibhir"
POLISH_SIGNATURE = "Grzegorz Szczepański"
logger = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    now_utc = now.astimezone(timezone.utc)
    reminders = []

    for appointment in appointments:
        if appointment.get("status", "").lower() == "cancelled":
            continue

        starts_at = appointment["starts_at"]
        starts_utc = starts_at.astimezone(timezone.utc)
        starts_local = starts_at.astimezone(DUBLIN)
        signature = (
            POLISH_SIGNATURE if appointment.get("country") == "PL" else SIGNATURE
        )
        name = str(appointment.get("customer_name") or "")
        when = f"{starts_local:%d %B %Y} at {starts_local:%H:%M}"
        channel = (
            "sms"
            if appointment.get("phone") and not appointment.get("optout_sms_v2")
            else "email"
        )

        for reminder_type, lead in (
            ("48-hour", timedelta(hours=48)),
            ("2-hour", SECOND_REMINDER_LEAD),
        ):
            if lead is None:
                continue

            scheduled_utc = starts_utc - lead
            if scheduled_utc < now_utc:
                scheduled_utc = now_utc

            send_at = scheduled_utc.astimezone(DUBLIN)
            if 0 <= send_at.hour < 8 or 21 <= send_at.hour:
                send_at = send_at.replace(hour=20, minute=0, second=0, microsecond=0)
                if send_at.astimezone(timezone.utc) < now_utc:
                    send_at = now.astimezone(DUBLIN)

            text = f"Hi {name}, your appointment is {when}. {signature}"
            if channel == "sms" and len(text) > 160:
                suffix = f", your appointment is {when}. {signature}"
                text = f"Hi {name[:max(0, 160 - len('Hi ' + suffix))]}{suffix}"
                if len(text) > 160:
                    text = text[:160 - len(suffix)] + suffix

            reminders.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }
            )
            contact = appointment.get("phone") or "redacted"
            logger.info(
                "Reminder planned: appointment_id=%s type=%s who=%s channel=%s contact=%s send_at=%s",
                appointment["id"],
                reminder_type,
                name,
                channel,
                contact if channel == "sms" else "redacted",
                send_at.isoformat(),
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders