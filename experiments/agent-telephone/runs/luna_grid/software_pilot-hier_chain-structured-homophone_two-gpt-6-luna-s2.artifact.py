from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_SIGNATURES = {
    "PL": "Grzegorz Szczepański",
}
_DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"
_LOGGER = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    local_now = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if str(appointment["status"]).casefold() == "cancelled":
            continue

        starts_at = appointment["starts_at"].astimezone(_DUBLIN)
        signature = _SIGNATURES.get(
            str(appointment["country"]).upper(), _DEFAULT_SIGNATURE
        )
        use_sms = bool(appointment["phone"]) and not appointment["optout_sms_v2"]
        channel = "sms" if use_sms else "email"
        contact = appointment["phone"] if use_sms else "[redacted]"
        name = str(appointment["customer_name"] or "")
        appointment_time = starts_at.strftime("%Y-%m-%d at %H:%M")
        suffix = f" Your appointment is on {appointment_time}. {signature}"

        for lead_hours in (2, 48):
            send_at = starts_at - timedelta(hours=lead_hours)
            if lead_hours == 48 and send_at < local_now:
                send_at = local_now

            if send_at.hour >= 21 or send_at.hour <= 7:
                send_at = (send_at - timedelta(days=1)).replace(
                    hour=20, minute=0, second=0, microsecond=0
                )

            if send_at < local_now:
                continue

            text = f"Hi {name},{suffix}"
            if use_sms and len(text) > 160:
                available = max(0, 160 - len(f"Hi ,{suffix}"))
                text = f"Hi {name[:available]},{suffix}"
                if len(text) > 160:
                    text = suffix.strip()

            reminders.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                    "_lead_hours": lead_hours,
                }
            )
            _LOGGER.info(
                "Reminder planned for %s via %s to %s",
                name,
                channel,
                contact,
            )

    reminders.sort(
        key=lambda reminder: (
            reminder["send_at"],
            str(reminder["appointment_id"]),
            reminder["_lead_hours"],
        )
    )
    for reminder in reminders:
        del reminder["_lead_hours"]
    return reminders