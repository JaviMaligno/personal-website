from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    """Return appointment reminders scheduled in Europe/Dublin local time."""
    now = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if str(appointment.get("status", "")).lower() == "cancelled":
            continue

        appointment_at = next(
            appointment[key]
            for key in ("appointment_datetime", "starts_at", "datetime")
            if key in appointment
        ).astimezone(_DUBLIN)

        customer = appointment.get("customer", {})
        name = customer.get("name", appointment.get("customer_name", ""))
        phone = customer.get("phone", appointment.get("phone"))
        email = customer.get("email", appointment.get("email"))
        country = customer.get("country", appointment.get("country"))
        signature = "Grzegorz Szczepański" if country == "PL" else "Siobhán Ní Dhuibhir"

        when = appointment_at.strftime("%Y-%m-%d")
        at = appointment_at.strftime("%H:%M")
        for lead in (timedelta(hours=48), timedelta(hours=2)):
            send_at = appointment_at - lead
            if send_at < now:
                send_at = now

            local = send_at.astimezone(_DUBLIN)
            if local.hour >= 21:
                local = local.replace(hour=20, minute=0, second=0, microsecond=0)
            elif local.hour < 8:
                local = (local - timedelta(days=1)).replace(
                    hour=20, minute=0, second=0, microsecond=0
                )
            send_at = local
            if send_at < now:
                if now.hour < 8 or now.hour >= 21:
                    send_at = (now + timedelta(days=1)).replace(
                        hour=8, minute=0, second=0, microsecond=0
                    )
                else:
                    send_at = now

            channel = (
                "sms"
                if phone and not customer.get(
                    "optout_sms_v2", appointment.get("optout_sms_v2", False)
                )
                else "email"
            )
            text = f"Hi {name}, reminder: your appointment is on {when} at {at}. {signature}"
            if channel == "sms" and len(text) > 160:
                fixed = f"Hi , reminder: your appointment is on {when} at {at}. {signature}"
                name = name[: max(0, 160 - len(fixed))]
                text = f"Hi {name}, reminder: your appointment is on {when} at {at}. {signature}"
                if len(text) > 160:
                    text = fixed[: 160 - len(signature)] + signature

            reminder = {
                "appointment_id": appointment.get("appointment_id", appointment.get("id")),
                "channel": channel,
                "send_at": send_at,
                "text": text,
            }
            reminders.append(reminder)
            contact = phone if channel == "sms" else "[email address redacted]"
            _LOG.info(
                "Planned reminder for %s via %s to %s",
                name or "customer",
                channel,
                contact or "[contact unavailable]",
            )

    return sorted(reminders, key=lambda reminder: reminder["send_at"])