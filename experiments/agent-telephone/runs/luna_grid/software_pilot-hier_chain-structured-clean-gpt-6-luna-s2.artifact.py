from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    """Return chronologically sorted SMS and email reminders."""
    def as_dublin(value, field):
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise ValueError(f"{field} must be a timezone-aware datetime")
        return value.astimezone(_DUBLIN)

    now_local = as_dublin(now, "now")
    now_utc = now_local.astimezone(timezone.utc)
    reminders = []

    for appointment in appointments:
        required = ("id", "customer_name", "email", "phone", "country",
                    "status", "starts_at", "optout_sms_v2")
        missing = [field for field in required if field not in appointment]
        if missing:
            raise ValueError(f"Appointment is missing required fields: {', '.join(missing)}")

        if appointment["status"] == "cancelled":
            continue

        starts_local = as_dublin(appointment["starts_at"], "starts_at")
        starts_utc = starts_local.astimezone(timezone.utc)
        phone = appointment["phone"]
        use_sms = bool(phone and str(phone).strip()) and not appointment["optout_sms_v2"]
        channel = "sms" if use_sms else "email"
        contact_kind = "phone on file" if use_sms else "email address on file"

        date_text = starts_local.strftime("%d/%m/%Y")
        time_text = starts_local.strftime("%H:%M")
        signoff = ("Grzegorz Szczepański" if appointment["country"] == "PL"
                   else "Siobhán Ní Dhuibhir")
        name = str(appointment["customer_name"]).strip()
        if channel == "sms":
            prefix = f"Reminder: "
            suffix = f" appointment on {date_text} at {time_text}. {signoff}"
            available = 160 - len(prefix) - len(suffix)
            if available < 0:
                raise ValueError("Appointment date and required sign-off exceed SMS limit")
            name = name[:available].rstrip()
            message = prefix + name + suffix
            if len(message) > 160:
                raise ValueError("Unable to fit reminder within SMS limit")
        else:
            message = (
                f"Hello {name}, this is a reminder about your appointment "
                f"on {date_text} at {time_text}.\n\n{signoff}"
            )

        for hours_before in (48, 2):
            point_utc = starts_utc - timedelta(hours=hours_before)
            if hours_before == 48 and point_utc < now_utc:
                point_utc = now_utc
            if point_utc < now_utc:
                continue

            send_at = point_utc.astimezone(_DUBLIN)
            if send_at.hour >= 21 or send_at.hour < 8:
                quiet_adjusted = send_at.replace(hour=20, minute=0, second=0, microsecond=0)
                send_at = max(quiet_adjusted, now_local)

            if send_at < now_local:
                send_at = now_local

            reminder = {
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": message,
            }
            reminders.append(reminder)
            _LOG.info(
                "Planned reminder for appointment %s via %s (%s)",
                appointment["id"], channel, contact_kind,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders