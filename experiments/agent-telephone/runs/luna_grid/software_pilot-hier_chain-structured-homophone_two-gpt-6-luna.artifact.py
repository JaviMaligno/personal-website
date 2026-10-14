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
        if appointment["status"] == "cancelled":
            continue

        channel = (
            "sms"
            if appointment.get("phone") and not appointment.get("optout_sms_v2", False)
            else "email"
        )
        starts_at = appointment["starts_at"].astimezone(_DUBLIN)
        date_time = starts_at.strftime("%Y-%m-%d %H:%M")
        signature = _SIGNATURES.get(appointment.get("country"), "Siobhán Ní Dhuibhir")
        name = str(appointment["customer_name"])
        text = f"Reminder for {name}: appointment on {date_time}. {signature}"

        if channel == "sms" and len(text) > 160:
            suffix = f": appointment on {date_time}. {signature}"
            available = 160 - len("Reminder for ") - len(suffix)
            text = f"Reminder for {name[:max(0, available)]}{suffix}"

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            send_at = max(starts_at - lead, now)

            if time(21) <= send_at.timetz().replace(tzinfo=None) or send_at.hour < 8:
                if send_at.hour < 8:
                    send_at = (send_at - timedelta(days=1)).replace(
                        hour=20, minute=0, second=0, microsecond=0
                    )
                else:
                    send_at = send_at.replace(
                        hour=20, minute=0, second=0, microsecond=0
                    )

                if send_at < now:
                    send_at = (
                        now.replace(hour=8, minute=0, second=0, microsecond=0)
                        if now.hour < 8 or now.hour >= 21
                        else now
                    )

            _LOG.info(
                "Planned reminder for %s via %s to %s",
                name,
                channel,
                appointment.get("phone") if channel == "sms" else "email",
            )
            reminders.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }
            )

    return sorted(reminders, key=lambda reminder: reminder["send_at"])