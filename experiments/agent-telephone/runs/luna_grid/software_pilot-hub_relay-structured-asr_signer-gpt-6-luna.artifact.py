from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging


_DUBLIN = ZoneInfo("Europe/Dublin")
_SIGNATURE_DEFAULT = "Chevonne Nee Divver"
_SIGNATURE_PL = "Grzegorz Szczepański"
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    """Return scheduled reminders for timezone-aware appointment datetimes."""
    now_local = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment.get("status") == "cancelled":
            continue

        customer = appointment.get("customer") or {}
        name = customer.get("name", appointment.get("customer_name", ""))
        phone = customer.get("phone", appointment.get("phone"))
        email = customer.get("email", appointment.get("email"))
        opted_out = customer.get(
            "optout_sms_v2", appointment.get("optout_sms_v2", False)
        )
        country = customer.get("country", appointment.get("country"))
        channel = "sms" if phone and not opted_out else "email"
        contact = phone if channel == "sms" else email
        signature = _SIGNATURE_PL if country == "PL" else _SIGNATURE_DEFAULT

        appointment_at = (
            appointment.get("appointment_datetime")
            or appointment.get("datetime")
            or appointment.get("start")
        )
        appointment_local = appointment_at.astimezone(_DUBLIN)
        appointment_display = appointment_local.strftime("%Y-%m-%d at %H:%M")

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            send_at = max(appointment_local - offset, now_local)

            if send_at.hour >= 21:
                send_at = send_at.replace(hour=20, minute=0, second=0, microsecond=0)
            elif send_at.hour < 8:
                send_at = (send_at - timedelta(days=1)).replace(
                    hour=20, minute=0, second=0, microsecond=0
                )

            if send_at < now_local:
                send_at = now_local.replace(hour=20, minute=0, second=0, microsecond=0)
                if send_at < now_local:
                    send_at += timedelta(days=1)

            message = f"Reminder: your appointment is {appointment_display}. {signature}"
            if channel == "sms" and len(message) > 160:
                short_name = name[:1] if name else ""
                message = f"Reminder {short_name}: appointment {appointment_display}. {signature}"
                if len(message) > 160:
                    message = f"Appointment {appointment_display}. {signature}"

            reminder = {
                "appointment_id": appointment.get("appointment_id"),
                "channel": channel,
                "send_at": send_at,
                "text": message,
            }
            reminders.append(reminder)
            _LOG.info(
                "Planned reminder for %s via %s to %s",
                name or "customer",
                channel,
                "phone" if channel == "sms" else "email (address redacted)",
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders