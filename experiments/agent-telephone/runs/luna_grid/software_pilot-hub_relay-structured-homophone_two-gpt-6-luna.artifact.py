from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging


_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)
_SIGNATURES = {
    "PL": "Grzegorz Szczepański",
}


def plan_reminders(appointments, now):
    now = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if str(appointment.get("status", "")).lower() == "cancelled":
            continue

        appointment_at = appointment.get(
            "datetime",
            appointment.get("appointment_datetime", appointment.get("start")),
        )
        if appointment_at is None:
            continue
        appointment_at = appointment_at.astimezone(_DUBLIN)

        phone = appointment.get("phone_number") or appointment.get("phone")
        use_sms = bool(phone) and not appointment.get("optout_sms_v2", False)
        channel = "sms" if use_sms else "email"
        contact = phone if use_sms else "address withheld"

        name = str(appointment.get("customer_name", appointment.get("name", "Customer")))
        signature = _SIGNATURES.get(appointment.get("country"), "Siobhán Ní Dhuibhir")
        date_text = appointment_at.strftime("%Y-%m-%d")
        time_text = appointment_at.strftime("%H:%M")
        text = f"Reminder for your appointment on {date_text} at {time_text}. {signature}"

        if use_sms:
            full_text = f"Hi {name}, {text}"
            if len(full_text) <= 160:
                text = full_text
            else:
                text = f"Hi, {text}"
                if len(text) > 160:
                    text = text[:160]

        for interval in (timedelta(hours=48), timedelta(hours=2)):
            send_at = max(appointment_at - interval, now)
            if send_at.hour >= 21:
                send_at = send_at.replace(hour=20, minute=0, second=0, microsecond=0)
            elif send_at.hour < 8:
                send_at = (send_at - timedelta(days=1)).replace(
                    hour=20, minute=0, second=0, microsecond=0
                )

            if send_at < now or send_at >= appointment_at:
                continue

            reminder = {
                "appointment_id": appointment.get("appointment_id"),
                "channel": channel,
                "send_at": send_at,
                "text": text,
            }
            reminders.append(reminder)
            _LOG.info(
                "Planned reminder for %s via %s to %s",
                appointment.get("appointment_id"),
                channel,
                contact if use_sms else "email (address withheld)",
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders