from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging


_LOGGER = logging.getLogger(__name__)
_DUBLIN = ZoneInfo("Europe/Dublin")


def plan_reminders(appointments, now):
    """Return SMS or email reminders for non-cancelled appointments."""
    reminders = []

    for appointment in appointments:
        if appointment.get("status") == "cancelled":
            continue

        starts_at = appointment["starts_at"]
        name = appointment.get("customer_name") or appointment.get("name") or ""
        phone = appointment.get("phone")
        email = appointment.get("email")

        if phone and appointment.get("optout_sms_v2") is False:
            channel, contact = "sms", phone
        elif email:
            channel, contact = "email", "email address redacted"
        else:
            continue

        local_start = starts_at
        date_text = local_start.strftime("%Y-%m-%d")
        time_text = local_start.strftime("%H:%M")
        signature = (
            "Grzegorz Szczepański"
            if appointment.get("country") == "PL"
            else "Siobhán Ní Dhuibhir"
        )
        base_text = f"Hi {{name}}, reminder: appointment on {date_text} at {time_text}. {signature}"
        customer_name = str(name)

        if channel == "sms":
            text = base_text.format(name=customer_name)
            while len(text) > 160 and customer_name:
                customer_name = customer_name[:-1]
                text = base_text.format(name=customer_name)
            if len(text) > 160:
                text = f"Appointment {date_text} {time_text}. {signature}"
        else:
            text = base_text.format(name=customer_name)

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            send_at = starts_at - offset
            if send_at < now:
                send_at = now

            dublin_time = send_at.astimezone(_DUBLIN)
            if dublin_time.time() >= time(21, 0) or dublin_time.time() < time(8, 0):
                previous_day = dublin_time.date()
                if dublin_time.time() < time(8, 0):
                    previous_day -= timedelta(days=1)
                quiet_adjusted = datetime.combine(
                    previous_day, time(20, 0), tzinfo=_DUBLIN
                ).astimezone(send_at.tzinfo)
                send_at = max(quiet_adjusted, now)

            reminders.append(
                {
                    "appointment_id": appointment.get("appointment_id"),
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }
            )
            _LOGGER.info(
                "Reminder for %s via %s to %s",
                name or appointment.get("appointment_id", "customer"),
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders