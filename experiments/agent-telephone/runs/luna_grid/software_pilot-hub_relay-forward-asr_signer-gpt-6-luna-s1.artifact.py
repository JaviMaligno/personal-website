from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)
_SIGNATURE_DEFAULT = "Chevonne Nee Divver"
_SIGNATURE_PL = "Grzegorz Szczepański"


def plan_reminders(appointments, now):
    """Return scheduled appointment reminders, ordered by their Dublin send time."""
    now_dublin = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if str(appointment.get("status", "")).lower() == "cancelled":
            continue

        starts_at = appointment["starts_at"].astimezone(_DUBLIN)
        appointment_date = starts_at.strftime("%d/%m/%Y")
        appointment_time = starts_at.strftime("%H:%M")
        signature = (
            _SIGNATURE_PL
            if appointment.get("country") == "PL"
            else _SIGNATURE_DEFAULT
        )
        name = str(appointment.get("customer_name") or "")

        phone = appointment.get("phone")
        if phone and not appointment.get("optout_sms_v2", False):
            channel = "sms"
            contact = phone
        elif appointment.get("email"):
            channel = "email"
            contact = appointment["email"]
        else:
            continue

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            send_at = starts_at - offset
            if offset == timedelta(hours=48) and send_at < now_dublin:
                send_at = now_dublin
            elif send_at < now_dublin:
                continue

            if send_at.hour >= 21 or send_at.hour < 8:
                send_at = send_at.replace(hour=20, minute=0, second=0, microsecond=0)
            if send_at < now_dublin:
                continue

            if channel == "sms":
                text = (
                    f"Hi {name}, your appointment is on {appointment_date} "
                    f"at {appointment_time}. {signature}"
                )
                while len(text) > 160 and name:
                    name = name[:-1]
                    text = (
                        f"Hi {name}, your appointment is on {appointment_date} "
                        f"at {appointment_time}. {signature}"
                    )
            else:
                text = (
                    f"Hello {name}, your appointment is on {appointment_date} "
                    f"at {appointment_time}. {signature}"
                )

            reminders.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }
            )
            if channel == "sms":
                _LOG.info(
                    "Reminder for %s via SMS to %s",
                    name or "customer",
                    contact,
                )
            else:
                _LOG.info(
                    "Reminder for %s via email (address redacted)",
                    name or "customer",
                )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders