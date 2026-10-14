from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging


_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)
_SIGNATURES = {
    "PL": "Grzegorz Szczepański",
}
_DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"


def plan_reminders(appointments, now):
    """Return scheduled appointment reminders, sorted by send_at."""
    now_dublin = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment.get("status") == "cancelled":
            continue

        starts_at = appointment["starts_at"].astimezone(_DUBLIN)
        signature = _SIGNATURES.get(appointment.get("country"), _DEFAULT_SIGNATURE)
        opted_out = appointment.get("optout_sms_v2", False)

        for hours_before in (48, 2):
            scheduled = starts_at - timedelta(hours=hours_before)

            if scheduled < now_dublin:
                if hours_before == 2 or hours_before != 48:
                    continue
                scheduled = now_dublin

            if scheduled.hour >= 21 or scheduled.hour < 8:
                scheduled = scheduled.replace(hour=20, minute=0, second=0, microsecond=0)
                if scheduled < now_dublin:
                    continue

            if appointment.get("phone") and not opted_out:
                channel = "sms"
                contact = appointment["phone"]
                text = (
                    f"Reminder: {appointment['customer_name']}, your appointment is "
                    f"{starts_at:%Y-%m-%d} at {starts_at:%H:%M}. {signature}"
                )
                if len(text) > 160:
                    fixed = (
                        f"Reminder: , your appointment is {starts_at:%Y-%m-%d} "
                        f"at {starts_at:%H:%M}. {signature}"
                    )
                    name_budget = max(0, 160 - len(fixed))
                    text = (
                        f"Reminder: {appointment['customer_name'][:name_budget]}, "
                        f"your appointment is {starts_at:%Y-%m-%d} at "
                        f"{starts_at:%H:%M}. {signature}"
                    )
            else:
                channel = "email"
                contact = appointment.get("email")
                if not contact:
                    continue
                text = (
                    f"Reminder: your appointment is {starts_at:%Y-%m-%d} "
                    f"at {starts_at:%H:%M}. {signature}"
                )

            _LOG.info("Planned reminder for %s via %s to %s", appointment["id"], channel, contact)
            reminders.append({
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": scheduled,
                "text": text,
            })

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders