from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def _sms_text(name, appointment_local, signoff):
    date = appointment_local.strftime("%Y-%m-%d")
    time = appointment_local.strftime("%H:%M")
    prefix = f"Appointment reminder: "
    suffix = f" on {date} at {time}. {signoff}"
    available = max(0, 160 - len(prefix) - len(suffix))
    return prefix + name[:available] + suffix


def plan_reminders(appointments, now):
    now_utc = now.astimezone(timezone.utc)
    reminders = []

    for appointment in appointments:
        if appointment["status"] == "cancelled":
            continue

        starts_utc = appointment["starts_at"].astimezone(timezone.utc)
        starts_local = starts_utc.astimezone(_DUBLIN)
        signoff = (
            "Grzegorz Szczepański"
            if appointment["country"] == "PL"
            else "Siobhán Ní Dhuibhir"
        )
        use_sms = bool(appointment["phone"] and appointment["optout_sms_v2"])
        channel = "sms" if use_sms else "email"

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            send_utc = starts_utc - offset
            if offset == timedelta(hours=48) and send_utc < now_utc:
                send_utc = now_utc
            elif send_utc < now_utc:
                continue

            send_local = send_utc.astimezone(_DUBLIN)
            if send_local.hour >= 21:
                send_local = send_local.replace(hour=20, minute=0, second=0, microsecond=0)
            elif send_local.hour < 8:
                send_local = (send_local - timedelta(days=1)).replace(
                    hour=20, minute=0, second=0, microsecond=0
                )

            send_utc = send_local.astimezone(timezone.utc)
            if send_utc < now_utc:
                continue

            if use_sms:
                text = _sms_text(appointment["customer_name"], starts_local, signoff)
            else:
                text = (
                    f"Appointment reminder: {appointment['customer_name']} "
                    f"on {starts_local:%Y-%m-%d} at {starts_local:%H:%M}. {signoff}"
                )

            reminders.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": send_local,
                    "text": text,
                }
            )
            contact = appointment["phone"] if use_sms else "[redacted]"
            _LOG.info(
                "Reminder recipient=%s channel=%s contact=%s",
                appointment["customer_name"],
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"].astimezone(timezone.utc))
    return reminders