from datetime import datetime, time, timedelta
from logging import getLogger
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
LOGGER = getLogger(__name__)
SIGNATURE_IE = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"


def plan_reminders(appointments, now):
    now_local = now.astimezone(DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment.get("status") == "cancelled":
            continue

        phone = appointment.get("phone")
        use_sms = bool(phone) and not appointment.get("optout_sms_v2", False)
        channel = "sms" if use_sms else "email"
        contact = phone if use_sms else appointment.get("email")
        if not contact:
            continue

        starts_at = appointment["starts_at"].astimezone(DUBLIN)
        signature = SIGNATURE_PL if appointment.get("country") == "PL" else SIGNATURE_IE
        appointment_time = starts_at.strftime("%d %B %Y at %H:%M")
        name = str(appointment.get("customer_name") or "").strip()

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            send_at = max(starts_at - lead, now_local)
            if send_at.time() >= time(21) or send_at.time() < time(8):
                send_at = send_at.replace(hour=20, minute=0, second=0, microsecond=0)
                if send_at < now_local:
                    send_at = now_local.replace(
                        hour=8, minute=0, second=0, microsecond=0
                    )
                    if send_at <= now_local:
                        send_at += timedelta(days=1)

            if channel == "sms":
                prefix = f"Hi {name}, " if name else ""
                text = f"{prefix}your appointment is {appointment_time}. {signature}"
                if len(text) > 160:
                    available = 160 - len(f"Hi , your appointment is {appointment_time}. {signature}")
                    short_name = name[:max(0, available)].rstrip()
                    text = (
                        f"Hi {short_name}, your appointment is {appointment_time}. {signature}"
                        if short_name
                        else f"Your appointment is {appointment_time}. {signature}"
                    )
            else:
                prefix = f"Hi {name}, " if name else ""
                text = f"{prefix}your appointment is {appointment_time}. {signature}"

            reminders.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }
            )
            logged_contact = contact if channel == "sms" else "[email]"
            LOGGER.info(
                "Reminder for %s via %s to %s",
                name or "customer",
                channel,
                logged_contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders
