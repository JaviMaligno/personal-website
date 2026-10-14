from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
SIGNATURE = "Chevonne Nee Divver"
PL_SIGNATURE = "Grzegorz Szczepański"


def plan_reminders(appointments, now):
    now = now.astimezone(DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment.get("status") == "cancelled":
            continue

        appointment_at = next(
            appointment[key]
            for key in ("appointment_at", "appointment_datetime", "starts_at", "datetime")
            if key in appointment
        ).astimezone(DUBLIN)

        phone = appointment.get("phone_number") or appointment.get("phone")
        channel = (
            "sms"
            if phone and not appointment.get("optout_sms_v2", False)
            else "email"
        )
        signature = PL_SIGNATURE if appointment.get("country") == "PL" else SIGNATURE
        customer = appointment.get("customer_name") or appointment.get("name") or ""
        date_time = appointment_at.strftime("%Y-%m-%d at %H:%M")
        text = f"Reminder for {customer}: your appointment is {date_time}. {signature}"

        if channel == "sms" and len(text) > 160:
            suffix = f": your appointment is {date_time}. {signature}"
            prefix = "Reminder for "
            available = 160 - len(prefix) - len(suffix)
            text = f"{prefix}{customer[:max(0, available)]}{suffix}"

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            send_at = appointment_at - offset
            if send_at < now:
                send_at = now

            local = send_at.astimezone(DUBLIN)
            if local.hour >= 21 or local.hour < 8:
                day = local.date() if local.hour >= 21 else (local - timedelta(days=1)).date()
                send_at = datetime.combine(day, datetime.min.time(), DUBLIN).replace(
                    hour=20
                )

            if send_at >= now:
                reminders.append(
                    {
                        "appointment_id": appointment.get("appointment_id", appointment.get("id")),
                        "channel": channel,
                        "send_at": send_at,
                        "text": text,
                    }
                )
                import logging

                logging.info(
                    "Planned reminder for %s via %s to %s",
                    appointment.get("customer_name") or appointment.get("name") or "customer",
                    channel,
                    phone if channel == "sms" else "email",
                )

    return sorted(reminders, key=lambda reminder: reminder["send_at"])