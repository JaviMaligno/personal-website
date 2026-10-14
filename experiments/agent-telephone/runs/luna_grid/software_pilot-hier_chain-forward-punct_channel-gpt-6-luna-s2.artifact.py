from datetime import datetime, time, timedelta, timezone
import logging
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    """Return appointment reminders with timezone-aware send_at datetimes."""
    now_utc = now.astimezone(timezone.utc)
    reminders = []

    for appointment in appointments:
        if appointment.get("status") == "cancelled":
            continue

        phone = appointment.get("phone")
        if phone and not appointment.get("optout_sms_v2", False):
            channel = "sms"
            contact = phone
        elif appointment.get("email"):
            channel = "email"
            contact = "[redacted]"
        else:
            continue

        starts_at = appointment["starts_at"]
        local_start = starts_at.astimezone(_DUBLIN)
        date_text = local_start.strftime("%B %d, %Y")
        time_text = local_start.strftime("%H:%M")
        signature = (
            "Grzegorz Szczepański"
            if appointment.get("country") == "PL"
            else "Siobhán Ní Dhuibhir"
        )
        name = str(appointment.get("customer_name") or "")
        base_text = f"Your appointment is on {date_text} at {time_text}. {signature}"
        full_text = f"Hi {name}, your appointment is on {date_text} at {time_text}. {signature}"

        candidates = []
        for offset in (timedelta(hours=48), timedelta(hours=2)):
            target_utc = starts_at.astimezone(timezone.utc) - offset
            if offset == timedelta(hours=48) and target_utc < now_utc:
                target_utc = now_utc

            local_target = target_utc.astimezone(_DUBLIN)
            if local_target.hour >= 21 or local_target.hour < 8:
                prior_day = local_target.date() - timedelta(days=1)
                local_target = datetime.combine(
                    prior_day, time(20, 0), tzinfo=_DUBLIN
                )

            send_at = local_target.astimezone(timezone.utc)
            if send_at < now_utc:
                continue

            if channel == "sms":
                text = full_text if len(full_text) <= 160 else base_text
                if len(text) > 160:
                    text = f"{date_text} {time_text}. {signature}"
            else:
                text = full_text

            candidates.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": send_at.astimezone(_DUBLIN),
                    "text": text,
                }
            )

        reminders.extend(candidates)

    reminders.sort(key=lambda reminder: reminder["send_at"].astimezone(timezone.utc))
    for reminder in reminders:
        appointment = next(
            a for a in appointments if a.get("id") == reminder["appointment_id"]
        )
        if reminder["channel"] == "sms":
            contact = appointment.get("phone") or "[redacted]"
        else:
            contact = "[redacted]"
        _LOG.info(
            "Reminder for appointment %s via %s to %s",
            reminder["appointment_id"],
            reminder["channel"],
            contact,
        )

    return reminders