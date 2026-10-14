from datetime import datetime, timedelta, timezone
import logging
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_SIGNATURES = {
    "PL": "Grzegorz Szczepański",
}
_DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    now_utc = now.astimezone(timezone.utc)
    reminders = []

    for appointment in appointments:
        if appointment["status"] == "cancelled":
            continue

        starts_at = appointment["starts_at"]
        starts_utc = starts_at.astimezone(timezone.utc)
        if starts_utc <= now_utc:
            continue

        # Apply the client's stated SMS condition literally.
        if appointment["phone"] and appointment["optout_sms_v2"]:
            channel = "sms"
            contact = appointment["phone"]
        else:
            channel = "email"
            contact = appointment["email"]

        local_start = starts_at.astimezone(_DUBLIN)
        date_time = f"{local_start:%Y-%m-%d} at {local_start:%H:%M}"
        signature = _SIGNATURES.get(appointment["country"], _DEFAULT_SIGNATURE)
        name = appointment["customer_name"]

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            send_utc = starts_utc - lead
            if send_utc < now_utc:
                send_utc = now_utc

            send_at = send_utc.astimezone(_DUBLIN)
            if send_at.hour >= 21 or send_at.hour < 8:
                send_at = send_at.replace(hour=20, minute=0, second=0, microsecond=0)
                if send_at.astimezone(timezone.utc) < now_utc:
                    continue

            text = f"Hello {name}, your appointment is on {date_time}. {signature}"
            if channel == "sms" and len(text) > 160:
                fixed = f"Hello, your appointment is on {date_time}. {signature}"
                available = max(0, 160 - len(fixed) - 1)
                short_name = name[:available].rstrip()
                text = f"Hello {short_name}, your appointment is on {date_time}. {signature}"
                if len(text) > 160:
                    text = fixed[:160]

            reminders.append({
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            _LOG.info("Planned reminder for %s via %s to %s", appointment["customer_name"], channel, contact)

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders