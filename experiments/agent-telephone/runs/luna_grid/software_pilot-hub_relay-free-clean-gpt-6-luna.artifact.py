from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

__all__ = ["plan_reminders"]

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    """Return upcoming appointment reminders, ordered by local send time."""
    now_local = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment.get("cancelled"):
            continue

        appointment_at = appointment.get("starts_at", appointment.get("appointment_at"))
        if appointment_at is None:
            continue
        appointment_local = appointment_at.astimezone(_DUBLIN)
        if appointment_local <= now_local:
            continue

        phone = appointment.get("phone")
        use_sms = bool(phone) and not appointment.get("optout_sms_v2", False)
        channel = "sms" if use_sms else "email"
        contact = phone if use_sms else appointment.get("email")
        if not contact:
            continue

        name = str(appointment.get("customer_name", "")).strip()
        ending = (
            "Grzegorz Szczepański"
            if str(appointment.get("country", "")).upper() == "PL"
            else "Siobhán Ní Dhuibhir"
        )
        appointment_time = appointment_local.strftime("%Y-%m-%d %H:%M")
        appointment_id = appointment.get("appointment_id")

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            due = appointment_local - lead
            if lead == timedelta(hours=48) and due <= now_local:
                due = now_local
            elif due <= now_local:
                continue

            if due.hour >= 21:
                due = due.replace(hour=20, minute=0, second=0, microsecond=0)
            elif due.hour < 8:
                due = (due - timedelta(days=1)).replace(
                    hour=20, minute=0, second=0, microsecond=0
                )

            if due < now_local:
                due = now_local

            prefix = f"Reminder: {name}, appointment {appointment_time}. "
            text = f"{prefix}{ending}"
            if use_sms and len(text) > 160:
                available = max(0, 160 - len(f"Reminder: , appointment {appointment_time}. {ending}"))
                name = name[:available]
                prefix = f"Reminder: {name}, appointment {appointment_time}. "
                text = f"{prefix}{ending}"

            reminders.append(
                {
                    "appointment_id": appointment_id,
                    "channel": channel,
                    "send_at": due,
                    "text": text,
                    "_contact": contact,
                }
            )

    reminders.sort(key=lambda item: item["send_at"])
    for reminder in reminders:
        _LOG.info(
            "Reminder for appointment %s via %s to %s",
            reminder["appointment_id"],
            reminder["channel"],
            reminder["_contact"] if reminder["channel"] == "sms" else "[email recipient]",
        )
        reminder.pop("_contact")
    return reminders